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
from enum import StrEnum

from sirius_engine.domain.events import rebuild_state
from sirius_engine.domain.run import CancellationStatus, Run, RunState
from sirius_engine.domain.work_item import WorkItemState
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.ports.world import RemoteRunStatus, RunWorldObservation, RunWorldObserver


@dataclass(frozen=True, slots=True)
class UnobservedRun:
    """Un ``Run`` que el barrido dejó como estaba porque la lectura no fue concluyente."""

    run_id: str
    diagnostico: str


@dataclass(frozen=True, slots=True)
class RecoverySweepResult:
    """Qué tocó el barrido, para que quien lo invoque pueda registrarlo."""

    reconciled_run_ids: tuple[str, ...]
    released_work_item_ids: tuple[str, ...]
    #: Runs sobre los que el mundo no dio una observación utilizable. No se
    #: tocaron -no hay desenlace que inventar-, pero tampoco se callan: el
    #: barrido es el único que sabe que ocurrió (H-2, ADR-053).
    unobserved_runs: tuple[UnobservedRun, ...] = ()


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


class RunSweepOutcome(StrEnum):
    """Qué pudo hacer el barrido con un ``Run``.

    Tres valores y no dos, porque «no hice nada» esconde dos cosas que no se
    parecen: no había nada que hacer (el mundo informó y el Run sigue vivo)
    y no pude saber si lo había (H-2, ADR-053).
    """

    #: El Run cambió de estado: hay un evento nuevo en el diario.
    RECONCILED = "reconciled"
    #: El mundo informó, y todavía no toca actuar sobre este Run.
    NOTHING_TO_DO = "nothing_to_do"
    #: La observación no fue utilizable. El Run se queda como estaba.
    UNOBSERVED = "unobserved"


def _diagnostico_de_observacion_inutilizable(observation: RunWorldObservation) -> str:
    """Por qué el barrido no pudo usar esta observación.

    Si el observador explicó el fallo, se conserva su explicación tal cual:
    él es el único que sabe qué pasó al leer. Si no la dio, el barrido dice
    lo único que sí le consta -que la observación no era utilizable-, sin
    inventarse la causa.
    """
    if observation.diagnostico:
        return observation.diagnostico
    if observation.status is RemoteRunStatus.UNKNOWN:
        return "el mundo no pudo observar el Run durante el barrido de recuperación"
    return (
        "el mundo reportó SUCCEEDED pero el resultado no se pudo leer "
        "durante el barrido de recuperación"
    )


def _reconcile_run(
    store: WorkEngineStore, run: Run, observation: RunWorldObservation, *, now: datetime
) -> RunSweepOutcome:
    """Aplicar la transición del almacén que corresponde a lo que el mundo reportó.

    Devuelve ``RECONCILED`` si el ``Run`` cambió de estado (evento nuevo
    anexado); ``NOTHING_TO_DO`` si no había nada que hacer todavía -incluido
    el caso de ``PENDING`` (sigue vivo) y el de ``LOST`` antes de que venza
    su ``deadline`` (§3.3: ``LOST`` exige la cota absoluta cumplida; el
    barrido no la fuerza, deja que una pasada posterior -con un ``now``
    mayor- la complete, "como mucho repite una consulta")-; y ``UNOBSERVED``
    cuando la observación no permite concluir nada.

    **Por qué ``UNOBSERVED`` no escribe en el diario** (H-2, incidencia #214,
    ADR-053): el diario registra hechos del mundo, y un fallo de lectura no
    lo es. Cerrar el Run como ``SUCCEEDED`` sin resultado legible afirmaría
    «terminó bien y no entregó nada»; cerrarlo como ``FAILED`` o ``LOST``
    afirmaría un desenlace que nadie observó. El Run se queda vivo, la
    siguiente pasada vuelve a preguntar -y si el mundo nunca vuelve a ser
    legible, su ``deadline`` acaba habilitando ``LOST``, que es la vía que
    §3.3 ya prevé para eso-.
    """
    status = observation.status
    if status is RemoteRunStatus.PENDING:
        return RunSweepOutcome.NOTHING_TO_DO
    if status is RemoteRunStatus.UNKNOWN:
        return RunSweepOutcome.UNOBSERVED
    if status is RemoteRunStatus.SUCCEEDED:
        if observation.resultado is None:
            # `None` es «no pude leer el resultado», no «el resultado está
            # vacío». `resultado or {}` colapsaba las dos (H-2). Un `{}`
            # explícito sí es una lectura y sigue cerrando el Run.
            return RunSweepOutcome.UNOBSERVED
        live = _ensure_running(store, run, now=now)
        store.succeed_run(live.run_id, resultado=observation.resultado, now=now)
        return RunSweepOutcome.RECONCILED
    if status is RemoteRunStatus.FAILED:
        live = _ensure_dispatched(store, run, now=now)
        store.fail_run(
            live.run_id,
            diagnostico=(
                observation.diagnostico or "fallo observado durante el barrido de recuperación"
            ),
            now=now,
        )
        return RunSweepOutcome.RECONCILED
    if status is RemoteRunStatus.LOST:
        if now < run.deadline:
            return RunSweepOutcome.NOTHING_TO_DO
        live = _ensure_dispatched(store, run, now=now)
        store.mark_run_lost(live.run_id, now=now)
        return RunSweepOutcome.RECONCILED
    if status is RemoteRunStatus.CANCELLED:
        if run.cancellation_status is not CancellationStatus.UNCONFIRMED:
            return RunSweepOutcome.NOTHING_TO_DO
        store.confirm_run_cancelled(run.run_id, now=now)
        return RunSweepOutcome.RECONCILED
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
    unobserved_runs: list[UnobservedRun] = []
    for run_id in sorted(state.runs):
        run = state.runs[run_id]
        if run.estado is RunState.FINISHED:
            continue
        observation = world.check_run(run, now=now)
        outcome = _reconcile_run(store, run, observation, now=now)
        if outcome is RunSweepOutcome.RECONCILED:
            reconciled_run_ids.append(run_id)
        elif outcome is RunSweepOutcome.UNOBSERVED:
            unobserved_runs.append(
                UnobservedRun(
                    run_id=run_id,
                    diagnostico=_diagnostico_de_observacion_inutilizable(observation),
                )
            )

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
        unobserved_runs=tuple(unobserved_runs),
    )
