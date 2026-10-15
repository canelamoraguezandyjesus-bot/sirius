"""Atender al oído una y otra vez, en un hilo propio (pieza D de la 0.3, ADR-244).

Con la ventana abierta, alguien tiene que leer el micro sin parar y contestar cada turno, y
no puede ser el hilo de la ventana: contestar tarda segundos y la congelaría. Lo hace este
bucle, que arranca ``sirius.main`` y para al salir. La ventana solo arranca la escucha,
la calla y hace de portera de cada turno (``ListeningBridge``).

- **Atiende y, si no llegó nada, espera un poco**: ``PAUSE_SECONDS``, lo que tarda el micro
  de verdad en traer el siguiente trozo, como la orden de consola.
- **Sin escuchar no hace nada**: ``attend`` vuelve enseguida si el micro está cerrado, antes
  de que se abra la ventana, con el botón de silencio o si dejó de oír.
- **Un fallo que se escape no lo mata**: se apunta solo el tipo, como todo lo del oído, y
  vuelve a intentarlo al rato, sin llenar el diario.
- **Parar es pedírselo, sin esperar**: la ventana lo para al cerrarse, y si el hilo
  estuviera preguntándole por un turno, esperarlo desde ella la colgaría. El hilo es de
  fondo: si un turno no ha acabado al salir, Sirius sale igual.
"""

from __future__ import annotations

import threading
from typing import Protocol

from sirius.application.local_listening import Attended
from sirius.infrastructure.logging import get_logger

#: Lo que espera antes de volver a mirar el micro, si no llegó nada.
PAUSE_SECONDS = 0.03
#: Lo que espera tras un fallo que no esperaba, para no llenar el diario.
FAILURE_PAUSE_SECONDS = 1.0

_logger = get_logger(__name__)


class Listening(Protocol):
    """Lo que el bucle necesita del oído."""

    def attend(self) -> Attended:
        """Atiende lo que ha llegado al micro."""
        ...


class ListeningLoop:
    """Atiende al oído en un hilo propio hasta que se le pide parar."""

    def __init__(
        self,
        listening: Listening,
        *,
        pause_seconds: float = PAUSE_SECONDS,
        failure_pause_seconds: float = FAILURE_PAUSE_SECONDS,
    ) -> None:
        self._listening = listening
        self._pause = pause_seconds
        self._failure_pause = failure_pause_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="sirius-oido", daemon=True)

    @property
    def running(self) -> bool:
        """Si el hilo sigue atendiendo."""
        return self._thread.is_alive()

    def start(self) -> None:
        """Empieza a atender, en su hilo."""
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
                attended = self._listening.attend()
            except Exception as error:
                _logger.error("El oído se interrumpió (%s)", type(error).__name__)
                self._stop.wait(self._failure_pause)
                continue
            if not attended.turns:
                self._stop.wait(self._pause)
