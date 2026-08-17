"""El reproductor real, y en qué hilo hace su trabajo.

Esta es la prueba que faltaba. La voz se sintetiza en el ``QThreadPool`` porque
llama a la red, y el reproductor construía sus objetos de Qt ahí mismo. Qt se
niega a emparentar objetos entre hilos —*«Cannot create children for a parent
that is in a different thread»*—, así que el audio se descodificaba y no llegaba
a los altavoces: **sin sonido y sin ningún error**, que es justo lo que se ve
desde fuera como «no funciona» sin pista ninguna. Se descubrió en la primera
prueba real en Windows, no aquí, porque aquí no había nada que lo mirase.

No hace falta tarjeta de sonido para comprobarlo: lo que se afirma es en qué
hilo se ejecuta cada cosa. Solo las dos últimas necesitan QtMultimedia de verdad
y se saltan solas donde no está —el runner de Quality no lo trae (MS-A02)—.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QRunnable, QThread, QThreadPool
from pytestqt.qtbot import QtBot

from sirius.adapters.audio import qt_playback
from sirius.adapters.audio.qt_playback import QtAudioPlayback
from sirius.ports.audio_playback import PlaybackErrorKind

pytestmark = pytest.mark.gui

requires_multimedia = pytest.mark.skipif(
    not qt_playback.multimedia_is_available(),
    reason="este sistema no trae QtMultimedia; el runner de Quality tampoco (MS-A02)",
)
"""Se pregunta una sola vez, al recoger las pruebas, y sin importar nada de Qt
a nivel de módulo: un ``ImportError`` aquí tumbaría la recolección entera."""


class _SpyPlayer:
    """Un reproductor de mentira que solo anota en qué hilo se le habla.

    Anota ``True``/``False``, no el ``QThread``: guardarlo y compararlo después
    hace que, al fallar, pytest intente describir un hilo del ``QThreadPool``
    que ya no existe, y el proceso se cae con un fallo de segmento en vez de
    dar un rojo legible. La comparación se hace aquí, mientras el hilo vive.
    """

    def __init__(self, owner_thread: QThread) -> None:
        self._owner_thread = owner_thread
        self.sources: list[str] = []
        self.plays = 0
        self.stops = 0
        self.played_in_owner_thread: list[bool] = []

    def stop(self) -> None:
        self.stops += 1

    def setSource(self, url: Any) -> None:  # la firma es la de Qt, no la nuestra
        self.sources.append(url.toLocalFile())

    def play(self) -> None:
        self.plays += 1
        self.played_in_owner_thread.append(QThread.currentThread() is self._owner_thread)


class _PlaybackWithSpy(QtAudioPlayback):
    """El reproductor real con un ``QMediaPlayer`` de mentira dentro.

    Se sustituye solo la creación del reproductor: el reparto de hilos, las
    señales y el orden de las órdenes son los de producción.
    """

    def __init__(self, player: _SpyPlayer) -> None:
        super().__init__()
        self.spy = player

    def _ensure_player(self) -> Any:
        return self.spy


class _CallFromPool(QRunnable):
    """Ejecuta algo en un hilo del ``QThreadPool``, como hace ``SpeakWorker``."""

    def __init__(self, action: Any, owner_thread: QThread) -> None:
        super().__init__()
        self._action = action
        self._owner_thread = owner_thread
        self.left_the_owner_thread = False

    def run(self) -> None:
        self.left_the_owner_thread = QThread.currentThread() is not self._owner_thread
        self._action()


def _audio_file(tmp_path: Path) -> Path:
    audio = tmp_path / "voz.wav"
    audio.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
    return audio


def _run_in_pool(action: Any, owner_thread: QThread) -> bool:
    """Ejecuta ``action`` fuera del hilo principal y dice si de verdad salió."""
    task = _CallFromPool(action, owner_thread)
    pool = QThreadPool()
    pool.start(task)
    assert pool.waitForDone(5_000), "el hilo de fondo no terminó"
    return task.left_the_owner_thread


@pytest.fixture
def multimedia_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Finge que el sistema tiene audio, para no depender de la máquina."""
    monkeypatch.setattr(qt_playback, "multimedia_is_available", lambda: True)


