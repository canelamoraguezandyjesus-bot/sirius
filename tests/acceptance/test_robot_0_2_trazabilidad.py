"""La tabla de ``docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md`` dice la verdad (ADR-233).

Es la misma idea que ADR-006 para las PA de 0.1: la tabla se declara a mano y una
máquina comprueba que lo declarado existe. Aquí, además, que cada fila diga de
qué piezas depende y si está en verde, y que eso cuadre con el decorador
``pieza(...)`` de cada prueba y con ``PIEZAS_ENTREGADAS`` del conductor. Así la
tabla no puede decir «en verde» de una pieza que no ha entrado, ni dejar una
prueba sin fila.

Las pruebas de debajo de la primera alimentan la comprobación con tablas rotas a
propósito: si un día dejara de cazar algo, fallarían ellas.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from conductor_robot_0_2 import PIEZAS, PIEZAS_ENTREGADAS

_RAIZ = Path(__file__).resolve().parents[2]
_DOCUMENTO = _RAIZ / "docs" / "evolution" / "PRUEBAS_0.2_DEL_ROBOT.md"
_CARPETA = _RAIZ / "tests" / "acceptance"

COBERTURAS = frozenset({"automática", "parcial", "manual"})
MOTIVOS = frozenset({"proveedor-real", "windows-real", "evaluación-humana"})
ESTADOS = frozenset({"en verde", "pendiente"})
_VACIO = "—"


@dataclass(frozen=True, slots=True)
class Inventario:
    """Lo aprobado: cuántas pruebas de máquina tiene, como poco, cada PA, y qué evaluaciones hay."""

    pruebas_por_pa: Mapping[str, int]
    evaluaciones: frozenset[str]


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


@dataclass(frozen=True, slots=True)
class Fila:
    id: str
    piezas: frozenset[str]
    cobertura: str
    motivo: str
    evaluacion: str
    estado: str
    pruebas: tuple[str, ...]


def leer_tabla(texto: str) -> list[Fila]:
    filas: list[Fila] = []
    for linea in texto.splitlines():
        if not linea.startswith("| PA-R02-"):
            continue
        celdas = [celda.strip() for celda in linea.strip().strip("|").split("|")]
        identificador, _, _, piezas, cobertura, motivo, evaluacion, estado, pruebas = celdas
        filas.append(
            Fila(
                id=identificador,
                piezas=frozenset(letra.strip() for letra in piezas.split(",") if letra.strip()),
                cobertura=cobertura,
                motivo=motivo,
                evaluacion=evaluacion,
                estado=estado,
                pruebas=tuple(re.findall(r"`([^`]+)`", pruebas)),
            )
        )
    return filas


def leer_evaluaciones(texto: str) -> frozenset[str]:
    return frozenset(re.findall(r"^### (E-R02-\d{2})\s*$", texto, flags=re.MULTILINE))


def _letra_de_pieza(funcion: ast.FunctionDef) -> str | None:
    for decorador in funcion.decorator_list:
        if (
            isinstance(decorador, ast.Call)
            and isinstance(decorador.func, ast.Name)
            and decorador.func.id == "pieza"
            and decorador.args
            and isinstance(decorador.args[0], ast.Constant)
            and isinstance(decorador.args[0].value, str)
        ):
            return decorador.args[0].value
    return None


def leer_pruebas(carpeta: Path, propia: str) -> dict[str, str | None]:
    """Cada prueba de ``test_robot_0_2_*.py``, con la letra de su ``pieza(...)``."""
    pruebas: dict[str, str | None] = {}
    for fichero in sorted(carpeta.glob("test_robot_0_2_*.py")):
        if fichero.name == propia:
            continue
        arbol = ast.parse(fichero.read_text(encoding="utf-8"))
        for nodo in arbol.body:
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                ruta = fichero.relative_to(carpeta.parents[1]).as_posix()
                pruebas[f"{ruta}::{nodo.name}"] = _letra_de_pieza(nodo)
    return pruebas


def defectos(
    filas: Iterable[Fila],
    pruebas: Mapping[str, str | None],
    evaluaciones: frozenset[str],
    entregadas: frozenset[str],
    inventario: Inventario = INVENTARIO_APROBADO,
) -> list[str]:
    """Todo lo que la tabla afirma y no es verdad. Vacía si no hay nada.

    La tabla se compara con ``inventario``, que es independiente de ella y de
    las pruebas: quitar a la vez una fila y sus pruebas también se ve.
    """
    filas = list(filas)
    encontrados: list[str] = []

    esperados = list(inventario.pruebas_por_pa)
    if [fila.id for fila in filas] != esperados:
        encontrados.append(
            f"la tabla no tiene, en orden, las PA del inventario aprobado: {[f.id for f in filas]}"
        )
    for fila in filas:
        minimo = inventario.pruebas_por_pa.get(fila.id, 0)
        if len(fila.pruebas) < minimo:
            encontrados.append(
                f"{fila.id}: tiene {len(fila.pruebas)} pruebas y el inventario aprobado "
                f"pide {minimo}"
            )
    if evaluaciones != inventario.evaluaciones:
        encontrados.append(
            "las evaluaciones del documento no son las del inventario aprobado: faltan "
            f"{sorted(inventario.evaluaciones - evaluaciones)} y sobran "
            f"{sorted(evaluaciones - inventario.evaluaciones)}"
        )

    for prueba, letra in pruebas.items():
        if letra is None:
            encontrados.append(f"{prueba}: no dice de qué pieza depende")
        elif letra not in PIEZAS:
            encontrados.append(f"{prueba}: la pieza {letra!r} no está en ADR-233")

    vistas: dict[str, str] = {}
    referenciadas: set[str] = set()
    for fila in filas:
        if fila.cobertura not in COBERTURAS:
            encontrados.append(
                f"{fila.id}: cobertura {fila.cobertura!r} fuera de {sorted(COBERTURAS)}"
            )
        if fila.cobertura == "automática":
            if fila.motivo != _VACIO or fila.evaluacion != _VACIO:
                encontrados.append(f"{fila.id}: es automática y declara motivo o evaluación")
        else:
            if fila.motivo not in MOTIVOS:
                encontrados.append(
                    f"{fila.id}: no es automática y su motivo {fila.motivo!r} no vale"
                )
            if fila.evaluacion not in evaluaciones:
                encontrados.append(
                    f"{fila.id}: su evaluación {fila.evaluacion!r} no está en el documento"
                )
        if fila.evaluacion != _VACIO:
            referenciadas.add(fila.evaluacion)
        if not fila.pruebas:
            encontrados.append(f"{fila.id}: no nombra ninguna prueba")
        letras: set[str] = set()
        for prueba in fila.pruebas:
            if prueba in vistas:
                encontrados.append(f"{prueba}: sale en {vistas[prueba]} y en {fila.id}")
            vistas[prueba] = fila.id
            if prueba not in pruebas:
                encontrados.append(f"{fila.id}: nombra {prueba}, que no existe")
                continue
            letra = pruebas[prueba]
            if letra is not None:
                letras.add(letra)
        if fila.piezas != letras:
            encontrados.append(
                f"{fila.id}: dice piezas {sorted(fila.piezas)} "
                f"y sus pruebas son de {sorted(letras)}"
            )
        if fila.estado not in ESTADOS:
            encontrados.append(f"{fila.id}: estado {fila.estado!r} fuera de {sorted(ESTADOS)}")
        else:
            debe = "en verde" if fila.piezas and fila.piezas <= entregadas else "pendiente"
            if fila.estado != debe:
                encontrados.append(
                    f"{fila.id}: dice «{fila.estado}» y, con las piezas entregadas, es «{debe}»"
                )

    for prueba in pruebas:
        if prueba not in vistas:
            encontrados.append(f"{prueba}: no sale en la tabla")
    for evaluacion in sorted(evaluaciones - referenciadas):
        encontrados.append(f"{evaluacion}: ninguna fila la usa")
    return encontrados


def test_la_tabla_de_las_pruebas_de_la_0_2_dice_la_verdad() -> None:
    texto = _DOCUMENTO.read_text(encoding="utf-8")
    filas = leer_tabla(texto)
    pruebas = leer_pruebas(_CARPETA, Path(__file__).name)

    assert filas, "la tabla está vacía o ha cambiado de forma"
    assert pruebas, "no hay pruebas de la 0.2 que comprobar"
    assert defectos(filas, pruebas, leer_evaluaciones(texto), PIEZAS_ENTREGADAS) == []


# --- La comprobación caza cada mentira posible -------------------------------

_P1 = "tests/acceptance/test_robot_0_2_x.py::test_uno"
_P2 = "tests/acceptance/test_robot_0_2_x.py::test_dos"
_BUENA = (
    Fila("PA-R02-01", frozenset({"B"}), "automática", _VACIO, _VACIO, "en verde", (_P1,)),
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
    return defectos(filas, pruebas, evaluaciones, _ENTREGADAS, inventario)


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
    sin_motivo = _con(1, motivo=_VACIO)
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
