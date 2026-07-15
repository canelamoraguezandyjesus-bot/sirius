"""Regression test: no GUI test may ever show a real QMessageBox or QFileDialog.

``tests/gui/conftest.py`` blocks ``QMessageBox.warning/information/critical/
question`` and ``QFileDialog.getOpenFileName/getSaveFileName`` globally for
every GUI test, turning an accidental real dialog into a loud, immediate
failure instead of a hung test run or a real window on the desktop.
"""

from __future__ import annotations

import pytest
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
