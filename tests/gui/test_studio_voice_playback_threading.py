"""Regresión: Sirius decía «hablando» y no salía voz.

El defecto observado: en Model Studio, Sirius respondía, la interfaz pasaba al
estado ``HABLANDO`` y por los altavoces no salía nada. Ninguna prueba lo veía
porque ``StudioVoiceUseCase`` se prueba con un reproductor simulado y
``QtMultimedia`` no existe en el runner Linux, así que ``QtAudioPlayback`` no
llegaba a ejecutarse nunca en la validación.

La causa: ``MainWindow._start_speaking`` lanza un ``SpeakWorker`` al
``QThreadPool``, de modo que ``QtAudioPlayback.play()`` llega desde un hilo del
pool. Allí se construía el ``QMediaPlayer``, con un ``QtAudioPlayback`` que vive
en el hilo de la interfaz como padre. Qt rechaza ese parentesco entre hilos y el
reproductor acababa con afinidad a un hilo del pool, que no tiene bucle de
eventos: ``setSource()`` es asíncrono y nunca terminaba de cargar el medio. Y al
acabar el ``QRunnable`` ese hilo volvía al pool, dejando el reproductor atado a
un hilo muerto para el intento siguiente.

Lo que fijan estas pruebas es la garantía que cierra el defecto: **venga de
donde venga la orden, el objeto de Qt se crea y se maneja en el hilo del
adaptador**. Se comprueba sin ``QtMultimedia``, sustituyendo la creación del
reproductor, para que corra en cualquier máquina.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QRunnable, QThreadPool
from pytestqt.qtbot import QtBot

from sirius.adapters.audio import qt_playback
from sirius.adapters.audio.qt_playback import QtAudioPlayback
from sirius.ports.audio_playback import PlaybackError, PlaybackErrorKind


class _FakePlayer:
    """Lo justo que ``_apply_play`` le pide a un ``QMediaPlayer``."""

    def __init__(self) -> None:
        self.sources: list[str] = []
        self.play_calls = 0
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1

    def setSource(self, url: Any) -> None:  # nombre impuesto por la API de Qt
        self.sources.append(url.toLocalFile())

    def play(self) -> None:
        self.play_calls += 1


class _RecordingPlayback(QtAudioPlayback):
    """Anota en qué hilo se construye y se maneja el reproductor."""

    def __init__(self) -> None:
        super().__init__()
        self.player = _FakePlayer()
        self.threads: list[int] = []

    def _ensure_player(self) -> Any:
        self.threads.append(threading.get_ident())
        return self.player


class _PlayFromWorker(QRunnable):
    """Pide hablar exactamente como lo hace ``SpeakWorker``."""

    def __init__(self, playback: QtAudioPlayback, audio_path: Path) -> None:
        super().__init__()
        self._playback = playback
        self._audio_path = audio_path
        self.worker_thread: int | None = None
        self.outcome: PlaybackError | None = None
        self.done = threading.Event()

    def run(self) -> None:
        self.worker_thread = threading.get_ident()
        try:
            self.outcome = self._playback.play(self._audio_path, lambda: None)
        finally:
            self.done.set()


@pytest.fixture
def audio_file(tmp_path: Path) -> Path:
    destination = tmp_path / "sirius-voz-1.wav"
    destination.write_bytes(b"RIFF....WAVE")
    return destination


@pytest.fixture
def with_multimedia(monkeypatch: pytest.MonkeyPatch) -> None:
    """El runner Linux no trae QtMultimedia; aquí no hace falta que lo traiga.

    Lo que se prueba es en qué hilo se maneja el reproductor, no el reproductor.
    """
    monkeypatch.setattr(qt_playback, "_multimedia_is_available", lambda: True)


@pytest.mark.usefixtures("with_multimedia")
def test_playing_from_a_worker_thread_touches_qt_on_the_adapter_thread(
    qtbot: QtBot,
    audio_file: Path,
) -> None:
    playback = _RecordingPlayback()
    interface_thread = threading.get_ident()

    task = _PlayFromWorker(playback, audio_file)
    QThreadPool.globalInstance().start(task)
    assert task.done.wait(timeout=5.0), "el trabajador no terminó"

    # El trabajo de Qt viaja por la cola de eventos, así que hay que dejarla
    # correr: es justo el bucle de eventos que al reproductor le faltaba.
    qtbot.waitUntil(lambda: playback.player.play_calls == 1, timeout=5000)

    assert task.outcome is None
    assert task.worker_thread is not None
    assert task.worker_thread != interface_thread, "el trabajador corrió en el hilo de la interfaz"
    assert playback.threads == [interface_thread], (
        "el reproductor se creó en el hilo del pool, que no tiene bucle de eventos"
    )
    assert playback.player.sources == [str(audio_file)]


@pytest.mark.usefixtures("with_multimedia")
def test_playing_from_the_interface_thread_stays_immediate(
    qtbot: QtBot,
    audio_file: Path,
) -> None:
    """Desde el hilo de la interfaz la orden sigue siendo síncrona.

    ``AutoConnection`` entrega directo cuando ya se está en el hilo correcto, de
    modo que arreglar el caso del pool no vuelve asíncrono lo que no lo era.
    """
    del qtbot
    playback = _RecordingPlayback()

    assert playback.play(audio_file, lambda: None) is None

    assert playback.player.play_calls == 1
    assert playback.threads == [threading.get_ident()]


@pytest.mark.usefixtures("with_multimedia")
def test_stopping_before_the_queued_order_runs_cancels_the_playback(
    qtbot: QtBot,
    audio_file: Path,
) -> None:
    """Un ``stop()`` que adelanta a un ``play()`` encolado no deja voz suelta."""
    playback = _RecordingPlayback()

    task = _PlayFromWorker(playback, audio_file)
    QThreadPool.globalInstance().start(task)
    assert task.done.wait(timeout=5.0), "el trabajador no terminó"

    # Todavía no se ha corrido el bucle de eventos: la orden sigue en la cola.
    playback.stop()
    qtbot.wait(50)

    assert playback.player.play_calls == 0


def test_playing_without_multimedia_reports_no_device(
    monkeypatch: pytest.MonkeyPatch,
    audio_file: Path,
) -> None:
    monkeypatch.setattr(qt_playback, "_multimedia_is_available", lambda: False)
    playback = _RecordingPlayback()

    outcome = playback.play(audio_file, lambda: None)

    assert isinstance(outcome, PlaybackError)
    assert outcome.kind is PlaybackErrorKind.NO_DEVICE


def test_playing_a_missing_file_reports_invalid_audio(tmp_path: Path) -> None:
    playback = _RecordingPlayback()

    outcome = playback.play(tmp_path / "no-existe.wav", lambda: None)

    assert isinstance(outcome, PlaybackError)
    assert outcome.kind is PlaybackErrorKind.INVALID_AUDIO
