"""La tabla de pruebas de aceptación de una versión del robot dice la verdad (ADR-233).

Es la misma idea que ADR-006 para las PA de 0.1: la tabla se declara a mano y una
máquina comprueba que lo declarado existe. Aquí, además, que cada fila diga de
qué piezas depende y si está en verde, y que eso cuadre con el decorador
``pieza(...)`` de cada prueba y con ``PIEZAS_ENTREGADAS`` del conductor de la
versión. Así la tabla no puede decir «en verde» de una pieza que no ha entrado,
ni dejar una prueba sin fila.

Nació en ``test_robot_0_2_trazabilidad.py`` y se saca aquí para que cada versión
tenga su comprobación con el mismo rasero: lo que cambia de una a otra es su
``Version`` (el documento, los prefijos de sus PA y evaluaciones, el patrón de
sus pruebas y sus piezas) y su inventario aprobado, que vive en la prueba de
cada versión, a la vista de la revisión.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

COBERTURAS = frozenset({"automática", "parcial", "manual"})
MOTIVOS = frozenset({"proveedor-real", "windows-real", "evaluación-humana"})
ESTADOS = frozenset({"en verde", "pendiente"})
VACIO = "—"


@dataclass(frozen=True, slots=True)
class Inventario:
    """Lo aprobado: cuántas pruebas de máquina tiene, como poco, cada PA, y qué evaluaciones hay."""

    pruebas_por_pa: Mapping[str, int]
    evaluaciones: frozenset[str]


@dataclass(frozen=True, slots=True)
class Fila:
    id: str
    piezas: frozenset[str]
    cobertura: str
    motivo: str
    evaluacion: str
    estado: str
    pruebas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Version:
    """Lo que distingue la trazabilidad de una versión del robot.

    ``prefijo_pa`` y ``prefijo_e`` son los de sus identificadores («PA-R02-»,
    «E-R02-»); ``patron`` casa con los ficheros de sus pruebas de máquina; y
    ``piezas`` y ``adr`` son los de su conductor.
    """

    documento: Path
    prefijo_pa: str
    prefijo_e: str
    patron: str
    piezas: Mapping[str, str]
    adr: str


def leer_tabla(texto: str, prefijo_pa: str) -> list[Fila]:
    filas: list[Fila] = []
    for linea in texto.splitlines():
        if not linea.startswith(f"| {prefijo_pa}"):
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


def leer_evaluaciones(texto: str, prefijo_e: str) -> frozenset[str]:
    return frozenset(
        re.findall(rf"^### ({re.escape(prefijo_e)}\d{{2}})\s*$", texto, flags=re.MULTILINE)
    )


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


def leer_pruebas(carpeta: Path, propia: str, patron: str) -> dict[str, str | None]:
    """Cada prueba de los ficheros que casan con ``patron``, con la letra de su ``pieza(...)``."""
    pruebas: dict[str, str | None] = {}
    for fichero in sorted(carpeta.glob(patron)):
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
    inventario: Inventario,
    piezas: Mapping[str, str],
    adr: str,
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
        elif letra not in piezas:
            encontrados.append(f"{prueba}: la pieza {letra!r} no está en {adr}")

    vistas: dict[str, str] = {}
    referenciadas: set[str] = set()
    for fila in filas:
        if fila.cobertura not in COBERTURAS:
            encontrados.append(
                f"{fila.id}: cobertura {fila.cobertura!r} fuera de {sorted(COBERTURAS)}"
            )
        if fila.cobertura == "automática":
            if fila.motivo != VACIO or fila.evaluacion != VACIO:
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
        if fila.evaluacion != VACIO:
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


def defectos_de(
    version: Version,
    carpeta: Path,
    propia: str,
    entregadas: frozenset[str],
    inventario: Inventario,
) -> list[str]:
    """Los defectos de la tabla de ``version`` tal como está en el árbol.

    ``carpeta`` es la de las pruebas de aceptación y ``propia`` el fichero de la
    comprobación, que no es una prueba de la versión.
    """
    texto = version.documento.read_text(encoding="utf-8")
    filas = leer_tabla(texto, version.prefijo_pa)
    pruebas = leer_pruebas(carpeta, propia, version.patron)
    encontrados: list[str] = []
    if not filas:
        encontrados.append(f"{version.documento.name}: la tabla está vacía o ha cambiado de forma")
    if not pruebas:
        encontrados.append(f"no hay pruebas que casen con {version.patron}")
    return encontrados + defectos(
        filas,
        pruebas,
        leer_evaluaciones(texto, version.prefijo_e),
        entregadas,
        inventario,
        version.piezas,
        version.adr,
    )
