"""La ventana y el oído, cada uno en su hilo (pieza D de la 0.3, ADR-244).

El oído (``LocalListening``) atiende el micro desde el hilo que lo atienda: el del bucle de
``sirius.main`` en producción, y el de la prueba en las pruebas. La ventana vive en el
suyo. Este puente es lo que mira la escucha (``ListeningWatcher``): lleva cada pregunta y
cada aviso del oído al hilo de la ventana.

- **Antes de cada turno para él** (``may_answer``) le pregunta a la ventana, en su hilo, y
  espera la respuesta: si está con otra cosa, el turno no va. Si va, espera además, en el
  hilo del oído, a que lo de segundo plano acabe lo que tiene entre manos, como espera un
  turno escrito: la ventana no se queda esperando nunca.
- **Al acabar cada turno** (``answered``) y **si el oído deja de oír por su cuenta**
  (``stopped``), se lo cuenta a la ventana en su hilo, sin esperar.
- **Desde el hilo de la ventana, todo es directo**: una conexión que espera, desde su
  propio hilo, se quedaría colgada.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtCore import QObject, Qt, Signal

from sirius.application.local_listening import HeardTurn
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class VoiceTurnHost(Protocol):
    """Lo que el puente necesita de la ventana. Todo se llama en el hilo de la ventana."""

    def begin_voice_turn(self, operation_id: str, heard: str) -> Sequence[threading.Event] | None:
        """Si el turno para él puede ir ya a la charla, lo pone en marcha y devuelve lo que
        tiene que acabar antes de entregarlo; ``None`` si no puede ir."""
        ...

    def finish_voice_turn(self, turn: HeardTurn | None) -> None:
        """El turno que dejó pasar ha acabado: ``None`` si al final no fue a la charla."""
        ...

    def listening_stopped(self, notice: str) -> None:
        """El oído ha dejado de oír por su cuenta; ``notice`` dice por qué."""
        ...


@dataclass(slots=True)
class _Question:
    """Una pregunta del oído a la ventana, con su respuesta cuando la tenga."""

    operation_id: str
    heard: str
    #: Lo que hay que esperar antes de entregar el turno; ``None``, que no va.
    waits: Sequence[threading.Event] | None = None


class ListeningBridge(QObject):
    """Lo que mira la escucha por la ventana: le pregunta y le avisa en su hilo."""

    _asked = Signal(object)
    _answered = Signal(object)
    _stopped = Signal(str)

    def __init__(self, host: VoiceTurnHost, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._host = host
        #: El hilo de la ventana, donde se crea el puente.
        self._home = threading.get_ident()
        self._asked.connect(self._ask_host, Qt.ConnectionType.BlockingQueuedConnection)
        self._answered.connect(self._tell_answered)
        self._stopped.connect(self._tell_stopped)

    def may_answer(self, operation_id: str, heard: str) -> bool:
        question = _Question(operation_id, heard)
        if threading.get_ident() == self._home:
            self._ask_host(question)
        else:
            # Espera a que la ventana conteste; si ya no existe, nadie contesta y no va.
            self._asked.emit(question)
        if question.waits is None:
            return False
        for done in question.waits:
            done.wait()
        return True

    def answered(self, turn: HeardTurn | None) -> None:
        self._answered.emit(turn)

    def stopped(self, notice: str) -> None:
        self._stopped.emit(notice)

    def _ask_host(self, question: _Question) -> None:
        try:
            question.waits = self._host.begin_voice_turn(question.operation_id, question.heard)
        except Exception as error:  # la ventana no rompe al oído: el turno no va
            _logger.error("La ventana no pudo empezar un turno de voz (%s)", type(error).__name__)

    def _tell_answered(self, turn: object) -> None:
        assert turn is None or isinstance(turn, HeardTurn)
        try:
            self._host.finish_voice_turn(turn)
        except Exception as error:
            _logger.error("La ventana no pudo acabar un turno de voz (%s)", type(error).__name__)

    def _tell_stopped(self, notice: str) -> None:
        try:
            self._host.listening_stopped(notice)
        except Exception as error:
            _logger.error("La ventana no pudo decir que no oye (%s)", type(error).__name__)
