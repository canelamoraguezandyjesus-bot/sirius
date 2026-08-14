"""Ajustes rápidos de Model Studio: qué voz usa Sirius.

Elegir una voz por su nombre es imposible: «onyx» y «sage» no significan nada
hasta que se oyen. Por eso este diálogo no es una lista y ya —cada voz se puede
probar antes de adoptarla, y lo que se oye es la que se llevará puesta—.

Solo la voz. Ni volumen ni dispositivo: en Windows la reproducción va por el
reproductor del sistema, que no expone volumen propio, y un control que no
controla nada es peor que no tenerlo.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sirius.presentation.model_studio import theme

TITULO = "Ajustes de Model Studio"


class StudioSettingsDialog(QDialog):
    """Elige la voz de Sirius, con un botón para oírla antes de decidir."""

    test_requested = Signal(str)

    def __init__(
        self,
        voices: Sequence[str],
        current: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(TITULO)
        self.setObjectName("studioSettingsDialog")
        self.setModal(True)

        titulo = QLabel("VOZ DE SIRIUS")
        titulo.setObjectName("studioSettingsTitle")

        ayuda = QLabel(
            "Selecciona una y pulsa «Probar» para oírla. La que dejes elegida "
            "al aceptar es la que se queda."
        )
        ayuda.setWordWrap(True)
        ayuda.setObjectName("studioSettingsHelp")

        self.voice_list = QListWidget()
        self.voice_list.setObjectName("studioVoiceList")
        self.voice_list.setAccessibleName("Voces disponibles")
        for voice in voices:
            item = QListWidgetItem(voice)
            self.voice_list.addItem(item)
            if voice == current:
                self.voice_list.setCurrentItem(item)
        if self.voice_list.currentItem() is None and voices:
            self.voice_list.setCurrentRow(0)

        self.test_button = QPushButton("Probar")
        self.test_button.setObjectName("studioSettingsTest")
        self.test_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_button.setAccessibleName("Probar la voz seleccionada")
        self.test_button.clicked.connect(self._emit_test)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(self.test_button)
        fila.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(titulo)
        layout.addWidget(ayuda)
        layout.addWidget(self.voice_list, 1)
        layout.addLayout(fila)
        layout.addWidget(self.buttons)

        self.setStyleSheet(self._style_sheet())

    @property
    def selected_voice(self) -> str:
        item = self.voice_list.currentItem()
        return item.text() if item is not None else ""

    def _emit_test(self) -> None:
        if self.selected_voice:
            self.test_requested.emit(self.selected_voice)

    def _style_sheet(self) -> str:
        return f"""
        QDialog#studioSettingsDialog {{
            background-color: {theme.BACKGROUND};
        }}
        QLabel#studioSettingsTitle {{
            color: {theme.TEXT_SECONDARY};
            font-weight: bold;
            letter-spacing: 1px;
        }}
        QLabel#studioSettingsHelp {{
            color: {theme.TEXT_MUTED};
        }}
        QListWidget#studioVoiceList {{
            background-color: {theme.SURFACE_RAISED};
            border: 1px solid {theme.HAIRLINE};
            border-radius: 6px;
            color: {theme.TEXT_PRIMARY};
            padding: 4px;
        }}
        QListWidget#studioVoiceList::item {{
            padding: 6px 8px;
            border-radius: 4px;
        }}
        QListWidget#studioVoiceList::item:selected {{
            background-color: {theme.ACCENT};
            color: {theme.BACKGROUND};
        }}
        QPushButton {{
            background-color: {theme.SURFACE_RAISED};
            border: 1px solid {theme.HAIRLINE};
            border-radius: 6px;
            color: {theme.TEXT_PRIMARY};
            padding: 6px 16px;
        }}
        QPushButton:hover {{
            border-color: {theme.ACCENT};
        }}
        """
