"""Síntesis de voz real con la API de audio de OpenAI.

``available_voices()`` devuelve el juego del endpoint de síntesis por lotes,
que es el único autorizado. La voz ``cedar`` que fijaba #126 **no** está aquí:
se introdujo con la API en tiempo real, que queda fuera de alcance, y no se ha
podido verificar en este endpoint (hallazgo MS-A09). Si algún día se comprueba
que existe, se añade a la tupla y ya está: no hay nada más que tocar.

Nunca lanza por un fallo externo.
"""

from __future__ import annotations

from pathlib import Path

import openai

from sirius.infrastructure.logging import get_logger
from sirius.ports.text_to_speech import (
    SpeechError,
    SpeechErrorKind,
    SpeechRequest,
    SynthesizedSpeech,
)

_logger = get_logger(__name__)

DEFAULT_SPEECH_MODEL = "gpt-4o-mini-tts"

DEFAULT_VOICE = "onyx"
"""Voz de partida: masculina, serena y disponible con seguridad en este endpoint.

Es provisional y se decide con evidencia, escuchándolas. Está aquí como valor
por defecto, no como decisión cerrada.
"""

SPEECH_VOICES: tuple[str, ...] = (
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
    "verse",
)


def _classify(exc: Exception) -> SpeechErrorKind:
    if isinstance(exc, openai.AuthenticationError):
        return SpeechErrorKind.AUTHENTICATION
    if isinstance(exc, openai.PermissionDeniedError):
        return SpeechErrorKind.PERMISSION
    if isinstance(exc, openai.RateLimitError):
        return SpeechErrorKind.RATE_LIMITED
    if isinstance(exc, openai.APITimeoutError):
        return SpeechErrorKind.TIMEOUT
    if isinstance(exc, openai.APIConnectionError | openai.InternalServerError):
        return SpeechErrorKind.CONNECTION
    if isinstance(exc, openai.BadRequestError):
        return SpeechErrorKind.INVALID_VOICE
    return SpeechErrorKind.UNKNOWN


class OpenAISpeech:
    """Convierte texto en un WAV temporal con la API de audio de OpenAI."""

    def __init__(
        self,
        client: openai.OpenAI,
        temporary_directory: Path,
        model: str = DEFAULT_SPEECH_MODEL,
    ) -> None:
        self._client = client
        self._directory = temporary_directory
        self._model = model
        self._counter = 0

    def available_voices(self) -> tuple[str, ...]:
        return SPEECH_VOICES

    def synthesize(self, request: SpeechRequest) -> SynthesizedSpeech | SpeechError:
        # Se comprueba antes de llamar: una voz inexistente es un error de
        # configuración, y gastar una petición para descubrirlo no aporta nada.
        if request.voice not in SPEECH_VOICES:
            return SpeechError(
                SpeechErrorKind.INVALID_VOICE,
                f"la voz «{request.voice}» no existe en este proveedor",
            )

        self._directory.mkdir(parents=True, exist_ok=True)
        self._counter += 1
        destination = self._directory / f"sirius-voz-{self._counter}.wav"

        try:
            response = self._client.audio.speech.create(
                model=self._model,
                voice=request.voice,
                input=request.text,
                instructions=request.instructions,
                response_format="wav",
            )
            destination.write_bytes(response.read())
        except Exception as exc:  # traducido a un error tipado; nunca se relanza
            kind = _classify(exc)
            # Ni el texto ni la clave llegan al registro: solo el tipo de fallo.
            _logger.warning("síntesis de voz fallida (%s)", kind.value)
            destination.unlink(missing_ok=True)
            return SpeechError(kind, kind.value)

        return SynthesizedSpeech(audio_path=destination, character_count=len(request.text))
