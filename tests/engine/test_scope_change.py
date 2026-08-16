"""Cambio de alcance versionado (arquitectura §3.2, incidencia #177 requisito 7).

"Cambio de alcance conserva versión e historial: la versión anterior sigue
siendo legible después del cambio." Reprioritización se cubre aquí también:
no es un estado, no versiona (§3.2).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sirius_engine.domain.errors import IllegalTransitionError
from sirius_engine.domain.events import AggregateType
from sirius_engine.domain.run import CancellationStatus, RunOutcome, RunState
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeRun, MakeWorkItem


def test_scope_change_bumps_version_and_keeps_the_previous_version_readable(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-SCOPE"
    original = make_work_item(now=now, work_id=work_id)
    assert original.version == 1

    later = now + timedelta(hours=1)
    changed = store.change_work_item_scope(
        work_id, now=later, objetivo="objetivo revisado", entregable="entregable revisado"
    )

    assert changed.version == 2
    assert changed.objetivo == "objetivo revisado"
    assert changed.entregable == "entregable revisado"
    assert changed.fase is WorkItemPhase.PREPARAR

    versions = store.list_work_item_versions(work_id)
    assert len(versions) == 2
    first_version, second_version = versions
    assert first_version.version == 1
    assert first_version.objetivo == original.objetivo
    assert first_version.entregable == original.entregable
    assert second_version.version == 2
    assert second_version.objetivo == "objetivo revisado"

    # The current pointer moved on, but the first version object is unmutated.
    assert original.objetivo == "objetivo normalizado y confirmado"


def test_scope_change_only_touches_the_fields_given(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-SCOPE-PARTIAL"
    make_work_item(now=now, work_id=work_id)

    changed = store.change_work_item_scope(work_id, now=now, entregable="solo esto cambia")
    assert changed.entregable == "solo esto cambia"
    assert changed.objetivo == "objetivo normalizado y confirmado"
    assert changed.criterio_terminado == "el entregable existe y pasa sus pruebas"


def test_scope_change_forces_redo_preparar_from_any_phase(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-SCOPE-ACTIVE"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    changed = store.change_work_item_scope(work_id, now=now, objetivo="objetivo nuevo")
    assert changed.estado is WorkItemState.ACTIVE
    assert changed.fase is WorkItemPhase.PREPARAR


def test_scope_change_rejected_from_a_terminal_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-SCOPE-TERMINAL"
    make_work_item(now=now, work_id=work_id)
    store.cancel_work_item(work_id, now=now)

    with pytest.raises(IllegalTransitionError):
        store.change_work_item_scope(work_id, now=now, objetivo="demasiado tarde")


# -- Historial de versiones: una entrada por revisión de alcance ----------------------


def test_list_work_item_versions_returns_one_entry_per_scope_revision(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-VERSIONS-DEDUP"
    make_work_item(now=now, work_id=work_id)
    # Same version (1): a state change, not a scope revision.
    store.activate_work_item(work_id, now=now)

    store.change_work_item_scope(work_id, now=now, objetivo="objetivo revisado")

    versions = store.list_work_item_versions(work_id)
    assert [version.version for version in versions] == [1, 2]
    # The version-1 snapshot kept is the latest one known for it (ACTIVE),
    # not a stale copy from before the state change.
    assert versions[0].estado is WorkItemState.ACTIVE
    assert versions[1].version == 2
    assert versions[1].objetivo == "objetivo revisado"

    # No journal entry was discarded to build this projection.
    events = [
        event
        for event in store.list_events()
        if event.aggregate_type is AggregateType.WORK_ITEM and event.aggregate_id == work_id
    ]
    assert len(events) == 3


# -- Repriorización: no es un estado, no versiona -------------------------------------


def test_reprioritize_does_not_bump_version_or_change_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-REPRIORITIZE"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    reprioritized = store.reprioritize_work_item(work_id, prioridad=9, now=now)
    assert reprioritized.prioridad == 9
    assert reprioritized.version == 1
    assert reprioritized.estado is WorkItemState.ACTIVE


# -- Cambio de alcance cancela primero los Runs vivos que invalida --------------------


def test_scope_change_requests_cancellation_of_a_live_run_before_changing_scope(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    work_id = "WI-SCOPE-CANCELS-RUNS"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-OLD-SCOPE", work_id=work_id, now=now, deadline=deadline)
    store.dispatch_run("RUN-OLD-SCOPE", now=now)
    store.confirm_run_running("RUN-OLD-SCOPE", now=now)

    store.change_work_item_scope(work_id, now=now, objetivo="objetivo nuevo")

    # The invalidated run is not silently forgotten: cancellation was
    # requested, but it stays live until the adapter confirms a remote
    # terminal state or demonstrated isolation (§3.3) — never auto-confirmed.
    run = store.get_run("RUN-OLD-SCOPE")
    assert run is not None
    assert run.estado is RunState.RUNNING
    assert run.cancellation_status is CancellationStatus.UNCONFIRMED
    assert run.desenlace is None

    # The cancellation request lands in the journal before the scope change.
    events = store.list_events()
    cancel_index = next(
        i for i, event in enumerate(events) if event.kind == "run_cancellation_requested"
    )
    scope_index = next(
        i for i, event in enumerate(events) if event.kind == "work_item_scope_changed"
    )
    assert cancel_index < scope_index


def test_scope_change_invalidates_a_prepared_run_so_it_can_never_be_dispatched(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """CODEX-001: un Run PREPARED con el alcance viejo no debe poder despacharse.

    A diferencia de un Run DISPATCHED/RUNNING, uno PREPARED nunca llegó a un
    Worker remoto, así que se invalida de una vez en vez de pasar por la
    cancelación en dos tiempos (§3.3).
    """
    work_id = "WI-SCOPE-INVALIDATES-PREPARED"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-STALE-PREPARED", work_id=work_id, now=now, deadline=deadline)

    store.change_work_item_scope(work_id, now=now, objetivo="objetivo nuevo")

    run = store.get_run("RUN-STALE-PREPARED")
    assert run is not None
    assert run.estado is RunState.FINISHED
    assert run.desenlace is RunOutcome.CANCELLED
    # No pasó por la cancelación en dos tiempos: nunca hubo nada remoto que confirmar.
    assert run.cancellation_status is CancellationStatus.NONE

    with pytest.raises(IllegalTransitionError):
        store.dispatch_run("RUN-STALE-PREPARED", now=now)

    events = store.list_events()
    invalidated_index = next(
        i for i, event in enumerate(events) if event.kind == "run_prepared_invalidated"
    )
    scope_index = next(
        i for i, event in enumerate(events) if event.kind == "work_item_scope_changed"
    )
    assert invalidated_index < scope_index


def test_scope_change_does_not_touch_a_finished_run(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    work_id = "WI-SCOPE-FINISHED-RUN"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-DONE", work_id=work_id, now=now, deadline=deadline)
    store.dispatch_run("RUN-DONE", now=now)
    store.confirm_run_running("RUN-DONE", now=now)
    store.succeed_run("RUN-DONE", resultado={"ok": True}, now=now)

    store.change_work_item_scope(work_id, now=now, objetivo="objetivo nuevo")

    run = store.get_run("RUN-DONE")
    assert run is not None
    assert run.cancellation_status is CancellationStatus.NONE


def test_scope_change_does_not_double_request_an_already_pending_cancellation(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    work_id = "WI-SCOPE-ALREADY-CANCELLING"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-ALREADY-CANCELLING", work_id=work_id, now=now, deadline=deadline)
    store.dispatch_run("RUN-ALREADY-CANCELLING", now=now)
    store.request_run_cancellation("RUN-ALREADY-CANCELLING", now=now)

    # Must not raise IllegalTransitionError for re-requesting a pending cancellation.
    store.change_work_item_scope(work_id, now=now, objetivo="objetivo nuevo")

    run = store.get_run("RUN-ALREADY-CANCELLING")
    assert run is not None
    assert run.cancellation_status is CancellationStatus.UNCONFIRMED
