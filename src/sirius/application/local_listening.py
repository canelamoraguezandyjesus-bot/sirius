"""Oír y hablar en local: lo que el propietario dice por el micro entra en la charla, y
Sirius lo contesta en voz alta (ADR-242, ADR-243).

Las piezas B y C de la 0.3 (ADR-241). El servicio lee lo que ha llegado al micro,
pregunta al detector de turno por cada trozo y, cuando el detector da el turno por
acabado, lo transcribe y le pasa el texto a la misma charla que la ventana
(``SendMessageUseCase.send_message``): la misma semilla, la misma memoria y las mismas
órdenes, «olvida eso» incluida. Mientras la charla escribe la respuesta, la dice frase a
frase desde la primera, con la voz y el altavoz.

- **No espera.** ``attend`` atiende lo que ya ha llegado y vuelve; quien lo llama, la
  orden de consola o la ventana, decide cada cuánto.
- **No guarda audio.** Los trozos del turno viven en memoria hasta cerrarlo, y el
  diario no recibe nada de lo oído: «olvida eso» no podría borrarlo de ahí.
- **Sin el oído instalado no hace nada.** Antes de abrir el micro mira que esté todo en
  este ordenador; si falta algo, devuelve el aviso con la orden que lo instala, no abre
  el micro, no contesta y no baja nada (PA-R03-08).
- **La orden no se promete como arreglo.** Se aconseja para lo que ella toca, lo que falta
  y lo que no carga, y el aviso dice lo que hace siempre: instala o pone al día lo que
  falte y, si el problema es otro, dice cuál. Para el micro y el detector, que no toca, no
  se aconseja. Adivinar si la arreglaría salió mal en seis rondas de Codex sobre la PR
  #687 (2, 4, 5, 6, 7 y 8).
- **Lo oído solo va a una charla de este ordenador.** Si el modelo de la charla es de
  fuera (OpenAI, que Configuración sigue ofreciendo), no oye. Como la charla puede
  cambiar de modelo en marcha, cada turno se entrega pidiendo que no salga: la charla
  comprueba el mismo modelo con el que envía, leído una sola vez, y si es de fuera no
  guarda ni envía nada. Entonces el turno no sale, deja de escuchar y lo dice. Mirarlo
  también al cerrar el turno solo ahorra transcribirlo en balde (PA-R03-08, rondas 9 y
  10 de Codex sobre la PR #687).
- **Nada de lo que contesta la charla se queda por el camino.** El turno lleva lo que
  devolvió la charla, entero y sin traducir, el mismo resultado que recibe la ventana con
  lo escrito, y lo que el modelo propone recordar queda pendiente de que él lo confirme,
  como en la ventana (rondas 11, 12 y 13 de Codex sobre la PR #687).
- **Lo que falla dentro de un turno no tumba a quien escucha.** Como la ventana con lo
  escrito, cada envío lleva su operación, y si la charla lanza una excepción el turno lo
  dice con esa operación, para contar lo que quedó guardado, y se sigue oyendo. Si falla
  el detector o el modelo de oír, deja de oír y lo dice. El diario apunta solo el tipo de
  fallo (ronda 15 de Codex sobre la PR #687).
- **Dice lo que escribe, desde la primera frase.** Lo cerrado de lo que la charla va
  escribiendo pasa por ``SpeechCutter``, que lo prepara con la función de Model Studio, y
  cada frase se pide a la voz y suena en cuanto está. Desde la primera hasta que el
  altavoz acaba, el micro está cerrado: su propia voz no vuelve como un turno
  (PA-R03-03). Cortarle mientras habla es la pieza E.
- **Si la voz o el altavoz fallan, deja de hablar y lo dice.** El fallo no sale a la
  charla, que sigue escribiendo y guarda la respuesta entera; después deja de oír con su
  aviso, como si fallara el detector.
- **En la pieza B todo lo oído es para él**; a quién le hablan lo decide la pieza D.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from sirius.application.send_message import ChatLeavesThisComputer, SendMessageResult
from sirius.application.speech_cutter import SpeechCutter
from sirius.domain.conversation import MessageStatus
from sirius.infrastructure.logging import get_logger
from sirius.ports.llm import runs_on_this_computer
from sirius.ports.local_voice import (
    ListeningEngines,
    SpeakingEngines,
    TurnSignal,
    VoiceInstallation,
    VoiceUnavailable,
)

_logger = get_logger(__name__)

#: Cuántos trozos sin voz se guardan antes de que empiece un turno, para no cortarle la
#: primera sílaba: Silero da la voz por empezada un poco después de que empiece. Con los
#: trozos del micro de verdad, de 512 muestras a 16 kHz, son medio segundo.
PRE_ROLL_CHUNKS = 16
#: Lo que dice si la charla va a un modelo de fuera de este ordenador.
CHAT_LEAVES = (
    "No puedo oírte: la charla va ahora a un modelo de fuera de este ordenador, y lo que "
    "oigo no sale de aquí."
)


class Chat(Protocol):
    """La charla de Sirius, la misma que usa la ventana."""

    @property
    def llm_provider(self) -> object:
        """El modelo con el que conversa ahora, que puede cambiar en marcha."""
        ...

    def send_message(
        self,
        user_text: str,
        *,
        operation_id: str | None = None,
        on_delta: Callable[[str], None] | None = None,
        on_completed: Callable[[], None] | None = None,
        only_on_this_computer: bool = False,
    ) -> SendMessageResult:
        """Lo entrega a la charla con la operación ``operation_id``. Le pasa a ``on_delta``
        lo que va escribiendo y, si acaba bien, llama a ``on_completed`` en cuanto la
        respuesta está guardada, antes de lo que la charla hace después del turno. Con
        ``only_on_this_computer``, solo si el modelo con el que lo envía, el mismo que
        comprueba, es de este ordenador, y si no, ``ChatLeavesThisComputer`` sin guardar ni
        enviar nada."""
        ...


class MemorySuggestions(Protocol):
    """Donde queda lo que el modelo propone recordar, pendiente de que él lo confirme."""

    def propose(self, content: str, *, message_id: int | None = None) -> object:
        """Lo deja pendiente, ligado a la respuesta que lo propuso."""
        ...


@dataclass(frozen=True, slots=True)
class HeardTurn:
    """Un turno de voz cerrado: lo que oyó, si era para él, lo que contestó la charla y lo
    que el modelo propuso recordar.

    ``heard`` es lo oído, tal cual. Para enseñarlo está lo guardado,
    ``result.user_message``: tras «olvida lo de…» lo guardado ya no dice qué había que
    olvidar, y lo oído sí (ronda 14 de Codex sobre la PR #687).

    ``result`` es lo que devolvió la charla, entero y sin traducir: el mismo resultado que
    recibe la ventana con lo escrito, para que quien enseñe el turno lo enseñe como ella.
    Traducirlo a mano campo a campo perdió algo en tres rondas seguidas de Codex sobre la
    PR #687 (11, 12 y 13). Es ``None`` si la charla lanzó una excepción; entonces lo
    guardado es lo de ``operation_id``, la operación con la que se envió, como la ventana
    tras un envío roto (ronda 15). ``proposed`` es lo que el modelo propuso recordar y
    quedó pendiente de que él lo confirme.
    """

    heard: str
    addressed: bool
    result: SendMessageResult | None
    operation_id: str
    proposed: str | None = None
    #: Segundos desde que el detector dejó de oír su voz hasta que sonó la primera frase;
    #: ``None`` si no dijo nada. Es lo que mide E-R03-02.
    first_sound_delay: float | None = None

    @property
    def answered(self) -> bool:
        """Si la charla acabó bien."""
        return self.result is not None and self.result.outcome is MessageStatus.COMPLETED

    @property
    def reply(self) -> str:
        """Lo que escribió: entero si acabó bien, y si no, lo que llegara a escribir."""
        if self.result is None:
            return ""
        return self.result.sirius_message.content or ""


@dataclass(frozen=True, slots=True)
class Attended:
    """Lo que pasó al atender el micro: los turnos cerrados, en orden, y el aviso si no oye."""

    turns: tuple[HeardTurn, ...] = ()
    notice: str = ""


class LocalListening[Chunk]:
    """El oído y la voz del robot: del micro a la charla y de la charla al altavoz, todo en
    este ordenador."""

    def __init__(
        self,
        *,
        chat: Chat,
        installation: VoiceInstallation,
        load_engines: Callable[[], ListeningEngines[Chunk]],
        load_speaking: Callable[[], SpeakingEngines[Any]],
        memory_suggestions: MemorySuggestions,
        pre_roll: int = PRE_ROLL_CHUNKS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._chat = chat
        self._clock = clock
        self._memory_suggestions = memory_suggestions
        self._installation = installation
        self._load_engines = load_engines
        self._load_speaking = load_speaking
        self._engines: ListeningEngines[Chunk] | None = None
        self._speaking: SpeakingEngines[Any] | None = None
        #: El micro está cerrado porque Sirius habla; se abre cuando el altavoz acaba.
        self._paused_to_speak = False
        self._detector_stale = False
        self._listening = False
        self._notice = ""
        self._before_turn: deque[Chunk] = deque(maxlen=pre_roll)
        self._turn: list[Chunk] | None = None
        #: Cuándo dijo el detector por última vez que había voz: de ahí cuenta E-R03-02.
        self._voice_heard_at = 0.0

    @property
    def listening(self) -> bool:
        """Si el micro está abierto y Sirius atiende lo que llega."""
        return self._listening

    def start(self) -> str:
        """Abre el micro si el oído está instalado; devuelve el aviso si no puede, o vacío.

        Si ya escucha, no hace nada. Sin el oído instalado, no carga nada, no abre el
        micro y no baja nada: el aviso dice qué falta y qué orden lo instala.
        """
        if self._listening:
            return ""
        if not runs_on_this_computer(self._chat.llm_provider):
            _logger.info("El oído no arranca: la charla va a un modelo de fuera")
            return self._fail(CHAT_LEAVES)
        missing = self._installation.missing()
        if missing:
            _logger.info("El oído no arranca: falta %s", ", ".join(missing))
            problem = f"Para oírte y hablarte me falta instalar {_list(missing)} en este ordenador."
            return self._fail(problem, install=True)
        try:
            if self._engines is None:
                self._engines = self._load_engines()
                self._detector_stale = False
        except VoiceUnavailable as error:
            _logger.info("El oído no arranca: %s", error.reason)
            return self._fail(f"No puedo oírte: {error.reason}.", install=True)
        try:
            if self._speaking is None:
                self._speaking = self._load_speaking()
        except VoiceUnavailable as error:
            _logger.info("La voz no arranca: %s", error.reason)
            return self._fail(f"No puedo hablarte: {error.reason}.", install=True)
        if self._detector_stale:
            try:
                self._engines.detector.reset()
            except Exception as error:
                _logger.warning("El detector de voz sigue sin reiniciarse: %s", error)
                problem = f"No puedo oírte: el detector de voz no se ha podido reiniciar ({error})."
                return self._fail(problem)
            self._detector_stale = False
        try:
            self._engines.microphone.open()
        except VoiceUnavailable as error:
            _logger.info("El oído no arranca: %s", error.reason)
            return self._fail(f"No puedo oírte: {error.reason}.")
        self._listening = True
        self._notice = ""
        return ""

    def stop(self) -> None:
        """Cierra el micro y olvida el turno a medias, si lo había, también en el detector.

        Si no, al volver a escuchar el detector seguiría en el turno viejo: Silero
        creería que aún hay voz y el silencio siguiente abriría un turno sin palabras
        (ronda 1 de Codex sobre la PR #687).

        Si hablaba, se calla: el altavoz tira lo que le quedaba por decir.

        Nada de lo que falle aquí deja a Sirius oyendo ni suelta una pieza: el estado se
        limpia antes, el micro garantiza que al cerrarse no da más audio, y si el detector
        no se puede reiniciar se apunta, y el siguiente ``start`` lo vuelve a intentar y,
        si sigue sin poder, lo dice como aviso en vez de abrir el micro (rondas 2 y 3).
        """
        engines = self._engines
        # Mientras habla, el micro ya está cerrado.
        microphone_open = self._listening and not self._paused_to_speak
        self._listening = False
        self._paused_to_speak = False
        self._turn = None
        self._before_turn.clear()
        if self._speaking is not None:
            self._speaking.speaker.stop()
        if engines is None:
            return
        try:
            if microphone_open:
                engines.microphone.close()
        finally:
            try:
                engines.detector.reset()
            except Exception as error:
                _logger.warning("El detector de voz no se ha podido reiniciar al parar: %s", error)
                self._detector_stale = True

    def attend(self) -> Attended:
        """Atiende todo lo que ha llegado al micro y devuelve los turnos que cerró.

        Cada trozo se le enseña al detector una vez y en orden; cuando dice que el turno
        ha acabado, se transcribe el turno entero y el texto va a la charla. Sin escuchar,
        no lee el micro y devuelve el aviso de por qué.
        """
        if not self._listening or self._engines is None:
            return Attended(notice=self._notice)
        if self._paused_to_speak and not self._resume_listening():
            # Sigue hablando: con el micro cerrado no hay nada que leer.
            return Attended(notice="" if self._listening else self._notice)
        microphone = self._engines.microphone
        turns: list[HeardTurn] = []
        while (
            self._listening
            and not self._paused_to_speak
            and (chunk := microphone.read()) is not None
        ):
            turn = self._take(chunk)
            if turn is not None:
                turns.append(turn)
        return Attended(turns=tuple(turns), notice="" if self._listening else self._notice)

    def _take(self, chunk: Chunk) -> HeardTurn | None:
        """Le enseña ``chunk`` al detector y, si con él acaba el turno, lo atiende."""
        assert self._engines is not None
        try:
            signal = self._engines.detector.listen(chunk)
        except Exception as error:
            self._engine_failed("el detector de voz", error)
            return None
        if signal is TurnSignal.VOICE:
            self._voice_heard_at = self._clock()
        if self._turn is None:
            if signal is TurnSignal.VOICE:
                self._turn = [*self._before_turn, chunk]
                self._before_turn.clear()
            else:
                self._before_turn.append(chunk)
            return None
        self._turn.append(chunk)
        if signal is not TurnSignal.ENDED:
            return None
        chunks, self._turn = self._turn, None
        if not runs_on_this_computer(self._chat.llm_provider):
            # La charla ya se fue a un modelo de fuera: ni se transcribe.
            del chunks
            self._chat_left()
            return None
        try:
            heard = self._engines.transcriber.transcribe(chunks).strip()
        except Exception as error:
            self._engine_failed("el modelo de oír", error)
            return None
        finally:
            del chunks
        if not heard:
            _logger.info("Turno de voz sin palabras: no va a la charla")
            return None
        # La operación la pone el oído, como la ventana: si la charla se rompe a medias,
        # con ella se sabe qué quedó guardado de este turno.
        operation_id = str(uuid.uuid4())
        assert self._speaking is not None
        speech = _Speech(self._speaking, before_first=self._pause_to_speak, clock=self._clock)
        voice_heard_at = self._voice_heard_at
        try:
            # Lo que quedaba sin cerrar se dice en cuanto la respuesta acaba bien, sin esperar
            # a lo que la charla hace después del turno; si no acaba bien, lo escrito a
            # medias no se dice.
            result = self._chat.send_message(
                heard,
                operation_id=operation_id,
                on_delta=speech.hear,
                on_completed=speech.finish,
                only_on_this_computer=True,
            )
        except ChatLeavesThisComputer:
            # Se fue mientras se transcribía: la charla no ha guardado ni enviado nada.
            self._chat_left()
            return None
        except Exception as error:
            # La frontera de la ventana con lo escrito (`SendMessageWorker`): se cuenta,
            # no tumba a quien escucha, y el diario se queda solo con el tipo.
            _logger.error(
                "Turno de voz %s interrumpido por una excepción (%s)",
                operation_id,
                type(error).__name__,
            )
            self._after_speaking(speech)
            return HeardTurn(heard=heard, addressed=True, result=None, operation_id=operation_id)
        _logger.info("Turno de voz entregado a la charla")
        self._after_speaking(speech)
        delay = None
        if speech.first_sound_at is not None:
            delay = speech.first_sound_at - voice_heard_at
            # Solo la cifra: el diario no se queda con nada de lo oído ni de lo dicho.
            _logger.info("Turno de voz: primer sonido a %d ms de dejar de oír su voz", delay * 1000)
        proposed = None
        if result.outcome is MessageStatus.COMPLETED and result.memory_suggestion is not None:
            proposed = self._propose(result.memory_suggestion, result.sirius_message.id)
        return HeardTurn(
            heard=heard,
            addressed=True,
            result=result,
            operation_id=operation_id,
            proposed=proposed,
            first_sound_delay=delay,
        )

    def _propose(self, suggestion: str, message_id: int) -> str | None:
        """Deja pendiente lo que el modelo propone recordar, como la ventana con lo escrito.

        Lo hace quien envía, no la charla: proponer es una llamada aparte, nunca un efecto
        de enviar. Si falla, el turno ya contestado no se pierde, y el diario apunta solo
        el tipo de fallo, nada de lo propuesto.
        """
        try:
            self._memory_suggestions.propose(suggestion, message_id=message_id)
        except Exception as error:
            _logger.error("No se pudo proponer lo que recordar (%s)", type(error).__name__)
            return None
        return suggestion

    def _pause_to_speak(self) -> None:
        """Cierra el micro antes de la primera frase: su propia voz no vuelve como un turno."""
        assert self._engines is not None
        self._engines.microphone.close()
        self._paused_to_speak = True

    def _after_speaking(self, speech: _Speech) -> None:
        """Si decirlo falló, deja de oír y lo dice; si no, vuelve a oír en cuanto calle."""
        if speech.failure is not None:
            what, error = speech.failure
            self._engine_failed(what, error, doing="hablarte")
        elif self._paused_to_speak:
            self._resume_listening()

    def _resume_listening(self) -> bool:
        """Si el altavoz ya ha acabado, vuelve a abrir el micro; si no, espera a otra vuelta."""
        assert self._engines is not None and self._speaking is not None
        if self._speaking.speaker.playing:
            return False
        try:
            self._engines.microphone.open()
        except VoiceUnavailable as error:
            _logger.info("El micro no vuelve a abrirse: %s", error.reason)
            self._fail(f"No puedo oírte: {error.reason}.")
            self.stop()
            return False
        self._paused_to_speak = False
        return True

    def _engine_failed(self, what: str, error: Exception, *, doing: str = "oírte") -> None:
        """Una pieza del oído o de la voz falló a mitad: deja de oír y lo dice, sin tumbar a
        quien escucha y sin aconsejar la orden de instalar, que no lo arregla; el diario se
        queda solo con el tipo de fallo."""
        _logger.error("%s ha fallado (%s)", what, type(error).__name__)
        self._fail(f"No puedo {doing}: {what} ha fallado ({type(error).__name__}).")
        self.stop()

    def _chat_left(self) -> None:
        """La charla va a un modelo de fuera: el turno no sale, deja de oír y lo dice."""
        _logger.warning("La charla va a un modelo de fuera: el turno de voz no sale")
        self._fail(CHAT_LEAVES)
        self.stop()

    def _fail(self, problem: str, *, install: bool = False) -> str:
        """Apunta el aviso; con ``install``, con la orden de instalar y lo que hace."""
        notice = problem
        if install:
            notice += (
                " Ejecuta en PowerShell, dentro de la carpeta de Sirius: "
                f"{self._installation.install_command} . Instala o pone al día lo que falte "
                "de la voz y, si el problema es otro, te dice cuál."
            )
        self._notice = notice
        return notice


def _list(things: tuple[str, ...]) -> str:
    """«a», «a y b», «a, b y c»."""
    if len(things) == 1:
        return things[0]
    return f"{', '.join(things[:-1])} y {things[-1]}"


class _Speech:
    """Dice la respuesta frase a frase mientras la charla la escribe.

    Nada de lo que falle al decirla sale de aquí: la charla, que llama a ``hear`` mientras
    escribe, sigue hasta guardar la respuesta entera. El fallo queda en ``failure``, con
    qué falló, para quien envió, y desde él no se dice nada más.
    """

    def __init__(
        self,
        engines: SpeakingEngines[Any],
        *,
        before_first: Callable[[], None],
        clock: Callable[[], float],
    ) -> None:
        self._engines = engines
        self._before_first = before_first
        self._clock = clock
        self._cutter = SpeechCutter()
        self._started = False
        self.failure: tuple[str, Exception] | None = None
        #: Cuándo empezó a sonar la primera frase, con lo que tarda el altavoz.
        self.first_sound_at: float | None = None

    def hear(self, text: str) -> None:
        """Lo nuevo que ha escrito la charla: dice las frases que ya están cerradas."""
        self._say(lambda: self._cutter.feed(text))

    def finish(self) -> None:
        """La charla acabó bien: dice lo que quedaba."""
        self._say(self._cutter.finish)

    def _say(self, cut: Callable[[], list[str]]) -> None:
        if self.failure is not None:
            return
        what = "la voz"
        try:
            for sentence in cut():
                if not self._started:
                    self._started = True
                    self._before_first()
                what = "la voz"
                sound = self._engines.voice.say(sentence)
                what = "el altavoz"
                speaker = self._engines.speaker
                speaker.play(sound)
                if self.first_sound_at is None:
                    self.first_sound_at = self._clock() + speaker.latency
        except Exception as error:
            self.failure = (what, error)
