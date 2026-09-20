"""El registro de ideas aparcadas y descartadas (ADR-208).

POR QUÉ ESTA GUARDA EXISTE. Una idea «aparcada» sin decir qué tendría que pasar
para volver a mirarla no es una idea aparcada: es una idea olvidada con mejor
nombre, y vuelve a aparecer en cada repaso obligando a pensarla entera otra vez.
Pasó de verdad: la orquestación grande se aparcó el 24-07-2026 y volvió el 16-09
como si fuera nueva. Es la misma lección que ADR-198 escribió para las
decisiones, aplicada a las ideas.

Es determinista a propósito: lee un fichero YAML y comprueba qué campos trae.
No razona, no llama a ningún modelo y cuesta milisegundos.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRO = REPO_ROOT / "docs" / "ideas" / "registro_de_ideas.yml"

#: Cada estado exige el campo que lo hace útil. Sin él, la entrada no dice nada
#: que alguien pueda usar dentro de tres meses.
CAMPO_OBLIGATORIO_POR_ESTADO = {
    "aparcada": "volver_si",
    "descartada": "porque",
    "promovida": "promovida_a",
}

#: Lo que toda idea declara, sea cual sea su estado.
CAMPOS_SIEMPRE = ("id", "titulo", "estado", "nacida", "origen")

FORMATO_ID = re.compile(r"^I-\d{3}$")


def _ideas() -> list[Mapping[str, Any]]:
    datos = yaml.safe_load(REGISTRO.read_text(encoding="utf-8"))
    assert isinstance(datos, Mapping), "el registro de ideas no es un mapa"
    ideas = datos.get("ideas")
    assert isinstance(ideas, list), "el registro no trae una lista `ideas`"
    return [i for i in ideas if isinstance(i, Mapping)]


IDEAS = _ideas()


def test_el_registro_existe_y_se_lee() -> None:
    assert IDEAS, "el registro de ideas está vacío; si no hay ninguna, se dice, no se borra"


@pytest.mark.parametrize("idea", IDEAS, ids=lambda i: str(i.get("id", "?")))
def test_toda_idea_declara_lo_minimo(idea: Mapping[str, Any]) -> None:
    faltan = [c for c in CAMPOS_SIEMPRE if not str(idea.get(c, "")).strip()]
    assert not faltan, f"la idea {idea.get('id')} no declara: {', '.join(faltan)}"


@pytest.mark.parametrize("idea", IDEAS, ids=lambda i: str(i.get("id", "?")))
def test_el_identificador_sigue_el_convenio(idea: Mapping[str, Any]) -> None:
    identificador = str(idea.get("id", ""))
    assert FORMATO_ID.match(identificador), (
        f"«{identificador}» no sigue el convenio I-NNN, tres dígitos"
    )


@pytest.mark.parametrize("idea", IDEAS, ids=lambda i: str(i.get("id", "?")))
def test_el_estado_es_uno_de_los_tres(idea: Mapping[str, Any]) -> None:
    estado = str(idea.get("estado", ""))
    assert estado in CAMPO_OBLIGATORIO_POR_ESTADO, (
        f"la idea {idea.get('id')} declara el estado «{estado}», que no existe. "
        f"Son: {', '.join(sorted(CAMPO_OBLIGATORIO_POR_ESTADO))}."
    )


@pytest.mark.parametrize("idea", IDEAS, ids=lambda i: str(i.get("id", "?")))
def test_cada_estado_trae_el_campo_que_lo_hace_util(idea: Mapping[str, Any]) -> None:
    """Es la guarda que de verdad importa: sin esto el registro es un cajón."""
    estado = str(idea.get("estado", ""))
    campo = CAMPO_OBLIGATORIO_POR_ESTADO.get(estado)
    if campo is None:
        pytest.skip("el estado ya lo rechaza otra prueba")
    assert str(idea.get(campo, "")).strip(), (
        f"la idea {idea.get('id')} está «{estado}» y no declara `{campo}`. "
        "Una aparcada sin disparador vuelve como nueva; una descartada sin razón "
        "se vuelve a discutir entera."
    )


def test_ningun_identificador_repetido() -> None:
    vistos = [str(i.get("id")) for i in IDEAS]
    repetidos = sorted({x for x in vistos if vistos.count(x) > 1})
    assert not repetidos, f"identificadores repetidos: {', '.join(repetidos)}"


def test_la_vista_de_conocimiento_lee_este_registro() -> None:
    """Un registro que no aparece en `MEMORIA.md` es una pieza sin lector."""
    from sirius_engine.memoria import REGISTRO_IDEAS

    assert (REPO_ROOT / REGISTRO_IDEAS) == REGISTRO
    assert "## Las ideas aparcadas y descartadas" in (REPO_ROOT / "MEMORIA.md").read_text(
        encoding="utf-8"
    )
