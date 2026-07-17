"""First-run onboarding: shown only while no API key is configured (RF-001, B2a).

Independent of ``MainWindow``: it needs none of the conversation or backup
surface, so inheriting from it would only grow that hierarchy for no reason.
Like every other presentation module, it never imports SQLite, OpenAI, or a
secret store directly (AGENTS.md: "No accedas a SQLite, OpenAI o secretos
desde la interfaz") — it only knows ``ApiKeySettingsUseCase`` and
``ValidateAndSaveApiKeyUseCase``, plus a composition-root-provided callable to
activate the real provider once a key is saved.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sirius.application.validate_and_save_api_key import ValidateAndSaveApiKeyUseCase
from sirius.presentation.credential_validation_worker import CredentialValidationWorker

DATA_POLICY_TEXT = (
    "La conversación, el proyecto, los recuerdos, las decisiones y la "
    "configuración no secreta se guardan localmente en este equipo. Para "
    "generar cada respuesta, se envía al proveedor únicamente el contexto "
    "necesario de la conversación.\n\n"
    "La clave de API se guarda mediante el almacén seguro de credenciales de "
    "Windows: no se guarda en la base de datos local, no se incluye en los "
    "registros de la aplicación y no forma parte de las exportaciones ni de "
    "las copias de seguridad ordinarias.\n\n"
    "Sirius 0.1 no utiliza herramientas externas ni ejecuta acciones fuera de "
    "esta conversación."
)
"""Single, centralized place for the first-run data-policy text (B2a §2):
one location to review and edit instead of phrases scattered across methods."""


class OnboardingWindow(QMainWindow):
    """Primera apertura: política de datos, proveedor/modelo y clave de API.

    Emits ``configured`` exactly once, after a candidate key has been
    validated against the provider, saved, and the real provider activated —
    never before. The caller (``sirius.main``) is responsible for showing the
    main conversation window and closing this one.
    """

    configured = Signal()

    def __init__(
        self,
        validate_and_save_api_key_use_case: ValidateAndSaveApiKeyUseCase,
        activate_llm_provider: Callable[[], None],
        default_provider: str,
        default_model: str,
        *,
        show_warning: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__()
        self._validate_and_save_api_key_use_case = validate_and_save_api_key_use_case
        self._activate_llm_provider = activate_llm_provider
        self._default_model = default_model
        self._show_warning = show_warning or self._default_show_warning
        self._is_credential_busy = False
        self._close_requested = False
        # QThreadPool.start() keeps no Python reference to a QRunnable: kept
        # here so a fast validation can't be garbage-collected before its
        # queued cross-thread signal is delivered (same reasoning as
        # MainWindow._active_send_worker).
        self._active_worker: CredentialValidationWorker | None = None
        self._thread_pool = QThreadPool()

        self.setWindowTitle("Sirius 0.1 — Primera configuración")
        self.resize(560, 420)

        title = QLabel("Antes de empezar")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        title.setFont(title_font)

        policy_label = QLabel(DATA_POLICY_TEXT)
        policy_label.setWordWrap(True)

        self.provider_label = QLabel(f"Proveedor: {default_provider}    Modelo: {default_model}")

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Clave de API de OpenAI")
        self.api_key_input.returnPressed.connect(self._handle_continue_clicked)

        self.continue_button = QPushButton("Continuar")
        self.continue_button.clicked.connect(self._handle_continue_clicked)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Clave de API:", self.api_key_input)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(title)
        layout.addWidget(policy_label)
        layout.addWidget(self.provider_label)
        layout.addLayout(form)
        layout.addWidget(self.continue_button)
        layout.addWidget(self.status_label)
        layout.addStretch()
        self.setCentralWidget(container)

    def _default_show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.api_key_input.setEnabled(enabled)
        self.continue_button.setEnabled(enabled)

    def _handle_continue_clicked(self) -> None:
        if self._is_credential_busy:
            return

        key = self.api_key_input.text().strip()
        if not key:
            self._show_warning("Falta la clave", "Escribe una clave antes de continuar.")
            return

        self._is_credential_busy = True
        self._set_controls_enabled(False)
        self.status_label.setText("Validando clave con el proveedor...")

        worker = CredentialValidationWorker(
            self._validate_and_save_api_key_use_case, key, self._default_model
        )
        worker.signals.succeeded.connect(self._on_validation_succeeded)
        worker.signals.failed.connect(self._on_validation_failed)
        self._active_worker = worker
        self._thread_pool.start(worker)

    def _finish_validation(self) -> bool:
        close_requested = self._close_requested
        self._is_credential_busy = False
        self._active_worker = None
        self._set_controls_enabled(True)
        if close_requested:
            self._close_requested = False
            self.close()
        return close_requested

    def _on_validation_succeeded(self) -> None:
        self.api_key_input.clear()
        self._activate_llm_provider()
        close_requested = self._finish_validation()
        if not close_requested:
            self.status_label.setText("")
            self.configured.emit()

    def _on_validation_failed(self, message: str) -> None:
        self.api_key_input.clear()
        close_requested = self._finish_validation()
        if not close_requested:
            self.status_label.setText(message)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Defer closing while a validation is in flight (same policy as
        ``ValidatedMainWindow``): never destroy the worker or this window
        while a request is still running.
        """
        if self._is_credential_busy:
            self._close_requested = True
            event.ignore()
            return
        super().closeEvent(event)
