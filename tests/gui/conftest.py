"""Shared pytest-qt safety net: no GUI test may ever show a real QMessageBox.

``MainWindow`` routes every dialog through an injectable ``show_warning``/
``show_information`` seam (see ``sirius.presentation.main_window``); every
test helper in this package injects a no-op double by default. This fixture
is the backstop: if some code path ever bypasses that seam and calls the real
``QMessageBox`` statics directly, it fails loudly and immediately instead of
opening a real window on the desktop or hanging the test run waiting for a
human click.
"""

from __future__ import annotations

from typing import NoReturn

import pytest
from PySide6.QtWidgets import QMessageBox


def _blocked(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError(
        "A real QMessageBox was invoked during a test; inject show_warning/"
        "show_information (or another test double) instead."
    )


@pytest.fixture(autouse=True)
def block_real_message_boxes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(QMessageBox, "warning", _blocked)
    monkeypatch.setattr(QMessageBox, "information", _blocked)
    monkeypatch.setattr(QMessageBox, "critical", _blocked)
    monkeypatch.setattr(QMessageBox, "question", _blocked)
