"""Superficie de Model Studio: criterios de aceptación de SIRIUS-MODEL-STUDIO-UI-001 §11.

Cubre los criterios verificables sin audio ni hardware, que son los de la
primera entrega (E1): 1 a 10 y 12. El criterio 11 (parada de emergencia durante
una grabación) pertenece al Módulo Captura y aquí no se simula.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QPushButton, QWidget
from pytestqt.qtbot import QtBot

from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.domain.model_studio import StudioCaptureState, StudioInteractionState
from sirius.presentation.model_studio import theme
from sirius.presentation.model_studio.studio_page import StudioPage


def _press(
    widget: QWidget,
    key: Qt.Key,
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
) -> None:
    """Envía una pulsación real de tecla al widget."""
    QApplication.sendEvent(widget, QKeyEvent(QEvent.Type.KeyPress, key, modifiers, "\r"))


def _page(qtbot: QtBot) -> StudioPage:
    page = StudioPage(animated=False)
    qtbot.addWidget(page)
    page.resize(1280, 720)
    return page


# --- Criterio 1: proporción de columnas ---------------------------------


def test_left_column_takes_roughly_a_quarter(qtbot: QtBot) -> None:
    """Seccion 2.1: izquierda 25-30 %, derecha 70-75 %."""
    page = _page(qtbot)
    page.show()
    qtbot.waitExposed(page)

    left_share = theme.LEFT_COLUMN_STRETCH / (
        theme.LEFT_COLUMN_STRETCH + theme.RIGHT_COLUMN_STRETCH
    )
    assert 0.25 <= left_share <= 0.30


# --- Criterios 2, 3, 4: la presencia ------------------------------------


def test_presence_is_present_and_reflects_state(qtbot: QtBot) -> None:
    page = _page(qtbot)

    page.set_interaction_state(StudioInteractionState.HABLANDO)

    assert page.presence.state is StudioInteractionState.HABLANDO


# --- Criterio 5: solo TÚ y SIRIUS, sin avatares -------------------------


def test_messages_only_identify_you_and_sirius(qtbot: QtBot) -> None:
    page = _page(qtbot)

    page.append_message(MessageRole.USER, "Hola")
    page.append_message(MessageRole.SIRIUS, "Dime.")

    assert page.message_bodies() == [
        (MessageRole.USER, "Hola"),
        (MessageRole.SIRIUS, "Dime."),
    ]


def test_message_status_is_said_in_plain_language(qtbot: QtBot) -> None:
    """§4: errores y resultados en texto claro, no en lenguaje técnico."""
    page = _page(qtbot)

    page.append_message(MessageRole.SIRIUS, "A medias", MessageStatus.CANCELLED)
    page.append_message(MessageRole.SIRIUS, "Roto", MessageStatus.FAILED)
    page.append_message(MessageRole.SIRIUS, None, MessageStatus.REDACTED)

    bodies = [body for _role, body in page.message_bodies()]
    assert bodies == ["A medias (cancelado)", "Roto (fallido)", "(mensaje redactado)"]
    assert "None" not in " ".join(bodies)


# --- Criterio 7: no hay panel separado de transcripción -----------------


def test_there_is_no_separate_transcription_panel(qtbot: QtBot) -> None:
    """La transcripción llegará a la caja de entrada, no a un panel aparte."""
    page = _page(qtbot)

    names = [widget.accessibleName().lower() for widget in page.findChildren(QWidget)]
    assert not any("transcripción" in name for name in names)
    assert any("texto y voz" in name for name in names)


# --- Criterio 8: caja única, expandible y accesible ---------------------


def test_a_single_box_receives_text_and_voice(qtbot: QtBot) -> None:
    page = _page(qtbot)

    assert page.input.placeholderText() == "Escribe o habla con Sirius…"
    assert page.input.accessibleName()


def test_input_grows_and_then_stops_growing(qtbot: QtBot) -> None:
    """§5: crece hasta un máximo y a partir de ahí se desplaza por dentro."""
    page = _page(qtbot)
    page.show()
    qtbot.waitExposed(page)
    initial = page.input.height()

    page.input.setPlainText("\n".join(f"línea {index}" for index in range(4)))
    grown = page.input.height()
    page.input.setPlainText("\n".join(f"línea {index}" for index in range(80)))

    assert grown > initial
    assert page.input.height() <= theme.INPUT_MAXIMUM_HEIGHT


def test_enter_sends_and_shift_enter_does_not(qtbot: QtBot) -> None:
    page = _page(qtbot)
    page.input.setPlainText("hola")

    with qtbot.waitSignal(page.send_requested, timeout=1000) as blocker:
        _press(page.input, Qt.Key.Key_Return)
    assert blocker.args == ["hola"]
    assert page.input.toPlainText() == ""

    page.input.setPlainText("otra")
    _press(page.input, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    assert "otra" in page.input.toPlainText()


def test_blank_input_sends_nothing(qtbot: QtBot) -> None:
    page = _page(qtbot)
    page.input.setPlainText("   \n  ")
    received: list[str] = []
    page.send_requested.connect(received.append)

    _press(page.input, Qt.Key.Key_Return)

    assert received == []


# --- Criterio 9: iconos con función, tooltip y estado -------------------


def test_every_icon_button_has_tooltip_and_accessible_name(qtbot: QtBot) -> None:
    page = _page(qtbot)

    buttons = page.findChildren(QPushButton, "studioIconButton")
    assert len(buttons) >= 10
    for button in buttons:
        assert button.toolTip(), "un control sin tooltip"
        assert button.accessibleName(), "un control sin nombre accesible"
        assert not button.icon().isNull(), "un control sin icono"


def test_controls_that_do_not_exist_yet_say_so(qtbot: QtBot) -> None:
    """Se muestran deshabilitados con el motivo, en vez de aparecer luego.

    Así la barra no cambia de forma al llegar la voz y la captura, que es lo
    que exige el criterio 12.
    """
    page = _page(qtbot)

    for button in (
        page.microphone_button,
        page.stop_voice_button,
        page.mute_button,
        page.repeat_button,
        page.read_all_button,
        page.capture_button,
    ):
        assert not button.isEnabled()
        assert "todavía no disponible" in button.toolTip()

    assert page.send_button.isEnabled()
    assert page.fullscreen_button.isEnabled()
    assert page.exit_button.isEnabled()


# --- Criterio 10: estados separados -------------------------------------


def test_interaction_and_capture_states_are_separate_labels(qtbot: QtBot) -> None:
    page = _page(qtbot)

    page.set_interaction_state(StudioInteractionState.PENSANDO)
    page.set_capture_state(StudioCaptureState.GRABANDO)

    assert page.interaction_state_label.text() == "PENSANDO"
    assert "GRABANDO" in page.capture_state_label.text()
    assert page.interaction_state_label is not page.capture_state_label


def test_red_indicator_only_when_the_backend_confirms_recording(qtbot: QtBot) -> None:
    """#127: ni ``INICIANDO`` ni ``INCIERTO`` pueden encender el rojo."""
    page = _page(qtbot)

    for state in (
        StudioCaptureState.INICIANDO,
        StudioCaptureState.INCIERTO,
        StudioCaptureState.DETENIENDO,
        StudioCaptureState.PAUSADO,
    ):
        page.set_capture_state(state)
        assert theme.RECORDING not in page.capture_state_label.styleSheet()
        assert "●" not in page.capture_state_label.text()

    page.set_capture_state(StudioCaptureState.GRABANDO)
    assert theme.RECORDING in page.capture_state_label.styleSheet()
    assert "●" in page.capture_state_label.text()


