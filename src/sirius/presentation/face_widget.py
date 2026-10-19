"""La cara de Sirius en la ventana, dibujada (pieza B de ADR-259).

Dibuja con ``QPainter`` lo que dice ``FaceLife`` para cada instante: los ojos con sus
pupilas, los párpados, las cejas y la boca, sin imágenes ni vídeos. Un temporizador la
redibuja unas 30 veces por segundo en el hilo de la ventana, y la charla, el oído y la voz
trabajan en los suyos: aunque el modelo tarde, la cara sigue viva.

El reloj y el volumen se los dan: el reloj de la ventana en Sirius y el de las pruebas en
las pruebas, y el volumen, el de lo que suena por el altavoz. Apunta lo que dibujó la
última vez y cuántas veces ha dibujado: es lo que leen las pruebas de aceptación.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from sirius.domain.face import FaceLife, FacePose
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)

#: Cada cuánto se redibuja, en milisegundos: unas 30 veces por segundo.
FRAME_MS = 33
#: Las partes que dibuja, con el nombre con que las lee quien mira la cara.
PARTS = frozenset({"ojos", "párpados", "cejas", "boca"})

_FONDO = QColor("#1f2430")
_CARA = QColor("#2b3242")
_OJO = QColor("#f2f4f8")
_IRIS = QColor("#3fb6d8")
_PUPILA = QColor("#1b1e27")
_TRAZO = QColor("#c9d1e3")


class FaceWidget(QWidget):
    """La cara: un panel que se dibuja a sí mismo con la vida de ``FaceLife``."""

    def __init__(
        self,
        clock: Callable[[], float],
        level: Callable[[], float] = lambda: 0.0,
        *,
        life: FaceLife | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._clock = clock
        self._level = level
        self._life = life if life is not None else FaceLife()
        self._paints = 0
        self._last: tuple[float, FacePose] | None = None
        self._drawn: frozenset[str] = frozenset()
        self._volume_failed = False
        self.setMinimumHeight(150)
        self.setAccessibleName("La cara de Sirius")
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    def stop(self) -> None:
        """Deja de redibujarse sola: la ventana se cierra."""
        self._timer.stop()

    @property
    def paints(self) -> int:
        """Cuántas veces se ha dibujado desde que se creó."""
        return self._paints

    @property
    def last_drawn(self) -> tuple[float, FacePose] | None:
        """El instante y la cara de la última vez que se dibujó; ``None`` si aún no."""
        return self._last

    @property
    def drawn_parts(self) -> frozenset[str]:
        """Las partes que dibujó la última vez."""
        return self._drawn

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        now = self._clock()
        pose = self._life.pose(now, level=self._volume())
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._draw(painter, pose)
        finally:
            painter.end()
        self._paints += 1
        self._last = (now, pose)
        self._drawn = PARTS

    def _volume(self) -> float:
        """Lo fuerte que suena su voz; si no se puede saber, callada. La cara no se para
        por eso: un fallo aquí la dejaría congelada, que es lo único que no puede pasar."""
        try:
            return float(self._level())
        except Exception as error:
            if not self._volume_failed:
                self._volume_failed = True
                _logger.warning("La cara no puede leer el volumen de su voz: %s", error)
            return 0.0

    def _draw(self, painter: QPainter, pose: FacePose) -> None:
        ancho, alto = float(self.width()), float(self.height())
        painter.fillRect(self.rect(), _FONDO)
        lado = min(ancho, alto * 1.6)
        centro = QPointF(ancho / 2, alto / 2 - pose.breath * alto * 0.012)
        cara = QRectF(centro.x() - lado * 0.45, centro.y() - alto * 0.45, lado * 0.9, alto * 0.9)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_CARA)
        painter.drawRoundedRect(cara, alto * 0.2, alto * 0.2)

        radio = alto * 0.13
        separacion = lado * 0.17
        altura_ojos = centro.y() - alto * 0.08
        for lado_x in (-1, 1):
            ojo = QPointF(centro.x() + lado_x * separacion, altura_ojos)
            self._draw_eye(painter, ojo, radio, pose)
            self._draw_brow(painter, ojo, radio, lado_x, pose.brows)
        self._draw_mouth(painter, QPointF(centro.x(), centro.y() + alto * 0.22), lado, alto, pose)

    def _draw_eye(self, painter: QPainter, ojo: QPointF, radio: float, pose: FacePose) -> None:
        painter.setBrush(_OJO)
        painter.drawEllipse(ojo, radio, radio)
        pupila = QPointF(ojo.x() + pose.gaze[0] * radio * 0.5, ojo.y() - pose.gaze[1] * radio * 0.5)
        painter.setBrush(_IRIS)
        painter.drawEllipse(pupila, radio * 0.5, radio * 0.5)
        painter.setBrush(_PUPILA)
        painter.drawEllipse(pupila, radio * 0.3, radio * 0.3)
        # El brillo, arriba a la izquierda y quieto aunque mire a otro sitio: es la luz.
        painter.setBrush(_OJO)
        painter.drawEllipse(
            QPointF(pupila.x() - radio * 0.14, pupila.y() - radio * 0.16), radio * 0.1, radio * 0.1
        )
        # El párpado baja desde arriba lo que tenga cerrado el ojo, sin salirse de él.
        cerrado = 1.0 - min(max(pose.eyes, 0.0), 1.0)
        if cerrado > 0:
            caja = QRectF(ojo.x() - radio, ojo.y() - radio, radio * 2, radio * 2).adjusted(
                -2, -2, 2, 2
            )
            borde = QPainterPath()
            borde.addEllipse(caja)
            painter.save()
            painter.setClipPath(borde)
            painter.fillRect(
                QRectF(caja.left(), caja.top(), caja.width(), caja.height() * cerrado), _CARA
            )
            painter.restore()

    def _draw_brow(
        self, painter: QPainter, ojo: QPointF, radio: float, lado_x: int, cejas: float
    ) -> None:
        altura = ojo.y() - radio * (1.45 + 0.35 * cejas)
        inclinacion = radio * 0.25 * cejas * lado_x
        painter.setPen(_trazo(radio * 0.22))
        painter.drawLine(
            QPointF(ojo.x() - radio * 0.8, altura + inclinacion),
            QPointF(ojo.x() + radio * 0.8, altura - inclinacion),
        )
        painter.setPen(Qt.PenStyle.NoPen)

    def _draw_mouth(
        self, painter: QPainter, centro: QPointF, lado: float, alto: float, pose: FacePose
    ) -> None:
        ancho = lado * 0.22
        abierta = alto * 0.16 * min(max(pose.mouth, 0.0), 1.0)
        if abierta < 1.5:
            painter.setPen(_trazo(alto * 0.025))
            painter.drawLine(
                QPointF(centro.x() - ancho / 2, centro.y()),
                QPointF(centro.x() + ancho / 2, centro.y()),
            )
            painter.setPen(Qt.PenStyle.NoPen)
            return
        painter.setBrush(_PUPILA)
        painter.setPen(_trazo(alto * 0.02))
        painter.drawEllipse(centro, ancho / 2, abierta / 2)
        painter.setPen(Qt.PenStyle.NoPen)


def _trazo(grosor: float) -> QPen:
    """El trazo de las cejas y la boca, con las puntas redondas."""
    pluma = QPen(_TRAZO, grosor)
    pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pluma
