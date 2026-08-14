"""Panel compacto de grabación, escenas y marcas.

§6.1 de ``SIRIUS-MODEL-STUDIO-UI-001``: los controles de captura forman parte de
Model Studio pero **no saturan la barra principal**, así que viven en un panel
desplegable que se abre desde un único icono.

Como el resto de la superficie, esto es solo una vista: recibe estado por
métodos y avisa de intenciones por señales. No conoce OBS, ni el puerto de
captura, ni la lista blanca de escenas.

La parada de emergencia **no** vive aquí. Está en la barra inferior, siempre a
mano mientras se graba, porque el criterio de aceptación 11 exige que quede
accesible durante una grabación y abrir un panel para encontrarla no lo es.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, SignalInstance
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sirius.domain.model_studio import StudioCaptureState
from sirius.presentation.model_studio import theme

_SCENE_BUTTON_PROPERTY = "sceneId"


def format_elapsed(seconds: float | None) -> str:
    """Cronómetro en ``mm:ss``. Sin dato, guiones en vez de un cero engañoso."""
    if seconds is None:
        return "--:--"
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class StudioCapturePanel(QFrame):
    """Controles de grabación, escenas y marcas."""

    record_clicked = Signal()
    stop_clicked = Signal()
    pause_clicked = Signal()
    resume_clicked = Signal()
    mark_clicked = Signal()
    scene_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("studioCapturePanel")
        self._scene_buttons: list[QPushButton] = []
        self._state = StudioCaptureState.DESACTIVADO

        self.state_label = QLabel("")
        state_font = QFont()
        state_font.setPointSize(theme.FONT_STATE_PT)
        state_font.setBold(True)
        state_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        self.state_label.setFont(state_font)
        self.state_label.setAccessibleName("Estado del sistema de grabación")

        self.elapsed_label = QLabel(format_elapsed(None))
        elapsed_font = QFont()
        elapsed_font.setPointSize(theme.FONT_ASIDE_VALUE_PT)
        self.elapsed_label.setFont(elapsed_font)
        self.elapsed_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        self.elapsed_label.setAccessibleName("Tiempo grabado")

        self.record_button = self._action("Grabar", self.record_clicked)
        self.stop_button = self._action("Detener", self.stop_clicked)
        self.pause_button = self._action("Pausar", self.pause_clicked)
        self.resume_button = self._action("Reanudar", self.resume_clicked)
        self.mark_button = self._action("Marcar momento", self.mark_clicked)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName("studioCaptureMessage")
        self.message_label.setVisible(False)

        self.scenes_container = QWidget()
        self._scenes_layout = QVBoxLayout(self.scenes_container)
        self._scenes_layout.setContentsMargins(0, 0, 0, 0)
        self._scenes_layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self.state_label)
        header.addStretch(1)
        header.addWidget(self.elapsed_label)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addWidget(self.record_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.pause_button)
        buttons.addWidget(self.resume_button)
        buttons.addWidget(self.mark_button)
        buttons.addStretch(1)

        scenes_title = QLabel("ESCENAS AUTORIZADAS")
        title_font = QFont()
        title_font.setPointSize(theme.FONT_ASIDE_TITLE_PT)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.3)
        scenes_title.setFont(title_font)
        scenes_title.setStyleSheet(f"color: {theme.TEXT_MUTED};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addLayout(buttons)
        layout.addWidget(scenes_title)
        layout.addWidget(self.scenes_container)
        layout.addWidget(self.message_label)

        self.setStyleSheet(self._style_sheet())
        self.set_state(StudioCaptureState.DESACTIVADO)

    def _action(self, label: str, signal: SignalInstance) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("studioCaptureAction")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(label)
        button.setToolTip(label)
        button.clicked.connect(signal.emit)
        return button

    def _style_sheet(self) -> str:
        return f"""
        QFrame#studioCapturePanel {{
            background-color: {theme.SURFACE_RAISED};
            border: 1px solid {theme.HAIRLINE};
            border-radius: 12px;
        }}
        QPushButton#studioCaptureAction, QPushButton#studioSceneButton {{
            background-color: transparent;
            border: 1px solid {theme.HAIRLINE};
            border-radius: 8px;
            padding: 6px 12px;
            color: {theme.TEXT_SECONDARY};
        }}
        QPushButton#studioCaptureAction:hover:enabled,
        QPushButton#studioSceneButton:hover:enabled {{
            border: 1px solid {theme.ACCENT};
            color: {theme.TEXT_PRIMARY};
        }}
        QPushButton#studioSceneButton[active="true"] {{
            border: 1px solid {theme.ACCENT};
            color: {theme.ACCENT};
        }}
        QLabel#studioCaptureMessage {{
            color: {theme.TEXT_SECONDARY};
        }}
        """

    # --- Datos que entran ------------------------------------------------

    def set_scenes(self, scenes: list[tuple[str, str]]) -> None:
        """Escenas autorizadas, como pares ``(identificador, nombre visible)``.

        Solo se pintan las de la lista blanca: una escena que exista en el
        programa de grabación pero no esté autorizada no puede aparecer aquí,
        porque tampoco se podría activar.
        """
        for button in self._scene_buttons:
            self._scenes_layout.removeWidget(button)
            button.deleteLater()
        self._scene_buttons.clear()

        for scene_id, display_name in scenes:
            button = QPushButton(display_name)
            button.setObjectName("studioSceneButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAccessibleName(f"Cambiar a {display_name}")
            button.setToolTip(f"Cambiar a {display_name}")
            button.setProperty(_SCENE_BUTTON_PROPERTY, scene_id)
            button.clicked.connect(
                lambda _checked=False, identifier=scene_id: self.scene_selected.emit(identifier)
            )
            self._scenes_layout.addWidget(button)
            self._scene_buttons.append(button)
        self.set_state(self._state)

    def set_active_scene(self, scene_id: str | None) -> None:
        for button in self._scene_buttons:
            active = button.property(_SCENE_BUTTON_PROPERTY) == scene_id
            button.setProperty("active", "true" if active else "false")
            # Qt no repinta solo cuando cambia una propiedad usada por el estilo.
            button.style().unpolish(button)
            button.style().polish(button)

    def set_elapsed(self, seconds: float | None) -> None:
        self.elapsed_label.setText(format_elapsed(seconds))

    def set_message(self, message: str) -> None:
        self.message_label.setText(message)
        self.message_label.setVisible(bool(message))

    def set_state(self, state: StudioCaptureState) -> None:
        """Ajusta qué se puede pulsar según lo que el backend haya confirmado."""
        self._state = state
        self.state_label.setText(state.label)
        self.state_label.setStyleSheet(
            f"color: {theme.RECORDING};"
            if state.is_recording_confirmed
            else f"color: {theme.TEXT_SECONDARY};"
        )

        connected = state not in (StudioCaptureState.DESACTIVADO, StudioCaptureState.ERROR)
        recording = state is StudioCaptureState.GRABANDO
        paused = state is StudioCaptureState.PAUSADO
        # En INICIANDO, DETENIENDO, CAMBIANDO e INCIERTO no se ofrece nada: hay
        # una orden en vuelo y no se sabe todavía en qué va a quedar.
        settled = state in (
            StudioCaptureState.PREPARADO,
            StudioCaptureState.GRABANDO,
            StudioCaptureState.PAUSADO,
        )

        self.record_button.setEnabled(settled and state is StudioCaptureState.PREPARADO)
        self.stop_button.setEnabled(settled and (recording or paused))
        self.pause_button.setEnabled(settled and recording)
        self.resume_button.setEnabled(settled and paused)
        # Marcar solo tiene sentido durante una grabación confirmada: apuntaría
        # a un vídeo que no existe.
        self.mark_button.setEnabled(recording)
        for button in self._scene_buttons:
            button.setEnabled(connected and settled)

        if not recording and not paused:
            self.set_elapsed(None)

    @property
    def state(self) -> StudioCaptureState:
        return self._state

    def scene_ids(self) -> list[str]:
        """Escenas que se están ofreciendo. Pensado para las pruebas."""
        return [str(button.property(_SCENE_BUTTON_PROPERTY)) for button in self._scene_buttons]
