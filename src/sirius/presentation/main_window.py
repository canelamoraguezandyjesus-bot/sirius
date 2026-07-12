"""Ventana principal de Sirius 0.1."""

from __future__ import annotations

from PySide6.QtCore import Qt
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

from sirius.config.settings import load_settings, save_settings


class MainWindow(QMainWindow):
    """Ventana inicial de configuración de Sirius."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Sirius 0.1")
        self.resize(900, 620)

        title = QLabel("Configuración inicial de Sirius")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Vamos a preparar los datos básicos antes de comenzar.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Cómo quieres que Sirius te llame")

        self.data_path_input = QLineEdit()

        # Cargar la configuración guardada
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

        self.setCentralWidget(container)

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
