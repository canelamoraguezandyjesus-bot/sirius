"""La orden de E-R02-02 da la cuenta de las marcas como PA-R02-06 (ADR-247).

En su ordenador la ejecuta él, sobre su base. Aquí, con Sirius de verdad, el conductor de
la 0.2: que cuente lo mismo que la prueba de aceptación, que diga qué modelos dieron las
respuestas, que lea la base de la carpeta que él eligió y que no escriba nunca en ella.
"""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from _bases_abiertas import PUEDE_MIRAR, sin_recolector, vigila_lo_que_se_borra
from alembic import command
from alembic.config import Config
from conductor_robot_0_2 import Conductor, OllamaDeMentira

import contar_las_marcas as orden
from sirius.composition_root import DATA_PATHS_UNKNOWN
from sirius.infrastructure.bootstrap_location_store import build_bootstrap_location_store
from sirius.infrastructure.paths import resolve_paths

pytestmark = pytest.mark.integration

_RAIZ = Path(__file__).resolve().parents[2]

#: Las «eso no» de PA-R02-06: de las 60, las 10 primeras y una de cada cinco. De las
#: últimas 50 quedan 40 «eso es Sirius», justo las que hacen falta.
_COMO_PA_R02_06 = frozenset(n for n in range(1, 61) if n <= 10 or n % 5 == 0)

#: La revisión de la base anterior a la de ahora: la de quien no ha vuelto a abrir Sirius.
_REVISION_ANTERIOR = "96dcb8c3d40e"


def _marca(conductor: Conductor, cuantas: int, *, no: frozenset[int]) -> None:
    """Él dice ``cuantas`` cosas y marca cada respuesta, «eso no» las de ``no``. Las 30
    primeras las contesta el modelo de las pruebas, y las demás qwen3:4b-instruct."""
    for n in range(1, cuantas + 1):
        if n == 31:
            conductor.charla_por_ollama("qwen3:4b-instruct", OllamaDeMentira())
        conductor.di(f"Mensaje {n}.")
    for n in range(1, cuantas + 1):
        conductor.marca(n, "eso no" if n in no else "eso es Sirius")


def _su_base() -> Path:
    return resolve_paths().data_dir / "sirius.db"


