"""ADR-228: el implementador sabe qué hora es.

El corrector tiene su plazo a la vista desde ADR-155; el implementador no lo
tenía: su prompt le mandaba parar con `FAILED_SAFELY` si algo no cabía, pero
sin reloj no podía saber que no cabía, y el tope del job lo mató a los 59:52
sin una línea de diagnóstico (#581, 11-09-2026, bitácora entrada 92).

La primera versión de ADR-228 clavó un plazo fijo de 50 minutos en el paso del
agente. Codex (ronda 1 de la PR #675) mostró que seguía siendo mentira cuando la
preparación era lenta: con más de 35 minutos de checkout, Qt, uv y puertas, el
tope del job (85) llegaba antes que el plazo del paso y «Aplicar el veredicto»
moría con él. Desde entonces el plazo se CALCULA: el primer paso del job anota
su arranque, el paso del prompt resta lo consumido al tope del job y publica
`plazo_min`, y el paso del agente usa ese número como `timeout-minutes`. Estas
guardas fijan esa forma leyendo el YAML real; la aritmética la ejercita
``tests/engine/test_worker_request.py`` sobre el guión real.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from sirius_engine.adapters.github_worker_request import (
    PLAZO_MINIMO_MIN,
    RESERVA_FINAL_MIN,
    RESERVA_PARA_LA_VALIDACION_MIN,
    TOPE_DEL_JOB_MIN,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "implement-sirius-work.yml"

ARRANQUE = "Anotar el arranque del job"
IMPLEMENTADOR = "Ejecutar Claude Code (implementador)"
SYNC = "Sync environment"
PLAZO_DINAMICO = "${{ fromJSON(steps.build_prompt.outputs.plazo_min || '1') }}"
#: La cadena completa medida en el runner del implementador: hasta 21,4 min
#: (#653, run 35516764738, pytest 1283 s). La reserva tiene que cubrirla.
PEOR_CADENA_MEDIDA_MIN = 22
RESERVA_MAXIMA_MIN = 30
#: Peor `uv sync` medido sin caché (ADR-224): 16 m 30 s.
PEOR_SYNC_MEDIDO_MIN = 17
#: «Aplicar el veredicto» tarda menos de 5 min; la reserva final lo cubre con margen.
RESERVA_FINAL_MINIMA_MIN = 5


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


def test_el_arranque_del_job_se_anota_en_el_primer_paso() -> None:
    """El plazo se cuenta desde que el job empieza, no desde que el prompt se
    prepara: si el paso que anota el arranque no fuera el primero, todo lo que
    corriera antes quedaría fuera de la resta y el plazo volvería a ser mentira."""
    primero = _pasos()[0]
    assert str(primero.get("name")) == ARRANQUE, f"el primer paso es {primero.get('name')!r}"
    run = str(primero.get("run") or "")
    assert "JOB_ARRANQUE_EPOCH=$(date -u +%s)" in run and '>> "$GITHUB_ENV"' in run


def test_el_implementador_tiene_plazo_propio_y_es_el_que_recibe_en_su_prompt() -> None:
    """El número del plazo y el del tope son el MISMO número, y es el que el paso
    del prompt calcula y publica. Un paso sin plazo propio muere con el job -sin
    «Aplicar el veredicto»-, y un plazo distinto del que el prompt anuncia haría
    planificar al implementador contra una hora falsa."""
    tope = _paso_por_nombre(IMPLEMENTADOR).get("timeout-minutes")
    assert tope == PLAZO_DINAMICO, (
        f"el paso del implementador declara timeout-minutes={tope!r}; tiene que ser el "
        f"`plazo_min` que publica el paso del prompt: {PLAZO_DINAMICO}"
    )
    run = str(_paso_del_prompt().get("run") or "")
    codigo = "\n".join(_lineas_de_codigo(run))
    assert 'echo "plazo_min=${plazo_min}" >> "$GITHUB_OUTPUT"' in codigo
    assert "plazo_min=$(( TOPE_JOB_MIN - RESERVA_FINAL_MIN - consumido_min ))" in codigo
    assert "consumido_min=$(( (ahora_epoch - JOB_ARRANQUE_EPOCH + 59) / 60 ))" in codigo


def test_el_tope_del_job_es_el_que_se_reparte() -> None:
    """`TOPE_JOB_MIN` del paso del prompt y el `timeout-minutes` del job son el
    mismo número: si el job cambiara y la resta no, el plazo del agente volvería
    a estar fuera del job. El `sync` conserva su plazo propio (ADR-224)."""
    job = _job()
    tope = job.get("timeout-minutes")
    assert isinstance(tope, int) and tope > 0
    run = str(_paso_del_prompt().get("run") or "")
    assert _valor(run, "TOPE_JOB_MIN") == tope, f"TOPE_JOB_MIN ≠ timeout-minutes del job ({tope})"
    con_plazo: dict[str, int] = {
        str(p.get("name")): int(p["timeout-minutes"])
        for p in _pasos()
        if isinstance(p.get("timeout-minutes"), int)
    }
    assert SYNC in con_plazo and con_plazo[SYNC] >= PEOR_SYNC_MEDIDO_MIN, con_plazo.get(SYNC)
    assert IMPLEMENTADOR not in con_plazo, "el plazo del agente no es un número fijo"


def test_las_reservas_cubren_lo_medido_y_dejan_sitio_para_implementar() -> None:
    run = str(_paso_del_prompt().get("run") or "")
    reserva_validacion = _valor(run, "RESERVA_VALIDACION_MIN")
    assert PEOR_CADENA_MEDIDA_MIN <= reserva_validacion <= RESERVA_MAXIMA_MIN, reserva_validacion
    reserva_final = _valor(run, "RESERVA_FINAL_MIN")
    assert reserva_final >= RESERVA_FINAL_MINIMA_MIN, reserva_final
    minimo = _valor(run, "PLAZO_MINIMO_MIN")
    assert minimo >= reserva_validacion + 10, (
        "por debajo del mínimo no se arranca al agente: tiene que caber la validación "
        "final y algo de implementación"
    )
    assert minimo + reserva_final < _valor(run, "TOPE_JOB_MIN")


def test_la_proyeccion_del_motor_usa_los_mismos_numeros_que_el_workflow() -> None:
    """La proyección Python del prompt (A4-P2) reproduce la línea del reloj con
    sus propias constantes; si el YAML cambia un número y Python no, la
    no-divergencia cae byte a byte, pero esta guarda lo dice con nombre."""
    run = str(_paso_del_prompt().get("run") or "")
    assert _valor(run, "TOPE_JOB_MIN") == TOPE_DEL_JOB_MIN
    assert _valor(run, "RESERVA_FINAL_MIN") == RESERVA_FINAL_MIN
    assert _valor(run, "RESERVA_VALIDACION_MIN") == RESERVA_PARA_LA_VALIDACION_MIN
    assert _valor(run, "PLAZO_MINIMO_MIN") == PLAZO_MINIMO_MIN


def test_el_contexto_del_prompt_lleva_las_dos_horas_con_fecha() -> None:
    """Las dos horas se calculan con `date -u` en el runner, segundos antes de
    arrancar al implementador, llevan FECHA (un run que cruce la medianoche no
    puede ser ambiguo) y van en «Contexto de esta ejecución», no en el prompt
    versionado del rol (H-28: ese texto no se toca aquí)."""
    run = str(_paso_del_prompt().get("run") or "")
    codigo = "\n".join(_lineas_de_codigo(run))
    assert 'plazo_utc="$(date -u -d "+${plazo_min} minutes" +%Y-%m-%dT%H:%M:%SZ)"' in codigo
    assert (
        'limite_validacion_utc="$(date -u -d "+$((plazo_min - RESERVA_VALIDACION_MIN)) minutes" '
        '+%Y-%m-%dT%H:%M:%SZ)"'
    ) in codigo
    lineas_del_plazo = [
        linea for linea in _lineas_de_codigo(run) if "Plazo de esta ejecución (ADR-228)" in linea
    ]
    assert len(lineas_del_plazo) == 1, "el contexto debe llevar exactamente una línea de plazo"
    linea = lineas_del_plazo[0]
    assert linea.startswith('echo "- Plazo de esta ejecución (ADR-228)'), (
        "la línea del plazo tiene que ser un `echo` dentro del heredoc del prompt, no un no-op"
    )
    assert "${plazo_utc}" in linea and "${limite_validacion_utc}" in linea
    assert "${plazo_min} minutos" in linea
    assert "FAILED_SAFELY" in linea and "date -u" in linea
    assert run.index("Plazo de esta ejecución (ADR-228)") > run.index(
        "## Contexto de esta ejecución"
    )


def test_una_preparacion_lenta_deja_un_veredicto_en_vez_de_un_agente_sin_plazo() -> None:
    """Por debajo de `PLAZO_MINIMO_MIN` el guión escribe un veredicto FAILED_SAFELY
    en `SIRIUS_VERDICT_FILE` (la ruta que «Aplicar el veredicto» lee) y falla;
    el paso del agente se salta con una salida válida para su `timeout-minutes`."""
    run = str(_paso_del_prompt().get("run") or "")
    codigo = "\n".join(_lineas_de_codigo(run))
    assert 'if [ "$plazo_min" -lt "$PLAZO_MINIMO_MIN" ]; then' in codigo
    assert (
        '"verdict":"FAILED_SAFELY"' in codigo and '"${RUNNER_TEMP}/sirius_verdict.json"' in codigo
    )
    assert 'echo "plazo_min=1" >> "$GITHUB_OUTPUT"' in codigo
    veredicto = _paso_por_nombre("Aplicar el veredicto")
    assert "${RUNNER_TEMP}/sirius_verdict.json" in str(veredicto.get("run") or ""), (
        "el veredicto que deja el paso del prompt tiene que ser el que «Aplicar el veredicto» lee"
    )


def test_todos_los_pasos_antes_del_agente_tienen_plazo_y_dejan_la_reserva_final() -> None:
    """Ronda 2 de Codex en la PR #675: el cálculo del plazo solo sirve si llega
    antes de que la reserva final empiece a gastarse. Con checkout, uv, la
    puerta o el consumo del evento sin plazo propio, una preparación de 83
    minutos llegaba al paso del prompt con dos minutos para el veredicto. Todos
    los pasos anteriores al agente llevan plazo, su suma más la reserva final
    cabe en el job, y «Aplicar el veredicto» cabe en la reserva final."""
    pasos = _pasos()
    indice_agente = next(i for i, p in enumerate(pasos) if p.get("name") == IMPLEMENTADOR)
    previos = pasos[:indice_agente]
    sin_plazo = [
        str(p.get("name")) for p in previos if not isinstance(p.get("timeout-minutes"), int)
    ]
    assert sin_plazo == [], f"pasos anteriores al agente sin `timeout-minutes`: {sin_plazo}"
    suma_previos = sum(int(p["timeout-minutes"]) for p in previos)
    run = str(_paso_del_prompt().get("run") or "")
    tope = _valor(run, "TOPE_JOB_MIN")
    reserva_final = _valor(run, "RESERVA_FINAL_MIN")
    assert suma_previos + reserva_final <= tope, (
        f"los pasos anteriores al agente pueden consumir {suma_previos} min y la reserva final "
        f"es {reserva_final}: no caben en el job ({tope}); el paso del prompt podría llegar con "
        "la reserva ya gastada"
    )
    veredicto = _paso_por_nombre("Aplicar el veredicto")
    assert isinstance(veredicto.get("timeout-minutes"), int), "«Aplicar el veredicto» sin plazo"
    assert veredicto["timeout-minutes"] < reserva_final, (
        "la reserva final tiene que cubrir entero el plazo de «Aplicar el veredicto»"
    )
