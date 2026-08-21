"""El diario reconstruye el estado (arquitectura §3.5, §12; incidencia #177 requisito 8).

"Reproducir el diario de una secuencia arbitraria de operaciones devuelve
exactamente el mismo estado." Se comprueba plegando
:func:`sirius_engine.domain.events.rebuild_state` sobre ``store.list_events()``
y comparando contra el estado en vivo del almacén, tras una mezcla amplia de
operaciones sobre varios WorkItem y Run.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sirius_engine.domain.events import rebuild_state
from sirius_engine.domain.run import RunState
from sirius_engine.domain.work_item import WorkItemState
from sirius_engine.ports.store import WorkEngineStore

from .conftest import WORKER_ALTERNATIVO, MakeRun, MakeWorkItem


def _run_arbitrary_sequence(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=2)

    make_work_item(now=now, work_id="WI-1")
    store.activate_work_item("WI-1", now=now)
    store.escalate_work_item("WI-1", now=now)
    store.resolve_work_item_decision("WI-1", continuar=True, now=now)
    store.dispatch_work_item_async("WI-1", now=now)
    store.observe_work_item_external_fact("WI-1", now=now)
    store.pause_work_item("WI-1", now=now)
    store.resume_work_item("WI-1", now=now)
    store.change_work_item_scope("WI-1", now=now, objetivo="objetivo revisado")
    store.reprioritize_work_item("WI-1", prioridad=5, now=now)
    store.fail_work_item_safely("WI-1", diagnostico="dependencia externa caída", now=now)
    store.reactivate_work_item("WI-1", now=now)
    store.begin_work_item_execution("WI-1", now=now)
    store.begin_work_item_check("WI-1", now=now)
    store.begin_work_item_review("WI-1", now=now)
    store.request_work_item_repair("WI-1", now=now)
    store.resume_work_item_after_repair("WI-1", now=now)
    store.begin_work_item_review("WI-1", now=now)
    store.approve_work_item_review("WI-1", now=now)
    store.deliver_work_item("WI-1", resultado={"ok": True}, now=now)

    make_work_item(now=now, work_id="WI-2")
    store.cancel_work_item("WI-2", now=now)

    make_run(run_id="RUN-1", work_id="WI-1", now=now, deadline=deadline, recurso_mutable="pr#1")
    store.dispatch_run("RUN-1", now=now)
    store.confirm_run_running("RUN-1", now=now)
    store.observe_run("RUN-1", observacion="50%", now=now)
    store.fail_run("RUN-1", diagnostico="timeout", now=now)
    store.retry_run("RUN-1", new_run_id="RUN-2", deadline=deadline, now=now)
    store.dispatch_run("RUN-2", now=now)
    store.request_run_cancellation("RUN-2", now=now)
    store.confirm_run_cancelled("RUN-2", now=now)
    store.substitute_run_worker(
        "RUN-1",
        new_run_id="RUN-3",
        worker=WORKER_ALTERNATIVO,
        motivo="cambio de Worker tras el fallo",
        deadline=deadline,
        now=now,
    )
    store.dispatch_run("RUN-3", now=now)
    store.confirm_run_running("RUN-3", now=now)
    store.succeed_run("RUN-3", resultado={"pr": "merged"}, now=now)

    make_run(run_id="RUN-4", work_id="WI-2", now=now, deadline=now + timedelta(minutes=1))
    store.dispatch_run("RUN-4", now=now)
    store.mark_run_lost("RUN-4", now=now + timedelta(minutes=1))


def test_replaying_the_journal_reproduces_the_live_work_item_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    _run_arbitrary_sequence(store, make_work_item, make_run, now)

    rebuilt = rebuild_state(store.list_events())

    for work_id in ("WI-1", "WI-2"):
        live = store.get_work_item(work_id)
        assert live is not None
        assert rebuilt.latest_work_item(work_id) == live

        live_versions = store.list_work_item_versions(work_id)
        assert rebuilt.work_item_versions[work_id] == tuple(live_versions)


def test_replaying_the_journal_reproduces_the_live_run_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    _run_arbitrary_sequence(store, make_work_item, make_run, now)

    rebuilt = rebuild_state(store.list_events())

    for run_id in ("RUN-1", "RUN-2", "RUN-3", "RUN-4"):
        live = store.get_run(run_id)
        assert live is not None
        assert rebuilt.runs[run_id] == live


def test_replaying_the_journal_is_order_independent(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """Folding by ``sequence`` — not by the order the caller passes events in."""
    _run_arbitrary_sequence(store, make_work_item, make_run, now)

    events = list(store.list_events())
    shuffled = list(reversed(events))
    assert shuffled != events, "the fixture must have more than one event for this to be meaningful"

    rebuilt_in_order = rebuild_state(events)
    rebuilt_shuffled = rebuild_state(shuffled)

    assert rebuilt_in_order.work_item_versions == rebuilt_shuffled.work_item_versions
    assert rebuilt_in_order.runs == rebuilt_shuffled.runs


def test_final_states_reached_by_the_arbitrary_sequence_are_the_expected_ones(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """Sanity check that the fixture sequence itself is legal end to end."""
    _run_arbitrary_sequence(store, make_work_item, make_run, now)

    wi1 = store.get_work_item("WI-1")
    assert wi1 is not None
    assert wi1.estado is WorkItemState.DELIVERED

    wi2 = store.get_work_item("WI-2")
    assert wi2 is not None
    assert wi2.estado is WorkItemState.CANCELLED

    run3 = store.get_run("RUN-3")
    assert run3 is not None
    assert run3.estado is RunState.FINISHED

    run4 = store.get_run("RUN-4")
    assert run4 is not None
    assert run4.estado is RunState.FINISHED
