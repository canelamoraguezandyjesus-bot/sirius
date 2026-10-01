"""ADR-228: el implementador sabe qué hora es.

El corrector tiene su plazo a la vista desde ADR-155; el implementador no lo
tenía: su prompt le mandaba parar con `FAILED_SAFELY` si algo no cabía, pero
sin reloj no podía saber que no cabía, y el tope del job lo mató a los 59:52
sin una línea de diagnóstico (#581, 11-09-2026, bitácora entrada 92).

Estas guardas fijan las dos mitades, con la misma forma que
``test_corrector_entrega_por_hallazgo.py``: el paso del agente tiene plazo
propio y el prompt recibe ese MISMO número convertido en dos horas; y el job
cubre la suma de todos los plazos propios sin pasar del máximo que admite el
contador de los siete días.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from sirius_engine.adapters.github_worker_request import (
    PLAZO_DEL_IMPLEMENTADOR_MIN,
    RESERVA_PARA_LA_VALIDACION_MIN,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "implement-sirius-work.yml"

IMPLEMENTADOR = "Ejecutar Claude Code (implementador)"
SYNC = "Sync environment"
#: Reserva para la cadena completa (9-15 min medidos en el runner) más el push.
RESERVA_MINIMA_MIN = 12
RESERVA_MAXIMA_MIN = 20
#: Peor `uv sync` medido sin caché (ADR-224): 16 m 30 s.
PEOR_SYNC_MEDIDO_MIN = 17
#: Lo que el contador de los siete días admite como tope de un job (ADR-093).
TOPE_MAXIMO_DE_UN_JOB_MIN = 85
#: Checkout, uv, puerta, consumir el evento, prompt y aplicar el veredicto.
RESTO_DEL_JOB_MIN = 5


def _job() -> dict[str, Any]:
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    jobs = doc["jobs"]
    assert len(jobs) == 1, f"se esperaba un único job, hay {sorted(jobs)}"
    return dict(next(iter(jobs.values())))


def _pasos() -> list[dict[str, Any]]:
    return list(_job()["steps"])


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


def test_el_implementador_tiene_plazo_propio_y_es_el_que_recibe_en_su_prompt() -> None:
    """El número del plazo y el del tope son el MISMO número. Un paso sin plazo
    propio muere con el job -sin «Aplicar el veredicto»-, y un plazo distinto
    del que el prompt anuncia haría planificar al implementador contra una
    hora falsa."""
    tope = _paso_por_nombre(IMPLEMENTADOR).get("timeout-minutes")
    assert isinstance(tope, int) and tope > 0, "el paso del implementador no declara plazo propio"
    run = str(_paso_del_prompt().get("run") or "")
    assert _valor(run, "PLAZO_MIN") == tope, (
        f"PLAZO_MIN del paso del prompt ≠ timeout-minutes del implementador ({tope})"
    )


def test_la_reserva_para_la_validacion_final_cubre_la_cadena_medida() -> None:
    run = str(_paso_del_prompt().get("run") or "")
    reserva = _valor(run, "RESERVA_MIN")
    assert RESERVA_MINIMA_MIN <= reserva <= RESERVA_MAXIMA_MIN, reserva
    assert reserva < _valor(run, "PLAZO_MIN")


def test_la_proyeccion_del_motor_usa_los_mismos_numeros_que_el_workflow() -> None:
    """La proyección Python del prompt (A4-P2) reproduce la línea del reloj con
    sus propias constantes; si el YAML cambia un número y Python no, la
    no-divergencia cae byte a byte, pero esta guarda lo dice con nombre."""
    run = str(_paso_del_prompt().get("run") or "")
    assert _valor(run, "PLAZO_MIN") == PLAZO_DEL_IMPLEMENTADOR_MIN
    assert _valor(run, "RESERVA_MIN") == RESERVA_PARA_LA_VALIDACION_MIN


def test_el_contexto_del_prompt_lleva_las_dos_horas() -> None:
    """Las dos horas se calculan con `date -u` en el runner, segundos antes de
    arrancar al implementador, y van en «Contexto de esta ejecución», no en el
    prompt versionado del rol (H-28: ese texto no se toca aquí)."""
    run = str(_paso_del_prompt().get("run") or "")
    codigo = "\n".join(_lineas_de_codigo(run))
    assert 'plazo_utc="$(date -u -d "+${PLAZO_MIN} minutes"' in codigo
    assert 'limite_validacion_utc="$(date -u -d "+$((PLAZO_MIN - RESERVA_MIN)) minutes"' in codigo
    lineas_del_plazo = [
        linea for linea in _lineas_de_codigo(run) if "Plazo de esta ejecución (ADR-228)" in linea
    ]
    assert len(lineas_del_plazo) == 1, "el contexto debe llevar exactamente una línea de plazo"
    linea = lineas_del_plazo[0]
    assert linea.startswith('echo "- Plazo de esta ejecución (ADR-228)'), (
        "la línea del plazo tiene que ser un `echo` dentro del heredoc del prompt, no un no-op"
    )
    assert "${plazo_utc}" in linea and "${limite_validacion_utc}" in linea
    assert "${PLAZO_MIN} minutos" in linea
    assert "FAILED_SAFELY" in linea and "date -u" in linea
    assert run.index("Plazo de esta ejecución (ADR-228)") > run.index(
        "## Contexto de esta ejecución"
    )


def test_el_tope_del_job_cubre_todos_los_plazos_propios_y_no_pasa_del_maximo() -> None:
    """Si el job no cubre la suma, el tope del job vuelve a ser el que mata al
    agente, y el reloj que recibe sería mentira. Y por encima de 85 el
    contador de los siete días se queda sin hora posible (ADR-093)."""
    job = _job()
    tope = job.get("timeout-minutes")
    assert isinstance(tope, int)
    con_plazo: dict[str, int] = {
        str(p.get("name")): int(p["timeout-minutes"])
        for p in _pasos()
        if isinstance(p.get("timeout-minutes"), int)
    }
    assert IMPLEMENTADOR in con_plazo and SYNC in con_plazo, sorted(con_plazo)
    assert con_plazo[SYNC] >= PEOR_SYNC_MEDIDO_MIN, con_plazo[SYNC]
    suma = sum(con_plazo.values())
    assert tope >= suma + RESTO_DEL_JOB_MIN, (
        f"el job ({tope}) no cubre los plazos propios {con_plazo} ({suma}) más {RESTO_DEL_JOB_MIN}"
    )
    assert tope <= TOPE_MAXIMO_DE_UN_JOB_MIN, tope
