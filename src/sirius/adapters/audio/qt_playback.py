"""Reproducción de audio real con QtMultimedia.

Mismo cuidado que en la captura: **QtMultimedia se importa dentro de las
funciones**, porque el runner Linux de Quality no trae ``libpulse`` y un import
a nivel de módulo dejaría la validación en rojo sin que fallara nada de verdad
(hallazgo MS-A02).

**Todo el trabajo de Qt ocurre en el hilo donde vive este objeto**, aunque se
pida reproducir desde otro. La síntesis tarda y llama a la red, así que corre
en el ``QThreadPool``; si ese hilo construyera el reproductor, Qt se negaría
—*«Cannot create children for a parent that is in a different thread»*— y el
audio se decodificaría sin llegar nunca a los altavoces: sin sonido y sin
error, que es la peor combinación posible. Las órdenes viajan por señales
propias con conexión automática: emitidas desde otro hilo se encolan en el de
la interfaz, y emitidas desde el de la interfaz se ejecutan al momento, así que
el orden entre detener y reproducir se conserva siempre.

Un fallo de altavoces no puede llevarse por delante la conversación escrita:
todo se traduce a un error tipado y quien llama decide qué contar.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QUrl, Signal

from sirius.infrastructure.logging import get_logger
from sirius.ports.audio_playback import PlaybackError, PlaybackErrorKind

if TYPE_CHECKING:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

_logger = get_logger(__name__)


def multimedia_is_available() -> bool:
    """Si este sistema puede reproducir audio con Qt.

    Solo importa un módulo, así que se puede llamar desde cualquier hilo: es
    lo único que permite responder ``NO_DEVICE`` en el acto y dejar el resto
    del trabajo para el hilo dueño del reproductor.
    """
    try:
        import PySide6.QtMultimedia  # noqa: F401
    except ImportError:
        _logger.warning("QtMultimedia no está disponible en este sistema")
        return False
    return True


class QtAudioPlayback(QObject):
    """Reproduce un WAV ya generado, con detener y silenciar idempotentes."""

    _play_requested = Signal(str)
    _stop_requested = Signal()
    _mute_requested = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player: QMediaPlayer | None = None
        self._output: QAudioOutput | None = None
        self._on_finished: Callable[[], None] | None = None
        self._muted = False
        # Conexión automática: directa dentro del propio hilo, encolada desde
        # fuera. Es lo que traslada el trabajo de Qt al hilo correcto.
        self._play_requested.connect(self._start_playback)
        self._stop_requested.connect(self._stop_playback)
        self._mute_requested.connect(self._apply_mute)

    # --- Puerto ----------------------------------------------------------

    def play(self, audio_path: Path, on_finished: Callable[[], None]) -> PlaybackError | None:
        """Pide reproducir. Lo que se puede comprobar ya, se comprueba ya.

        Que el archivo exista y que el sistema tenga audio se responden en el
        acto y sin tocar Qt. El resto se ejecuta en el hilo dueño del
        reproductor, así que esta llamada vuelve antes de que empiece a sonar.
        """
        if not audio_path.exists():
            return PlaybackError(PlaybackErrorKind.INVALID_AUDIO, "el audio ya no está")
        if not multimedia_is_available():
            return PlaybackError(
                PlaybackErrorKind.NO_DEVICE, "el sistema no tiene soporte de audio"
            )

        self._on_finished = on_finished
        self._play_requested.emit(str(audio_path))
        return None

    def stop(self) -> None:
        """Detiene la reproducción. Idempotente y sin avisar del final.

        Quien detiene ya sabe que ha detenido: llamar a ``on_finished`` aquí
        haría creer que el audio terminó de sonar solo.
        """
        self._on_finished = None
        self._stop_requested.emit()

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        self._mute_requested.emit(muted)

    def is_playing(self) -> bool:
        if self._player is None:
            return False
        from PySide6.QtMultimedia import QMediaPlayer as _QMediaPlayer

        return self._player.playbackState() == _QMediaPlayer.PlaybackState.PlayingState

    @property
    def is_muted(self) -> bool:
        return self._muted

    # --- Interior: siempre en el hilo dueño del objeto -------------------

    def _start_playback(self, audio_path: str) -> None:
        player = self._ensure_player()
        if player is None:
            # Sin reproductor no llegará ningún final: se avisa ahora para que
            # el temporal no se quede olvidado en el disco.
            self._announce_finished()
            return

        player.stop()
        player.setSource(QUrl.fromLocalFile(audio_path))
        player.play()

    def _stop_playback(self) -> None:
        if self._player is not None:
            self._player.stop()

    def _apply_mute(self, muted: bool) -> None:
        if self._output is not None:
            self._output.setMuted(muted)

    def _ensure_player(self) -> Any:
        if self._player is not None:
            return self._player
        try:
            from PySide6.QtMultimedia import QAudioOutput as _QAudioOutput
            from PySide6.QtMultimedia import QMediaPlayer as _QMediaPlayer
        except ImportError:
            _logger.warning("QtMultimedia no está disponible en este sistema")
            return None

        self._output = _QAudioOutput(self)
        self._output.setMuted(self._muted)
        self._player = _QMediaPlayer(self)
        self._player.setAudioOutput(self._output)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        return self._player

    def _on_media_status_changed(self, status: Any) -> None:
        """El final se detecta por el estado del medio, no por el del reproductor.

        ``StoppedState`` también ocurre al cambiar de audio, y avisar ahí haría
        que el temporal del audio siguiente se borrara antes de sonar. Solo
        hay dos finales de verdad: el audio terminó, o resultó ilegible.
        """
        from PySide6.QtMultimedia import QMediaPlayer as _QMediaPlayer

        if status == _QMediaPlayer.MediaStatus.InvalidMedia:
            _logger.warning("el audio sintetizado no se ha podido reproducir")
        elif status != _QMediaPlayer.MediaStatus.EndOfMedia:
            return
        self._announce_finished()

    def _announce_finished(self) -> None:
        callback, self._on_finished = self._on_finished, None
        if callback is not None:
            callback()
