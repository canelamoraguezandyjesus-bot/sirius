"""El camino de sonido de Windows: el del propio sistema, sin descodificador.

Se prueba en cualquier máquina porque las tres llamadas a ``winsound`` viven
en funciones sueltas del módulo y aquí se sustituyen. Lo que se comprueba es lo
que puede romperse de verdad: en qué hilo ocurre el trabajo, cuánto se cree que
dura el audio, y que el turno termine siempre —suene o no—, porque de ese aviso
depende que se borre el temporal y que la ventana deje de decir «HABLANDO».
"""

from __future__ import annotations

import wave
from collections.abc import Callable
from pathlib import Path

import pytest
from PySide6.QtCore import QRunnable, QThread, QThreadPool
from pytestqt.qtbot import QtBot

from sirius.adapters.audio import winsound_playback
from sirius.adapters.audio.winsound_playback import (
    MINIMUM_SECONDS,
    WinsoundAudioPlayback,
    audio_seconds,
)
from sirius.ports.audio_playback import PlaybackErrorKind

pytestmark = pytest.mark.gui

_FRAME_RATE = 24_000


class _Altavoz:
    """Anota lo que se le pide, y en qué hilo, en vez de sonar."""

    def __init__(self, owner_thread: QThread) -> None:
        self._owner_thread = owner_thread
        self.reproducidos: list[str] = []
        self.purgas = 0
        self.reproducido_en_el_hilo_dueno: list[bool] = []
        self.fallo: Exception | None = None

    def reproducir(self, audio_path: str) -> None:
        if self.fallo is not None:
            raise self.fallo
        self.reproducidos.append(audio_path)
        self.reproducido_en_el_hilo_dueno.append(QThread.currentThread() is self._owner_thread)

    def purgar(self) -> None:
        self.purgas += 1


@pytest.fixture
def altavoz(monkeypatch: pytest.MonkeyPatch) -> _Altavoz:
    espia = _Altavoz(QThread.currentThread())
    monkeypatch.setattr(winsound_playback, "winsound_is_available", lambda: True)
    monkeypatch.setattr(winsound_playback, "play_wav_file", espia.reproducir)
    monkeypatch.setattr(winsound_playback, "stop_all_sounds", espia.purgar)
    return espia