def test_qt_work_happens_in_the_owner_thread_not_in_the_caller(
    qtbot: QtBot, tmp_path: Path, multimedia_available: None
) -> None:
    """La regresión concreta: pedir voz desde un hilo de fondo sí suena."""
    owner_thread = QThread.currentThread()
    playback = _PlaybackWithSpy(_SpyPlayer(owner_thread))
    audio = _audio_file(tmp_path)
    errors: list[object] = []

    left = _run_in_pool(lambda: errors.append(playback.play(audio, lambda: None)), owner_thread)

    assert errors == [None], "reproducir no debía dar error"
    assert left, "la prueba no llegó a salir del hilo principal"

    qtbot.waitUntil(lambda: playback.spy.plays == 1, timeout=2_000)
    assert playback.spy.played_in_owner_thread == [True], (
        "el trabajo de Qt se hizo en el hilo de fondo: así no suena nada"
    )
    assert playback.spy.sources == [str(audio)]


def test_stopping_and_then_playing_keeps_the_new_audio(
    qtbot: QtBot, tmp_path: Path, multimedia_available: None
) -> None:
    """Es la secuencia que usa la voz al encadenar dos respuestas.

    El aviso de «terminado» borra el temporal. Si pararlo contase como final,
    borraría el archivo del audio siguiente antes de que llegue a sonar.
    """
    playback = _PlaybackWithSpy(_SpyPlayer(QThread.currentThread()))
    audio = _audio_file(tmp_path)
    finished: list[None] = []

    def _order() -> None:
        playback.stop()
        playback.play(audio, lambda: finished.append(None))

    _run_in_pool(_order, QThread.currentThread())

    qtbot.waitUntil(lambda: playback.spy.plays == 1, timeout=2_000)
    assert finished == [], "parar la anterior no puede anunciar un final"
    assert audio.exists()


def test_missing_audio_is_reported_without_touching_qt(
    qtbot: QtBot, tmp_path: Path, multimedia_available: None
) -> None:
    playback = _PlaybackWithSpy(_SpyPlayer(QThread.currentThread()))

    error = playback.play(tmp_path / "no-existe.wav", lambda: None)

    assert error is not None
    assert error.kind is PlaybackErrorKind.INVALID_AUDIO
    qtbot.wait(50)
    assert playback.spy.plays == 0


def test_a_system_without_audio_is_reported_instead_of_failing(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sin soporte de audio se responde, no se revienta: el chat escrito sigue."""
    monkeypatch.setattr(qt_playback, "multimedia_is_available", lambda: False)
    playback = _PlaybackWithSpy(_SpyPlayer(QThread.currentThread()))

    error = playback.play(_audio_file(tmp_path), lambda: None)

    assert error is not None
    assert error.kind is PlaybackErrorKind.NO_DEVICE
    qtbot.wait(50)
    assert playback.spy.plays == 0


@requires_multimedia
def test_only_the_end_of_the_audio_announces_the_end(
    qtbot: QtBot, tmp_path: Path, multimedia_available: None
) -> None:
    """Cargar o parar no son finales. Solo terminar de sonar lo es."""
    from PySide6.QtMultimedia import QMediaPlayer

    media = QMediaPlayer.MediaStatus
    playback = _PlaybackWithSpy(_SpyPlayer(QThread.currentThread()))
    finished: list[None] = []

    playback.play(_audio_file(tmp_path), lambda: finished.append(None))
    qtbot.waitUntil(lambda: playback.spy.plays == 1, timeout=2_000)

    for status in (media.LoadingMedia, media.LoadedMedia, media.BufferedMedia):
        playback._on_media_status_changed(status)
    assert finished == []

    playback._on_media_status_changed(media.EndOfMedia)
    assert finished == [None]

    # Y no se repite: el temporal ya se borró con el primer aviso.
    playback._on_media_status_changed(media.EndOfMedia)
    assert finished == [None]


@requires_multimedia
def test_unreadable_audio_also_frees_the_temporary_file(
    qtbot: QtBot, tmp_path: Path, multimedia_available: None
) -> None:
    """Un audio ilegible no puede dejar el temporal olvidado en el disco."""
    from PySide6.QtMultimedia import QMediaPlayer

    media = QMediaPlayer.MediaStatus
    playback = _PlaybackWithSpy(_SpyPlayer(QThread.currentThread()))
    finished: list[None] = []

    playback.play(_audio_file(tmp_path), lambda: finished.append(None))
    qtbot.waitUntil(lambda: playback.spy.plays == 1, timeout=2_000)

    playback._on_media_status_changed(media.InvalidMedia)

    assert finished == [None]


def test_muting_before_there_is_a_player_is_remembered(
    qtbot: QtBot, tmp_path: Path, multimedia_available: None
) -> None:
    """Silenciar antes de la primera respuesta no puede perderse."""
    playback = QtAudioPlayback()

    playback.set_muted(True)
    qtbot.wait(50)

    assert playback.is_muted
    assert not playback.is_playing()
