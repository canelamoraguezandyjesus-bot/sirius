"""Reproducción de audio real con QtMultimedia.

Mismo cuidado que en la captura: **QtMultimedia se importa dentro de las
funciones**, porque el runner Linux de Quality no trae ``libpulse`` y un import
a nivel de módulo dejaría la validación en rojo sin que fallara nada de verdad
(hallazgo MS-A02).

Un fallo de altavoces no puede llevarse por delante la conversación escrita:
todo se traduce a un error tipado y quien llama decide qué contar.

**Todo lo que toca a Qt corre en el hilo de este objeto, nunca en el de quien
llama.** ``StudioVoiceUseCase.speak()`` se ejecuta en un ``SpeakWorker`` del
``QThreadPool``, así que ``play()`` llega desde un hilo del pool mientras este
adaptador vive en el hilo de la interfaz. Construir ahí el ``QMediaPlayer``
dejaba el reproductor con afinidad a un hilo sin bucle de eventos: ``setSource``
es asíncrono y nunca llegaba a cargar el medio, de modo que Sirius decía
«hablando» y no sonaba nada. Y al terminar el ``QRunnable`` el hilo volvía al
pool, dejando el reproductor atado a un hilo muerto para el siguiente intento.
Por eso las órdenes se encolan con ``QMetaObject.invokeMethod``: en
``AutoConnection`` van directas si ya estamos en el hilo correcto, y por la cola
de eventos si no.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QMetaObject, QObject, Qt, QUrl, Slot

from sirius.infrastructure.logging import get_logger
from sirius.ports.audio_playback import PlaybackError, PlaybackErrorKind

if TYPE_CHECKING:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

_logger = get_logger(__name__)


def _multimedia_is_available() -> bool:
    """¿Trae este sistema QtMultimedia? Se responde sin tocar el dispositivo."""
    try:
        import PySide6.QtMultimedia  # noqa: F401
    except ImportError:
        _logger.warning("QtMultimedia no está disponible en este sistema")
        return False
    return True


class QtAudioPlayback(QObject):
    """Reproduce un WAV ya generado, con detener y silenciar idempotentes."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player: QMediaPlayer | None = None
        self._output: QAudioOutput | None = None
        self._on_finished: Callable[[], None] | None = None
        self._muted = False
        self._playing = False
        # Protege lo que se lee y escribe desde dos hilos: el del pool que pide
        # hablar y el de la interfaz que ejecuta la orden.
        self._lock = threading.Lock()
        self._pending_source: Path | None = None

    def play(self, audio_path: Path, on_finished: Callable[[], None]) -> PlaybackError | None:
        """Empieza a reproducir. Se puede llamar desde cualquier hilo.

        Lo que se puede responder al instante -que el archivo siga ahí y que el
        sistema tenga audio- se comprueba aquí, para no romper el contrato
        síncrono del puerto. Lo que toca a Qt se encola.
        """
        if not audio_path.exists():
            return PlaybackError(PlaybackErrorKind.INVALID_AUDIO, "el audio ya no está")

        if not _multimedia_is_available():
            return PlaybackError(
                PlaybackErrorKind.NO_DEVICE, "el sistema no tiene soporte de audio"
            )

        with self._lock:
            self._pending_source = audio_path
            self._on_finished = on_finished

        self._invoke("_apply_play")
        return None

    def stop(self) -> None:
        """Detiene la reproducción. Idempotente y sin avisar del final.

        Quien detiene ya sabe que ha detenido: llamar a ``on_finished`` aquí
        haría creer que el audio terminó de sonar solo. Olvidar la devolución
        de llamada se hace YA, sin esperar a la cola, para que un cambio de
        estado que llegue por el camino no la dispare.
        """
        with self._lock:
            self._on_finished = None
            self._pending_source = None
        self._invoke("_apply_stop")

    def set_muted(self, muted: bool) -> None:
        # El estado que consulta ``is_muted`` se actualiza ya; lo que toca al
        # dispositivo se encola.
        self._muted = muted
        self._invoke("_apply_muted")

    def is_playing(self) -> bool:
        """Se responde con el último estado observado, no preguntando a Qt.

        ``QMediaPlayer`` no se consulta desde otro hilo: quien pregunta suele
        ser la interfaz, pero ``StudioVoiceUseCase.is_speaking`` es accesible
        desde donde sea.
        """
        return self._playing

    @property
    def is_muted(self) -> bool:
        return self._muted

    # --- Interior --------------------------------------------------------

    def _invoke(self, slot_name: str) -> None:
        """Ejecuta el slot en el hilo de este objeto.

        ``AutoConnection`` es directa cuando ya estamos en ese hilo, así que
        para la interfaz nada cambia; solo se encola cuando la orden viene del
        ``QThreadPool``.
        """
        QMetaObject.invokeMethod(self, slot_name, Qt.ConnectionType.AutoConnection)

    @Slot()
    def _apply_play(self) -> None:
        with self._lock:
            source = self._pending_source
            self._pending_source = None
        if source is None:
            # Un ``stop()`` adelantó a esta orden por la cola: no hay nada que
            # reproducir y no reproducirlo es exactamente lo pedido.
            return

        player = self._ensure_player()
        if player is None:
            return

        # Una reproducción nueva sustituye a la anterior: nunca dos voces.
        player.stop()
        player.setSource(QUrl.fromLocalFile(str(source)))
        player.play()

    @Slot()
    def _apply_stop(self) -> None:
        if self._player is not None:
            self._player.stop()

    @Slot()
    def _apply_muted(self) -> None:
        if self._output is not None:
            self._output.setMuted(self._muted)

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
        self._player.errorOccurred.connect(self._on_error)
        return self._player

    def _on_playback_state_changed(self, state: Any) -> None:
        from PySide6.QtMultimedia import QMediaPlayer as _QMediaPlayer

        self._playing = state == _QMediaPlayer.PlaybackState.PlayingState
        if state != _QMediaPlayer.PlaybackState.StoppedState:
            return
        with self._lock:
            callback, self._on_finished = self._on_finished, None
        if callback is not None:
            callback()

    def _on_error(self, error: Any, error_string: str) -> None:
        """Deja constancia de por qué Qt no ha sonado.

        Sin esto un fallo del reproductor era mudo en todos los sentidos: no
        salía voz y tampoco quedaba rastro de la causa. No se traduce a un
        ``PlaybackError`` porque ``play()`` ya ha respondido; el estado pasará a
        ``StoppedState`` y el temporal se limpiará por el camino de siempre.
        """
        del error
        _logger.warning("la reproducción de voz ha fallado: %s", error_string)
