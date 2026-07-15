"""Main window variant with validate-before-save credential handling."""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QPushButton

from sirius.application.validate_and_save_api_key import ValidateAndSaveApiKeyUseCase
from sirius.presentation.credential_validation_worker import CredentialValidationWorker
from sirius.presentation.main_window import MainWindow


class ValidatedMainWindow(MainWindow):
    """Integrate credential validation without exposing the secret store to Qt."""

    def __init__(
        self,
        *args: object,
        validate_and_save_api_key_use_case: ValidateAndSaveApiKeyUseCase,
        **kwargs: object,
    ) -> None:
        self._validate_and_save_api_key_use_case = validate_and_save_api_key_use_case
        self._is_credential_busy = False
        self._active_credential_worker: CredentialValidationWorker | None = None
        self._save_key_button: QPushButton | None = None
        super().__init__(*args, **kwargs)

    def _save_api_key(self) -> None:
        if self._is_credential_busy:
            return

        key = self.api_key_input.text().strip()
        model = self.model_input.text().strip()
        if not key:
            self.key_feedback_label.setText("")
            self._show_warning("Falta la clave", "Escribe una clave antes de guardarla.")
            return
        if not model:
            self.key_feedback_label.setText("")
            self._show_warning("Falta el modelo", "Escribe el modelo que debe validar la clave.")
            return

        sender = self.sender()
        self._save_key_button = sender if isinstance(sender, QPushButton) else None
        self._set_credential_controls_enabled(False)
        self._is_credential_busy = True
        self.key_feedback_label.setText("Validando clave con el proveedor...")

        worker = CredentialValidationWorker(
            self._validate_and_save_api_key_use_case,
            key,
            model,
        )
        worker.signals.succeeded.connect(self._on_credential_validation_succeeded)
        worker.signals.failed.connect(self._on_credential_validation_failed)
        self._active_credential_worker = worker
        self._thread_pool.start(worker)

    def _set_credential_controls_enabled(self, enabled: bool) -> None:
        self.api_key_input.setEnabled(enabled)
        self.model_input.setEnabled(enabled)
        self.provider_combo.setEnabled(enabled)
        if self._save_key_button is not None:
            self._save_key_button.setEnabled(enabled)

    def _finish_credential_validation(self) -> None:
        self._is_credential_busy = False
        self._active_credential_worker = None
        self._set_credential_controls_enabled(True)
        if self._close_requested:
            self._close_requested = False
            self.close()

    def _on_credential_validation_succeeded(self) -> None:
        self.api_key_input.clear()
        refreshed = self._refresh_key_status_label()
        self._finish_credential_validation()
        if refreshed and not self._close_requested:
            self.key_feedback_label.setText(
                "Clave validada y guardada. Reinicia Sirius para activar el proveedor."
            )

    def _on_credential_validation_failed(self, message: str) -> None:
        self.api_key_input.clear()
        self._finish_credential_validation()
        if not self._close_requested:
            self.key_feedback_label.setText(message)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._is_credential_busy:
            self._close_requested = True
            event.ignore()
            return
        super().closeEvent(event)
