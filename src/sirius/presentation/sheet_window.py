"""Lo que comparten las hojas que se abren encima de Sirius (ADR-247).

La prueba a ciegas, las preguntas trampa y la prueba de voces. En su ordenador, una
respuesta larguísima hizo la prueba a ciegas más ancha y más alta que la pantalla: no se
podía bajar ni leer, «Siguiente» quedaba fuera, y la hoja no tenía ni para minimizar. Desde
entonces cada hoja es una ventana de Windows como cualquier otra: se minimiza, se maximiza
y cambia de tamaño, se abre a dos tercios de la pantalla disponible, y cada uno de sus
pasos va dentro de una barra para bajar, con el ancho de la hoja, así que el texto se parte
en líneas en vez de ensancharla.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QDialog, QFrame, QScrollArea, QWidget

__all__ = ["OPEN_SHARE", "fit_as_sheet", "scrollable"]

#: Lo que ocupa una hoja al abrirse, de la pantalla disponible donde está Sirius.
OPEN_SHARE = 2 / 3


def scrollable(page: QWidget) -> QScrollArea:
    """``page`` dentro de una barra para bajar que le da el ancho de la hoja."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidget(page)
    return area


class _MinimizeTheOwner(QObject):
    """Minimizar una hoja minimiza la ventana de Sirius, la dueña.

    En Windows, una hoja modal que pertenece a la ventana no tiene botón en la barra de
    tareas: minimizada, se quedaba como una barrita abajo a la izquierda, con la ventana de
    Sirius bloqueada, y parecía colgada. Así la hoja no se queda minimizada; se minimiza la
    dueña, que Windows esconde con todas las suyas y vuelve a enseñar con ellas al
    restaurarla desde la barra de tareas (incidencia #696).
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.WindowStateChange
            and isinstance(watched, QWidget)
            and watched.windowState() & Qt.WindowState.WindowMinimized
        ):
            owner = watched.parentWidget()
            if owner is not None:
                watched.setWindowState(watched.windowState() & ~Qt.WindowState.WindowMinimized)
                window = owner.window()
                window.setWindowState(window.windowState() | Qt.WindowState.WindowMinimized)
        return False


def fit_as_sheet(dialog: QDialog) -> None:
    """Botones de minimizar, maximizar y cerrar, sin el «?» de ayuda, y un tamaño que cabe.

    Se llama al final de construir la hoja, con sus pasos ya dentro de sus barras: así lo
    menos que puede medir es poco, y nada la ensancha más que la pantalla. Minimizarla
    minimiza la ventana de Sirius (``_MinimizeTheOwner``).
    """
    dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    dialog.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
    dialog.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
    dialog.installEventFilter(_MinimizeTheOwner(dialog))
    owner = dialog.parentWidget()
    available = (owner if owner is not None else dialog).screen().availableGeometry().size()
    size = (available * OPEN_SHARE).expandedTo(dialog.minimumSizeHint()).boundedTo(available)
    dialog.resize(size)
