"""Run lifecycle: illegal transitions and legal sequences (incidencia #177).

Requisito 1 (exhaustivo) y requisito 2 (recorrido completo
``PREPARED -> DISPATCHED -> RUNNING -> FINISHED/SUCCEEDED``, más ``LOST``).
La cancelación en dos tiempos tiene su propio fichero
(``test_cancellation.py``, requisitos 3-4).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

import pytest

from sirius_engine.domain.errors import DeadlineNotExceededError, IllegalTransitionError
from sirius_engine.domain.run import Run, RunOutcome, RunState
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeRun

Operation = Callable[[WorkEngineStore, str, datetime], Run]
Arranger = Callable[[WorkEngineStore, MakeRun, str, datetime, datetime], None]


def _op_dispatch(store: WorkEngineStore, run_id: str, now: datetime) -> Run:
    return store.dispatch_run(run_id, now=now)


def _op_confirm_running(store: WorkEngineStore, run_id: str, now: datetime) -> Run:
    return store.confirm_run_running(run_id, now=now)


def _op_observe(store: WorkEngineStore, run_id: str, now: datetime) -> Run:
    return store.observe_run(run_id, observacion="en curso", now=now)


def _op_succeed(store: WorkEngineStore, run_id: str, now: datetime) -> Run:
    return store.succeed_run(run_id, resultado={"ok": True}, now=now)


def _op_fail(store: WorkEngineStore, run_id: str, now: datetime) -> Run:
    return store.fail_run(run_id, diagnostico="fallo irrecuperable", now=now)


def _op_mark_lost(store: WorkEngineStore, run_id: str, now: datetime) -> Run:
    return store.mark_run_lost(run_id, now=now)


def _op_request_cancel(store: WorkEngineStore, run_id: str, now: datetime) -> Run:
    return store.request_run_cancellation(run_id, now=now)


def _op_confirm_cancelled(store: WorkEngineStore, run_id: str, now: datetime) -> Run:
    return store.confirm_run_cancelled(run_id, now=now)


OPERATIONS: dict[str, Operation] = {
    "dispatch": _op_dispatch,
    "confirm_running": _op_confirm_running,
    "observe": _op_observe,
    "succeed": _op_succeed,
    "fail": _op_fail,
    "mark_lost": _op_mark_lost,
    "request_cancel": _op_request_cancel,
    # confirm_cancelled requires a prior request_cancel; from a freshly
    # arranged Run it is always illegal (cancellation_status is NONE) — this
    # exhaustive matrix arranges bare states, so it is deliberately absent
    # from LEGAL_FROM for every state and exercised in test_cancellation.py.
    "confirm_cancelled": _op_confirm_cancelled,
}

#: The approved graph of arquitectura §3.3, hardcoded independently of the
#: implementation. ``deadline`` is set in the past for every arrangement
#: below, so ``mark_lost`` is legal purely by state where the graph allows it.
LEGAL_FROM: dict[RunState, frozenset[str]] = {
    RunState.PREPARED: frozenset({"dispatch"}),
    RunState.DISPATCHED: frozenset(
        {"confirm_running", "observe", "fail", "mark_lost", "request_cancel"}
    ),
    RunState.RUNNING: frozenset({"observe", "succeed", "fail", "mark_lost", "request_cancel"}),
    RunState.FINISHED: frozenset(),
}


def _to_prepared(
    store: WorkEngineStore, make_run: MakeRun, run_id: str, now: datetime, deadline: datetime
) -> None:
    make_run(run_id=run_id, now=deadline, deadline=deadline)


def _to_dispatched(
    store: WorkEngineStore, make_run: MakeRun, run_id: str, now: datetime, deadline: datetime
) -> None:
    _to_prepared(store, make_run, run_id, now, deadline)
    store.dispatch_run(run_id, now=deadline)


def _to_running(
    store: WorkEngineStore, make_run: MakeRun, run_id: str, now: datetime, deadline: datetime
) -> None:
    _to_dispatched(store, make_run, run_id, now, deadline)
    store.confirm_run_running(run_id, now=deadline)


def _to_finished(
    store: WorkEngineStore, make_run: MakeRun, run_id: str, now: datetime, deadline: datetime
) -> None:
    _to_running(store, make_run, run_id, now, deadline)
    store.succeed_run(run_id, resultado={"ok": True}, now=deadline)


ARRANGERS: dict[RunState, Arranger] = {
    RunState.PREPARED: _to_prepared,
    RunState.DISPATCHED: _to_dispatched,
    RunState.RUNNING: _to_running,
    RunState.FINISHED: _to_finished,
}


@pytest.mark.parametrize("state", list(RunState), ids=lambda s: s.value)
def test_only_approved_operations_succeed_from_each_state(
    store: WorkEngineStore, make_run: MakeRun, now: datetime, state: RunState
) -> None:
    deadline = now - timedelta(hours=1)  # already elapsed: isolates the state guard
    op_now = now
    for operation_name, operation in OPERATIONS.items():
        run_id = f"RUN-{state.value}-{operation_name}"
        ARRANGERS[state](store, make_run, run_id, now, deadline)
        if operation_name in LEGAL_FROM[state]:
            operation(store, run_id, op_now)  # must not raise
        else:
            with pytest.raises(IllegalTransitionError) as excinfo:
                operation(store, run_id, op_now)
            assert excinfo.value.current_state == state


def test_mark_lost_requires_the_deadline_to_have_elapsed(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    run_id = "RUN-DEADLINE-NOT-ELAPSED"
    deadline = now + timedelta(hours=1)
    make_run(run_id=run_id, now=now, deadline=deadline)
    store.dispatch_run(run_id, now=now)

    with pytest.raises(DeadlineNotExceededError):
        store.mark_run_lost(run_id, now=now)

    # Once the deadline has genuinely elapsed, the same operation succeeds.
    lost = store.mark_run_lost(run_id, now=deadline)
    assert lost.estado is RunState.FINISHED
    assert lost.desenlace is RunOutcome.LOST


# -- Requisito 2: recorrido legal completo -------------------------------------------


def test_full_happy_path_prepared_to_succeeded(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    run_id = "RUN-HAPPY-PATH"
    prepared = make_run(run_id=run_id, now=now, deadline=now + timedelta(hours=1))
    assert prepared.estado is RunState.PREPARED
    assert prepared.intento == 1

    dispatched = store.dispatch_run(run_id, now=now)
    assert dispatched.estado is RunState.DISPATCHED

    running = store.confirm_run_running(run_id, now=now)
    assert running.estado is RunState.RUNNING

    observed = store.observe_run(run_id, observacion="80% completado", now=now)
    assert observed.ultima_observacion == "80% completado"

    finished = store.succeed_run(run_id, resultado={"pr": "https://example.invalid/pr/1"}, now=now)
    assert finished.estado is RunState.FINISHED
    assert finished.desenlace is RunOutcome.SUCCEEDED
    assert finished.resultado == {"pr": "https://example.invalid/pr/1"}


def test_failed_path(store: WorkEngineStore, make_run: MakeRun, now: datetime) -> None:
    run_id = "RUN-FAILED"
    make_run(run_id=run_id, now=now, deadline=now + timedelta(hours=1))
    store.dispatch_run(run_id, now=now)
    store.confirm_run_running(run_id, now=now)

    failed = store.fail_run(run_id, diagnostico="dependencia externa caída", now=now)
    assert failed.estado is RunState.FINISHED
    assert failed.desenlace is RunOutcome.FAILED
    assert failed.diagnostico == "dependencia externa caída"


def test_lost_path(store: WorkEngineStore, make_run: MakeRun, now: datetime) -> None:
    run_id = "RUN-LOST"
    deadline = now + timedelta(minutes=5)
    make_run(run_id=run_id, now=now, deadline=deadline)
    store.dispatch_run(run_id, now=now)

    lost = store.mark_run_lost(run_id, now=deadline)
    assert lost.estado is RunState.FINISHED
    assert lost.desenlace is RunOutcome.LOST
