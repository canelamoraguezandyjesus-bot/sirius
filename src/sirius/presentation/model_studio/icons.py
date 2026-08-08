"""Iconos de Model Studio, dibujados en código.

§6 de ``SIRIUS-MODEL-STUDIO-UI-001`` pide iconos convencionales, sin
iconografía inventada y sin símbolos decorativos. Se dibujan con ``QPainter``
en vez de cargarse desde archivos por tres razones: no añaden ninguna
dependencia ni recurso que empaquetar, se adaptan al color y al tamaño que
pida quien los usa —lo que importa sobre fondo negro— y no dependen de que una
fuente concreta tenga un glifo.

Cada icono se dibuja sobre una rejilla lógica de 24 por 24 y se escala al tamaño
pedido. Las funciones son perezosas a propósito: construir un ``QPixmap`` exige
que exista una ``QGuiApplication``, así que nada de esto puede ocurrir al
importar el módulo.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_GRID = 24.0
_RENDER_SCALE = 4
"""Se dibuja al cuádruple y se deja que Qt reduzca: bordes limpios en HiDPI."""


def _pen(painter: QPainter, color: QColor, width: float = 1.9) -> None:
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _draw_microphone(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    painter.drawRoundedRect(QRectF(9.0, 3.0, 6.0, 10.0), 3.0, 3.0)
    path = QPainterPath(QPointF(5.5, 11.0))
    path.arcTo(QRectF(5.5, 5.0, 13.0, 13.0), 180.0, 180.0)
    painter.drawPath(path)
    painter.drawLine(QPointF(12.0, 17.5), QPointF(12.0, 21.0))


def _draw_send(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    path = QPainterPath(QPointF(3.0, 12.0))
    path.lineTo(QPointF(21.0, 4.0))
    path.lineTo(QPointF(14.5, 20.5))
    path.lineTo(QPointF(11.5, 13.6))
    path.closeSubpath()
    painter.drawPath(path)
    painter.drawLine(QPointF(11.5, 13.6), QPointF(21.0, 4.0))


def _draw_cancel(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    painter.drawLine(QPointF(5.5, 5.5), QPointF(18.5, 18.5))
    painter.drawLine(QPointF(18.5, 5.5), QPointF(5.5, 18.5))


def _draw_stop(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    painter.setBrush(color)
    painter.drawRoundedRect(QRectF(6.5, 6.5, 11.0, 11.0), 1.8, 1.8)


def _draw_speaker_body(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    path = QPainterPath(QPointF(4.0, 9.5))
    path.lineTo(QPointF(7.5, 9.5))
    path.lineTo(QPointF(12.0, 5.0))
    path.lineTo(QPointF(12.0, 19.0))
    path.lineTo(QPointF(7.5, 14.5))
    path.lineTo(QPointF(4.0, 14.5))
    path.closeSubpath()
    painter.drawPath(path)


def _draw_mute(painter: QPainter, color: QColor) -> None:
    _draw_speaker_body(painter, color)
    painter.drawLine(QPointF(15.5, 9.5), QPointF(20.5, 14.5))
    painter.drawLine(QPointF(20.5, 9.5), QPointF(15.5, 14.5))


def _draw_sound_on(painter: QPainter, color: QColor) -> None:
    """El altavoz con ondas: la voz está activa.

    Existe porque el altavoz tachado dibujado siempre se lee como «no hay
    sonido» aunque el botón sea el que silencia. El icono tiene que decir cómo
    está la voz, no qué pasa si lo pulsas.
    """
    _draw_speaker_body(painter, color)
    for radius in (4.5, 8.0):
        wave = QRectF(12.0 - radius, 12.0 - radius, radius * 2.0, radius * 2.0)
        path = QPainterPath()
        path.arcMoveTo(wave, -55.0)
        path.arcTo(wave, -55.0, 110.0)
        painter.drawPath(path)


def _draw_repeat(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    path = QPainterPath()
    path.arcMoveTo(QRectF(4.5, 4.5, 15.0, 15.0), 70.0)
    path.arcTo(QRectF(4.5, 4.5, 15.0, 15.0), 70.0, -300.0)
    painter.drawPath(path)
    head = QPainterPath(QPointF(11.2, 3.4))
    head.lineTo(QPointF(15.4, 5.6))
    head.lineTo(QPointF(11.0, 8.2))
    painter.drawPath(head)


def _draw_read_all(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    for index, width in enumerate((13.0, 10.0, 13.0, 7.0)):
        y = 5.5 + index * 4.3
        painter.drawLine(QPointF(3.5, y), QPointF(3.5 + width, y))
    head = QPainterPath(QPointF(18.2, 12.4))
    head.lineTo(QPointF(22.0, 14.8))
    head.lineTo(QPointF(18.2, 17.2))
    head.closeSubpath()
    painter.setBrush(color)
    painter.drawPath(head)


def _draw_fullscreen(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    corners = (
        ((4.0, 9.0), (4.0, 4.0), (9.0, 4.0)),
        ((15.0, 4.0), (20.0, 4.0), (20.0, 9.0)),
        ((20.0, 15.0), (20.0, 20.0), (15.0, 20.0)),
        ((9.0, 20.0), (4.0, 20.0), (4.0, 15.0)),
    )
    for start, corner, end in corners:
        path = QPainterPath(QPointF(*start))
        path.lineTo(QPointF(*corner))
        path.lineTo(QPointF(*end))
        painter.drawPath(path)


def _draw_settings(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    for index, knob_x in enumerate((15.0, 8.5, 17.0)):
        y = 6.0 + index * 6.0
        painter.drawLine(QPointF(3.5, y), QPointF(20.5, y))
        painter.setBrush(QColor(color))
        painter.drawEllipse(QPointF(knob_x, y), 2.3, 2.3)
        painter.setBrush(Qt.BrushStyle.NoBrush)


def _draw_capture(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    painter.drawEllipse(QPointF(12.0, 12.0), 8.6, 8.6)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(12.0, 12.0), 4.2, 4.2)


def _draw_exit_studio(painter: QPainter, color: QColor) -> None:
    _pen(painter, color)
    painter.drawLine(QPointF(4.0, 12.0), QPointF(14.5, 12.0))
    head = QPainterPath(QPointF(9.0, 7.0))
    head.lineTo(QPointF(4.0, 12.0))
    head.lineTo(QPointF(9.0, 17.0))
    painter.drawPath(head)
    painter.drawLine(QPointF(19.0, 4.5), QPointF(19.0, 19.5))


_PAINTERS: dict[str, Callable[[QPainter, QColor], None]] = {
    "microphone": _draw_microphone,
    "send": _draw_send,
    "cancel": _draw_cancel,
    "stop": _draw_stop,
    "mute": _draw_mute,
    "sound_on": _draw_sound_on,
    "repeat": _draw_repeat,
    "read_all": _draw_read_all,
    "fullscreen": _draw_fullscreen,
    "settings": _draw_settings,
    "capture": _draw_capture,
    "exit_studio": _draw_exit_studio,
}

AVAILABLE_ICONS = frozenset(_PAINTERS)


def studio_icon(name: str, color: str, size: int) -> QIcon:
    """Devuelve el icono ``name`` dibujado en ``color`` a ``size`` píxeles.

    Lanza ``KeyError`` si el nombre no existe: un icono mal escrito debe
    romper en la construcción de la ventana, no aparecer en blanco al grabar.
    """
    painter_function = _PAINTERS[name]
    pixmap = QPixmap(size * _RENDER_SCALE, size * _RENDER_SCALE)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        scale = size * _RENDER_SCALE / _GRID
        painter.scale(scale, scale)
        painter_function(painter, QColor(color))
    finally:
        painter.end()

    pixmap.setDevicePixelRatio(float(_RENDER_SCALE))
    return QIcon(pixmap)
