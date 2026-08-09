"""Panel de grabación en la superficie, y su conexión con la ventana real.

Cubre el criterio de aceptación 11 —la parada de emergencia accesible durante
una grabación— y que ningún control ofrezca algo que el backend no haya
confirmado.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from sirius.adapters.capture.fake import FakeCaptureBackend
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import build_sqlite_identity_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.capture_commands import CaptureCommand, interpret
from sirius.application.studio_capture import StudioCaptureUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.capture import Scene, SceneRegistry
from sirius.domain.model_studio import StudioCaptureState
from sirius.presentation.main_window import MainWindow
from sirius.presentation.model_studio.capture_panel import StudioCapturePanel, format_elapsed

_SCENES = SceneRegistry(
    (
        Scene("pantalla", "Pantalla", "Pantalla", ("pantalla",), is_fallback=True),
        Scene("cenital", "Cámara cenital", "Cámara cenital", ("cenital",)),
    )
)


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _panel(qtbot: QtBot) -> StudioCapturePanel:
    panel = StudioCapturePanel()
    qtbot.addWidget(panel)
    panel.set_scenes([("pantalla", "Pantalla"), ("cenital", "Cámara cenital")])
    return panel


# --- Cronómetro ----------------------------------------------------------


def test_without_a_recording_the_clock_shows_dashes() -> None:
    """Un cero engañaría: parecería que se está grabando desde hace nada."""
    assert format_elapsed(None) == "--:--"


def test_the_clock_is_minutes_and_seconds() -> None:
    assert format_elapsed(0.0) == "00:00"
    assert format_elapsed(95.0) == "01:35"
    assert format_elapsed(3671.0) == "61:11"


def test_a_negative_time_never_shows_a_negative_clock() -> None:
    assert format_elapsed(-5.0) == "00:00"


# --- Qué se puede pulsar en cada estado ---------------------------------


def test_nothing_is_offered_while_the_module_is_off(qtbot: QtBot) -> None:
    panel = _panel(qtbot)

    panel.set_state(StudioCaptureState.DESACTIVADO)

    assert not panel.record_button.isEnabled()
    assert not panel.stop_button.isEnabled()
    assert not panel.mark_button.isEnabled()


def test_only_recording_allows_marking_a_moment(qtbot: QtBot) -> None:
    """Marcar sin grabación apuntaría a un vídeo que no existe."""
    panel = _panel(qtbot)

    panel.set_state(StudioCaptureState.PREPARADO)
    assert not panel.mark_button.isEnabled()

    panel.set_state(StudioCaptureState.GRABANDO)
    assert panel.mark_button.isEnabled()


@pytest.mark.parametrize(
    "state",
    [
        StudioCaptureState.INICIANDO,
        StudioCaptureState.DETENIENDO,
        StudioCaptureState.CAMBIANDO,
        StudioCaptureState.INCIERTO,
    ],
)
def test_nothing_is_offered_while_an_order_is_in_flight(
    qtbot: QtBot, state: StudioCaptureState
) -> None:
    """Con una orden en vuelo no se sabe en qué va a quedar: no se ofrece nada."""
    panel = _panel(qtbot)

    panel.set_state(state)

    assert not panel.record_button.isEnabled()
    assert not panel.stop_button.isEnabled()
    assert not panel.mark_button.isEnabled()
    assert not any(button.isEnabled() for button in panel.findChildren(type(panel.record_button)))


def test_ready_offers_recording_and_recording_offers_stopping(qtbot: QtBot) -> None:
    panel = _panel(qtbot)

    panel.set_state(StudioCaptureState.PREPARADO)
    assert panel.record_button.isEnabled()
    assert not panel.stop_button.isEnabled()

    panel.set_state(StudioCaptureState.GRABANDO)
    assert not panel.record_button.isEnabled()
    assert panel.stop_button.isEnabled()
    assert panel.pause_button.isEnabled()


def test_a_paused_recording_offers_resuming_not_pausing(qtbot: QtBot) -> None:
    panel = _panel(qtbot)

    panel.set_state(StudioCaptureState.PAUSADO)

    assert panel.resume_button.isEnabled()
    assert not panel.pause_button.isEnabled()
    assert panel.stop_button.isEnabled()


def test_the_clock_resets_when_the_recording_ends(qtbot: QtBot) -> None:
    panel = _panel(qtbot)
    panel.set_state(StudioCaptureState.GRABANDO)
    panel.set_elapsed(42.0)

    panel.set_state(StudioCaptureState.PREPARADO)

    assert panel.elapsed_label.text() == "--:--"


# --- Escenas -------------------------------------------------------------


def test_only_authorized_scenes_are_offered(qtbot: QtBot) -> None:
    panel = _panel(qtbot)

    assert panel.scene_ids() == ["pantalla", "cenital"]


def test_choosing_a_scene_asks_for_it_by_identifier(qtbot: QtBot) -> None:
    panel = _panel(qtbot)
    panel.set_state(StudioCaptureState.PREPARADO)
    chosen: list[str] = []
    panel.scene_selected.connect(chosen.append)

    panel.findChildren(type(panel.record_button))
    for button in panel.findChildren(type(panel.record_button)):
        if button.text() == "Cámara cenital":
            button.click()

    assert chosen == ["cenital"]


def test_every_scene_button_has_an_accessible_name(qtbot: QtBot) -> None:
    panel = _panel(qtbot)

    for button in panel.findChildren(type(panel.record_button)):
        assert button.accessibleName()
        assert button.toolTip()


# --- Criterio 11: parada de emergencia ----------------------------------


def _window(tmp_path: Path, capture: StudioCaptureUseCase | None = None) -> MainWindow:
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project_repository.create_project(
        "HEAD-R1", "Cabeza", state_summary="montando", blockers=(), next_step="probar"
    )
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()

    dependencies = build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )
    return MainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        get_budget_status_use_case=dependencies.get_budget_status_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        project_continuity_use_case=dependencies.project_continuity_use_case,
        project_lifecycle_use_case=dependencies.project_lifecycle_use_case,
        save_manual_memory_use_case=dependencies.save_manual_memory_use_case,
        get_memory_origin_use_case=dependencies.get_memory_origin_use_case,
        correct_memory_use_case=dependencies.correct_memory_use_case,
        archive_memory_use_case=dependencies.archive_memory_use_case,
        delete_memory_use_case=dependencies.delete_memory_use_case,
        propose_decision_use_case=dependencies.propose_decision_use_case,
        approve_decision_use_case=dependencies.approve_decision_use_case,
        get_decision_origin_use_case=dependencies.get_decision_origin_use_case,
        supersede_decision_use_case=dependencies.supersede_decision_use_case,
        archive_decision_use_case=dependencies.archive_decision_use_case,
        detect_precedence_conflicts_use_case=dependencies.detect_precedence_conflicts_use_case,
        get_knowledge_overview_use_case=dependencies.get_knowledge_overview_use_case,
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        export_structured_use_case=dependencies.export_structured_use_case,
        close_database_connections=dependencies.close_database_connections,
        studio_capture_use_case=capture,
        show_warning=lambda title, text: None,
        show_information=lambda title, text: None,
    )


@pytest.mark.gui
def test_the_emergency_stop_is_hidden_until_there_is_something_to_stop(
    qtbot: QtBot, tmp_path: Path
) -> None:
    window = _window(tmp_path)
    qtbot.addWidget(window)

    assert not window.studio_page.emergency_stop_button.isVisibleTo(window.studio_page)


@pytest.mark.gui
@pytest.mark.parametrize(
    "state",
    [
        StudioCaptureState.INICIANDO,
        StudioCaptureState.GRABANDO,
        StudioCaptureState.PAUSADO,
        StudioCaptureState.CAMBIANDO,
        StudioCaptureState.INCIERTO,
    ],
)
def test_the_emergency_stop_appears_whenever_a_recording_may_be_running(
    qtbot: QtBot, tmp_path: Path, state: StudioCaptureState
) -> None:
    """No solo en GRABANDO: también mientras la orden va en camino.

    Son justo los momentos en los que puede haber una grabación en marcha sin
    confirmar, y en los que más falta hace poder cortarla.
    """
    window = _window(tmp_path)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.set_capture_state(state)

    assert window.studio_page.emergency_stop_button.isVisibleTo(window.studio_page)


@pytest.mark.gui
def test_the_emergency_stop_is_reachable_without_opening_the_panel(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Criterio 11: tener que abrir un panel para encontrarla no es accesible."""
    capture = StudioCaptureUseCase(FakeCaptureBackend(), _SCENES, enabled=True)
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)
    window.open_model_studio()
    window.studio_page.set_capture_state(StudioCaptureState.GRABANDO)

    assert not window.studio_page.capture_panel_open
    assert window.studio_page.emergency_stop_button.isVisibleTo(window.studio_page)
    assert window.studio_page.emergency_stop_button.isEnabled()


