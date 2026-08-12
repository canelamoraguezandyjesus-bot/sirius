"""Contrato de transcripción de voz a texto, neutral respecto del proveedor.

Nunca lanza por un fallo externo: devuelve ``Transcription`` o
``TranscriptionError``, igual que ``LLMProvider`` termina siempre en un evento
terminal. Así la aplicación trata todos los desenlaces igual y ningún tipo del
SDK se escapa hacia arriba.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Transcription:
    """Texto reconocido y duración real del audio.

    Informa de la cantidad, no del precio: la tarifa vive en ``BudgetPolicy``,
    en un solo sitio, y no repartida por cada adaptador.
    """

    text: str
    audio_seconds: float


class TranscriptionErrorKind(StrEnum):
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMITED = "rate_limited"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    INVALID_AUDIO = "invalid_audio"
    BUDGET_EXCEEDED = "budget_exceeded"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TranscriptionError:
    """Fallo de transcripción. ``message`` nunca incluye claves ni cuerpos."""

    kind: TranscriptionErrorKind
    message: str


class SpeechToText(Protocol):
    """Convierte un archivo de audio en texto."""

    def transcribe(self, audio_path: Path, language: str) -> Transcription | TranscriptionError:
        """Transcribe el audio. Nunca lanza por un fallo externo."""
        ...
