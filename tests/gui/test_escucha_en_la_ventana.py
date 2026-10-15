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
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMainWindow
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.listening_loop import ListeningLoop
from sirius.application.memory_commands import FORGET_ABOUT_STORED
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.local_voice import LocalVoiceSettings
from sirius.infrastructure.local_voice_installation import (
    INSTALL_COMMAND,
    LISTENING_MODEL_FILES,
    LocalVoiceInstallation,
    speaking_voice_files,
)
from sirius.infrastructure.paths import resolve_paths
from sirius.main import (
    _build_initial_project_window,
    _build_listening_main_window,
    _build_main_window,
    _build_post_key_window,
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
from sirius.presentation.error_messages import failed_send_message
from sirius.presentation.main_window import LISTENING, MUTED, VOICE_BUSY
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

    def health_check(self) -> bool:
        return True

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

    def play(self, sound: str) -> None:
        del sound

    def stop(self) -> None:
        pass


@dataclass
class _Sirius:
    deps: ConversationDependencies
    modelo: _Modelo
    micro: _Micro = field(default_factory=_Micro)
    detector: _Detector = field(default_factory=_Detector)
    transcriptor: _Transcriptor = field(default_factory=_Transcriptor)

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


def _monta(tmp_path: Path, *, con_la_voz: bool = True) -> _Sirius:
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

    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
        listening_engines=oido,
        speaking_engines=lambda modelo_de_voz: SpeakingEngines(_Voz(), _Altavoz()),
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
