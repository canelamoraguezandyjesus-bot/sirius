from pathlib import Path
from typing import cast

import pytest
from PySide6.QtWidgets import QTabWidget
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import build_conversation_dependencies
from sirius.presentation.main_window import MainWindow
from sirius.presentation.project_continuity_widget import NO_BLOCKERS_TEXT, ProjectContinuityWidget


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path, *, configure_project: bool = True) -> Path:
    """Mimic initialize_persistence(): schema + the three canonical singletons.

    ``configure_project=True`` (the default) also completes the placeholder
    project, representing an installation that has already been through
    B3a's first-project screen — the normal case ``MainWindow`` expects.
    """
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project = project_repository.get_or_create_active_project()
    if configure_project:
        project_repository.update_project(
            project.id,
            name="Sirius 0.1",
            objective="Cerrar B3b",
            current_state="en curso",
            next_step="escribir pruebas",
        )
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    return database_path


def _build_window(database_path: Path) -> MainWindow:
    dependencies = build_conversation_dependencies(
        database_path, database_path.parent / "backups", secret_store=FakeSecretStore()
    )
    return MainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
        api_key_settings_use_case=dependencies.api_key_settings_use_case,
        project_continuity_use_case=dependencies.project_continuity_use_case,
        create_backup_use_case=dependencies.create_backup_use_case,
        validate_backup_use_case=dependencies.validate_backup_use_case,
        restore_backup_use_case=dependencies.restore_backup_use_case,
        close_database_connections=dependencies.close_database_connections,
        show_warning=lambda title, text: None,
        show_information=lambda title, text: None,
    )


@pytest.mark.gui
def test_main_window_has_expected_title(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.windowTitle() == "Sirius 0.1"


@pytest.mark.gui
def test_main_window_shows_the_project_continuity_widget_in_the_conversation_tab(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """B3b: the section lives in "Conversación" — no new tab is created."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    tabs = cast(QTabWidget, window.centralWidget())
    assert tabs.count() == 2
    assert tabs.tabText(0) == "Conversación"
    assert tabs.tabText(1) == "Configuración"
    assert isinstance(window.project_continuity_widget, ProjectContinuityWidget)
    assert window.project_continuity_widget.name_label.text() == "Sirius 0.1"
    assert window.project_continuity_widget.next_step_label.text() == "Ahora toca: escribir pruebas"


@pytest.mark.gui
def test_project_continuity_widget_shows_no_blockers_for_a_freshly_configured_project(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.project_continuity_widget.blockers_label.text() == NO_BLOCKERS_TEXT


@pytest.mark.gui
def test_main_window_built_without_a_configured_project_shows_a_safe_state(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Defensive: MainWindow built directly (bypassing the B3a gate) with only
    the bootstrap placeholder never creates a project and never crashes."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db", configure_project=False)
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.project_continuity_widget._current_summary is None


@pytest.mark.gui
def test_conversation_history_still_loads_alongside_the_continuity_widget(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.message_list is not None
    assert window.error_label.text() == ""
