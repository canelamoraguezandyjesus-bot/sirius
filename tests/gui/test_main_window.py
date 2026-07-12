import pytest
from pytestqt.qtbot import QtBot

from sirius.presentation.main_window import MainWindow


@pytest.mark.gui
def test_main_window_has_expected_title(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Sirius 0.1"
