"""Presencia visual de Sirius: una entidad digital abstracta hecha de partículas.

No es un rostro. No hay malla facial, ni avatar, ni contorno de cabeza, ni
orejas, ni nariz, ni mandíbula, ni cuello, ni dientes. Es un contenedor digital
que sugiere una entidad activa mediante tres elementos puramente geométricos:

- **Ojos robóticos:** dos bloques geométricos que parpadean y cambian de tamaño
  de forma sutil e irregular, para dar sensación de vida y atención.
- **Boca abstracta:** una fila de barras verticales tipo ecualizador. En reposo
  es casi una línea horizontal; al hablar, las barras suben y bajan.
- **Contenedor:** cuatro marcas de esquina que encuadran la entidad y la leen
  como interfaz, no como cara.

**Sin sincronización labial.** Las barras no imitan fonemas ni analizan audio:
se agitan de forma continua y fluida mientras Sirius habla o está activo. El
movimiento nace de un pulso constante, no de la señal sonora.

Todo es determinista a partir de una semilla. El parpadeo y los cambios de
tamaño *parecen* aleatorios porque combinan frecuencias inconmensurables, pero
se reproducen exactamente igual en cada arranque, de modo que las pruebas
pueden comprobar la presencia sin depender del azar ni del reloj: ``advance()``
avanza el tiempo explícitamente y el temporizador solo existe para la
aplicación real.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QHideEvent, QPainter, QPaintEvent, QPen, QShowEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from sirius.domain.model_studio import StudioInteractionState
from sirius.presentation.model_studio import theme

_FRAME_INTERVAL_MS = 33
"""~30 fotogramas por segundo. Animación ligera que no bloquea la interfaz."""

DEFAULT_SEED = 20260807

_FIELD_PARTICLES = 200
_EYE_PARTICLES = 46
_MOUTH_BARS = 9
_MOUTH_PARTICLES_PER_BAR = 6

# --- Geometría de la entidad, en coordenadas normalizadas [-1, 1] --------

_EYE_CENTER_X = 0.26
_EYE_CENTER_Y = -0.16
_EYE_HALF_WIDTH = 0.075
_EYE_HALF_HEIGHT = 0.052

_MOUTH_CENTER_Y = 0.26
_MOUTH_HALF_WIDTH = 0.22
_MOUTH_BAR_REST_HEIGHT = 0.014
_MOUTH_BAR_ACTIVE_HEIGHT = 0.115

_CONTAINER_HALF = 0.72
_CONTAINER_ARM = 0.16
"""Marcas de esquina del contenedor: encuadran sin dibujar un marco cerrado."""

_REFERENCE_SIDE = 420.0
"""Lado en píxeles para el que se calibraron los radios de punto."""


class _Group(Enum):
    FIELD = auto()
    EYE = auto()
    MOUTH = auto()


@dataclass(slots=True)
class _Particle:
    """Un punto: dónde vive en reposo y cómo se agita alrededor de ese sitio.

    ``unit_x``/``unit_y`` son su posición dentro del bloque al que pertenece,
    en [-1, 1]. Gracias a ellas un ojo puede aplastarse al parpadear y una
    barra puede crecer sin recalcular anclajes.
    """

    anchor_x: float
    anchor_y: float
    group: _Group
    color: QColor
    radius: float
    drift_amplitude: float
    drift_speed: float
    phase_x: float
    phase_y: float
    unit_x: float = 0.0
    unit_y: float = 0.0
    bar_index: int = 0


def _build_particles(seed: int) -> list[_Particle]:
    rng = random.Random(seed)
    particles: list[_Particle] = []

    field_palette = (
        QColor(theme.PARTICLE_FAR),
        QColor(theme.PARTICLE_FAR),
        QColor(theme.PARTICLE_MID),
    )
    for _ in range(_FIELD_PARTICLES):
        # Disco con el centro despejado: la entidad respira y el campo queda
        # alrededor, nunca encima de los ojos ni de la boca.
        angle = rng.uniform(0.0, math.tau)
        distance = 0.34 + 0.60 * math.sqrt(rng.random())
        particles.append(
            _Particle(
                anchor_x=math.cos(angle) * distance,
                anchor_y=math.sin(angle) * distance,
                group=_Group.FIELD,
                color=rng.choice(field_palette),
                radius=rng.uniform(0.7, 1.2),
                drift_amplitude=rng.uniform(0.008, 0.024),
                drift_speed=rng.uniform(0.18, 0.62),
                phase_x=rng.uniform(0.0, math.tau),
                phase_y=rng.uniform(0.0, math.tau),
            )
        )

    eye_palette = (
        QColor(theme.PARTICLE_MID),
        QColor(theme.PARTICLE_NEAR),
        QColor(theme.PARTICLE_NEAR),
    )
    for side in (-1.0, 1.0):
        for _ in range(_EYE_PARTICLES):
            # Rejilla con temblor: densa y rectangular, para que el ojo se lea
            # como un bloque geométrico y no como una mancha redonda.
            unit_x = rng.uniform(-1.0, 1.0)
            unit_y = rng.uniform(-1.0, 1.0)
            particles.append(
                _Particle(
                    anchor_x=side * _EYE_CENTER_X,
                    anchor_y=_EYE_CENTER_Y,
                    group=_Group.EYE,
                    color=rng.choice(eye_palette),
                    radius=rng.uniform(1.0, 1.6),
                    drift_amplitude=rng.uniform(0.001, 0.004),
                    drift_speed=rng.uniform(0.4, 0.9),
                    phase_x=rng.uniform(0.0, math.tau),
                    phase_y=rng.uniform(0.0, math.tau),
                    unit_x=unit_x,
                    unit_y=unit_y,
                )
            )

    mouth_palette = (QColor(theme.PARTICLE_MID), QColor(theme.PARTICLE_NEAR))
    for bar_index in range(_MOUTH_BARS):
        position = -1.0 + 2.0 * bar_index / (_MOUTH_BARS - 1)
        for slot in range(_MOUTH_PARTICLES_PER_BAR):
            unit_y = -1.0 + 2.0 * slot / (_MOUTH_PARTICLES_PER_BAR - 1)
            particles.append(
                _Particle(
                    anchor_x=position * _MOUTH_HALF_WIDTH,
                    anchor_y=_MOUTH_CENTER_Y,
                    group=_Group.MOUTH,
                    color=rng.choice(mouth_palette),
                    radius=rng.uniform(1.0, 1.5),
                    drift_amplitude=rng.uniform(0.001, 0.003),
                    drift_speed=rng.uniform(0.3, 0.7),
                    phase_x=rng.uniform(0.0, math.tau),
                    phase_y=rng.uniform(0.0, math.tau),
                    unit_y=unit_y,
                    bar_index=bar_index,
                )
            )

    return particles


@dataclass(frozen=True, slots=True)
class _StateLook:
    """Cómo altera un estado la presencia, sin cambiar su composición."""

    field_motion: float
    eye_brightness: float
    eye_pulse: float
    mouth_activity: float
    """0 = boca casi plana; 1 = ecualizador en pleno movimiento."""
    overall_opacity: float
    animated: bool
    blinks: bool


# ``eye_brightness`` se queda por debajo de 1.0 en reposo a propósito: si los
# ojos ya estuvieran al máximo, el pulso al escuchar no tendría margen para
# notarse. Además responde a "más brillantes que el campo, pero sin convertirse
# en elementos sólidos".
_LOOKS: dict[StudioInteractionState, _StateLook] = {
    # Apagado: se intuye que hay algo, no se mueve nada y no parpadea.
    StudioInteractionState.DESACTIVADO: _StateLook(0.0, 0.30, 0.0, 0.0, 0.28, False, False),
    # Reposo: agitación lenta y continua; la entidad está viva y atenta.
    StudioInteractionState.PREPARADO: _StateLook(1.0, 0.75, 0.0, 0.0, 1.0, True, True),
    # Escuchando: los ojos pulsan y se abren más; la boca sigue quieta.
    StudioInteractionState.ESCUCHANDO: _StateLook(0.9, 1.0, 1.0, 0.0, 1.0, True, True),
    StudioInteractionState.TRANSCRIBIENDO: _StateLook(1.2, 0.88, 0.35, 0.10, 1.0, True, True),
    StudioInteractionState.REVISANDO: _StateLook(0.8, 0.80, 0.0, 0.0, 1.0, True, True),
    # Pensando: el campo se agita y se expande, sin formar nada reconocible.
    StudioInteractionState.PENSANDO: _StateLook(2.6, 0.72, 0.2, 0.0, 1.0, True, True),
    StudioInteractionState.EJECUTANDO: _StateLook(1.9, 0.88, 0.45, 0.20, 1.0, True, True),
    StudioInteractionState.SINTETIZANDO: _StateLook(1.2, 0.78, 0.0, 0.35, 1.0, True, True),
    # Hablando: ecualizador a pleno rendimiento y agitación continua del campo.
    StudioInteractionState.HABLANDO: _StateLook(1.5, 0.82, 0.0, 1.0, 1.0, True, True),
    # Error: pierde estabilidad y brillo, sin destellos agresivos.
    StudioInteractionState.ERROR: _StateLook(1.6, 0.50, 0.0, 0.0, 0.55, True, True),
}


def _blink_openness(time: float) -> float:
    """Apertura del ojo en [0, 1]. 1 = abierto, 0 = cerrado del todo.

    El ritmo se modula con una segunda frecuencia inconmensurable, así que los
    parpadeos caen a intervalos irregulares —que es lo que los hace creíbles—
    sin usar azar: el mismo instante da siempre el mismo resultado.
    """
    rate = 0.23 + 0.05 * math.sin(time * 0.11)
    cycle = time * rate + 0.35
    phase = cycle - math.floor(cycle)
    if phase >= 0.08:
        return 1.0
    return abs(math.cos(phase / 0.08 * math.pi))


def _bar_height(time: float, bar_index: int, activity: float) -> float:
    """Altura de una barra del ecualizador.

    Cada barra tiene su propia frecuencia y su propio desfase, de modo que el
    conjunto se agita de forma fluida y nunca al unísono. No hay análisis de
    audio: es un pulso constante.
    """
    if activity <= 0.0:
        return _MOUTH_BAR_REST_HEIGHT
    speed = 4.1 + 0.7 * bar_index
    phase = bar_index * 1.37
    wave = 0.5 + 0.5 * math.sin(time * speed + phase)
    # Segunda onda lenta: el conjunto crece y decrece además de vibrar.
    swell = 0.65 + 0.35 * math.sin(time * 1.3 + bar_index * 0.4)
    reach = (
        _MOUTH_BAR_REST_HEIGHT + (_MOUTH_BAR_ACTIVE_HEIGHT - _MOUTH_BAR_REST_HEIGHT) * wave * swell
    )
    return _MOUTH_BAR_REST_HEIGHT + (reach - _MOUTH_BAR_REST_HEIGHT) * activity


class PresenceWidget(QWidget):
    """La entidad de partículas. Solo sabe pintar un estado, no producirlo."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        seed: int = DEFAULT_SEED,
        animated: bool = True,
    ) -> None:
        super().__init__(parent)
        self._particles = _build_particles(seed)
        self._state = StudioInteractionState.PREPARADO
        self._elapsed = 0.0
        self._animation_enabled = animated

        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        self.setMinimumSize(160, 160)
        # Cuadrada: ocupa el ancho que le den y la misma altura, ni más ni
        # menos. Así el contexto queda pegado debajo y el hueco sobrante se va
        # al final de la columna.
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setAccessibleName("Presencia visual de Sirius")
        self.setAccessibleDescription(
            "Entidad abstracta de partículas azules, con dos ojos geométricos y "
            "una boca de barras, que refleja el estado de Sirius."
        )

        self._timer = QTimer(self)
        self._timer.setInterval(_FRAME_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)

    # --- Estado ----------------------------------------------------------

    @property
    def state(self) -> StudioInteractionState:
        return self._state

    def set_state(self, state: StudioInteractionState) -> None:
        """Cambia el estado representado. Idempotente."""
        if state is self._state:
            return
        self._state = state
        self._sync_timer()
        self.update()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return width

    @property
    def particle_count(self) -> int:
        """Número de puntos. Fijo: sirve para acotar el coste de pintar."""
        return len(self._particles)

    def advance(self, seconds: float) -> None:
        """Avanza la animación de forma explícita.

        Es el único camino por el que corre el tiempo, también para el
        temporizador. Las pruebas lo llaman directamente y obtienen siempre el
        mismo fotograma para el mismo instante.
        """
        if not _LOOKS[self._state].animated:
            return
        self._elapsed += seconds
        self.update()

    # --- Ciclo de vida ---------------------------------------------------

    def _on_tick(self) -> None:
        self.advance(_FRAME_INTERVAL_MS / 1000.0)

    def _sync_timer(self) -> None:
        should_run = self._animation_enabled and self.isVisible() and _LOOKS[self._state].animated
        if should_run and not self._timer.isActive():
            self._timer.start()
        elif not should_run and self._timer.isActive():
            self._timer.stop()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event: QHideEvent) -> None:
        # Fuera de vista no se gasta un solo fotograma: mientras el usuario
        # trabaja en la interfaz técnica, Model Studio no consume CPU.
        self._timer.stop()
        super().hideEvent(event)

    # --- Dibujo ----------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        try:
            painter.fillRect(self.rect(), QColor(theme.BACKGROUND))
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            side = min(self.width(), self.height()) * 0.86
            if side <= 0.0:
                return
            self._paint_container(painter, side)
            self._paint_particles(painter, side)
        finally:
            painter.end()

    def _paint_container(self, painter: QPainter, side: float) -> None:
        """Cuatro marcas de esquina: encuadran la entidad como una interfaz.

        No es un marco cerrado ni un contorno de cabeza; son cuatro ángulos
        sueltos, que es lo que distingue un contenedor digital de un retrato.
        """
        look = _LOOKS[self._state]
        color = QColor(theme.PARTICLE_FAR)
        color.setAlphaF(max(0.0, min(1.0, 0.75 * look.overall_opacity)))
        pen = QPen(color)
        pen.setWidthF(max(1.0, side / 300.0))
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        half = side / 2.0
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        extent = _CONTAINER_HALF * half
        arm = _CONTAINER_ARM * half

        for sign_x in (-1.0, 1.0):
            for sign_y in (-1.0, 1.0):
                corner_x = center_x + sign_x * extent
                corner_y = center_y + sign_y * extent
                painter.drawLine(
                    QPointF(corner_x, corner_y),
                    QPointF(corner_x - sign_x * arm, corner_y),
                )
                painter.drawLine(
                    QPointF(corner_x, corner_y),
                    QPointF(corner_x, corner_y - sign_y * arm),
                )

    def _paint_particles(self, painter: QPainter, side: float) -> None:
        look = _LOOKS[self._state]
        half = side / 2.0
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        radius_scale = max(0.75, side / _REFERENCE_SIDE)
        time = self._elapsed

        painter.setPen(Qt.PenStyle.NoPen)

        # Agitación global constante: la entidad nunca queda del todo inmóvil.
        expansion = 1.0 + 0.018 * math.sin(time * 0.6) + 0.010 * math.sin(time * 1.47)
        eye_pulse = 0.5 + 0.5 * math.sin(time * 2.1)
        openness = _blink_openness(time) if look.blinks else 1.0
        # Cambio de tamaño sutil e irregular, distinto en cada ojo.
        eye_scale = 1.0 + 0.10 * math.sin(time * 0.73) + 0.06 * math.sin(time * 1.19)

        for particle in self._particles:
            drift = particle.drift_amplitude * look.field_motion
            offset_x = drift * math.sin(time * particle.drift_speed + particle.phase_x)
            offset_y = drift * math.cos(time * particle.drift_speed + particle.phase_y)

            x = particle.anchor_x + offset_x
            y = particle.anchor_y + offset_y
            alpha_scale = look.overall_opacity
            radius = particle.radius

            if particle.group is _Group.EYE:
                x += particle.unit_x * _EYE_HALF_WIDTH * eye_scale
                y += particle.unit_y * _EYE_HALF_HEIGHT * eye_scale * openness
                # El pulso baja el brillo entre latidos y lo devuelve al
                # máximo del estado: sube y baja sin llegar nunca a destello.
                alpha_scale *= look.eye_brightness * (
                    1.0 - 0.35 * look.eye_pulse * (1.0 - eye_pulse)
                )
            elif particle.group is _Group.MOUTH:
                height = _bar_height(time, particle.bar_index, look.mouth_activity)
                y += particle.unit_y * height
                alpha_scale *= 0.85
            else:
                x *= expansion
                y *= expansion

            color = QColor(particle.color)
            color.setAlphaF(max(0.0, min(1.0, alpha_scale)))
            painter.setBrush(color)
            painter.drawEllipse(
                QPointF(center_x + x * half, center_y + y * half),
                radius * radius_scale,
                radius * radius_scale,
            )
