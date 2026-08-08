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

TEMPORARY_PREFIX = "sirius-voz-"

_RIFF = b"RIFF"
_WAVE = b"WAVE"
_DATA = b"data"
_HEADER = 12
_CHUNK_HEADER = 8


def repair_wav_sizes(payload: bytes) -> bytes:
    """Reescribe los tamaños del encabezado WAV cuando llegan como marcador.

    El proveedor genera el audio mientras lo envía, así que escribe los tamaños
    de ``RIFF`` y de ``data`` antes de saber cuánto va a durar y los deja con un
    valor de relleno. Un reproductor que se fíe del encabezado puede cortar
    antes de tiempo o rechazar el archivo; FFmpeg avisa por consola —*«Ignoring
    maximum wav data size, file may be invalid»*, *«Packet corrupt»*— y estima
    la duración por el bitrate, que es justo lo que no se quiere de un audio que
    hay que oír entero. Aquí se sustituyen por los bytes que de verdad llegaron.

    Solo se toca lo que es imposible: un tamaño de cero o mayor que el archivo.
    Un encabezado coherente se deja intacto, porque tras ``data`` puede venir
    otro trozo legítimo y recortarlo sería estropear un audio correcto. Si el
    contenido no es un WAV reconocible se devuelve tal cual: este adaptador
    traduce, no descarta.
    """
    if len(payload) < _HEADER or payload[:4] != _RIFF or payload[8:_HEADER] != _WAVE:
        return payload

    buffer = bytearray(payload)
    offset = _HEADER
    while offset + _CHUNK_HEADER <= len(buffer):
        chunk_id = bytes(buffer[offset : offset + 4])
        declared = int.from_bytes(buffer[offset + 4 : offset + _CHUNK_HEADER], "little")
        available = len(buffer) - (offset + _CHUNK_HEADER)

        if chunk_id == _DATA:
            if declared != 0 and declared <= available:
                return payload
            buffer[offset + 4 : offset + _CHUNK_HEADER] = available.to_bytes(4, "little")
            buffer[4:8] = (len(buffer) - 8).to_bytes(4, "little")
            return bytes(buffer)

        if declared == 0 or declared > available:
            # Encabezado que no se puede recorrer: se deja el archivo intacto
            # antes que adivinar dónde empieza el audio.
            return payload
        # Los trozos ocupan un número par de bytes: uno impar lleva relleno.
        offset += _CHUNK_HEADER + declared + (declared % 2)

    return payload


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
        destination = self._directory / f"{TEMPORARY_PREFIX}{self._counter}.wav"

        try:
            response = self._client.audio.speech.create(
                model=self._model,
                voice=request.voice,
                input=request.text,
                instructions=request.instructions,
                response_format="wav",
            )
            destination.write_bytes(repair_wav_sizes(response.read()))
        except Exception as exc:  # traducido a un error tipado; nunca se relanza
            kind = _classify(exc)
            # Ni el texto ni la clave llegan al registro: solo el tipo de fallo.
            _logger.warning("síntesis de voz fallida (%s)", kind.value)
            destination.unlink(missing_ok=True)
            return SpeechError(kind, kind.value)

        return SynthesizedSpeech(audio_path=destination, character_count=len(request.text))
