from pathlib import Path

import pytest
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
from sirius.composition_root import build_conversation_dependencies
from sirius.presentation.main_window import MainWindow


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


def _bootstrapped_database(database_path: Path) -> Path:
    """Mimic initialize_persistence(): schema + the three canonical singletons."""
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_project_repository(database_path).get_or_create_active_project()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    return database_path


def _build_window(database_path: Path) -> MainWindow:
    dependencies = build_conversation_dependencies(database_path)
    return MainWindow(
        send_message_use_case=dependencies.send_message_use_case,
        get_history_use_case=dependencies.get_history_use_case,
    )


@pytest.mark.gui
def test_main_window_has_expected_title(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    window = _build_window(database_path)
    qtbot.addWidget(window)

    assert window.windowTitle() == "Sirius 0.1"
