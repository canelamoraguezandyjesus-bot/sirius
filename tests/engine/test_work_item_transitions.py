"""WorkItem state machine: illegal transitions and legal sequences (incidencia #177).

Requisito 1: toda transición fuera del grafo aprobado (arquitectura §3.2)
falla explícitamente — se comprueba de forma EXHAUSTIVA: cada operación
desde cada estado. Requisito 2: al menos un recorrido legal completo, más
WAITING, PAUSED/reanudación y FAILED_SAFELY.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest

from sirius_engine.domain.errors import IllegalTransitionError
from sirius_engine.domain.work_item import WorkItem, WorkItemPhase, WorkItemState
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeWorkItem

Operation = Callable[[WorkEngineStore, str, datetime], WorkItem]
Arranger = Callable[[WorkEngineStore, MakeWorkItem, str, datetime], None]


def _op_activate(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.activate_work_item(work_id, now=now)


def _op_cancel(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.cancel_work_item(work_id, now=now)


def _op_escalate(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.escalate_work_item(work_id, now=now)


def _op_resolve_continue(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.resolve_work_item_decision(work_id, continuar=True, now=now)


def _op_resolve_cancel(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.resolve_work_item_decision(work_id, continuar=False, now=now)


def _op_dispatch_async(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.dispatch_work_item_async(work_id, now=now)


def _op_observe_external_fact(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.observe_work_item_external_fact(work_id, now=now)


def _op_fail_safely(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.fail_work_item_safely(work_id, diagnostico="sin progreso posible", now=now)


def _op_reactivate(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.reactivate_work_item(work_id, now=now)


def _op_deliver(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.deliver_work_item(work_id, resultado={"entregado": True}, now=now)


def _op_pause(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.pause_work_item(work_id, now=now)


def _op_resume(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.resume_work_item(work_id, now=now)


OPERATIONS: dict[str, Operation] = {
    "activate": _op_activate,
    "cancel": _op_cancel,
    "escalate": _op_escalate,
    "resolve_decision_continue": _op_resolve_continue,
    "resolve_decision_cancel": _op_resolve_cancel,
    "dispatch_async": _op_dispatch_async,
    "observe_external_fact": _op_observe_external_fact,
    "fail_safely": _op_fail_safely,
    "reactivate": _op_reactivate,
    "deliver": _op_deliver,
    "pause": _op_pause,
    "resume": _op_resume,
}

#: The approved graph of arquitectura §3.2, hardcoded independently of the
#: implementation so this test can actually catch a wrong guard.
LEGAL_FROM: dict[WorkItemState, frozenset[str]] = {
    WorkItemState.PLANNED: frozenset({"activate", "cancel", "pause"}),
    WorkItemState.ACTIVE: frozenset(
        {"escalate", "dispatch_async", "fail_safely", "deliver", "pause"}
    ),
    WorkItemState.WAITING: frozenset({"observe_external_fact", "pause"}),
    WorkItemState.NEEDS_DECISION: frozenset(
        {"resolve_decision_continue", "resolve_decision_cancel"}
    ),
    WorkItemState.PAUSED: frozenset({"resume"}),
    WorkItemState.FAILED_SAFELY: frozenset({"reactivate", "cancel"}),
    WorkItemState.CANCELLED: frozenset(),
    WorkItemState.DELIVERED: frozenset(),
}


def _to_planned(
    store: WorkEngineStore, make_work_item: MakeWorkItem, work_id: str, now: datetime
) -> None:
    make_work_item(now=now, work_id=work_id)


def _to_active(
    store: WorkEngineStore, make_work_item: MakeWorkItem, work_id: str, now: datetime
) -> None:
    _to_planned(store, make_work_item, work_id, now)
    store.activate_work_item(work_id, now=now)
    # Recorre el ciclo de fases (§3.4) hasta ENTREGAR, para que "deliver" sea
    # legal desde ACTIVE en esta matriz de estados; las demás operaciones no
    # dependen de la fase.
    store.begin_work_item_execution(work_id, now=now)
    store.begin_work_item_check(work_id, now=now)
    store.begin_work_item_review(work_id, now=now)
    store.approve_work_item_review(work_id, now=now)


def _to_waiting(
    store: WorkEngineStore, make_work_item: MakeWorkItem, work_id: str, now: datetime
) -> None:
    _to_active(store, make_work_item, work_id, now)
    store.dispatch_work_item_async(work_id, now=now)


def _to_needs_decision(
    store: WorkEngineStore, make_work_item: MakeWorkItem, work_id: str, now: datetime
) -> None:
    _to_active(store, make_work_item, work_id, now)
    store.escalate_work_item(work_id, now=now)


def _to_paused(
    store: WorkEngineStore, make_work_item: MakeWorkItem, work_id: str, now: datetime
) -> None:
    _to_active(store, make_work_item, work_id, now)
    store.pause_work_item(work_id, now=now)


def _to_failed_safely(
    store: WorkEngineStore, make_work_item: MakeWorkItem, work_id: str, now: datetime
) -> None:
    _to_active(store, make_work_item, work_id, now)
    store.fail_work_item_safely(work_id, diagnostico="sin progreso posible", now=now)


def _to_cancelled(
    store: WorkEngineStore, make_work_item: MakeWorkItem, work_id: str, now: datetime
) -> None:
    _to_planned(store, make_work_item, work_id, now)
    store.cancel_work_item(work_id, now=now)


def _to_delivered(
    store: WorkEngineStore, make_work_item: MakeWorkItem, work_id: str, now: datetime
) -> None:
    _to_active(store, make_work_item, work_id, now)
    store.deliver_work_item(work_id, resultado={"entregado": True}, now=now)


ARRANGERS: dict[WorkItemState, Arranger] = {
    WorkItemState.PLANNED: _to_planned,
    WorkItemState.ACTIVE: _to_active,
    WorkItemState.WAITING: _to_waiting,
    WorkItemState.NEEDS_DECISION: _to_needs_decision,
    WorkItemState.PAUSED: _to_paused,
    WorkItemState.FAILED_SAFELY: _to_failed_safely,
    WorkItemState.CANCELLED: _to_cancelled,
    WorkItemState.DELIVERED: _to_delivered,
}


@pytest.mark.parametrize("state", list(WorkItemState), ids=lambda s: s.value)
def test_only_approved_operations_succeed_from_each_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime, state: WorkItemState
) -> None:
    for operation_name, operation in OPERATIONS.items():
        work_id = f"WI-{state.value}-{operation_name}"
        ARRANGERS[state](store, make_work_item, work_id, now)
        if operation_name in LEGAL_FROM[state]:
            operation(store, work_id, now)  # must not raise
        else:
            with pytest.raises(IllegalTransitionError) as excinfo:
                operation(store, work_id, now)
            assert excinfo.value.current_state == state


def test_no_operation_ever_leaves_a_terminal_state() -> None:
    for state in (WorkItemState.CANCELLED, WorkItemState.DELIVERED):
        assert LEGAL_FROM[state] == frozenset()


# -- Requisito 2: recorridos legales completos --------------------------------------


def test_full_happy_path_planned_to_delivered(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-HAPPY-PATH"
    created = make_work_item(now=now, work_id=work_id)
    assert created.estado is WorkItemState.PLANNED
    assert created.fase is WorkItemPhase.PREPARAR

    activated = store.activate_work_item(work_id, now=now)
    assert activated.estado is WorkItemState.ACTIVE
    assert activated.fase is WorkItemPhase.PREPARAR

    executing = store.begin_work_item_execution(work_id, now=now)
    assert executing.fase is WorkItemPhase.EJECUTAR

    checking = store.begin_work_item_check(work_id, now=now)
    assert checking.fase is WorkItemPhase.COMPROBAR

    reviewing = store.begin_work_item_review(work_id, now=now)
    assert reviewing.fase is WorkItemPhase.REVISAR

    approved = store.approve_work_item_review(work_id, now=now)
    assert approved.fase is WorkItemPhase.ENTREGAR
    assert approved.estado is WorkItemState.ACTIVE

    delivered = store.deliver_work_item(work_id, resultado={"entregado": True}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED
    assert delivered.resultado == {"entregado": True}


def test_waiting_round_trip_then_delivered(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-WAITING"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    waiting = store.dispatch_work_item_async(work_id, now=now)
    assert waiting.estado is WorkItemState.WAITING

    active_again = store.observe_work_item_external_fact(work_id, now=now)
    assert active_again.estado is WorkItemState.ACTIVE

    store.begin_work_item_execution(work_id, now=now)
    store.begin_work_item_check(work_id, now=now)
    store.begin_work_item_review(work_id, now=now)
    store.approve_work_item_review(work_id, now=now)

    delivered = store.deliver_work_item(work_id, resultado={}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED


def test_pause_resume_round_trip_preserves_prior_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-PAUSE"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    paused = store.pause_work_item(work_id, now=now)
    assert paused.estado is WorkItemState.PAUSED
    assert paused.paused_from is WorkItemState.ACTIVE

    resumed = store.resume_work_item(work_id, now=now)
    assert resumed.estado is WorkItemState.ACTIVE
    assert resumed.paused_from is None

    store.begin_work_item_execution(work_id, now=now)
    store.begin_work_item_check(work_id, now=now)
    store.begin_work_item_review(work_id, now=now)
    store.approve_work_item_review(work_id, now=now)

    delivered = store.deliver_work_item(work_id, resultado={}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED


def test_pause_from_planned_resumes_to_planned(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-PAUSE-PLANNED"
    make_work_item(now=now, work_id=work_id)

    paused = store.pause_work_item(work_id, now=now)
    assert paused.paused_from is WorkItemState.PLANNED

    resumed = store.resume_work_item(work_id, now=now)
    assert resumed.estado is WorkItemState.PLANNED


def test_failed_safely_round_trip_then_delivered(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-FAILED-SAFELY"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    failed = store.fail_work_item_safely(work_id, diagnostico="dependencia rota", now=now)
    assert failed.estado is WorkItemState.FAILED_SAFELY
    assert failed.diagnostico == "dependencia rota"

    reactivated = store.reactivate_work_item(work_id, now=now)
    assert reactivated.estado is WorkItemState.ACTIVE

    store.begin_work_item_execution(work_id, now=now)
    store.begin_work_item_check(work_id, now=now)
    store.begin_work_item_review(work_id, now=now)
    store.approve_work_item_review(work_id, now=now)

    delivered = store.deliver_work_item(work_id, resultado={}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED


def test_escalation_and_decision_to_continue(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-DECISION-CONTINUE"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    escalated = store.escalate_work_item(work_id, now=now)
    assert escalated.estado is WorkItemState.NEEDS_DECISION

    resolved = store.resolve_work_item_decision(work_id, continuar=True, now=now)
    assert resolved.estado is WorkItemState.ACTIVE


def test_escalation_and_decision_to_cancel(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-DECISION-CANCEL"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)
    store.escalate_work_item(work_id, now=now)

    resolved = store.resolve_work_item_decision(work_id, continuar=False, now=now)
    assert resolved.estado is WorkItemState.CANCELLED