@pytest.mark.gui
def test_the_emergency_stop_reaches_the_use_case(qtbot: QtBot, tmp_path: Path) -> None:
    backend = FakeCaptureBackend()
    capture = StudioCaptureUseCase(backend, _SCENES, enabled=True)
    backend.connect()
    capture.start_recording()
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.emergency_stop_button.click()
    qtbot.waitUntil(lambda: "stop_recording" in backend.commands, timeout=5000)

    assert backend.commands.count("stop_recording") >= 1


# --- Panel dentro de la ventana -----------------------------------------


@pytest.mark.gui
def test_without_a_capture_module_the_button_says_why(qtbot: QtBot, tmp_path: Path) -> None:
    window = _window(tmp_path)
    qtbot.addWidget(window)

    assert not window.studio_page.capture_available
    assert not window.studio_page.capture_button.isEnabled()
    assert "todavía no disponible" in window.studio_page.capture_button.toolTip()


@pytest.mark.gui
def test_the_panel_starts_closed_and_the_module_off(qtbot: QtBot, tmp_path: Path) -> None:
    """Abrir Sirius no conecta con el sistema de grabación (MS-001)."""
    backend = FakeCaptureBackend()
    capture = StudioCaptureUseCase(backend, _SCENES)
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)

    assert not window.studio_page.capture_panel_open
    assert not capture.is_enabled
    assert not backend.is_connected()
    assert backend.commands == []


