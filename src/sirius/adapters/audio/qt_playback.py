"""Reproducción de audio real con QtMultimedia.

Mismo cuidado que en la captura: **QtMultimedia se importa dentro de las
funciones**, porque el runner Linux de Quality no trae ``libpulse`` y un import
a nivel de módulo dejaría la validación en rojo sin que fallara nada de verdad
(hallazgo MS-A02).

Un fallo de altavoces no puede llevarse por delante la conversación escrita:
todo se traduce a un error tipado y quien llama decide qué contar.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QUrl

from sirius.infrastructure.logging import get_logger
from sirius.ports.audio_playback import PlaybackError, PlaybackErrorKind

if TYPE_CHECKING:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

_logger = get_logger(__name__)


class QtAudioPlayback(QObject):
    """Reproduce un WAV ya generado, con detener y silenciar idempotentes."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player: QMediaPlayer | None = None
        self._output: QAudioOutput | None = None
        self._on_finished: Callable[[], None] | None = None
        self._muted = False

    def play(self, audio_path: Path, on_finished: Callable[[], None]) -> PlaybackError | None:
        if not audio_path.exists():
            return PlaybackError(PlaybackErrorKind.INVALID_AUDIO, "el audio ya no está")

        player = self._ensure_player()
        if player is None:
            return PlaybackError(
                PlaybackErrorKind.NO_DEVICE, "el sistema no tiene soporte de audio"
            )

        # Una reproducción nueva sustituye a la anterior: nunca dos voces.
        player.stop()
        self._on_finished = on_finished
        player.setSource(QUrl.fromLocalFile(str(audio_path)))
        player.play()
        return None

    def stop(self) -> None:
        """Detiene la reproducción. Idempotente y sin avisar del final.

        Quien detiene ya sabe que ha detenido: llamar a ``on_finished`` aquí
        haría creer que el audio terminó de sonar solo.
        """
        self._on_finished = None
        if self._player is not None:
            self._player.stop()

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        if self._output is not None:
            self._output.setMuted(muted)

    def is_playing(self) -> bool:
        if self._player is None:
            return False
        from PySide6.QtMultimedia import QMediaPlayer as _QMediaPlayer

        return self._player.playbackState() == _QMediaPlayer.PlaybackState.PlayingState

    @property
    def is_muted(self) -> bool:
        return self._muted

    # --- Interior --------------------------------------------------------

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
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        return self._player

    def _on_playback_state_changed(self, state: Any) -> None:
        from PySide6.QtMultimedia import QMediaPlayer as _QMediaPlayer

        if state != _QMediaPlayer.PlaybackState.StoppedState:
            return
        callback, self._on_finished = self._on_finished, None
        if callback is not None:
            callback()
