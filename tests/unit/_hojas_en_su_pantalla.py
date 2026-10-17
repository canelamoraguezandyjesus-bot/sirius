"""Lo que se mira en las tres hojas que se abren encima de Sirius (ADR-247).

La prueba a ciegas, las preguntas trampa y la prueba de voces. En su ordenador, una
respuesta larguísima hizo la prueba a ciegas más ancha y más alta que la pantalla: no se
podía bajar ni leer, «Siguiente» quedaba fuera, y la hoja no tenía ni para minimizar. Aquí
se mira que cada hoja se minimiza, se maximiza y cambia de tamaño, que se abre a un tamaño
que cabe en la pantalla disponible, y que cada uno de sus pasos se baja con su barra.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QDialog, QScrollArea, QStackedWidget, QWidget
from pytestqt.qtbot import QtBot

from sirius.presentation.sheet_window import OPEN_SHARE


def abre(hoja: QDialog, qtbot: QtBot) -> None:
    """La enseña como en su ordenador, sin esperar a que se cierre."""
    hoja.show()
    qtbot.waitExposed(hoja)


def cabe_en_su_pantalla(hoja: QDialog) -> bool:
    disponible = hoja.screen().availableGeometry()
    marco = hoja.frameGeometry()
    return marco.width() <= disponible.width() and marco.height() <= disponible.height()


def se_ve_en(paso: QScrollArea, pieza: QWidget) -> bool:
    """Si ``pieza`` queda entera dentro de lo que enseña ``paso``, tal como está bajado."""
    donde = pieza.mapTo(paso.viewport(), QPoint(0, 0))
    return paso.viewport().rect().contains(QRect(donde, pieza.size()))


def mira_que_es_una_ventana_que_cabe(hoja: QDialog, pasos: QStackedWidget, qtbot: QtBot) -> None:
    """Botones de minimizar, maximizar y cerrar, sin el «?»; que cambia de tamaño, se abre
    a dos tercios de su pantalla y cada paso va dentro de su barra para bajar."""
    banderas = hoja.windowFlags()
    assert banderas & Qt.WindowType.WindowMinimizeButtonHint, "no se puede minimizar"
    assert banderas & Qt.WindowType.WindowMaximizeButtonHint, "no se puede maximizar"
    assert banderas & Qt.WindowType.WindowCloseButtonHint, "no se puede cerrar"
    assert not banderas & Qt.WindowType.WindowContextHelpButtonHint, "lleva el «?»"
    abre(hoja, qtbot)
    assert cabe_en_su_pantalla(hoja)
    assert hoja.size() == hoja.screen().availableGeometry().size() * OPEN_SHARE, (
        "no se abre a su tamaño"
    )
    assert hoja.minimumWidth() < hoja.maximumWidth(), "no cambia de ancho"
    assert hoja.minimumHeight() < hoja.maximumHeight(), "no cambia de alto"
    sin_barra = [i for i in range(pasos.count()) if not isinstance(pasos.widget(i), QScrollArea)]
    assert not sin_barra, f"los pasos {sin_barra} no se bajan"