@pytest.mark.gui
def test_opening_the_panel_connects_and_asks_the_real_state(qtbot: QtBot, tmp_path: Path) -> None:
    backend = FakeCaptureBackend()
    capture = StudioCaptureUseCase(backend, _SCENES)
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.capture_button.setChecked(True)
    qtbot.waitUntil(lambda: backend.is_connected(), timeout=5000)

    assert window.studio_page.capture_panel_open
    assert "get_status" in backend.commands


@pytest.mark.gui
def test_the_authorized_scenes_reach_the_panel(qtbot: QtBot, tmp_path: Path) -> None:
    capture = StudioCaptureUseCase(FakeCaptureBackend(), _SCENES)
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)

    assert window.studio_page.capture_panel.scene_ids() == ["pantalla", "cenital"]


@pytest.mark.gui
def test_closing_the_panel_does_not_stop_an_ongoing_recording(qtbot: QtBot, tmp_path: Path) -> None:
    backend = FakeCaptureBackend()
    capture = StudioCaptureUseCase(backend, _SCENES, enabled=True)
    backend.connect()
    capture.start_recording()
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.capture_button.setChecked(True)
    window.studio_page.capture_button.setChecked(False)
    qtbot.waitUntil(lambda: not backend.is_connected(), timeout=5000)

    assert "stop_recording" not in backend.commands


# --- MS-017: decirlo y pulsarlo son la misma orden ----------------------


def _connected_capture() -> tuple[StudioCaptureUseCase, FakeCaptureBackend]:
    backend = FakeCaptureBackend(scene_names=("Pantalla", "Cámara cenital"))
    capture = StudioCaptureUseCase(backend, _SCENES, enabled=True)
    backend.connect()
    return capture, backend


