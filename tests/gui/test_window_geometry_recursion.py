"""Regresión del cierre al acoplar o redimensionar la ventana.

El defecto observado: al arrastrar Sirius para acoplarlo a media pantalla en
Windows, la interfaz entraba en un recálculo que no terminaba y el proceso
moría con ``RecursionError``.

La causa medida era un bucle de realimentación de geometría. ``_sync_size``
llamaba a ``adjustSize()``, que redimensiona el widget al ancho de su propio
sizeHint; pero quien manda sobre esa geometría es el contenedor, que acto
seguido le reimpone el ancho de la columna. Cada ida y vuelta reflui el texto
a un alto distinto, que emite ``height_changed``, que vuelve a llamar a
``_sync_size``. En X11 ese intercambio se difiere al bucle de eventos y solo
oscila; en Windows el sistema entrega ``WM_SIZE`` de forma síncrona durante
``SetWindowPos``, así que las dos mitades se apilan en la misma pila de
llamadas hasta agotarla.

Estas pruebas fijan las dos garantías que cierran el defecto: ningún manejador
de geometría puede reentrar, y ninguno impone geometría que el contenedor vaya
a contradecir.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.domain.conversation import MessageRole
from sirius.presentation.message_view import MessageItemWidget

from .test_conversation_ui import _bootstrapped_database, _build_window

LONG_MESSAGE = "palabra " * 300


def _hosted_message_widget(qtbot: QtBot, width: int = 600) -> tuple[QWidget, MessageItemWidget]:
    """Un mensaje dentro de un contenedor que gobierna su geometría."""
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    widget = MessageItemWidget()
    layout.addWidget(widget)
    qtbot.addWidget(host)
    host.resize(width, 400)
    host.show()
    qtbot.waitUntil(lambda: widget.width() > 0, timeout=5000)
    widget.set_message("Sirius", LONG_MESSAGE, bold=True)
    QApplication.processEvents()
    return host, widget


@pytest.mark.gui
def test_the_message_body_follows_the_container_width(qtbot: QtBot) -> None:
    """El síntoma visible del bucle: ``adjustSize`` imponía su propio ancho.

    Con el contenedor a 900 px el cuerpo se quedaba clavado en 256, que es el
    ancho del sizeHint por omisión de un QTextEdit, y dejaba de seguirlo.
    """
    host, widget = _hosted_message_widget(qtbot)
    body = widget._segment_bodies[0]

    for container_width in (400, 800, 350, 900):
        host.resize(container_width, 400)
        QApplication.processEvents()
        assert body.width() > container_width - 60, (
            f"el cuerpo ({body.width()}) no sigue al contenedor ({container_width}): "
            "algo le está imponiendo una geometría propia"
        )


@pytest.mark.gui
def test_a_resize_emits_one_geometry_update_per_message(qtbot: QtBot) -> None:
    """Cada cambio de ancho debe estabilizarse a la primera, no rebotar."""
    host, widget = _hosted_message_widget(qtbot)
    emissions: list[int] = []
    widget.size_changed.connect(lambda: emissions.append(1))

    widths = (420, 780, 360, 880)
    for width in widths:
        host.resize(width, 400)
        QApplication.processEvents()

    # Con el rebote de ``adjustSize`` cada cambio de ancho emitía varias veces.
    assert len(emissions) == len(widths), (
        f"{len(emissions)} emisiones para {len(widths)} cambios de ancho: la "
        "geometría está rebotando en vez de estabilizarse"
    )


@pytest.mark.gui
def test_the_body_height_sync_cannot_reenter(qtbot: QtBot) -> None:
    """Reentrada síncrona, como la que provoca Windows al acoplar."""
    _host, widget = _hosted_message_widget(qtbot)
    body = widget._segment_bodies[0]
    entries = {"count": 0}

    def _reenter() -> None:
        # Al cambiar el alto, algo vuelve a pedir el MISMO recálculo dentro de
        # la misma pila, sin que el contenido haya cambiado: esa es la forma
        # exacta del bucle. Debe cortarse, no encadenarse.
        entries["count"] += 1
        if entries["count"] < 50:
            body._sync_height()

    body.height_changed.connect(_reenter)
    body.set_markdown_content("otro texto bastante más largo " * 40)

    assert entries["count"] == 1


@pytest.mark.gui
def test_the_widget_size_sync_cannot_reenter(qtbot: QtBot) -> None:
    host, widget = _hosted_message_widget(qtbot)
    entries = {"count": 0}

    def _reenter() -> None:
        # Reentrada directa: sin convergencia esto no terminaría nunca.
        entries["count"] += 1
        if entries["count"] < 200:
            widget._sync_size()

    widget.size_changed.connect(_reenter)

    # Un cambio real de ancho arranca la cadena; tiene que estabilizarse.
    host.resize(430, 400)
    QApplication.processEvents()

    assert 0 < entries["count"] <= 2, (
        f"la cadena de geometría no converge: {entries['count']} reentradas"
    )


@pytest.mark.gui
def test_scrolling_to_the_bottom_cannot_reenter(qtbot: QtBot, tmp_path: Path) -> None:
    """``setValue`` puede reemitir ``rangeChanged``, que vuelve a desplazar."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    repository = build_sqlite_conversation_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    for index in range(20):
        repository.append_message(conversation.id, MessageRole.SIRIUS, f"M{index} {LONG_MESSAGE}")

    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.resize(900, 600)
    window.show()
    qtbot.waitUntil(lambda: window.message_list.viewport().width() > 0, timeout=5000)

    entries = {"count": 0}

    def _reenter(_value: int) -> None:
        entries["count"] += 1
        if entries["count"] < 50:
            window._scroll_history_to_bottom()

    window.message_list.verticalScrollBar().valueChanged.connect(_reenter)
    window._scroll_history_to_bottom()

    assert entries["count"] <= 1


