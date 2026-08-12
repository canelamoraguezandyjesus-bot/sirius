"""Superficie audiovisual de Model Studio.

Implementa ``SIRIUS-MODEL-STUDIO-UI-001``: columna izquierda con la presencia
de partículas y el contexto del proyecto, zona derecha con la conversación,
caja única de entrada, barra superior con estados separados de interacción y
captura, y barra inferior de iconos con tooltip.

Esta clase es **solo una vista**. No conoce casos de uso, ni proveedores, ni
persistencia: recibe datos por métodos y avisa de lo que el usuario quiere
hacer por señales. Esa es la razón de que el Módulo Voz y el Módulo Captura
puedan conectarse después sin tocarla, y de que cambiar de proveedor no llegue
nunca hasta aquí.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.domain.model_studio import StudioCaptureState, StudioInteractionState
from sirius.presentation.model_studio import theme
from sirius.presentation.model_studio.capture_panel import StudioCapturePanel
from sirius.presentation.model_studio.icons import studio_icon
from sirius.presentation.model_studio.presence_widget import PresenceWidget

_INPUT_PLACEHOLDER = "Escribe o habla con Sirius…"
_PENDING_TOOLTIP_SUFFIX = " · todavía no disponible"

_SPEAKER_LABELS: dict[MessageRole, str] = {
    MessageRole.USER: "TÚ",
    MessageRole.SIRIUS: "SIRIUS",
}


def compose_body(content: str | None, status: MessageStatus) -> str:
    """Texto visible de un mensaje, con el sufijo de estado si lo hay.

    Mismo criterio que la interfaz técnica: cancelado y fallido se anuncian en
    lenguaje claro, y un mensaje redactado nunca imprime ``None``.
    """
    suffix = {
        MessageStatus.CANCELLED: " (cancelado)",
        MessageStatus.FAILED: " (fallido)",
    }.get(status, "")
    shown = "(mensaje redactado)" if status is MessageStatus.REDACTED else content
    return f"{shown}{suffix}"


class _MessageWidget(QWidget):
    """Un turno de la conversación: etiqueta y cuerpo. Sin avatares (§4)."""

    def __init__(self, role: MessageRole, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._role = role

        speaker = QLabel(_SPEAKER_LABELS[role])
        speaker_font = QFont()
        speaker_font.setPointSize(theme.FONT_SPEAKER_PT)
        speaker_font.setBold(True)
        speaker_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        speaker.setFont(speaker_font)
        speaker.setStyleSheet(
            f"color: {theme.ACCENT};"
            if role is MessageRole.SIRIUS
            else f"color: {theme.TEXT_MUTED};"
        )

        self._body = QLabel("")
        body_font = QFont()
        body_font.setPointSize(theme.FONT_MESSAGE_PT)
        self._body.setFont(body_font)
        self._body.setWordWrap(True)
        # E1 muestra texto plano a propósito: el renderizado seguro de Markdown
        # ya existe en la interfaz técnica (B8a) y traerlo aquí es trabajo de
        # una entrega posterior, no de la estructura visual.
        self._body.setTextFormat(Qt.TextFormat.PlainText)
        self._body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._body.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")

        # Un renglón de 1400 px es incómodo de leer en vídeo aunque quepa.
        self.setMaximumWidth(theme.MESSAGE_MAXIMUM_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(speaker)
        layout.addWidget(self._body)

    @property
    def role(self) -> MessageRole:
        return self._role

    def body_text(self) -> str:
        return self._body.text()

    def set_body(self, text: str) -> None:
        self._body.setText(text)


class StudioInput(QTextEdit):
    """Caja única para texto escrito y, más adelante, transcripción de voz.

    §5: la misma caja recibe ambos, crece automáticamente hasta una altura
    máxima razonable y a partir de ahí se desplaza por dentro sin invadir el
    historial.
    """

    submitted = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(_INPUT_PLACEHOLDER)
        self.setAccessibleName("Entrada de texto y voz")
        font = QFont()
        font.setPointSize(theme.FONT_INPUT_PT)
        self.setFont(font)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(theme.INPUT_MINIMUM_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().contentsChanged.connect(self._adjust_height)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Enter envía; Mayús+Enter hace salto de línea."""
        is_return = event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        if is_return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            event.accept()
            self.submitted.emit()
            return
        super().keyPressEvent(event)

    def _adjust_height(self) -> None:
        content = self.document().size().height() + self.contentsMargins().top() * 2 + 12
        height = int(min(max(content, theme.INPUT_MINIMUM_HEIGHT), theme.INPUT_MAXIMUM_HEIGHT))
        if height != self.height():
            self.setFixedHeight(height)


