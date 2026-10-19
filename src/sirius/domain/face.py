"""La cara de Sirius: cómo está en cada instante (pieza B de ADR-259).

Es la capa base del busto de Disney que pide el plan (§6, «Lo que se hace», 4 a 6): en
reposo parpadea sin ritmo fijo, mueve un poco los ojos y «respira», y la boca sigue el
volumen de su voz. Aquí no se pinta nada: se dice, para un instante, cómo están los ojos,
la mirada, las cejas y la boca, y la ventana lo dibuja
(``sirius.presentation.face_widget``).

- **Sin ritmo fijo.** Cada parpadeo llega entre 2 y 6 s después del anterior, al azar, y
  dura un cuarto de segundo: se cierra en 70 ms, se queda cerrado 50 y se abre en 130.
- **La mirada se mueve un poco.** Cada 1,2 a 3,5 s salta a otro punto cerca del frente, a
  menos de 0,18 en horizontal y de 0,12 en vertical, y llega en 60 ms, de golpe, como un
  ojo de verdad.
- **Respira** con una onda de 4,4 s.
- **La boca** se abre con el volumen de lo que suena, de 0 a 1, y lo alcanza en unas
  centésimas: en un quinto de segundo está donde suena.
- **Todo sale del reloj que le den**: el de verdad en Sirius y el de las pruebas en las
  pruebas. Con el mismo reloj y la misma semilla, la misma cara.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

#: Entre cuántos segundos llega el parpadeo siguiente, al azar.
BLINK_EVERY: tuple[float, float] = (2.0, 6.0)
#: Lo que tarda un parpadeo en cerrarse, lo que se queda cerrado y lo que tarda en abrirse.
BLINK_CLOSING = 0.07
BLINK_CLOSED = 0.05
BLINK_OPENING = 0.13
#: Entre cuántos segundos salta la mirada a otro sitio, hasta dónde y en cuánto llega.
GAZE_EVERY: tuple[float, float] = (1.2, 3.5)
GAZE_REACH: tuple[float, float] = (0.18, 0.12)
GAZE_SACCADE = 0.06
#: Lo que dura una respiración, en segundos.
BREATH_PERIOD = 4.4
#: Lo que tarda la boca en seguir al volumen: en cinco veces esto está donde suena.
MOUTH_FOLLOW = 0.04
#: Tras cuántos segundos sin mirarla la cara empieza de nuevo, en vez de repasarlos.
RESTART_AFTER = 60.0


@dataclass(frozen=True, slots=True)
class FacePose:
    """La cara en un instante.

    ``eyes`` va de 0, cerrados, a 1, abiertos. ``gaze`` es hacia dónde miran, de -1 a 1 en
    cada eje, con la izquierda y la derecha de lo que ve la cámara: (0, 0) es al frente y
    la y crece hacia arriba. ``brows`` va de -1, fruncidas, a 1, arriba; ``mouth``, de 0,
    cerrada, a 1, abierta del todo; ``breath``, de -1 a 1, lo que sube y baja al respirar.
    ``gesture`` es el gesto de la lista que está haciendo, si hace alguno.
    """

    eyes: float
    gaze: tuple[float, float]
    brows: float
    mouth: float
    breath: float
    gesture: str | None = None


class FaceLife:
    """La vida de la cara: dado un instante y lo fuerte que suena su voz, cómo está.

    Lleva el parpadeo, la mirada y la boca de un instante al siguiente, así que se le
    pregunta con el tiempo hacia delante; si el reloj vuelve atrás, se toma el último
    instante que vio. Un salto largo del reloj, como el de una prueba que avanza una hora o
    el de un ordenador que vuelve de dormir, no deja nada a medias ni se para a repasarlo:
    el parpadeo y la mirada empiezan de nuevo desde ese instante.
    """

    def __init__(self, *, seed: int | None = None) -> None:
        self._random = random.Random(seed)
        self._start: float | None = None
        self._last = 0.0
        self._blink_at = -math.inf
        self._next_blink = 0.0
        self._gaze_from = (0.0, 0.0)
        self._gaze_to = (0.0, 0.0)
        self._gaze_at = -math.inf
        self._next_gaze = 0.0
        self._mouth = 0.0

    def pose(self, now: float, *, level: float = 0.0) -> FacePose:
        """La cara en ``now``, con su voz sonando a ``level``, de 0 a 1."""
        if self._start is None:
            self._start = now
            self._last = now
            self._next_blink = now + self._random.uniform(*BLINK_EVERY)
            self._next_gaze = now + self._random.uniform(*GAZE_EVERY)
        now = max(now, self._last)
        elapsed = now - self._last
        self._last = now
        # Tras un salto largo, como el de un ordenador que vuelve de dormir, se empieza de
        # nuevo desde ahora en vez de repasar cada parpadeo que no se vio.
        if now - self._next_blink > RESTART_AFTER:
            self._next_blink = now + self._random.uniform(*BLINK_EVERY)
        if now - self._next_gaze > RESTART_AFTER:
            self._next_gaze = now + self._random.uniform(*GAZE_EVERY)
        while self._next_blink <= now:
            self._blink_at = self._next_blink
            self._next_blink += self._random.uniform(*BLINK_EVERY)
        while self._next_gaze <= now:
            self._gaze_from = self._gaze_to
            self._gaze_to = (
                self._random.uniform(-GAZE_REACH[0], GAZE_REACH[0]),
                self._random.uniform(-GAZE_REACH[1], GAZE_REACH[1]),
            )
            self._gaze_at = self._next_gaze
            self._next_gaze += self._random.uniform(*GAZE_EVERY)
        target = min(max(level, 0.0), 1.0)
        self._mouth += (target - self._mouth) * (1 - math.exp(-elapsed / MOUTH_FOLLOW))
        return FacePose(
            eyes=1.0 - _closed(now - self._blink_at),
            gaze=self._gaze(now),
            brows=0.0,
            mouth=self._mouth,
            breath=math.sin(2 * math.pi * (now - self._start) / BREATH_PERIOD),
        )

    def _gaze(self, now: float) -> tuple[float, float]:
        done = min((now - self._gaze_at) / GAZE_SACCADE, 1.0)
        eased = done * done * (3 - 2 * done)
        return (
            self._gaze_from[0] + (self._gaze_to[0] - self._gaze_from[0]) * eased,
            self._gaze_from[1] + (self._gaze_to[1] - self._gaze_from[1]) * eased,
        )


def _closed(since: float) -> float:
    """Cuánto cierra el párpado ``since`` segundos después de empezar un parpadeo."""
    if since < 0 or since >= BLINK_CLOSING + BLINK_CLOSED + BLINK_OPENING:
        return 0.0
    if since < BLINK_CLOSING:
        return since / BLINK_CLOSING
    if since < BLINK_CLOSING + BLINK_CLOSED:
        return 1.0
    return 1.0 - (since - BLINK_CLOSING - BLINK_CLOSED) / BLINK_OPENING
