"""La ventana escucha siempre y trata cada turno de voz como uno escrito (pieza D de la 0.3,
ADR-244).

Las pruebas de aceptación (``tests/acceptance/test_robot_0_3_ventana.py``) miran lo que ve
el propietario con el conductor: que escucha al abrirse, el silencio y la charla por voz
con sus dos botones. Estas miran los bordes que allí no salen: qué dice si no puede oír,
que mientras contesta por voz la ventana está ocupada como con lo escrito, que si está con
otra cosa el turno no va, el cierre a mitad de un turno, y el bucle de producción. Sirius
va montado de verdad, con un micro, un oído, una voz y un modelo de mentira.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMainWindow, QPushButton
from pytestqt.qtbot import QtBot

from sirius.adapters.audio.fake import (
    FakeAudioCapture,
    FakeAudioPlayback,
    FakeSpeechToText,
    FakeTextToSpeech,
)
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.blind_test import BlindTestUseCase
from sirius.application.listening_loop import ListeningLoop
from sirius.application.local_listening import CHAT_LEAVES
from sirius.application.memory_commands import FORGET_ABOUT_STORED
from sirius.application.studio_voice import StudioVoiceUseCase, VoiceSettings
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.local_voice import LocalVoiceSettings
from sirius.config.settings import load_settings
from sirius.domain.reply_judge import TrickVerdict
from sirius.infrastructure.local_voice_installation import (
    INSTALL_COMMAND,
    LISTENING_MODEL_FILES,
    LocalVoiceInstallation,
    speaking_voice_files,
)
from sirius.infrastructure.network import connection_registry
from sirius.infrastructure.paths import resolve_paths
from sirius.main import (
    _build_initial_project_window,
    _build_listening_main_window,
    _build_main_window,
    _build_onboarding_window,
    _build_post_key_window,
    _release_on_quit,
)
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.llm import (
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)
from sirius.ports.local_voice import Captured, ListeningEngines, SpeakingEngines, TurnSignal
from sirius.ports.text_to_speech import (
    SpeechError,
    SpeechErrorKind,
    SpeechRequest,
    SynthesizedSpeech,
)
from sirius.presentation.error_messages import failed_send_message
from sirius.presentation.main_window import LISTENING, MUTED, VOICE_BUSY, VOICE_QUIET_SECONDS
from sirius.presentation.message_view import MessageItemWidget
from sirius.presentation.validated_main_window import ValidatedMainWindow

pytestmark = pytest.mark.gui


class _Modelo:
    """Un modelo de este ordenador. Contesta «Respuesta N.»; con ``antes``, eso pasa antes de
    escribir, en el hilo que envía; con ``se_rompe``, falla sin ser del modelo; con
    ``falla_con``, falla el modelo; con ``propone``, propone recordar algo."""

    runs_on_this_computer = True
    model_name = "de-aqui"

    def __init__(self) -> None:
        self.peticiones: list[str] = []
        self.operaciones: list[str] = []
        self.canceladas: list[str] = []
        self.antes: Callable[[], None] | None = None
        self.se_rompe = False
        self.propone: str | None = None
        self.falla_con: LLMErrorKind | None = None
        #: Cuántas veces le pidieron que cargara, como a Ollama al arrancar (ADR-252).
        self.precargas = 0

    def health_check(self) -> bool:
        return True

    def warm_up(self) -> None:
        self.precargas += 1

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        self.peticiones.append(request.input_text)
        self.operaciones.append(request.operation_id)
        if self.antes is not None:
            self.antes()
        if self.se_rompe:
            msg = "un fallo que no es del modelo"
            raise RuntimeError(msg)
        if request.operation_id in self.canceladas:
            yield LLMCancelled(partial_text="")
            return
        if self.falla_con is not None:
            yield LLMError(kind=self.falla_con, message="tarda", partial_text="")
            return
        texto = f"Respuesta {len(self.peticiones)}."
        yield LLMTextDelta(texto)
        yield LLMCompleted(
            text=texto, input_tokens=1, output_tokens=1, memory_suggestion=self.propone
        )

    def cancel(self, operation_id: str) -> None:
        self.canceladas.append(operation_id)


class _SinHuellas:
    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        del texts
        raise EmbeddingError("sin huellas")


class _Micro:
    """Lo que suena con él cerrado se pierde."""

    def __init__(self) -> None:
        self.abierto = False
        self.trozos: list[str] = []
        self.falla_al_abrir: Exception | None = None

    def open(self) -> None:
        if self.falla_al_abrir is not None:
            raise self.falla_al_abrir
        self.abierto = True

    def close(self) -> None:
        self.abierto = False
        self.trozos.clear()

    def read(self) -> Captured[str] | None:
        return Captured(self.trozos.pop(0)) if self.abierto and self.trozos else None


class _Detector:
    def __init__(self) -> None:
        self.falla: Exception | None = None

    def listen(self, chunk: str) -> TurnSignal:
        if self.falla is not None:
            raise self.falla
        return TurnSignal.ENDED if chunk == "fin" else TurnSignal.VOICE

    def reset(self) -> None:
        pass


class _Transcriptor:
    def __init__(self) -> None:
        self.dira = ""

    def transcribe(self, chunks: Sequence[str]) -> str:
        del chunks
        return self.dira


class _Voz:
    def say(self, text: str) -> str:
        return text


class _Altavoz:
    playing = False
    latency = 0.0

    def __init__(self) -> None:
        #: Suena en el acto: todo lo que toma empieza a sonar.
        self.started = 0
        #: Si lo soltaron: con él se suelta su cancelación de eco (ADR-252).
        self.cerrado = False

    def play(self, sound: str) -> None:
        del sound
        self.started += 1

    def stop(self) -> None:
        pass

    def close(self) -> None:
        self.cerrado = True


@dataclass
class _Sirius:
    deps: ConversationDependencies
    modelo: _Modelo
    micro: _Micro = field(default_factory=_Micro)
    detector: _Detector = field(default_factory=_Detector)
    transcriptor: _Transcriptor = field(default_factory=_Transcriptor)
    #: Cada altavoz que carga la voz, en orden.
    altavoces: list[_Altavoz] = field(default_factory=list)

    def suena(self, frase: str) -> None:
        """El propietario dice ``frase`` por el micro; aún nadie lo ha atendido."""
        self.transcriptor.dira = frase
        if self.micro.abierto:
            self.micro.trozos.extend(["voz", "fin"])


def _instala_la_voz() -> None:
    """Los modelos de oír y de hablar, donde los deja la orden de instalar: de mentira."""
    instalacion = LocalVoiceInstallation(LocalVoiceSettings())
    instalacion.listening_model_dir.mkdir(parents=True, exist_ok=True)
    for nombre in (*LISTENING_MODEL_FILES, "vocabulary.txt"):
        (instalacion.listening_model_dir / nombre).write_bytes(b"de mentira")
    instalacion.speaking_voice_dir.mkdir(parents=True, exist_ok=True)
    for nombre in speaking_voice_files(LocalVoiceSettings().speaking_voice.value):
        (instalacion.speaking_voice_dir / nombre).write_bytes(b"de mentira")


class _JuezQueCuenta:
    """Un juez de mentira: apunta lo que puntúa y da siempre un 4."""

    def __init__(self) -> None:
        self.puntuadas: list[str] = []

    def score(self, reply: str, *, should_stop: Callable[[], bool] | None = None) -> int:
        del should_stop
        self.puntuadas.append(reply)
        return 4

    def verdict(
        self, bad_idea: str, reply: str, *, should_stop: Callable[[], bool] | None = None
    ) -> TrickVerdict:
        del bad_idea, reply, should_stop
        return TrickVerdict.DISCREPA

    def cancel(self) -> None:
        pass

    def cancel_verdicts(self) -> None:
        pass


def _monta(
    tmp_path: Path, *, con_la_voz: bool = True, juez: _JuezQueCuenta | None = None
) -> _Sirius:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    if con_la_voz:
        _instala_la_voz()
    modelo = _Modelo()
    piezas: dict[str, object] = {}

    def oido() -> ListeningEngines[str]:
        sirius = piezas["sirius"]
        assert isinstance(sirius, _Sirius)
        return ListeningEngines(sirius.micro, sirius.detector, sirius.transcriptor)

    def altavoz() -> _Altavoz:
        sirius = piezas["sirius"]
        assert isinstance(sirius, _Sirius)
        sirius.altavoces.append(_Altavoz())
        return sirius.altavoces[-1]

    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
        listening_engines=oido,
        speaking_engines=lambda modelo_de_voz: SpeakingEngines(_Voz(), altavoz()),
        reply_judge=juez,
    )
    deps.initial_project_use_case.create_initial_project("Charla", "Charlar")
    deps.send_message_use_case.set_llm_provider(modelo)
    sirius = _Sirius(deps, modelo)
    piezas["sirius"] = sirius
    return sirius


def _ventana(qtbot: QtBot, sirius: _Sirius) -> ValidatedMainWindow:
    """La ventana de verdad, sin su bucle: el oído lo atiende la prueba. Espera a que lo de
    segundo plano que arranca al abrirse haya acabado."""
    ventana = _build_main_window(sirius.deps, [])
    qtbot.addWidget(ventana)
    qtbot.waitUntil(lambda: _sin_segundo_plano(ventana), timeout=5000)
    return ventana


def _sin_segundo_plano(ventana: ValidatedMainWindow) -> bool:
    return not (
        ventana.judge_in_progress or ventana.embedding_in_progress or ventana.dream_in_progress
    )


def _mensajes(ventana: ValidatedMainWindow) -> list[tuple[str, str]]:
    lista = ventana.message_list
    vistos: list[tuple[str, str]] = []
    for i in range(lista.count()):
        widget = lista.itemWidget(lista.item(i))
        if isinstance(widget, MessageItemWidget):
            vistos.append((lista.item(i).text().split(":", 1)[0], widget.rendered_plain_text()))
    return vistos


def test_al_abrirse_escucha_y_el_boton_lo_calla_y_lo_vuelve_a_abrir(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)

    assert (ventana.listening_label.text(), ventana.mute_button.text()) == (LISTENING, "Silencio")
    assert sirius.micro.abierto

    ventana.mute_button.click()

    assert (ventana.listening_label.text(), ventana.mute_button.text()) == (MUTED, "Escuchar")
    assert not sirius.micro.abierto
    assert ventana.voice_notice_label.text() == ""

    ventana.mute_button.click()

    assert (ventana.listening_label.text(), ventana.mute_button.text()) == (LISTENING, "Silencio")
    assert sirius.micro.abierto


def test_sin_la_voz_instalada_no_dice_que_escucha_y_dice_que_falta(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path, con_la_voz=False)
    ventana = _ventana(qtbot, sirius)

    assert ventana.listening_label.isHidden()
    assert ventana.mute_button.text() == "Escuchar"
    aviso = ventana.voice_notice_label.text()
    assert aviso.startswith("Para oírte y hablarte me falta instalar")
    assert INSTALL_COMMAND in aviso
    assert not sirius.micro.abierto


def test_si_abrir_el_oido_falla_como_no_se_espera_la_ventana_se_abre_y_lo_dice(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    sirius.micro.falla_al_abrir = RuntimeError("la clave es Zarzamora")

    ventana = _ventana(qtbot, sirius)

    assert ventana.listening_label.isHidden()
    aviso = "No puedo oírte: algo ha fallado al abrir el oído (RuntimeError)."
    assert ventana.voice_notice_label.text() == aviso
    ventana.mute_button.click()
    assert ventana.voice_notice_label.text() == aviso
    sirius.micro.falla_al_abrir = None
    ventana.mute_button.click()
    assert ventana.listening_label.text() == LISTENING


def test_volver_a_escuchar_tras_instalar_la_voz_no_pide_reabrir_sirius(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path, con_la_voz=False)
    ventana = _ventana(qtbot, sirius)
    _instala_la_voz()

    ventana.mute_button.click()

    assert ventana.listening_label.text() == LISTENING
    assert ventana.voice_notice_label.text() == ""
    assert sirius.micro.abierto


def test_si_deja_de_oir_por_su_cuenta_la_ventana_lo_dice(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    sirius.detector.falla = RuntimeError("roto")
    sirius.suena("Sirius, hola")

    sirius.deps.local_listening.attend()

    assert ventana.listening_label.isHidden()
    assert ventana.mute_button.text() == "Escuchar"
    assert ventana.voice_notice_label.text() == (
        "No puedo oírte: el detector de voz ha fallado (RuntimeError)."
    )


def test_lo_que_no_era_para_el_no_se_ve(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    antes = _mensajes(ventana)
    sirius.suena("Y mañana, cielos despejados.")

    sirius.deps.local_listening.attend()

    assert _mensajes(ventana) == antes
    assert sirius.modelo.peticiones == []


def test_mientras_contesta_por_voz_la_ventana_esta_ocupada_como_con_lo_escrito(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    vista: dict[str, object] = {}

    def mira_la_ventana() -> None:
        vista["enviar"] = ventana.send_button.isEnabled()
        vista["escribir"] = ventana.message_input.isEnabled()
        vista["cancelar"] = not ventana.cancel_button.isHidden()
        vista["estado"] = ventana.status_label.text()
        vista["ultimo"] = _mensajes(ventana)[-1]

    sirius.modelo.antes = mira_la_ventana
    sirius.suena("Sirius, ¿qué tal?")

    sirius.deps.local_listening.attend()

    assert vista == {
        "enviar": False,
        "escribir": False,
        "cancelar": False,
        "estado": "Sirius está pensando...",
        "ultimo": ("Tú", "Sirius, ¿qué tal?"),
    }
    assert _mensajes(ventana)[-2:] == [("Tú", "Sirius, ¿qué tal?"), ("Sirius", "Respuesta 1.")]
    assert ventana.send_button.isEnabled()
    assert ventana.status_label.text() == ""


def test_con_lo_escrito_en_marcha_un_turno_de_voz_no_va_y_lo_dice(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    escribiendo, sigue = threading.Event(), threading.Event()

    def espera() -> None:
        escribiendo.set()
        sigue.wait(5)

    sirius.modelo.antes = espera
    ventana.message_input.setText("Hola por escrito.")
    ventana.send_button.click()
    qtbot.waitUntil(escribiendo.is_set, timeout=5000)
    sirius.modelo.antes = None
    sirius.suena("Sirius, ¿me oyes?")

    try:
        atendido = sirius.deps.local_listening.attend()
    finally:
        sigue.set()
    qtbot.waitUntil(ventana.send_button.isEnabled, timeout=5000)

    assert atendido.turns == ()
    assert ventana.voice_notice_label.text() == VOICE_BUSY
    assert sirius.modelo.peticiones == ["Hola por escrito."]


def test_si_la_charla_se_rompe_en_un_turno_de_voz_se_ve_como_un_envio_roto(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    sirius.modelo.se_rompe = True
    sirius.suena("Sirius, ¿qué tal?")

    (turno,) = sirius.deps.local_listening.attend().turns

    assert ventana.error_label.text() == failed_send_message(None, turno.operation_id)
    assert not ventana.retry_button.isHidden()
    assert ventana.send_button.isEnabled()


def test_si_al_final_no_va_a_la_charla_lo_que_se_enseno_se_quita(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    antes = _mensajes(ventana)

    assert ventana.begin_voice_turn("op-1", "Sirius, hola") == []
    assert _mensajes(ventana)[-1] == ("Tú", "Sirius, hola")
    ventana.finish_voice_turn(None)

    assert _mensajes(ventana) == antes
    assert ventana.send_button.isEnabled()


def test_un_turno_de_voz_para_lo_de_segundo_plano_y_espera_a_que_acabe(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)

    class _Juez:
        def __init__(self) -> None:
            self.done = threading.Event()
            self.parado = False

        def stop(self) -> None:
            self.parado = True

    juez = _Juez()
    ventana._active_judge_worker = juez  # type: ignore[assignment]

    espera = ventana.begin_voice_turn("op-1", "Sirius, hola")

    assert espera == [juez.done]
    assert juez.parado
    ventana._active_judge_worker = None
    ventana.finish_voice_turn(None)


def test_cerrar_la_ventana_deja_de_oir_y_ya_no_la_mira(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)

    ventana.close()

    assert not sirius.deps.local_listening.listening
    assert not sirius.micro.abierto
    # Si alguien vuelve a abrir el oído, la ventana cerrada ya no es quien lo mira.
    sirius.deps.local_listening.start()
    sirius.suena("Sirius, ¿sigues ahí?")
    (turno,) = sirius.deps.local_listening.attend().turns
    assert turno.answered
    assert ("Tú", "Sirius, ¿sigues ahí?") not in _mensajes(ventana)


def test_cerrar_mientras_contesta_por_voz_lo_cancela_y_cierra_al_acabar(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    ventana.show()
    escribiendo, sigue = threading.Event(), threading.Event()

    def espera() -> None:
        escribiendo.set()
        sigue.wait(5)

    sirius.modelo.antes = espera
    sirius.suena("Sirius, cuéntame algo.")
    bucle = ListeningLoop(sirius.deps.local_listening, pause_seconds=0.01)
    bucle.start()
    try:
        qtbot.waitUntil(escribiendo.is_set, timeout=5000)
        ventana.close()
        # Espera a que acabe el turno: sigue abierta, ya no oye y el turno va cancelado.
        assert ventana.isVisible()
        assert not sirius.deps.local_listening.listening
        assert sirius.modelo.canceladas == sirius.modelo.operaciones
    finally:
        sigue.set()
    qtbot.waitUntil(lambda: not ventana.isVisible(), timeout=5000)
    bucle.stop()
    assert bucle.wait(5)


def test_la_ventana_de_verdad_atiende_al_oido_con_su_bucle_y_lo_para_al_cerrarse(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _build_listening_main_window(sirius.deps, [])
    qtbot.addWidget(ventana)
    bucle = ventana._listening_loop
    assert bucle is not None and bucle.running
    # Al arrancar pidió que el modelo de la charla fuera cargando (ADR-252).
    qtbot.waitUntil(lambda: sirius.modelo.precargas == 1, timeout=5000)

    sirius.suena("Sirius, hola.")
    qtbot.waitUntil(lambda: ("Sirius", "Respuesta 1.") in _mensajes(ventana), timeout=5000)

    ventana.close()

    assert bucle.wait(5)


def test_un_aviso_de_que_dejo_de_oir_que_llega_tarde_no_tapa_que_ya_escucha(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)

    ventana.listening_stopped("No puedo oírte: el detector de voz ha fallado (RuntimeError).")

    assert ventana.listening_label.text() == LISTENING
    assert ventana.voice_notice_label.text() == ""


def test_cerrada_la_ventana_un_turno_de_voz_no_empieza(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    ventana.close()

    assert ventana.begin_voice_turn("op-1", "Sirius, hola") is None
    assert ventana.send_button.isEnabled()


def test_con_una_exportacion_en_marcha_un_turno_de_voz_no_va_y_lo_dice(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    ventana._is_export_busy = True
    try:
        assert ventana.begin_voice_turn("op-1", "Sirius, hola") is None
        assert ventana.voice_notice_label.text() == VOICE_BUSY
    finally:
        ventana._is_export_busy = False


def test_olvida_lo_de_dicho_por_voz_se_ve_como_quedo_guardado(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    sirius.suena("Sirius, olvida lo de mi vecino Ramiro.")

    sirius.deps.local_listening.attend()

    assert ("Tú", FORGET_ABOUT_STORED) in _mensajes(ventana)
    assert not any("Ramiro" in texto for _, texto in _mensajes(ventana))


def test_lo_que_propone_recordar_por_voz_se_ve_en_conocimiento(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    refrescos: list[None] = []
    refresca = ventana.knowledge_widget.refresh

    def cuenta() -> None:
        refrescos.append(None)
        refresca()

    monkeypatch.setattr(ventana.knowledge_widget, "refresh", cuenta)
    sirius.suena("Sirius, ¿qué tal?")
    sirius.deps.local_listening.attend()
    assert refrescos == []

    sirius.modelo.propone = "le gusta el café"
    sirius.suena("Sirius, me encanta el café.")
    sirius.deps.local_listening.attend()

    assert refrescos == [None]


def test_si_el_modelo_falla_en_un_turno_de_voz_se_ve_como_con_lo_escrito(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    sirius.modelo.falla_con = LLMErrorKind.TIMEOUT
    sirius.suena("Sirius, ¿qué tal?")

    (turno,) = sirius.deps.local_listening.attend().turns

    assert ventana.error_label.text() == failed_send_message(
        LLMErrorKind.TIMEOUT, turno.operation_id
    )
    assert not ventana.retry_button.isHidden()


def test_ponte_serio_dicho_por_voz_se_ve_en_el_modo(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    sirius.suena("Sirius, ponte serio.")

    sirius.deps.local_listening.attend()

    assert not ventana.mode_label.isHidden()
    assert ventana.mode_label.text() == "Modo serio"


def test_al_arrancar_la_ventana_de_verdad_trae_su_bucle(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path)
    ventanas: list[QMainWindow] = []

    ventana = _build_post_key_window(sirius.deps, ventanas)
    qtbot.addWidget(ventana)

    assert isinstance(ventana, ValidatedMainWindow)
    bucle = ventana._listening_loop
    assert bucle is not None and bucle.running
    ventana.close()
    assert bucle.wait(5)


def test_al_crear_el_proyecto_la_ventana_que_se_abre_trae_su_bucle(
    qtbot: QtBot, tmp_path: Path
) -> None:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
    )
    ventanas: list[QMainWindow] = []
    proyecto = _build_initial_project_window(deps, ventanas)
    qtbot.addWidget(proyecto)
    proyecto.name_input.setText("Charla")
    proyecto.objective_input.setText("Charlar")

    proyecto._handle_create_clicked()

    (ventana,) = ventanas
    qtbot.addWidget(ventana)
    assert isinstance(ventana, ValidatedMainWindow)
    bucle = ventana._listening_loop
    assert bucle is not None and bucle.running
    ventana.close()
    assert bucle.wait(5)


# --- Model Studio y el oído no se pisan (ronda 2 de Codex sobre la PR #689) ----------
#
# Model Studio tiene su micro y su voz. Con el oído abierto, su voz volvería por el micro
# como un turno, y los dos micros captarían a la vez: mientras está abierto, el oído no
# oye, y al salir vuelve a oír si oía.


def test_en_model_studio_el_oido_no_oye_y_al_salir_vuelve_a_oir(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)

    ventana.open_model_studio()

    assert not sirius.micro.abierto
    assert not sirius.deps.local_listening.listening
    assert ventana.listening_label.isHidden()
    sirius.suena("Sirius, soy la voz de Model Studio")
    assert sirius.deps.local_listening.attend().turns == ()
    assert sirius.modelo.peticiones == []

    ventana.close_model_studio()

    assert sirius.micro.abierto
    assert (ventana.listening_label.text(), ventana.mute_button.text()) == (LISTENING, "Silencio")


def test_en_silencio_al_entrar_en_model_studio_sigue_en_silencio_al_salir(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    ventana.mute_button.click()

    ventana.open_model_studio()
    ventana.close_model_studio()

    assert not sirius.micro.abierto
    assert (ventana.listening_label.text(), ventana.mute_button.text()) == (MUTED, "Escuchar")


def test_si_dejo_de_oir_por_un_fallo_salir_de_model_studio_no_lo_reabre(
    qtbot: QtBot, tmp_path: Path
) -> None:
    # Tras un fallo, lo reabre el botón, como siempre: salir de Model Studio no lo intenta.
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    sirius.detector.falla = RuntimeError("roto")
    sirius.suena("Sirius, hola")
    sirius.deps.local_listening.attend()
    sirius.detector.falla = None
    aviso = ventana.voice_notice_label.text()

    ventana.open_model_studio()
    ventana.close_model_studio()

    assert not sirius.micro.abierto
    assert not sirius.deps.local_listening.listening
    assert ventana.voice_notice_label.text() == aviso


@pytest.mark.parametrize("cerrandose", ["_close_requested", "_closed"])
def test_si_la_ventana_se_esta_cerrando_salir_de_model_studio_no_reabre_el_oido(
    qtbot: QtBot, tmp_path: Path, cerrandose: str
) -> None:
    # Cerrándose, la ventana ya no mira al oído: si oyera, nadie haría de portera.
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    ventana.open_model_studio()
    setattr(ventana, cerrandose, True)

    ventana.close_model_studio()

    assert not sirius.micro.abierto
    assert not sirius.deps.local_listening.listening


class _SintesisQueEspera(FakeTextToSpeech):
    """La voz de Model Studio sintetiza cuando la prueba la deja: acaba después de salir.
    Con ``falla``, acaba sin nada que sonar."""

    def __init__(self, directory: Path) -> None:
        super().__init__(directory)
        self.empezo = threading.Event()
        self.sigue = threading.Event()
        self.falla = False

    def synthesize(self, request: SpeechRequest) -> SynthesizedSpeech | SpeechError:
        self.empezo.set()
        self.sigue.wait(5)
        if self.falla:
            return SpeechError(SpeechErrorKind.TIMEOUT, "tarda")
        return super().synthesize(request)


def _con_la_voz_de_model_studio(
    qtbot: QtBot, tmp_path: Path
) -> tuple[_Sirius, ValidatedMainWindow, _SintesisQueEspera, FakeAudioPlayback]:
    """Sirius con el oído y con una voz de Model Studio de mentira que la prueba gobierna."""
    sirius = _monta(tmp_path)
    directorio = tmp_path / "audio"
    directorio.mkdir()
    sintesis = _SintesisQueEspera(directorio)
    su_altavoz = FakeAudioPlayback()
    voz = StudioVoiceUseCase(
        audio_capture=FakeAudioCapture(directorio),
        speech_to_text=FakeSpeechToText(),
        text_to_speech=sintesis,
        audio_playback=su_altavoz,
        settings=VoiceSettings(voice="onyx"),
    )
    sirius.deps = replace(sirius.deps, studio_voice_use_case=voz)
    return sirius, _ventana(qtbot, sirius), sintesis, su_altavoz


def test_al_salir_de_model_studio_el_oido_espera_a_que_su_voz_calle(
    qtbot: QtBot, tmp_path: Path
) -> None:
    # Ronda 5 de Codex sobre la PR #689 (ADR-244): lo que Model Studio aún sintetizaba al
    # salir suena después, como sin el oído; el oído no lo oye porque espera a que calle.
    sirius, ventana, sintesis, su_altavoz = _con_la_voz_de_model_studio(qtbot, tmp_path)
    ventana.open_model_studio()
    try:
        ventana.studio_page.input.setPlainText("¿por dónde empiezo?")
        ventana.studio_page.send_button.click()
        qtbot.waitUntil(sintesis.empezo.is_set, timeout=5000)

        ventana.close_model_studio()

        assert not sirius.micro.abierto, "con su voz a medias, el oído aún no oye"
        sintesis.sigue.set()
        qtbot.waitUntil(lambda: bool(su_altavoz.played), timeout=5000)
        qtbot.waitUntil(lambda: not ventana._active_voice_workers, timeout=5000)
        assert not sirius.micro.abierto, "mientras suena, tampoco"

        su_altavoz.finish()

        assert sirius.micro.abierto
        assert ventana.listening_label.text() == LISTENING
    finally:
        sintesis.sigue.set()
        ventana._thread_pool.waitForDone(5000)


def _sal_con_su_voz_a_medias(
    qtbot: QtBot, ventana: ValidatedMainWindow, sintesis: _SintesisQueEspera
) -> None:
    """Entra en Model Studio, le pide algo y sale mientras su voz aún lo sintetiza."""
    ventana.open_model_studio()
    ventana.studio_page.input.setPlainText("¿por dónde empiezo?")
    ventana.studio_page.send_button.click()
    qtbot.waitUntil(sintesis.empezo.is_set, timeout=5000)
    ventana.close_model_studio()


def test_con_su_voz_en_marcha_al_salir_ni_el_boton_abre_el_oido_hasta_que_calle(
    qtbot: QtBot, tmp_path: Path
) -> None:
    # Ronda 6 de Codex sobre la PR #689 (ADR-244): el botón no esperaba como el oído, y
    # abría el micro con la voz de Model Studio a punto de sonar. Se ve apagado, y aunque
    # algo lo pulsara, el oído no se abre hasta que su voz calla.
    sirius, ventana, sintesis, su_altavoz = _con_la_voz_de_model_studio(qtbot, tmp_path)
    try:
        _sal_con_su_voz_a_medias(qtbot, ventana, sintesis)

        assert not ventana.mute_button.isEnabled()
        ventana._handle_mute_clicked()
        assert not sirius.micro.abierto, "con su voz a medias, ni el botón abre el oído"

        sintesis.sigue.set()
        qtbot.waitUntil(lambda: bool(su_altavoz.played), timeout=5000)
        qtbot.waitUntil(lambda: not ventana._active_voice_workers, timeout=5000)
        assert not ventana.mute_button.isEnabled()
        ventana._handle_mute_clicked()
        assert not sirius.micro.abierto, "mientras suena, tampoco"

        su_altavoz.finish()

        assert sirius.micro.abierto
        assert ventana.mute_button.isEnabled()
        assert (ventana.listening_label.text(), ventana.mute_button.text()) == (
            LISTENING,
            "Silencio",
        )
    finally:
        sintesis.sigue.set()
        ventana._thread_pool.waitForDone(5000)


def test_en_silencio_y_con_su_voz_en_marcha_al_salir_el_boton_vuelve_cuando_calla(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius, ventana, sintesis, su_altavoz = _con_la_voz_de_model_studio(qtbot, tmp_path)
    ventana.mute_button.click()
    try:
        _sal_con_su_voz_a_medias(qtbot, ventana, sintesis)
        assert not ventana.mute_button.isEnabled()

        sintesis.sigue.set()
        qtbot.waitUntil(lambda: bool(su_altavoz.played), timeout=5000)
        qtbot.waitUntil(lambda: not ventana._active_voice_workers, timeout=5000)
        su_altavoz.finish()

        assert ventana.mute_button.isEnabled()
        assert not sirius.micro.abierto
        assert (ventana.listening_label.text(), ventana.mute_button.text()) == (
            MUTED,
            "Escuchar",
        )
    finally:
        sintesis.sigue.set()
        ventana._thread_pool.waitForDone(5000)


def test_lo_que_pida_escuchar_mientras_su_voz_sigue_en_marcha_se_hace_cuando_calla(
    qtbot: QtBot, tmp_path: Path
) -> None:
    # Pedido en silencio con su voz a medias, no se pierde: se escucha cuando calla.
    sirius, ventana, sintesis, su_altavoz = _con_la_voz_de_model_studio(qtbot, tmp_path)
    ventana.mute_button.click()
    try:
        _sal_con_su_voz_a_medias(qtbot, ventana, sintesis)

        ventana._handle_mute_clicked()

        assert not sirius.micro.abierto
        sintesis.sigue.set()
        qtbot.waitUntil(lambda: bool(su_altavoz.played), timeout=5000)
        qtbot.waitUntil(lambda: not ventana._active_voice_workers, timeout=5000)
        assert not sirius.micro.abierto
        su_altavoz.finish()

        assert sirius.micro.abierto
        assert not sirius.deps.local_listening.muted
        assert ventana.listening_label.text() == LISTENING
    finally:
        sintesis.sigue.set()
        ventana._thread_pool.waitForDone(5000)


def test_si_lo_que_sintetizaba_al_salir_no_llega_a_sonar_el_oido_vuelve_al_acabar(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius, ventana, sintesis, su_altavoz = _con_la_voz_de_model_studio(qtbot, tmp_path)
    sintesis.falla = True
    ventana.open_model_studio()
    try:
        ventana.studio_page.input.setPlainText("¿por dónde empiezo?")
        ventana.studio_page.send_button.click()
        qtbot.waitUntil(sintesis.empezo.is_set, timeout=5000)
        ventana.close_model_studio()
        assert not sirius.micro.abierto

        sintesis.sigue.set()

        qtbot.waitUntil(lambda: sirius.micro.abierto, timeout=5000)
        assert su_altavoz.played == []
    finally:
        sintesis.sigue.set()
        ventana._thread_pool.waitForDone(5000)


def test_dentro_de_model_studio_que_su_voz_acabe_no_abre_el_oido(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius, ventana, sintesis, su_altavoz = _con_la_voz_de_model_studio(qtbot, tmp_path)
    sintesis.sigue.set()
    ventana.open_model_studio()
    try:
        ventana.studio_page.input.setPlainText("¿por dónde empiezo?")
        ventana.studio_page.send_button.click()
        qtbot.waitUntil(lambda: bool(su_altavoz.played), timeout=5000)
        qtbot.waitUntil(lambda: not ventana._active_voice_workers, timeout=5000)

        su_altavoz.finish()

        assert not sirius.micro.abierto
        assert not sirius.deps.local_listening.listening
    finally:
        ventana._thread_pool.waitForDone(5000)


# --- El juez no frena la voz (ADR-252) -----------------------------------------------------


def test_el_juez_no_puntua_mientras_dura_la_charla_de_voz(qtbot: QtBot, tmp_path: Path) -> None:
    juez = _JuezQueCuenta()
    sirius = _monta(tmp_path, juez=juez)
    ventana = _ventana(qtbot, sirius)
    reloj = [1000.0]
    ventana._monotonic = lambda: reloj[0]

    # El primer turno tarda en contestar 50 s: la espera cuenta desde que acaba.
    sirius.modelo.antes = lambda: reloj.__setitem__(0, reloj[0] + 50)
    sirius.suena("Sirius, ¿qué tal?")
    sirius.deps.local_listening.attend()
    sirius.modelo.antes = None

    # Acabado el turno de voz, el juez no arranca: espera a que pase la charla.
    assert _mensajes(ventana)[-1] == ("Sirius", "Respuesta 1.")
    assert not ventana.judge_in_progress
    assert ventana._judge_timer.isActive()
    assert ventana._judge_timer.interval() >= (VOICE_QUIET_SECONDS - 1) * 1000
    qtbot.wait(100)
    assert juez.puntuadas == []

    # Otro turno antes de que pase: vuelve a esperar, ahora desde este.
    reloj[0] += 30
    sirius.suena("Sirius, ¿sigues ahí?")
    sirius.deps.local_listening.attend()
    ventana._judge_timer.timeout.emit()
    qtbot.wait(100)
    assert juez.puntuadas == []

    # Pasado el rato sin hablarle, puntúa lo que quedó sin nota.
    reloj[0] += VOICE_QUIET_SECONDS + 1
    ventana._judge_timer.timeout.emit()
    qtbot.waitUntil(lambda: len(juez.puntuadas) == 2, timeout=5000)
    assert juez.puntuadas == ["Respuesta 1.", "Respuesta 2."]


def test_sin_charla_de_voz_el_juez_puntua_al_acabar_lo_escrito(
    qtbot: QtBot, tmp_path: Path
) -> None:
    juez = _JuezQueCuenta()
    sirius = _monta(tmp_path, juez=juez)
    ventana = _ventana(qtbot, sirius)

    ventana.message_input.setText("Hola, Sirius.")
    ventana.send_button.click()

    qtbot.waitUntil(lambda: juez.puntuadas == ["Respuesta 1."], timeout=5000)
    assert not ventana._judge_timer.isActive()


def test_un_turno_de_voz_que_no_va_tambien_hace_esperar_al_juez(
    qtbot: QtBot, tmp_path: Path
) -> None:
    juez = _JuezQueCuenta()
    sirius = _monta(tmp_path, juez=juez)
    ventana = _ventana(qtbot, sirius)
    ventana._monotonic = lambda: 1000.0
    escribiendo, sigue = threading.Event(), threading.Event()

    def espera() -> None:
        escribiendo.set()
        sigue.wait(5)

    sirius.modelo.antes = espera
    ventana.message_input.setText("Hola por escrito.")
    ventana.send_button.click()
    qtbot.waitUntil(escribiendo.is_set, timeout=5000)
    sirius.modelo.antes = None
    sirius.suena("Sirius, ¿me oyes?")

    # Le hablan mientras escribe: ese turno no va, pero la charla de voz ha empezado.
    try:
        sirius.deps.local_listening.attend()
    finally:
        sigue.set()
    qtbot.waitUntil(ventana.send_button.isEnabled, timeout=5000)

    assert ventana._judge_timer.isActive()
    qtbot.wait(100)
    assert juez.puntuadas == []


def test_el_aviso_de_la_charla_de_fuera_dice_donde_elegir_un_modelo_de_aqui(
    qtbot: QtBot, tmp_path: Path
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)

    # La pestaña y el botón que nombra son los de verdad (ADR-252).
    pestanas = [ventana.tabs.tabText(indice) for indice in range(ventana.tabs.count())]
    assert "Configuración" in pestanas
    assert f"Configuración, «{ventana.blind_test_button.text()}»" in CHAT_LEAVES


class _ModeloDeFuera:
    """Un modelo de fuera de este ordenador, como el de OpenAI."""

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        del request
        yield LLMCompleted(text="De fuera.", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _EligeACiegas:
    """La hoja de la prueba a ciegas, donde él acaba eligiendo ``ELEGIDO``."""

    ELEGIDO = "gemma3:4b"

    def __init__(self, use_case: BlindTestUseCase, **kwargs: object) -> None:
        del kwargs
        self._use_case = use_case

    def exec(self) -> int:
        self._use_case.choose(self.ELEGIDO)
        return 0


def test_tras_elegir_a_ciegas_un_modelo_de_aqui_oye_y_guardar_no_vuelve_a_openai(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-253: tras elegirlo, la ventana seguía diciendo que la charla iba fuera, no oía, y
    «Guardar configuración» la devolvía a OpenAI sin decir nada."""
    sirius = _monta(tmp_path)
    sirius.deps.send_message_use_case.set_llm_provider(_ModeloDeFuera())
    ventana = _ventana(qtbot, sirius)
    assert ventana.voice_notice_label.text() == CHAT_LEAVES
    monkeypatch.setattr("sirius.presentation.main_window.BlindTestDialog", _EligeACiegas)

    ventana.blind_test_button.click()

    assert ventana.voice_notice_label.text() == ""
    assert sirius.deps.local_listening.listening
    assert ventana.listening_label.text() == LISTENING
    ventana._show_information = lambda title, text: None
    ventana.name_input.setText("Andy")
    guardar = next(
        boton
        for boton in ventana.findChildren(QPushButton)
        if boton.text() == "Guardar configuración"
    )
    guardar.click()
    assert load_settings()["llm_provider"] == "ollama"
    assert load_settings()["ollama_chat_model"] == _EligeACiegas.ELEGIDO


