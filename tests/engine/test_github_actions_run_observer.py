"""Clasificación real del observador de Runs de Actions (C1, incidencia #232, S3).

Cada caso reproduce una fila de la tabla borde x observación de
``experiments/work_engine_spike_i1/RESULTADOS.md`` (S3-P1), pasada por
:class:`GitHubActionsRunObserver` en vez de por la sonda desechable del
spike -este es el bloque que promueve esas mediciones a producción-.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sirius_engine.adapters.fixture_run_actions_probe import FixedRunActionsProbe
from sirius_engine.adapters.github_actions_run_observer import GitHubActionsRunObserver
from sirius_engine.domain.run import CancellationStatus, Run, RunState
from sirius_engine.domain.worker_ref import WorkerRef
from sirius_engine.ports.github_mirror import LecturaEstado
from sirius_engine.ports.run_actions_probe import LecturaRunActionsSnapshot, RunActionsSnapshot
from sirius_engine.ports.world import RemoteRunStatus

_REPO = "owner/repo"
_AHORA = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
_WORKER = WorkerRef(adapter="claude-code", perfil_ref="perfiles/prueba", perfil_version=1)


def _run(
    *,
    run_id: str = "32438622606",
    deadline: datetime | None = None,
    cancellation_status: CancellationStatus = CancellationStatus.NONE,
) -> Run:
    return Run(
        run_id=run_id,
        work_id="WI-0001",
        paso="paso-1",
        worker=_WORKER,
        work_package={},
        intento=1,
        estado=RunState.RUNNING,
        deadline=deadline if deadline is not None else _AHORA + timedelta(hours=2),
        created_at=_AHORA - timedelta(hours=1),
        updated_at=_AHORA,
        cancellation_status=cancellation_status,
    )


def _observer(*, run_id: str, snapshot: RunActionsSnapshot) -> GitHubActionsRunObserver:
    probe = FixedRunActionsProbe(
        snapshots_por_run={
            (_REPO, run_id): LecturaRunActionsSnapshot(estado=LecturaEstado.OK, snapshot=snapshot)
        }
    )
    return GitHubActionsRunObserver(probe=probe, repo=_REPO)


def test_fila_5_completado_con_exito_sin_via_de_resultados_se_reporta_failed() -> None:
    """S3-P1 fila 5: éxito medido, pero sin vía de resultados que confirme un WorkResult.

    Este Adapter no sabe leer el ``WorkResult`` estructurado (eso vive en el
    veredicto/PR, fuera de este puerto): reportar ``SUCCEEDED`` con
    ``resultado=None`` dejaba el Run vivo para siempre, porque
    ``recovery.py`` trata esa combinación como observación inutilizable
    (CODEX-002). Un ``WorkResult`` ausente o ilegible se cierra como
    ``FAILED`` con diagnóstico (arquitectura §5.1, líneas 273-286), nunca
    como éxito inventado.
    """
    run = _run(run_id="32438622606")
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="completed", conclusion="success", total_jobs=1
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.FAILED
    assert observacion.diagnostico is not None and "success" in observacion.diagnostico


def test_fila_6_completado_con_fallo_se_reporta_failed() -> None:
    run = _run(run_id="32434919237")
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="completed", conclusion="failure", total_jobs=1
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.FAILED
    assert observacion.diagnostico is not None and "failure" in observacion.diagnostico


def test_fila_4_skipped_se_reporta_failed_con_diagnostico_explicito() -> None:
    run = _run(run_id="32439900059")
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="completed", conclusion="skipped", total_jobs=1
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.FAILED
    assert observacion.diagnostico is not None and "skipped" in observacion.diagnostico


def test_fila_1_cancelado_con_trabajo_real_y_cancel_pedido_se_confirma() -> None:
    """S3-P1 fila 1: `total_jobs>0`, cancelado, Y el motor había pedido `CANCEL` (§3.3)."""
    run = _run(run_id="32216181668", cancellation_status=CancellationStatus.UNCONFIRMED)
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="completed", conclusion="cancelled", total_jobs=1
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.CANCELLED


def test_cancelado_con_trabajo_real_sin_cancel_pedido_es_una_perdida() -> None:
    """Misma fila 1, pero SIN que el motor pidiera `CANCEL`: aislamiento externo, no confirmado."""
    run = _run(run_id="32216181668", cancellation_status=CancellationStatus.NONE)
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="completed", conclusion="cancelled", total_jobs=1
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.LOST


def test_cancelado_sin_poder_leer_total_jobs_es_unknown() -> None:
    """CODEX-003: sin `total_jobs`, un cancelado no se puede clasificar entre la fila 1 y

    la fila 3 -"cancelado antes de arrancar" (`FAILED`) y "cancelado con
    trabajo real sin `CANCEL` pedido" (`LOST`) exigen saber si había algún
    job creado. El dato ausente no autoriza a caer por ninguna de las dos
    ramas medidas: se reporta `UNKNOWN`.
    """
    run = _run(run_id="32216181668", cancellation_status=CancellationStatus.NONE)
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="completed", conclusion="cancelled", total_jobs=None
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.UNKNOWN
    assert observacion.diagnostico is not None and observacion.diagnostico != ""


def test_fila_3_no_arrancado_cancelado_sin_job_se_reporta_failed() -> None:
    """S3-P1 fila 3: `total_jobs==0` y `cancelled` -no llegó a arrancar, no es una pérdida-."""
    run = _run(run_id="29793001470")
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="completed", conclusion="cancelled", total_jobs=0
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.FAILED
    assert observacion.diagnostico is not None and "job" in observacion.diagnostico


def test_fila_2_no_arrancado_perpetuo_antes_del_deadline_es_pending() -> None:
    """S3-P1 fila 2: `status=queued`, `total_jobs==0`. Antes del deadline: sigue vivo."""
    run = _run(run_id="32217400860", deadline=_AHORA + timedelta(hours=1))
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="queued", conclusion=None, total_jobs=0
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.PENDING


def test_fila_2_no_arrancado_perpetuo_tras_el_deadline_es_lost() -> None:
    """La misma observación estructural, pero con la cota absoluta del Run ya vencida.

    S3 declaró NO CONCLUYENTE cualquier umbral de duración derivado de
    `total_jobs==0` en solitario: esta prueba usa `Run.deadline` -un dato
    del dominio anterior a esta incidencia-, no un número inventado aquí.
    """
    run = _run(run_id="32217400860", deadline=_AHORA - timedelta(minutes=1))
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="queued", conclusion=None, total_jobs=0
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.LOST


def test_un_job_real_en_curso_es_pending_antes_del_deadline() -> None:
    """`total_jobs>0`: hay evidencia estructural de que sí arrancó, y la cota no ha vencido."""
    run = _run(run_id="32438622606", deadline=_AHORA + timedelta(minutes=1))
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="in_progress", conclusion=None, total_jobs=1
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.PENDING


def test_un_job_real_en_curso_es_lost_tras_vencer_el_deadline() -> None:
    """CODEX-001: `total_jobs>0` no exime de la cota absoluta -un job que arrancó y quedó

    colgado tras el deadline es la misma falta de desenlace concluyente que
    la arquitectura (§3.3, líneas 179-183) cierra como `LOST`, aunque no sea
    la ambigüedad de `total_jobs==0` que S3 midió.
    """
    run = _run(run_id="32438622606", deadline=_AHORA - timedelta(minutes=1))
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="in_progress", conclusion=None, total_jobs=1
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.LOST


def test_lectura_no_disponible_es_unknown_no_pending() -> None:
    run = _run()
    probe = FixedRunActionsProbe()  # sin fixture configurada: NO_DISPONIBLE
    observacion = GitHubActionsRunObserver(probe=probe, repo=_REPO).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.UNKNOWN
    assert observacion.diagnostico is not None and observacion.diagnostico != ""


def test_run_ausente_de_la_api_es_unknown() -> None:
    """La API respondió "no existe" para un run que el motor sí despachó: no se inventa LOST."""
    run = _run()
    probe = FixedRunActionsProbe(
        snapshots_por_run={
            (_REPO, run.run_id): LecturaRunActionsSnapshot(estado=LecturaEstado.OK, snapshot=None)
        }
    )
    observacion = GitHubActionsRunObserver(probe=probe, repo=_REPO).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.UNKNOWN


def test_conclusion_no_reconocida_por_s3_es_unknown_no_se_adivina() -> None:
    run = _run()
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="completed", conclusion="action_required", total_jobs=1
    )
    observacion = _observer(run_id=run.run_id, snapshot=snapshot).check_run(run, now=_AHORA)
    assert observacion.status is RemoteRunStatus.UNKNOWN


def test_clasificacion_es_determinista() -> None:
    run = _run(run_id="32217400860", deadline=_AHORA - timedelta(minutes=1))
    snapshot = RunActionsSnapshot(
        run_id=run.run_id, estado_run="queued", conclusion=None, total_jobs=0
    )
    observer = _observer(run_id=run.run_id, snapshot=snapshot)
    assert observer.check_run(run, now=_AHORA) == observer.check_run(run, now=_AHORA)
