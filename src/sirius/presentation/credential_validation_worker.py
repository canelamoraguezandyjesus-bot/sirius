"""Qt worker for validating and storing a candidate API key."""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.validate_and_save_api_key import (
    CredentialValidationError,
    ValidateAndSaveApiKeyError,
    ValidateAndSaveApiKeyUseCase,
)
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class CredentialValidationWorkerSignals(QObject):
    succeeded = Signal()
    failed = Signal(str)


class CredentialValidationWorker(QRunnable):
    """Run provider validation away from the GUI thread."""

    def __init__(
        self,
        use_case: ValidateAndSaveApiKeyUseCase,
        credential: str,
        model: str,
    ) -> None:
        super().__init__()
        self._use_case = use_case
        self._credential = credential
        self._model = model
        self.signals = CredentialValidationWorkerSignals()

    def run(self) -> None:
        try:
            self._use_case.validate_and_save(self._credential, self._model)
        except (CredentialValidationError, ValidateAndSaveApiKeyError) as exc:
            _logger.warning("Validación o guardado de credencial rechazado (%s)", type(exc).__name__)
            self.signals.failed.emit(str(exc))
        except Exception as exc:
            _logger.error(
                "Validación de credencial interrumpida por un error inesperado (%s)",
                type(exc).__name__,
            )
            self.signals.failed.emit("No se pudo validar la clave. Inténtalo de nuevo.")
        else:
            self.signals.succeeded.emit()
