"""Las marcas tienen que acabar en un archivo, junto al vídeo.

Sirius confirma cada marca con *«Marcado. Ya lo encontrarás luego»*. Durante un
tiempo eso fue mentira: el diario existía como contrato y no había nadie
detrás, así que la marca se decía y se perdía. Estas pruebas son las que
sostienen esa frase.

La otra mitad importa igual: **nada se pierde cuando algo falla**. Si no se
sabe a qué vídeo pertenecen, o no se puede escribir en su carpeta, las marcas
se quedan guardadas en otro sitio en vez de desaparecer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius.adapters.capture.file_journal import (
    ARCHIVO_DIARIO,
    ARCHIVO_EN_CURSO,
    SUFIJO_MARCAS,
    FileCaptureJournal,
    formatear_tiempo,
)


class _RelojFijo:
    def utc_now(self) -> datetime:
        return datetime(2026, 8, 9, 18, 51, 23, tzinfo=UTC)


@pytest.fixture
def diario(tmp_path: Path) -> FileCaptureJournal:
    return FileCaptureJournal(tmp_path / "capturas", _RelojFijo())


# --- El tiempo, escrito como se lee --------------------------------------


def test_short_takes_are_written_as_minutes_and_seconds() -> None:
    assert formatear_tiempo(0) == "00:00"
    assert formatear_tiempo(14.7) == "00:14"
    assert formatear_tiempo(151) == "02:31"


def test_long_takes_grow_an_hours_field() -> None:
    assert formatear_tiempo(3852) == "1:04:12"


def test_a_negative_time_never_produces_a_broken_line() -> None:
    """No debería pasar, pero un menos en un archivo de montaje no ayuda."""
    assert formatear_tiempo(-5) == "00:00"


# --- El archivo junto al vídeo -------------------------------------------


def test_the_marks_end_up_next_to_the_video(diario: FileCaptureJournal, tmp_path: Path) -> None:
    video = tmp_path / "videos" / "2026-08-09 18-51-23.mp4"
    video.parent.mkdir(parents=True)

    diario.begin_take()
    diario.record_mark("el primer led", 14.0)
    diario.record_mark("se me cayó la resistencia", 151.0)
    diario.end_take(str(video))

    marcas = video.with_name(f"{video.stem}{SUFIJO_MARCAS}")
    contenido = marcas.read_text(encoding="utf-8")
    assert "2026-08-09 18-51-23.mp4" in contenido
    assert "00:14\tel primer led" in contenido
    assert "02:31\tse me cayó la resistencia" in contenido


def test_the_provisional_file_is_removed_once_it_is_saved(
    diario: FileCaptureJournal, tmp_path: Path
) -> None:
    video = tmp_path / "videos" / "toma.mp4"
    video.parent.mkdir(parents=True)

    diario.begin_take()
    diario.record_mark("algo", 3.0)
    assert (tmp_path / "capturas" / ARCHIVO_EN_CURSO).exists()

    diario.end_take(str(video))

    assert not (tmp_path / "capturas" / ARCHIVO_EN_CURSO).exists()


def test_a_take_without_marks_leaves_no_file(diario: FileCaptureJournal, tmp_path: Path) -> None:
    """Un .txt vacío junto a cada vídeo es ruido, y hace dudar."""
    video = tmp_path / "videos" / "toma.mp4"
    video.parent.mkdir(parents=True)

    diario.begin_take()
    diario.end_take(str(video))

    assert list(video.parent.glob(f"*{SUFIJO_MARCAS}")) == []


def test_each_take_starts_from_zero(diario: FileCaptureJournal, tmp_path: Path) -> None:
    """Las marcas de la toma anterior no pueden colarse en la siguiente."""
    carpeta = tmp_path / "videos"
    carpeta.mkdir()

    diario.begin_take()
    diario.record_mark("de la primera", 5.0)
    diario.end_take(str(carpeta / "una.mp4"))

    diario.begin_take()
    diario.record_mark("de la segunda", 7.0)
    diario.end_take(str(carpeta / "dos.mp4"))

    segunda = (carpeta / f"dos{SUFIJO_MARCAS}").read_text(encoding="utf-8")
    assert "de la segunda" in segunda
    assert "de la primera" not in segunda


# --- Cuando algo falla, no se pierde nada --------------------------------


def test_marks_survive_a_take_that_never_says_where_it_saved(
    diario: FileCaptureJournal, tmp_path: Path
) -> None:
    """Que falte el nombre del vídeo no es motivo para tirar las marcas."""
    diario.begin_take()
    diario.record_mark("esto no se puede perder", 9.0)

    diario.end_take(None)

    guardadas = list((tmp_path / "capturas").glob("marcas-*.txt"))
    assert len(guardadas) == 1
    assert "esto no se puede perder" in guardadas[0].read_text(encoding="utf-8")


def test_marks_survive_a_folder_that_cannot_be_written(
    diario: FileCaptureJournal, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """En Windows la carpeta del vídeo puede estar bloqueada o sincronizando."""
    original = Path.write_text

    def _fallar_junto_al_video(self: Path, *args: object, **kwargs: object) -> int:
        if SUFIJO_MARCAS in self.name:
            raise OSError("acceso denegado")
        return original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", _fallar_junto_al_video)

    diario.begin_take()
    diario.record_mark("tampoco se puede perder", 4.0)
    diario.end_take("C:/videos/toma.mp4")

    guardadas = list((tmp_path / "capturas").glob("marcas-*.txt"))
    assert len(guardadas) == 1
    assert "tampoco se puede perder" in guardadas[0].read_text(encoding="utf-8")


def test_writing_never_raises_while_recording(
    diario: FileCaptureJournal, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un disco lleno no puede tumbar una grabación en marcha."""

    def _siempre_falla(*_: object, **__: object) -> None:
        raise OSError("disco lleno")

    monkeypatch.setattr(Path, "write_text", _siempre_falla)
    monkeypatch.setattr(Path, "mkdir", _siempre_falla)

    diario.begin_take()
    diario.record_mark("da igual", 1.0)
    diario.end_take("C:/videos/toma.mp4")