@pytest.mark.gui
def test_saying_graba_starts_recording_without_touching_the_conversation(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Una orden se ejecuta; no se guarda en el historial ni va al modelo."""
    capture, backend = _connected_capture()
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.input.setPlainText("graba")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: "start_recording" in backend.commands, timeout=5000)

    assert window.studio_page.message_count == 0
    assert window.message_list.count() == 0
    assert window.studio_page.input.toPlainText() == ""


@pytest.mark.gui
def test_saying_para_stops_the_recording(qtbot: QtBot, tmp_path: Path) -> None:
    capture, backend = _connected_capture()
    capture.start_recording()
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.input.setPlainText("para")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: "stop_recording" in backend.commands, timeout=5000)

    assert backend.commands.count("stop_recording") == 1


@pytest.mark.gui
def test_saying_a_camera_switches_the_scene(qtbot: QtBot, tmp_path: Path) -> None:
    capture, backend = _connected_capture()
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.input.setPlainText("cámbiate a la cámara cenital")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: "switch_scene:Cámara cenital" in backend.commands, timeout=5000)

    assert window.studio_page.message_count == 0


@pytest.mark.gui
def test_speaking_and_clicking_produce_the_same_command(qtbot: QtBot, tmp_path: Path) -> None:
    """MS-017: la voz y la interfaz llaman al mismo controlador."""
    spoken_capture, spoken_backend = _connected_capture()
    (tmp_path / "hablado").mkdir()
    spoken_window = _window(tmp_path / "hablado", spoken_capture)
    qtbot.addWidget(spoken_window)
    spoken_window.open_model_studio()
    spoken_window.studio_page.input.setPlainText("cambia a la cenital")
    spoken_window.studio_page.send_button.click()
    qtbot.waitUntil(
        lambda: any(c.startswith("switch_scene") for c in spoken_backend.commands), timeout=5000
    )

    clicked_capture, clicked_backend = _connected_capture()
    (tmp_path / "pulsado").mkdir()
    clicked_window = _window(tmp_path / "pulsado", clicked_capture)
    qtbot.addWidget(clicked_window)
    clicked_window.open_model_studio()
    clicked_window.studio_page.capture_panel.scene_selected.emit("cenital")
    qtbot.waitUntil(
        lambda: any(c.startswith("switch_scene") for c in clicked_backend.commands), timeout=5000
    )

    spoken = [c for c in spoken_backend.commands if c.startswith("switch_scene")]
    clicked = [c for c in clicked_backend.commands if c.startswith("switch_scene")]
    assert spoken == clicked == ["switch_scene:Cámara cenital"]


@pytest.mark.gui
def test_a_normal_question_still_goes_to_the_conversation(qtbot: QtBot, tmp_path: Path) -> None:
    """Hablar de una cámara no puede cambiar de plano."""
    capture, backend = _connected_capture()
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.input.setPlainText("¿qué cámara me recomiendas para el cenital?")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: window.studio_page.message_count > 0, timeout=5000)

    assert not any(command.startswith("switch_scene") for command in backend.commands)


@pytest.mark.gui
def test_without_a_capture_module_orders_are_just_messages(qtbot: QtBot, tmp_path: Path) -> None:
    window = _window(tmp_path)
    qtbot.addWidget(window)
    window.open_model_studio()

    window.studio_page.input.setPlainText("graba")
    window.studio_page.send_button.click()
    qtbot.waitUntil(lambda: window.studio_page.message_count > 0, timeout=5000)

    assert window.studio_page.message_bodies()[0][1] == "graba"


@pytest.mark.gui
def test_an_unauthorized_camera_never_switches_and_is_reported(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """No se adivina la escena más parecida: se rechaza y se dice."""
    capture, backend = _connected_capture()
    window = _window(tmp_path, capture)
    qtbot.addWidget(window)
    window.open_model_studio()
    window.studio_page.capture_panel.scene_selected.emit("la del salón")
    qtbot.waitUntil(
        lambda: bool(window.studio_page.capture_panel.message_label.text()), timeout=5000
    )

    assert not any(command.startswith("switch_scene") for command in backend.commands)
    assert "no está autorizada" in window.studio_page.capture_panel.message_label.text()


# --- Lo que la interfaz enseña, el sistema lo tiene que entender ---------


_BOTON_Y_ORDEN = (
    ("record_button", CaptureCommand.START_RECORDING),
    ("stop_button", CaptureCommand.STOP_RECORDING),
    ("pause_button", CaptureCommand.PAUSE_RECORDING),
    ("resume_button", CaptureCommand.RESUME_RECORDING),
    ("mark_button", CaptureCommand.MARK_MOMENT),
)


@pytest.mark.gui
def test_every_button_label_works_as_a_typed_order(qtbot: QtBot) -> None:
    """Escribir lo que pone en un botón tiene que hacer lo que hace el botón.

    Parece obvio y no lo era: el botón de parar pone «Detener», y «detener» no
    se reconocía —solo «para»—, así que quien leía el botón y lo escribía no
    conseguía nada y no tenía forma de saber por qué. Una palabra que la
    interfaz enseña y el sistema no entiende es peor que una que no se enseña,
    porque parece que el sistema está roto.
    """
    panel = StudioCapturePanel()
    qtbot.addWidget(panel)

    for atributo, orden in _BOTON_Y_ORDEN:
        etiqueta = getattr(panel, atributo).text()
        intencion = interpret(etiqueta, _SCENES)

        assert intencion is not None, f"«{etiqueta}» está escrito en un botón y no se reconoce"
        assert intencion.command is orden, f"«{etiqueta}» hace otra cosa distinta a su botón"


@pytest.mark.gui
def test_every_scene_button_can_also_be_asked_for_by_name(qtbot: QtBot) -> None:
    """Lo mismo con las escenas: el nombre que se ve es el que se puede decir."""
    panel = StudioCapturePanel()
    qtbot.addWidget(panel)
    panel.set_scenes([(escena.scene_id, escena.display_name) for escena in _SCENES.scenes])

    for boton in panel.scenes_container.findChildren(QPushButton):
        intencion = interpret(f"cambia a {boton.text()}", _SCENES)

        assert intencion is not None, f"«{boton.text()}» se ve en pantalla y no se puede pedir"
        assert intencion.command is CaptureCommand.SWITCH_SCENE
