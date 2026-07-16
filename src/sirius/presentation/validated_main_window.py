"""Main window with validate-before-save credential handling."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QPushButton

from sirius.application.api_key_settings import ApiKeySettingsUseCase
from sirius.application.create_backup import CreateBackupUseCase
from sirius.application.get_conversation_history import GetConversationHistoryUseCase
from sirius.application.restore_backup import RestoreBackupUseCase
from sirius.application.send_message import SendMessageUseCase
from sirius.application.validate_and_save_api_key import ValidateAndSaveApiKeyUseCase
from sirius.application.validate_backup import ValidateBackupUseCase
from sirius.presentation.credential_validation_worker import CredentialValidationWorker
from sirius.presentation.main_window import MainWindow


class ValidatedMainWindow(MainWindow):
    """Validate an OpenAI key before storing it, without exposing the secret store."""

    def __init__(
        self,
        send_message_use_case: SendMessageUseCase,
        get_history_use_case: GetConversationHistoryUseCase,
        api_key_settings_use_case: ApiKeySettingsUseCase,
        validate_and_save_api_key_use_case: ValidateAndSaveApiKeyUseCase,
        create_backup_use_case: CreateBackupUseCase,
        validate_backup_use_case: ValidateBackupUseCase,
        restore_backup_use_case: RestoreBackupUseCase,
        close_database_connections: Callable[[], None],
        *,
        show_warning: Callable[[str, str], None] | None = None,
        show_information: Callable[[str, str], None] | None = None,
        confirm_restore: Callable[[str, str], bool] | None = None,
        choose_backup_file: Callable[[str], str] | None = None,
    ) -> None:
        self._validate_and_save_api_key_use_case = validate_and_save_api_key_use_case
        self._is_credential_busy = False
        self._active_credential_worker: CredentialValidationWorker | None = None
        self._save_key_button: QPushButton | None = None
        super().__init__(
            send_message_use_case=send_message_use_case,
            get_history_use_case=get_history_use_case,
            api_key_settings_use_case=api_key_settings_use_case,
            create_backup_use_case=create_backup_use_case,
            validate_backup_use_case=validate_backup_use_case,
            restore_backup_use_case=restore_backup_use_case,
            close_database_connections=close_database_connections,
            show_warning=show_warning,
            show_information=show_information,
            confirm_restore=confirm_restore,
            choose_backup_file=choose_backup_file,
        )

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

    def _delete_api_key(self) -> None:
        if self._is_credential_busy:
            return
        super()._delete_api_key()

    def _set_credential_controls_enabled(self, enabled: bool) -> None:
        self.api_key_input.setEnabled(enabled)
        self.model_input.setEnabled(enabled)
        self.provider_combo.setEnabled(enabled)
        if self._save_key_button is not None:
            self._save_key_button.setEnabled(enabled)

    def _finish_credential_validation(self) -> bool:
        close_requested = self._close_requested
        self._is_credential_busy = False
        self._active_credential_worker = None
        self._set_credential_controls_enabled(True)
        if close_requested:
            self._close_requested = False
            self.close()
        return close_requested

    def _on_credential_validation_succeeded(self) -> None:
        self.api_key_input.clear()
        refreshed = self._refresh_key_status_label()
        close_requested = self._finish_credential_validation()
        if refreshed and not close_requested:
            self.key_feedback_label.setText(
                "Clave validada y guardada. Reinicia Sirius para activar el proveedor."
            )

    def _on_credential_validation_failed(self, message: str) -> None:
        self.api_key_input.clear()
        close_requested = self._finish_credential_validation()
        if not close_requested:
            self.key_feedback_label.setText(message)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._is_credential_busy:
            self._close_requested = True
            event.ignore()
            return
        super().closeEvent(event)