def test_da_la_cuenta_de_pa_r02_06_y_pasa_con_40_de_las_ultimas_50(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    _marca(conductor, 60, no=_COMO_PA_R02_06)
    lineas: list[str] = []

    codigo = orden.main(escribe=lineas.append)

    assert conductor.cuenta_de_marcas(ultimas=50) == (40, 50)
    assert codigo == orden.PASA
    assert lineas == [
        "Las últimas 50 respuestas marcadas: 40 «eso es Sirius» y 10 «eso no».",
        "Las dieron qwen3:4b-instruct en 30 y grabador-de-pruebas en 20.",
        "Pasa: 40 de 50, y hacen falta 40.",
    ]


def test_con_39_de_las_ultimas_50_no_pasa(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    _marca(conductor, 60, no=_COMO_PA_R02_06 | {11})
    lineas: list[str] = []

    codigo = orden.main(escribe=lineas.append)

    assert conductor.cuenta_de_marcas(ultimas=50) == (39, 50)
    assert codigo == orden.NO_PASA
    assert lineas[0] == "Las últimas 50 respuestas marcadas: 39 «eso es Sirius» y 11 «eso no»."
    assert lineas[-1] == "No pasa: 39 de 50, y hacen falta 40."


def test_con_menos_de_50_dice_cuantas_lleva_y_cuantas_faltan(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    _marca(conductor, 23, no=frozenset({1, 2, 3}))
    lineas: list[str] = []

    codigo = orden.main(escribe=lineas.append)

    assert codigo == orden.FALTAN_MARCAS
    assert lineas == [
        "Respuestas marcadas hasta ahora: 23.",
        "De ellas, 20 «eso es Sirius» y 3 «eso no». Las dio grabador-de-pruebas.",
        "Todavía no hay 50 marcadas: llevas 23 y faltan 27.",
    ]


def test_sin_ninguna_marca_dice_que_faltan_las_50(tmp_path: Path) -> None:
    Conductor(tmp_path).cierra()
    lineas: list[str] = []

    codigo = orden.main(escribe=lineas.append)

    assert codigo == orden.FALTAN_MARCAS
    assert lineas == [
        "Respuestas marcadas hasta ahora: 0.",
        "Todavía no hay 50 marcadas: llevas 0 y faltan 50.",
    ]


def test_si_sirius_no_sabe_donde_estan_sus_datos_dice_que_lo_abra() -> None:
    lineas: list[str] = []

    codigo = orden.main(escribe=lineas.append)

    assert codigo == orden.SIN_DATOS
    assert lineas == [DATA_PATHS_UNKNOWN]


def test_lee_la_base_de_la_carpeta_que_el_eligio(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    _marca(conductor, 60, no=_COMO_PA_R02_06)
    conductor.cierra()
    elegida = tmp_path / "datos-elegidos"
    elegida.mkdir()
    (elegida / "sirius.db").write_bytes(_su_base().read_bytes())
    _su_base().unlink()
    build_bootstrap_location_store().save(elegida)
    lineas: list[str] = []

    codigo = orden.main(escribe=lineas.append)

    assert codigo == orden.PASA
    assert lineas[-1] == "Pasa: 40 de 50, y hacen falta 40."


def test_no_escribe_en_su_base_aunque_sea_de_antes_y_este_ocupada(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    _marca(conductor, 60, no=_COMO_PA_R02_06)
    conductor.cierra()
    base = _su_base()
    configuracion = Config(str(_RAIZ / "alembic.ini"))
    configuracion.set_main_option("script_location", str(_RAIZ / "migrations"))
    configuracion.set_main_option("sqlalchemy.url", f"sqlite:///{base}")
    command.downgrade(configuracion, _REVISION_ANTERIOR)
    antes = base.read_bytes()
    lineas: list[str] = []

    # Con su cerrojo de escritura cogido, como la ventana a mitad de guardar: leer se
    # puede, y cualquier escritura de la orden fallaría.
    with closing(sqlite3.connect(base)) as ventana:
        ventana.execute("BEGIN IMMEDIATE")
        codigo = orden.main(escribe=lineas.append)
        ventana.rollback()

    assert codigo == orden.PASA
    assert lineas[-1] == "Pasa: 40 de 50, y hacen falta 40."
    assert base.read_bytes() == antes
    with closing(sqlite3.connect(base)) as conexion:
        assert conexion.execute("SELECT version_num FROM alembic_version").fetchall() == [
            (_REVISION_ANTERIOR,)
        ]


@pytest.mark.skipif(not PUEDE_MIRAR, reason="sin /proc no se ve qué ficheros tiene abiertos")
def test_al_borrar_su_carpeta_temporal_ninguna_base_sigue_abierta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    conductor = Conductor(tmp_path)
    _marca(conductor, 60, no=_COMO_PA_R02_06)
    borrados = vigila_lo_que_se_borra(monkeypatch)
    lineas: list[str] = []

    with sin_recolector():
        codigo = orden.main(escribe=lineas.append)

    assert codigo == orden.PASA
    assert borrados
    assert [abiertos for _, abiertos in borrados] == [[] for _ in borrados]


def test_si_no_puede_borrar_su_carpeta_temporal_lo_avisa_y_la_cuenta_queda(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    conductor = Conductor(tmp_path)
    _marca(conductor, 60, no=_COMO_PA_R02_06)
    verdadero = shutil.rmtree
    sin_borrar: list[Path] = []

    def como_en_windows(ruta: Any, *args: Any, **kwargs: Any) -> None:
        sin_borrar.append(Path(ruta))
        raise PermissionError(13, "está siendo utilizado por otro proceso", str(ruta))

    monkeypatch.setattr(shutil, "rmtree", como_en_windows)
    lineas: list[str] = []

    try:
        codigo = orden.main(escribe=lineas.append)
    finally:
        for carpeta in sin_borrar:
            verdadero(carpeta, ignore_errors=True)

    assert codigo == orden.PASA
    assert lineas[-2] == "Pasa: 40 de 50, y hacen falta 40."
    assert lineas[-1].startswith(f"Aviso: no se pudo borrar la carpeta temporal {sin_borrar[0]}.")