def test_capture_starts_deactivated(qtbot: QtBot) -> None:
    """Sin activación automática al abrir: el Módulo Captura no existe aún."""
    page = _page(qtbot)

    assert page.capture_state is StudioCaptureState.DESACTIVADO
    assert not page.capture_state.is_recording_confirmed


# --- Estados que bloquean la escritura ----------------------------------


def test_typing_is_blocked_while_work_is_in_flight(qtbot: QtBot) -> None:
    page = _page(qtbot)

    page.set_interaction_state(StudioInteractionState.PENSANDO)
    assert not page.input.isEnabled()
    assert page.cancel_button.isEnabled()

    page.set_interaction_state(StudioInteractionState.PREPARADO)
    assert page.input.isEnabled()
    assert not page.cancel_button.isEnabled()


def test_typing_survives_an_error(qtbot: QtBot) -> None:
    """§10: un fallo no puede inutilizar el chat escrito."""
    page = _page(qtbot)

    page.set_interaction_state(StudioInteractionState.ERROR)
    page.set_error("No se pudo enviar.")

    assert page.input.isEnabled()
    assert page.send_button.isEnabled()
    assert page.error_label.isVisible() or page.error_label.text() == "No se pudo enviar."


def test_submitting_while_busy_does_nothing(qtbot: QtBot) -> None:
    page = _page(qtbot)
    page.set_interaction_state(StudioInteractionState.PENSANDO)
    page.input.setPlainText("algo")
    received: list[str] = []
    page.send_requested.connect(received.append)

    page._handle_submit()

    assert received == []


