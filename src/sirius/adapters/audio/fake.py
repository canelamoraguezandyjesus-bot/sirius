"""Adaptadores de audio simulados, deterministas y sin red ni dispositivos.

Son los que usan CI y todas las pruebas automáticas: no abren el micrófono, no
suenan por los altavoces y no llaman a ningún proveedor. La prueba real con
hardware y clave queda para una ventana manual autorizada.

Nunca importan QtMultimedia, ni siquiera de forma perezosa. Esa es la razón de
que la suite entera pueda ejecutarse en el runner Linux de Quality, que no trae
``libpulse`` (hallazgo MS-A02).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sirius.ports.audio_capture import (
    AudioCaptureError,
    AudioCaptureErrorKind,
    AudioCaptureResult,
    CaptureLimits,
)
from sirius.ports.audio_playback import PlaybackError
from sirius.ports.speech_to_text import Transcription, TranscriptionError
from sirius.ports.text_to_speech import SpeechError, SpeechRequest, SynthesizedSpeech

_FAKE_WAV_HEADER = b"RIFF\x00\x00\x00\x00WAVEfmt "


class FakeAudioCapture:
    """Captura simulada: escribe un WAV mínimo en un directorio temporal."""

    def __init__(
        self,
        temporary_directory: Path,
        *,
        duration_seconds: float = 3.5,
        start_error: AudioCaptureError | None = None,
        stop_error: AudioCaptureError | None = None,
        stopped_by_limit: bool = False,
    ) -> None:
        self._directory = temporary_directory
        self._duration_seconds = duration_seconds
        self._start_error = start_error
        self._stop_error = stop_error
        self._stopped_by_limit = stopped_by_limit
        self._capturing = False
        self._current: Path | None = None
        self._counter = 0
        self.discarded: list[Path] = []
        self.cancelled = 0

    def start(self, limits: CaptureLimits) -> AudioCaptureError | None:
        del limits
        if self._start_error is not None:
            return self._start_error
        if self._capturing:
            return AudioCaptureError(AudioCaptureErrorKind.DEVICE_BUSY, "ya se está capturando")
        self._counter += 1
        self._current = self._directory / f"captura-{self._counter}.wav"
        self._current.write_bytes(_FAKE_WAV_HEADER)
        self._capturing = True
        return None

    def stop(self) -> AudioCaptureResult | AudioCaptureError:
        if not self._capturing or self._current is None:
            return AudioCaptureError(
                AudioCaptureErrorKind.NOT_CAPTURING, "no había captura en curso"
            )
        self._capturing = False
        captured = self._current
        self._current = None
        if self._stop_error is not None:
            self.discard(captured)
            return self._stop_error
        return AudioCaptureResult(
            audio_path=captured,
            duration_seconds=self._duration_seconds,
            size_bytes=captured.stat().st_size,
            stopped_by_limit=self._stopped_by_limit,
        )

    def cancel(self) -> None:
        self.cancelled += 1
        self._capturing = False
        if self._current is not None:
            self.discard(self._current)
            self._current = None

    def is_capturing(self) -> bool:
        return self._capturing

    def discard(self, audio_path: Path) -> None:
        self.discarded.append(audio_path)
        audio_path.unlink(missing_ok=True)


class FakeSpeechToText:
    """Transcripción simulada: devuelve un texto fijo o un error fijo."""

    def __init__(
        self,
        text: str = "hola Sirius",
        *,
        audio_seconds: float = 3.5,
        error: TranscriptionError | None = None,
    ) -> None:
        self._text = text
        self._audio_seconds = audio_seconds
        self._error = error
        self.calls: list[tuple[Path, str]] = []

    def transcribe(self, audio_path: Path, language: str) -> Transcription | TranscriptionError:
        self.calls.append((audio_path, language))
        if self._error is not None:
            return self._error
        return Transcription(text=self._text, audio_seconds=self._audio_seconds)


class FakeTextToSpeech:
    """Síntesis simulada: escribe un WAV mínimo y registra lo que se le pidió."""

    VOICES = ("onyx", "echo", "alloy", "sage")

    def __init__(self, temporary_directory: Path, *, error: SpeechError | None = None) -> None:
        self._directory = temporary_directory
        self._error = error
        self._counter = 0
        self.requests: list[SpeechRequest] = []

    def synthesize(self, request: SpeechRequest) -> SynthesizedSpeech | SpeechError:
        self.requests.append(request)
        if self._error is not None:
            return self._error
        self._counter += 1
        path = self._directory / f"voz-{self._counter}.wav"
        path.write_bytes(_FAKE_WAV_HEADER)
        return SynthesizedSpeech(audio_path=path, character_count=len(request.text))

    def available_voices(self) -> tuple[str, ...]:
        return self.VOICES


class FakeAudioPlayback:
    """Reproducción simulada: no suena nada y el final se dispara a mano."""

    def __init__(self, *, error: PlaybackError | None = None) -> None:
        self._error = error
        self._playing = False
        self._muted = False
        self._on_finished: Callable[[], None] | None = None
        self.played: list[Path] = []
        self.stops = 0

    def play(self, audio_path: Path, on_finished: Callable[[], None]) -> PlaybackError | None:
        if self._error is not None:
            return self._error
        self.played.append(audio_path)
        self._playing = True
        self._on_finished = on_finished
        return None

    def stop(self) -> None:
        self.stops += 1
        self._playing = False
        self._on_finished = None

    def set_muted(self, muted: bool) -> None:
        self._muted = muted

    def is_playing(self) -> bool:
        return self._playing

    @property
    def is_muted(self) -> bool:
        return self._muted

    def finish(self) -> None:
        """Simula que el audio terminó de sonar por sí solo.

        **Grita si no hay nada sonando**, en vez de callarse. Un `finish()` que
        llega antes de que `play()` se haya llamado no tiene a quién avisar; si
        se traga el aviso, el trozo siguiente no se sintetiza nunca y la prueba
        muere en un plazo agotado de cinco segundos **sin causa visible**. Eso
        es lo que le pasó a `test_nothing_is_said_twice` el 23-08-2026, con dos
        ejecuciones de Quality sobre el mismo commit dando resultados distintos
        (#290, ADR-081).

        La trampa es fina: esperar a que se registre la petición de SÍNTESIS no
        garantiza que la REPRODUCCIÓN haya arrancado, y entre las dos hay una
        ventana que la carga de la máquina ensancha. Lo que hay que esperar es
        que crezca `played`.
        """
        if self._on_finished is None:
            raise AssertionError(
                "finish() sin nada sonando: play() todavía no se ha llamado (o ya "
                "hubo un stop()), así que el aviso de final no tiene destinatario "
                "y se perdería en silencio. Espera a que crezca `played` antes de "
                "dar el audio por terminado."
            )
        self._playing = False
        callback, self._on_finished = self._on_finished, None
        callback()
