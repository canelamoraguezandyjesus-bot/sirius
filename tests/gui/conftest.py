"""Shared pytest-qt safety net: no GUI test may ever show a real dialog.

``MainWindow`` routes every dialog through injectable seams (``show_warning``/
``show_information``/``confirm_restore``/``choose_backup_file``/
``open_containing_folder``, see ``sirius.presentation.main_window``); every
test helper in this package injects a no-op or recording double by default.
This fixture is the backstop: if some code path ever bypasses a seam and calls
a real ``QMessageBox``, ``QFileDialog`` or ``QDesktopServices`` static
directly, it fails loudly and immediately instead of opening a real window
(or a real file manager) on the desktop, or hanging the test run waiting for
a human click.
"""

from __future__ import annotations

from typing import NoReturn

import pytest
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox


def _blocked(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError(
        "A real QMessageBox was invoked during a test; inject show_warning/"
        "show_information/confirm_restore (or another test double) instead."
    )


def _file_dialog_blocked(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError(
        "A real QFileDialog was invoked during a test; inject choose_backup_file "
        "(or another test double) instead."
    )


def _desktop_services_blocked(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError(
        "A real QDesktopServices.openUrl was invoked during a test; inject "
        "open_containing_folder (or another test double) instead."
    )


@pytest.fixture(autouse=True)
def block_real_message_boxes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(QMessageBox, "warning", _blocked)
    monkeypatch.setattr(QMessageBox, "information", _blocked)
    monkeypatch.setattr(QMessageBox, "critical", _blocked)
    monkeypatch.setattr(QMessageBox, "question", _blocked)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", _file_dialog_blocked)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", _file_dialog_blocked)
    monkeypatch.setattr(QDesktopServices, "openUrl", _desktop_services_blocked)
