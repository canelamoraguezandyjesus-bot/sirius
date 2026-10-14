"""Oír en local: lo que el propietario dice por el micro entra en la charla (ADR-242).

La pieza B de la 0.3 (ADR-241). El servicio lee lo que ha llegado al micro, pregunta al
detector de turno por cada trozo y, cuando el detector da el turno por acabado, lo
transcribe y le pasa el texto a la misma charla que la ventana
(``SendMessageUseCase.send_message``): la misma semilla, la misma memoria y las mismas
órdenes, «olvida eso» incluida.

- **No espera.** ``attend`` atiende lo que ya ha llegado y vuelve; quien lo llama, la
  orden de consola o la ventana, decide cada cuánto.
- **No guarda audio.** Los trozos del turno viven en memoria hasta cerrarlo, y el
  diario no recibe nada de lo oído: «olvida eso» no podría borrarlo de ahí.
- **Sin el oído instalado no hace nada.** Antes de abrir el micro mira que esté todo en
  este ordenador; si falta algo, devuelve el aviso con la orden que lo instala, no abre
  el micro, no contesta y no baja nada (PA-R03-08).
- **En la pieza B todo lo oído es para él**; a quién le hablan lo decide la pieza D.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from sirius.application.send_message import SendMessageResult
from sirius.domain.conversation import MessageStatus
from sirius.infrastructure.logging import get_logger
from sirius.ports.local_voice import (
    ListeningEngines,
    TurnSignal,
    VoiceInstallation,
    VoiceUnavailable,
)

_logger = get_logger(__name__)

#: Cuántos trozos sin voz se guardan antes de que empiece un turno, para no cortarle la
#: primera sílaba: Silero da la voz por empezada un poco después de que empiece. Con los
#: trozos del micro de verdad, de 512 muestras a 16 kHz, son medio segundo.
PRE_ROLL_CHUNKS = 16


class Chat(Protocol):
    """La charla de Sirius, la misma que usa la ventana."""

    def send_message(self, user_text: str) -> SendMessageResult: ...


@dataclass(frozen=True, slots=True)
class HeardTurn:
    """Un turno de voz cerrado: lo que oyó, si era para él y lo que contestó.

    ``answered`` dice si la charla acabó bien; si no, ``reply`` es lo que llegara a
    escribir, como en la ventana.
    """

    heard: str
    addressed: bool
    reply: str
    answered: bool = True


@dataclass(frozen=True, slots=True)
class Attended:
    """Lo que pasó al atender el micro: los turnos cerrados, en orden, y el aviso si no oye."""

    turns: tuple[HeardTurn, ...] = ()
    notice: str = ""


class LocalListening[Chunk]:
    """El oído del robot: del micro a la charla, todo en este ordenador."""

    def __init__(
        self,
        *,
        chat: Chat,
        installation: VoiceInstallation,
        load_engines: Callable[[], ListeningEngines[Chunk]],
        pre_roll: int = PRE_ROLL_CHUNKS,
    ) -> None:
        self._chat = chat
        self._installation = installation
        self._load_engines = load_engines
        self._engines: ListeningEngines[Chunk] | None = None
        self._listening = False
        self._notice = ""
        self._before_turn: deque[Chunk] = deque(maxlen=pre_roll)
        self._turn: list[Chunk] | None = None

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
        missing = self._installation.missing()
        if missing:
            _logger.info("El oído no arranca: falta %s", ", ".join(missing))
            return self._fail(f"Para oírte me falta {_list(missing)} en este ordenador.", True)
        try:
            if self._engines is None:
                self._engines = self._load_engines()
            self._engines.microphone.open()
        except VoiceUnavailable as error:
            _logger.info("El oído no arranca: %s", error.reason)
            return self._fail(f"No puedo oírte: {error.reason}.", error.fixed_by_install)
        self._listening = True
        self._notice = ""
        return ""

    def stop(self) -> None:
        """Cierra el micro y olvida el turno a medias, si lo había, también en el detector.

        Si no, al volver a escuchar el detector seguiría en el turno viejo: Silero
        creería que aún hay voz y el silencio siguiente abriría un turno sin palabras
        (ronda 1 de Codex sobre la PR #687). El estado del servicio se limpia antes, y si
        cerrar el micro o reiniciar el detector falla, se sueltan las piezas: el siguiente
        ``start`` las carga de nuevo, y el fallo sigue su camino (ronda 2).
        """
        engines, listening = self._engines, self._listening
        self._listening = False
        self._turn = None
        self._before_turn.clear()
        if engines is None:
            return
        try:
            if listening:
                engines.microphone.close()
            engines.detector.reset()
        except BaseException:
            self._engines = None
            raise

    def attend(self) -> Attended:
        """Atiende todo lo que ha llegado al micro y devuelve los turnos que cerró.

        Cada trozo se le enseña al detector una vez y en orden; cuando dice que el turno
        ha acabado, se transcribe el turno entero y el texto va a la charla. Sin escuchar,
        no lee el micro y devuelve el aviso de por qué.
        """
        if not self._listening or self._engines is None:
            return Attended(notice=self._notice)
        microphone = self._engines.microphone
        turns: list[HeardTurn] = []
        while (chunk := microphone.read()) is not None:
            turn = self._take(chunk)
            if turn is not None:
                turns.append(turn)
        return Attended(turns=tuple(turns))

    def _take(self, chunk: Chunk) -> HeardTurn | None:
        """Le enseña ``chunk`` al detector y, si con él acaba el turno, lo atiende."""
        assert self._engines is not None
        signal = self._engines.detector.listen(chunk)
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
        heard = self._engines.transcriber.transcribe(chunks).strip()
        del chunks
        if not heard:
            _logger.info("Turno de voz sin palabras: no va a la charla")
            return None
        result = self._chat.send_message(heard)
        _logger.info("Turno de voz entregado a la charla")
        return HeardTurn(
            heard=heard,
            addressed=True,
            reply=result.sirius_message.content or "",
            answered=result.outcome is MessageStatus.COMPLETED,
        )

    def _fail(self, problem: str, fixed_by_install: bool) -> str:
        notice = problem
        if fixed_by_install:
            notice += (
                " Para instalarlo, ejecuta en PowerShell, dentro de la carpeta de Sirius: "
                f"{self._installation.install_command}"
            )
        self._notice = notice
        return notice


def _list(things: tuple[str, ...]) -> str:
    """«a», «a y b», «a, b y c»."""
    if len(things) == 1:
        return things[0]
    return f"{', '.join(things[:-1])} y {things[-1]}"
