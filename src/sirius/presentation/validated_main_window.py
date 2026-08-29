"""Main window with validate-before-save credential handling."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QPushButton

from sirius.application.api_key_settings import ApiKeySettingsUseCase
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_decision import ArchiveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.budget_status import GetBudgetStatusUseCase
from sirius.application.confirm_memory_suggestion import ConfirmMemorySuggestionUseCase
from sirius.application.correct_memory import CorrectMemoryUseCase
from sirius.application.create_backup import CreateBackupUseCase
from sirius.application.decision_origin import GetDecisionOriginUseCase
from sirius.application.delete_memory import DeleteMemoryUseCase
from sirius.application.detect_precedence_conflicts import DetectPrecedenceConflictsUseCase
from sirius.application.export_structured import ExportStructuredUseCase
from sirius.application.get_conversation_history import GetConversationHistoryUseCase
from sirius.application.historical_projects import HistoricalProjectsUseCase
from sirius.application.knowledge_overview import GetKnowledgeOverviewUseCase
from sirius.application.memory_origin import GetMemoryOriginUseCase
from sirius.application.project_continuity import ProjectContinuityUseCase
from sirius.application.project_lifecycle import ProjectLifecycleUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.propose_memory_suggestion import ProposeMemorySuggestionUseCase
from sirius.application.reject_memory_suggestion import RejectMemorySuggestionUseCase
from sirius.application.restore_backup import RestoreBackupUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.send_message import SendMessageUseCase
from sirius.application.studio_capture import StudioCaptureUseCase
from sirius.application.studio_voice import StudioVoiceUseCase
from sirius.application.supersede_decision import SupersedeDecisionUseCase
from sirius.application.tag_category import TagCategoryUseCase
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
        get_budget_status_use_case: GetBudgetStatusUseCase,
        api_key_settings_use_case: ApiKeySettingsUseCase,
        validate_and_save_api_key_use_case: ValidateAndSaveApiKeyUseCase,
        project_continuity_use_case: ProjectContinuityUseCase,
        project_lifecycle_use_case: ProjectLifecycleUseCase,
        save_manual_memory_use_case: SaveManualMemoryUseCase,
        get_memory_origin_use_case: GetMemoryOriginUseCase,
        correct_memory_use_case: CorrectMemoryUseCase,
        archive_memory_use_case: ArchiveMemoryUseCase,
        delete_memory_use_case: DeleteMemoryUseCase,
        propose_decision_use_case: ProposeDecisionUseCase,
        approve_decision_use_case: ApproveDecisionUseCase,
        get_decision_origin_use_case: GetDecisionOriginUseCase,
        supersede_decision_use_case: SupersedeDecisionUseCase,
        archive_decision_use_case: ArchiveDecisionUseCase,
        detect_precedence_conflicts_use_case: DetectPrecedenceConflictsUseCase,
        get_knowledge_overview_use_case: GetKnowledgeOverviewUseCase,
        propose_memory_suggestion_use_case: ProposeMemorySuggestionUseCase,
        confirm_memory_suggestion_use_case: ConfirmMemorySuggestionUseCase,
        reject_memory_suggestion_use_case: RejectMemorySuggestionUseCase,
        create_backup_use_case: CreateBackupUseCase,
        validate_backup_use_case: ValidateBackupUseCase,
        restore_backup_use_case: RestoreBackupUseCase,
        export_structured_use_case: ExportStructuredUseCase,
        historical_projects_use_case: HistoricalProjectsUseCase,
        close_database_connections: Callable[[], None],
        *,
        tag_category_use_case: TagCategoryUseCase | None = None,
        studio_voice_use_case: StudioVoiceUseCase | None = None,
        studio_capture_use_case: StudioCaptureUseCase | None = None,
        save_studio_voice: Callable[[str], None] | None = None,
        show_warning: Callable[[str, str], None] | None = None,
        show_information: Callable[[str, str], None] | None = None,
        confirm_restore: Callable[[str, str], bool] | None = None,
        choose_backup_file: Callable[[str], str] | None = None,
        open_containing_folder: Callable[[Path], None] | None = None,
        confirm_export: Callable[[str, str], bool] | None = None,
        choose_export_directory: Callable[[str], str] | None = None,
    ) -> None:
        self._validate_and_save_api_key_use_case = validate_and_save_api_key_use_case
        self._is_credential_busy = False
        self._active_credential_worker: CredentialValidationWorker | None = None
        self._save_key_button: QPushButton | None = None
        super().__init__(
            send_message_use_case=send_message_use_case,
            get_history_use_case=get_history_use_case,
            get_budget_status_use_case=get_budget_status_use_case,
            api_key_settings_use_case=api_key_settings_use_case,
            project_continuity_use_case=project_continuity_use_case,
            project_lifecycle_use_case=project_lifecycle_use_case,
            save_manual_memory_use_case=save_manual_memory_use_case,
            get_memory_origin_use_case=get_memory_origin_use_case,
            correct_memory_use_case=correct_memory_use_case,
            archive_memory_use_case=archive_memory_use_case,
            delete_memory_use_case=delete_memory_use_case,
            propose_decision_use_case=propose_decision_use_case,
            approve_decision_use_case=approve_decision_use_case,
            get_decision_origin_use_case=get_decision_origin_use_case,
            supersede_decision_use_case=supersede_decision_use_case,
            archive_decision_use_case=archive_decision_use_case,
            detect_precedence_conflicts_use_case=detect_precedence_conflicts_use_case,
            get_knowledge_overview_use_case=get_knowledge_overview_use_case,
            propose_memory_suggestion_use_case=propose_memory_suggestion_use_case,
            confirm_memory_suggestion_use_case=confirm_memory_suggestion_use_case,
            reject_memory_suggestion_use_case=reject_memory_suggestion_use_case,
            create_backup_use_case=create_backup_use_case,
            validate_backup_use_case=validate_backup_use_case,
            restore_backup_use_case=restore_backup_use_case,
            export_structured_use_case=export_structured_use_case,
            historical_projects_use_case=historical_projects_use_case,
            close_database_connections=close_database_connections,
            tag_category_use_case=tag_category_use_case,
            studio_voice_use_case=studio_voice_use_case,
            studio_capture_use_case=studio_capture_use_case,
            save_studio_voice=save_studio_voice,
            show_warning=show_warning,
            show_information=show_information,
            confirm_restore=confirm_restore,
            choose_backup_file=choose_backup_file,
            open_containing_folder=open_containing_folder,
            confirm_export=confirm_export,
            choose_export_directory=choose_export_directory,
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
