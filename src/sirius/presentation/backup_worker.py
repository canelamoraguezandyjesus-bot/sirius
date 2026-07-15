"""Qt background workers for backup creation, validation, and restoration.

Mirrors ``conversation_worker.py``: every use case call runs on a dedicated
``QThreadPool``, never the GUI thread. Results and safe error messages travel
back to the main thread exclusively through Qt signals (queued automatically
across threads), so a worker's ``run()`` never touches a widget directly.

``BackupError`` and its subclasses are the *expected* outcome of an invalid
password, a tampered file, or a failed restoration; their messages are
documented as safe to show verbatim (``sirius.ports.backup.BackupError``:
"Messages are safe: they never include the backup password or decrypted
content."). Any other exception is treated as a genuine crash: logged with
its type only, and reported to the user with a generic, safe message.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.create_backup import CreateBackupUseCase
from sirius.application.restore_backup import RestoreBackupUseCase
from sirius.application.validate_backup import ValidateBackupUseCase
from sirius.infrastructure.logging import get_logger
from sirius.ports.backup import BackupError

_logger = get_logger(__name__)

_GENERIC_FAILURE_MESSAGE = "No se pudo completar la operación. Inténtalo de nuevo."


class CreateBackupWorkerSignals(QObject):
    """Signals emitted by ``CreateBackupWorker``."""

    succeeded = Signal(object)  # BackupResult
    failed = Signal(str)


class CreateBackupWorker(QRunnable):
    """Runs ``CreateBackupUseCase.create_backup`` on a worker thread."""

    def __init__(self, use_case: CreateBackupUseCase, password: str) -> None:
        super().__init__()
        self._use_case = use_case
        self._password = password
        self.signals = CreateBackupWorkerSignals()

    def run(self) -> None:
        try:
            result = self._use_case.create_backup(self._password)
        except BackupError as exc:
            _logger.warning("Creación de copia rechazada (%s)", type(exc).__name__)
            self.signals.failed.emit(str(exc))
        except Exception as exc:  # A worker-boundary catch: report, never crash the pool thread.
            _logger.error(
                "Creación de copia interrumpida por un error inesperado (%s)", type(exc).__name__
            )
            self.signals.failed.emit(_GENERIC_FAILURE_MESSAGE)
        else:
            self.signals.succeeded.emit(result)


class ValidateBackupWorkerSignals(QObject):
    """Signals emitted by ``ValidateBackupWorker``."""

    succeeded = Signal(object)  # BackupValidationResult
    failed = Signal(str)


class ValidateBackupWorker(QRunnable):
    """Runs ``ValidateBackupUseCase.validate_backup`` on a worker thread."""

    def __init__(self, use_case: ValidateBackupUseCase, backup_path: Path, password: str) -> None:
        super().__init__()
        self._use_case = use_case
        self._backup_path = backup_path
        self._password = password
        self.signals = ValidateBackupWorkerSignals()

    def run(self) -> None:
        try:
            result = self._use_case.validate_backup(self._backup_path, self._password)
        except BackupError as exc:
            _logger.warning("Validación de copia rechazada (%s)", type(exc).__name__)
            self.signals.failed.emit(str(exc))
        except Exception as exc:
            _logger.error(
                "Validación de copia interrumpida por un error inesperado (%s)", type(exc).__name__
            )
            self.signals.failed.emit(_GENERIC_FAILURE_MESSAGE)
        else:
            self.signals.succeeded.emit(result)


class RestoreBackupWorkerSignals(QObject):
    """Signals emitted by ``RestoreBackupWorker``."""

    succeeded = Signal(object)  # BackupRestoreResult
    failed = Signal(str)


class RestoreBackupWorker(QRunnable):
    """Runs ``RestoreBackupUseCase.restore_backup`` on a worker thread.

    Always called with ``confirmed=True``: the destructive confirmation
    happens on the GUI thread, before this worker is ever constructed.
    """

    def __init__(self, use_case: RestoreBackupUseCase, backup_path: Path, password: str) -> None:
        super().__init__()
        self._use_case = use_case
        self._backup_path = backup_path
        self._password = password
        self.signals = RestoreBackupWorkerSignals()

    def run(self) -> None:
        try:
            result = self._use_case.restore_backup(
                self._backup_path, self._password, confirmed=True
            )
        except BackupError as exc:
            _logger.warning("Restauración rechazada (%s)", type(exc).__name__)
            self.signals.failed.emit(str(exc))
        except Exception as exc:
            _logger.error(
                "Restauración interrumpida por un error inesperado (%s)", type(exc).__name__
            )
            self.signals.failed.emit(_GENERIC_FAILURE_MESSAGE)
        else:
            self.signals.succeeded.emit(result)
