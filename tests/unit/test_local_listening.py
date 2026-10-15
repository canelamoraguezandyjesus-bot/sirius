"""El oído del robot, del micro a la charla (ADR-242), con un doble en cada pieza.

Las pruebas de aceptación (``tests/acceptance/test_robot_0_3_voz.py``) miran lo que ve
el propietario; estas miran los bordes del servicio que allí no salen: lo que guarda de
antes de la voz, un turno sin palabras, lo que pasa si falta algo, si la charla falla o
si se para a medias, y que el diario no se quede con nada de lo oído.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import cast

import pytest

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.ollama_chat import OllamaChatProvider
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
from sirius.adapters.llm.unconfigured import UnconfiguredLLMProvider
from sirius.application.local_listening import (
    CHAT_LEAVES,
    Attended,
    HeardTurn,
    LocalListening,
)
from sirius.application.send_message import ChatLeavesThisComputer, SendMessageResult
from sirius.domain.conversation import MessageStatus
from sirius.ports.llm import LLMErrorKind, runs_on_this_computer
from sirius.ports.local_voice import ListeningEngines, TurnSignal, VoiceUnavailable

FIN = "fin"


def voz(texto: str) -> str:
    return f"voz:{texto}"


class _Micro:
    """Un micro con lo que va a sonar ya escrito: ``voz:...`` es voz, vacío es silencio."""

    def __init__(self) -> None:
        self.pendientes: list[str] = []
        self.abierto = False
        self.aperturas = 0
        self.falla_al_abrir: VoiceUnavailable | None = None
        self.falla_al_cerrar: Exception | None = None

    def open(self) -> None:
        if self.falla_al_abrir is not None:
            raise self.falla_al_abrir
        self.abierto = True
        self.aperturas += 1

    def close(self) -> None:
        if self.falla_al_cerrar is not None:
            raise self.falla_al_cerrar
        self.abierto = False

    def read(self) -> str | None:
        assert self.abierto, "se ha leído el micro cerrado"
        return self.pendientes.pop(0) if self.pendientes else None


class _Detector:
    def __init__(self) -> None:
        self.vistos: list[str] = []
        self.reinicios = 0
        self.falla_al_reiniciar: Exception | None = None

    def listen(self, chunk: str) -> TurnSignal:
        self.vistos.append(chunk)
        if chunk == FIN:
            return TurnSignal.ENDED
        return TurnSignal.VOICE if chunk.startswith("voz:") else TurnSignal.QUIET

    def reset(self) -> None:
        if self.falla_al_reiniciar is not None:
            raise self.falla_al_reiniciar
        self.reinicios += 1


class _DetectorQueRecuerda(_Detector):
    """Como Silero: oída la voz, sigue diciendo que hay voz hasta el fin del turno."""

    def __init__(self) -> None:
        super().__init__()
        self.hablando = False

    def listen(self, chunk: str) -> TurnSignal:
        self.vistos.append(chunk)
        if chunk == FIN:
            self.hablando = False
            return TurnSignal.ENDED
        if chunk.startswith("voz:"):
            self.hablando = True
        return TurnSignal.VOICE if self.hablando else TurnSignal.QUIET

    def reset(self) -> None:
        super().reset()
        self.hablando = False


class _Transcriptor:
    def __init__(self) -> None:
        self.turnos: list[list[str]] = []
        self.devuelve: str | None = None
        #: Lo que pasa mientras transcribe, que tarda: por ejemplo, que cambie la charla.
        self.al_transcribir: Callable[[], None] | None = None

    def transcribe(self, chunks: Sequence[str]) -> str:
        self.turnos.append(list(chunks))
        if self.al_transcribir is not None:
            self.al_transcribir()
        if self.devuelve is not None:
            return self.devuelve
        return " ".join(c.removeprefix("voz:") for c in chunks if c.startswith("voz:"))


class _Charla:
    def __init__(self) -> None:
        #: Un modelo de este ordenador, como Ollama.
        self.llm_provider: object = SimpleNamespace(runs_on_this_computer=True)
        self.mensajes: list[str] = []
        self.falla: Exception | None = None
        self.desenlace = MessageStatus.COMPLETED
        self.por_que: LLMErrorKind | None = None
        #: Lo que el modelo propone recordar al contestar, como Ollama tras el delimitador.
        self.propone: str | None = None

    def send_message(
        self, user_text: str, *, only_on_this_computer: bool = False
    ) -> SendMessageResult:
        # Como la de verdad: comprueba el mismo modelo con el que enviaría.
        if only_on_this_computer and not runs_on_this_computer(self.llm_provider):
            raise ChatLeavesThisComputer("de fuera")
        self.mensajes.append(user_text)
        if self.falla is not None:
            falla, self.falla = self.falla, None
            raise falla
        respuesta = SimpleNamespace(
            outcome=self.desenlace,
            sirius_message=SimpleNamespace(id=7, content=f"R: {user_text}"),
            error_kind=self.por_que,
            memory_suggestion=self.propone,
        )
        return cast("SendMessageResult", respuesta)


class _Propuestas:
    """Donde quedan pendientes las propuestas de memoria, como el caso de uso de verdad."""

    def __init__(self) -> None:
        self.hechas: list[tuple[str, int | None]] = []
        self.falla: Exception | None = None

    def propose(self, content: str, *, message_id: int | None = None) -> object:
        if self.falla is not None:
            raise self.falla
        self.hechas.append((content, message_id))
        return object()


class _Instalacion:
    def __init__(self) -> None:
        self.faltan: tuple[str, ...] = ()

    @property
    def install_command(self) -> str:
        return "la orden de instalar"

    def missing(self) -> tuple[str, ...]:
        return self.faltan


class _Oido:
    """Todo junto, con el servicio montado como en producción."""

    def __init__(self, *, antes: int = 2, detector: _Detector | None = None) -> None:
        self.micro = _Micro()
        self.detector = detector or _Detector()
        self.transcriptor = _Transcriptor()
        self.charla = _Charla()
        self.propuestas = _Propuestas()
        self.instalacion = _Instalacion()
        self.cargas = 0
        self.falla_al_cargar: VoiceUnavailable | None = None
        self.servicio: LocalListening[str] = LocalListening(
            chat=self.charla,
            installation=self.instalacion,
            load_engines=self._carga,
            memory_suggestions=self.propuestas,
            pre_roll=antes,
        )

    def _carga(self) -> ListeningEngines[str]:
        self.cargas += 1
        if self.falla_al_cargar is not None:
            raise self.falla_al_cargar
        return ListeningEngines(self.micro, self.detector, self.transcriptor)

    def suena(self, *trozos: str) -> Attended:
        self.micro.pendientes.extend(trozos)
        return self.servicio.attend()


def test_un_turno_va_a_la_charla_con_lo_que_sono_justo_antes_de_la_voz() -> None:
    oido = _Oido(antes=2)
    assert oido.servicio.start() == ""

    atendido = oido.suena("", "a", "b", voz("Hola"), "", FIN)

    assert atendido == Attended(turns=(HeardTurn("Hola", True, "R: Hola"),))
    # Los dos trozos de antes de la voz, para no cortarle la primera sílaba; no más.
    assert oido.transcriptor.turnos == [["a", "b", voz("Hola"), "", FIN]]
    assert oido.charla.mensajes == ["Hola"]


def test_cada_trozo_se_le_ensena_al_detector_una_vez_y_en_orden() -> None:
    oido = _Oido()
    oido.servicio.start()

    oido.suena("", voz("Uno"), "", FIN, "", voz("Dos"), FIN)

    assert oido.detector.vistos == ["", voz("Uno"), "", FIN, "", voz("Dos"), FIN]


def test_sin_fin_de_turno_espera_y_lo_cierra_cuando_el_detector_lo_dice() -> None:
    oido = _Oido()
    oido.servicio.start()

    assert oido.suena(voz("Estaba pensando"), "", "") == Attended()
    assert oido.transcriptor.turnos == []
    assert oido.charla.mensajes == []

    atendido = oido.suena("", FIN)

    assert [t.heard for t in atendido.turns] == ["Estaba pensando"]
    assert oido.transcriptor.turnos == [[voz("Estaba pensando"), "", "", "", FIN]]


def test_un_fin_de_turno_sin_voz_delante_ni_empieza_turno_ni_transcribe() -> None:
    # Whisper se inventa frases sobre el silencio: sin voz no hay turno que transcribir.
    oido = _Oido(antes=1)
    oido.servicio.start()

    assert oido.suena("", FIN, "") == Attended()
    assert oido.transcriptor.turnos == []
    assert oido.charla.mensajes == []

    atendido = oido.suena(voz("Hola"), FIN)

    assert [t.heard for t in atendido.turns] == ["Hola"]
    # El turno empezó con la voz y lo de justo antes, no con aquel fin suelto.
    assert oido.transcriptor.turnos == [["", voz("Hola"), FIN]]


def test_dos_turnos_en_una_sola_atencion_se_devuelven_en_orden() -> None:
    oido = _Oido()
    oido.servicio.start()

    atendido = oido.suena(voz("Uno"), FIN, voz("Dos"), FIN)

    assert [t.heard for t in atendido.turns] == ["Uno", "Dos"]
    assert oido.charla.mensajes == ["Uno", "Dos"]


def test_un_turno_sin_palabras_no_va_a_la_charla() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.transcriptor.devuelve = "   "

    assert oido.suena(voz("ruido"), FIN) == Attended()
    assert oido.charla.mensajes == []

    oido.transcriptor.devuelve = None
    assert [t.heard for t in oido.suena(voz("Hola"), FIN).turns] == ["Hola"]


def test_si_falta_el_modelo_avisa_con_la_orden_y_no_carga_ni_abre_nada() -> None:
    oido = _Oido()
    oido.instalacion.faltan = ("el modelo de oír (faster-whisper small)",)

    aviso = oido.servicio.start()

    assert "el modelo de oír (faster-whisper small)" in aviso
    assert "la orden de instalar" in aviso
    assert oido.cargas == 0
    assert not oido.micro.abierto
    assert not oido.servicio.listening
    oido.micro.pendientes.append(voz("Hola"))
    assert oido.servicio.attend() == Attended(notice=aviso), "sin escuchar no se lee el micro"
    assert oido.micro.pendientes == [voz("Hola")]


def test_si_faltan_varias_cosas_las_dice_todas() -> None:
    oido = _Oido()
    oido.instalacion.faltan = ("el modelo de oír", "la voz", "el detector")

    assert "me falta instalar el modelo de oír, la voz y el detector en este ordenador" in (
        oido.servicio.start()
    )


def test_si_el_oido_no_carga_aconseja_la_orden_diciendo_lo_que_hace() -> None:
    # Ronda 8 de Codex sobre la PR #687: si la orden lo arreglaría no se adivina (una
    # versión vieja sí la arregla; una DLL que no carga, no). Se aconseja diciendo lo que
    # hace siempre: pone o pone al día lo que falte y, si es otra cosa, dice cuál.
    oido = _Oido()
    oido.falla_al_cargar = VoiceUnavailable("pipecat.audio.vad.silero no carga (DLL)")

    aviso = oido.servicio.start()

    assert aviso.startswith("No puedo oírte: pipecat.audio.vad.silero no carga (DLL).")
    assert "la orden de instalar" in aviso
    assert "Instala o pone al día lo que falte de la voz" in aviso
    assert "si el problema es otro, te dice cuál" in aviso
    assert not oido.servicio.listening


# --- Lo oído solo va a una charla de este ordenador (PA-R03-08) --------------------
#
# Ronda 9 de Codex sobre la PR #687: Configuración sigue ofreciendo OpenAI, y lo dicho por
# voz habría salido con la charla. La voz solo entrega lo que oye a un modelo de aquí.


def test_solo_los_modelos_de_este_ordenador_dicen_que_se_quedan_aqui() -> None:
    assert runs_on_this_computer(OllamaChatProvider)
    assert runs_on_this_computer(FakeLLMProvider)
    assert runs_on_this_computer(UnconfiguredLLMProvider)
    assert not runs_on_this_computer(OpenAIResponsesProvider)
    assert not runs_on_this_computer(object()), "el que no lo dice, cuenta como de fuera"


def test_con_la_charla_en_un_modelo_de_fuera_no_oye_ni_carga_ni_abre_nada() -> None:
    oido = _Oido()
    oido.charla.llm_provider = SimpleNamespace()

    aviso = oido.servicio.start()

    assert aviso == CHAT_LEAVES
    assert "la orden de instalar" not in aviso, "instalar no lo arregla"
    assert oido.cargas == 0
    assert not oido.micro.abierto
    assert not oido.servicio.listening


def test_si_la_charla_se_va_a_un_modelo_de_fuera_mientras_oye_el_turno_no_sale() -> None:
    oido = _Oido()
    assert oido.servicio.start() == ""
    oido.charla.llm_provider = SimpleNamespace()

    atendido = oido.suena(voz("Mi clave es 1234"), FIN, voz("y otra cosa"))

    assert atendido == Attended(notice=CHAT_LEAVES)
    assert oido.charla.mensajes == []
    assert oido.transcriptor.turnos == [], "ni se transcribe"
    assert not oido.servicio.listening
    assert not oido.micro.abierto


def test_si_la_charla_se_va_fuera_mientras_transcribe_el_turno_no_sale() -> None:
    # Ronda 10 de Codex sobre la PR #687: la comprobación de antes de transcribir ya había
    # pasado, y la charla cambió de modelo mientras faster-whisper transcribía.
    oido = _Oido()
    assert oido.servicio.start() == ""

    def se_va_fuera() -> None:
        oido.charla.llm_provider = SimpleNamespace()

    oido.transcriptor.al_transcribir = se_va_fuera

    atendido = oido.suena(voz("Mi clave es 1234"), FIN)

    assert atendido == Attended(notice=CHAT_LEAVES)
    assert oido.charla.mensajes == []
    assert not oido.servicio.listening
    assert not oido.micro.abierto


def test_sin_microfono_avisa_sin_la_orden_que_no_lo_arregla() -> None:
    oido = _Oido()
    oido.micro.falla_al_abrir = VoiceUnavailable("no hay micrófono")

    aviso = oido.servicio.start()

    assert aviso == "No puedo oírte: no hay micrófono."
    assert not oido.servicio.listening


def test_arrancar_dos_veces_no_vuelve_a_cargar_ni_a_abrir() -> None:
    oido = _Oido()

    assert oido.servicio.start() == ""
    assert oido.servicio.start() == ""

    assert oido.cargas == 1
    assert oido.micro.aperturas == 1


def test_un_aviso_se_quita_cuando_ya_puede_oir() -> None:
    oido = _Oido()
    oido.instalacion.faltan = ("el modelo de oír",)
    assert oido.servicio.start()

    oido.instalacion.faltan = ()

    assert oido.servicio.start() == ""
    assert oido.servicio.attend() == Attended()


def test_parar_cierra_el_micro_y_olvida_el_turno_a_medias() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.suena(voz("Lo que no acabó"), "")

    oido.servicio.stop()

    assert not oido.micro.abierto
    assert oido.servicio.attend() == Attended()
    oido.servicio.start()
    atendido = oido.suena(voz("Hola"), FIN)
    assert [t.heard for t in atendido.turns] == ["Hola"]
    assert oido.transcriptor.turnos == [[voz("Hola"), FIN]]


def test_parar_a_media_frase_tambien_reinicia_el_detector() -> None:
    # Ronda 1 de Codex sobre la PR #687: sin reiniciarlo, el detector seguía en el turno
    # viejo y el primer silencio al volver abría un turno sin palabras.
    detector = _DetectorQueRecuerda()
    oido = _Oido(detector=detector)
    oido.servicio.start()
    oido.suena(voz("Lo que no acabó"), "")

    oido.servicio.stop()
    oido.servicio.start()

    assert detector.reinicios == 1
    assert oido.suena("", "", FIN) == Attended()
    assert oido.transcriptor.turnos == []


def test_si_el_detector_no_se_reinicia_al_parar_se_reintenta_al_volver() -> None:
    # Rondas 2 y 3 de Codex sobre la PR #687: un fallo al parar no puede dejar el servicio
    # diciendo una cosa y el hardware otra, ni soltar el micro que quizá sigue abierto.
    oido = _Oido()
    oido.servicio.start()
    oido.suena(voz("A medias"), "")
    oido.detector.falla_al_reiniciar = RuntimeError("sin memoria para Silero")

    oido.servicio.stop()

    assert not oido.servicio.listening
    assert not oido.micro.abierto
    assert oido.servicio.attend() == Attended(), "parado no lee el micro"
    # Al volver lo intenta otra vez; si sigue sin poder, lo dice y no abre el micro.
    aviso = oido.servicio.start()
    assert "el detector de voz no se ha podido reiniciar (sin memoria para Silero)" in aviso
    assert "la orden de instalar" not in aviso, "reinstalar no lo arregla"
    assert not oido.micro.abierto
    assert oido.servicio.attend() == Attended(notice=aviso)
    # Cuando puede, oye con las mismas piezas, sin volver a cargarlas.
    oido.detector.falla_al_reiniciar = None
    assert oido.servicio.start() == ""
    assert oido.detector.reinicios == 1
    assert oido.cargas == 1
    assert oido.micro.aperturas == 2
    assert [t.heard for t in oido.suena(voz("Hola"), FIN).turns] == ["Hola"]


def test_si_el_micro_falla_al_cerrar_el_servicio_queda_parado_y_conserva_sus_piezas() -> None:
    # Un micro que no cumple su contrato y falla al cerrar: el servicio ya está parado,
    # el detector se reinicia igual y no se suelta nada.
    oido = _Oido()
    oido.servicio.start()
    oido.micro.falla_al_cerrar = OSError("PortAudio no responde")

    with pytest.raises(OSError, match="PortAudio"):
        oido.servicio.stop()

    assert not oido.servicio.listening
    assert oido.detector.reinicios == 1
    oido.micro.falla_al_cerrar = None
    assert oido.servicio.start() == ""
    assert oido.cargas == 1, "las mismas piezas: el micro que quizá sigue abierto no se suelta"


def test_si_la_charla_falla_el_turno_no_se_queda_a_medias() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.falla = RuntimeError("el modelo no contesta")

    with pytest.raises(RuntimeError, match="el modelo no contesta"):
        oido.suena(voz("Primero"), FIN)

    atendido = oido.suena(voz("Segundo"), FIN)
    assert [t.heard for t in atendido.turns] == ["Segundo"]
    assert oido.transcriptor.turnos[-1] == [voz("Segundo"), FIN]


def test_si_la_charla_no_acaba_bien_el_turno_lo_dice() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.desenlace = MessageStatus.FAILED

    (turno,) = oido.suena(voz("Hola"), FIN).turns

    assert turno.heard == "Hola"
    assert not turno.answered


def test_si_la_charla_no_acaba_bien_el_turno_dice_por_que() -> None:
    # Ronda 12 de Codex sobre la PR #687: lo que devuelve la charla no se queda por el
    # camino; quien enseña el turno dice lo mismo que la ventana para ese fallo.
    oido = _Oido()
    oido.servicio.start()
    oido.charla.desenlace = MessageStatus.FAILED
    oido.charla.por_que = LLMErrorKind.CONNECTION
    oido.charla.propone = "Le gusta el café"

    (turno,) = oido.suena(voz("Hola"), FIN).turns

    assert not turno.answered
    assert turno.error_kind is LLMErrorKind.CONNECTION
    assert turno.proposed is None
    assert oido.propuestas.hechas == [], "un turno que no acabó bien no propone nada"


def test_lo_que_el_modelo_propone_recordar_queda_pendiente_como_en_la_ventana() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.propone = "Le gusta el café"

    (turno,) = oido.suena(voz("Me encanta el café"), FIN).turns

    assert oido.propuestas.hechas == [("Le gusta el café", 7)]
    assert turno.proposed == "Le gusta el café"
    assert turno.answered


def test_sin_propuesta_no_propone_nada() -> None:
    oido = _Oido()
    oido.servicio.start()

    (turno,) = oido.suena(voz("Hola"), FIN).turns

    assert oido.propuestas.hechas == []
    assert turno.proposed is None


def test_si_proponer_falla_el_turno_contestado_sigue_y_el_diario_no_guarda_lo_propuesto(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logging.getLogger("sirius.application.local_listening"), "disabled", False)
    oido = _Oido()
    oido.servicio.start()
    oido.charla.propone = "La clave es Zarzamora"
    oido.propuestas.falla = RuntimeError("la base está cerrada")

    with caplog.at_level(logging.DEBUG):
        (turno,) = oido.suena(voz("Hola"), FIN).turns

    assert turno.answered
    assert turno.reply == "R: Hola"
    assert turno.proposed is None
    assert "No se pudo proponer lo que recordar (RuntimeError)" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()


def test_el_diario_no_se_queda_con_nada_de_lo_oido(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Una migración anterior en el mismo proceso (Alembic, `fileConfig`) apaga los
    # registradores que ya existían: se enciende el del oído para poder leerlo.
    monkeypatch.setattr(logging.getLogger("sirius.application.local_listening"), "disabled", False)
    oido = _Oido()
    oido.servicio.start()

    with caplog.at_level(logging.DEBUG):
        oido.suena(voz("La clave es Zarzamora"), FIN)

    assert "Turno de voz entregado a la charla" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()
