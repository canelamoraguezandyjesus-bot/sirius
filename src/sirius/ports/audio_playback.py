"""Contrato de reproducción de audio, neutral respecto del dispositivo.

Detener y silenciar son idempotentes a propósito: son los controles que el
usuario pulsa con prisa mientras graba, y pulsarlos dos veces no puede romper
nada ni dejar audio sonando.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class PlaybackErrorKind(StrEnum):
    NO_DEVICE = "no_device"
    DEVICE_BUSY = "device_busy"
    INVALID_AUDIO = "invalid_audio"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PlaybackError:
    kind: PlaybackErrorKind
    message: str


class AudioPlayback(Protocol):
    """Reproduce un archivo de audio ya generado."""

    def play(self, audio_path: Path, on_finished: Callable[[], None]) -> PlaybackError | None:
        """Empieza a reproducir. Devuelve el error si no pudo, o ``None``.

        ``on_finished`` se invoca al terminar de forma natural, no al detener:
        quien detiene ya sabe que ha detenido.
        """
        ...

    def stop(self) -> None:
        """Detiene la reproducción. Idempotente."""
        ...

    def set_muted(self, muted: bool) -> None:
        """Silencia o reactiva la salida. Idempotente."""
        ...

    def is_playing(self) -> bool: ...

    @property
    def is_muted(self) -> bool: ...
