"""Pre-bootstrap data-location screen (B2b, D-10): default vs. advanced folder choice.

Shown only when ``DataLocationUseCase.resolve()`` says a first choice is
genuinely required (a brand-new install with no installation yet at the
default path) or when the external pointer file could not be trusted. Like
every other presentation module, it only ever talks to
``sirius.application.data_location.DataLocationUseCase`` — never
platformdirs, the pointer-file format, or a physical filesystem operation
directly (AGENTS.md: "No accedas a SQLite ... desde la interfaz").

No SQLite, logging, or composition happens while this window is open: the
caller (``sirius.main``) only builds those once ``resolved`` fires.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sirius.application.data_location import (
    DataLocationError,
    DataLocationUseCase,
    DataPathCheck,
    DataPathHasExistingInstallationError,
)

DEFAULT_PATH_INTRO_TEXT = (
    "Sirius guardará tu conversación, tu proyecto y tus recuerdos en esta "
    "carpeta de este equipo. Puedes continuar con la ubicación predeterminada "
    "o elegir otra en Opciones avanzadas."
)

RECOVERY_INTRO_TEXT = (
    "No se pudo leer el archivo que recuerda dónde están los datos de Sirius: "
    "puede estar dañado o incompleto.\n\n"
    "Elige de nuevo la ubicación: la ruta predeterminada de abajo, u otra "
    "carpeta mediante Opciones avanzadas. No se abrirá ninguna base de datos "
    "hasta que confirmes una ubicación válida."
)

ONEDRIVE_WARNING_TITLE = "Carpeta dentro de OneDrive"
ONEDRIVE_WARNING_TEXT = (
    "La carpeta elegida está dentro de OneDrive. La sincronización en la nube "
    "puede bloquear archivos o interferir con la base de datos local mientras "
    "Sirius está en uso.\n\n"
    "Sirius 0.1 no garantiza compatibilidad total con carpetas sincronizadas.\n\n"
    "¿Deseas continuar de todos modos?"
)

EXISTING_DATA_TITLE = "Esta carpeta ya tiene datos de Sirius"
ACCESS_ERROR_TITLE = "No se pudo usar esta carpeta"


class DataLocationWindow(QMainWindow):
    """First-run (or recovery) screen to accept the default path or pick another.

    Emits ``resolved`` exactly once, with the absolute path that was just
    validated and persisted. The caller is responsible for starting
    logging/persistence/composition and for closing this window.
    """

    resolved = Signal(str)

    def __init__(
        self,
        use_case: DataLocationUseCase,
        *,
        recovery: bool = False,
        show_warning: Callable[[str, str], None] | None = None,
        confirm_onedrive: Callable[[str, str], bool] | None = None,
        choose_folder: Callable[[], str] | None = None,
    ) -> None:
        super().__init__()
        self._use_case = use_case
        self._show_warning = show_warning or self._default_show_warning
        self._confirm_onedrive = confirm_onedrive or self._default_confirm_onedrive
        self._choose_folder = choose_folder or self._default_choose_folder

        self.setWindowTitle("Sirius 0.1 — Ubicación de los datos")
        self.resize(560, 360)

        title = QLabel("Dónde se guardarán tus datos")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        title.setFont(title_font)

        self.intro_label = QLabel(RECOVERY_INTRO_TEXT if recovery else DEFAULT_PATH_INTRO_TEXT)
        self.intro_label.setWordWrap(True)

        self.default_path_label = QLabel(str(use_case.default_path))
        self.default_path_label.setWordWrap(True)
        self.default_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.accept_default_button = QPushButton("Continuar con esta ubicación")
        self.accept_default_button.clicked.connect(self._handle_accept_default_clicked)
        self.accept_default_button.setDefault(True)
        self.accept_default_button.setAutoDefault(True)

        self.advanced_button = QPushButton("Opciones avanzadas: elegir otra carpeta...")
        self.advanced_button.clicked.connect(self._handle_choose_custom_clicked)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(title)
        layout.addWidget(self.intro_label)
        layout.addWidget(self.default_path_label)
        layout.addWidget(self.accept_default_button)
        layout.addWidget(self.advanced_button)
        layout.addWidget(self.status_label)
        layout.addStretch()
        self.setCentralWidget(container)

    def _default_show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _default_confirm_onedrive(self, title: str, text: str) -> bool:
        answer = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _default_choose_folder(self) -> str:
        return QFileDialog.getExistingDirectory(self, "Elegir carpeta de datos")

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.accept_default_button.setEnabled(enabled)
        self.advanced_button.setEnabled(enabled)

    def _handle_accept_default_clicked(self) -> None:
        self._resolve_candidate(self._use_case.default_path, is_default=True)

    def _handle_choose_custom_clicked(self) -> None:
        chosen = self._choose_folder()
        if not chosen:
            return
        self._resolve_candidate(Path(chosen), is_default=False)

    def _resolve_candidate(self, candidate: Path, *, is_default: bool) -> None:
        self.status_label.setText("")
        try:
            check = self._use_case.validate_candidate(candidate, is_default=is_default)
        except DataPathHasExistingInstallationError as exc:
            self._show_warning(EXISTING_DATA_TITLE, str(exc))
            return
        except DataLocationError as exc:
            self._show_warning(ACCESS_ERROR_TITLE, str(exc))
            return

        if check.is_onedrive and not self._confirm_onedrive(
            ONEDRIVE_WARNING_TITLE, ONEDRIVE_WARNING_TEXT
        ):
            return

        self._confirm(check)

    def _confirm(self, check: DataPathCheck) -> None:
        self._use_case.confirm(check)
        self._set_controls_enabled(False)
        self.status_label.setText(f"Ubicación confirmada: {check.path}")
        self.resolved.emit(str(check.path))
