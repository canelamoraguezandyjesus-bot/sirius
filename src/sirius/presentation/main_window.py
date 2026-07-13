"""Ventana principal de Sirius 0.1."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sirius.application.api_key_settings import ApiKeySettingsError, ApiKeySettingsUseCase
from sirius.application.get_conversation_history import (
    ConversationNotInitializedError,
    GetConversationHistoryUseCase,
)
from sirius.application.send_message import SendMessageResult, SendMessageUseCase
from sirius.config.llm_provider_settings import (
    LLMProviderConfigurationError,
    LLMProviderKind,
    resolve_openai_provider_settings,
    resolve_provider_kind,
)
from sirius.config.settings import load_settings, save_settings
from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.presentation.conversation_worker import SendMessageWorker


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
        *,
        show_warning: Callable[[str, str], None] | None = None,
        show_information: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__()
        self._send_message_use_case = send_message_use_case
        self._get_history_use_case = get_history_use_case
        self._api_key_settings_use_case = api_key_settings_use_case
        # Dialogs are shown only through these two seams: production defaults
        # to real QMessageBox popups, but tests inject a recording double so
        # scripts/check.ps1 never opens a real window on the desktop.
        self._show_warning = show_warning or self._default_show_warning
        self._show_information = show_information or self._default_show_information
        self._is_sending = False
        self._close_requested = False
        self._active_operation_id: str | None = None
        self._streaming_item: QListWidgetItem | None = None
        self._streaming_text = ""
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

    # --- Conversación --------------------------------------------------

    def _build_conversation_tab(self) -> QWidget:
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
        if self._is_sending:
            return

        self._is_sending = True
        self._active_operation_id = str(uuid.uuid4())
        self._streaming_item = None
        self._streaming_text = ""
        self.send_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.message_input.setEnabled(False)
        self.status_label.setText("Sirius está pensando...")
        self.error_label.setText("")

        self._append_message_item(MessageRole.USER, text)
        self.message_input.clear()

        worker = SendMessageWorker(self._send_message_use_case, text, self._active_operation_id)
        worker.signals.delta.connect(self._on_delta)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.crashed.connect(self._on_crashed)
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
        self._streaming_item = None
        self._streaming_text = ""
        self.send_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        self.message_input.setEnabled(True)
        self.status_label.setText("")
        if self._close_requested:
            self._close_requested = False
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Request cancellation and defer closing instead of blocking.

        The worker keeps running to completion on its own thread; once it
        finishes, ``_finish_sending`` notices the pending request and closes
        the window from the main thread. Nothing is killed and no write is
        left half-done.
        """
        if self._is_sending:
            self._close_requested = True
            if self._active_operation_id is not None:
                self._send_message_use_case.cancel(self._active_operation_id)
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
        layout.addStretch()
        return container

    def _refresh_key_status_label(self) -> None:
        has_key = self._api_key_settings_use_case.has_key()
        self.key_status_label.setText(
            "Clave de API: configurada." if has_key else "Clave de API: no configurada."
        )

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

        self._refresh_key_status_label()
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

        self._refresh_key_status_label()
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
