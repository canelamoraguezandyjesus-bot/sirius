"""Qt background worker for the structured export (B9b).

Mirrors ``backup_worker.py``: ``ExportStructuredUseCase.export_structured``
runs on a dedicated ``QThreadPool``, never the GUI thread. Results and safe
error messages travel back to the main thread exclusively through Qt signals.

``ExportError`` is the *expected* outcome of a write failure (e.g. a full or
read-only destination); its message is safe to show verbatim — the use case
never includes the API key or any other secret in it. Any other exception is
treated as a genuine crash: logged with its type only, and reported to the
user with a generic, safe message.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.export_structured import ExportStructuredUseCase
from sirius.infrastructure.logging import get_logger
from sirius.ports.export import ExportError

_logger = get_logger(__name__)

_GENERIC_FAILURE_MESSAGE = "No se pudo completar la operación. Inténtalo de nuevo."


class ExportWorkerSignals(QObject):
    """Signals emitted by ``ExportWorker``."""

    succeeded = Signal(object)  # Path
    failed = Signal(str)


class ExportWorker(QRunnable):
    """Runs ``ExportStructuredUseCase.export_structured`` on a worker thread."""

    def __init__(self, use_case: ExportStructuredUseCase, destination_dir: Path) -> None:
        super().__init__()
        self._use_case = use_case
        self._destination_dir = destination_dir
        self.signals = ExportWorkerSignals()

    def run(self) -> None:
        try:
            result = self._use_case.export_structured(self._destination_dir)
        except ExportError as exc:
            _logger.warning("Exportación rechazada (%s)", type(exc).__name__)
            self.signals.failed.emit(str(exc))
        except Exception as exc:  # A worker-boundary catch: report, never crash the pool thread.
            _logger.error(
                "Exportación interrumpida por un error inesperado (%s)", type(exc).__name__
            )
            self.signals.failed.emit(_GENERIC_FAILURE_MESSAGE)
        else:
            self.signals.succeeded.emit(result)
