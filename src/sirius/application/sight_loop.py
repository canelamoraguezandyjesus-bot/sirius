"""Mirar una y otra vez, en un hilo propio (pieza D de la 0.4, ADR-262).

Como el bucle del oído (``listening_loop``): con la ventana abierta, alguien tiene que leer
la cámara sin parar, y no puede ser el hilo de la ventana. Lo hace este bucle, que arranca
la ventana al abrirse y para al cerrarse.

- **Mira y espera**: ``EVERY_SECONDS`` entre vuelta y vuelta, unas diez veces por segundo,
  que basta para saber quién habla y quién mira.
- **Sin ver no hace nada**: ``look`` vuelve enseguida si la cámara no está abierta.
- **Un fallo que se escape no lo mata**: se apunta solo el tipo y vuelve a intentarlo al
  rato, sin llenar el diario.
- **Parar es pedírselo, sin esperar**, y el hilo es de fondo, como el del oído.
"""

from __future__ import annotations

import threading
from typing import Protocol

from sirius.infrastructure.logging import get_logger

#: Lo que espera entre vuelta y vuelta.
EVERY_SECONDS = 0.1
#: Lo que espera tras un fallo que no esperaba, para no llenar el diario.
FAILURE_PAUSE_SECONDS = 1.0

_logger = get_logger(__name__)


class Sight(Protocol):
    """Lo que el bucle necesita de la vista."""

    def look(self) -> None:
        """Mira una vez."""
        ...


class SightLoop:
    """Atiende a la vista en un hilo propio hasta que se le pide parar."""

    def __init__(
        self,
        sight: Sight,
        *,
        every_seconds: float = EVERY_SECONDS,
        failure_pause_seconds: float = FAILURE_PAUSE_SECONDS,
    ) -> None:
        self._sight = sight
        self._every = every_seconds
        self._failure_pause = failure_pause_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="sirius-vista", daemon=True)

    @property
    def running(self) -> bool:
        """Si el hilo sigue mirando."""
        return self._thread.is_alive()

    def start(self) -> None:
        """Empieza a mirar, en su hilo."""
        self._thread.start()

    def stop(self) -> None:
        """Le pide parar: acaba la vuelta en la que está y no da otra."""
        self._stop.set()

    def wait(self, timeout: float) -> bool:
        """Espera hasta ``timeout`` segundos a que pare; dice si ha parado."""
        if self._thread.ident is not None:
            self._thread.join(timeout)
        return not self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._sight.look()
            except Exception as error:
                _logger.error("La vista se interrumpió (%s)", type(error).__name__)
                self._stop.wait(self._failure_pause)
                continue
            self._stop.wait(self._every)
