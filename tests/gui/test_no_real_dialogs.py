"""Regression test: no GUI test may ever show a real dialog or file manager.

``tests/gui/conftest.py`` blocks ``QMessageBox.warning/information/critical/
question``, ``QFileDialog.getOpenFileName/getSaveFileName`` and
``QDesktopServices.openUrl`` globally for every GUI test, turning an
accidental real dialog — or a real Explorer window opened by the "Abrir
carpeta" button — into a loud, immediate failure instead of a hung test run
or a stray window on the desktop.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox


def test_calling_the_real_qmessagebox_warning_is_blocked_during_tests() -> None:
    with pytest.raises(AssertionError):
        QMessageBox.warning(None, "título", "texto")


def test_calling_the_real_qmessagebox_information_is_blocked_during_tests() -> None:
    with pytest.raises(AssertionError):
        QMessageBox.information(None, "título", "texto")


def test_calling_the_real_qmessagebox_critical_is_blocked_during_tests() -> None:
    with pytest.raises(AssertionError):
        QMessageBox.critical(None, "título", "texto")


def test_calling_the_real_qmessagebox_question_is_blocked_during_tests() -> None:
    with pytest.raises(AssertionError):
        QMessageBox.question(None, "título", "texto")


def test_calling_the_real_qfiledialog_getopenfilename_is_blocked_during_tests() -> None:
    with pytest.raises(AssertionError):
        QFileDialog.getOpenFileName(None, "título")


def test_calling_the_real_qfiledialog_getsavefilename_is_blocked_during_tests() -> None:
    with pytest.raises(AssertionError):
        QFileDialog.getSaveFileName(None, "título")


def test_calling_the_real_qdesktopservices_openurl_is_blocked_during_tests() -> None:
    with pytest.raises(AssertionError):
        QDesktopServices.openUrl(QUrl.fromLocalFile("/tmp"))
