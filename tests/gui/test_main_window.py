from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sirius.presentation.main_window import MainWindow


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


@pytest.mark.gui
def test_main_window_has_expected_title(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Sirius 0.1"