def _wav(destination: Path, seconds: float = 0.5) -> Path:
    with wave.open(str(destination), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(_FRAME_RATE)
        handle.writeframes(b"\x00\x00" * int(_FRAME_RATE * seconds))
    return destination


# --- Cuánto se cree que dura ---------------------------------------------


def test_the_duration_comes_from_the_real_file(tmp_path: Path) -> None:
    assert audio_seconds(_wav(tmp_path / "voz.wav", seconds=1.5)) == pytest.approx(1.5, abs=0.05)


def test_a_lying_header_never_makes_the_audio_longer(tmp_path: Path) -> None:
    """El encabezado del proveedor mentía; el tamaño en disco no puede.

    Si se creyera el encabezado, el aviso de final llegaría tardísimo o nunca,
    y el temporal se quedaría en el disco esperándolo.
    """
    audio = _wav(tmp_path / "voz.wav", seconds=0.5)
    datos = bytearray(audio.read_bytes())
    # Se declara un número de fotogramas absurdo, como hacía el WAV recibido.
    datos[40:44] = (0xFFFFFF).to_bytes(4, "little")
    audio.write_bytes(bytes(datos))

    assert audio_seconds(audio) < 1.0


def test_something_that_is_not_a_wav_gets_the_shortest_wait(tmp_path: Path) -> None:
    roto = tmp_path / "roto.wav"
    roto.write_bytes(b"esto no es un wav")

    assert audio_seconds(roto) == MINIMUM_SECONDS


# --- Dónde ocurre el trabajo ---------------------------------------------


class _DesdeElPool(QRunnable):
    def __init__(self, accion: Callable[[], None]) -> None:
        super().__init__()
        self._accion = accion

    def run(self) -> None:
        self._accion()


def _en_segundo_plano(accion: Callable[[], None]) -> None:
    pool = QThreadPool()
    pool.start(_DesdeElPool(accion))
    assert pool.waitForDone(5_000), "el hilo de fondo no terminó"


def test_playing_from_a_background_thread_still_reaches_the_speakers(
    qtbot: QtBot, tmp_path: Path, altavoz: _Altavoz
) -> None:
    """La misma regresión que en el camino de Qt, vigilada también aquí."""
    reproductor = WinsoundAudioPlayback()
    audio = _wav(tmp_path / "voz.wav")

    def _pedir_voz() -> None:
        reproductor.play(audio, lambda: None)

    _en_segundo_plano(_pedir_voz)

    qtbot.waitUntil(lambda: len(altavoz.reproducidos) == 1, timeout=2_000)
    assert altavoz.reproducido_en_el_hilo_dueno == [True]
    assert altavoz.reproducidos == [str(audio)]


# --- Que el turno termine siempre ----------------------------------------


def test_the_end_of_the_audio_is_announced_when_it_runs_out(
    qtbot: QtBot, tmp_path: Path, altavoz: _Altavoz
) -> None:
    reproductor = WinsoundAudioPlayback()
    terminados: list[None] = []

    reproductor.play(_wav(tmp_path / "voz.wav", seconds=0.3), lambda: terminados.append(None))
    assert reproductor.is_playing()

    qtbot.waitUntil(lambda: terminados == [None], timeout=3_000)
    assert not reproductor.is_playing()


def test_muted_does_not_play_but_still_closes_the_turn(
    qtbot: QtBot, tmp_path: Path, altavoz: _Altavoz
) -> None:
    """Silenciado no puede significar «temporal olvidado y ventana colgada»."""
    reproductor = WinsoundAudioPlayback()
    reproductor.set_muted(True)
    terminados: list[None] = []

    reproductor.play(_wav(tmp_path / "voz.wav"), lambda: terminados.append(None))

    assert altavoz.reproducidos == []
    assert terminados == [None]


def test_stopping_on_purpose_never_announces_an_ending(
    qtbot: QtBot, tmp_path: Path, altavoz: _Altavoz
) -> None:
    reproductor = WinsoundAudioPlayback()
    terminados: list[None] = []
    reproductor.play(_wav(tmp_path / "voz.wav", seconds=2.0), lambda: terminados.append(None))

    reproductor.stop()

    assert altavoz.purgas == 1
    assert not reproductor.is_playing()
    qtbot.wait(100)
    assert terminados == []


def test_a_rejected_file_closes_the_turn_instead_of_hanging(
    qtbot: QtBot, tmp_path: Path, altavoz: _Altavoz
) -> None:
    """Si Windows rechaza el archivo hay que soltarlo, no esperarlo."""
    altavoz.fallo = RuntimeError("formato no admitido")
    reproductor = WinsoundAudioPlayback()
    terminados: list[None] = []

    reproductor.play(_wav(tmp_path / "voz.wav"), lambda: terminados.append(None))

    assert terminados == [None]
    assert not reproductor.is_playing()


def test_missing_audio_is_reported(tmp_path: Path, altavoz: _Altavoz) -> None:
    reproductor = WinsoundAudioPlayback()

    error = reproductor.play(tmp_path / "no-existe.wav", lambda: None)

    assert error is not None
    assert error.kind is PlaybackErrorKind.INVALID_AUDIO


def test_outside_windows_it_says_so_instead_of_failing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(winsound_playback, "winsound_is_available", lambda: False)
    reproductor = WinsoundAudioPlayback()

    error = reproductor.play(_wav(tmp_path / "voz.wav"), lambda: None)

    assert error is not None
    assert error.kind is PlaybackErrorKind.NO_DEVICE
