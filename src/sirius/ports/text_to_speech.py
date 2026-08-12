"""Contrato de síntesis de voz, neutral respecto del proveedor.

La voz concreta es un dato de configuración, no una constante de código: el
documento de #126 fijaba ``cedar``, que está asociada a la API en tiempo real
y no se ha podido verificar en el endpoint de síntesis por lotes autorizado
(hallazgo MS-A09). Aquí la voz se pide, no se presupone, y cambiarla no toca
ni la aplicación ni la interfaz.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SpeechRequest:
    """Qué decir, con qué voz y con qué intención.

    ``instructions`` describe el tono —español natural, masculino, cercano,
    directo y sereno, sin voz de locutor— sin tocar la identidad canónica de
    Sirius, que vive en la memoria y no aquí.
    """

    text: str
    voice: str
    instructions: str


@dataclass(frozen=True, slots=True)
class SynthesizedSpeech:
    """Audio generado en un archivo temporal, y cuánto texto se sintetizó.

    Informa de la cantidad, no del precio: la tarifa vive en ``BudgetPolicy``.
    """

    audio_path: Path
    character_count: int


class SpeechErrorKind(StrEnum):
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMITED = "rate_limited"
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    INVALID_VOICE = "invalid_voice"
    BUDGET_EXCEEDED = "budget_exceeded"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SpeechError:
    kind: SpeechErrorKind
    message: str


class TextToSpeech(Protocol):
    """Convierte texto en un archivo de audio reproducible."""

    def synthesize(self, request: SpeechRequest) -> SynthesizedSpeech | SpeechError:
        """Sintetiza el texto. Nunca lanza por un fallo externo."""
        ...

    def available_voices(self) -> tuple[str, ...]:
        """Voces que el proveedor admite de verdad.

        Existe para no volver a fijar en un documento una voz que el endpoint
        autorizado quizá no acepte: quien configure puede comprobarlo antes.
        """
        ...
