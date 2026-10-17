"""Minimizar una hoja minimiza la ventana de Sirius (incidencia #696).

En Windows, una hoja modal que pertenece a la ventana no tiene botón en la barra de tareas:
minimizada, se quedaba como una barrita abajo a la izquierda, con la ventana de Sirius
bloqueada. Aquí se mira en offscreen, por los estados de Qt: lo que haga Windows con ellos
no se ve.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QMainWindow
from pytestqt.qtbot import QtBot

from sirius.presentation.sheet_window import fit_as_sheet

pytestmark = pytest.mark.gui

_MINIMIZADA = Qt.WindowState.WindowMinimized
_MAXIMIZADA = Qt.WindowState.WindowMaximized


def _hoja_de(qtbot: QtBot) -> tuple[QMainWindow, QDialog]:
    ventana = QMainWindow()
    qtbot.addWidget(ventana)
    ventana.show()
    qtbot.waitExposed(ventana)
    hoja = QDialog(ventana)
    fit_as_sheet(hoja)
    hoja.show()
    qtbot.waitExposed(hoja)
    return ventana, hoja


def test_minimizar_la_hoja_minimiza_la_ventana_y_no_la_hoja(qtbot: QtBot) -> None:
    ventana, hoja = _hoja_de(qtbot)

    hoja.showMinimized()

    assert not hoja.windowState() & _MINIMIZADA
    assert ventana.windowState() & _MINIMIZADA


def test_maximizar_y_cerrar_la_hoja_siguen_igual(qtbot: QtBot) -> None:
    ventana, hoja = _hoja_de(qtbot)

    hoja.showMaximized()

    assert hoja.windowState() & _MAXIMIZADA
    assert not ventana.windowState() & _MINIMIZADA
    hoja.close()
    assert not hoja.isVisible()
    assert ventana.isVisible()


def test_una_hoja_sin_dueña_se_minimiza_como_siempre(qtbot: QtBot) -> None:
    hoja = QDialog()
    qtbot.addWidget(hoja)
    fit_as_sheet(hoja)
    hoja.show()
    qtbot.waitExposed(hoja)

    hoja.showMinimized()

    assert hoja.windowState() & _MINIMIZADA
