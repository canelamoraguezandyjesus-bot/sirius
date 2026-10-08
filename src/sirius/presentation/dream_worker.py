"""El sueño en segundo plano (pieza G de ADR-233, ADR-239).

La ventana lo lanza al abrirse: sueña los días anteriores que aún no ha soñado,
con el modelo de este ordenador. Para cuando el propietario escribe, para que el
turno vaya antes; lo que falte lo sueña la próxima vez que se abra.
"""

from __future__ import annotations

import threading
from datetime import date

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.dream import DreamService
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class DreamWorkerSignals(QObject):
    #: Cuántos días soñó.
    finished = Signal(int)


class DreamWorker(QRunnable):
    """Sueña los días que faltan, fuera del hilo de la ventana."""

    def __init__(self, service: DreamService, *, today: date | None = None) -> None:
        super().__init__()
        self._service = service
        self._today = today
        self._stop = threading.Event()
        self.signals = DreamWorkerSignals()

    def stop(self) -> None:
        """Que pare antes del siguiente día; el que está soñando lo termina."""
        self._stop.set()

    def run(self) -> None:
        dreamed = 0
        try:
            dreamed = self._service.dream_pending(
                self._today or date.today(), should_stop=self._stop.is_set
            )
        except Exception as exc:  # soñar nunca puede romper la ventana
            _logger.error("El sueño se interrumpió (%s)", type(exc).__name__)
        finally:
            self.signals.finished.emit(dreamed)
