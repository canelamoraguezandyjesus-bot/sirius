"""La tabla de ``docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md`` dice la verdad (ADR-233).

La comprobación vive en ``trazabilidad_del_robot``, compartida con las versiones
siguientes; aquí está lo que es de la 0.2: su ``Version`` y su inventario
aprobado. Las pruebas de debajo de la primera alimentan la comprobación con
tablas rotas a propósito: si un día dejara de cazar algo, fallarían ellas.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from pathlib import Path

from conductor_robot_0_2 import PIEZAS, PIEZAS_ENTREGADAS
from trazabilidad_del_robot import VACIO, Fila, Inventario, Version, defectos, defectos_de

_RAIZ = Path(__file__).resolve().parents[2]
_CARPETA = _RAIZ / "tests" / "acceptance"
_VERSION = Version(
    documento=_RAIZ / "docs" / "evolution" / "PRUEBAS_0.2_DEL_ROBOT.md",
    prefijo_pa="PA-R02-",
    prefijo_e="E-R02-",
    patron="test_robot_0_2_*.py",
    piezas=PIEZAS,
    adr="ADR-233",
)

#: El inventario aprobado en ADR-233: 18 PA, 39 pruebas de máquina y cinco
#: evaluaciones del propietario. Una prueba se puede renombrar o mejorar, pero
#: quitar una PA, una prueba o una evaluación es retirar una prueba, y eso no lo
#: hace una sesión sola (AGENTS.md): se cambia aquí, a la vista de la revisión.
INVENTARIO_APROBADO = Inventario(
    pruebas_por_pa={
        "PA-R02-01": 2,
        "PA-R02-02": 2,
        "PA-R02-03": 2,
        "PA-R02-04": 4,
        "PA-R02-05": 2,
        "PA-R02-06": 4,
        "PA-R02-07": 3,
        "PA-R02-08": 2,
        "PA-R02-09": 2,
        "PA-R02-10": 2,
        "PA-R02-11": 2,
        "PA-R02-12": 2,
        "PA-R02-13": 2,
        "PA-R02-14": 1,
        "PA-R02-15": 2,
        "PA-R02-16": 1,
        "PA-R02-17": 2,
        "PA-R02-18": 2,
    },
    evaluaciones=frozenset(f"E-R02-{n:02d}" for n in range(1, 6)),
)


def test_la_tabla_de_las_pruebas_de_la_0_2_dice_la_verdad() -> None:
    assert (
        defectos_de(_VERSION, _CARPETA, Path(__file__).name, PIEZAS_ENTREGADAS, INVENTARIO_APROBADO)
        == []
    )


# --- La comprobación caza cada mentira posible -------------------------------

_P1 = "tests/acceptance/test_robot_0_2_x.py::test_uno"
_P2 = "tests/acceptance/test_robot_0_2_x.py::test_dos"
_BUENA = (
    Fila("PA-R02-01", frozenset({"B"}), "automática", VACIO, VACIO, "en verde", (_P1,)),
    Fila("PA-R02-02", frozenset({"C"}), "parcial", "windows-real", "E-R02-01", "pendiente", (_P2,)),
)
_PRUEBAS: dict[str, str | None] = {_P1: "B", _P2: "C"}
_EVALUACIONES = frozenset({"E-R02-01"})
_ENTREGADAS = frozenset({"A", "B"})
_INVENTARIO = Inventario(
    pruebas_por_pa={"PA-R02-01": 1, "PA-R02-02": 1}, evaluaciones=_EVALUACIONES
)


def _defectos(
    filas: Iterable[Fila],
    pruebas: Mapping[str, str | None] = _PRUEBAS,
    evaluaciones: frozenset[str] = _EVALUACIONES,
    inventario: Inventario = _INVENTARIO,
) -> list[str]:
    return defectos(filas, pruebas, evaluaciones, _ENTREGADAS, inventario, PIEZAS, "ADR-233")


def _con(fila: int, **cambios: object) -> list[Fila]:
    filas = list(_BUENA)
    filas[fila] = replace(filas[fila], **cambios)  # type: ignore[arg-type]
    return filas


def test_una_tabla_que_dice_la_verdad_no_tiene_defectos() -> None:
    assert _defectos(_BUENA) == []


def test_caza_una_prueba_que_no_sale_en_la_tabla() -> None:
    pruebas = {**_PRUEBAS, "tests/acceptance/test_robot_0_2_x.py::test_tres": "B"}
    assert any("test_tres: no sale en la tabla" in d for d in _defectos(_BUENA, pruebas))


def test_caza_una_prueba_nombrada_que_no_existe() -> None:
    filas = _con(0, pruebas=(_P1, "tests/acceptance/test_robot_0_2_x.py::test_fantasma"))
    assert any("test_fantasma, que no existe" in d for d in _defectos(filas))


def test_caza_en_verde_sin_la_pieza_y_pendiente_con_ella() -> None:
    adelantada = _con(1, estado="en verde")
    assert any("PA-R02-02: dice «en verde»" in d for d in _defectos(adelantada))
    atrasada = _con(0, estado="pendiente")
    assert any("PA-R02-01: dice «pendiente»" in d for d in _defectos(atrasada))


def test_caza_piezas_que_no_cuadran_con_las_de_sus_pruebas() -> None:
    filas = _con(0, piezas=frozenset({"B", "G"}), estado="pendiente")
    assert any("PA-R02-01: dice piezas" in d for d in _defectos(filas))


def test_caza_una_cobertura_parcial_sin_motivo_o_sin_evaluacion() -> None:
    sin_motivo = _con(1, motivo=VACIO)
    assert any("su motivo" in d for d in _defectos(sin_motivo))
    sin_evaluacion = _con(1, evaluacion="E-R02-09")
    assert any("no está en el documento" in d for d in _defectos(sin_evaluacion))


def test_caza_un_hueco_en_la_numeracion() -> None:
    filas = _con(1, id="PA-R02-03")
    assert any("las PA del inventario aprobado" in d for d in _defectos(filas))


def test_caza_una_prueba_sin_pieza_y_una_evaluacion_huerfana() -> None:
    sin_pieza = {**_PRUEBAS, _P1: None}
    assert any("no dice de qué pieza depende" in d for d in _defectos(_BUENA, sin_pieza))
    huerfana = _EVALUACIONES | {"E-R02-02"}
    con_huerfana = Inventario(pruebas_por_pa=_INVENTARIO.pruebas_por_pa, evaluaciones=huerfana)
    assert any(
        "E-R02-02: ninguna fila la usa" in d
        for d in _defectos(_BUENA, evaluaciones=huerfana, inventario=con_huerfana)
    )


def test_caza_una_prueba_de_una_pieza_que_no_es_de_la_version() -> None:
    """La letra de una ``pieza(...)`` tiene que ser de la tabla del ADR de la versión."""
    de_otra = {**_PRUEBAS, _P1: "Z"}
    assert any("la pieza 'Z' no está en ADR-233" in d for d in _defectos(_BUENA, de_otra))


# --- Lo aprobado no se reduce, aunque tabla y pruebas se reduzcan a la vez ---


def test_caza_que_se_quite_la_ultima_pa_junto_con_sus_pruebas() -> None:
    """Hallazgo P2 de Codex en la ronda 1 sobre la PR #681."""
    defectos_vistos = _defectos([_BUENA[0]], {_P1: "B"}, frozenset())

    assert any("las PA del inventario aprobado" in d for d in defectos_vistos)
    assert any("faltan ['E-R02-01']" in d for d in defectos_vistos)


def test_caza_que_una_pa_pierda_una_de_sus_pruebas() -> None:
    inventario = Inventario(
        pruebas_por_pa={"PA-R02-01": 2, "PA-R02-02": 1}, evaluaciones=_EVALUACIONES
    )

    assert any(
        "PA-R02-01: tiene 1 pruebas y el inventario aprobado pide 2" in d
        for d in _defectos(_BUENA, inventario=inventario)
    )


def test_el_inventario_aprobado_suma_las_39_pruebas_y_las_cinco_evaluaciones() -> None:
    assert len(INVENTARIO_APROBADO.pruebas_por_pa) == 18
    assert sum(INVENTARIO_APROBADO.pruebas_por_pa.values()) == 39
    assert len(INVENTARIO_APROBADO.evaluaciones) == 5
