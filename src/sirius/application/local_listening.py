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
  cada frase se pide a la voz y suena en cuanto está. Sin cancelador de eco, desde la
  primera frase hasta que el altavoz acaba, el micro está cerrado: su propia voz no
  vuelve como un turno (PA-R03-03), y no se le puede cortar.
- **Con cancelador de eco, se le puede cortar** (pieza E, ADR-245). El micro sigue
  abierto mientras contesta, y cada trozo pasa por el cancelador antes del detector: su
  propia voz se aparta ahí. Mientras la charla escribe, el oído lee el micro cada vez que
  le llega texto de ella; después, al atender. En cuanto oye voz en lo limpio mientras
  contesta, pensando o hablando, o con su voz aún en el aire cuando el micro la captó,
  calla la voz y el altavoz; la charla sigue escribiendo y guarda la respuesta entera, y
  se le apunta hasta dónde se oyó. Lo que le corta es para él: calla en el instante en
  que empieza esa voz. Los turnos que se cierran mientras contesta van a la charla cuando
  acaba, y si son de la charla se decide al cerrarlos: contestar al primero no deja fuera
  al siguiente.
- **Si la voz o el altavoz fallan, deja de hablar y lo dice.** El fallo no sale a la
  charla, que sigue escribiendo y guarda la respuesta entera; después deja de oír con su
  aviso, como si fallara el detector.
