"""La cara de Sirius en la ventana, dibujada (pieza B de ADR-259).

Dibuja con ``QPainter`` lo que dice ``FaceLife`` para cada instante: los ojos con sus
pupilas, los párpados, las cejas y la boca, sin imágenes ni vídeos. Un temporizador la
redibuja unas 30 veces por segundo en el hilo de la ventana, y la charla, el oído y la voz
trabajan en los suyos: aunque el modelo tarde, la cara sigue viva.

El reloj y el volumen se los dan: el reloj de la ventana en Sirius y el de las pruebas en
las pruebas, y el volumen, el de lo que suena por el altavoz. Apunta lo que dibujó la
última vez y cuántas veces ha dibujado: es lo que leen las pruebas de aceptación.

Los gestos le llegan por dos sitios (pieza C de la 0.4, ADR-261): los de lo que dice en
voz alta, del oído, cuando empieza a sonar la frase en que van, y los de lo escrito en la
ventana, que no suena, en cuanto llega el texto (``make``). Los dibuja con lo que dice
``FaceLife``: una ceja, las dos, la sonrisa, el guiño, los ojos en blanco y la cabeza.

Adónde mira se lo dicen (pieza D de la 0.4, ADR-262): ``Attention``, con lo que ve la
cámara y en qué está el oído. La mirada va con la izquierda y la derecha de la cámara, y
la cámara no es un espejo: quien sale a la izquierda de la imagen está a la derecha de
quien mira la pantalla. Así que la pupila se dibuja al revés en horizontal, y mira de
verdad hacia quien está.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType

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

#: Los colores con que se dibuja, por lo que pintan: el fondo, la cara, el blanco de los
#: ojos y su brillo, el iris, la pupila y el dentro de la boca abierta, y el trazo de las
#: cejas, la boca y las pestañas. Las pruebas de aceptación leen la cara de los píxeles de
#: la ventana por estos colores (ronda 1 de Codex sobre la PR #702).
PALETTE: Mapping[str, str] = MappingProxyType(
    {
        "fondo": "#1f2430",
        "cara": "#2b3242",
        "ojo": "#f2f4f8",
        "iris": "#3fb6d8",
        "pupila": "#1b1e27",
        "trazo": "#c9d1e3",
    }
)

_FONDO = QColor(PALETTE["fondo"])
_CARA = QColor(PALETTE["cara"])
_OJO = QColor(PALETTE["ojo"])
_IRIS = QColor(PALETTE["iris"])
_PUPILA = QColor(PALETTE["pupila"])
_TRAZO = QColor(PALETTE["trazo"])


class FaceWidget(QWidget):
    """La cara: un panel que se dibuja a sí mismo con la vida de ``FaceLife``."""

    def __init__(
        self,
        clock: Callable[[], float],
        level: Callable[[], float] = lambda: 0.0,
        gestures: Callable[[], tuple[str, tuple[str, ...]]] = lambda: ("", ()),
        gaze: Callable[[], tuple[float, float] | None] = lambda: None,
        *,
        life: FaceLife | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._clock = clock
        self._level = level
        #: Los gestos de lo que dice en voz alta que ya suenan, con la operación de su
        #: turno: ``LocalListening.speaking_gestures``.
        self._gestures = gestures
        #: Adónde mirar ahora, o ``None`` para mirar a su aire: ``Attention.gaze``.
        self._gaze = gaze
        self._gaze_failed = False
        self._life = life if life is not None else FaceLife()
        self._paints = 0
        self._last: tuple[float, FacePose] | None = None
        self._drawn: frozenset[str] = frozenset()
        self._volume_failed = False
        self._gestures_failed = False
        #: El turno de voz cuyos gestos ha visto, y cuántos ha hecho ya.
        self._gesture_turn = ""
        self._gestures_made = 0
        self.setMinimumHeight(150)
        self.setAccessibleName("La cara de Sirius")
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    def stop(self) -> None:
        """Deja de redibujarse sola: la ventana se cierra."""
        self._timer.stop()

    def make(self, gesture: str) -> None:
        """Hace ``gesture``: lo escrito en la ventana, que no suena, lo hace al llegar."""
        self._life.make(gesture)

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
        self._new_gestures()
        pose = self._life.pose(now, level=self._volume(), look_at=self._look_at())
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

    def _look_at(self) -> tuple[float, float] | None:
        """Adónde mirar; si no se puede saber, a su aire, por lo mismo que el volumen."""
        try:
            return self._gaze()
        except Exception as error:
            if not self._gaze_failed:
                self._gaze_failed = True
                _logger.warning("La cara no puede saber adónde mirar: %s", error)
            return None

    def _new_gestures(self) -> None:
        """Le pide a la vida los gestos de lo que dice que han empezado a sonar desde la
        última vez. Si no se pueden leer, sigue sin ellos, por lo mismo que el volumen."""
        try:
            turn, started = self._gestures()
        except Exception as error:
            if not self._gestures_failed:
                self._gestures_failed = True
                _logger.warning("La cara no puede leer los gestos de lo que dice: %s", error)
            return
        if turn != self._gesture_turn:
            self._gesture_turn, self._gestures_made = turn, 0
        for gesture in started[self._gestures_made :]:
            self._life.make(gesture)
        self._gestures_made = len(started)

    def _draw(self, painter: QPainter, pose: FacePose) -> None:
        ancho, alto = float(self.width()), float(self.height())
        painter.fillRect(self.rect(), _FONDO)
        lado = min(ancho, alto * 1.6)
        # Asentir y negar mueven la cabeza entera; respirar, un poco arriba y abajo.
        centro = QPointF(
            ancho / 2 + pose.head[0] * lado * 0.05,
            alto / 2 - pose.breath * alto * 0.012 - pose.head[1] * alto * 0.06,
        )
        cara = QRectF(centro.x() - lado * 0.45, centro.y() - alto * 0.45, lado * 0.9, alto * 0.9)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_CARA)
        painter.drawRoundedRect(cara, alto * 0.2, alto * 0.2)

        radio = alto * 0.13
        separacion = lado * 0.17
        altura_ojos = centro.y() - alto * 0.08
        for lado_x in (-1, 1):
            ojo = QPointF(centro.x() + lado_x * separacion, altura_ojos)
            # El guiño y la ceja que sube sola son los de la derecha de la pantalla. Con el
            # ceño, las puntas de dentro bajan; la ceja que sube sola baja la de dentro un
            # poco, como quien no se lo cree; las dos que suben, suben rectas.
            guino = pose.wink if lado_x == 1 else 0.0
            sola = pose.brow_raise if lado_x == 1 else 0.0
            self._draw_eye(painter, ojo, radio, pose, guino)
            self._draw_brow(
                painter, ojo, radio, lado_x, pose.brows + sola, max(-pose.brows, 0.0) + 0.6 * sola
            )
        self._draw_mouth(painter, QPointF(centro.x(), centro.y() + alto * 0.22), lado, alto, pose)

    def _draw_eye(
        self, painter: QPainter, ojo: QPointF, radio: float, pose: FacePose, guino: float
    ) -> None:
        painter.setBrush(_OJO)
        painter.drawEllipse(ojo, radio, radio)
        # Al revés en horizontal: la cámara no es un espejo.
        pupila = QPointF(ojo.x() - pose.gaze[0] * radio * 0.5, ojo.y() - pose.gaze[1] * radio * 0.5)
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
        cerrado = max(1.0 - min(max(pose.eyes, 0.0), 1.0), min(max(guino, 0.0), 1.0))
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
        if cerrado >= 0.95:
            # Cerrado del todo, como en un guiño, se ve la raya de las pestañas.
            raya = QPainterPath(QPointF(ojo.x() - radio * 0.85, ojo.y()))
            raya.quadTo(
                QPointF(ojo.x(), ojo.y() + radio * 0.35), QPointF(ojo.x() + radio * 0.85, ojo.y())
            )
            painter.setPen(_trazo(radio * 0.16))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(raya)
            painter.setPen(Qt.PenStyle.NoPen)

    def _draw_brow(
        self,
        painter: QPainter,
        ojo: QPointF,
        radio: float,
        lado_x: int,
        alzada: float,
        giro: float,
    ) -> None:
        """Una ceja: ``alzada`` la sube, de -1 a 1, y ``giro`` le baja la punta de dentro y
        le sube la de fuera, de 0 a 1."""
        altura = ojo.y() - radio * (1.45 + 0.35 * alzada)
        caida = radio * 0.25 * giro
        painter.setPen(_trazo(radio * 0.22))
        painter.drawLine(
            QPointF(ojo.x() + lado_x * radio * 0.8, altura - caida),
            QPointF(ojo.x() - lado_x * radio * 0.8, altura + caida),
        )
        painter.setPen(Qt.PenStyle.NoPen)

    def _draw_mouth(
        self, painter: QPainter, centro: QPointF, lado: float, alto: float, pose: FacePose
    ) -> None:
        ancho = lado * 0.22
        abierta = alto * 0.16 * min(max(pose.mouth, 0.0), 1.0)
        if abierta < 1.5:
            # Cerrada es una línea; sonriendo, se curva hacia arriba por las puntas.
            sonrisa = min(max(pose.smile, 0.0), 1.0)
            boca = QPainterPath(QPointF(centro.x() - ancho / 2, centro.y() - sonrisa * alto * 0.03))
            boca.quadTo(
                QPointF(centro.x(), centro.y() + sonrisa * alto * 0.07),
                QPointF(centro.x() + ancho / 2, centro.y() - sonrisa * alto * 0.03),
            )
            painter.setPen(_trazo(alto * 0.025))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(boca)
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
