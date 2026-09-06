"""ADR-152: los pasos posteriores al agente ejecutan la automatización de `main`.

Los workflows de rol hacen checkout de `main`, ejecutan un agente y después
aplican su veredicto (la revisión, además, recoge el resultado de Codex y
agrega). Hasta ADR-152 esos pasos invocaban `scripts/automation/...` por ruta
relativa al árbol de trabajo, y el árbol, a esas alturas, es el que el agente
dejó: el corrector hace checkout de la rama de la PR para corregirla. El 06-09
el veredicto de #545 (run 34007489545) corrió el `sirius_apply_verdict.sh` de
esa rama, anterior a ADR-149, y no relanzó Quality. Peor que la corrección
perdida: el agente elegía qué automatización aplicaba su propio veredicto con
el PAT.

Estos guardianes fijan la forma que lo hace imposible: una copia de
`scripts/automation` tomada nada más hacer checkout, y ninguna referencia al
árbol en los pasos posteriores al agente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"

CONGELACION = "Congelar la automatización de main"
COPIA = '"${RUNNER_TEMP}/automation-de-main/'
ORDEN_DE_COPIA = 'cp -R scripts/automation "${RUNNER_TEMP}/automation-de-main"'
GUIONES_POSTERIORES = (
    "sirius_apply_verdict.sh",
    "sirius_codex_review.py",
    "sirius_aggregate_reviews.py",
)

# Cada workflow con agente y el prefijo del nombre del paso que lo ejecuta.
CON_AGENTE = [
    ("implement-sirius-work.yml", "Ejecutar Claude Code (implementador)"),
    ("review-sirius-work.yml", "Ejecutar Claude Code (revisor)"),
    ("repair-sirius-work.yml", "Ejecutar Claude Code (corrector)"),
    ("investigar-orden.yml", "Atender la orden"),
]


def _pasos(nombre: str) -> list[dict[str, Any]]:
    doc = yaml.safe_load((WORKFLOWS / nombre).read_text(encoding="utf-8"))
    jobs = doc["jobs"]
    assert len(jobs) == 1, f"{nombre}: se esperaba un único job, hay {sorted(jobs)}"
    return list(next(iter(jobs.values()))["steps"])


def _indice(pasos: list[dict[str, Any]], nombre: str) -> int:
    indices = [i for i, p in enumerate(pasos) if str(p.get("name") or "") == nombre]
    assert len(indices) == 1, f"paso {nombre!r}: {len(indices)} coincidencias"
    return indices[0]


def _indice_del_agente(pasos: list[dict[str, Any]], prefijo: str) -> int:
    indices = [i for i, p in enumerate(pasos) if str(p.get("name") or "").startswith(prefijo)]
    assert len(indices) == 1, f"agente {prefijo!r}: {len(indices)} coincidencias"
    return indices[0]


def _lineas_de_codigo(paso: dict[str, Any]) -> list[str]:
    """Las líneas ejecutables del `run`, sin los comentarios: un comentario que
    cite un guion no es una invocación (el paso que abre la PR del investigador
    nombra `sirius_apply_verdict.sh` en un comentario)."""
    return [
        linea.strip()
        for linea in str(paso.get("run") or "").splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    ]


@pytest.mark.parametrize(("workflow", "agente"), CON_AGENTE)
def test_la_copia_se_toma_justo_tras_el_checkout_y_antes_del_agente(
    workflow: str, agente: str
) -> None:
    pasos = _pasos(workflow)
    checkout = _indice(pasos, "Checkout")
    congelacion = _indice(pasos, CONGELACION)
    assert congelacion == checkout + 1, (
        f"{workflow}: la copia debe tomarse inmediatamente después del checkout, "
        "antes de que ningún otro paso toque el árbol"
    )
    assert congelacion < _indice_del_agente(pasos, agente)
    paso = pasos[congelacion]
    assert ORDEN_DE_COPIA in str(paso.get("run") or "")
    # Acotado y, si no puede copiar, falla: sin la copia no hay veredicto de
    # `main`, y un veredicto de otro sitio es justo lo que se prohíbe.
    assert paso.get("timeout-minutes") == 1
    assert "exit 1" in str(paso.get("run") or "")


@pytest.mark.parametrize(("workflow", "agente"), CON_AGENTE)
def test_los_pasos_posteriores_al_agente_invocan_la_copia_congelada(
    workflow: str, agente: str
) -> None:
    pasos = _pasos(workflow)
    posteriores = pasos[_indice_del_agente(pasos, agente) + 1 :]
    invocaciones = 0
    for paso in posteriores:
        for linea in _lineas_de_codigo(paso):
            for guion in GUIONES_POSTERIORES:
                if guion not in linea:
                    continue
                invocaciones += 1
                assert COPIA + guion in linea, (
                    f"{workflow} / {paso.get('name')}: {guion} debe ejecutarse desde "
                    f"la copia congelada de main, no desde el árbol: {linea!r}"
                )
    # Al menos el veredicto: si nadie invocara la automatización después del
    # agente, el guardián de arriba sería vacuo.
    assert invocaciones >= 1, f"{workflow}: ningún paso posterior aplica el veredicto"


@pytest.mark.parametrize(("workflow", "agente"), CON_AGENTE)
def test_ningun_paso_posterior_al_agente_ejecuta_el_arbol(workflow: str, agente: str) -> None:
    """Prohibición general, más allá de los tres guiones conocidos: después del
    agente, `scripts/automation/` del árbol no se ejecuta para nada."""
    pasos = _pasos(workflow)
    posteriores = pasos[_indice_del_agente(pasos, agente) + 1 :]
    for paso in posteriores:
        for linea in _lineas_de_codigo(paso):
            assert "scripts/automation/" not in linea, (
                f"{workflow} / {paso.get('name')}: referencia al árbol después del "
                f"agente: {linea!r}"
            )
