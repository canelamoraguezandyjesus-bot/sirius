"""Presencia visual de Sirius: un campo de partículas con dos ojos y una boca.

§3 de ``SIRIUS-MODEL-STUDIO-UI-001`` es explícito sobre lo que esto **no** es:
no hay contorno de cabeza, ni orejas, ni nariz, ni mandíbula, ni cuello, ni
base, ni dientes, ni símbolo en la frente. Solo puntos azules sobre negro, con
dos concentraciones para los ojos y una curva para la boca, pequeños y
centrados, con mucho espacio negativo alrededor.

El movimiento es deliberadamente mínimo (§3.4): deriva casi imperceptible en
reposo, pulso suave en los ojos al escuchar, redistribución al pensar y
animación pequeña de la boca al hablar. Nunca destellos.

Todo es determinista a partir de una semilla, de modo que la misma presencia se
dibuja igual en cada arranque y las pruebas pueden comprobarla sin depender del
azar ni del reloj: ``advance()`` avanza el tiempo explícitamente y el
temporizador solo existe para la aplicación real.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QHideEvent, QPainter, QPaintEvent, QShowEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from sirius.domain.model_studio import StudioInteractionState
from sirius.presentation.model_studio import theme

_FRAME_INTERVAL_MS = 33
"""~30 fotogramas por segundo. §10 exige animación ligera que no bloquee."""

DEFAULT_SEED = 20260807

_FIELD_PARTICLES = 190
_EYE_PARTICLES = 34
_MOUTH_PARTICLES = 30

_EYE_CENTER_X = 0.24
_EYE_CENTER_Y = -0.13
_EYE_RADIUS = 0.085
_MOUTH_CENTER_Y = 0.24
_MOUTH_HALF_WIDTH = 0.28
_MOUTH_SAG = 0.028
"""Curvatura de la boca. Deliberadamente pequeña: con una curva marcada la
presencia se lee como una carita sonriente permanente, y §3.3 pide una línea o
curva discreta bajo los ojos, no una expresión fija."""

_REFERENCE_SIDE = 420.0
"""Lado en píxeles para el que se calibraron los radios de punto."""


class _Group(Enum):
    FIELD = auto()
    EYE = auto()
    MOUTH = auto()


@dataclass(slots=True)
class _Particle:
    """Un punto: dónde vive en reposo y cómo deriva alrededor de ese sitio."""

    anchor_x: float
    anchor_y: float
    group: _Group
    color: QColor
    radius: float
    drift_amplitude: float
    drift_speed: float
    phase_x: float
    phase_y: float


def _build_particles(seed: int) -> list[_Particle]:
    rng = random.Random(seed)
    particles: list[_Particle] = []

    field_palette = (
        QColor(theme.PARTICLE_FAR),
        QColor(theme.PARTICLE_FAR),
        QColor(theme.PARTICLE_MID),
    )
    for _ in range(_FIELD_PARTICLES):
        # Distribución en disco con sesgo hacia fuera: el centro queda
        # despejado para que la cara respire (§3.1, espacio negativo).
        angle = rng.uniform(0.0, math.tau)
        distance = 0.30 + 0.65 * math.sqrt(rng.random())
        particles.append(
            _Particle(
                anchor_x=math.cos(angle) * distance,
                anchor_y=math.sin(angle) * distance,
                group=_Group.FIELD,
                color=rng.choice(field_palette),
                radius=rng.uniform(0.7, 1.2),
                drift_amplitude=rng.uniform(0.006, 0.018),
                drift_speed=rng.uniform(0.16, 0.42),
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
            angle = rng.uniform(0.0, math.tau)
            distance = _EYE_RADIUS * math.sqrt(rng.random())
            particles.append(
                _Particle(
                    anchor_x=side * _EYE_CENTER_X + math.cos(angle) * distance * 1.15,
                    anchor_y=_EYE_CENTER_Y + math.sin(angle) * distance,
                    group=_Group.EYE,
                    color=rng.choice(eye_palette),
                    radius=rng.uniform(1.0, 1.7),
                    drift_amplitude=rng.uniform(0.003, 0.009),
                    drift_speed=rng.uniform(0.25, 0.55),
                    phase_x=rng.uniform(0.0, math.tau),
                    phase_y=rng.uniform(0.0, math.tau),
                )
            )

    mouth_palette = (QColor(theme.PARTICLE_MID), QColor(theme.PARTICLE_NEAR))
    for _ in range(_MOUTH_PARTICLES):
        # Curva suave, más discreta que los ojos pero claramente visible (§3.3).
        position = rng.uniform(-1.0, 1.0)
        particles.append(
            _Particle(
                anchor_x=position * _MOUTH_HALF_WIDTH,
                anchor_y=_MOUTH_CENTER_Y + _MOUTH_SAG * (1.0 - position * position),
                group=_Group.MOUTH,
                color=rng.choice(mouth_palette),
                radius=rng.uniform(0.9, 1.4),
                drift_amplitude=rng.uniform(0.002, 0.006),
                drift_speed=rng.uniform(0.2, 0.5),
                phase_x=rng.uniform(0.0, math.tau),
                phase_y=rng.uniform(0.0, math.tau),
            )
        )

    return particles


@dataclass(frozen=True, slots=True)
class _StateLook:
    """Cómo altera un estado la presencia, sin cambiar su composición."""

    field_motion: float
    eye_brightness: float
    eye_pulse: float
    mouth_openness: float
    mouth_motion: float
    overall_opacity: float
    animated: bool


# ``eye_brightness`` se queda por debajo de 1.0 en reposo a propósito: si los
# ojos ya estuvieran al máximo, el pulso de ``ESCUCHANDO`` no tendría margen
# para notarse y §3.2 quedaría sin cumplir. Además responde a "más brillantes
# que el campo, pero sin convertirse en elementos sólidos".
_LOOKS: dict[StudioInteractionState, _StateLook] = {
    # Apagado: se intuye que hay algo, no se mueve nada.
    StudioInteractionState.DESACTIVADO: _StateLook(0.0, 0.30, 0.0, 0.0, 0.0, 0.28, False),
    # Reposo: deriva lenta y casi imperceptible.
    StudioInteractionState.PREPARADO: _StateLook(1.0, 0.75, 0.0, 0.0, 0.0, 1.0, True),
    # Escuchando: pulso suave alrededor de los ojos.
    StudioInteractionState.ESCUCHANDO: _StateLook(0.9, 1.0, 1.0, 0.0, 0.0, 1.0, True),
    StudioInteractionState.TRANSCRIBIENDO: _StateLook(1.1, 0.88, 0.35, 0.0, 0.0, 1.0, True),
    StudioInteractionState.REVISANDO: _StateLook(0.8, 0.80, 0.0, 0.0, 0.0, 1.0, True),
    # Pensando: redistribución del campo, sin formar una cabeza.
    StudioInteractionState.PENSANDO: _StateLook(2.6, 0.72, 0.2, 0.0, 0.0, 1.0, True),
    StudioInteractionState.EJECUTANDO: _StateLook(1.9, 0.88, 0.45, 0.0, 0.0, 1.0, True),
    StudioInteractionState.SINTETIZANDO: _StateLook(1.2, 0.78, 0.0, 0.25, 0.3, 1.0, True),
    # Hablando: movimiento mínimo de boca y respiración del conjunto.
    StudioInteractionState.HABLANDO: _StateLook(1.3, 0.82, 0.0, 1.0, 1.0, 1.0, True),
    # Error: pierde estabilidad y brillo, sin destellos agresivos.
    StudioInteractionState.ERROR: _StateLook(1.6, 0.50, 0.0, 0.0, 0.0, 0.55, True),
}


class PresenceWidget(QWidget):
    """El campo de partículas. Solo sabe pintar un estado, no producirlo."""

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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Presencia visual de Sirius")
        self.setAccessibleDescription(
            "Campo de partículas azules que sugiere dos ojos y una boca, "
            "y refleja el estado de Sirius."
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
            painter.setPen(Qt.PenStyle.NoPen)
            self._paint_particles(painter)
        finally:
            painter.end()

    def _paint_particles(self, painter: QPainter) -> None:
        look = _LOOKS[self._state]
        side = min(self.width(), self.height()) * 0.86
        if side <= 0.0:
            return
        half = side / 2.0
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        radius_scale = max(0.75, side / _REFERENCE_SIDE)
        time = self._elapsed

        # Respiración global: un latido muy lento del conjunto.
        breath = 1.0 + 0.012 * math.sin(time * 0.6)
        eye_pulse = 0.5 + 0.5 * math.sin(time * 2.1)
        mouth_wave = math.sin(time * 5.5)

        for particle in self._particles:
            drift = particle.drift_amplitude * look.field_motion
            offset_x = drift * math.sin(time * particle.drift_speed + particle.phase_x)
            offset_y = drift * math.cos(time * particle.drift_speed + particle.phase_y)

            x = particle.anchor_x + offset_x
            y = particle.anchor_y + offset_y
            alpha_scale = look.overall_opacity
            radius = particle.radius

            if particle.group is _Group.EYE:
                # El pulso baja el brillo entre latidos y lo devuelve al máximo
                # del estado: sube y baja sin llegar nunca a destello.
                alpha_scale *= look.eye_brightness * (
                    1.0 - 0.35 * look.eye_pulse * (1.0 - eye_pulse)
                )
                # Al escuchar, los puntos se concentran ligeramente hacia el
                # centro del ojo: pulsa sin convertirse en un elemento sólido.
                if look.eye_pulse > 0.0:
                    eye_center_x = math.copysign(_EYE_CENTER_X, particle.anchor_x)
                    contraction = 0.06 * look.eye_pulse * eye_pulse
                    x += (eye_center_x - x) * contraction
                    y += (_EYE_CENTER_Y - y) * contraction
            elif particle.group is _Group.MOUTH:
                if look.mouth_openness > 0.0:
                    # La boca varía de altura y anchura, sin dientes ni labios
                    # y sin sincronía fonema a fonema (§3.3).
                    opening = look.mouth_openness * (0.55 + 0.45 * mouth_wave)
                    y += 0.035 * opening * (1.0 if particle.anchor_y > _MOUTH_CENTER_Y else -1.0)
                    x *= 1.0 + 0.06 * opening
                    radius *= 1.0 + 0.18 * look.mouth_motion * abs(mouth_wave)
            else:
                x *= breath
                y *= breath

            color = QColor(particle.color)
            color.setAlphaF(max(0.0, min(1.0, alpha_scale)))
            painter.setBrush(color)
            painter.drawEllipse(
                QPointF(center_x + x * half, center_y + y * half),
                radius * radius_scale,
                radius * radius_scale,
            )
