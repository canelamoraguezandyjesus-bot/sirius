"""Ventana principal de Sirius 0.1."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRunnable, Qt, QThreadPool
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sirius.application.api_key_settings import ApiKeySettingsError, ApiKeySettingsUseCase
from sirius.application.create_backup import CreateBackupUseCase
from sirius.application.get_conversation_history import (
    ConversationNotInitializedError,
    GetConversationHistoryUseCase,
)
from sirius.application.project_continuity import ProjectContinuityUseCase
from sirius.application.restore_backup import RestoreBackupUseCase
from sirius.application.send_message import SendMessageResult, SendMessageUseCase
from sirius.application.validate_backup import ValidateBackupUseCase
from sirius.config.llm_provider_settings import (
    LLMProviderConfigurationError,
    LLMProviderKind,
    resolve_openai_provider_settings,
    resolve_provider_kind,
)
from sirius.config.settings import load_settings, save_settings
from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.infrastructure.logging import get_logger
from sirius.ports.backup import (
    BackupManifest,
    BackupRestoreResult,
    BackupResult,
    BackupValidationResult,
)
from sirius.presentation.backup_worker import (
    CreateBackupWorker,
    RestoreBackupWorker,
    ValidateBackupWorker,
)
from sirius.presentation.conversation_worker import SendMessageWorker
from sirius.presentation.project_continuity_widget import ProjectContinuityWidget

_logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Ventana principal de Sirius: conversación y configuración.

    Never receives a ``SecretStore`` and never calls ``get_secret``: the only
    secret-related dependency it holds is ``ApiKeySettingsUseCase``, whose
    API cannot return the key's value (AGENTS.md: "No accedas a ... secretos
    desde la interfaz").
    """

    def __init__(
        self,
        send_message_use_case: SendMessageUseCase,
        get_history_use_case: GetConversationHistoryUseCase,
        api_key_settings_use_case: ApiKeySettingsUseCase,
        project_continuity_use_case: ProjectContinuityUseCase,
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
        super().__init__()
        self._send_message_use_case = send_message_use_case
        self._get_history_use_case = get_history_use_case
        self._api_key_settings_use_case = api_key_settings_use_case
        self._project_continuity_use_case = project_continuity_use_case
        self._create_backup_use_case = create_backup_use_case
        self._validate_backup_use_case = validate_backup_use_case
        self._restore_backup_use_case = restore_backup_use_case
        # Not a use case: the minimal SQLAlchemy-lifecycle mechanism a safe
        # restoration needs (see ConversationDependencies' docstring). Called
        # right before RestoreBackupUseCase so the atomic file replace is not
        # blocked by this window's own pooled connections.
        self._close_database_connections = close_database_connections
        # Dialogs are shown only through these seams: production defaults to
        # real Qt dialogs, but tests inject recording/no-op doubles so
        # scripts/check.ps1 never opens a real window on the desktop.
        self._show_warning = show_warning or self._default_show_warning
        self._show_information = show_information or self._default_show_information
        self._confirm_restore = confirm_restore or self._default_confirm_restore
        self._choose_backup_file = choose_backup_file or self._default_choose_backup_file
        self._is_sending = False
        self._is_backup_busy = False
        self._close_requested = False
        self._active_operation_id: str | None = None
        self._streaming_item: QListWidgetItem | None = None
        self._streaming_text = ""
        # QThreadPool.start() does not keep a Python-level reference to a
        # QRunnable: without this, a worker whose run() finishes very
        # quickly can be garbage-collected before its queued cross-thread
        # signal is delivered, silently losing the result. Cleared once the
        # in-flight operation's slot has run. Kept separate per worker kind:
        # a send and a backup operation never run concurrently, but each
        # slot must only ever clear its own worker.
        self._active_send_worker: QRunnable | None = None
        self._active_backup_worker: QRunnable | None = None
        self._thread_pool = QThreadPool()

        self.setWindowTitle("Sirius 0.1")
        self.resize(900, 620)

        tabs = QTabWidget()
        tabs.addTab(self._build_conversation_tab(), "Conversación")
        tabs.addTab(self._build_settings_tab(), "Configuración")
        self.setCentralWidget(tabs)

        self._load_history()

    def _default_show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _default_show_information(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)

    def _default_confirm_restore(self, title: str, text: str) -> bool:
        answer = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _default_choose_backup_file(self, title: str) -> str:
        path_text, _ = QFileDialog.getOpenFileName(
            self, title, "", "Copias de Sirius (*.siriusbackup)"
        )
        return path_text

    # --- Conversación --------------------------------------------------

    def _build_conversation_tab(self) -> QWidget:
        self.project_continuity_widget = ProjectContinuityWidget(
            self._project_continuity_use_case, show_warning=self._show_warning
        )

        self.message_list = QListWidget()
        self.message_list.setAccessibleName("Historial de la conversación")

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Escribe un mensaje para Sirius")
        self.message_input.returnPressed.connect(self._handle_send_clicked)

        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self._handle_send_clicked)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self._handle_cancel_clicked)
        self.cancel_button.setVisible(False)

        input_row = QHBoxLayout()
        input_row.addWidget(self.message_input)
        input_row.addWidget(self.send_button)
        input_row.addWidget(self.cancel_button)

        self.status_label = QLabel("")
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.project_continuity_widget)
        layout.addWidget(self.message_list)
        layout.addLayout(input_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.error_label)
        return container

    def _load_history(self) -> None:
        self._replace_history_with_authoritative_state()

    def _replace_history_with_authoritative_state(self) -> None:
        """Rebuild the visible list from GetConversationHistoryUseCase.

        Used at startup and to reconcile after a cancelled or failed send: an
        optimistic/streamed message that never actually persisted disappears;
        one that did persist before the failure (e.g. the provider failed
        afterwards) stays, because it is really there.
        """
        self.message_list.clear()
        self._streaming_item = None
        try:
            messages = self._get_history_use_case.get_history()
        except ConversationNotInitializedError:
            self.error_label.setText("No se pudo cargar el historial de la conversación.")
            return

        for message in messages:
            self._append_message_item(message.role, message.content, message.status)

    def _append_message_item(
        self, role: MessageRole, content: str, status: MessageStatus = MessageStatus.COMPLETED
    ) -> QListWidgetItem:
        item = QListWidgetItem("")
        self._set_item_text(item, role, content, status)
        if role is MessageRole.SIRIUS:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        self.message_list.addItem(item)
        return item

    @staticmethod
    def _set_item_text(
        item: QListWidgetItem, role: MessageRole, content: str, status: MessageStatus
    ) -> None:
        prefix = "Tú" if role is MessageRole.USER else "Sirius"
        suffix = {
            MessageStatus.CANCELLED: " (cancelado)",
            MessageStatus.FAILED: " (fallido)",
        }.get(status, "")
        item.setText(f"{prefix}: {content}{suffix}")

    def _handle_send_clicked(self) -> None:
        text = self.message_input.text()
        if not text.strip():
            return
        if self._is_sending or self._is_backup_busy:
            return

        self._is_sending = True
        self._active_operation_id = str(uuid.uuid4())
        self._streaming_item = None
        self._streaming_text = ""
        self.send_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.message_input.setEnabled(False)
        self._set_backup_controls_enabled(False)
        self.status_label.setText("Sirius está pensando...")
        self.error_label.setText("")

        self._append_message_item(MessageRole.USER, text)
        self.message_input.clear()

        worker = SendMessageWorker(self._send_message_use_case, text, self._active_operation_id)
        worker.signals.delta.connect(self._on_delta)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.crashed.connect(self._on_crashed)
        self._active_send_worker = worker
        self._thread_pool.start(worker)

    def _handle_cancel_clicked(self) -> None:
        # Idempotent: disabling the button after the first click prevents
        # repeated calls, and SendMessageUseCase.cancel() is itself
        # idempotent even if called more than once for the same operation.
        if self._active_operation_id is None:
            return
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Cancelando...")
        self._send_message_use_case.cancel(self._active_operation_id)

    def _on_delta(self, text: str) -> None:
        self._streaming_text += text
        if self._streaming_item is None:
            self._streaming_item = self._append_message_item(MessageRole.SIRIUS, "")
        self._set_item_text(
            self._streaming_item, MessageRole.SIRIUS, self._streaming_text, MessageStatus.COMPLETED
        )

    def _on_finished(self, result: SendMessageResult) -> None:
        # ``result.sirius_message`` is the row SendMessageUseCase actually
        # persisted (COMPLETED with the full reply, or CANCELLED/FAILED with
        # whatever partial text streamed) — authoritative, no need to reload.
        if self._streaming_item is None:
            self._streaming_item = self._append_message_item(
                MessageRole.SIRIUS, result.sirius_message.content, result.sirius_message.status
            )
        else:
            self._set_item_text(
                self._streaming_item,
                MessageRole.SIRIUS,
                result.sirius_message.content,
                result.sirius_message.status,
            )

        operation_id = result.sirius_message.operation_id
        if result.outcome is MessageStatus.CANCELLED:
            self.error_label.setText("Envío cancelado.")
        elif result.outcome is MessageStatus.FAILED:
            self.error_label.setText(
                f"No se pudo completar el envío. Inténtalo de nuevo. (ref: {operation_id})"
            )
        self._finish_sending()

    def _on_crashed(self, error_message: str) -> None:
        del error_message  # not shown verbatim: keep the user-facing message safe and generic
        operation_id = self._active_operation_id
        self._replace_history_with_authoritative_state()
        self.error_label.setText(
            f"No se pudo completar el envío. Inténtalo de nuevo. (ref: {operation_id})"
        )
        self._finish_sending()

    def _finish_sending(self) -> None:
        self._is_sending = False
        self._active_operation_id = None
        self._active_send_worker = None
        self._streaming_item = None
        self._streaming_text = ""
        self.send_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        self.message_input.setEnabled(True)
        self.status_label.setText("")
        self._set_backup_controls_enabled(True)
        if self._close_requested:
            self._close_requested = False
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Request cancellation and defer closing instead of blocking.

        The worker keeps running to completion on its own thread; once it
        finishes, ``_finish_sending``/``_finish_backup_operation`` notices the
        pending request and closes the window from the main thread. Nothing
        is killed and no write is left half-done.
        """
        if self._is_sending:
            self._close_requested = True
            if self._active_operation_id is not None:
                self._send_message_use_case.cancel(self._active_operation_id)
            event.ignore()
            return
        if self._is_backup_busy:
            self._close_requested = True
            event.ignore()
            return
        super().closeEvent(event)

    # --- Configuración ---------------------------------------------------

    def _build_settings_tab(self) -> QWidget:
        title = QLabel("Configuración inicial de Sirius")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Vamos a preparar los datos básicos antes de comenzar.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Cómo quieres que Sirius te llame")

        self.data_path_input = QLineEdit()

        settings = load_settings()
        self.name_input.setText(settings.get("user_name", ""))
        self.data_path_input.setText(settings.get("data_path", "datos"))

        form = QFormLayout()
        form.addRow("Tu nombre:", self.name_input)
        form.addRow("Carpeta de datos:", self.data_path_input)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems([kind.value for kind in LLMProviderKind])
        try:
            current_provider = resolve_provider_kind(settings)
        except LLMProviderConfigurationError:
            current_provider = LLMProviderKind.FAKE
        self.provider_combo.setCurrentText(current_provider.value)

        self.model_input = QLineEdit()
        self.max_output_tokens_input = QLineEdit()
        self.budget_input = QLineEdit()
        try:
            provider_defaults = resolve_openai_provider_settings(settings)
        except LLMProviderConfigurationError:
            provider_defaults = resolve_openai_provider_settings({})
        self.model_input.setText(provider_defaults.model)
        self.max_output_tokens_input.setText(str(provider_defaults.max_output_tokens))
        self.budget_input.setText(str(provider_defaults.monthly_budget_usd))

        form.addRow("Proveedor:", self.provider_combo)
        form.addRow("Modelo:", self.model_input)
        form.addRow("Máximo de tokens de salida:", self.max_output_tokens_input)
        form.addRow("Presupuesto mensual (USD):", self.budget_input)

        save_button = QPushButton("Guardar configuración")
        save_button.clicked.connect(self._save_configuration)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Nueva clave de API de OpenAI")

        self.key_status_label = QLabel()
        self.key_feedback_label = QLabel("")
        self._refresh_key_status_label()

        save_key_button = QPushButton("Guardar clave")
        save_key_button.clicked.connect(self._save_api_key)
        delete_key_button = QPushButton("Eliminar clave")
        delete_key_button.clicked.connect(self._delete_api_key)

        key_form = QFormLayout()
        key_form.addRow("Clave de API de OpenAI:", self.api_key_input)

        key_buttons_row = QHBoxLayout()
        key_buttons_row.addWidget(save_key_button)
        key_buttons_row.addWidget(delete_key_button)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addWidget(save_button)
        layout.addLayout(key_form)
        layout.addLayout(key_buttons_row)
        layout.addWidget(self.key_status_label)
        layout.addWidget(self.key_feedback_label)
        layout.addWidget(self._build_backup_group())
        layout.addStretch()

        # The backup/recovery section grew this tab beyond the default
        # 900x620 window: wrap it (same tab, same controls, no new screen)
        # in a resizable scroll area so every control — including the
        # restore section — stays reachable by mouse and by keyboard.
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container)
        return scroll_area

    # --- Copia de seguridad y restauración --------------------------------

    def _build_backup_group(self) -> QGroupBox:
        group = QGroupBox("Copia de seguridad y restauración")
        layout = QVBoxLayout(group)

        layout.addWidget(self._build_create_backup_section())
        layout.addWidget(self._build_validate_backup_section())
        layout.addWidget(self._build_restore_backup_section())
        return group

    def _build_create_backup_section(self) -> QWidget:
        self.create_backup_password_input = QLineEdit()
        self.create_backup_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.create_backup_password_repeat_input = QLineEdit()
        self.create_backup_password_repeat_input.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Contraseña de la copia:", self.create_backup_password_input)
        form.addRow("Repite la contraseña:", self.create_backup_password_repeat_input)

        self.create_backup_button = QPushButton("Crear copia cifrada")
        self.create_backup_button.clicked.connect(self._handle_create_backup_clicked)

        self.create_backup_status_label = QLabel("")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addLayout(form)
        layout.addWidget(self.create_backup_button)
        layout.addWidget(self.create_backup_status_label)
        return container

    def _build_validate_backup_section(self) -> QWidget:
        self.validate_backup_path_input = QLineEdit()
        self.validate_backup_path_input.setPlaceholderText("Ningún archivo seleccionado")
        self.validate_backup_browse_button = QPushButton("Examinar...")
        self.validate_backup_browse_button.clicked.connect(
            self._handle_validate_backup_browse_clicked
        )

        path_row = QHBoxLayout()
        path_row.addWidget(self.validate_backup_path_input)
        path_row.addWidget(self.validate_backup_browse_button)

        self.validate_backup_password_input = QLineEdit()
        self.validate_backup_password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Archivo (.siriusbackup):", path_row)
        form.addRow("Contraseña de la copia:", self.validate_backup_password_input)

        self.validate_backup_button = QPushButton("Validar copia")
        self.validate_backup_button.clicked.connect(self._handle_validate_backup_clicked)

        self.validate_backup_result_label = QLabel("")
        self.validate_backup_result_label.setWordWrap(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addLayout(form)
        layout.addWidget(self.validate_backup_button)
        layout.addWidget(self.validate_backup_result_label)
        return container

    def _build_restore_backup_section(self) -> QWidget:
        self.restore_backup_path_input = QLineEdit()
        self.restore_backup_path_input.setPlaceholderText("Ningún archivo seleccionado")
        self.restore_backup_browse_button = QPushButton("Examinar...")
        self.restore_backup_browse_button.clicked.connect(
            self._handle_restore_backup_browse_clicked
        )

        path_row = QHBoxLayout()
        path_row.addWidget(self.restore_backup_path_input)
        path_row.addWidget(self.restore_backup_browse_button)

        self.restore_backup_password_input = QLineEdit()
        self.restore_backup_password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Archivo (.siriusbackup):", path_row)
        form.addRow("Contraseña de la copia:", self.restore_backup_password_input)

        self.restore_backup_button = QPushButton("Restaurar copia")
        self.restore_backup_button.clicked.connect(self._handle_restore_backup_clicked)

        self.restore_backup_status_label = QLabel("")
        self.restore_backup_feedback_label = QLabel("")
        self.restore_backup_feedback_label.setWordWrap(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addLayout(form)
        layout.addWidget(self.restore_backup_button)
        layout.addWidget(self.restore_backup_status_label)
        layout.addWidget(self.restore_backup_feedback_label)
        return container

    def _set_backup_controls_enabled(self, enabled: bool) -> None:
        self.create_backup_button.setEnabled(enabled)
        self.create_backup_password_input.setEnabled(enabled)
        self.create_backup_password_repeat_input.setEnabled(enabled)
        self.validate_backup_button.setEnabled(enabled)
        self.validate_backup_browse_button.setEnabled(enabled)
        self.validate_backup_path_input.setEnabled(enabled)
        self.validate_backup_password_input.setEnabled(enabled)
        self.restore_backup_button.setEnabled(enabled)
        self.restore_backup_browse_button.setEnabled(enabled)
        self.restore_backup_path_input.setEnabled(enabled)
        self.restore_backup_password_input.setEnabled(enabled)

    def _start_backup_operation(self) -> None:
        self._is_backup_busy = True
        self._set_backup_controls_enabled(False)
        self.send_button.setEnabled(False)
        self.message_input.setEnabled(False)

    def _finish_backup_operation(self) -> None:
        self._is_backup_busy = False
        self._active_backup_worker = None
        self._set_backup_controls_enabled(True)
        self.send_button.setEnabled(True)
        self.message_input.setEnabled(True)
        if self._close_requested:
            self._close_requested = False
            self.close()

    @staticmethod
    def _format_backup_summary(manifest: BackupManifest, size_bytes: int) -> str:
        return (
            f"Fecha: {manifest.created_at.isoformat()}\n"
            f"Versión de aplicación: {manifest.app_version}\n"
            f"Esquema: {manifest.schema_version}\n"
            f"Tamaño: {size_bytes:,} bytes"
        )

    # --- Crear copia -------------------------------------------------------

    def _handle_create_backup_clicked(self) -> None:
        if self._is_sending or self._is_backup_busy:
            return

        password = self.create_backup_password_input.text()
        repeat = self.create_backup_password_repeat_input.text()
        self.create_backup_password_input.clear()
        self.create_backup_password_repeat_input.clear()

        if not password:
            self._show_warning("Falta la contraseña", "Escribe una contraseña para la copia.")
            return
        if password != repeat:
            self._show_warning(
                "Las contraseñas no coinciden",
                "Escribe la misma contraseña en los dos campos.",
            )
            return

        self._start_backup_operation()
        self.create_backup_status_label.setText("Creando copia cifrada...")

        worker = CreateBackupWorker(self._create_backup_use_case, password)
        worker.signals.succeeded.connect(self._on_create_backup_succeeded)
        worker.signals.failed.connect(self._on_create_backup_failed)
        self._active_backup_worker = worker
        self._thread_pool.start(worker)

    def _on_create_backup_succeeded(self, result: BackupResult) -> None:
        # Captured before _finish_backup_operation() clears the flag: a
        # pending close must not pop up a new dialog once the window is on
        # its way out.
        should_notify = not self._close_requested
        self._finish_backup_operation()
        self.create_backup_status_label.setText("")
        if should_notify:
            self._show_information(
                "Copia creada",
                f"Copia cifrada creada correctamente en:\n{result.path}",
            )

    def _on_create_backup_failed(self, message: str) -> None:
        should_notify = not self._close_requested
        self._finish_backup_operation()
        self.create_backup_status_label.setText("")
        if should_notify:
            self._show_warning("No se pudo crear la copia", message)

    # --- Validar copia -------------------------------------------------------

    def _handle_validate_backup_browse_clicked(self) -> None:
        path_text = self._choose_backup_file("Seleccionar copia de seguridad")
        if path_text:
            self.validate_backup_path_input.setText(path_text)

    def _handle_validate_backup_clicked(self) -> None:
        if self._is_sending or self._is_backup_busy:
            return

        path_text = self.validate_backup_path_input.text().strip()
        password = self.validate_backup_password_input.text()
        self.validate_backup_password_input.clear()

        if not path_text:
            self._show_warning("Falta el archivo", "Selecciona un archivo .siriusbackup.")
            return
        if not password:
            self._show_warning("Falta la contraseña", "Escribe la contraseña de la copia.")
            return

        self._start_backup_operation()
        self.validate_backup_result_label.setText("Validando copia...")

        worker = ValidateBackupWorker(self._validate_backup_use_case, Path(path_text), password)
        worker.signals.succeeded.connect(self._on_validate_backup_succeeded)
        worker.signals.failed.connect(self._on_validate_backup_failed)
        self._active_backup_worker = worker
        self._thread_pool.start(worker)

    def _on_validate_backup_succeeded(self, result: BackupValidationResult) -> None:
        self._finish_backup_operation()
        self.validate_backup_result_label.setText(
            self._format_backup_summary(result.manifest, result.size_bytes)
        )

    def _on_validate_backup_failed(self, message: str) -> None:
        self._finish_backup_operation()
        self.validate_backup_result_label.setText(message)

    # --- Restaurar copia -----------------------------------------------------

    def _handle_restore_backup_browse_clicked(self) -> None:
        path_text = self._choose_backup_file("Seleccionar copia a restaurar")
        if path_text:
            self.restore_backup_path_input.setText(path_text)

    def _handle_restore_backup_clicked(self) -> None:
        if self._is_sending or self._is_backup_busy:
            return

        path_text = self.restore_backup_path_input.text().strip()
        password = self.restore_backup_password_input.text()
        self.restore_backup_password_input.clear()

        if not path_text:
            self._show_warning("Falta el archivo", "Selecciona un archivo .siriusbackup.")
            return
        if not password:
            self._show_warning("Falta la contraseña", "Escribe la contraseña de la copia.")
            return

        self._start_backup_operation()
        self.restore_backup_status_label.setText("Validando copia...")
        self.restore_backup_feedback_label.setText("")

        backup_path = Path(path_text)
        worker = ValidateBackupWorker(self._validate_backup_use_case, backup_path, password)
        worker.signals.succeeded.connect(
            lambda result: self._on_restore_validation_succeeded(result, backup_path, password)
        )
        worker.signals.failed.connect(self._on_restore_validation_failed)
        self._active_backup_worker = worker
        self._thread_pool.start(worker)

    def _on_restore_validation_succeeded(
        self, result: BackupValidationResult, backup_path: Path, password: str
    ) -> None:
        self.restore_backup_status_label.setText("")

        # A close was requested while the pre-validation was still running:
        # honor it instead of popping up a destructive confirmation dialog
        # for a window that is on its way out. _finish_backup_operation()
        # already closes the window when a close is pending.
        if self._close_requested:
            self._finish_backup_operation()
            return

        summary = self._format_backup_summary(result.manifest, result.size_bytes)
        confirmed = self._confirm_restore(
            "Confirmar restauración",
            "Esta acción sustituirá todos los datos actuales de Sirius por los de la "
            "copia seleccionada.\n\n"
            "Antes de reemplazar nada, Sirius creará automáticamente una copia de "
            "seguridad de los datos actuales.\n\n"
            "Si la copia que vas a restaurar es antigua, puede reintroducir información "
            "que ya habías eliminado.\n\n"
            "La clave de API de OpenAI no forma parte de la copia y no se restaurará: "
            "tendrás que volver a configurarla si hace falta.\n\n"
            f"{summary}\n\n"
            "¿Deseas continuar?",
        )
        if not confirmed:
            self._finish_backup_operation()
            self.restore_backup_feedback_label.setText("Restauración cancelada.")
            return

        self.restore_backup_status_label.setText("Restaurando...")
        # Must run before RestoreBackupUseCase: this window's own pooled
        # connections to sirius.db would otherwise block the atomic file
        # replace on Windows (confirmed empirically; see PLAN.md). If this
        # fails, the restore must never be attempted: restore the interface,
        # log only the exception type, and never show the raw exception.
        try:
            self._close_database_connections()
        except Exception as exc:
            _logger.error(
                "No se pudieron cerrar las conexiones antes de restaurar (%s)",
                type(exc).__name__,
            )
            self._finish_backup_operation()
            self.restore_backup_status_label.setText("")
            self.restore_backup_feedback_label.setText(
                "No se pudo preparar la restauración. Inténtalo de nuevo."
            )
            return

        worker = RestoreBackupWorker(self._restore_backup_use_case, backup_path, password)
        worker.signals.succeeded.connect(self._on_restore_backup_succeeded)
        worker.signals.failed.connect(self._on_restore_backup_failed)
        self._active_backup_worker = worker
        self._thread_pool.start(worker)

    def _on_restore_validation_failed(self, message: str) -> None:
        self._finish_backup_operation()
        self.restore_backup_status_label.setText("")
        self.restore_backup_feedback_label.setText(message)

    def _on_restore_backup_succeeded(self, result: BackupRestoreResult) -> None:
        # Deliberately not `_finish_backup_operation()`: the window is about
        # to close, and re-enabling now-obsolete controls would be pointless.
        self._is_backup_busy = False
        self._active_backup_worker = None
        self.restore_backup_status_label.setText("")
        message = "Los datos se restauraron correctamente."
        if result.safety_backup_path is not None:
            message += (
                "\n\nSe guardó una copia de seguridad de los datos anteriores en:\n"
                f"{result.safety_backup_path}"
            )
        message += "\n\nSirius se cerrará ahora. Ábrelo de nuevo para continuar."
        self._show_information("Restauración completada", message)
        self.close()

    def _on_restore_backup_failed(self, message: str) -> None:
        # The connections were already disposed before this attempt; that is
        # harmless even on failure (SQLAlchemy reconnects lazily on next use)
        # because RestoreBackupUseCase guarantees the file on disk is left
        # either untouched or correctly rolled back.
        self._finish_backup_operation()
        self.restore_backup_status_label.setText("")
        self.restore_backup_feedback_label.setText(message)

    def _refresh_key_status_label(self) -> bool:
        try:
            has_key = self._api_key_settings_use_case.has_key()
        except ApiKeySettingsError:
            self.key_status_label.setText("Clave de API: estado no disponible.")
            self.key_feedback_label.setText(
                "No se pudo consultar el almacén seguro de credenciales de Windows."
            )
            return False

        self.key_status_label.setText(
            "Clave de API: configurada." if has_key else "Clave de API: no configurada."
        )
        return True

    def _save_api_key(self) -> None:
        key = self.api_key_input.text().strip()
        if not key:
            self.key_feedback_label.setText("")
            self._show_warning("Falta la clave", "Escribe una clave antes de guardarla.")
            return
        try:
            self._api_key_settings_use_case.save_key(key)
        except ApiKeySettingsError:
            self.key_feedback_label.setText("")
            self._show_warning(
                "No se pudo guardar",
                "No se pudo guardar la clave en el almacén seguro de Windows.",
            )
            return
        finally:
            self.api_key_input.clear()

        if self._refresh_key_status_label():
            # An inline, non-modal status replaces a success dialog here: saving
            # a key is a frequent action and must never require a click to
            # dismiss (V7A: no QMessageBox for this specific confirmation).
            self.key_feedback_label.setText("Clave guardada.")

    def _delete_api_key(self) -> None:
        try:
            self._api_key_settings_use_case.delete_key()
        except ApiKeySettingsError:
            self.key_feedback_label.setText("")
            self._show_warning(
                "No se pudo eliminar",
                "No se pudo eliminar la clave del almacén seguro de Windows.",
            )
            return

        if self._refresh_key_status_label():
            self.key_feedback_label.setText("")
        self._show_information("Clave eliminada", "La clave de API se ha eliminado.")

    def _save_configuration(self) -> None:
        name = self.name_input.text().strip()
        data_path = self.data_path_input.text().strip()

        if not name:
            self._show_warning("Falta información", "Escribe primero tu nombre.")
            return

        try:
            max_output_tokens = int(self.max_output_tokens_input.text().strip())
            monthly_budget_usd = float(self.budget_input.text().strip())
        except ValueError:
            self._show_warning(
                "Valor inválido",
                "El máximo de tokens y el presupuesto mensual deben ser números.",
            )
            return

        if max_output_tokens <= 0 or monthly_budget_usd <= 0:
            self._show_warning(
                "Valor inválido",
                "El máximo de tokens y el presupuesto mensual deben ser mayores que cero.",
            )
            return

        data: dict[str, Any] = {
            "user_name": name,
            "data_path": data_path,
            "llm_provider": self.provider_combo.currentText(),
            "openai_model": self.model_input.text().strip(),
            "openai_max_output_tokens": max_output_tokens,
            "openai_monthly_budget_usd": monthly_budget_usd,
        }
        save_settings(data)

        self._show_information(
            "Configuración guardada",
            f"Sirius recordará que debe llamarte {name}.",
        )