# --- Conversación --------------------------------------------------------


def test_streaming_rewrites_the_same_turn(qtbot: QtBot) -> None:
    page = _page(qtbot)
    page.append_message(MessageRole.USER, "Hola")
    page.append_message(MessageRole.SIRIUS, "")

    page.update_last_message("Hola,", MessageStatus.COMPLETED)
    page.update_last_message("Hola, dime.", MessageStatus.COMPLETED)

    assert page.message_count == 2
    assert page.message_bodies()[-1] == (MessageRole.SIRIUS, "Hola, dime.")


def test_updating_without_messages_is_safe(qtbot: QtBot) -> None:
    page = _page(qtbot)

    page.update_last_message("nada", MessageStatus.COMPLETED)

    assert page.message_count == 0


def test_clearing_history_empties_the_surface(qtbot: QtBot) -> None:
    page = _page(qtbot)
    page.append_message(MessageRole.USER, "Uno")
    page.append_message(MessageRole.SIRIUS, "Dos")

    page.clear_history()

    assert page.message_count == 0
    assert page.message_bodies() == []


# --- Zona auxiliar y modo limpio ----------------------------------------


def test_aside_shows_project_and_context(qtbot: QtBot) -> None:
    page = _page(qtbot)

    page.set_project_name("HEAD-R1")
    page.set_context_summary("Montando la protoboard.")

    assert page.project_label.text() == "HEAD-R1"
    assert page.project_block.value_text() == "HEAD-R1"
    assert page.context_block.value_text() == "Montando la protoboard."


def test_aside_says_it_plainly_when_there_is_no_project(qtbot: QtBot) -> None:
    page = _page(qtbot)

    page.set_project_name("")
    page.set_context_summary("   ")

    assert page.project_block.value_text() == "Sin proyecto activo"
    assert page.context_block.value_text() == "Sin contexto disponible"


def test_notes_slot_is_reserved_but_empty(qtbot: QtBot) -> None:
    """El hueco queda marcado para que añadirlas después no mueva nada."""
    page = _page(qtbot)

    assert "posterior" in page.notes_block.value_text()


def test_clean_mode_folds_the_aside(qtbot: QtBot) -> None:
    """§9.1: modo grabación limpia, sin paneles ni información administrativa."""
    page = _page(qtbot)
    page.show()
    qtbot.waitExposed(page)

    page.toggle_clean_mode()
    assert page.clean_mode
    assert not page.aside.isVisible()

    page.toggle_clean_mode()
    assert not page.clean_mode
    qtbot.waitUntil(lambda: page.aside.isVisible(), timeout=2000)


def test_escape_leaves_clean_mode(qtbot: QtBot) -> None:
    page = _page(qtbot)
    page.show()
    qtbot.waitExposed(page)
    page.toggle_clean_mode()

    _press(page, Qt.Key.Key_Escape)

    assert not page.clean_mode


def test_exit_button_asks_to_leave(qtbot: QtBot) -> None:
    page = _page(qtbot)

    with qtbot.waitSignal(page.exit_requested, timeout=1000):
        page.exit_button.click()
