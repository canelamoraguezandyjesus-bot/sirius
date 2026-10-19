"""Cada petición al modelo dice si lleva la regla de no insultar, o por qué no (ronda 2 de
Codex sobre la PR #703, ADR-264).

La regla iba puesta camino a camino, y a cada camino nuevo se le olvidaba: la voz de las
órdenes de memoria en la ronda 1, la prueba a ciegas y las preguntas trampa en la 2. Aquí
se buscan en el código todas las funciones que construyen una petición al modelo, y cada
una tiene que estar en ``CARE_COVERAGE``: una nueva no pasa sin que alguien decida si
escribe como Sirius delante de alguien. Que las que la llevan la lleven de verdad lo miran
sus pruebas: las de la charla, las órdenes de memoria, la prueba a ciegas y las preguntas
trampa.
"""

from __future__ import annotations

import ast
from pathlib import Path

from sirius.application.age import CARE_COVERAGE, CARRIES_THE_RULE

_SRC = Path(__file__).resolve().parents[2] / "src"


def _peticiones_en(arbol: ast.AST, modulo: str) -> set[str]:
    """Las funciones de ``arbol`` que construyen un ``LLMRequest``, como
    «módulo.Clase.función»."""
    encontradas: set[str] = set()

    def busca(nodo: ast.AST, ruta: tuple[str, ...]) -> None:
        for hijo in ast.iter_child_nodes(nodo):
            if isinstance(hijo, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                busca(hijo, (*ruta, hijo.name))
                continue
            if isinstance(hijo, ast.Call) and _construye_una_peticion(hijo):
                encontradas.add(".".join((modulo, *ruta)))
            busca(hijo, ruta)

    busca(arbol, ())
    return encontradas


def _construye_una_peticion(llamada: ast.Call) -> bool:
    funcion = llamada.func
    if isinstance(funcion, ast.Name):
        return funcion.id == "LLMRequest"
    return isinstance(funcion, ast.Attribute) and funcion.attr == "LLMRequest"


def _peticiones() -> set[str]:
    encontradas: set[str] = set()
    for fichero in sorted((_SRC / "sirius").rglob("*.py")):
        modulo = ".".join(fichero.relative_to(_SRC).with_suffix("").parts)
        encontradas |= _peticiones_en(ast.parse(fichero.read_text(encoding="utf-8")), modulo)
    return encontradas


def test_cada_peticion_al_modelo_dice_si_lleva_la_regla_o_por_que_no() -> None:
    encontradas = _peticiones()

    sin_decidir = sorted(encontradas - set(CARE_COVERAGE))
    sobran = sorted(set(CARE_COVERAGE) - encontradas)
    assert sin_decidir == [], (
        f"estas peticiones al modelo no dicen si llevan la regla de no insultar: {sin_decidir}. "
        "Si escriben algo que lea u oiga alguien como de Sirius, que la lleven (CareWatch); "
        "si no, que CARE_COVERAGE diga por qué."
    )
    assert sobran == [], f"CARE_COVERAGE nombra peticiones que ya no existen: {sobran}"


def test_las_que_escriben_como_sirius_son_las_cuatro_que_se_ven() -> None:
    assert sorted(k for k, v in CARE_COVERAGE.items() if v == CARRIES_THE_RULE) == [
        "sirius.application.blind_test._answer",
        "sirius.application.send_message.CommandVoice.request",
        "sirius.application.send_message.SendMessageUseCase._send",
        "sirius.application.trick_questions._complete",
    ]


def test_la_busqueda_ve_una_peticion_nueva_donde_este() -> None:
    codigo = """
from sirius.ports import llm
from sirius.ports.llm import LLMRequest

def suelta():
    return LLMRequest(operation_id="a", instructions="", input_text="")

class Algo:
    def pide(self):
        return [llm.LLMRequest(operation_id="b", instructions="", input_text="")]
"""
    assert _peticiones_en(ast.parse(codigo), "sirius.nuevo") == {
        "sirius.nuevo.suelta",
        "sirius.nuevo.Algo.pide",
    }
