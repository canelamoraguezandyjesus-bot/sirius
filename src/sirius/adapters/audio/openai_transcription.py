"""Transcripción real con la API de audio de OpenAI.

Traduce cada excepción del SDK a un error tipado del puerto, igual que hace
``OpenAIResponsesProvider`` con el texto: nada de ``openai`` sale de este
archivo hacia arriba. Cambiar de proveedor de transcripción es escribir otro
adaptador junto a este, sin tocar el caso de uso ni la interfaz.

Nunca lanza por un fallo externo.
"""

from __future__ import annotations

import wave
from pathlib import Path

import openai

from sirius.infrastructure.logging import get_logger
from sirius.ports.speech_to_text import (
    Transcription,
    TranscriptionError,
    TranscriptionErrorKind,
)

_logger = get_logger(__name__)

DEFAULT_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"


def _classify(exc: Exception) -> TranscriptionErrorKind:
    if isinstance(exc, openai.AuthenticationError):
        return TranscriptionErrorKind.AUTHENTICATION
    if isinstance(exc, openai.PermissionDeniedError):
        return TranscriptionErrorKind.PERMISSION
    if isinstance(exc, openai.RateLimitError):
        return TranscriptionErrorKind.RATE_LIMITED
    if isinstance(exc, openai.APITimeoutError):
        return TranscriptionErrorKind.TIMEOUT
    if isinstance(exc, openai.APIConnectionError | openai.InternalServerError):
        return TranscriptionErrorKind.CONNECTION
    if isinstance(exc, openai.BadRequestError):
        return TranscriptionErrorKind.INVALID_AUDIO
    return TranscriptionErrorKind.UNKNOWN


def _wav_duration_seconds(audio_path: Path) -> float:
    """Duración real del WAV, para descontarla del presupuesto.

    Se lee del propio archivo y no se estima: el precio de transcribir va por
    minutos, así que una estimación optimista falsearía el gasto.
    """
    try:
        with wave.open(str(audio_path), "rb") as handle:
            frame_rate = handle.getframerate()
            if frame_rate <= 0:
                return 0.0
            return handle.getnframes() / float(frame_rate)
    except OSError, wave.Error:
        return 0.0


class OpenAITranscription:
    """Convierte un WAV en texto con la API de audio de OpenAI."""

    def __init__(
        self,
        client: openai.OpenAI,
        model: str = DEFAULT_TRANSCRIPTION_MODEL,
    ) -> None:
        self._client = client
        self._model = model

    def transcribe(self, audio_path: Path, language: str) -> Transcription | TranscriptionError:
        if not audio_path.exists():
            return TranscriptionError(
                TranscriptionErrorKind.INVALID_AUDIO, "el audio ya no está disponible"
            )
        try:
            with audio_path.open("rb") as handle:
                response = self._client.audio.transcriptions.create(
                    model=self._model,
                    file=handle,
                    language=language,
                )
        except Exception as exc:  # traducido a un error tipado; nunca se relanza
            kind = _classify(exc)
            # El registro no incluye el audio, ni la transcripción, ni la clave:
            # solo el tipo de fallo.
            _logger.warning("transcripción fallida (%s)", kind.value)
            return TranscriptionError(kind, kind.value)

        text = getattr(response, "text", None)
        if not isinstance(text, str):
            return TranscriptionError(
                TranscriptionErrorKind.UNKNOWN, "el proveedor no devolvió texto"
            )
        return Transcription(text=text, audio_seconds=_wav_duration_seconds(audio_path))
