"""Las huellas cifradas de quien dio permiso, en una base de verdad (pieza E de la 0.4,
ADR-263): dar permiso cambia las de esa persona de una vez, quitarlo borra todas las suyas,
y lo borrado no se queda en el fichero."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.sqlite_recognition_prints import (
    SqliteRecognitionPrints,
    build_sqlite_recognition_prints,
)
from sirius.ports.recognition import PrintKind, SealedPrint

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _base(tmp_path: Path) -> Path:
    """Una base con todas las migraciones, como la deja Sirius al abrirse."""
    database_path = tmp_path / "sirius.db"
    config = Config(str(_REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")
    return database_path


def _huellas(persona: str, sello: bytes) -> tuple[SealedPrint, SealedPrint]:
    return (
        SealedPrint(persona, PrintKind.FACE, sello + b"-cara"),
        SealedPrint(persona, PrintKind.VOICE, sello + b"-voz"),
    )


def test_guarda_las_de_una_persona_y_las_devuelve_tal_cual(tmp_path: Path) -> None:
    almacen = build_sqlite_recognition_prints(_base(tmp_path))

    almacen.replace("Marta", _huellas("Marta", b"m"))

    assert almacen.all() == _huellas("Marta", b"m")
    almacen.close()


def test_dar_permiso_otra_vez_cambia_solo_las_suyas(tmp_path: Path) -> None:
    almacen = build_sqlite_recognition_prints(_base(tmp_path))
    almacen.replace("Marta", _huellas("Marta", b"m1"))
    almacen.replace("Pepe", _huellas("Pepe", b"p"))

    almacen.replace("Marta", _huellas("Marta", b"m2"))

    assert sorted(almacen.all(), key=lambda h: h.sealed) == sorted(
        (*_huellas("Marta", b"m2"), *_huellas("Pepe", b"p")), key=lambda h: h.sealed
    )
    almacen.close()


def test_unas_huellas_de_otra_persona_no_se_guardan_ni_borran_nada(tmp_path: Path) -> None:
    almacen = build_sqlite_recognition_prints(_base(tmp_path))
    almacen.replace("Marta", _huellas("Marta", b"m"))

    with pytest.raises(ValueError, match="quien da el permiso"):
        almacen.replace("Marta", _huellas("Pepe", b"p"))

    assert almacen.all() == _huellas("Marta", b"m")
    almacen.close()


def test_si_falla_a_medias_no_cambia_nada(tmp_path: Path) -> None:
    """O todo o nada: si guardar la segunda falla, la primera no se queda, y las de antes
    siguen."""
    almacen = build_sqlite_recognition_prints(_base(tmp_path))
    almacen.replace("Marta", _huellas("Marta", b"m"))
    rota = SealedPrint("Marta", PrintKind.VOICE, None)  # type: ignore[arg-type]

    with pytest.raises(Exception, match="NOT NULL"):
        almacen.replace("Marta", (SealedPrint("Marta", PrintKind.FACE, b"nueva"), rota))

    assert almacen.all() == _huellas("Marta", b"m")
    almacen.close()


def test_quitar_el_permiso_borra_todas_las_suyas_y_dice_cuantas(tmp_path: Path) -> None:
    almacen = build_sqlite_recognition_prints(_base(tmp_path))
    almacen.replace("Marta", _huellas("Marta", b"m"))
    almacen.replace("Pepe", _huellas("Pepe", b"p"))

    assert almacen.remove("Marta") == 2
    assert almacen.remove("Marta") == 0

    assert almacen.all() == _huellas("Pepe", b"p")
    almacen.close()


def test_lo_borrado_no_se_queda_en_el_fichero_ni_su_nombre(tmp_path: Path) -> None:
    """La huella cifrada de una cara de verdad mide más de lo que cabe en una página de
    SQLite: aquí, unos 6 KB, que también van a páginas de desbordamiento."""
    base = _base(tmp_path)
    almacen = build_sqlite_recognition_prints(base)
    sello = b"HUELLA-SELLADA-" + bytes(range(65, 91)) * 230
    nombre = "Persona-Que-Se-Va-Xyzzy"
    almacen.replace(nombre, (SealedPrint(nombre, PrintKind.FACE, sello),))
    almacen.close()
    assert sello[:200] in base.read_bytes(), "la prueba no ve lo guardado"

    almacen = build_sqlite_recognition_prints(base)
    almacen.remove(nombre)
    almacen.close()

    contenido = base.read_bytes()
    assert sello[:40] not in contenido
    assert sello[3000:3040] not in contenido
    assert nombre.encode() not in contenido


def test_apunta_cuando_se_dio_el_permiso(tmp_path: Path) -> None:
    base = _base(tmp_path)
    momento = datetime(2026, 10, 19, 3, 0, tzinfo=UTC)
    almacen = SqliteRecognitionPrints(build_engine(base), clock=lambda: momento)

    almacen.replace("Marta", _huellas("Marta", b"m"))

    with closing(sqlite3.connect(base)) as conexion:
        fechas = {fila[0] for fila in conexion.execute("SELECT created_at FROM recognition_prints")}
    assert fechas == {"2026-10-19 03:00:00.000000"}
    almacen.close()
