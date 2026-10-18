"""El juez en segundo plano (pieza E de ADR-233, PA-R02-08).

La ventana lo lanza al abrirse y al acabar cada turno, con la respuesta ya en
pantalla, y le pide que pare cuando el propietario escribe o le habla, para que el
modelo local quede libre para la charla: corta la nota que está pidiendo, y el turno
espera solo a que la deje (ADR-252).
"""

from __future__ import annotations

import contextlib
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
        #: Se pone al acabar ``run``, después de avisar: un turno de voz lo espera desde
        #: el hilo del oído, que no recibe las señales de la ventana (ADR-244).
        self.done = threading.Event()

    def stop(self) -> None:
        """Que pare antes de la siguiente respuesta, y que corte la que está puntuando: un
        turno de voz no espera a que el juez acabe su petición (ADR-252)."""
        self._stop.set()
        self._service.cancel()

    def run(self) -> None:
        try:
            self._service.judge_pending(should_stop=self._stop.is_set)
        except Exception as exc:  # el juez nunca puede romper la ventana
            _logger.error("El juez se interrumpió (%s)", type(exc).__name__)
        finally:
            # Si se cerró Sirius mientras puntuaba, ya no hay ventana a la que avisar. Nada al
            # diario: puede estar cerrado ya (ADR-253).
            with contextlib.suppress(RuntimeError):
                self.signals.finished.emit()
            self.done.set()