def test_callado_con_el_boton_sigue_callado_tras_elegir_a_ciegas(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    ventana.mute_button.click()
    assert sirius.deps.local_listening.muted
    monkeypatch.setattr("sirius.presentation.main_window.BlindTestDialog", _EligeACiegas)

    ventana.blind_test_button.click()

    assert sirius.deps.local_listening.muted
    assert not sirius.deps.local_listening.listening
    assert ventana.listening_label.text() == MUTED


class _Aplicacion(QObject):
    """Hace de la QApplication de Sirius: solo su aviso de que sale."""

    aboutToQuit = Signal()


def test_al_salir_de_sirius_suelta_la_voz_y_no_al_cerrar_una_ventana(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    (altavoz,) = sirius.altavoces
    aplicacion = _Aplicacion()
    # Salir de verdad dejaría sin red a las demás pruebas: se apunta, con la voz como estaba.
    colgado: list[tuple[bool, bool]] = []

    def cuelga(*, final: bool = False) -> int:
        colgado.append((final, altavoz.cerrado))
        return 0

    monkeypatch.setattr("sirius.main.hang_up_all", cuelga)
    _release_on_quit(aplicacion, sirius.deps)  # type: ignore[arg-type]

    # Tras acabar un proyecto se cierra la ventana y se abre otra: sigue con su voz.
    ventana.close()
    assert not altavoz.cerrado

    # Al salir se suelta, y con ella la cancelación de eco (ADR-252). Antes se cuelga lo
    # que siga pidiendo por la red, y lo que se abra después, para que soltar la voz no
    # espere a una respuesta en vuelo (ADR-255).
    aplicacion.aboutToQuit.emit()
    assert altavoz.cerrado
    assert colgado == [(True, False)]


def test_las_ventanas_cuelgan_la_red_con_el_registro_que_les_da_main(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Ronda 4 de Codex sobre la #698: la presentación no importa la red de la
    infraestructura; el punto de composición da a cada ventana el registro del proceso, y
    ellas solo lo invocan al cerrarse."""
    sirius = _monta(tmp_path)
    ventana = _ventana(qtbot, sirius)
    bienvenida = _build_onboarding_window(sirius.deps, [])
    qtbot.addWidget(bienvenida)

    assert ventana._connections is connection_registry()
    assert bienvenida._connections is connection_registry()
