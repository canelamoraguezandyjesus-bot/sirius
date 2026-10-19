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
- **Los gestos** de la lista (``sirius.domain.gestures``) se hacen uno detrás de otro, en
  el orden en que llegan: cada uno se hace en 0,15 s como mucho, se sostiene y se deshace
  en 0,3, y dura lo suyo, de 0,6 s el guiño a 1,6 la sonrisa. Si llegan más de los que
  caben esperando, tres, los de más se dejan: la cara no se queda gesticulando lo que ya
  pasó (pieza C de la 0.4, ADR-261).
- **Todo sale del reloj que le den**: el de verdad en Sirius y el de las pruebas en las
  pruebas. Con el mismo reloj y la misma semilla, la misma cara.
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, replace

from sirius.domain.gestures import GESTURES

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
#: Lo que dura cada gesto de la lista, en segundos.
GESTURE_SECONDS: dict[str, float] = {
    "ceja_arriba": 1.2,
    "cejas_arriba": 1.0,
    "cejas_fruncidas": 1.4,
    "sonrisa": 1.6,
    "guino": 0.6,
    "ojos_en_blanco": 1.2,
    "asiente": 0.9,
    "niega": 1.1,
}
#: Lo que tarda un gesto en hacerse y en deshacerse.
GESTURE_IN = 0.15
GESTURE_OUT = 0.3
#: Cuántos gestos pueden esperar a que acabe el que se hace.
GESTURES_WAITING = 3
#: Adónde van los ojos en blanco: arriba del todo, como quien no puede más.
_EYES_ROLLED = (0.0, 0.9)


@dataclass(frozen=True, slots=True)
class FacePose:
    """La cara en un instante.

    ``eyes`` va de 0, cerrados, a 1, abiertos. ``gaze`` es hacia dónde miran, de -1 a 1 en
    cada eje, con la izquierda y la derecha de lo que ve la cámara: (0, 0) es al frente y
    la y crece hacia arriba. ``brows`` va de -1, fruncidas, a 1, arriba; ``mouth``, de 0,
    cerrada, a 1, abierta del todo; ``breath``, de -1 a 1, lo que sube y baja al respirar.
    ``gesture`` es el gesto de la lista que está haciendo, si hace alguno.

    Lo que ponen los gestos, todo de 0 a 1 salvo la cabeza: ``brow_raise``, cuánto sube la
    ceja de la derecha de la pantalla sobre las dos; ``wink``, cuánto cierra el ojo de la
    derecha de la pantalla un guiño, aparte del parpadeo; ``smile``, cuánto sonríe; y
    ``head``, cuánto se mueve la cabeza, de -1 a 1 en cada eje, como la mirada.
    """

    eyes: float
    gaze: tuple[float, float]
    brows: float
    mouth: float
    breath: float
    gesture: str | None = None
    brow_raise: float = 0.0
    wink: float = 0.0
    smile: float = 0.0
    head: tuple[float, float] = (0.0, 0.0)


class FaceLife:
    """La vida de la cara: dado un instante y lo fuerte que suena su voz, cómo está.

    Lleva el parpadeo, la mirada, la boca y los gestos de un instante al siguiente, así que
    se le pregunta con el tiempo hacia delante; si el reloj vuelve atrás, se toma el último
    instante que vio. Un salto largo del reloj, como el de una prueba que avanza una hora o
    el de un ordenador que vuelve de dormir, no deja nada a medias ni se para a repasarlo:
    el parpadeo y la mirada empiezan de nuevo desde ese instante.

    ``make`` le pide un gesto, que empieza en el instante siguiente por el que se le
    pregunte, o al acabar los que esperaban.
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
        self._waiting: deque[str] = deque()
        #: El gesto que hace y cuándo empezó.
        self._gesture: tuple[str, float] | None = None

    def make(self, gesture: str) -> None:
        """Hace ``gesture`` en cuanto acabe lo que ya iba a hacer. Uno que no es de la lista
        no se hace, ni uno que ya no cabe esperando."""
        if gesture in GESTURES and len(self._waiting) < GESTURES_WAITING:
            self._waiting.append(gesture)

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
        pose = FacePose(
            eyes=1.0 - _closed(now - self._blink_at),
            gaze=self._gaze(now),
            brows=0.0,
            mouth=self._mouth,
            breath=math.sin(2 * math.pi * (now - self._start) / BREATH_PERIOD),
        )
        return self._with_gesture(pose, now)

    def _with_gesture(self, pose: FacePose, now: float) -> FacePose:
        """``pose`` con el gesto que toca en ``now``, si toca alguno."""
        current = self._gesture
        if current is not None and now >= current[1] + GESTURE_SECONDS[current[0]]:
            current = None
        if current is None and self._waiting:
            current = (self._waiting.popleft(), now)
        self._gesture = current
        if current is None:
            return pose
        name, began = current
        since = now - began
        seconds = GESTURE_SECONDS[name]
        amount = _envelope(since, seconds)
        if name == "ceja_arriba":
            return replace(pose, gesture=name, brow_raise=amount)
        if name == "cejas_arriba":
            return replace(pose, gesture=name, brows=amount)
        if name == "cejas_fruncidas":
            return replace(pose, gesture=name, brows=-amount)
        if name == "sonrisa":
            return replace(pose, gesture=name, smile=amount)
        if name == "guino":
            return replace(pose, gesture=name, wink=amount)
        if name == "ojos_en_blanco":
            x, y = pose.gaze
            rolled = (
                x + (_EYES_ROLLED[0] - x) * amount,
                y + (_EYES_ROLLED[1] - y) * amount,
            )
            return replace(pose, gesture=name, gaze=rolled)
        # Asiente y niega van y vienen dos veces: abajo y arriba, o a un lado y al otro.
        swing = math.sin(4 * math.pi * since / seconds) * amount
        if name == "asiente":
            return replace(pose, gesture=name, head=(0.0, -swing))
        return replace(pose, gesture=name, head=(swing, 0.0))

    def _gaze(self, now: float) -> tuple[float, float]:
        done = min((now - self._gaze_at) / GAZE_SACCADE, 1.0)
        eased = done * done * (3 - 2 * done)
        return (
            self._gaze_from[0] + (self._gaze_to[0] - self._gaze_from[0]) * eased,
            self._gaze_from[1] + (self._gaze_to[1] - self._gaze_from[1]) * eased,
        )


def _envelope(since: float, seconds: float) -> float:
    """Cuánto se hace un gesto ``since`` segundos después de empezar, de 0 a 1: sube en
    ``GESTURE_IN``, se sostiene y baja en los últimos ``GESTURE_OUT``, sin saltos."""
    rise = min(since / GESTURE_IN, 1.0)
    fall = min(max(seconds - since, 0.0) / GESTURE_OUT, 1.0)
    done = min(rise, fall)
    return done * done * (3 - 2 * done)


def _closed(since: float) -> float:
    """Cuánto cierra el párpado ``since`` segundos después de empezar un parpadeo."""
    if since < 0 or since >= BLINK_CLOSING + BLINK_CLOSED + BLINK_OPENING:
        return 0.0
    if since < BLINK_CLOSING:
        return since / BLINK_CLOSING
    if since < BLINK_CLOSING + BLINK_CLOSED:
        return 1.0
    return 1.0 - (since - BLINK_CLOSING - BLINK_CLOSED) / BLINK_OPENING
