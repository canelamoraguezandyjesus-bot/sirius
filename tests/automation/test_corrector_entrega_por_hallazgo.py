"""ADR-155: el corrector entrega por hallazgo, con el plazo a la vista.

El corrector tiene 36 minutos por ronda (ADR-150) y no puede tener más (el
contador de siete días prohíbe jobs por encima de 85). En #545 murió dos veces
al agotar su paso —30:00 en la ronda 1, 36:12 en la ronda 4— sin haber empujado
nada: todo el trabajo de la ronda, perdido. La causa no eran los minutos sino la
forma de la ronda: el corrector no sabía cuándo moría y solo empujaba al final.

Estos guardianes fijan las dos mitades del arreglo: el workflow le dice al
corrector la hora a la que muere su paso y la hora límite para arrancar la
validación (con el MISMO número que gobierna el tope), y el prompt le exige
corregir por severidad, empujar tras cada hallazgo y, llegado el límite,
entregar lo hecho declarando lo que falta.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "repair-sirius-work.yml"
PROMPT = REPO_ROOT / "scripts" / "automation" / "prompts" / "corrector.md"

CORRECTOR = "Ejecutar Claude Code (corrector)"
#: Reserva para la cadena completa (9-15 min medidos en el runner) más el push.
RESERVA_MINIMA_MIN = 12
RESERVA_MAXIMA_MIN = 20


def _pasos() -> list[dict[str, Any]]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = doc["jobs"]
    assert len(jobs) == 1, f"se esperaba un único job, hay {sorted(jobs)}"
    return list(next(iter(jobs.values()))["steps"])


def _paso_por_nombre(nombre: str) -> dict[str, Any]:
    candidatos = [p for p in _pasos() if str(p.get("name") or "") == nombre]
    assert len(candidatos) == 1, f"paso {nombre!r}: {len(candidatos)} coincidencias"
    return candidatos[0]


def _paso_del_prompt() -> dict[str, Any]:
    candidatos = [p for p in _pasos() if p.get("id") == "build_prompt"]
    assert len(candidatos) == 1, "no encontré el paso `id: build_prompt`"
    return candidatos[0]


def _lineas_de_codigo(run: str) -> list[str]:
    return [
        linea.strip()
        for linea in run.splitlines()
        if linea.strip() and not linea.strip().startswith("#")
    ]


def _valor(run: str, variable: str) -> int:
    coincidencias = re.findall(rf"^\s*{variable}=(\d+)\s*$", run, flags=re.MULTILINE)
    assert len(coincidencias) == 1, (
        f"el paso del prompt debe fijar {variable}=<entero> exactamente una vez; "
        f"encontradas {len(coincidencias)}"
    )
    return int(coincidencias[0])


def test_el_plazo_que_recibe_el_corrector_es_el_timeout_de_su_paso() -> None:
    """El número del plazo y el del tope son el MISMO número. Si alguien sube o
    baja el `timeout-minutes` del corrector (ADR-150) sin tocar el prompt, el
    corrector planificaría contra una hora falsa: exactamente lo que este ADR
    viene a hacer imposible."""
    tope = _paso_por_nombre(CORRECTOR)["timeout-minutes"]
    run = str(_paso_del_prompt().get("run") or "")
    assert _valor(run, "PLAZO_MIN") == tope, (
        f"PLAZO_MIN del paso del prompt ≠ timeout-minutes del corrector ({tope})"
    )


def test_la_reserva_para_la_validacion_final_cubre_la_cadena_medida() -> None:
    """La cadena completa tarda entre 9 y 15 min en el runner (ADR-150, ADR-155),
    y después hay que empujar. Una reserva menor deja al corrector validando
    cuando el paso muere (la muerte de la ronda 1 de #545); una reserva
    desmedida le quita el tiempo de corregir."""
    run = str(_paso_del_prompt().get("run") or "")
    reserva = _valor(run, "RESERVA_MIN")
    assert RESERVA_MINIMA_MIN <= reserva <= RESERVA_MAXIMA_MIN, reserva
    assert reserva < _valor(run, "PLAZO_MIN")


def test_el_contexto_del_prompt_lleva_las_dos_horas() -> None:
    """Las dos horas se calculan con `date -u` en el runner, segundos antes de
    arrancar al corrector, y van en la sección «Contexto de esta ejecución»."""
    run = str(_paso_del_prompt().get("run") or "")
    codigo = "\n".join(_lineas_de_codigo(run))
    assert 'plazo_utc="$(date -u -d "+${PLAZO_MIN} minutes"' in codigo
    assert 'limite_validacion_utc="$(date -u -d "+$((PLAZO_MIN - RESERVA_MIN)) minutes"' in codigo
    lineas_del_plazo = [
        linea for linea in _lineas_de_codigo(run) if "Plazo de esta ronda (ADR-155)" in linea
    ]
    assert len(lineas_del_plazo) == 1, "el contexto debe llevar exactamente una línea de plazo"
    linea = lineas_del_plazo[0]
    assert "${plazo_utc}" in linea and "${limite_validacion_utc}" in linea
    assert "${PLAZO_MIN} minutos" in linea
    # La línea va DESPUÉS de que el contexto arranque, dentro del heredoc del prompt.
    posicion_contexto = run.index("## Contexto de esta ejecución")
    assert run.index("Plazo de esta ronda (ADR-155)") > posicion_contexto


def test_el_prompt_exige_severidad_push_por_hallazgo_y_plazo() -> None:
    texto = PROMPT.read_text(encoding="utf-8")
    assert "de mayor a menor severidad" in texto, (
        "corrector.md no exige corregir de mayor a menor severidad (ADR-155)"
    )
    assert "commit y push tras cada hallazgo" in texto, (
        "corrector.md no exige commit y push tras cada hallazgo corregido: una "
        "muerte por tiempo volvería a perder la ronda entera (ADR-155)"
    )
    assert "deja de corregir aunque queden hallazgos" in texto, (
        "corrector.md no manda parar al llegar la hora límite de la validación (ADR-155)"
    )
    assert "hora límite" in texto and "ADR-155" in texto


def test_fixed_admite_la_entrega_parcial_declarada() -> None:
    """`FIXED` con hallazgos sin corregir es honesto solo si los nombra; la
    definición antigua —«todas las observaciones corregibles quedaron
    resueltas»— dejaba al corrector sin veredicto para la entrega parcial y lo
    empujaba a agotar el plazo."""
    texto = PROMPT.read_text(encoding="utf-8")
    assert "todas las observaciones corregibles quedaron resueltas" not in texto, (
        "la definición de FIXED sigue presuponiendo todo corregido (ADR-155)"
    )
    definicion = texto[texto.index("- `FIXED`:") : texto.index("- `CHECKS_UNRELATED`:")]
    assert "sin corregir" in definicion and "por su identificador" in definicion, (
        "la definición de FIXED no exige nombrar por identificador lo que quedó "
        "sin corregir (ADR-155)"
    )