@pytest.mark.gui
def test_repeated_docking_like_resizes_stay_bounded(qtbot: QtBot, tmp_path: Path) -> None:
    """Acoplar a media pantalla, ida y vuelta, sin recálculo desbocado."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    repository = build_sqlite_conversation_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    for index in range(8):
        repository.append_message(conversation.id, MessageRole.SIRIUS, f"M{index} {LONG_MESSAGE}")

    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.resize(1200, 700)
    window.show()
    qtbot.waitUntil(lambda: window.message_list.viewport().width() > 0, timeout=5000)

    # Media pantalla, pantalla completa, media otra vez: el patrón del acoplado.
    for width in (600, 1200, 640, 1280, 620, 1100):
        window.resize(width, 700)
        QApplication.processEvents()
        assert window.message_list.count() == 8

    # Y el historial sigue siendo legible: sin solapamiento entre filas.
    rects = [
        window.message_list.visualItemRect(window.message_list.item(index))
        for index in range(window.message_list.count())
    ]
    for previous, current in itertools.pairwise(rects):
        assert current.y() >= previous.y() + previous.height()


@pytest.mark.gui
def test_maximize_restore_and_minimize_still_work(qtbot: QtBot, tmp_path: Path) -> None:
    """Ninguna de las garantías anteriores puede haberse perdido."""
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    repository = build_sqlite_conversation_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    repository.append_message(conversation.id, MessageRole.SIRIUS, LONG_MESSAGE)

    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.resize(1000, 700)
    window.show()
    qtbot.waitUntil(lambda: window.message_list.viewport().width() > 0, timeout=5000)

    window.showMaximized()
    QApplication.processEvents()
    assert window.isMaximized() or window.isVisible()

    window.showNormal()
    QApplication.processEvents()
    assert window.isVisible()

    window.showMinimized()
    QApplication.processEvents()

    window.showNormal()
    QApplication.processEvents()
    assert window.isVisible()
    assert window.message_list.count() == 1


@pytest.mark.gui
@pytest.mark.parametrize("scale_factor", ["1", "1.25", "1.5"])
def test_the_window_opens_under_windows_style_scaling(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scale_factor: str
) -> None:
    """El caso real ocurrió al 125 %; el arranque no puede depender de la escala.

    Solo se comprueba que la escala no rompe la construcción ni la geometría;
    la causa del cierre no era el escalado.
    """
    monkeypatch.setenv("QT_SCALE_FACTOR", scale_factor)
    database_path = _bootstrapped_database(tmp_path / "sirius.db")
    repository = build_sqlite_conversation_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    repository.append_message(conversation.id, MessageRole.SIRIUS, LONG_MESSAGE)

    window = _build_window(database_path)
    qtbot.addWidget(window)
    window.resize(900, 600)
    window.show()
    qtbot.waitUntil(lambda: window.message_list.viewport().width() > 0, timeout=5000)

    assert window.message_list.count() == 1
    assert window.message_list.item(0).sizeHint().height() > 0
    assert window.conversation_splitter.orientation() is Qt.Orientation.Horizontal
