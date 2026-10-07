"""El juez en segundo plano (pieza E de ADR-233, PA-R02-08).

La ventana lo lanza al abrirse y al acabar cada turno, con la respuesta ya en
pantalla, y le pide que pare cuando el propietario escribe, para que el modelo
local quede libre para la charla: el turno espera a que acabe la respuesta que
está puntuando.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.robot_conversation import ReplyJudgeService
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class ReplyJudgeWorkerSignals(QObject):
    finished = Signal()


class ReplyJudgeWorker(QRunnable):
    """Puntúa las respuestas que aún no tienen nota, fuera del hilo de la ventana."""

    def __init__(self, service: ReplyJudgeService) -> None:
        super().__init__()
        self._service = service
        self._stop = threading.Event()
        self.signals = ReplyJudgeWorkerSignals()

    def stop(self) -> None:
        """Que pare antes de la siguiente respuesta; la que está puntuando la termina."""
        self._stop.set()

    def run(self) -> None:
        try:
            self._service.judge_pending(should_stop=self._stop.is_set)
        except Exception as exc:  # el juez nunca puede romper la ventana
            _logger.error("El juez se interrumpió (%s)", type(exc).__name__)
        finally:
            self.signals.finished.emit()