# --- El diario de órdenes -------------------------------------------------


def test_every_order_leaves_a_line_with_its_moment(
    diario: FileCaptureJournal, tmp_path: Path
) -> None:
    diario.record("start_recording", "grabando")
    diario.record("switch_scene", "grabando", "cara")

    lineas = (tmp_path / "capturas" / ARCHIVO_DIARIO).read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2
    assert lineas[0].startswith("2026-08-09T18:51:23")
    assert lineas[1].endswith("cara")


# --- El camino entero: de la orden hablada al archivo --------------------


def test_the_promise_sirius_makes_out_loud_is_kept(tmp_path: Path) -> None:
    """Sirius dice «Marcado. Ya lo encontrarás luego». Esto es ese luego.

    Recorre lo mismo que una sesión real —encender, grabar, marcar, parar— con
    el diario de verdad detrás, y termina abriendo el archivo que quedará junto
    al vídeo. Es la prueba que hace cierta la frase.
    """
    from sirius.adapters.capture.fake import FakeCaptureBackend
    from sirius.application.studio_capture import StudioCaptureUseCase
    from sirius.domain.capture import Scene, SceneRegistry

    video = tmp_path / "videos" / "sesion-001.mkv"
    video.parent.mkdir(parents=True)
    escenas = SceneRegistry((Scene("mesa", "Mesa", "Mesa", ("mesa",), is_fallback=True),))
    caso_de_uso = StudioCaptureUseCase(
        backend=FakeCaptureBackend(output_path=str(video)),
        scenes=escenas,
        journal=FileCaptureJournal(tmp_path / "capturas", _RelojFijo()),
    )
    caso_de_uso.enable()

    caso_de_uso.start_recording()
    caso_de_uso.mark_moment("el primer led")
    caso_de_uso.stop_recording()

    marcas = video.with_name(f"{video.stem}{SUFIJO_MARCAS}")
    assert marcas.exists(), "la marca se dijo y no llegó a ningún sitio"
    assert "el primer led" in marcas.read_text(encoding="utf-8")


def test_pausing_does_not_close_the_take(tmp_path: Path) -> None:
    """Pausar no cierra el archivo, así que tampoco cierra las marcas."""
    from sirius.adapters.capture.fake import FakeCaptureBackend
    from sirius.application.studio_capture import StudioCaptureUseCase
    from sirius.domain.capture import Scene, SceneRegistry

    video = tmp_path / "videos" / "sesion-001.mkv"
    video.parent.mkdir(parents=True)
    escenas = SceneRegistry((Scene("mesa", "Mesa", "Mesa", ("mesa",), is_fallback=True),))
    caso_de_uso = StudioCaptureUseCase(
        backend=FakeCaptureBackend(output_path=str(video)),
        scenes=escenas,
        journal=FileCaptureJournal(tmp_path / "capturas", _RelojFijo()),
    )
    caso_de_uso.enable()

    caso_de_uso.start_recording()
    caso_de_uso.mark_moment("antes de la pausa")
    caso_de_uso.pause_recording()
    caso_de_uso.resume_recording()
    caso_de_uso.mark_moment("después de la pausa")
    caso_de_uso.stop_recording()

    contenido = video.with_name(f"{video.stem}{SUFIJO_MARCAS}").read_text(encoding="utf-8")
    assert "antes de la pausa" in contenido
    assert "después de la pausa" in contenido
