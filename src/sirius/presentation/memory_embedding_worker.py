"""Las huellas de los recuerdos en segundo plano (pieza F de ADR-233, ADR-238).

La ventana lo lanza al abrirse y cada vez que se guarda, se corrige o se
confirma un recuerdo. Calcula las huellas que faltan con el modelo de huellas
de Ollama, para que la búsqueda por significado encuentre también lo nuevo.
Para cuando el propietario escribe, para que el turno vaya antes, y sigue
después.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.memory_search import MemoryEmbeddingService
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class MemoryEmbeddingWorkerSignals(QObject):
    finished = Signal()


class MemoryEmbeddingWorker(QRunnable):
    """Calcula las huellas que faltan, fuera del hilo de la ventana."""

    def __init__(self, service: MemoryEmbeddingService, *, warm_up: bool = False) -> None:
        super().__init__()
        self._service = service
        self._warm_up = warm_up
        self._stop = threading.Event()
        self.signals = MemoryEmbeddingWorkerSignals()

    def stop(self) -> None:
        """Que pare antes del siguiente grupo de recuerdos; el que está calculando lo termina."""
        self._stop.set()

    def run(self) -> None:
        try:
            if self._service.embed_pending(should_stop=self._stop.is_set) == 0 and self._warm_up:
                self._service.warm_up()
        except Exception as exc:  # las huellas nunca pueden romper la ventana
            _logger.error("Las huellas se interrumpieron (%s)", type(exc).__name__)
        finally:
            self.signals.finished.emit()
