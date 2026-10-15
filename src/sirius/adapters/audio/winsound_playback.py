"""Reproducción de audio en Windows con el reproductor del propio sistema.

Existe por una razón concreta y vista en la máquina real: el motor multimedia
de Qt en Windows usa FFmpeg y, ante el WAV que devuelve el proveedor de voz,
escupía ``Ignoring maximum wav data size`` y ``Packet corrupt`` y no sacaba
sonido por los altavoces. Descartar el audio sin avisar de nada es el peor
fallo posible: desde fuera se ve como «no funciona» y sin ninguna pista.

``winsound`` es de la biblioteca estándar de Python —no añade ninguna
dependencia— y entrega el WAV al reproductor de Windows, el mismo que suena
cuando el sistema hace *ding*. Ningún descodificador de por medio.

Cumple el mismo puerto que el adaptador de Qt, así que cambiar de uno a otro es
elegir otra línea en la raíz de composición. Como el resto de adaptadores de
audio, ``winsound`` se importa dentro de las funciones: en Linux no existe, y
un import arriba rompería la recolección de las pruebas.

Lo que este camino no da, y se dice claro:

- **No controla el volumen del sistema.** Silenciar aquí es no reproducir.
- **No avisa por sí solo de cuándo termina.** El final se calcula leyendo la
  duración real del archivo, que es exacta porque el WAV se escribe entero
  antes de sonar.
"""

from __future__ import annotations

import sys
import wave
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from sirius.infrastructure.logging import get_logger
from sirius.ports.audio_playback import PlaybackError, PlaybackErrorKind

_logger = get_logger(__name__)

MAXIMUM_SECONDS = 600.0
"""Tope de seguridad para la duración calculada.

Un encabezado estropeado puede declarar horas de audio. Sin tope, el aviso de
final no llegaría nunca y el temporal se quedaría en el disco para siempre.
"""

MINIMUM_SECONDS = 0.2

AUDIO_ILEGIBLE = OSError, wave.Error, EOFError, ZeroDivisionError
"""Todo lo que puede lanzar un WAV que no se deja leer.

``EOFError`` es el de un archivo cortado a medias y **no** es un
``OSError``: sin nombrarlo, un temporal a medio escribir tumbaría la voz
entera en vez de limitarse a sonar mal.
"""


def winsound_is_available() -> bool:
    """Si este sistema es un Windows con ``winsound``. Sin efectos."""
    try:
        import winsound  # noqa: F401
    except ImportError:
        return False
    return True


def play_wav_file(audio_path: str) -> None:
    """Entrega el archivo al reproductor de Windows y vuelve en el acto.

    La comprobación de plataforma no es defensiva de más: es lo que le dice al
    comprobador de tipos que este cuerpo solo existe en Windows. Sin ella,
    ``winsound`` no tiene ninguno de estos nombres fuera de allí y la
    validación se queda en rojo en el runner Linux.
    """
    if sys.platform != "win32":
        raise RuntimeError("winsound solo existe en Windows")
    import winsound

    winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)


def stop_all_sounds() -> None:
    """Corta lo que esté sonando. Idempotente."""
    if sys.platform != "win32":
        return
    import winsound

    winsound.PlaySound(None, winsound.SND_PURGE)


def audio_seconds(audio_path: Path) -> float:
    """Cuánto dura el WAV, según lo que de verdad hay escrito en el archivo.

    Se cruzan dos cuentas: la que declara el encabezado y la que sale del
    tamaño en disco. Se queda con la menor, porque un encabezado puede mentir
    —es justo lo que hacía el WAV del proveedor— y el archivo no.
    """
    try:
        with wave.open(str(audio_path), "rb") as handle:
            frame_rate = handle.getframerate()
            bytes_per_second = frame_rate * handle.getsampwidth() * handle.getnchannels()
            declared = handle.getnframes() / frame_rate if frame_rate else 0.0
        on_disk = audio_path.stat().st_size / bytes_per_second if bytes_per_second else 0.0
    except AUDIO_ILEGIBLE:
        # Un archivo ilegible se sabrá al reproducirlo; aquí solo hace falta un
        # plazo razonable para no dejar el aviso de final colgado.
        return MINIMUM_SECONDS

    candidates = [value for value in (declared, on_disk) if value > 0.0]
    if not candidates:
        return MINIMUM_SECONDS
    return max(MINIMUM_SECONDS, min(min(candidates), MAXIMUM_SECONDS))


class WinsoundAudioPlayback(QObject):
    """Reproduce un WAV con el reproductor de Windows."""

    _play_requested = Signal(str, float)
    _stop_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._muted = False
        self._playing = False
        self._on_finished: Callable[[], None] | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_expected_end)
        # Mismo motivo que en el adaptador de Qt: la síntesis corre en un hilo
        # de fondo y el temporizador tiene que vivir en el hilo de la ventana.
        self._play_requested.connect(self._start_playback)
        self._stop_requested.connect(self._stop_playback)

    # --- Puerto ----------------------------------------------------------

    def play(self, audio_path: Path, on_finished: Callable[[], None]) -> PlaybackError | None:
        if not audio_path.exists():
            return PlaybackError(PlaybackErrorKind.INVALID_AUDIO, "el audio ya no está")
        if not winsound_is_available():
            return PlaybackError(
                PlaybackErrorKind.NO_DEVICE, "este sistema no es Windows con winsound"
            )

        self._on_finished = on_finished
        self._play_requested.emit(str(audio_path), audio_seconds(audio_path))
        return None

    def stop(self) -> None:
        self._on_finished = None
        self._stop_requested.emit()

    def set_muted(self, muted: bool) -> None:
        """Silenciar aquí es no sonar: este camino no toca el volumen del sistema."""
        self._muted = muted
        if muted:
            self._stop_requested.emit()

    def is_playing(self) -> bool:
        return self._playing

    @property
    def is_muted(self) -> bool:
        return self._muted

    # --- Interior: siempre en el hilo dueño del objeto -------------------

    def _start_playback(self, audio_path: str, seconds: float) -> None:
        self._silence()
        if self._muted:
            # No suena, pero el turno termina igual: si no, el temporal se
            # quedaría en el disco y la ventana seguiría diciendo «HABLANDO».
            self._announce_finished()
            return

        try:
            play_wav_file(audio_path)
        except RuntimeError:
            _logger.warning("Windows no ha podido reproducir el audio sintetizado")
            self._announce_finished()
            return

        self._playing = True
        self._timer.start(int(seconds * 1000))

    def _stop_playback(self) -> None:
        self._silence()

    def _silence(self) -> None:
        self._timer.stop()
        if not self._playing:
            return
        self._playing = False
        stop_all_sounds()

    def _on_expected_end(self) -> None:
        self._playing = False
        self._announce_finished()

    def _announce_finished(self) -> None:
        callback, self._on_finished = self._on_finished, None
        if callback is not None:
            callback()