- **Solo va a la charla lo que es para él** (pieza D, ADR-244): con su nombre, o sin él
  mientras dura la charla (``Addressing``). Lo que no es para él se transcribe, porque
  sin el texto no se sabe, y se descarta ahí: no va a la charla, que es lo único que
  escribe en la base, y el diario no apunta nada de lo oído. Cuenta la hora a la que el
  micro captó la voz, no la hora a la que la leyó: mientras transcribe o contesta, lo
  que suena espera en la cola del micro (ronda 1 de Codex sobre la PR #689).
- **Lo atiende un hilo y lo para otro.** La ventana abre, calla y cierra el oído desde el
  suyo mientras otro hilo lo atiende: todo lo que toca el micro, el detector y su estado
  va con un cerrojo, que se suelta mientras transcribe y contesta, para que el botón de
  silencio no espere a que acabe un turno. Lo que se cerró antes de callarlo o pararlo y
  aún no había ido a la charla ya no va; y si se para mientras habla, deja de hablar.
- **Quien enseña la escucha decide si un turno va ya a la charla** (``ListeningWatcher``):
  la ventana le dice que no si está con otra cosa, y se entera de cómo acabó cada turno y
  de cuándo deja de oír por su cuenta.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from sirius.application.addressing import Addressing, says_his_name
from sirius.application.send_message import ChatLeavesThisComputer, SendMessageResult
from sirius.application.speech_cutter import SpeechCutter
from sirius.domain.conversation import MessageStatus
from sirius.infrastructure.logging import get_logger
from sirius.ports.llm import runs_on_this_computer
from sirius.ports.local_voice import (
    Captured,
    EchoCanceller,
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

    def mark_cut(self, message_id: int, heard: str) -> None:
        """Le cortaron la respuesta ``message_id`` cuando el propietario había oído
        ``heard``: queda apuntado con ella, que sigue entera (pieza E, ADR-245)."""
        ...


class MemorySuggestions(Protocol):
    """Donde queda lo que el modelo propone recordar, pendiente de que él lo confirme."""

    def propose(self, content: str, *, message_id: int | None = None) -> object:
        """Lo deja pendiente, ligado a la respuesta que lo propuso."""
        ...


class Addressee(Protocol):
    """La charla (``Addressing``): cuándo calla Sirius y si una voz cae dentro. Su nombre
    se mira aparte, con ``says_his_name``."""

    @property
    def conversation_seconds(self) -> float:
        """Lo que dura la charla desde que Sirius calla."""
        ...

    def fell_silent(self, at: float) -> None:
        """Sirius acaba de callar."""
        ...

    def in_conversation(self, began: float) -> bool:
        """Si la voz que empezó a oírse en ``began`` es de la charla que corre."""
        ...


@dataclass(frozen=True, slots=True)
class HeardTurn:
    """Un turno de voz cerrado: lo que oyó, si era para él, lo que contestó la charla y lo
    que el modelo propuso recordar.

    ``heard`` es lo oído, tal cual. Para enseñarlo está lo guardado,
    ``result.user_message``: tras «olvida lo de…» lo guardado ya no dice qué había que
    olvidar, y lo oído sí (ronda 14 de Codex sobre la PR #687). Si no era para él
    (``addressed`` falso), no fue a la charla: ``result`` es ``None``, ``operation_id`` va
    vacío y nada lo guarda (ADR-244).

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


class ListeningWatcher(Protocol):
    """Quien enseña la escucha, como la ventana: decide si un turno para él va ya a la
    charla, y se entera de cómo acabó y de cuándo el oído deja de oír por su cuenta.

    Se le llama desde el hilo que atiende al oído, sin su cerrojo puesto.
    """

    def may_answer(self, operation_id: str, heard: str) -> bool:
        """Si el turno para él, con su operación y lo oído, puede ir ya a la charla. Puede
        esperar a que acabe lo que tenga entre manos; si dice que no, el turno no va."""
        ...

    def answered(self, turn: HeardTurn | None) -> None:
        """El turno que dejó pasar ha acabado: ``None`` si al final no fue a la charla."""
        ...

    def stopped(self, notice: str) -> None:
        """El oído ha dejado de oír por su cuenta; ``notice`` dice por qué."""
        ...


@dataclass(slots=True)
class _ClosedTurn[Chunk]:
    """Un turno que el detector dio por acabado y aún no se ha transcrito.

    ``chunks`` se vacía en cuanto se transcribe: el audio no vive más que eso.
    ``in_conversation`` dice si su voz empezó a oírse dentro de la charla que corría al
    cerrarse; ``voice_heard_at``, cuándo se oyó por última vez, para E-R03-02: los dos, a
    la hora a la que el micro captó el trozo, no a la que se leyó. ``generation``, cuántas
    veces se había callado o parado el oído al cerrarse. Lo de la charla se decide al
    cerrarlo, como la generación: hasta que le toca ir a la charla puede contestar a otro
    turno y callar otra vez (pieza E, ADR-245).
    """

    chunks: list[Chunk]
    in_conversation: bool
    voice_heard_at: float
    generation: int


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
        addressing: Addressee | None = None,
    ) -> None:
        self._chat = chat
        self._clock = clock
        self._addressing: Addressee = addressing if addressing is not None else Addressing()
        self._memory_suggestions = memory_suggestions
        self._installation = installation
        self._load_engines = load_engines
        self._load_speaking = load_speaking
        self._engines: ListeningEngines[Chunk] | None = None
        self._speaking: SpeakingEngines[Any] | None = None
        #: Todo lo que toca el micro, el detector y el estado del oído, desde el hilo que
        #: sea. Reentrante: lo que falla con él puesto para con él puesto.
        self._lock = threading.RLock()
        #: El micro está cerrado porque Sirius habla; se abre cuando el altavoz acaba.
        self._paused_to_speak = False
        self._detector_stale = False
        self._listening = False
        #: El botón de silencio: mientras, nada abre el micro, ni ``start``.
        self._muted = False
        #: Cuántas veces se ha callado o parado: un turno cerrado antes no va a la charla.
        self._generation = 0
        self._notice = ""
        #: El aviso de cuando dejó de oír por su cuenta, hasta contárselo a quien mira.
        self._gave_up: str | None = None
        self._watcher: ListeningWatcher | None = None
        #: Lo que está diciendo, para callarlo si se para.
        self._speech: _Speech | None = None
        #: Lo que dijo y aún suena, ya entregado a la charla, con su mensaje: si le cortan,
        #: se calla y se apunta hasta dónde se oyó (pieza E, ADR-245).
        self._still_sounding: _Sounding | None = None
        #: Los turnos que se cerraron mientras contestaba: van a la charla cuando acaba.
        self._closed_meanwhile: deque[_ClosedTurn[Chunk]] = deque()
        self._before_turn: deque[Chunk] = deque(maxlen=pre_roll)
        self._turn: list[Chunk] | None = None
        #: Cuándo empezó a oírse la voz del turno abierto: de ahí cuenta la charla.
        self._turn_began_at = 0.0
        #: Cuándo dijo el detector por última vez que había voz: de ahí cuenta E-R03-02.
        self._voice_heard_at = 0.0

    @property
    def listening(self) -> bool:
        """Si el micro está abierto y Sirius atiende lo que llega."""
        return self._listening

    @property
    def muted(self) -> bool:
        """Si está callado con el botón de silencio."""
        return self._muted

    @property
    def conversation_seconds(self) -> float:
        """Lo que dura la charla desde que Sirius calla: hasta entonces sobra su nombre."""
        return self._addressing.conversation_seconds

    def watch(self, watcher: ListeningWatcher | None) -> None:
        """Quien enseña la escucha a partir de ahora; ``None``, nadie."""
        with self._lock:
            self._watcher = watcher

    def start(self) -> str:
        """Abre el micro si el oído está instalado; devuelve el aviso si no puede, o vacío.

        Si ya escucha, o si está callado con el botón de silencio, no hace nada. Sin el
        oído instalado, no carga nada, no abre el micro y no baja nada: el aviso dice qué
        falta y qué orden lo instala. Si aún suena lo último que dijo, escucha ya, pero
        abre el micro cuando calle, como tras hablar (ronda 1 de Codex sobre la PR #688).
        """
        with self._lock:
            if self._listening or self._muted:
                return ""
            if not runs_on_this_computer(self._chat.llm_provider):
                _logger.info("El oído no arranca: la charla va a un modelo de fuera")
                return self._fail(CHAT_LEAVES)
            missing = self._installation.missing()
            if missing:
                _logger.info("El oído no arranca: falta %s", ", ".join(missing))
                problem = (
                    f"Para oírte y hablarte me falta instalar {_list(missing)} en este ordenador."
                )
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
                    problem = (
                        f"No puedo oírte: el detector de voz no se ha podido reiniciar ({error})."
                    )
                    return self._fail(problem)
                self._detector_stale = False
            if self._speaking.speaker.playing:
                self._listening = True
                self._paused_to_speak = True
                self._notice = ""
                return ""
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

        Si hablaba, se calla: lo que la charla siga escribiendo ya no se dice, el altavoz
        tira lo que le quedaba por decir, y lo que ya estaba saliendo acaba en lo que tarda
        en sonar.

        Nada de lo que falle aquí deja a Sirius oyendo ni suelta una pieza: el estado se
        limpia antes, el micro garantiza que al cerrarse no da más audio, y si el detector
        no se puede reiniciar se apunta, y el siguiente ``start`` lo vuelve a intentar y,
        si sigue sin poder, lo dice como aviso en vez de abrir el micro (rondas 2 y 3).
        """
        with self._lock:
            speech = self._speech
            if speech is not None:
                speech.silence()
            if self._speaking is not None:
                self._speaking.speaker.stop()
            self._stop_hearing()

    def mute(self) -> None:
        """El botón de silencio: cierra el micro como ``stop`` y no lo abre nadie hasta
        ``unmute``. Lo que suene mientras se pierde, y lo que había oído y aún no había ido
        a la charla ya no va. Si está hablando, sigue: el silencio es para el micro."""
        with self._lock:
            self._muted = True
            self._stop_hearing()

    def unmute(self) -> str:
        """Quita el silencio y vuelve a escuchar; devuelve el aviso si no puede, o vacío."""
        with self._lock:
            self._muted = False
            return self.start()

    def attend(self) -> Attended:
        """Atiende todo lo que ha llegado al micro y devuelve los turnos que cerró.

        Cada trozo se le enseña al detector una vez y en orden; cuando dice que el turno
        ha acabado, se transcribe el turno entero y, si es para él, el texto va a la
        charla. Sin escuchar, no lee el micro y devuelve el aviso de por qué. El cerrojo se
        suelta mientras transcribe y contesta.
        """
        turns: list[HeardTurn] = []
        while (closed := self._next_turn()) is not None:
            turn = self._attend_turn(closed)
            if turn is not None:
                turns.append(turn)
        with self._lock:
            notice = "" if self._listening else self._notice
            gave_up, self._gave_up = self._gave_up, None
            watcher = self._watcher
        if gave_up is not None and watcher is not None:
            watcher.stopped(gave_up)
        return Attended(turns=tuple(turns), notice=notice)

    def _stop_hearing(self) -> None:
        """Lo que hacen ``stop`` y ``mute`` con el micro y el detector; con el cerrojo."""
        engines = self._engines
        # Mientras habla, el micro ya está cerrado.
        microphone_open = self._listening and not self._paused_to_speak
        self._listening = False
        self._paused_to_speak = False
        self._generation += 1
        self._turn = None
        self._before_turn.clear()
        if self._speech is not None or self._still_sounding is not None:
            # Desde aquí el oído ya no ve cuándo calla: al parar, calla ya, aunque le quedara
            # algo por decir; al callar el micro, sigue hablando. La charla corre desde aquí
            # hasta que la mueva lo que venga después (pieza E, ADR-245).
            self._addressing.fell_silent(self._clock())
        self._still_sounding = None
        self._closed_meanwhile.clear()
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

    def _next_turn(self) -> _ClosedTurn[Chunk] | None:
        """El turno que se cerró mientras contestaba, si quedó alguno; si no, lee el micro
        hasta que el detector cierra un turno o no queda nada. Con el cerrojo, que suelta al
        volver."""
        with self._lock:
            if not self._listening or self._engines is None:
                return None
            if self._closed_meanwhile:
                return self._closed_meanwhile.popleft()
            if self._paused_to_speak and not self._resume_listening():
                # Sigue hablando: con el micro cerrado no hay nada que leer.
                return None
            microphone = self._engines.microphone
            while (
                self._listening
                and not self._paused_to_speak
                and (captured := microphone.read()) is not None
            ):
                closed = self._listen(captured)
                if closed is not None:
                    return closed
            return None

    def _listen(self, captured: Captured[Chunk]) -> _ClosedTurn[Chunk] | None:
        """Le enseña el trozo al detector, sin el eco si hay cancelador; si le hablan
        encima, calla; y si con el trozo acaba el turno, lo devuelve. Con el cerrojo."""
        assert self._engines is not None
        chunk = captured.chunk
        # La hora a la que lo captó el micro, antes de mirarlo: ni lo que esperó en su
        # cola mientras transcribía o contestaba ni lo que tarde el detector cuentan
        # (rondas 1 y 2 de Codex sobre la PR #689).
        captured_at = self._clock() - captured.age
        echoing = False
        canceller = self._echo_canceller()
        if canceller is not None:
            try:
                cleaned = canceller.clean(captured)
            except Exception as error:
                self._engine_failed("la cancelación de eco", error)
                return None
            chunk, echoing = cleaned.chunk, cleaned.echoing
            if self._still_sounding is not None and not echoing and not self._sounds():
                # Ya no le queda nada por decir, y cuando el micro captó esto su voz ya no
                # estaba en el aire: calló, y desde ahí corre la charla. En una pausa entre
                # frase y frase aún contesta.
                self._still_sounding = None
                self._addressing.fell_silent(captured_at)
        try:
            signal = self._engines.detector.listen(chunk)
        except Exception as error:
            self._engine_failed("el detector de voz", error)
            return None
        if signal is TurnSignal.VOICE:
            self._voice_heard_at = captured_at
        if self._turn is None:
            if signal is not TurnSignal.VOICE:
                self._before_turn.append(chunk)
                return None
            self._turn = [*self._before_turn, chunk]
            self._before_turn.clear()
            self._turn_began_at = self._voice_heard_at
        else:
            self._turn.append(chunk)
        if signal is TurnSignal.VOICE and (echoing or self._answering()):
            self._cut()
        if signal is not TurnSignal.ENDED:
            return None
        chunks, self._turn = self._turn, None
        in_conversation = self._addressing.in_conversation(self._turn_began_at)
        return _ClosedTurn(chunks, in_conversation, self._voice_heard_at, self._generation)

    def _echo_canceller(self) -> EchoCanceller[Any] | None:
        """El cancelador de eco, si la voz trae uno."""
        return None if self._speaking is None else self._speaking.echo_canceller

    def _answering(self) -> bool:
        """Si está contestando: desde que el turno va a la charla hasta que calla."""
        return self._speech is not None or self._still_sounding is not None

    def _sounds(self) -> bool:
        """Si el altavoz aún suena o tiene algo por sonar."""
        return self._speaking is not None and self._speaking.speaker.playing

    def _cut(self) -> None:
        """Le hablan encima mientras contesta, o con su voz aún en el aire: calla la voz y
        el altavoz, apunta hasta dónde se oyó lo que decía, y lo que le corta es para él,
        porque calla en el instante en que empieza esa voz. La charla sigue escribiendo y
        guarda la respuesta entera (pieza E, ADR-245). Con el cerrojo.

        Si ya le cortaron mientras la charla escribe, no hace nada: calló con ese corte, y
        lo que siga diciéndole cae en la charla que empezó ahí, sin alargarla.

        Calla el altavoz lo primero: hasta dónde se oyó se mira cuando ya no puede empezar
        otra frase, y apuntarlo no le hace seguir hablando."""
        if self._speech is not None and self._speech.heard_when_cut is not None:
            return
        assert self._speaking is not None
        self._speaking.speaker.stop()
        self._addressing.fell_silent(self._turn_began_at)
        if self._speech is not None:
            self._speech.cut()
        sounding, self._still_sounding = self._still_sounding, None
        if sounding is not None:
            sounding.speech.cut()
            self._mark_cut(sounding.message_id, sounding.speech)

    def _mark_cut(self, message_id: int | None, speech: _Speech) -> None:
        """Apunta en la charla hasta dónde se oyó la respuesta ``message_id``, si le
        cortaron. Si falla, la respuesta sigue guardada entera y el diario se queda con el
        tipo de fallo."""
        heard = speech.heard_when_cut
        if message_id is None or heard is None:
            return
        try:
            self._chat.mark_cut(message_id, heard)
        except Exception as error:
            _logger.error("No se pudo apuntar hasta dónde se oyó (%s)", type(error).__name__)

    def _hear_meanwhile(self) -> None:
        """Mientras la charla escribe, con cancelador: lee lo que ha llegado al micro, para
        que le puedan cortar sin esperar a que acabe. Los turnos que se cierran ahora van a
        la charla cuando acabe la respuesta."""
        with self._lock:
            if not self._listening or self._engines is None or self._echo_canceller() is None:
                return
            microphone = self._engines.microphone
            while self._listening and (captured := microphone.read()) is not None:
                closed = self._listen(captured)
                if closed is not None:
                    self._closed_meanwhile.append(closed)

    def _attend_turn(self, closed: _ClosedTurn[Chunk]) -> HeardTurn | None:
        """Transcribe el turno y, si es para él y quien mira lo deja, lo entrega a la charla.

        Sin el cerrojo: transcribir y contestar tardan, y mientras tanto la ventana tiene
        que poder callar el oído.
        """
        if not runs_on_this_computer(self._chat.llm_provider):
            # La charla ya se fue a un modelo de fuera: ni se transcribe.
            closed.chunks.clear()
            self._chat_left()
            return None
        assert self._engines is not None
        try:
            heard = self._engines.transcriber.transcribe(closed.chunks).strip()
        except Exception as error:
            self._engine_failed("el modelo de oír", error)
            return None
        finally:
            closed.chunks.clear()
        if not heard:
            _logger.info("Turno de voz sin palabras: no va a la charla")
            return None
        with self._lock:
            current = closed.generation == self._generation
            watcher = self._watcher
        if not current:
            _logger.info("Turno de voz de antes de callar o parar el oído: no va a la charla")
            return None
        if not (says_his_name(heard) or closed.in_conversation):
            # Ni lo oído ni nada de ello: solo que no era para él.
            _logger.info("Turno de voz que no era para él: no va a la charla")
            return HeardTurn(heard=heard, addressed=False, result=None, operation_id="")
        # La operación la pone el oído, como la ventana: si la charla se rompe a medias,
        # con ella se sabe qué quedó guardado de este turno.
        operation_id = str(uuid.uuid4())
        if watcher is not None and not watcher.may_answer(operation_id, heard):
            _logger.info("Turno de voz para él con la ventana ocupada: no va a la charla")
            return None
        turn: HeardTurn | None = None
        try:
            with self._lock:
                # Mientras la ventana decidía pudieron callarlo o pararlo. Desde aquí, lo que
                # diga lo calla ``stop``: ninguna frase se le escapa.
                if closed.generation != self._generation:
                    _logger.info("Turno de voz callado o parado antes de ir a la charla")
                    return None
                assert self._speaking is not None
                speech = _Speech(
                    self._speaking,
                    before_first=self._pause_to_speak,
                    clock=self._clock,
                    lock=self._lock,
                    meanwhile=self._hear_meanwhile,
                )
                self._speech = speech
            turn = self._deliver(heard, operation_id, closed.voice_heard_at, speech)
        finally:
            if watcher is not None:
                watcher.answered(turn)
        return turn

    def _deliver(
        self, heard: str, operation_id: str, voice_heard_at: float, speech: _Speech
    ) -> HeardTurn | None:
        """Lo entrega a la charla, dice la respuesta mientras la escribe y deja pendiente lo
        que el modelo proponga recordar; ``None`` si la charla se fue a un modelo de fuera."""
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
        finally:
            self._speech = None
        _logger.info("Turno de voz entregado a la charla")
        message_id = result.sirius_message.id if result.outcome is MessageStatus.COMPLETED else None
        # Si le cortaron mientras la charla escribía, la respuesta no estaba guardada aún.
        self._mark_cut(message_id, speech)
        self._after_speaking(speech, message_id)
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
        """Cierra el micro antes de la primera frase: su propia voz no vuelve como un turno.

        Si mientras tanto lo han callado o parado, el micro ya está cerrado y se queda así.
        Con cancelador no lo cierra: su voz se aparta de cada trozo (pieza E, ADR-245).
        """
        with self._lock:
            if not self._listening or self._paused_to_speak:
                return
            if self._echo_canceller() is not None:
                return
            assert self._engines is not None
            self._engines.microphone.close()
            self._paused_to_speak = True

    def _after_speaking(self, speech: _Speech, message_id: int | None = None) -> None:
        """Si decirlo falló, calla, deja de oír y lo dice. Si le cortaron, la charla ya
        corre desde el corte. Sin cancelador, vuelve a oír en cuanto calle; con él, si su
        voz aún suena, la charla empieza con el primer trozo que el micro capte sin ella, y
        hasta entonces aún se le puede cortar. Si no dijo nada, ya ha callado: desde ahí
        corre la charla."""
        with self._lock:
            if speech.failure is not None:
                what, error = speech.failure
                self._addressing.fell_silent(self._clock())
                self._engine_failed(what, error, doing="hablarte")
            elif speech.heard_when_cut is not None:
                return
            elif self._paused_to_speak:
                self._resume_listening()
            elif self._may_still_sound(speech):
                self._still_sounding = _Sounding(speech, message_id)
            else:
                self._addressing.fell_silent(self._clock())

    def _may_still_sound(self, speech: _Speech) -> bool:
        """Si lo que dijo puede seguir sonando y el oído lo sabrá: con cancelador, el micro
        abierto y el altavoz aún sonando."""
        return (
            speech.spoke
            and self._listening
            and self._echo_canceller() is not None
            and self._speaking is not None
            and self._speaking.speaker.playing
        )

    def _resume_listening(self) -> bool:
        """Si el altavoz ya ha acabado, vuelve a abrir el micro y empieza la charla; si no,
        espera a otra vuelta. Con el cerrojo."""
        assert self._engines is not None and self._speaking is not None
        if self._speaking.speaker.playing:
            return False
        # Ha callado ya, antes de abrir: lo que el micro capte mientras se abre es de la
        # charla.
        quiet_since = self._clock()
        try:
            self._engines.microphone.open()
        except VoiceUnavailable as error:
            _logger.info("El micro no vuelve a abrirse: %s", error.reason)
            self._give_up(f"No puedo oírte: {error.reason}.")
            return False
        self._paused_to_speak = False
        self._addressing.fell_silent(quiet_since)
        return True

    def _engine_failed(self, what: str, error: Exception, *, doing: str = "oírte") -> None:
        """Una pieza del oído o de la voz falló a mitad: deja de oír y lo dice, sin tumbar a
        quien escucha y sin aconsejar la orden de instalar, que no lo arregla; el diario se
        queda solo con el tipo de fallo."""
        _logger.error("%s ha fallado (%s)", what, type(error).__name__)
        self._give_up(f"No puedo {doing}: {what} ha fallado ({type(error).__name__}).")

    def _chat_left(self) -> None:
        """La charla va a un modelo de fuera: el turno no sale, deja de oír y lo dice."""
        _logger.warning("La charla va a un modelo de fuera: el turno de voz no sale")
        self._give_up(CHAT_LEAVES)

    def _give_up(self, problem: str) -> None:
        """Deja de oír por su cuenta: apunta el aviso, para, y queda contárselo a quien mira
        al acabar de atender."""
        with self._lock:
            self._fail(problem)
            self.stop()
            self._gave_up = self._notice

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


@dataclass(slots=True)
class _Sounding:
    """Lo que dijo Sirius y aún suena, ya entregado a la charla: su voz y su mensaje, para
    callarlo y apuntar hasta dónde se oyó si le cortan (pieza E, ADR-245)."""

    speech: _Speech
    message_id: int | None


class _Speech:
    """Dice la respuesta frase a frase mientras la charla la escribe.

    Nada de lo que falle al decirla sale de aquí: la charla, que llama a ``hear`` mientras
    escribe, sigue hasta guardar la respuesta entera. El fallo queda en ``failure``, con
    qué falló, para quien envió, y desde él no se dice nada más. Callada (``silence``),
    tampoco: cada frase se da al altavoz con el cerrojo del oído, el mismo con el que
    ``stop`` la calla y vacía el altavoz, así que ninguna se cuela después.

    Cada vez que la charla escribe, antes de decir lo cerrado, llama a ``meanwhile``: con
    cancelador, el oído lee ahí el micro, para que le puedan cortar sin esperar a que la
    charla acabe, y sin decir otra frase encima de quien ya habla. Si le cortan (``cut``),
    queda lo que se oyó: las frases que el altavoz llegó a empezar (pieza E, ADR-245).
    """

    def __init__(
        self,
        engines: SpeakingEngines[Any],
        *,
        before_first: Callable[[], None],
        clock: Callable[[], float],
        lock: threading.RLock,
        meanwhile: Callable[[], None] = lambda: None,
    ) -> None:
        self._engines = engines
        self._before_first = before_first
        self._clock = clock
        self._lock = lock
        self._meanwhile = meanwhile
        self._cutter = SpeechCutter()
        self._started = False
        self._silenced = False
        #: Las frases que se le dieron al altavoz, en orden.
        self._said: list[str] = []
        #: Cuántos sonidos había empezado el altavoz antes de la primera frase.
        self._base: int | None = None
        self.failure: tuple[str, Exception] | None = None
        #: Cuándo empezó a sonar la primera frase, con lo que tarda el altavoz.
        self.first_sound_at: float | None = None
        #: Lo que se oyó cuando le cortaron; ``None`` si no le han cortado.
        self.heard_when_cut: str | None = None

    @property
    def spoke(self) -> bool:
        """Si le dio al altavoz alguna frase."""
        return bool(self._said)

    def hear(self, text: str) -> None:
        """Lo nuevo que ha escrito la charla: deja al oído mirar el micro, por si le hablan
        encima, y dice las frases que ya están cerradas."""
        self._meanwhile()
        self._say(lambda: self._cutter.feed(text))

    def finish(self) -> None:
        """La charla acabó bien: dice lo que quedaba."""
        self._say(self._cutter.finish)

    def silence(self) -> None:
        """Deja de decir: lo que llegue después ya no suena."""
        self._silenced = True

    def cut(self) -> None:
        """Le cortan: deja de decir, y queda lo que se oyó hasta aquí. Lo que se oyó se
        apunta la primera vez."""
        self._silenced = True
        if self.heard_when_cut is None:
            self.heard_when_cut = self.heard()

    def heard(self) -> str:
        """Lo que empezó a sonar de lo que dijo, frase a frase: lo que el altavoz tiró al
        callarlo sin que llegara a sonar no cuenta."""
        if self._base is None:
            return ""
        sounded = self._engines.speaker.started - self._base
        return " ".join(self._said[: max(0, sounded)])

    def _say(self, cut: Callable[[], list[str]]) -> None:
        if self.failure is not None or self._silenced:
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
                with self._lock:
                    if self._silenced:
                        return
                    if self._base is None:
                        self._base = speaker.started
                    speaker.play(sound)
                    self._said.append(sentence)
                if self.first_sound_at is None:
                    self.first_sound_at = self._clock() + speaker.latency
        except Exception as error:
            self.failure = (what, error)
