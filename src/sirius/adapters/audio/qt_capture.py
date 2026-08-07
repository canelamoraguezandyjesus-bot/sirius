"""Captura de micrófono real con QtMultimedia.

**QtMultimedia se importa dentro de las funciones, nunca al principio del
archivo.** No es manía: el runner Linux donde corre Quality no trae
``libpulse``, así que un import a nivel de módulo rompería la recolección de
``pytest`` —antes de ejecutar una sola prueba y aunque todas usen adaptadores
simulados— y dejaría la validación en rojo (hallazgo MS-A02). Con el import
perezoso, este archivo se puede importar en cualquier sitio y solo toca el
sistema de audio cuando de verdad se va a grabar.

Se graba PCM en crudo y se envuelve en WAV al terminar, en vez de usar el
grabador de alto nivel de Qt: así el formato es siempre el mismo, sin depender
de qué códecs tenga instalados la máquina, y los topes de duración y tamaño se
aplican sobre los bytes reales según entran.
"""

from __future__ import annotations

import wave
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QTimer

from sirius.infrastructure.logging import get_logger
from sirius.ports.audio_capture import (
    AudioCaptureError,
    AudioCaptureErrorKind,
    AudioCaptureResult,
    CaptureLimits,
)

if TYPE_CHECKING:
    from PySide6.QtMultimedia import QAudioSource

_logger = get_logger(__name__)

SAMPLE_RATE_HZ = 16_000
"""16 kHz mono: es lo que piden los modelos de transcripción y ocupa poco.

Grabar a calidad de música no mejora el reconocimiento y multiplica el tamaño
del temporal, que además hay que subir por red.
"""

CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2

TEMPORARY_PREFIX = "sirius-captura-"


def _build_format() -> Any:
    from PySide6.QtMultimedia import QAudioFormat

    audio_format = QAudioFormat()
    audio_format.setSampleRate(SAMPLE_RATE_HZ)
    audio_format.setChannelCount(CHANNELS)
    audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    return audio_format


class QtAudioCapture(QObject):
    """Graba el intervalo entre una orden de inicio y una de parada."""

    def __init__(self, temporary_directory: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._directory = temporary_directory
        self._source: QAudioSource | None = None
        self._device: Any = None
        self._buffer = bytearray()
        self._limits = CaptureLimits()
        self._stopped_by_limit = False
        self._counter = 0
        self._limit_timer = QTimer(self)
        self._limit_timer.setSingleShot(True)
        self._limit_timer.timeout.connect(self._on_duration_limit)

    # --- Puerto ----------------------------------------------------------

    def start(self, limits: CaptureLimits) -> AudioCaptureError | None:
        if self.is_capturing():
            return AudioCaptureError(
                AudioCaptureErrorKind.DEVICE_BUSY, "ya hay una captura en curso"
            )

        try:
            from PySide6.QtMultimedia import QAudioSource as _QAudioSource
            from PySide6.QtMultimedia import QMediaDevices
        except ImportError:
            # Sin soporte de audio en el sistema, el chat escrito sigue igual.
            _logger.warning("QtMultimedia no está disponible en este sistema")
            return AudioCaptureError(
                AudioCaptureErrorKind.NO_DEVICE, "el sistema no tiene soporte de audio"
            )

        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            return AudioCaptureError(AudioCaptureErrorKind.NO_DEVICE, "no hay micrófono disponible")

        audio_format = _build_format()
        if not device.isFormatSupported(audio_format):
            audio_format = device.preferredFormat()

        self._buffer = bytearray()
        self._stopped_by_limit = False
        self._limits = limits
        self._source = _QAudioSource(device, audio_format, self)
        self._device = self._source.start()
        if self._device is None:
            self._release()
            return AudioCaptureError(
                AudioCaptureErrorKind.PERMISSION, "no se pudo abrir el micrófono"
            )

        self._device.readyRead.connect(self._on_ready_read)
        self._limit_timer.start(int(limits.maximum_seconds * 1000))
        return None

    def stop(self) -> AudioCaptureResult | AudioCaptureError:
        if not self.is_capturing():
            return AudioCaptureError(
                AudioCaptureErrorKind.NOT_CAPTURING, "no había captura en curso"
            )
        self._drain()
        captured = bytes(self._buffer)
        stopped_by_limit = self._stopped_by_limit
        self._release()

        if not captured:
            return AudioCaptureError(AudioCaptureErrorKind.EMPTY, "no se captó audio")

        try:
            destination = self._write_wav(captured)
        except OSError:
            _logger.warning("no se pudo escribir el audio capturado")
            return AudioCaptureError(AudioCaptureErrorKind.UNKNOWN, "no se pudo guardar el audio")

        return AudioCaptureResult(
            audio_path=destination,
            duration_seconds=len(captured) / (SAMPLE_RATE_HZ * SAMPLE_WIDTH_BYTES * CHANNELS),
            size_bytes=destination.stat().st_size,
            stopped_by_limit=stopped_by_limit,
        )

    def cancel(self) -> None:
        """Aborta y no deja nada escrito. Idempotente."""
        if self._source is not None:
            self._drain()
        self._buffer = bytearray()
        self._release()

    def is_capturing(self) -> bool:
        return self._source is not None

    def discard(self, audio_path: Path) -> None:
        audio_path.unlink(missing_ok=True)

    # --- Limpieza --------------------------------------------------------

    def cleanup_orphans(self) -> int:
        """Borra temporales que quedaron de un cierre forzado. Devuelve cuántos.

        Se llama al arrancar: un corte de luz en mitad de una grabación no
        puede dejar la voz del usuario tirada en el disco.
        """
        if not self._directory.exists():
            return 0
        removed = 0
        for orphan in self._directory.glob(f"{TEMPORARY_PREFIX}*.wav"):
            orphan.unlink(missing_ok=True)
            removed += 1
        return removed

    # --- Interior --------------------------------------------------------

    def _on_ready_read(self) -> None:
        self._drain()
        if len(self._buffer) >= self._limits.maximum_bytes:
            self._stopped_by_limit = True
            self._limit_timer.stop()
            # No se cierra aquí: parar es decisión de quien llamó, y este
            # objeto no puede saber qué quiere hacer con lo capturado. Se deja
            # de acumular y se marca el motivo.
            del self._buffer[self._limits.maximum_bytes :]

    def _drain(self) -> None:
        if self._device is None or self._stopped_by_limit:
            return
        chunk = self._device.readAll()
        if chunk:
            self._buffer.extend(bytes(chunk.data()))

    def _on_duration_limit(self) -> None:
        self._drain()
        self._stopped_by_limit = True

    def _write_wav(self, pcm: bytes) -> Path:
        self._directory.mkdir(parents=True, exist_ok=True)
        self._counter += 1
        destination = self._directory / f"{TEMPORARY_PREFIX}{self._counter}.wav"
        with wave.open(str(destination), "wb") as handle:
            handle.setnchannels(CHANNELS)
            handle.setsampwidth(SAMPLE_WIDTH_BYTES)
            handle.setframerate(SAMPLE_RATE_HZ)
            handle.writeframes(pcm)
        return destination

    def _release(self) -> None:
        self._limit_timer.stop()
        if self._source is not None:
            self._source.stop()
            self._source.deleteLater()
        self._source = None
        self._device = None
