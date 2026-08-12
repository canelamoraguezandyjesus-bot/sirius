"""El termómetro tiene que medir bien, o es peor que no tenerlo.

Un diagnóstico que dice «todo correcto» sobre un archivo estropeado manda a
buscar el fallo al sitio equivocado, que es exactamente el tiempo que esta
herramienta existe para ahorrar.
"""

from __future__ import annotations

import wave
from pathlib import Path

from sirius.voice_doctor import comprobar_archivo, comprobar_sistema, comprobar_version

_FRAME_RATE = 24_000


def _wav(destination: Path, seconds: float = 0.5) -> Path:
    with wave.open(str(destination), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(_FRAME_RATE)
        handle.writeframes(b"\x00\x00" * int(_FRAME_RATE * seconds))
    return destination


def test_this_tree_reports_that_it_has_the_fixes() -> None:
    """Si esto falla, el diagnóstico está mirando lo que no es.

    Es la comprobación más importante de todas: su única razón de existir es
    responder «¿estás ejecutando el código arreglado?» sin depender de git.
    """
    paso = comprobar_version()

    assert paso.correcto, paso.detalle


def test_a_healthy_wav_is_reported_as_healthy(tmp_path: Path) -> None:
    paso = comprobar_archivo(_wav(tmp_path / "voz.wav"))

    assert paso.correcto
    assert "24000 Hz" in paso.detalle


def test_a_header_that_does_not_match_the_disk_is_caught(tmp_path: Path) -> None:
    """El fallo real de Windows: encabezado enorme, archivo pequeño.

    Es lo que hacía que el descodificador tirase los paquetes y no sonara nada.
    """
    audio = _wav(tmp_path / "voz.wav")
    datos = bytearray(audio.read_bytes())
    datos[40:44] = (0xFFFFFF).to_bytes(4, "little")
    audio.write_bytes(bytes(datos))

    paso = comprobar_archivo(audio)

    assert not paso.correcto
    assert "descarta el sonido" in paso.detalle


def test_something_that_is_not_audio_is_caught(tmp_path: Path) -> None:
    roto = tmp_path / "roto.wav"
    roto.write_bytes(b"esto no es un wav")

    paso = comprobar_archivo(roto)

    assert not paso.correcto


def test_the_report_says_which_player_this_machine_will_use() -> None:
    paso = comprobar_sistema()

    assert paso.correcto
    assert "reproductor" in paso.detalle


def test_a_failing_step_prints_the_word_that_is_looked_for(tmp_path: Path) -> None:
    """El resumen se lee de un vistazo: FALLA tiene que saltar a la vista."""
    roto = tmp_path / "roto.wav"
    roto.write_bytes(b"nada")

    assert "FALLA" in comprobar_archivo(roto).linea()
    assert "OK" in comprobar_archivo(_wav(tmp_path / "voz.wav")).linea()
