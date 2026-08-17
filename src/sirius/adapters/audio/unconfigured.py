"""Voz seleccionada pero todavía no utilizable.

Mismo criterio que ``UnconfiguredLLMProvider``: sin clave de proveedor, Sirius
arranca igual y la conversación escrita funciona igual. Lo único que pasa es
que, al pulsar el micrófono, se explica por qué no puede hablar todavía en vez
de fallar de forma rara o, peor, fingir que graba.
"""

from __future__ import annotations

from pathlib import Path

from sirius.ports.speech_to_text import Transcription, TranscriptionError, TranscriptionErrorKind
from sirius.ports.text_to_speech import (
    SpeechError,
    SpeechErrorKind,
    SpeechRequest,
    SynthesizedSpeech,
)


class UnconfiguredSpeechToText:
    """Nunca transcribe: explica que falta configurar el proveedor."""

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def transcribe(self, audio_path: Path, language: str) -> Transcription | TranscriptionError:
        del audio_path, language
        return TranscriptionError(TranscriptionErrorKind.CONFIGURATION, self._reason)


class UnconfiguredTextToSpeech:
    """Nunca sintetiza: explica que falta configurar el proveedor."""

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def synthesize(self, request: SpeechRequest) -> SynthesizedSpeech | SpeechError:
        del request
        return SpeechError(SpeechErrorKind.CONFIGURATION, self._reason)

    def available_voices(self) -> tuple[str, ...]:
        return ()