class _AsideBlock(QWidget):
    """Un bloque de la zona auxiliar: título pequeño y valor legible."""

    def __init__(self, title: str, placeholder: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(theme.FONT_ASIDE_TITLE_PT)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")

        self._value = QLabel(placeholder)
        value_font = QFont()
        value_font.setPointSize(theme.FONT_ASIDE_VALUE_PT)
        self._value.setFont(value_font)
        self._value.setWordWrap(True)
        self._value.setTextFormat(Qt.TextFormat.PlainText)
        self._value.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(title_label)
        layout.addWidget(self._value)

    def value_text(self) -> str:
        return self._value.text()

    def set_value(self, text: str) -> None:
        self._value.setText(text)


class StudioPage(QWidget):
    """La superficie completa de Model Studio."""

    send_requested = Signal(str)
    cancel_requested = Signal()
    exit_requested = Signal()
    microphone_clicked = Signal()
    stop_voice_clicked = Signal()
    repeat_clicked = Signal()
    mute_toggled = Signal(bool)
    read_all_clicked = Signal()
    settings_clicked = Signal()
    capture_panel_toggled = Signal(bool)
    emergency_stop_clicked = Signal()

    def __init__(self, parent: QWidget | None = None, *, animated: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("studioPage")
        self.setAutoFillBackground(True)

        self._interaction_state = StudioInteractionState.PREPARADO
        self._capture_state = StudioCaptureState.DESACTIVADO
        self._messages: list[_MessageWidget] = []
        self._follow_bottom = True
        self._clean_mode = False
        self._voice_available = False
        self._voice_unavailable_reason = ""
        self._capture_available = False
        self._capture_panel_open = False

        self.presence = PresenceWidget(animated=animated)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_bottom_bar())

        self.setStyleSheet(self._style_sheet())
        self._refresh_state_labels()

    # --- Construcción ----------------------------------------------------

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("studioTopBar")
        bar.setFixedHeight(theme.TOP_BAR_HEIGHT)

        title = QLabel("SIRIUS")
        title_font = QFont()
        title_font.setPointSize(theme.FONT_TOPBAR_TITLE_PT)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.0)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")

        separator = QLabel("·")
        separator.setStyleSheet(f"color: {theme.TEXT_MUTED};")

        self.project_label = QLabel("Sin proyecto activo")
        meta_font = QFont()
        meta_font.setPointSize(theme.FONT_TOPBAR_META_PT)
        self.project_label.setFont(meta_font)
        self.project_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        self.project_label.setAccessibleName("Proyecto activo")

        self.interaction_state_label = QLabel("")
        self.interaction_state_label.setObjectName("studioInteractionState")
        self.interaction_state_label.setAccessibleName("Estado de interacción")

        # El estado de captura vive en su propia etiqueta, separado del de
        # interacción: criterio de aceptación 10.
        self.capture_state_label = QLabel("")
        self.capture_state_label.setObjectName("studioCaptureState")
        self.capture_state_label.setAccessibleName("Estado de captura")

        state_font = QFont()
        state_font.setPointSize(theme.FONT_STATE_PT)
        state_font.setBold(True)
        state_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        self.interaction_state_label.setFont(state_font)
        self.capture_state_label.setFont(state_font)

        # El aviso de gasto vive aquí y no abajo: quedarse sin presupuesto a
        # mitad de una grabación es un fallo visible, y el aviso que lo evita
        # solo sirve si está donde se está mirando.
        self.budget_label = QLabel("")
        self.budget_label.setObjectName("studioBudgetNotice")
        self.budget_label.setAccessibleName("Aviso de gasto del mes")
        self.budget_label.setVisible(False)

        self.exit_button = self._icon_button(
            "exit_studio", "Volver a la interfaz de Sirius", enabled=True
        )
        self.exit_button.clicked.connect(self.exit_requested.emit)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(theme.CONTENT_MARGIN, 0, theme.CONTENT_MARGIN, 0)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(separator)
        layout.addWidget(self.project_label)
        layout.addStretch(1)
        layout.addWidget(self.budget_label)
        layout.addWidget(self.interaction_state_label)
        layout.addWidget(self.capture_state_label)
        layout.addWidget(self.exit_button)
        return bar

    def _build_body(self) -> QWidget:
        body = QWidget()
        layout = QHBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_left_column(), theme.LEFT_COLUMN_STRETCH)
        layout.addWidget(self._build_right_column(), theme.RIGHT_COLUMN_STRETCH)
        return body

    def _build_left_column(self) -> QWidget:
        column = QWidget()
        column.setObjectName("studioLeftColumn")

        self.aside = QWidget()
        self.aside.setObjectName("studioAside")
        self.project_block = _AsideBlock("PROYECTO", "Sin proyecto activo")
        self.context_block = _AsideBlock("CONTEXTO", "Sin contexto disponible")
        # El hueco de las notas rápidas queda marcado y vacío: añadirlas
        # después no tendrá que mover nada de lo que ya está aprobado.
        self.notes_block = _AsideBlock("NOTAS RÁPIDAS", "Disponibles en una entrega posterior.")

        aside_layout = QVBoxLayout(self.aside)
        aside_layout.setContentsMargins(0, 0, 0, 0)
        aside_layout.setSpacing(18)
        aside_layout.addWidget(self.project_block)
        aside_layout.addWidget(self.context_block)
        aside_layout.addWidget(self.notes_block)

        # La presencia manda arriba y el contexto va pegado debajo; el espacio
        # que sobra se acumula al final de la columna en vez de abrirse un
        # hueco entre las dos cosas. La presencia es cuadrada (heightForWidth),
        # así que ocupa exactamente el ancho de la columna y nada más.
        layout = QVBoxLayout(column)
        layout.setContentsMargins(
            theme.CONTENT_MARGIN, theme.CONTENT_MARGIN, theme.CONTENT_MARGIN, theme.CONTENT_MARGIN
        )
        layout.setSpacing(24)
        layout.addWidget(self.presence)
        layout.addWidget(self.aside)
        layout.addStretch(1)
        return column

    def _build_right_column(self) -> QWidget:
        column = QWidget()
        column.setObjectName("studioRightColumn")

        self._history_container = QWidget()
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_layout.setSpacing(theme.MESSAGE_SPACING)
        self._history_layout.addStretch(1)

        self.history_scroll = QScrollArea()
        self.history_scroll.setObjectName("studioHistory")
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.history_scroll.setWidget(self._history_container)
        self.history_scroll.setAccessibleName("Historial de la conversación")
        scrollbar = self.history_scroll.verticalScrollBar()
        scrollbar.rangeChanged.connect(self._on_history_range_changed)
        scrollbar.valueChanged.connect(self._on_history_scrolled)

        self.capture_panel = StudioCapturePanel()
        self.capture_panel.setVisible(False)

        self.error_label = QLabel("")
        self.error_label.setObjectName("studioError")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)

        self.input = StudioInput()
        self.input.submitted.connect(self._handle_submit)

        self.send_button = self._icon_button("send", "Enviar", enabled=True, shortcut_hint="Enter")
        self.send_button.clicked.connect(self._handle_submit)

        self.microphone_button = self._icon_button("microphone", "Hablar con Sirius", enabled=False)
        self.microphone_button.clicked.connect(self.microphone_clicked.emit)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(10)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.microphone_button, 0, Qt.AlignmentFlag.AlignBottom)
        input_row.addWidget(self.send_button, 0, Qt.AlignmentFlag.AlignBottom)

        layout = QVBoxLayout(column)
        layout.setContentsMargins(
            theme.CONTENT_MARGIN, theme.CONTENT_MARGIN, theme.CONTENT_MARGIN, theme.CONTENT_MARGIN
        )
        layout.setSpacing(14)
        layout.addWidget(self.history_scroll, 1)
        layout.addWidget(self.capture_panel)
        layout.addWidget(self.error_label)
        layout.addLayout(input_row)
        return column

    def _build_bottom_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("studioBottomBar")
        bar.setFixedHeight(theme.BOTTOM_BAR_HEIGHT)

        self.cancel_button = self._icon_button("cancel", "Cancelar operación", enabled=False)
        self.cancel_button.clicked.connect(self.cancel_requested.emit)

        self.stop_voice_button = self._icon_button("stop", "Detener voz", enabled=False)
        self.stop_voice_button.clicked.connect(self.stop_voice_clicked.emit)

        self.mute_button = self._icon_button("sound_on", "Silenciar salida hablada", enabled=False)
        self.mute_button.setCheckable(True)
        self.mute_button.toggled.connect(self._handle_mute_toggled)

        self.repeat_button = self._icon_button("repeat", "Repetir última respuesta", enabled=False)
        self.repeat_button.clicked.connect(self.repeat_clicked.emit)
        self.read_all_button = self._icon_button(
            "read_all", "Leer la última respuesta entera, con el código", enabled=False
        )
        self.read_all_button.clicked.connect(self.read_all_clicked.emit)
        self.capture_button = self._icon_button(
            "capture", "Grabación, escenas y cámaras", enabled=False
        )
        self.capture_button.setCheckable(True)
        self.capture_button.toggled.connect(self._handle_capture_toggled)

        # La parada de emergencia NO vive en el panel: el criterio 11 exige que
        # esté accesible durante una grabación, y tener que abrir un panel para
        # encontrarla no lo es. Aparece en la barra en cuanto se graba.
        self.emergency_stop_button = QPushButton("PARADA DE EMERGENCIA")
        self.emergency_stop_button.setObjectName("studioEmergencyStop")
        self.emergency_stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.emergency_stop_button.setAccessibleName("Parada de emergencia de la grabación")
        self.emergency_stop_button.setToolTip("Detener la grabación inmediatamente")
        self.emergency_stop_button.clicked.connect(self.emergency_stop_clicked.emit)
        self.emergency_stop_button.setVisible(False)
        self.settings_button = self._icon_button(
            "settings", "Ajustes rápidos de Model Studio", enabled=False
        )
        self.settings_button.clicked.connect(self.settings_clicked.emit)
        self.fullscreen_button = self._icon_button(
            "fullscreen", "Modo limpio a pantalla completa", enabled=True, shortcut_hint="F11"
        )
        self.fullscreen_button.clicked.connect(self.toggle_clean_mode)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(theme.CONTENT_MARGIN, 0, theme.CONTENT_MARGIN, 0)
        layout.setSpacing(8)
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.stop_voice_button)
        layout.addWidget(self.mute_button)
        layout.addWidget(self.repeat_button)
        layout.addWidget(self.read_all_button)
        layout.addStretch(1)
        layout.addWidget(self.emergency_stop_button)
        layout.addWidget(self.capture_button)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.fullscreen_button)
        return bar

    def _icon_button(
        self,
        icon_name: str,
        label: str,
        *,
        enabled: bool,
        shortcut_hint: str | None = None,
    ) -> QPushButton:
        """Un control de la barra: icono, tooltip y nombre accesible (§6).

        Los controles que todavía no existen se muestran deshabilitados con el
        motivo en el tooltip, en vez de aparecer más tarde: así la barra no
        cambia de forma al llegar la voz y la captura.
        """
        button = QPushButton()
        button.setObjectName("studioIconButton")
        button.setIcon(studio_icon(icon_name, theme.TEXT_SECONDARY, theme.ICON_PIXELS))
        button.setFixedSize(theme.ICON_BUTTON_SIZE, theme.ICON_BUTTON_SIZE)
        button.setFlat(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setEnabled(enabled)

        tooltip = label if shortcut_hint is None else f"{label} ({shortcut_hint})"
        if not enabled:
            tooltip += _PENDING_TOOLTIP_SUFFIX
        button.setToolTip(tooltip)
        button.setAccessibleName(label)
        return button

    def _style_sheet(self) -> str:
        return f"""
        QWidget#studioPage,
        QWidget#studioLeftColumn,
        QWidget#studioRightColumn {{
            background-color: {theme.BACKGROUND};
        }}
        QLabel#studioBudgetNotice {{
            color: {theme.WARNING};
        }}
        QFrame#studioTopBar {{
            background-color: {theme.SURFACE_RAISED};
            border-bottom: 1px solid {theme.HAIRLINE};
        }}
        QFrame#studioBottomBar {{
            background-color: {theme.SURFACE_RAISED};
            border-top: 1px solid {theme.HAIRLINE};
        }}
        QScrollArea#studioHistory, QScrollArea#studioHistory > QWidget > QWidget {{
            background-color: {theme.BACKGROUND};
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.HAIRLINE};
            border-radius: 4px;
            min-height: 32px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QTextEdit {{
            background-color: {theme.SURFACE_RAISED};
            border: 1px solid {theme.HAIRLINE};
            border-radius: 10px;
            padding: 10px 12px;
            color: {theme.TEXT_PRIMARY};
            selection-background-color: {theme.ACCENT};
        }}
        QTextEdit:focus {{
            border: 1px solid {theme.ACCENT};
        }}
        QPushButton#studioIconButton {{
            background-color: transparent;
            border: none;
            border-radius: 8px;
        }}
        QPushButton#studioIconButton:hover:enabled {{
            background-color: {theme.HAIRLINE};
        }}
        QPushButton#studioIconButton:disabled {{
            opacity: 0.4;
        }}
        QLabel#studioError {{
            color: {theme.ERROR_TEXT};
        }}
        QPushButton#studioEmergencyStop {{
            background-color: transparent;
            border: 1px solid {theme.RECORDING};
            border-radius: 8px;
            padding: 6px 14px;
            color: {theme.RECORDING};
            font-weight: bold;
        }}
        QPushButton#studioEmergencyStop:hover {{
            background-color: {theme.RECORDING};
            color: {theme.BACKGROUND};
        }}
        """

    # --- Datos que entran ------------------------------------------------

    def set_project_name(self, name: str) -> None:
        text = name.strip() or "Sin proyecto activo"
        self.project_label.setText(text)
        self.project_block.set_value(text)

    def set_context_summary(self, summary: str) -> None:
        self.context_block.set_value(summary.strip() or "Sin contexto disponible")

    def set_interaction_state(self, state: StudioInteractionState) -> None:
        self._interaction_state = state
        self.presence.set_state(state)
        self.input.setEnabled(state.accepts_typing)
        self.send_button.setEnabled(state.accepts_typing)
        self.cancel_button.setEnabled(state is StudioInteractionState.PENSANDO)
        if self._voice_available:
            # Mientras escucha, el micrófono sigue activo porque es el botón
            # con el que se para. Mientras transcribe, no: volver a pulsarlo no
            # haría nada y solo confundiría.
            self.microphone_button.setEnabled(
                state
                in (
                    StudioInteractionState.PREPARADO,
                    StudioInteractionState.ESCUCHANDO,
                    StudioInteractionState.REVISANDO,
                    StudioInteractionState.HABLANDO,
                    StudioInteractionState.ERROR,
                )
            )
            self.microphone_button.setToolTip(
                "Dejar de hablar y transcribir"
                if state is StudioInteractionState.ESCUCHANDO
                else "Hablar con Sirius"
            )
        self._refresh_state_labels()

    def set_capture_state(self, state: StudioCaptureState) -> None:
        self._capture_state = state
        self.capture_panel.set_state(state)
        # La parada de emergencia aparece en cuanto hay algo que parar, sin
        # tener que abrir ningún panel (criterio de aceptación 11). También
        # durante INICIANDO y CAMBIANDO: son justo los momentos en los que
        # puede haber una grabación en marcha sin confirmar todavía.
        self.emergency_stop_button.setVisible(
            state
            in (
                StudioCaptureState.INICIANDO,
                StudioCaptureState.GRABANDO,
                StudioCaptureState.PAUSADO,
                StudioCaptureState.CAMBIANDO,
                StudioCaptureState.INCIERTO,
            )
        )
        self._refresh_state_labels()

    @property
    def interaction_state(self) -> StudioInteractionState:
        return self._interaction_state

    @property
    def capture_state(self) -> StudioCaptureState:
        return self._capture_state

    def set_voice_available(self, available: bool, unavailable_reason: str = "") -> None:
        """Enciende o apaga los controles de voz, diciendo por qué si están apagados.

        Un control apagado sin explicación es lo que hace pensar que la
        aplicación está rota; con el motivo en el tooltip, se entiende.
        """
        self._voice_available = available
        self._voice_unavailable_reason = unavailable_reason
        for button, label in (
            (self.microphone_button, "Hablar con Sirius"),
            (self.stop_voice_button, "Detener voz"),
            (self.repeat_button, "Repetir última respuesta"),
            (self.read_all_button, "Leer la última respuesta entera, con el código"),
            (self.settings_button, "Ajustes rápidos de Model Studio"),
        ):
            button.setEnabled(available)
            button.setToolTip(label if available else f"{label} · {unavailable_reason}")
        # El del silencio va aparte: su icono y su texto dependen además de si
        # está silenciado ahora mismo.
        self.mute_button.setEnabled(available)
        self._refresh_mute_button()

    @property
    def voice_available(self) -> bool:
        return self._voice_available

    def set_muted(self, muted: bool) -> None:
        """Refleja el silencio sin volver a emitir la señal."""
        was_blocked = self.mute_button.blockSignals(True)
        self.mute_button.setChecked(muted)
        self.mute_button.blockSignals(was_blocked)
        self._refresh_mute_button()

    def _handle_mute_toggled(self, muted: bool) -> None:
        self._refresh_mute_button()
        self.mute_toggled.emit(muted)

    def _refresh_mute_button(self) -> None:
        """El icono dice cómo está la voz; el texto, qué pasa si lo pulsas.

        Con el altavoz tachado dibujado siempre, mirar la barra hace pensar que
        el sonido está cortado aunque no lo esté. Ahora el altavoz suena cuando
        se oye y aparece tachado solo cuando de verdad está en silencio.
        """
        muted = self.mute_button.isChecked()
        self.mute_button.setIcon(
            studio_icon("mute" if muted else "sound_on", theme.TEXT_SECONDARY, theme.ICON_PIXELS)
        )
        label = "Volver a activar la voz" if muted else "Silenciar salida hablada"
        self.mute_button.setAccessibleName(label)
        self.mute_button.setToolTip(
            label if self._voice_available else f"{label} · {self._voice_unavailable_reason}"
        )

    def set_input_text(self, text: str) -> None:
        """Escribe la transcripción en la caja, para revisarla antes de enviar."""
        self.input.setPlainText(text)
        cursor = self.input.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.input.setTextCursor(cursor)
        self.input.setFocus()

    def set_capture_available(self, available: bool, unavailable_reason: str = "") -> None:
        """Enciende el acceso al panel de captura, o dice por qué está apagado."""
        self._capture_available = available
        self.capture_button.setEnabled(available)
        self.capture_button.setToolTip(
            "Grabación, escenas y cámaras"
            if available
            else f"Grabación, escenas y cámaras · {unavailable_reason}"
        )
        if not available:
            self.capture_button.setChecked(False)

    @property
    def capture_available(self) -> bool:
        return self._capture_available

    @property
    def capture_panel_open(self) -> bool:
        """Si el panel está desplegado.

        Es estado propio y no ``isVisible()``: un widget cuya ventana todavía
        no se ha mostrado responde que no es visible aunque esté desplegado, y
        aquí lo que importa es lo que el usuario pidió.
        """
        return self._capture_panel_open

    def _handle_capture_toggled(self, checked: bool) -> None:
        self._capture_panel_open = checked
        self.capture_panel.setVisible(checked)
        self.capture_panel_toggled.emit(checked)

    def set_budget_notice(self, message: str) -> None:
        """Aviso de gasto, visible sin salir de la superficie de grabación."""
        self.budget_label.setText(message)
        self.budget_label.setVisible(bool(message))

    def set_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))

    def _refresh_state_labels(self) -> None:
        self.interaction_state_label.setText(self._interaction_state.label)
        self.interaction_state_label.setStyleSheet(
            f"color: {theme.ERROR_TEXT};"
            if self._interaction_state is StudioInteractionState.ERROR
            else f"color: {theme.TEXT_SECONDARY};"
        )

        # El indicador rojo solo puede encenderlo una grabación confirmada por
        # el backend: nunca ``INICIANDO`` ni ``INCIERTO`` (#127).
        recording = self._capture_state.is_recording_confirmed
        self.capture_state_label.setText(
            f"● {self._capture_state.label}" if recording else self._capture_state.label
        )
        self.capture_state_label.setStyleSheet(
            f"color: {theme.RECORDING};" if recording else f"color: {theme.TEXT_MUTED};"
        )

    # --- Conversación ----------------------------------------------------

    def clear_history(self) -> None:
        for widget in self._messages:
            self._history_layout.removeWidget(widget)
            widget.deleteLater()
        self._messages.clear()
        self._follow_bottom = True

    def append_message(
        self,
        role: MessageRole,
        content: str | None,
        status: MessageStatus = MessageStatus.COMPLETED,
    ) -> None:
        widget = _MessageWidget(role)
        widget.set_body(compose_body(content, status))
        # Antes del estiramiento final, que mantiene los mensajes arriba
        # mientras la conversación es corta.
        self._history_layout.insertWidget(self._history_layout.count() - 1, widget)
        self._messages.append(widget)

    def update_last_message(self, content: str | None, status: MessageStatus) -> None:
        """Reescribe el último turno. Sin turnos, no hace nada.

        Es el camino del streaming: cada fragmento reescribe el mismo widget,
        que crece hacia abajo sin desplazar lo anterior.
        """
        if not self._messages:
            return
        self._messages[-1].set_body(compose_body(content, status))

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def message_bodies(self) -> list[tuple[MessageRole, str]]:
        """Conversación visible, en orden. Pensado para las pruebas."""
        return [(widget.role, widget.body_text()) for widget in self._messages]

    def _on_history_range_changed(self, _minimum: int, _maximum: int) -> None:
        if self._follow_bottom:
            scrollbar = self.history_scroll.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _on_history_scrolled(self, value: int) -> None:
        scrollbar = self.history_scroll.verticalScrollBar()
        self._follow_bottom = scrollbar.maximum() == 0 or value >= scrollbar.maximum() - 8

    # --- Acciones --------------------------------------------------------

    def _handle_submit(self) -> None:
        text = self.input.toPlainText()
        if not text.strip():
            return
        if not self._interaction_state.accepts_typing:
            return
        self.input.clear()
        self.send_requested.emit(text)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Escape sale del modo limpio: nunca se queda uno atrapado a pantalla completa."""
        if event.key() == Qt.Key.Key_Escape and self._clean_mode:
            event.accept()
            self.toggle_clean_mode()
            return
        super().keyPressEvent(event)

    @property
    def clean_mode(self) -> bool:
        return self._clean_mode

    def toggle_clean_mode(self) -> None:
        """Modo grabación limpia (§9.1): pliega la zona auxiliar y va a pantalla completa."""
        self._clean_mode = not self._clean_mode
        self.aside.setVisible(not self._clean_mode)
        window = self.window()
        if window is not None:
            if self._clean_mode:
                window.showFullScreen()
            else:
                window.showNormal()
