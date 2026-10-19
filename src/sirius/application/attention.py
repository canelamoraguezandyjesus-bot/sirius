"""A quién mira la cara (pieza D de la 0.4, ADR-262).

El plan (§6, «Lo que se hace», 6): mira a quien habla y aparta la vista al pensar. Lo
decide con lo que dice el oído de en qué está y con lo que ve la vista:

- **Oyendo un turno**, mira a quien mueve la boca, y se acuerda de él.
- **Pensando**, desde que el turno va a la charla hasta que dice algo, aparta la vista:
  arriba y hacia el lado contrario de quien le habló.
- **Hablando**, mira a quien le habló.
- **En nada**, mira a quien hable, o si no a quien le mire; si no, la cara mira a su aire.
- **Sin vista**, sin cámara enchufada en Sirius, aparta la vista al pensar igual, y lo demás
  lo mira a su aire.

La mirada va con la izquierda y la derecha de lo que ve la cámara, de -1 a 1, como dice
``FacePose``: quien está en ``x`` de la imagen, de 0 a 1, está en ``2x - 1``.

Lo lee la cara desde el hilo de la ventana, unas 30 veces por segundo, sin cerrojos: el
oído y la vista lo dan de lo último que saben. De quién le habló se acuerda aquí, de lo
que vio la última vez que le preguntaron mientras oía.
"""

from __future__ import annotations

from typing import Protocol

from sirius.application.local_listening import VoicePhase

#: Hacia dónde aparta la vista al pensar: arriba, y hacia el lado contrario de quien le
#: habló. La y crece hacia arriba.
AWAY = (0.55, 0.65)


class Hearing(Protocol):
    """Lo que la atención necesita del oído."""

    @property
    def phase(self) -> VoicePhase: ...


class Seeing(Protocol):
    """Lo que la atención necesita de la vista."""

    def talker_x(self) -> float | None: ...

    def watcher_x(self) -> float | None: ...


class Attention:
    """Adónde mira la cara ahora: un punto de la mirada, o ``None`` para que mire a su aire."""

    def __init__(self, hearing: Hearing | None, seeing: Seeing | None) -> None:
        self._hearing = hearing
        self._seeing = seeing
        #: Dónde estaba quien le habló la última vez que se le vio hablar oyéndole.
        self._last_talker: float | None = None

    def gaze(self) -> tuple[float, float] | None:
        phase = self._hearing.phase if self._hearing is not None else VoicePhase.QUIET
        seeing = self._seeing
        talker = seeing.talker_x() if seeing is not None else None
        if phase is VoicePhase.HEARING and talker is not None:
            self._last_talker = talker
        if phase is VoicePhase.THINKING:
            side = -1.0 if self._last_talker is not None and self._last_talker > 0.5 else 1.0
            return (side * AWAY[0], AWAY[1])
        if phase is VoicePhase.SPEAKING and self._last_talker is not None:
            return (_gaze_x(self._last_talker), 0.0)
        if talker is not None:
            return (_gaze_x(talker), 0.0)
        watcher = seeing.watcher_x() if seeing is not None else None
        return (_gaze_x(watcher), 0.0) if watcher is not None else None


def _gaze_x(x: float) -> float:
    """La mirada hacia quien está en ``x`` de la imagen."""
    return x * 2 - 1
