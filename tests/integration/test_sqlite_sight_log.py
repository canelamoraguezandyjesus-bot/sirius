"""Lo que recuerda haber visto, en una base de verdad (pieza G de la 0.4, ADR-265): se
apunta y se lee en orden, lo de antes se borra, quitar un permiso quita el nombre, y nada
de eso se queda en el fichero."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from sirius.adapters.persistence.sqlite_sight_log import build_sqlite_sight_log
from sirius.ports.sight_log import Change, SeenChange

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SEIS = datetime(2026, 10, 19, 18, 0, tzinfo=UTC)


@pytest.fixture
def en_tokio(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Este ordenador, con la hora de Tokio, nueve horas por delante de UTC."""
    if not hasattr(time, "tzset"):
        pytest.skip("cambiar la zona horaria del proceso necesita time.tzset")
    monkeypatch.setenv("TZ", "Asia/Tokyo")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def _base(tmp_path: Path) -> Path:
    """Una base con todas las migraciones, como la deja Sirius al abrirse."""
    database_path = tmp_path / "sirius.db"
    config = Config(str(_REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")
    return database_path


def test_apunta_cada_cambio_y_lo_devuelve_en_orden_con_su_hora_en_utc(tmp_path: Path) -> None:
    almacen = build_sqlite_sight_log(_base(tmp_path))
    cambios = (
        SeenChange(_SEIS + timedelta(minutes=2), Change.CAME, "Marta"),
        SeenChange(_SEIS, Change.THERE, None),
        SeenChange(_SEIS + timedelta(minutes=30), Change.LEFT, "Marta"),
    )

    almacen.add(cambios)

    assert almacen.since(_SEIS) == (cambios[1], cambios[0], cambios[2])
    assert almacen.since(_SEIS + timedelta(minutes=1)) == (cambios[0], cambios[2])
    almacen.close()


@pytest.mark.usefixtures("en_tokio")
def test_una_hora_de_este_ordenador_se_guarda_en_utc(tmp_path: Path) -> None:
    almacen = build_sqlite_sight_log(_base(tmp_path))
    local = datetime(2026, 10, 19, 20, 2, tzinfo=UTC).astimezone()
    assert local.hour == 5, "en Tokio, a la mañana siguiente"

    almacen.add((SeenChange(local, Change.CAME, None),))

    assert almacen.since(_SEIS)[-1].at == datetime(2026, 10, 19, 20, 2, tzinfo=UTC)
    assert almacen.since(local + timedelta(minutes=1)) == ()
    almacen.close()


def test_borra_lo_de_antes_de_un_momento(tmp_path: Path) -> None:
    almacen = build_sqlite_sight_log(_base(tmp_path))
    almacen.add(
        (
            SeenChange(_SEIS - timedelta(days=2), Change.CAME, "Pepe"),
            SeenChange(_SEIS, Change.CAME, "Marta"),
        )
    )

    assert almacen.drop_before(_SEIS - timedelta(days=1)) == 1

    assert almacen.since(_SEIS - timedelta(days=3)) == (SeenChange(_SEIS, Change.CAME, "Marta"),)
    almacen.close()


def test_quitar_un_permiso_quita_su_nombre_y_no_queda_en_el_fichero(tmp_path: Path) -> None:
    base = _base(tmp_path)
    almacen = build_sqlite_sight_log(base)
    almacen.add(
        (
            SeenChange(_SEIS, Change.CAME, "Mariagracia"),
            SeenChange(_SEIS, Change.CAME, "Pepe"),
            SeenChange(_SEIS + timedelta(minutes=5), Change.LEFT, "Mariagracia"),
            SeenChange(_SEIS - timedelta(days=2), Change.CAME, "Rigoberta"),
        )
    )
    assert b"Mariagracia" in base.read_bytes()

    assert almacen.forget("Mariagracia") == 2
    almacen.drop_before(_SEIS - timedelta(days=1))

    assert [cambio.who for cambio in almacen.since(_SEIS)] == [None, "Pepe", None]
    almacen.close()
    contenido = base.read_bytes()
    assert b"Mariagracia" not in contenido, "secure_delete pone a ceros lo quitado"
    assert b"Rigoberta" not in contenido, "y lo borrado"
    assert not base.with_name(base.name + "-journal").exists()
