"""Puertos del oído local del robot (pieza B de ADR-241, ADR-242).

El micro, el detector de turno y el transcriptor, sin tipos de ninguna biblioteca: los
de verdad (``sounddevice``, Silero y Smart Turn de Pipecat, faster-whisper) viven en
``sirius.adapters.audio.local_listening`` y se cargan solo si están instalados, y las
pruebas ponen dobles. Lo que pasa de uno a otro es un trozo de audio que Sirius no abre:
solo el micro que lo dio, el detector y el transcriptor saben qué hay dentro.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class TurnSignal(Enum):
    """Lo que dice el detector de cada trozo que le enseñan."""

    #: No hay voz en este trozo.
    QUIET = "quiet"
    #: Hay voz: el turno empieza o sigue.
    VOICE = "voice"
    #: Con este trozo, el turno ha acabado.
    ENDED = "ended"


class VoiceUnavailable(RuntimeError):
    """El oído no puede arrancar en este ordenador.

    ``fixed_by_install`` dice si lo arregla la orden de instalar la voz (falta una
    biblioteca o un modelo, o el modelo no carga) o no (no hay micrófono).
    """

    def __init__(self, reason: str, *, fixed_by_install: bool) -> None:
        super().__init__(reason)
        self.reason = reason
        self.fixed_by_install = fixed_by_install


class Microphone[Chunk](Protocol):
    """El micrófono, trozo a trozo."""

    def open(self) -> None:
        """Empieza a captar. Falla con ``VoiceUnavailable`` si no hay micrófono."""
        ...

    def close(self) -> None:
        """Deja de dar audio a Sirius y tira lo captado que nadie ha leído.

        No falla: pase lo que pase con el hardware, después de cerrar no llega ningún
        trozo más, y lo que no se haya podido cerrar se apunta en el diario.
        """
        ...

    def read(self) -> Chunk | None:
        """El siguiente trozo captado, o ``None`` si no ha llegado ninguno. No espera."""
        ...


class TurnDetector[Chunk](Protocol):
    """Silero y Smart Turn: si hay voz y si el turno ha acabado.

    Hay que enseñarle cada trozo, en orden y una sola vez: lleva la cuenta de los
    silencios y de la voz del turno.
    """

    def listen(self, chunk: Chunk) -> TurnSignal: ...

    def reset(self) -> None:
        """Olvida el turno que llevaba: lo siguiente que oiga empieza de cero.

        Si no puede, falla y se queda como estaba.
        """
        ...


class Transcriber[Chunk](Protocol):
    """faster-whisper: lo dicho en los trozos de un turno, en texto."""

    def transcribe(self, chunks: Sequence[Chunk]) -> str: ...


@dataclass(frozen=True, slots=True)
class ListeningEngines[Chunk]:
    """Las tres piezas del oído, ya cargadas."""

    microphone: Microphone[Chunk]
    detector: TurnDetector[Chunk]
    transcriber: Transcriber[Chunk]


class VoiceInstallation(Protocol):
    """Lo instalado en este ordenador para oír, y la orden que lo instala."""

    @property
    def install_command(self) -> str:
        """La orden que el propietario ejecuta para instalar la voz."""
        ...

    def missing(self) -> tuple[str, ...]:
        """Lo que falta para oír, dicho para el propietario; vacío si no falta nada."""
        ...
