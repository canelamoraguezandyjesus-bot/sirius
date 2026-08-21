"""Clasificador puro de bordes y tabla borde x observación (S3, incidencia #211).

Ninguna función de este módulo llama a `gh`, a la red, ni a un reloj real
(``datetime.now``/``time.time``): recibe los campos ya leídos por
:mod:`probe` -o, en pruebas y en el informe, los mismos campos congelados en
``fixtures/`` (S3-P4, requisito "la sonda no depende de que existan runs
nuevos"). El criterio de clasificación es siempre un campo estructural que
la API ya devuelve, nunca un umbral de duración adivinado (ADR-046, nota de
arranque §4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class EstadoBorde(StrEnum):
    """Las cinco clases que S3-P1 exige distinguir, más un cajón de escape."""

    CANCELADO = "cancelado"
    NO_ARRANCADO = "no_arrancado"
    SKIPPED = "skipped"
    COMPLETADO_EXITO = "completado_exito"
    COMPLETADO_FALLO = "completado_fallo"
    DESCONOCIDO = "desconocido"


@dataclass(frozen=True, slots=True)
class ObservacionRun:
    """Los campos observables de un run, ya leídos -nunca recalculados aquí."""

    caso: str
    run_id: str
    nombre: str
    status: str
    conclusion: str | None
    creado_en: str
    iniciado_en: str | None
    actualizado_en: str
    total_jobs: int
    job_conclusion: str | None
    job_runner_id: int | None
    job_runner_name: str | None
    job_iniciado_en: str | None
    job_completado_en: str | None
    logs_http: str


def observacion_desde_fixture(datos: dict[str, object]) -> ObservacionRun:
    """Traduce un fixture JSON (misma forma que devuelve la API real) a :class:`ObservacionRun`."""
    run = datos["run"]
    assert isinstance(run, dict)
    jobs_resp = datos["jobs"]
    assert isinstance(jobs_resp, dict)
    jobs = jobs_resp.get("jobs", [])
    assert isinstance(jobs, list)
    primer_job = jobs[0] if jobs else None
    return ObservacionRun(
        caso=str(datos["caso"]),
        run_id=str(datos["run_id"]),
        nombre=str(run.get("name") or ""),
        status=str(run["status"]),
        conclusion=run.get("conclusion"),
        creado_en=str(run["created_at"]),
        iniciado_en=run.get("run_started_at"),
        actualizado_en=str(run["updated_at"]),
        total_jobs=int(jobs_resp.get("total_count", len(jobs))),
        job_conclusion=(primer_job or {}).get("conclusion"),
        job_runner_id=(primer_job or {}).get("runner_id"),
        job_runner_name=(primer_job or {}).get("runner_name"),
        job_iniciado_en=(primer_job or {}).get("started_at"),
        job_completado_en=(primer_job or {}).get("completed_at"),
        logs_http=str(datos["logs_http"]),
    )


def clasificar(obs: ObservacionRun) -> EstadoBorde:
    """Clasifica por campos estructurales, en este orden -el orden importa (S3-P1).

    ``total_jobs == 0`` se comprueba PRIMERO: es la única señal que separa
    "nunca llegó a arrancar" de cualquier otro desenlace, incluido
    "cancelado" -un run cancelado con un job real asignado es una historia
    distinta de uno cancelado antes de que existiera ningún job. Invertir
    este orden es exactamente la mutación que S3-P1 exige poder detectar.
    """
    if obs.total_jobs == 0:
        return EstadoBorde.NO_ARRANCADO
    if obs.conclusion == "cancelled":
        return EstadoBorde.CANCELADO
    if obs.conclusion == "skipped" or obs.job_conclusion == "skipped":
        return EstadoBorde.SKIPPED
    if obs.conclusion == "success":
        return EstadoBorde.COMPLETADO_EXITO
    if obs.conclusion == "failure":
        return EstadoBorde.COMPLETADO_FALLO
    return EstadoBorde.DESCONOCIDO


def _segundos_entre(inicio: str | None, fin: str | None) -> float | None:
    if inicio is None or fin is None:
        return None
    a = datetime.fromisoformat(inicio.replace("Z", "+00:00"))
    b = datetime.fromisoformat(fin.replace("Z", "+00:00"))
    return (b - a).total_seconds()


@dataclass(frozen=True, slots=True)
class FilaTabla:
    caso: str
    run_id: str
    borde: EstadoBorde
    latencia_cola_s: float | None
    """``job.started_at - run.created_at``: cuánto tardó en verse asignado un runner."""
    duracion_job_s: float | None
    """``job.completed_at - job.started_at``: duración del propio job, si llegó a arrancar."""
    desvio_cierre_s: float | None
    """``run.updated_at - job.completed_at``: cuánto tarda el run en reflejar que el job terminó."""
    logs_http: str


def construir_tabla(observaciones: tuple[ObservacionRun, ...]) -> tuple[FilaTabla, ...]:
    """Determinista: función pura de ``observaciones``, sin E/S ni reloj."""
    filas = []
    for obs in observaciones:
        filas.append(
            FilaTabla(
                caso=obs.caso,
                run_id=obs.run_id,
                borde=clasificar(obs),
                latencia_cola_s=_segundos_entre(obs.creado_en, obs.job_iniciado_en),
                duracion_job_s=_segundos_entre(obs.job_iniciado_en, obs.job_completado_en),
                desvio_cierre_s=_segundos_entre(obs.job_completado_en, obs.actualizado_en),
                logs_http=obs.logs_http,
            )
        )
    return tuple(filas)
