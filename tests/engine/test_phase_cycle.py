"""Ciclo de fases PREPARAR-ENTREGAR (arquitectura §3.4, incidencia #177/#178).

"``deliver()`` solo exige ACTIVE" era insuficiente: una activación seguida
de inmediato por una entrega declaraba entregado trabajo que nunca pasó por
EJECUTAR, COMPROBAR ni REVISAR. Estas pruebas fijan que la entrega exige
haber recorrido el ciclo determinista de fases —incluido el bucle
REVISAR/REPARAR— antes de aceptarse.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from sirius_engine.domain.errors import IllegalPhaseTransitionError, IllegalTransitionError
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeWorkItem


def test_deliver_is_rejected_before_the_phase_cycle_runs(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-DELIVER-TOO-SOON"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    current = store.get_work_item(work_id)
    assert current is not None
    assert current.fase is WorkItemPhase.PREPARAR

    with pytest.raises(IllegalPhaseTransitionError) as excinfo:
        store.deliver_work_item(work_id, resultado={"entregado": True}, now=now)
    assert excinfo.value.current_phase == WorkItemPhase.PREPARAR

    # Nothing changed: still ACTIVE/PREPARAR, not DELIVERED.
    unchanged = store.get_work_item(work_id)
    assert unchanged is not None
    assert unchanged.estado is WorkItemState.ACTIVE
    assert unchanged.fase is WorkItemPhase.PREPARAR


@pytest.mark.parametrize(
    "phase_before_deliver",
    [WorkItemPhase.EJECUTAR, WorkItemPhase.COMPROBAR, WorkItemPhase.REVISAR],
)
def test_deliver_is_rejected_mid_cycle(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    now: datetime,
    phase_before_deliver: WorkItemPhase,
) -> None:
    work_id = f"WI-DELIVER-MID-{phase_before_deliver.value}"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)
    store.begin_work_item_execution(work_id, now=now)
    if phase_before_deliver is not WorkItemPhase.EJECUTAR:
        store.begin_work_item_check(work_id, now=now)
    if phase_before_deliver is WorkItemPhase.REVISAR:
        store.begin_work_item_review(work_id, now=now)

    with pytest.raises(IllegalPhaseTransitionError):
        store.deliver_work_item(work_id, resultado={}, now=now)


def test_phase_cycle_advances_in_order_and_delivery_succeeds_once_approved(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-PHASE-HAPPY"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    executing = store.begin_work_item_execution(work_id, now=now)
    assert executing.fase is WorkItemPhase.EJECUTAR

    checking = store.begin_work_item_check(work_id, now=now)
    assert checking.fase is WorkItemPhase.COMPROBAR

    reviewing = store.begin_work_item_review(work_id, now=now)
    assert reviewing.fase is WorkItemPhase.REVISAR

    approved = store.approve_work_item_review(work_id, now=now)
    assert approved.fase is WorkItemPhase.ENTREGAR
    assert approved.estado is WorkItemState.ACTIVE  # approving review alone never delivers

    delivered = store.deliver_work_item(work_id, resultado={"entregado": True}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED
    assert delivered.fase is WorkItemPhase.ENTREGAR


def test_review_changes_required_loops_through_repair_back_to_check(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-PHASE-REPAIR-LOOP"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)
    store.begin_work_item_execution(work_id, now=now)
    store.begin_work_item_check(work_id, now=now)
    store.begin_work_item_review(work_id, now=now)

    repairing = store.request_work_item_repair(work_id, now=now)
    assert repairing.fase is WorkItemPhase.REPARAR

    back_to_check = store.resume_work_item_after_repair(work_id, now=now)
    assert back_to_check.fase is WorkItemPhase.COMPROBAR

    # The loop can run more than once before approval.
    store.begin_work_item_review(work_id, now=now)
    store.request_work_item_repair(work_id, now=now)
    store.resume_work_item_after_repair(work_id, now=now)
    reviewing_again = store.begin_work_item_review(work_id, now=now)
    assert reviewing_again.fase is WorkItemPhase.REVISAR

    approved = store.approve_work_item_review(work_id, now=now)
    assert approved.fase is WorkItemPhase.ENTREGAR

    delivered = store.deliver_work_item(work_id, resultado={}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED


@pytest.mark.parametrize(
    "operation_name",
    [
        "begin_work_item_check",
        "begin_work_item_review",
        "approve_work_item_review",
        "request_work_item_repair",
        "resume_work_item_after_repair",
    ],
)
def test_phase_operations_are_rejected_out_of_order(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime, operation_name: str
) -> None:
    work_id = f"WI-PHASE-OUT-OF-ORDER-{operation_name}"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)  # fase == PREPARAR: none of these are legal yet

    operation = getattr(store, operation_name)
    with pytest.raises(IllegalPhaseTransitionError):
        operation(work_id, now=now)


def test_phase_operations_require_the_work_item_to_be_active(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-PHASE-NOT-ACTIVE"
    make_work_item(now=now, work_id=work_id)  # still PLANNED

    with pytest.raises(IllegalTransitionError):
        store.begin_work_item_execution(work_id, now=now)


def test_scope_change_forces_redo_from_any_phase_including_mid_cycle(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-PHASE-SCOPE-RESET"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)
    store.begin_work_item_execution(work_id, now=now)
    store.begin_work_item_check(work_id, now=now)
    store.begin_work_item_review(work_id, now=now)
    store.approve_work_item_review(work_id, now=now)  # fase == ENTREGAR

    changed = store.change_work_item_scope(work_id, now=now, objetivo="objetivo nuevo")
    assert changed.fase is WorkItemPhase.PREPARAR

    # Delivery is rejected again until the cycle is redone.
    with pytest.raises(IllegalPhaseTransitionError):
        store.deliver_work_item(work_id, resultado={}, now=now)
