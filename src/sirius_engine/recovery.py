"""Barrido de recuperación al arrancar (A2, incidencia #186, arquitectura §3.5).

«Al arrancar, el motor ejecuta un barrido de recuperación: para cada Run no
terminado consulta ``STATUS`` contra el mundo real [...] y reconcilia; para
cada WorkItem en ``ACTIVE``/``WAITING`` recalcula el siguiente paso. Un
reinicio de Sirius no pierde ni duplica trabajo: como mucho repite una
consulta.»

Es el mismo patrón que un bucle de control: leer estado deseado (el diario,
vía :func:`~sirius_engine.domain.events.rebuild_state` sobre
``store.list_events()``), leer estado real (:mod:`sirius_engine.ports.world`,
que en A2 solo tiene un doble de pruebas — la implementación real es A3 y
bloques posteriores), calcular la diferencia y actuar de forma idempotente
por medio del propio puerto ``WorkEngineStore``, nunca escribiendo estado
propio fuera de lo que el almacén ya persiste.

**Acotación deliberada de "recalcular el siguiente paso" (ver ADR-029 §2)**:
A2 no tiene despachador de trabajo (eso es Supervisor/A4/A5), así que para
un ``WorkItem`` la única "siguiente paso" que este bloque calcula es
liberar la espera asíncrona -``WAITING -> ACTIVE`` vía
``observe_work_item_external_fact``- cuando todos los ``Run`` vivos de ese
``WorkItem`` alcanzaron ya un desenlace observable. Un ``WorkItem`` en
``ACTIVE`` no tiene ninguna acción propia de A2 que recalcular: su "próximo
paso" real (qué Worker despachar, qué fase seguir) queda para los bloques
que sí tienen Adapters de Worker.

La idempotencia de todo el barrido es una consecuencia de su diseño, no una
comprobación aparte que alguien deba recordar mantener: cada `Run` que se
reconcilia sale del conjunto "no terminado" (`FINISHED`) que la siguiente
pasada recorre, y cada `WorkItem` liberado sale de `WAITING`. Una segunda
pasada sobre el mismo estado no encuentra nada que reconciliar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius_engine.domain.events import rebuild_state
from sirius_engine.domain.run import CancellationStatus, Run, RunState
from sirius_engine.domain.work_item import WorkItemState
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.ports.world import RemoteRunStatus, RunWorldObservation, RunWorldObserver


@dataclass(frozen=True, slots=True)
class RecoverySweepResult:
    """Qué tocó el barrido, para que quien lo invoque pueda registrarlo."""

    reconciled_run_ids: tuple[str, ...]
    released_work_item_ids: tuple[str, ...]


def _ensure_dispatched(store: WorkEngineStore, run: Run, *, now: datetime) -> Run:
    """Promover ``run`` a ``DISPATCHED`` si seguía en ``PREPARED``, sin ir más allá.

    El barrido reconcilia contra un hecho que YA ocurrió en el mundo real
    (el mundo no reporta desenlaces de Runs que nunca se despacharon), así
    que si el diario se quedó en ``PREPARED`` es porque el motor murió antes
    de registrar el despacho -no porque el despacho no ocurriera-. Promover
    lo mínimo necesario para que la transición terminal sea legal evita
    inventar un ``confirm_running`` que el mundo no confirmó explícitamente.
    """
    if run.estado is RunState.PREPARED:
        return store.dispatch_run(run.run_id, now=now)
    return run


def _ensure_running(store: WorkEngineStore, run: Run, *, now: datetime) -> Run:
    """Como :func:`_ensure_dispatched`, pero hasta ``RUNNING`` (lo que exige ``succeed_run``)."""
    current = _ensure_dispatched(store, run, now=now)
    if current.estado is RunState.DISPATCHED:
        return store.confirm_run_running(current.run_id, now=now)
    return current


def _reconcile_run(
    store: WorkEngineStore, run: Run, observation: RunWorldObservation, *, now: datetime
) -> bool:
    """Aplicar la transición del almacén que corresponde a lo que el mundo reportó.

    Devuelve ``True`` si el ``Run`` cambió de estado (evento nuevo anexado),
    ``False`` si no había nada que hacer todavía -incluido el caso de
    ``PENDING`` (sigue vivo) y el de ``LOST`` antes de que venza su
    ``deadline`` (§3.3: ``LOST`` exige la cota absoluta cumplida; el barrido
    no la fuerza, deja que una pasada posterior -con un ``now`` mayor- la
    complete, "como mucho repite una consulta").
    """
    status = observation.status
    if status is RemoteRunStatus.PENDING:
        return False
    if status is RemoteRunStatus.SUCCEEDED:
        live = _ensure_running(store, run, now=now)
        store.succeed_run(live.run_id, resultado=observation.resultado or {}, now=now)
        return True
    if status is RemoteRunStatus.FAILED:
        live = _ensure_dispatched(store, run, now=now)
        store.fail_run(
            live.run_id,
            diagnostico=(
                observation.diagnostico or "fallo observado durante el barrido de recuperación"
            ),
            now=now,
        )
        return True
    if status is RemoteRunStatus.LOST:
        if now < run.deadline:
            return False
        live = _ensure_dispatched(store, run, now=now)
        store.mark_run_lost(live.run_id, now=now)
        return True
    if status is RemoteRunStatus.CANCELLED:
        if run.cancellation_status is not CancellationStatus.UNCONFIRMED:
            return False
        store.confirm_run_cancelled(run.run_id, now=now)
        return True
    raise AssertionError(f"RemoteRunStatus no manejado: {status!r}")


def run_recovery_sweep(
    store: WorkEngineStore, world: RunWorldObserver, *, now: datetime
) -> RecoverySweepResult:
    """Ejecutar el barrido de recuperación (arquitectura §3.5) una vez.

    Se invoca al arrancar el motor, y es seguro invocarla de nuevo en
    cualquier momento (idempotente): una pasada sobre un estado ya
    reconciliado no anexa ningún evento nuevo.
    """
    state = rebuild_state(store.list_events())

    reconciled_run_ids: list[str] = []
    for run_id in sorted(state.runs):
        run = state.runs[run_id]
        if run.estado is RunState.FINISHED:
            continue
        observation = world.check_run(run, now=now)
        if _reconcile_run(store, run, observation, now=now):
            reconciled_run_ids.append(run_id)

    released_work_item_ids: list[str] = []
    for work_id in sorted(state.work_item_versions):
        work_item = store.get_work_item(work_id)
        if work_item is None or work_item.estado is not WorkItemState.WAITING:
            continue
        runs_for_item = store.list_runs_for_work_item(work_id)
        if runs_for_item and all(run.estado is RunState.FINISHED for run in runs_for_item):
            store.observe_work_item_external_fact(work_id, now=now)
            released_work_item_ids.append(work_id)

    return RecoverySweepResult(
        reconciled_run_ids=tuple(reconciled_run_ids),
        released_work_item_ids=tuple(released_work_item_ids),
    )
