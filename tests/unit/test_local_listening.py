"""El oído y la voz del robot, del micro a la charla y de ella al altavoz (ADR-242, ADR-243,
ADR-244), con un doble en cada pieza.

Las pruebas de aceptación (``tests/acceptance/test_robot_0_3_voz.py``) miran lo que ve
el propietario; estas miran los bordes del servicio que allí no salen: lo que guarda de
antes de la voz, un turno sin palabras, lo que pasa si falta algo, si la charla falla o
si se para a medias, y que el diario no se quede con nada de lo oído; y, al hablar, el
orden de lo que se dice y del micro, lo que pasa si la voz o el altavoz fallan y lo que
tarda en sonar.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import cast

import pytest

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.ollama_chat import OllamaChatProvider
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
from sirius.adapters.llm.unconfigured import UnconfiguredLLMProvider
from sirius.application.addressing import Addressing
from sirius.application.local_listening import (
    CHAT_LEAVES,
    LOOK_BEFORE_SECONDS,
    Addressee,
    Attended,
    HeardTurn,
    LocalListening,
    VoicePhase,
    gesture_mark,
    read_meanwhile,
)
from sirius.application.send_message import ChatLeavesThisComputer, SendMessageResult
from sirius.application.speech_cutter import SpeechCutter
from sirius.domain.conversation import MessageStatus
from sirius.domain.gestures import Gesture
from sirius.ports.llm import LLMErrorKind, runs_on_this_computer
from sirius.ports.local_voice import (
    Captured,
    Cleaned,
    ListeningEngines,
    SpeakingEngines,
    TurnSignal,
    VoiceUnavailable,
)

FIN = "fin"
#: Lo que capta el micro con su propia voz sonando: su eco.
ECO = "eco"


def voz(texto: str) -> str:
    return f"voz:{texto}"


def eco(trozo: str = "") -> str:
    """Lo que capta el micro mientras suena su voz: el eco, y encima ``trozo`` si lo hay."""
    return f"{ECO}+{trozo}" if trozo else ECO


class _Micro:
    """Un micro con lo que va a sonar ya escrito: ``voz:...`` es voz, vacío es silencio.

    Como el de verdad, lo que suena con él cerrado se pierde, y al cerrarlo se tira lo
    que nadie ha leído. Apunta en ``eventos`` cuándo se abre y se cierra. Lo que capta se
    lee en el acto; con ``reloj``, apunta cuándo lo captó y dice cuánto esperó a que lo
    leyeran, como el de verdad mientras el oído transcribe o contesta. Con ``al_leer``,
    cada trozo llega cuando se lee: ahí pasa el tiempo que dura el audio.
    """

    def __init__(self, eventos: list[str] | None = None) -> None:
        self.eventos = eventos if eventos is not None else []
        self.pendientes: list[str] = []
        self.perdidos: list[str] = []
        self.abierto = False
        self.aperturas = 0
        self.falla_al_abrir: VoiceUnavailable | None = None
        self.falla_al_cerrar: Exception | None = None
        self.reloj: Callable[[], float] | None = None
        #: Cuándo captó cada trozo de ``pendientes``, si tiene reloj.
        self._captados_en: list[float] = []
        #: Lo que pasa mientras se abre, ya abierto: por ejemplo, que capte algo.
        self.al_abrir: Callable[[], None] | None = None
        #: Lo que pasa justo antes de dar cada trozo: por ejemplo, que dure lo que dura.
        self.al_leer: Callable[[str], None] | None = None

    def capta(self, *trozos: str) -> None:
        if not self.abierto:
            self.perdidos.extend(trozos)
            return
        self.pendientes.extend(trozos)
        if self.reloj is not None:
            self._captados_en.extend([self.reloj()] * len(trozos))

    def open(self) -> None:
        if self.falla_al_abrir is not None:
            raise self.falla_al_abrir
        self.abierto = True
        self.aperturas += 1
        self.eventos.append("abre")
        if self.al_abrir is not None:
            self.al_abrir()

    def close(self) -> None:
        if self.falla_al_cerrar is not None:
            raise self.falla_al_cerrar
        self.abierto = False
        self.pendientes.clear()
        self._captados_en.clear()
        self.eventos.append("cierra")

    def read(self) -> Captured[str] | None:
        assert self.abierto, "se ha leído el micro cerrado"
        if not self.pendientes:
            return None
        trozo = self.pendientes.pop(0)
        if self.al_leer is not None:
            self.al_leer(trozo)
        if self.reloj is None or not self._captados_en:
            return Captured(trozo)
        return Captured(trozo, age=self.reloj() - self._captados_en.pop(0))


class _Cancelador:
    """Hace de la cancelación de eco: quita de cada trozo el eco y dice si lo había. Apunta
    cada trozo que limpia, en orden."""

    def __init__(self) -> None:
        self.limpiados: list[str] = []
        self.falla: Exception | None = None

    def clean(self, captured: Captured[str]) -> Cleaned[str]:
        if self.falla is not None:
            raise self.falla
        self.limpiados.append(captured.chunk)
        if captured.chunk == ECO:
            return Cleaned("", echoing=True)
        if captured.chunk.startswith(f"{ECO}+"):
            return Cleaned(captured.chunk.removeprefix(f"{ECO}+"), echoing=True)
        return Cleaned(captured.chunk)


class _Detector:
    def __init__(self) -> None:
        self.vistos: list[str] = []
        self.reinicios = 0
        self.falla_al_reiniciar: Exception | None = None
        self.falla_al_oir: Exception | None = None
        #: Lo que pasa mientras oye cada trozo: por ejemplo, que pase el tiempo.
        self.al_oir: Callable[[str], None] | None = None

    def listen(self, chunk: str) -> TurnSignal:
        self.vistos.append(chunk)
        if self.al_oir is not None:
            self.al_oir(chunk)
        if self.falla_al_oir is not None:
            raise self.falla_al_oir
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
    def __init__(self, eventos: list[str] | None = None) -> None:
        self.eventos = eventos if eventos is not None else []
        #: Un modelo de este ordenador, como Ollama.
        self.llm_provider: object = SimpleNamespace(runs_on_this_computer=True)
        self.mensajes: list[str] = []
        self.operaciones: list[str | None] = []
        self.falla: Exception | None = None
        #: Lo que escribe el modelo, a trozos, para el próximo turno; sin ellos, «R: <lo
        #: oído>» de una vez. Lo guardado es todo junto, como en la charla de verdad. Un
        #: gesto entre los trozos lo da como la de verdad, en su sitio (ADR-261).
        self.trozos: list[str | Gesture] | None = None
        #: Si se rompe después de escribir los trozos, sin guardar la respuesta.
        self.se_rompe_al_acabar: Exception | None = None
        self.desenlace = MessageStatus.COMPLETED
        self.por_que: LLMErrorKind | None = None
        #: Lo que el modelo propone recordar al contestar, como Ollama tras el delimitador.
        self.propone: str | None = None
        #: Lo que pasa al empezar a enviar, y tras escribir cada trozo: por ejemplo, que
        #: callen o paren el oído mientras contesta.
        self.al_enviar: Callable[[], None] | None = None
        self.al_escribir: Callable[[str], None] | None = None
        #: Los cortes apuntados: el mensaje y lo que se oyó de él (pieza E).
        self.cortes: list[tuple[int, str]] = []
        self.falla_al_apuntar: Exception | None = None
        #: Las respuestas que le cortaron mientras las escribía: como la de verdad, deja de
        #: escribirlas, y lo que llevaba escrito es lo que guarda (ADR-254).
        self.cortadas: list[str] = []
        self.falla_al_cortar: Exception | None = None
        #: Lo que pasa en cuanto la respuesta queda guardada, antes de lo que la charla hace
        #: después del turno, como resumir, que puede ser otra llamada al modelo.
        self.al_acabar: Callable[[], None] | None = None
        #: Cada respuesta se guarda con su número, del 7 en adelante.
        self._siguiente = 7

    def cut(self, operation_id: str) -> None:
        if self.falla_al_cortar is not None:
            raise self.falla_al_cortar
        self.cortadas.append(operation_id)
        self.eventos.append("deja de escribir")

    def mark_cut(self, message_id: int, heard: str) -> None:
        if self.falla_al_apuntar is not None:
            raise self.falla_al_apuntar
        self.cortes.append((message_id, heard))
        self.eventos.append(f"corte:{message_id}:{heard}")

    def send_message(
        self,
        user_text: str,
        *,
        operation_id: str | None = None,
        on_delta: Callable[[str], None] | None = None,
        on_completed: Callable[[], None] | None = None,
        on_gesture: Callable[[str], None] | None = None,
        only_on_this_computer: bool = False,
    ) -> SendMessageResult:
        # Como la de verdad: comprueba el mismo modelo con el que enviaría.
        if only_on_this_computer and not runs_on_this_computer(self.llm_provider):
            raise ChatLeavesThisComputer("de fuera")
        self.mensajes.append(user_text)
        self.operaciones.append(operation_id)
        if self.al_enviar is not None:
            self.al_enviar()
        if self.falla is not None:
            falla, self.falla = self.falla, None
            raise falla
        trozos, self.trozos = self.trozos or [f"R: {user_text}"], None
        escritos: list[str] = []
        for trozo in trozos:
            if operation_id in self.cortadas:
                break
            if isinstance(trozo, Gesture):
                self.eventos.append(f"gesto:{trozo.name}")
                if on_gesture is not None:
                    on_gesture(trozo.name)
                continue
            escritos.append(trozo)
            self.eventos.append(f"escribe:{trozo}")
            if on_delta is not None:
                on_delta(trozo)
            if self.al_escribir is not None:
                self.al_escribir(trozo)
        if self.se_rompe_al_acabar is not None:
            rotura, self.se_rompe_al_acabar = self.se_rompe_al_acabar, None
            raise rotura
        if self.desenlace is MessageStatus.COMPLETED and on_completed is not None:
            on_completed()
        if self.al_acabar is not None:
            self.al_acabar()
        # Lo que la charla hace después del turno, como resumir, que puede tardar.
        self.eventos.append("después del turno")
        numero, self._siguiente = self._siguiente, self._siguiente + 1
        respuesta = SimpleNamespace(
            outcome=self.desenlace,
            sirius_message=SimpleNamespace(
                id=numero,
                content="".join(escritos),
                status=self.desenlace,
                operation_id=f"op-{numero}",
            ),
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


class _Voz:
    """Piper: apunta cada frase que le piden y la devuelve como sonido."""

    def __init__(self, eventos: list[str]) -> None:
        self.eventos = eventos
        self.falla: Exception | None = None
        #: Lo que pasa mientras dice cada frase: por ejemplo, que pase el tiempo.
        self.al_decir: Callable[[], None] | None = None

    def say(self, text: str) -> str:
        self.eventos.append(f"di:{text}")
        if self.al_decir is not None:
            self.al_decir()
        if self.falla is not None:
            raise self.falla
        return f"sonido de {text}"


class _Reloj:
    """El reloj con que el oído mide lo que tarda: solo avanza cuando la prueba lo dice."""

    def __init__(self) -> None:
        self.ahora = 100.0

    def __call__(self) -> float:
        return self.ahora

    def avanza(self, segundos: float) -> None:
        self.ahora += segundos


class _Altavoz:
    """Apunta lo que suena; sigue sonando mientras la prueba lo diga."""

    def __init__(self, eventos: list[str]) -> None:
        self.eventos = eventos
        self.sigue_sonando = False
        #: Como el de verdad: lo que ya estaba saliendo sigue sonando después de callar.
        self.suena_tras_callar = False
        self.falla: Exception | None = None
        self.latency = 0.0
        #: Lo que pasa mientras toma cada sonido, antes de apuntarlo.
        self.al_sonar: Callable[[], None] | None = None
        #: Cuántos de los sonidos que tomó han empezado a sonar; sin más, todos en el acto.
        self.empezados = 0
        #: Si lo que toma espera en cola sin empezar a sonar hasta que la prueba lo diga.
        self.en_cola = False
        #: Lo que pasa mientras calla: por ejemplo, que aún empiece a sonar lo siguiente.
        self.al_callar: Callable[[], None] | None = None
        #: Lo fuerte que suena, de 0 a 1, como lo diga la prueba.
        self.nivel = 0.0

    def play(self, sound: str) -> None:
        if self.falla is not None:
            raise self.falla
        if self.al_sonar is not None:
            self.al_sonar()
        self.eventos.append(f"suena:{sound}")
        if not self.en_cola:
            self.empezados += 1

    @property
    def level(self) -> float:
        return self.nivel

    @property
    def started(self) -> int:
        return self.empezados

    @property
    def playing(self) -> bool:
        return self.sigue_sonando

    def stop(self) -> None:
        if self.al_callar is not None:
            self.al_callar()
        self.sigue_sonando = self.sigue_sonando and self.suena_tras_callar
        self.eventos.append("calla")

    def close(self) -> None:
        self.sigue_sonando = False
        self.eventos.append("suelta")


class _Lector:
    """Hace del hilo que lee el micro mientras la charla contesta: la prueba dice cuándo lee
    (``lee``), y apunta cuántas veces se puso a leer y cuántas paró."""

    def __init__(self) -> None:
        self.arranques = 0
        self.paradas = 0
        self._oye: Callable[[], None] | None = None

    def __call__(self, oye: Callable[[], None]) -> _Lector:
        self.arranques += 1
        self._oye = oye
        return self

    def lee(self) -> None:
        """Lo que haría el hilo en una de sus vueltas, si está leyendo."""
        if self._oye is not None:
            self._oye()

    def stop(self) -> None:
        self.paradas += 1
        self._oye = None


class _TodoEsParaEl:
    """Como en las piezas B y C: todo lo oído es para él. A quién le hablan (pieza D) se
    prueba en ``test_addressing.py`` y, con el servicio, en las pruebas de la pieza D de
    abajo, con ``Addressing``."""

    conversation_seconds = 10.0

    def __init__(self) -> None:
        self.callados: list[float] = []

    def fell_silent(self, at: float) -> None:
        self.callados.append(at)

    def in_conversation(self, began: float) -> bool:
        del began
        return True


class _Oido:
    """Todo junto, con el servicio montado como en producción.

    ``eventos`` es lo que pasa en orden: el micro que se abre y se cierra, lo que escribe
    la charla, lo que se le pide a la voz y lo que suena.
    """

    def __init__(
        self,
        *,
        antes: int = 2,
        detector: _Detector | None = None,
        a_quien: Addressee | None = None,
        cancelador: bool = False,
        mira: Callable[[float], bool] | None = None,
    ) -> None:
        self.eventos: list[str] = []
        self.cancelador = _Cancelador()
        self._con_cancelador = cancelador
        self.micro = _Micro(self.eventos)
        self.detector = detector or _Detector()
        self.transcriptor = _Transcriptor()
        self.charla = _Charla(self.eventos)
        self.voz = _Voz(self.eventos)
        self.altavoz = _Altavoz(self.eventos)
        self.propuestas = _Propuestas()
        self.instalacion = _Instalacion()
        self.reloj = _Reloj()
        self.lector = _Lector()
        self.cargas = 0
        self.cargas_de_la_voz = 0
        self.falla_al_cargar: VoiceUnavailable | None = None
        self.falla_al_cargar_la_voz: VoiceUnavailable | None = None
        self.servicio: LocalListening[str] = LocalListening(
            chat=self.charla,
            installation=self.instalacion,
            load_engines=self._carga,
            load_speaking=self._carga_la_voz,
            memory_suggestions=self.propuestas,
            pre_roll=antes,
            clock=self.reloj,
            addressing=a_quien if a_quien is not None else _TodoEsParaEl(),
            reader=self.lector,
            **({"looked_at": mira} if mira is not None else {}),
        )

    def _carga(self) -> ListeningEngines[str]:
        self.cargas += 1
        if self.falla_al_cargar is not None:
            raise self.falla_al_cargar
        return ListeningEngines(self.micro, self.detector, self.transcriptor)

    def _carga_la_voz(self) -> SpeakingEngines[str]:
        self.cargas_de_la_voz += 1
        if self.falla_al_cargar_la_voz is not None:
            raise self.falla_al_cargar_la_voz
        return SpeakingEngines(
            self.voz, self.altavoz, self.cancelador if self._con_cancelador else None
        )

    def suena(self, *trozos: str) -> Attended:
        self.micro.capta(*trozos)
        return self.servicio.attend()

    def dicho(self) -> list[str]:
        """Lo que se le pidió a la voz, en orden."""
        return [e.removeprefix("di:") for e in self.eventos if e.startswith("di:")]


def test_un_turno_va_a_la_charla_con_lo_que_sono_justo_antes_de_la_voz() -> None:
    oido = _Oido(antes=2)
    assert oido.servicio.start() == ""

    atendido = oido.suena("", "a", "b", voz("Hola"), "", FIN)

    (turno,) = atendido.turns
    assert (turno.heard, turno.addressed, turno.reply, turno.answered) == (
        "Hola",
        True,
        "R: Hola",
        True,
    )
    assert atendido.notice == ""
    # Los dos trozos de antes de la voz, para no cortarle la primera sílaba; no más.
    assert oido.transcriptor.turnos == [["a", "b", voz("Hola"), "", FIN]]
    assert oido.charla.mensajes == ["Hola"]


def test_cada_trozo_se_le_ensena_al_detector_una_vez_y_en_orden() -> None:
    oido = _Oido()
    oido.servicio.start()

    oido.suena("", voz("Uno"), "", FIN)
    oido.suena("", voz("Dos"), FIN)

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
    # Si no dice nada, no cierra el micro (pieza C) y sigue con lo que ya había llegado:
    # aquí, la charla no acaba bien y lo escrito a medias no se dice.
    oido = _Oido()
    oido.servicio.start()
    oido.charla.desenlace = MessageStatus.FAILED

    atendido = oido.suena(voz("Uno"), FIN, voz("Dos"), FIN)

    assert [t.heard for t in atendido.turns] == ["Uno", "Dos"]
    assert oido.charla.mensajes == ["Uno", "Dos"]
    assert oido.dicho() == []


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

    assert oido.servicio.start().startswith(
        "Para oírte y hablarte me falta instalar el modelo de oír, la voz y el detector en "
        "este ordenador."
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
    assert oido.cargas_de_la_voz == 1
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


def test_si_la_charla_se_rompe_el_turno_lo_dice_con_su_operacion_y_sigue_oyendo(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ronda 15 de Codex sobre la PR #687: como la ventana con lo escrito, la excepción se
    # queda en la frontera; el turno dice con qué operación se envió, para contar lo
    # guardado, y se sigue oyendo. El diario, solo el tipo.
    oido = _Oido()
    oido.servicio.start()
    oido.charla.falla = RuntimeError("la base está cerrada: Zarzamora")

    with caplog.at_level(logging.DEBUG):
        (roto,) = oido.suena(voz("Primero"), FIN).turns

    assert roto.result is None
    assert roto.operation_id == oido.charla.operaciones[-1]
    assert not roto.answered
    assert roto.reply == ""
    assert oido.servicio.listening
    assert "interrumpido por una excepción (RuntimeError)" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()
    assert "primero" not in caplog.text.casefold()
    atendido = oido.suena(voz("Segundo"), FIN)
    assert [t.heard for t in atendido.turns] == ["Segundo"]
    assert oido.transcriptor.turnos[-1] == [voz("Segundo"), FIN]


def test_cada_turno_va_a_la_charla_con_su_propia_operacion() -> None:
    oido = _Oido()
    oido.servicio.start()

    turnos = (*oido.suena(voz("Uno"), FIN).turns, *oido.suena(voz("Dos"), FIN).turns)

    assert [t.operation_id for t in turnos] == oido.charla.operaciones
    assert len(set(oido.charla.operaciones)) == 2
    assert None not in oido.charla.operaciones


def test_si_el_modelo_de_oir_falla_a_mitad_deja_de_oir_y_lo_dice() -> None:
    oido = _Oido()
    oido.servicio.start()

    def rompe() -> None:
        raise RuntimeError("sin memoria")

    oido.transcriptor.al_transcribir = rompe

    atendido = oido.suena(voz("Hola"), FIN)

    assert atendido == Attended(
        notice="No puedo oírte: el modelo de oír ha fallado (RuntimeError)."
    )
    assert oido.charla.mensajes == []
    assert not oido.servicio.listening
    assert not oido.micro.abierto


def test_si_el_detector_falla_a_mitad_deja_de_oir_y_lo_dice() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.detector.falla_al_oir = ValueError("onnx")

    atendido = oido.suena(voz("Hola"), FIN)

    assert atendido == Attended(
        notice="No puedo oírte: el detector de voz ha fallado (ValueError)."
    )
    assert oido.charla.mensajes == []
    assert not oido.servicio.listening


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
    assert turno.result is not None
    assert turno.result.error_kind is LLMErrorKind.CONNECTION
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
    oido = _Oido()
    oido.servicio.start()

    with caplog.at_level(logging.DEBUG):
        oido.suena(voz("La clave es Zarzamora"), FIN)

    assert "Turno de voz entregado a la charla" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()


# --- Lo que contesta, lo dice en voz alta (pieza C, ADR-243) ------------------------


def test_dice_cada_frase_en_cuanto_la_charla_la_cierra_con_el_micro_cerrado() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = ["Primera frase.", " Segunda", " frase. Y la", " tercera."]

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert turno.reply == "Primera frase. Segunda frase. Y la tercera."
    # Cada frase, en cuanto la charla escribe lo que la cierra, y la última en cuanto la
    # respuesta acaba, sin esperar a lo que la charla hace después del turno, como
    # resumir. Antes de la primera se cierra el micro, y se abre cuando el altavoz acaba.
    assert oido.eventos == [
        "abre",
        "escribe:Primera frase.",
        "escribe: Segunda",
        "cierra",
        "di:Primera frase.",
        "suena:sonido de Primera frase.",
        "escribe: frase. Y la",
        "di:Segunda frase.",
        "suena:sonido de Segunda frase.",
        "escribe: tercera.",
        "di:Y la tercera.",
        "suena:sonido de Y la tercera.",
        "después del turno",
        "abre",
    ]
    assert oido.servicio.listening


def test_mientras_suena_no_lee_el_micro_y_vuelve_a_oir_cuando_calla() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.altavoz.sigue_sonando = True

    oido.suena(voz("Cuéntame"), FIN)

    assert not oido.micro.abierto
    assert oido.servicio.listening
    # Su propia voz, de vuelta por el micro, se pierde: está cerrado.
    assert oido.suena(voz("R: Cuéntame"), FIN) == Attended()
    assert oido.micro.perdidos == [voz("R: Cuéntame"), FIN]
    oido.altavoz.sigue_sonando = False
    assert oido.servicio.attend() == Attended()
    assert oido.micro.abierto
    assert [t.heard for t in oido.suena(voz("Otra cosa"), FIN).turns] == ["Otra cosa"]
    assert oido.transcriptor.turnos == [[voz("Cuéntame"), FIN], [voz("Otra cosa"), FIN]]


def test_lo_que_llego_mientras_pensaba_se_pierde_al_empezar_a_hablar() -> None:
    # Mientras contesta no escucha (ADR-243): al cerrar el micro para hablar, se tira lo
    # que nadie ha leído. Oírle mientras habla es la pieza E.
    oido = _Oido()
    oido.servicio.start()

    atendido = oido.suena(voz("Uno"), FIN, voz("Dos"), FIN)

    assert [t.heard for t in atendido.turns] == ["Uno"]
    assert oido.detector.vistos == [voz("Uno"), FIN]
    assert oido.charla.mensajes == ["Uno"]
    assert oido.micro.abierto


def test_si_la_charla_no_acaba_bien_no_dice_lo_que_quedo_a_medias() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = ["Una frase entera.", " Y otra a med"]
    oido.charla.desenlace = MessageStatus.CANCELLED

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert not turno.answered
    assert oido.dicho() == ["Una frase entera."]
    assert oido.micro.abierto


def test_si_no_hay_nada_que_decir_no_cierra_el_micro() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = ["---"]

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert turno.answered
    assert turno.first_sound_delay is None
    assert oido.eventos == ["abre", "escribe:---", "después del turno"]


@pytest.mark.parametrize(
    ("pieza", "que", "aviso"),
    [
        ("voz", "la voz", "No puedo hablarte: la voz ha fallado (RuntimeError)."),
        ("altavoz", "el altavoz", "No puedo hablarte: el altavoz ha fallado (RuntimeError)."),
    ],
)
def test_si_falla_al_hablar_la_charla_acaba_y_deja_de_oir_diciendolo(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    pieza: str,
    que: str,
    aviso: str,
) -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = ["Una frase.", " Otra frase con Zarzamora.", " Y otra."]
    falla = RuntimeError("onnxruntime: Zarzamora")
    if pieza == "voz":
        oido.voz.falla = falla
    else:
        oido.altavoz.falla = falla

    with caplog.at_level(logging.DEBUG):
        atendido = oido.suena(voz("Cuéntame"), FIN)

    (turno,) = atendido.turns
    # El fallo no sale a la charla: acaba y guarda la respuesta entera.
    assert turno.answered
    assert turno.reply == "Una frase. Otra frase con Zarzamora. Y otra."
    assert atendido.notice == aviso
    assert "la orden de instalar" not in aviso
    assert not oido.servicio.listening
    # Desde el fallo no dice nada más, calla lo que sonara y el micro sigue cerrado.
    assert oido.dicho() == ["Una frase."]
    assert oido.eventos[-1] == "calla"
    assert oido.eventos.count("cierra") == 1
    assert not oido.micro.abierto
    assert f"{que} ha fallado (RuntimeError)" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()


def test_si_falla_al_preparar_la_frase_tampoco_sale_a_la_charla(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def rompe(self: SpeechCutter, text: str) -> list[str]:
        raise ValueError(text)

    monkeypatch.setattr(SpeechCutter, "feed", rompe)
    oido = _Oido()
    oido.servicio.start()

    atendido = oido.suena(voz("Cuéntame"), FIN)

    assert [t.answered for t in atendido.turns] == [True]
    assert atendido.notice == "No puedo hablarte: la voz ha fallado (ValueError)."
    assert oido.dicho() == []


def test_si_la_charla_se_rompe_tras_empezar_a_hablar_vuelve_a_oir_al_callar() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = ["Una frase.", " Otra a med"]
    oido.charla.se_rompe_al_acabar = RuntimeError("la base está cerrada")

    atendido = oido.suena(voz("Cuéntame"), FIN)

    (roto,) = atendido.turns
    assert roto.result is None
    assert atendido.notice == ""
    assert oido.dicho() == ["Una frase."]
    assert oido.micro.abierto
    assert oido.servicio.listening


def test_si_la_charla_se_rompe_y_la_voz_fallo_deja_de_oir_diciendolo() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = ["Una frase.", " Otra a med"]
    oido.charla.se_rompe_al_acabar = RuntimeError("la base está cerrada")
    oido.voz.falla = OSError("sin memoria")

    atendido = oido.suena(voz("Cuéntame"), FIN)

    assert [t.result for t in atendido.turns] == [None]
    assert atendido.notice == "No puedo hablarte: la voz ha fallado (OSError)."
    assert not oido.servicio.listening


def test_si_la_voz_no_carga_aconseja_la_orden_y_no_abre_el_micro() -> None:
    oido = _Oido()
    oido.falla_al_cargar_la_voz = VoiceUnavailable("piper no carga (DLL)")

    aviso = oido.servicio.start()

    assert aviso.startswith("No puedo hablarte: piper no carga (DLL).")
    assert "la orden de instalar" in aviso
    assert not oido.micro.abierto
    assert not oido.servicio.listening
    # Al volver a intentarlo, carga lo que faltaba y nada más.
    oido.falla_al_cargar_la_voz = None
    assert oido.servicio.start() == ""
    assert (oido.cargas, oido.cargas_de_la_voz) == (1, 2)


def test_parar_mientras_habla_le_calla_y_al_volver_abre_el_micro() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.altavoz.sigue_sonando = True
    oido.suena(voz("Cuéntame"), FIN)

    oido.servicio.stop()

    assert not oido.altavoz.sigue_sonando
    assert oido.servicio.start() == ""
    assert oido.cargas_de_la_voz == 1, "la misma voz, sin volver a cargarla"
    assert [t.heard for t in oido.suena(voz("Hola"), FIN).turns] == ["Hola"]
    # Al volver, el micro se abre una vez: parar olvidó que estaba hablando.
    assert oido.eventos == [
        "abre",
        "escribe:R: Cuéntame",
        "cierra",
        "di:R: Cuéntame",
        "suena:sonido de R: Cuéntame",
        "después del turno",
        "calla",
        "abre",
        "escribe:R: Hola",
        "cierra",
        "di:R: Hola",
        "suena:sonido de R: Hola",
        "después del turno",
        "abre",
    ]


def test_si_el_micro_no_vuelve_a_abrirse_al_callar_deja_de_oir_y_lo_dice() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.altavoz.sigue_sonando = True
    oido.suena(voz("Cuéntame"), FIN)
    oido.micro.falla_al_abrir = VoiceUnavailable("no puedo abrir el micrófono (desenchufado)")
    oido.altavoz.sigue_sonando = False

    aviso = "No puedo oírte: no puedo abrir el micrófono (desenchufado)."
    assert oido.servicio.attend() == Attended(notice=aviso)
    assert not oido.servicio.listening


def test_si_el_micro_no_vuelve_a_abrirse_tras_contestar_el_turno_llega_con_el_aviso() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.micro.falla_al_abrir = VoiceUnavailable("no puedo abrir el micrófono (desenchufado)")

    atendido = oido.suena(voz("Cuéntame"), FIN)

    assert [t.answered for t in atendido.turns] == [True]
    assert atendido.notice == "No puedo oírte: no puedo abrir el micrófono (desenchufado)."
    assert not oido.servicio.listening


def test_mide_desde_que_deja_de_oir_su_voz_hasta_que_suena_la_primera_frase(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # E-R03-02: cuenta el silencio que espera el detector, transcribir, la charla, la voz y
    # lo que tarda el altavoz en sonar; no lo que había antes de la última voz.
    oido = _Oido()
    oido.servicio.start()
    # Cada trozo llega un cuarto de segundo después del anterior.
    oido.micro.al_leer = lambda trozo: oido.reloj.avanza(0.25) if trozo != FIN else None
    oido.transcriptor.al_transcribir = lambda: oido.reloj.avanza(0.5)
    oido.voz.al_decir = lambda: oido.reloj.avanza(0.125)
    oido.altavoz.latency = 0.0625
    oido.charla.trozos = ["La clave es Zarzamora.", " Y otra frase."]

    with caplog.at_level(logging.DEBUG):
        (turno,) = oido.suena("", voz("La clave"), "", voz("es Zarzamora"), "", FIN).turns

    # Desde la segunda voz: su silencio, 0,25; transcribir, 0,5; la primera frase, 0,125;
    # y el altavoz, 0,0625.
    assert turno.first_sound_delay == 0.9375
    assert "Turno de voz: primer sonido a 937 ms de dejar de oír su voz" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()


def test_si_al_volver_aun_suena_lo_que_dijo_no_abre_el_micro_hasta_que_calle() -> None:
    # Ronda 1 de Codex sobre la PR #688: parar no calla lo que el altavoz ya tenía, y
    # abrir el micro entonces dejaría entrar su propia voz.
    oido = _Oido()
    oido.servicio.start()
    oido.altavoz.sigue_sonando = True
    oido.altavoz.suena_tras_callar = True
    oido.suena(voz("Cuéntame"), FIN)
    oido.servicio.stop()

    assert oido.servicio.start() == ""

    assert oido.servicio.listening
    assert not oido.micro.abierto
    assert oido.suena(voz("R: Cuéntame"), FIN) == Attended(), "su propia voz se pierde"
    oido.altavoz.sigue_sonando = False
    assert oido.servicio.attend() == Attended()
    assert oido.micro.abierto
    assert [t.heard for t in oido.suena(voz("Hola"), FIN).turns] == ["Hola"]
    assert oido.charla.mensajes == ["Cuéntame", "Hola"]


# --- A quién le hablan, el silencio y quien mira (pieza D, ADR-244) ----------------


class _Mirador:
    """Hace de la ventana: deja pasar cada turno o no, y apunta lo que le cuentan."""

    def __init__(self, *, deja: bool = True) -> None:
        self.deja = deja
        self.preguntas: list[tuple[str, str]] = []
        self.acabados: list[HeardTurn | None] = []
        self.paros: list[str] = []
        #: Lo que pasa mientras decide: por ejemplo, que callen el oído.
        self.al_preguntar: Callable[[], None] | None = None

    def may_answer(self, operation_id: str, heard: str) -> bool:
        self.preguntas.append((operation_id, heard))
        if self.al_preguntar is not None:
            self.al_preguntar()
        return self.deja

    def answered(self, turn: HeardTurn | None) -> None:
        self.acabados.append(turn)

    def stopped(self, notice: str) -> None:
        self.paros.append(notice)


def _oido_que_elige() -> _Oido:
    """El oído con ``Addressing``, como en producción: con su nombre o en la charla."""
    oido = _Oido(a_quien=Addressing(conversation_seconds=10.0))
    oido.servicio.start()
    return oido


def test_lo_que_no_es_para_el_se_transcribe_y_se_descarta_sin_ir_a_la_charla() -> None:
    oido = _oido_que_elige()

    (turno,) = oido.suena(voz("Y mañana, cielos despejados"), FIN).turns

    assert (turno.heard, turno.addressed, turno.result, turno.operation_id) == (
        "Y mañana, cielos despejados",
        False,
        None,
        "",
    )
    assert oido.transcriptor.turnos == [[voz("Y mañana, cielos despejados"), FIN]]
    assert oido.charla.mensajes == []
    assert oido.dicho() == []
    assert oido.micro.abierto, "sigue oyendo"


def test_lo_que_no_es_para_el_no_queda_en_el_diario(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    oido = _oido_que_elige()

    with caplog.at_level(logging.DEBUG):
        oido.suena(voz("La clave es Zarzamora"), FIN)

    assert "no era para él" in caplog.text
    assert "zarzamora" not in caplog.text.casefold()


def test_sin_su_nombre_va_a_la_charla_solo_mientras_dura_la_charla() -> None:
    oido = _oido_que_elige()
    oido.suena(voz("Sirius, hola"), FIN)

    oido.reloj.avanza(9)
    assert [t.addressed for t in oido.suena(voz("¿Qué tal?"), FIN).turns] == [True]
    oido.reloj.avanza(11)
    assert [t.addressed for t in oido.suena(voz("¿Qué tal?"), FIN).turns] == [False]
    assert oido.charla.mensajes == ["Sirius, hola", "¿Qué tal?"]


def test_la_charla_empieza_cuando_el_altavoz_acaba_de_sonar() -> None:
    oido = _oido_que_elige()
    oido.altavoz.sigue_sonando = True
    oido.suena(voz("Sirius, cuéntame"), FIN)
    # Medio minuto hablando: la charla aún no ha empezado.
    oido.reloj.avanza(30)
    assert oido.servicio.attend() == Attended()
    oido.altavoz.sigue_sonando = False
    oido.servicio.attend()

    oido.reloj.avanza(9)

    assert [t.addressed for t in oido.suena(voz("¿Y luego?"), FIN).turns] == [True]


def test_si_no_dijo_nada_la_charla_empieza_al_acabar_el_turno() -> None:
    oido = _oido_que_elige()
    oido.charla.desenlace = MessageStatus.FAILED
    oido.suena(voz("Sirius, hola"), FIN)
    assert oido.dicho() == []

    oido.reloj.avanza(9)

    assert [t.addressed for t in oido.suena(voz("¿Me oyes?"), FIN).turns] == [True]


def test_lo_que_sono_mientras_contestaba_sin_decir_nada_no_es_de_la_charla_de_despues() -> None:
    # Ronda 1 de Codex sobre la PR #689: mientras la charla contesta, el micro sigue
    # captando y nadie lo lee. Si al final no dice nada, la charla empieza al acabar el
    # turno, y lo que la tele dijo mientras tanto empezó antes: no es de ella, aunque el
    # oído lo lea después.
    oido = _oido_que_elige()
    oido.micro.reloj = oido.reloj
    oido.charla.desenlace = MessageStatus.FAILED

    def la_tele_habla_mientras_contesta() -> None:
        oido.charla.al_enviar = None
        oido.reloj.avanza(1)
        oido.micro.capta(voz("Y mañana, cielos despejados"), FIN)
        oido.reloj.avanza(4)

    oido.charla.al_enviar = la_tele_habla_mientras_contesta

    atendido = oido.suena(voz("Sirius, hola"), FIN)

    assert oido.dicho() == []
    assert [(t.heard, t.addressed) for t in atendido.turns] == [
        ("Sirius, hola", True),
        ("Y mañana, cielos despejados", False),
    ]
    assert oido.charla.mensajes == ["Sirius, hola"]


def test_la_charla_cuenta_desde_que_el_micro_capta_su_voz_y_no_desde_que_la_lee() -> None:
    # Ronda 1 de Codex sobre la PR #689: lo que suena mientras el oído está con otra cosa
    # espera en la cola del micro. Si empezó dentro de la charla, es de ella aunque el
    # oído lo lea fuera.
    oido = _oido_que_elige()
    oido.micro.reloj = oido.reloj
    mirador = _Mirador()
    oido.servicio.watch(mirador)
    oido.suena(voz("Sirius, hola"), FIN)
    oido.reloj.avanza(8)

    def la_ventana_tarda_en_decir_que_no() -> None:
        # Mientras, él sigue hablando; a la pregunta siguiente, la ventana ya está libre.
        oido.micro.capta(voz("¿Me oyes?"), FIN)
        oido.reloj.avanza(5)
        mirador.al_preguntar = lambda: setattr(mirador, "deja", True)

    mirador.deja = False
    mirador.al_preguntar = la_ventana_tarda_en_decir_que_no

    atendido = oido.suena(voz("Sirius, ¿estás?"), FIN)

    # El primero no fue: la ventana estaba con otra cosa. El segundo empezó a sonar a los
    # 8 s de que callara, dentro de la charla, y el oído lo leyó a los 13.
    assert [(t.heard, t.addressed) for t in atendido.turns] == [("¿Me oyes?", True)]
    assert oido.charla.mensajes == ["Sirius, hola", "¿Me oyes?"]


def test_lo_que_el_micro_capta_mientras_se_abre_tras_hablar_ya_es_de_la_charla() -> None:
    # Calla antes de que se abra el micro: lo que capte al abrirse empezó después.
    oido = _oido_que_elige()
    oido.micro.reloj = oido.reloj
    oido.altavoz.sigue_sonando = True
    oido.suena(voz("Sirius, cuéntame"), FIN)
    oido.altavoz.sigue_sonando = False

    def capta_mientras_se_abre() -> None:
        oido.micro.al_abrir = None
        oido.micro.capta(voz("¿Y luego?"), FIN)
        oido.reloj.avanza(0.5)

    oido.micro.al_abrir = capta_mientras_se_abre

    (turno,) = oido.servicio.attend().turns

    assert (turno.heard, turno.addressed) == ("¿Y luego?", True)


def test_lo_que_tarda_en_sonar_cuenta_lo_que_su_voz_espero_en_la_cola() -> None:
    # E-R03-02 cuenta desde que deja de oírse su voz: desde que el micro la captó, no
    # desde que el oído la leyó.
    oido = _Oido()
    oido.micro.reloj = oido.reloj
    oido.servicio.start()
    oido.micro.capta(voz("Cuéntame"), FIN)
    # El oído estaba con otra cosa: dos segundos en la cola del micro.
    oido.reloj.avanza(2)

    (turno,) = oido.servicio.attend().turns

    assert turno.first_sound_delay == 2.0


def test_la_charla_cuenta_desde_que_empieza_a_oirse_su_voz() -> None:
    oido = _oido_que_elige()
    oido.suena(voz("Sirius, hola"), FIN)
    oido.reloj.avanza(8)
    # Cada trozo dura un segundo: empieza a oírse dentro de la charla y acaba fuera.
    oido.micro.al_leer = lambda _trozo: oido.reloj.avanza(1)

    (turno,) = oido.suena(voz("Pues"), voz("verás,"), voz("es largo"), FIN).turns

    assert turno.addressed
    assert oido.reloj.ahora - 100.0 > 10


def test_lo_que_tarda_el_detector_en_mirar_el_trozo_no_cuenta_para_la_charla() -> None:
    # Ronda 2 de Codex sobre la PR #689: la hora es la del micro al captar el trozo, antes
    # de que el detector lo mire. Su voz empieza a los 9,9 s de que calle; el detector
    # tarda 0,2 s en decir que es voz, y sigue siendo de la charla.
    oido = _oido_que_elige()
    oido.suena(voz("Sirius, hola"), FIN)
    oido.reloj.avanza(9.9)
    oido.detector.al_oir = lambda trozo: oido.reloj.avanza(0.2) if trozo != FIN else None

    (turno,) = oido.suena(voz("¿Me oyes?"), FIN).turns

    assert turno.addressed
    assert oido.charla.mensajes == ["Sirius, hola", "¿Me oyes?"]


def test_sin_decirle_a_quien_le_hablan_decide_como_en_produccion() -> None:
    eventos: list[str] = []
    micro, charla = _Micro(eventos), _Charla(eventos)
    servicio: LocalListening[str] = LocalListening(
        chat=charla,
        installation=_Instalacion(),
        load_engines=lambda: ListeningEngines(micro, _Detector(), _Transcriptor()),
        load_speaking=lambda: SpeakingEngines(_Voz(eventos), _Altavoz(eventos)),
        memory_suggestions=_Propuestas(),
    )
    servicio.start()
    micro.capta(voz("Y mañana, cielos despejados"), FIN)

    (turno,) = servicio.attend().turns

    assert not turno.addressed
    assert charla.mensajes == []
    assert servicio.conversation_seconds == 10.0


def test_la_charla_dura_lo_que_dice_a_quien_le_hablan() -> None:
    assert _Oido(a_quien=Addressing(conversation_seconds=7.0)).servicio.conversation_seconds == 7.0


def test_el_silencio_cierra_el_micro_y_nadie_lo_abre_hasta_quitarlo() -> None:
    oido = _Oido()
    oido.servicio.start()

    oido.servicio.mute()

    assert (oido.micro.abierto, oido.servicio.muted, oido.servicio.listening) == (
        False,
        True,
        False,
    )
    assert oido.servicio.start() == ""
    assert not oido.micro.abierto
    assert oido.suena(voz("Hola"), FIN) == Attended()
    assert oido.micro.perdidos == [voz("Hola"), FIN]

    assert oido.servicio.unmute() == ""

    assert (oido.micro.abierto, oido.servicio.muted, oido.servicio.listening) == (True, False, True)
    assert [t.heard for t in oido.suena(voz("Otra"), FIN).turns] == ["Otra"]
    assert oido.transcriptor.turnos == [[voz("Otra"), FIN]]


def test_quitar_el_silencio_dice_si_no_puede_volver_a_oir() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.servicio.mute()
    oido.micro.falla_al_abrir = VoiceUnavailable("no puedo abrir el micrófono (ocupado)")

    aviso = oido.servicio.unmute()

    assert aviso == "No puedo oírte: no puedo abrir el micrófono (ocupado)."
    assert not oido.servicio.muted
    assert not oido.servicio.listening


def test_el_silencio_olvida_el_turno_a_medias_y_reinicia_el_detector() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.suena(voz("Estaba pensando"), "")

    oido.servicio.mute()
    oido.servicio.unmute()

    assert oido.detector.reinicios == 1
    assert oido.suena("", FIN) == Attended()
    assert oido.transcriptor.turnos == []


def test_lo_oido_antes_del_silencio_que_aun_no_habia_ido_a_la_charla_ya_no_va() -> None:
    oido = _Oido()
    mirador = _Mirador()
    oido.servicio.watch(mirador)
    oido.servicio.start()
    oido.transcriptor.al_transcribir = oido.servicio.mute

    assert oido.suena(voz("Sirius, hola"), FIN) == Attended()
    assert oido.charla.mensajes == []
    # Ni se le pregunta a quien mira por un turno que ya no va a ir.
    assert mirador.preguntas == []


def test_si_lo_callan_mientras_quien_mira_decide_el_turno_no_va() -> None:
    oido = _Oido()
    mirador = _Mirador()
    mirador.al_preguntar = oido.servicio.mute
    oido.servicio.watch(mirador)
    oido.servicio.start()

    assert oido.suena(voz("Sirius, hola"), FIN) == Attended()
    assert oido.charla.mensajes == []
    assert mirador.acabados == [None]


def test_el_silencio_no_calla_lo_que_esta_diciendo() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = ["Primera frase.", " Segunda frase.", " Tercera."]
    oido.charla.al_escribir = lambda trozo: (
        oido.servicio.mute() if trozo == " Segunda frase." else None
    )

    oido.suena(voz("Cuéntame"), FIN)

    assert oido.dicho() == ["Primera frase.", "Segunda frase.", "Tercera."]
    assert "calla" not in oido.eventos
    assert not oido.micro.abierto
    assert oido.servicio.muted


def test_si_lo_callan_antes_de_la_primera_frase_no_le_abre_el_micro_al_acabar() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.al_enviar = oido.servicio.mute

    oido.suena(voz("Cuéntame"), FIN)

    assert oido.dicho() == ["R: Cuéntame"]
    assert not oido.micro.abierto
    assert oido.eventos.count("abre") == 1


def test_parar_mientras_prepara_una_frase_ya_no_la_da_al_altavoz() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.voz.al_decir = oido.servicio.stop

    oido.suena(voz("Cuéntame"), FIN)

    assert oido.dicho() == ["R: Cuéntame"]
    assert not any(evento.startswith("suena:") for evento in oido.eventos)


def test_parar_mientras_contesta_calla_lo_que_quedaba_por_decir() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = ["Primera frase.", " Segunda frase.", " Tercera."]
    oido.charla.al_escribir = lambda trozo: (
        oido.servicio.stop() if trozo == " Segunda frase." else None
    )

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    # La charla acaba y guarda la respuesta entera; lo que quedaba ya no suena.
    assert turno.reply == "Primera frase. Segunda frase. Tercera."
    assert oido.dicho() == ["Primera frase."]
    assert oido.eventos.count("calla") == 1


def test_quien_mira_decide_si_un_turno_para_el_va_a_la_charla() -> None:
    oido = _Oido()
    mirador = _Mirador(deja=False)
    oido.servicio.watch(mirador)
    oido.servicio.start()

    assert oido.suena(voz("Hola"), FIN) == Attended()
    assert [oido_ for _, oido_ in mirador.preguntas] == ["Hola"]
    assert oido.charla.mensajes == []
    assert mirador.acabados == []
    assert oido.micro.abierto, "sigue oyendo"


def test_quien_mira_se_entera_de_como_acabo_cada_turno_que_dejo_pasar() -> None:
    oido = _Oido()
    mirador = _Mirador()
    oido.servicio.watch(mirador)
    oido.servicio.start()

    (turno,) = oido.suena(voz("Hola"), FIN).turns
    oido.charla.falla = RuntimeError("rota")
    (roto,) = oido.suena(voz("Otra"), FIN).turns

    assert mirador.preguntas == [(turno.operation_id, "Hola"), (roto.operation_id, "Otra")]
    assert oido.charla.operaciones == [turno.operation_id, roto.operation_id]
    assert mirador.acabados == [turno, roto]
    assert roto.result is None


def test_si_la_charla_se_va_fuera_quien_mira_sabe_que_el_turno_no_fue() -> None:
    oido = _Oido()
    mirador = _Mirador()
    mirador.al_preguntar = lambda: setattr(
        oido.charla, "llm_provider", SimpleNamespace(runs_on_this_computer=False)
    )
    oido.servicio.watch(mirador)
    oido.servicio.start()

    assert oido.suena(voz("Hola"), FIN) == Attended(notice=CHAT_LEAVES)
    assert mirador.acabados == [None]
    assert mirador.paros == [CHAT_LEAVES]


def test_lo_que_no_era_para_el_no_se_le_pregunta_a_quien_mira() -> None:
    oido = _oido_que_elige()
    mirador = _Mirador()
    oido.servicio.watch(mirador)

    oido.suena(voz("La tele"), FIN)

    assert (mirador.preguntas, mirador.acabados) == ([], [])


def test_si_deja_de_oir_por_su_cuenta_se_lo_dice_a_quien_mira_una_vez() -> None:
    oido = _Oido()
    mirador = _Mirador()
    oido.servicio.watch(mirador)
    oido.servicio.start()
    oido.detector.falla_al_oir = RuntimeError("roto")

    atendido = oido.suena(voz("Hola"))
    oido.servicio.attend()

    assert atendido.notice
    assert mirador.paros == [atendido.notice]


def test_quien_mira_no_se_entera_de_que_lo_callan_o_lo_paran_otros() -> None:
    oido = _Oido()
    mirador = _Mirador()
    oido.servicio.watch(mirador)
    oido.servicio.start()

    oido.servicio.mute()
    oido.servicio.attend()
    oido.servicio.unmute()
    oido.servicio.stop()
    oido.servicio.attend()

    assert mirador.paros == []


def test_sin_quien_mire_ya_no_se_le_pregunta() -> None:
    oido = _Oido()
    mirador = _Mirador(deja=False)
    oido.servicio.watch(mirador)
    oido.servicio.watch(None)
    oido.servicio.start()

    assert [t.heard for t in oido.suena(voz("Hola"), FIN).turns] == ["Hola"]
    assert mirador.preguntas == []


# --- Desde dos hilos: la ventana calla el oído mientras otro lo atiende -------------


def test_el_silencio_no_espera_a_que_acabe_el_turno_que_esta_contestando() -> None:
    oido = _Oido()
    oido.servicio.start()
    escribiendo, sigue = threading.Event(), threading.Event()

    def al_enviar() -> None:
        escribiendo.set()
        sigue.wait(5)

    oido.charla.al_enviar = al_enviar
    oido.micro.capta(voz("Hola"), FIN)
    atiende = threading.Thread(target=oido.servicio.attend)
    atiende.start()
    calla = threading.Thread(target=oido.servicio.mute)
    try:
        assert escribiendo.wait(5)
        calla.start()
        calla.join(2)
        assert not calla.is_alive(), "el silencio esperó a que acabara el turno"
        assert not oido.micro.abierto
    finally:
        sigue.set()
        atiende.join(5)
        if calla.ident is not None:
            calla.join(5)


def test_el_silencio_espera_a_que_el_detector_acabe_con_su_trozo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oido = _Oido()
    oido.servicio.start()
    dentro, sigue = threading.Event(), threading.Event()
    reiniciado_a_medias: list[bool] = []
    reinicia = oido.detector.reset

    def al_oir(trozo: str) -> None:
        if trozo == voz("Hola"):
            dentro.set()
            sigue.wait(5)

    def reset() -> None:
        reiniciado_a_medias.append(dentro.is_set() and not sigue.is_set())
        reinicia()

    oido.detector.al_oir = al_oir
    monkeypatch.setattr(oido.detector, "reset", reset)
    oido.micro.capta(voz("Hola"), FIN)
    atiende = threading.Thread(target=oido.servicio.attend)
    atiende.start()
    calla = threading.Thread(target=oido.servicio.mute)
    try:
        assert dentro.wait(5)
        calla.start()
        calla.join(0.5)
        assert calla.is_alive(), "el silencio no esperó a que el detector acabara"
    finally:
        sigue.set()
        atiende.join(5)
        if calla.ident is not None:
            calla.join(5)
    assert reiniciado_a_medias == [False]


def test_parar_espera_a_que_el_altavoz_tome_la_frase_y_despues_la_calla() -> None:
    oido = _Oido()
    oido.servicio.start()
    tomando, sigue = threading.Event(), threading.Event()

    def al_sonar() -> None:
        tomando.set()
        sigue.wait(5)

    oido.altavoz.al_sonar = al_sonar
    oido.micro.capta(voz("Cuéntame"), FIN)
    atiende = threading.Thread(target=oido.servicio.attend)
    atiende.start()
    para = threading.Thread(target=oido.servicio.stop)
    try:
        assert tomando.wait(5)
        para.start()
        para.join(0.5)
        assert para.is_alive(), "parar no esperó a que el altavoz tomara la frase"
    finally:
        sigue.set()
        atiende.join(5)
        if para.ident is not None:
            para.join(5)
    # Lo que tomó el altavoz, lo vació después al callar.
    assert oido.eventos.index("calla") > oido.eventos.index("suena:sonido de R: Cuéntame")


# --- Pieza E: con cancelación de eco se le puede cortar (ADR-245) -----------------------


def _oido_con_cancelador(*, a_quien: Addressee | None = None) -> _Oido:
    oido = _Oido(cancelador=True, a_quien=a_quien)
    oido.micro.reloj = oido.reloj
    oido.servicio.start()
    return oido


def test_con_cancelador_el_micro_sigue_abierto_mientras_habla_y_su_eco_no_es_un_turno() -> None:
    oido = _oido_con_cancelador()
    oido.altavoz.sigue_sonando = True

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert turno.reply == "R: Cuéntame"
    assert oido.micro.abierto
    assert "cierra" not in oido.eventos
    # Su propia voz vuelve por el micro y el cancelador la aparta antes del detector.
    assert oido.suena(eco(), eco()) == Attended()
    assert oido.cancelador.limpiados == [voz("Cuéntame"), FIN, ECO, ECO]
    assert oido.detector.vistos == [voz("Cuéntame"), FIN, "", ""]
    assert "calla" not in oido.eventos
    assert oido.transcriptor.turnos == [[voz("Cuéntame"), FIN]]


def test_si_le_hablan_encima_mientras_suena_calla_al_oirle_y_lo_que_dice_es_para_el() -> None:
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))
    oido.altavoz.sigue_sonando = True
    oido.suena(voz("Sirius, cuéntame"), FIN)

    # Le habla encima: la voz llega con el eco, y calla al oírla, con el turno abierto. Calla
    # antes de apuntar hasta dónde se oyó.
    assert oido.suena(eco(voz("Espera"))) == Attended()

    assert oido.eventos[-2:] == ["calla", "corte:7:R: Sirius, cuéntame"]
    assert not oido.altavoz.playing
    # Lo que le corta es para él aunque no diga su nombre.
    (turno,) = oido.suena(FIN).turns
    assert (turno.heard, turno.addressed, turno.reply) == ("Espera", True, "R: Espera")


def test_al_cortarle_apunta_lo_que_llego_a_sonar_y_la_respuesta_sigue_entera() -> None:
    oido = _oido_con_cancelador()
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra."]
    oido.altavoz.sigue_sonando = True
    # Las tres frases esperan en la cola del altavoz, y solo la primera empieza a sonar.
    oido.altavoz.en_cola = True
    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns
    assert oido.dicho() == ["Una frase.", "Otra frase.", "Y otra."]
    oido.altavoz.empezados = 1

    oido.suena(eco(voz("Espera")))

    assert turno.reply == "Una frase. Otra frase. Y otra."
    assert oido.charla.cortes == [(7, "Una frase.")]
    # Ya estaba escrita: no hay nada que dejar de escribir (ADR-254).
    assert oido.charla.cortadas == []


def test_cuenta_como_oido_lo_que_empezo_a_sonar_hasta_que_callo_mientras_escribe() -> None:
    # Mientras calla, el altavoz aún puede empezar la frase siguiente, y esa ya se oyó.
    oido = _oido_con_cancelador()
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra. ", "Y más."]
    oido.altavoz.en_cola = True

    def habla_encima(trozo: str) -> None:
        if trozo == "Y otra. ":
            # Las dos primeras esperan en el altavoz, que empieza la primera, y le habla
            # encima; mientras calla, empieza la segunda.
            oido.altavoz.empezados = 1
            oido.altavoz.al_callar = lambda: setattr(oido.altavoz, "empezados", 2)
            oido.micro.capta(voz("Espera"))

    oido.charla.al_escribir = habla_encima

    oido.suena(voz("Cuéntame"), FIN)

    assert oido.charla.cortes == [(7, "Una frase. Otra frase.")]


def test_cuenta_como_oido_lo_que_empezo_a_sonar_hasta_que_callo_ya_escrito() -> None:
    oido = _oido_con_cancelador()
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra."]
    oido.altavoz.sigue_sonando = True
    oido.altavoz.en_cola = True
    oido.suena(voz("Cuéntame"), FIN)
    oido.altavoz.empezados = 1
    oido.altavoz.al_callar = lambda: setattr(oido.altavoz, "empezados", 2)

    oido.suena(eco(voz("Espera")))

    assert oido.charla.cortes == [(7, "Una frase. Otra frase.")]


def test_si_le_hablan_mientras_la_charla_escribe_calla_sin_decir_otra_frase() -> None:
    oido = _oido_con_cancelador()
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra."]

    def habla_encima() -> None:
        # En cuanto el altavoz toma la primera frase, el propietario habla encima.
        if oido.altavoz.empezados == 0:
            oido.micro.capta(eco(voz("Espera")))

    oido.altavoz.al_sonar = habla_encima

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    # Calla al leerle, antes de decir la frase siguiente; la charla sigue y guarda la
    # respuesta entera, y en ella queda apuntado lo que se oyó.
    assert oido.dicho() == ["Una frase."]
    assert "calla" in oido.eventos
    assert turno.reply == "Una frase. Otra frase. Y otra."
    assert oido.charla.cortes == [(7, "Una frase.")]


def test_al_cortarle_mientras_escribe_la_charla_deja_de_escribir_y_queda_lo_escrito() -> None:
    # Lo decidió el propietario el 17-10-2026 (ADR-254): al cortarle, la charla deja de
    # escribir la respuesta, aunque quede a medias, y en lo escrito se apunta lo que se oyó.
    oido = _oido_con_cancelador()
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra. ", "Y más. ", "Y ya."]

    def habla_encima() -> None:
        if oido.altavoz.empezados == 0:
            oido.micro.capta(eco(voz("Espera")))

    oido.altavoz.al_sonar = habla_encima

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert oido.charla.cortadas == [oido.charla.operaciones[0]]
    assert oido.eventos.index("calla") < oido.eventos.index("deja de escribir")
    assert turno.reply is not None
    assert "Una frase. Otra frase. Y otra. Y más. Y ya.".startswith(turno.reply)
    assert "Y ya." not in turno.reply
    assert oido.dicho() == ["Una frase."]
    assert oido.charla.cortes == [(7, "Una frase.")]


def test_si_no_se_puede_dejar_de_escribir_la_respuesta_acaba_entera_y_el_diario_dice_el_tipo(
    caplog: pytest.LogCaptureFixture,
) -> None:
    oido = _oido_con_cancelador()
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra. ", "Y más. ", "Y ya."]
    oido.charla.falla_al_cortar = RuntimeError("Una frase secreta.")

    def habla_encima() -> None:
        if oido.altavoz.empezados == 0:
            oido.micro.capta(eco(voz("Espera")))

    oido.altavoz.al_sonar = habla_encima

    with caplog.at_level(logging.ERROR, logger="sirius"):
        (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    # Como antes de ADR-254: calla, la charla acaba la respuesta y se apunta lo que se oyó.
    assert turno.reply == "Una frase. Otra frase. Y otra. Y más. Y ya."
    assert oido.dicho() == ["Una frase."]
    assert oido.charla.cortes == [(7, "Una frase.")]
    assert "No se pudo cortar la respuesta (RuntimeError)" in caplog.text
    assert "secreta" not in caplog.text


def test_si_le_hablan_mientras_piensa_no_empieza_a_hablar_encima() -> None:
    oido = _oido_con_cancelador()
    oido.charla.al_enviar = lambda: oido.micro.capta(voz("Y otra cosa"))

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert turno.reply == "R: Cuéntame"
    assert oido.dicho() == []
    assert oido.charla.cortes == [(7, "")]


def test_lo_que_se_cierra_mientras_contesta_va_a_la_charla_cuando_acaba() -> None:
    oido = _oido_con_cancelador()
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra."]
    dicho_encima: list[bool] = []

    def habla_encima() -> None:
        if not dicho_encima:
            dicho_encima.append(True)
            oido.micro.capta(eco(voz("Espera")), FIN)

    oido.altavoz.al_sonar = habla_encima

    atendido = oido.suena(voz("Cuéntame"), FIN)

    assert [t.heard for t in atendido.turns] == ["Cuéntame", "Espera"]
    assert oido.charla.mensajes == ["Cuéntame", "Espera"]


def test_la_charla_empieza_con_el_primer_trozo_que_capta_sin_su_voz() -> None:
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))
    oido.altavoz.sigue_sonando = True
    oido.suena(voz("Sirius, cuéntame"), FIN)
    # Habla un buen rato: lo que capta el micro mientras tanto lleva su eco.
    oido.reloj.avanza(30)
    oido.suena(eco(), eco())
    oido.altavoz.sigue_sonando = False
    oido.reloj.avanza(1)
    oido.micro.capta("")
    oido.reloj.avanza(5)

    (turno,) = oido.suena(voz("Y otra cosa"), FIN).turns

    # A 5 s de que el micro dejara de captar su voz: dentro de la charla, sin su nombre.
    assert turno.addressed
    oido.reloj.avanza(11)
    (fuera,) = oido.suena(voz("Y otra más"), FIN).turns
    assert not fuera.addressed


def test_lo_que_le_dijo_encima_es_para_el_aunque_se_lea_cuando_ya_ha_callado() -> None:
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))

    def habla_encima() -> None:
        # Mientras suena la frase, el propietario le habla encima; el oído lo leerá
        # cuando la charla acabe, y para entonces ya ha callado.
        oido.micro.capta(eco(voz("Espera")))
        oido.reloj.avanza(1)

    oido.altavoz.al_sonar = habla_encima
    oido.suena(voz("Sirius, cuéntame"), FIN)
    oido.altavoz.al_sonar = None

    (turno,) = oido.suena(FIN).turns

    assert (turno.heard, turno.addressed) == ("Espera", True)


def test_parar_mientras_aun_suena_lo_que_dijo_empieza_la_charla_al_parar() -> None:
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))
    oido.altavoz.sigue_sonando = True
    oido.suena(voz("Sirius, cuéntame"), FIN)
    oido.reloj.avanza(30)

    oido.servicio.stop()
    oido.servicio.start()
    oido.reloj.avanza(5)

    (turno,) = oido.suena(voz("Otra cosa"), FIN).turns
    assert turno.addressed


def test_si_falla_el_cancelador_deja_de_oir_y_lo_dice() -> None:
    oido = _oido_con_cancelador()
    oido.cancelador.falla = RuntimeError("roto")

    atendido = oido.suena(voz("Hola"), FIN)

    assert atendido.notice == "No puedo oírte: la cancelación de eco ha fallado (RuntimeError)."
    assert not oido.servicio.listening
    assert oido.charla.mensajes == []


def test_si_no_se_puede_apuntar_el_corte_el_diario_solo_dice_el_tipo(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    oido = _oido_con_cancelador()
    oido.altavoz.sigue_sonando = True
    oido.charla.trozos = ["Una frase secreta."]
    oido.charla.falla_al_apuntar = RuntimeError("Una frase secreta.")
    oido.suena(voz("Cuéntame"), FIN)

    with caplog.at_level(logging.INFO, logger="sirius"):
        oido.suena(eco(voz("Espera")), FIN)

    assert "No se pudo apuntar hasta dónde se oyó (RuntimeError)" in caplog.text
    assert "secreta" not in caplog.text
    assert oido.charla.mensajes == ["Cuéntame", "Espera"]


def test_le_corta_aunque_le_hable_en_una_pausa_de_lo_que_aun_le_queda_por_decir() -> None:
    # Entre frase y frase su voz no está en el aire, pero sigue contestando: le corta igual.
    oido = _oido_con_cancelador()
    oido.altavoz.sigue_sonando = True
    oido.suena(voz("Cuéntame"), FIN)

    oido.suena(voz("Espera"))

    assert oido.eventos[-2:] == ["calla", "corte:7:R: Cuéntame"]


def test_lo_que_le_corta_mientras_escribe_es_para_el_aunque_la_charla_tarde_en_acabar() -> None:
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra."]

    def habla_encima() -> None:
        if oido.altavoz.empezados == 0:
            oido.micro.capta(eco(voz("Espera")))

    oido.altavoz.al_sonar = habla_encima
    # La charla tarda: entre trozo y trozo pasan 6 s, y acaba mucho después del corte.
    oido.charla.al_escribir = lambda _trozo: oido.reloj.avanza(6)
    oido.suena(voz("Sirius, cuéntame"), FIN)
    oido.altavoz.al_sonar = None
    oido.charla.al_escribir = None

    (turno,) = oido.suena(FIN).turns

    assert (turno.heard, turno.addressed) == ("Espera", True)


def _con_su_respuesta_aun_sonando(oido: _Oido) -> None:
    """Le pregunta con su nombre y contesta; su voz sigue sonando, y su eco vuelve."""
    oido.altavoz.sigue_sonando = True
    oido.suena(voz("Sirius, cuéntame"), FIN)
    oido.suena(eco(), eco())


def test_si_tarda_en_hablarle_despues_de_callar_ya_no_es_de_la_charla() -> None:
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))
    _con_su_respuesta_aun_sonando(oido)
    oido.altavoz.sigue_sonando = False
    # Ya calló: el micro sigue captando, sin su voz.
    oido.suena("")
    oido.reloj.avanza(11)

    (turno,) = oido.suena(voz("Y otra cosa"), FIN).turns

    assert not turno.addressed


def test_la_charla_cuenta_desde_que_el_micro_capta_sin_su_voz_aunque_lo_lea_tarde() -> None:
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))
    _con_su_respuesta_aun_sonando(oido)
    oido.altavoz.sigue_sonando = False
    oido.micro.capta("")
    oido.reloj.avanza(2)
    oido.micro.capta(voz("Y otra cosa"), FIN)
    # El oído lo lee todo diez segundos después: la charla cuenta desde que lo captó.
    oido.reloj.avanza(10)

    (turno,) = oido.servicio.attend().turns

    assert turno.addressed


def test_si_le_dice_dos_cosas_mientras_la_charla_escribe_las_dos_son_para_el() -> None:
    # La charla empieza con el primer corte, y lo que le dice mientras la charla escribe
    # cae dentro. Contestar a lo primero le hace callar otra vez después de que empezara lo
    # segundo: si es de la charla se decide al cerrarse, no al ir a ella.
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra. ", "Y más."]
    dicho_encima: list[bool] = []

    def habla_encima() -> None:
        if not dicho_encima:
            dicho_encima.append(True)
            oido.micro.capta(eco(voz("Espera")), FIN)

    def sigue_hablando(trozo: str) -> None:
        oido.reloj.avanza(2)
        if trozo == "Y otra. ":
            oido.micro.capta(voz("Y cuéntame otra cosa"), FIN)

    oido.altavoz.al_sonar = habla_encima
    oido.charla.al_escribir = sigue_hablando

    atendido = oido.suena(voz("Sirius, cuéntame"), FIN)

    assert [(t.heard, t.addressed) for t in atendido.turns] == [
        ("Sirius, cuéntame", True),
        ("Espera", True),
        ("Y cuéntame otra cosa", True),
    ]


def test_lo_que_le_dice_mientras_la_charla_escribe_no_alarga_la_charla() -> None:
    # Calló con el primer corte, y la charla dura desde ahí: lo que siga diciéndole
    # mientras la charla escribe no le hace callar otra vez. Desde ADR-254, al cortarle la
    # charla deja de escribir; aquí cortarla falla, y sigue escribiendo como antes.
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra. ", "Y más. ", "Y ya."]
    oido.charla.falla_al_cortar = RuntimeError("no se deja cortar")
    dicho_encima: list[bool] = []

    def habla_encima() -> None:
        if not dicho_encima:
            dicho_encima.append(True)
            oido.micro.capta(eco(voz("Espera")), FIN)

    def sigue_hablando(trozo: str) -> None:
        oido.reloj.avanza(4)
        if trozo == "Otra frase. ":
            oido.micro.capta(voz("Y cuéntame otra cosa"), FIN)
        if trozo == "Y más. ":
            oido.micro.capta(voz("Y otra más"), FIN)

    oido.altavoz.al_sonar = habla_encima
    oido.charla.al_escribir = sigue_hablando

    atendido = oido.suena(voz("Sirius, cuéntame"), FIN)

    # A 8 s del corte, dentro; a 16 s, fuera, aunque a 8 s de lo anterior.
    assert [(t.heard, t.addressed) for t in atendido.turns] == [
        ("Sirius, cuéntame", True),
        ("Espera", True),
        ("Y cuéntame otra cosa", True),
        ("Y otra más", False),
    ]


# --- Ronda 1 de Codex sobre la PR #690 ---------------------------------------------------


def test_le_corta_aunque_le_hable_cuando_la_charla_ya_escribio_y_hace_lo_de_despues() -> None:
    # Después de escribir, la charla puede seguir con lo de después del turno, como resumir,
    # que es otra llamada al modelo: el micro se lee también entonces, y le calla en cuanto
    # le habla, sin esperar a que acabe.
    oido = _oido_con_cancelador()
    oido.altavoz.sigue_sonando = True

    def le_habla() -> None:
        oido.micro.capta(eco(voz("Espera")))
        oido.lector.lee()

    oido.charla.al_acabar = le_habla
    oido.suena(voz("Cuéntame"), FIN)

    assert oido.eventos.index("calla") < oido.eventos.index("después del turno")
    assert oido.charla.cortes == [(7, "R: Cuéntame")]


def test_le_corta_mientras_piensa_aunque_la_charla_tarde_en_escribir() -> None:
    # Antes de la primera frase el modelo puede tardar: el micro se lee igual, y la
    # respuesta no empieza a sonar encima.
    oido = _oido_con_cancelador()

    def le_habla() -> None:
        oido.micro.capta(voz("Espera"))
        oido.lector.lee()

    oido.charla.al_enviar = le_habla
    oido.suena(voz("Cuéntame"), FIN)

    # Y la charla deja de escribir antes de escribir nada (ADR-254).
    assert oido.eventos.index("calla") < oido.eventos.index("deja de escribir")
    assert not any(evento.startswith("escribe:") for evento in oido.eventos)
    assert oido.dicho() == []


def test_el_hilo_que_lee_mientras_contesta_va_con_cancelador_y_para_con_la_charla() -> None:
    sin = _Oido()
    sin.servicio.start()
    sin.suena(voz("Hola"), FIN)
    assert sin.lector.arranques == 0

    con = _oido_con_cancelador()
    con.suena(voz("Hola"), FIN)
    assert (con.lector.arranques, con.lector.paradas) == (1, 1)
    # También si la charla se rompe a medias.
    con.charla.falla = RuntimeError("rota")
    con.suena(voz("Otra"), FIN)
    assert (con.lector.arranques, con.lector.paradas) == (2, 2)


def test_el_hilo_que_lee_mientras_contesta_mira_el_micro_hasta_que_para() -> None:
    vueltas: list[int] = []
    dos = threading.Event()

    def oye() -> None:
        vueltas.append(1)
        if len(vueltas) >= 2:
            dos.set()

    lector = read_meanwhile(oye)
    try:
        assert dos.wait(2), "no miró el micro dos veces en 2 s"
    finally:
        lector.stop()
    hechas = len(vueltas)
    time.sleep(0.1)
    assert len(vueltas) == hechas, "siguió mirando después de parar"


def test_si_falla_mirar_el_micro_mientras_contesta_deja_de_mirar_y_el_diario_dice_el_tipo(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    vueltas: list[int] = []

    def oye() -> None:
        vueltas.append(1)
        raise RuntimeError("Una frase secreta.")

    with caplog.at_level(logging.ERROR, logger="sirius"):
        lector = read_meanwhile(oye)
        time.sleep(0.2)
        lector.stop()

    assert vueltas == [1]
    assert "dejó de mirar el micro mientras contestaba (RuntimeError)" in caplog.text
    assert "secreta" not in caplog.text


def _dos_turnos_y_lo_primero_aun_suena() -> _Oido:
    """Dos turnos se cierran mientras la charla contesta: le corta, «Espera», y sigue,
    «Y cuéntame otra cosa». Contesta al primero, y su respuesta se queda sonando."""
    oido = _oido_con_cancelador(a_quien=Addressing(conversation_seconds=10.0))
    oido.charla.trozos = ["Una frase. ", "Otra frase. ", "Y otra. ", "Y más."]
    dicho_encima: list[bool] = []

    def habla_encima() -> None:
        if not dicho_encima:
            dicho_encima.append(True)
            oido.micro.capta(eco(voz("Espera")), FIN, voz("Y cuéntame otra cosa"), FIN)

    def contesta() -> None:
        if oido.charla.mensajes[-1] == "Espera":
            oido.altavoz.sigue_sonando = True

    oido.altavoz.al_sonar = habla_encima
    oido.charla.al_enviar = contesta

    atendido = oido.suena(voz("Sirius, cuéntame"), FIN)

    # Mientras suena lo que contestó a «Espera», no contesta al segundo.
    assert [t.heard for t in atendido.turns] == ["Sirius, cuéntame", "Espera"]
    assert oido.charla.mensajes == ["Sirius, cuéntame", "Espera"]
    oido.altavoz.al_sonar = None
    return oido


def test_no_contesta_lo_siguiente_mientras_suena_lo_anterior_y_el_corte_es_de_lo_que_sonaba() -> (
    None
):
    # Así nunca hay dos respuestas en el altavoz, y si le cortan, el corte se apunta en la
    # que sonaba, con lo que se oyó de ella (ronda 1 de Codex sobre la PR #690).
    oido = _dos_turnos_y_lo_primero_aun_suena()

    # Le corta mientras suena la respuesta a «Espera»: se apunta en ella, y lo que esperaba
    # va antes que lo que le acaba de decir.
    despues = oido.suena(eco(voz("Para")), FIN)

    assert oido.charla.cortes == [(7, "Una frase."), (8, "R: Espera")]
    assert [(t.heard, t.addressed) for t in despues.turns] == [
        ("Y cuéntame otra cosa", True),
        ("Para", True),
    ]


def test_lo_que_esperaba_va_en_cuanto_calla_lo_anterior() -> None:
    oido = _dos_turnos_y_lo_primero_aun_suena()
    oido.altavoz.sigue_sonando = False

    # En cuanto el micro capta sin su voz, ya calló: va lo que esperaba.
    assert [t.heard for t in oido.suena("").turns] == ["Y cuéntame otra cosa"]


# --- Al salir (ADR-252) -----------------------------------------------------------------


def test_al_cerrar_para_y_suelta_la_voz_con_su_altavoz() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.suena(voz("Hola"), FIN)

    oido.servicio.close()

    # El altavoz se suelta, y con él la cancelación de eco, que va dentro.
    assert oido.eventos[-1] == "suelta"
    assert not oido.servicio.listening
    # Si vuelve a escuchar, carga la voz otra vez.
    assert oido.servicio.start() == ""
    assert oido.cargas_de_la_voz == 2


def test_cerrar_sin_haber_escuchado_no_carga_ni_suelta_nada() -> None:
    oido = _Oido()

    oido.servicio.close()

    assert oido.eventos == []
    assert oido.cargas_de_la_voz == 0


# --- Cambiar de voz (pieza F, ADR-246) ------------------------------------------------


def _voz_nueva(oido: _Oido) -> list[str]:
    """La voz que dirán los ajustes desde ahora, con su altavoz: lo que hagan va aparte."""
    nuevos: list[str] = []
    oido.voz = _Voz(nuevos)
    oido.altavoz = _Altavoz(nuevos)
    return nuevos


def test_al_cambiar_de_voz_suelta_la_de_antes_y_el_turno_siguiente_habla_con_la_nueva() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.suena(voz("Hola"), FIN)
    nuevos = _voz_nueva(oido)

    assert oido.servicio.reload_voice() == ""

    # Paró, soltó el altavoz de antes y volvió a escuchar, ya con la voz nueva.
    assert oido.eventos[-2:] == ["suelta", "abre"]
    assert oido.servicio.listening
    assert oido.cargas_de_la_voz == 2
    antes = len(oido.eventos)
    oido.suena(voz("Otra"), FIN)
    assert [e for e in nuevos if e.startswith(("di:", "suena:"))] == [
        "di:R: Otra",
        "suena:sonido de R: Otra",
    ]
    assert not [e for e in oido.eventos[antes:] if e.startswith(("di:", "suena:"))]


def test_avisa_justo_antes_de_cargar_la_voz_y_solo_cuando_la_carga() -> None:
    """La ventana carga la voz al abrirse, y con la de personaje no sale hasta que acaba:
    quien lo dice por la consola se entera antes de que empiece a cargarla (ADR-253)."""
    oido = _Oido()
    avisos: list[int] = []
    oido.servicio.before_loading_voice(lambda: avisos.append(oido.cargas_de_la_voz))

    oido.servicio.start()
    oido.servicio.stop()
    oido.servicio.start()

    assert avisos == [0], "una vez, con la voz aún por cargar"
    _voz_nueva(oido)
    oido.servicio.reload_voice()
    assert avisos == [0, 1]


def test_sin_escuchar_cambiar_de_voz_no_abre_el_micro_y_la_nueva_se_carga_al_escuchar() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.servicio.stop()
    _voz_nueva(oido)

    assert oido.servicio.reload_voice() == ""

    assert not oido.servicio.listening
    assert oido.cargas_de_la_voz == 1
    assert oido.servicio.start() == ""
    assert oido.cargas_de_la_voz == 2


def test_callado_cambiar_de_voz_no_lo_abre_y_al_quitar_el_silencio_habla_con_la_nueva() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.servicio.mute()
    _voz_nueva(oido)

    oido.servicio.reload_voice()

    assert not oido.servicio.listening
    assert oido.servicio.unmute() == ""
    assert oido.cargas_de_la_voz == 2


def test_cambiar_de_voz_antes_de_escuchar_no_carga_nada() -> None:
    oido = _Oido()

    assert oido.servicio.reload_voice() == ""

    assert oido.cargas_de_la_voz == 0
    assert oido.eventos == []


def test_si_la_voz_nueva_no_carga_lo_dice_y_no_escucha() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.falla_al_cargar_la_voz = VoiceUnavailable("la voz de personaje no carga (sin memoria)")

    aviso = oido.servicio.reload_voice()

    assert "No puedo hablarte: la voz de personaje no carga (sin memoria)." in aviso
    assert oido.instalacion.install_command in aviso
    assert not oido.servicio.listening


# --- Pieza B de la 0.4: lo que la cara lee del oído (ADR-260) ---


def test_la_cara_lee_lo_fuerte_que_habla_aunque_la_charla_tenga_el_cerrojo() -> None:
    oido = _Oido()
    assert oido.servicio.speaking_level == 0.0, "sin la voz cargada, callado"
    oido.servicio.start()
    oido.altavoz.nivel = 0.6
    assert oido.servicio.speaking_level == 0.6
    assert oido.servicio.clock is oido.reloj, "la cara vive con el reloj de la charla"

    # La charla tiene el cerrojo todo lo que tarda el modelo: la cara no lo espera.
    cogido, suelta = threading.Event(), threading.Event()

    def coge() -> None:
        with oido.servicio._lock:
            cogido.set()
            suelta.wait(5)

    hilo = threading.Thread(target=coge)
    hilo.start()
    assert cogido.wait(5)
    try:
        empieza = time.monotonic()
        assert oido.servicio.speaking_level == 0.6
        assert time.monotonic() - empieza < 1.0
    finally:
        suelta.set()
        hilo.join()


# --- Pieza C de la 0.4: los gestos de lo que dice, con su frase (ADR-261) ---


def test_cada_gesto_va_con_su_frase_y_se_hace_cuando_esa_empieza_a_sonar() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = [
        "Vale. ",
        Gesture("sonrisa"),
        "Me parece bien. Hombre, ",
        Gesture("ceja_arriba"),
        "eso ya. Adiós.",
    ]
    oido.altavoz.en_cola = True

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert oido.dicho() == ["Vale.", "Me parece bien.", "Hombre, eso ya.", "Adiós."]
    assert turno.reply == "Vale. Me parece bien. Hombre, eso ya. Adiós."
    operacion = turno.operation_id
    sonando = []
    for empezados in range(5):
        oido.altavoz.empezados = empezados
        sonando.append(oido.servicio.speaking_gestures)
    assert sonando == [
        (operacion, ()),
        (operacion, ()),
        (operacion, ("sonrisa",)),
        (operacion, ("sonrisa", "ceja_arriba")),
        (operacion, ("sonrisa", "ceja_arriba")),
    ]


@pytest.mark.parametrize("final", ["Claro.", "Claro. "])
def test_un_gesto_del_final_va_con_la_ultima_frase_y_no_se_dice(final: str) -> None:
    # Pegado a la frase, la marca sale con ella; tras un blanco, sale sola y sin nada que
    # decir, como tras un bloque de código al final.
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = [final, Gesture("guino")]

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert oido.dicho() == ["Claro."]
    assert oido.servicio.speaking_gestures == (turno.operation_id, ("guino",))


def test_el_gesto_de_lo_que_no_llega_a_sonar_no_se_hace() -> None:
    oido = _oido_con_cancelador()
    oido.charla.trozos = ["Una frase. ", Gesture("sonrisa"), "Otra frase. ", "Y otra."]
    oido.altavoz.sigue_sonando = True
    # Las frases esperan en la cola del altavoz, y solo la primera empieza a sonar.
    oido.altavoz.en_cola = True
    oido.suena(voz("Cuéntame"), FIN)
    oido.altavoz.empezados = 1

    oido.suena(eco(voz("Espera")))

    assert oido.charla.cortes == [(7, "Una frase.")]
    assert oido.servicio.speaking_gestures[1] == ()


def test_las_marcas_de_los_gestos_no_se_pueden_escribir_desde_la_charla() -> None:
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = [f"Hola {gesture_mark(0)}ami{gesture_mark(7)}go.", Gesture("guino")]

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert oido.dicho() == ["Hola amigo."]
    assert oido.servicio.speaking_gestures == (turno.operation_id, ("guino",))


def test_un_gesto_que_se_pierde_dentro_de_un_codigo_no_cambia_el_de_los_demas() -> None:
    # Un bloque de código no se dice, y la marca que cae dentro se pierde con él.
    oido = _Oido()
    oido.servicio.start()
    oido.charla.trozos = [
        "Mira:\n\n    codigo ",
        Gesture("sonrisa"),
        "aqui\n\nY luego ",
        Gesture("guino"),
        "más.",
    ]

    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    assert "Y luego más." in oido.dicho()
    assert oido.servicio.speaking_gestures == (turno.operation_id, ("guino",))


def test_la_cara_lee_los_gestos_aunque_la_charla_tenga_el_cerrojo() -> None:
    oido = _Oido()
    oido.servicio.start()
    antes = oido.servicio.speaking_gestures
    assert antes == ("", ()), "sin haber dicho nada, ninguno"
    oido.charla.trozos = [Gesture("asiente"), "Sí."]
    (turno,) = oido.suena(voz("Cuéntame"), FIN).turns

    cogido, suelta = threading.Event(), threading.Event()

    def coge() -> None:
        with oido.servicio._lock:
            cogido.set()
            suelta.wait(5)

    hilo = threading.Thread(target=coge)
    hilo.start()
    assert cogido.wait(5)
    try:
        empieza = time.monotonic()
        assert oido.servicio.speaking_gestures == (turno.operation_id, ("asiente",))
        assert time.monotonic() - empieza < 1.0
    finally:
        suelta.set()
        hilo.join()


# --- Lo que ve: si le miran y en qué está (pieza D de la 0.4, ADR-262) ----------------


class _Vista:
    """Hace de la vista: dice si desde un momento quien habla le mira, y apunta desde
    cuándo le preguntan."""

    def __init__(self, *, le_miran: bool) -> None:
        self.le_miran = le_miran
        self.desde: list[float] = []

    def __call__(self, since: float) -> bool:
        self.desde.append(since)
        return self.le_miran


def _oido_que_ve(vista: _Vista) -> _Oido:
    oido = _Oido(a_quien=Addressing(conversation_seconds=10.0), mira=vista)
    oido.servicio.start()
    return oido


def test_sin_su_nombre_ni_charla_es_para_el_si_quien_habla_le_mira() -> None:
    oido = _oido_que_ve(_Vista(le_miran=True))

    (turno,) = oido.suena(voz("¿Qué hora es?"), FIN).turns

    assert turno.addressed
    assert oido.charla.mensajes == ["¿Qué hora es?"]


def test_sin_su_nombre_ni_charla_ni_mirarle_no_es_para_el() -> None:
    oido = _oido_que_ve(_Vista(le_miran=False))

    (turno,) = oido.suena(voz("¿Qué hora es?"), FIN).turns

    assert not turno.addressed
    assert oido.charla.mensajes == []


def test_cuenta_que_le_mira_desde_un_segundo_antes_de_empezar_a_oirse_su_voz() -> None:
    # Quien le habla a alguien suele mirarle al empezar, y la cámara puede verlo antes de
    # que el detector oiga la voz.
    vista = _Vista(le_miran=False)
    oido = _oido_que_ve(vista)
    empieza = oido.reloj.ahora

    oido.micro.capta(voz("¿Qué hora es?"))
    oido.servicio.attend()
    oido.reloj.avanza(2.5)
    oido.suena(FIN)

    assert LOOK_BEFORE_SECONDS == 1.0
    assert vista.desde == [empieza - LOOK_BEFORE_SECONDS]


def test_sin_vista_un_turno_sin_su_nombre_no_es_para_el() -> None:
    oido = _oido_que_elige()

    (turno,) = oido.suena(voz("¿Qué hora es?"), FIN).turns

    assert not turno.addressed


def test_la_cara_sabe_si_oye_piensa_habla_o_nada() -> None:
    oido = _Oido()
    oido.servicio.start()
    fases: list[VoicePhase] = [oido.servicio.phase]
    oido.altavoz.sigue_sonando = True

    def al_enviar() -> None:
        fases.append(oido.servicio.phase)

    def al_acabar() -> None:
        fases.append(oido.servicio.phase)

    oido.charla.al_enviar = al_enviar
    oido.charla.al_acabar = al_acabar
    oido.charla.trozos = ["Son las tres. ", "Y diez."]
    oido.micro.capta(voz("¿Qué hora es?"))
    oido.servicio.attend()
    fases.append(oido.servicio.phase)
    oido.suena(FIN)
    fases.append(oido.servicio.phase)
    oido.altavoz.sigue_sonando = False
    fases.append(oido.servicio.phase)

    assert fases == [
        VoicePhase.QUIET,
        VoicePhase.HEARING,
        VoicePhase.THINKING,
        VoicePhase.SPEAKING,
        VoicePhase.SPEAKING,
        VoicePhase.QUIET,
    ]


def test_lo_que_no_dice_en_voz_alta_no_es_hablar() -> None:
    # Sin decir nada, al acabar la charla no habla: vuelve a nada.
    oido = _Oido()
    oido.servicio.start()
    oido.altavoz.sigue_sonando = True
    oido.charla.trozos = [""]

    oido.suena(voz("Hmm"), FIN)

    assert oido.servicio.phase is VoicePhase.QUIET


def test_la_cara_lee_en_que_esta_aunque_la_charla_tenga_el_cerrojo() -> None:
    oido = _Oido()
    oido.servicio.start()
    cogido, suelta = threading.Event(), threading.Event()

    def coge() -> None:
        with oido.servicio._lock:
            cogido.set()
            suelta.wait(5)

    hilo = threading.Thread(target=coge)
    hilo.start()
    assert cogido.wait(5)
    try:
        empieza = time.monotonic()
        assert oido.servicio.phase is VoicePhase.QUIET
        assert time.monotonic() - empieza < 1.0
    finally:
        suelta.set()
        hilo.join()
