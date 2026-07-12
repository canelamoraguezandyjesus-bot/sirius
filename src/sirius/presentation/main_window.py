"""Ventana principal de Sirius 0.1."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
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

from sirius.application.get_conversation_history import (
    ConversationNotInitializedError,
    GetConversationHistoryUseCase,
)
from sirius.application.send_message import SendMessageResult, SendMessageUseCase
from sirius.config.settings import load_settings, save_settings
from sirius.domain.conversation import MessageRole
from sirius.presentation.conversation_worker import SendMessageWorker


class MainWindow(QMainWindow):
    """Ventana principal de Sirius: conversación y configuración."""

    def __init__(
        self,
        send_message_use_case: SendMessageUseCase,
        get_history_use_case: GetConversationHistoryUseCase,
    ) -> None:
        super().__init__()
        self._send_message_use_case = send_message_use_case
        self._get_history_use_case = get_history_use_case
        self._is_sending = False
        self._close_requested = False
        self._thread_pool = QThreadPool()

        self.setWindowTitle("Sirius 0.1")
        self.resize(900, 620)

        tabs = QTabWidget()
        tabs.addTab(self._build_conversation_tab(), "Conversación")
        tabs.addTab(self._build_settings_tab(), "Configuración")
        self.setCentralWidget(tabs)

        self._load_history()

    # --- Conversación --------------------------------------------------

    def _build_conversation_tab(self) -> QWidget:
        self.message_list = QListWidget()
        self.message_list.setAccessibleName("Historial de la conversación")

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Escribe un mensaje para Sirius")
        self.message_input.returnPressed.connect(self._handle_send_clicked)

        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self._handle_send_clicked)

        input_row = QHBoxLayout()
        input_row.addWidget(self.message_input)
        input_row.addWidget(self.send_button)

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

        Used at startup and to reconcile after a failed send: an optimistic
        message that never actually persisted disappears; one that did
        persist before the failure (e.g. the provider failed afterwards)
        stays, because it is really there.
        """
        self.message_list.clear()
        try:
            messages = self._get_history_use_case.get_history()
        except ConversationNotInitializedError:
            self.error_label.setText("No se pudo cargar el historial de la conversación.")
            return

        for message in messages:
            self._append_message_item(message.role, message.content)

    def _append_message_item(self, role: MessageRole, content: str) -> None:
        prefix = "Tú" if role is MessageRole.USER else "Sirius"
        item = QListWidgetItem(f"{prefix}: {content}")
        if role is MessageRole.SIRIUS:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        self.message_list.addItem(item)

    def _handle_send_clicked(self) -> None:
        text = self.message_input.text()
        if not text.strip():
            return
        if self._is_sending:
            return

        self._is_sending = True
        self.send_button.setEnabled(False)
        self.message_input.setEnabled(False)
        self.status_label.setText("Sirius está pensando...")
        self.error_label.setText("")

        self._append_message_item(MessageRole.USER, text)
        self.message_input.clear()

        worker = SendMessageWorker(self._send_message_use_case, text)
        worker.signals.succeeded.connect(self._on_send_succeeded)
        worker.signals.failed.connect(self._on_send_failed)
        self._thread_pool.start(worker)

    def _on_send_succeeded(self, result: SendMessageResult) -> None:
        self._append_message_item(result.sirius_message.role, result.sirius_message.content)
        self._finish_sending()

    def _on_send_failed(self, error_message: str) -> None:
        del error_message  # not shown verbatim: keep the user-facing message safe and generic
        # Reconcile the optimistic message against what actually persisted:
        # gone if the first write failed, kept if it succeeded before the
        # provider/second write failed.
        self._replace_history_with_authoritative_state()
        self.error_label.setText("No se pudo completar el envío. Inténtalo de nuevo.")
        self._finish_sending()

    def _finish_sending(self) -> None:
        self._is_sending = False
        self.send_button.setEnabled(True)
        self.message_input.setEnabled(True)
        self.status_label.setText("")
        if self._close_requested:
            self._close_requested = False
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Defer closing instead of blocking while a send is in flight.

        The worker keeps running to completion on its own thread; once it
        finishes, ``_finish_sending`` notices the pending request and closes
        the window from the main thread. Nothing is killed and no write is
        left half-done.
        """
        if self._is_sending:
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

        save_button = QPushButton("Guardar configuración")
        save_button.clicked.connect(self._save_configuration)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addWidget(save_button)
        layout.addStretch()
        return container

    def _save_configuration(self) -> None:
        name = self.name_input.text().strip()
        data_path = self.data_path_input.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Falta información",
                "Escribe primero tu nombre.",
            )
            return

        save_settings(
            {
                "user_name": name,
                "data_path": data_path,
            }
        )

        QMessageBox.information(
            self,
            "Configuración guardada",
            f"Sirius recordará que debe llamarte {name}.",
        )
