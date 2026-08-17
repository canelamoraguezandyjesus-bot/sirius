"""Cancelación de Run en dos tiempos (arquitectura §3.3, incidencia #177 requisitos 3-4).

Requisito 3: tras ``CANCEL``, el Run queda en cancelación no confirmada y
NO es ``CANCELLED`` sin terminal remoto o aislamiento demostrado. Requisito
4: con una cancelación no confirmada sobre un recurso mutable, no se admite
un despacho nuevo incompatible sobre ese mismo recurso.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sirius_engine.domain.errors import IllegalTransitionError, MutableResourceConflictError
from sirius_engine.domain.run import CancellationStatus, RunOutcome, RunState
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeRun


def test_cancel_requested_is_not_cancelled_until_confirmed(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    run_id = "RUN-CANCEL-UNCONFIRMED"
    make_run(run_id=run_id, now=now, deadline=now + timedelta(hours=1))
    store.dispatch_run(run_id, now=now)
    store.confirm_run_running(run_id, now=now)

    requested = store.request_run_cancellation(run_id, now=now)
    assert requested.cancellation_status is CancellationStatus.UNCONFIRMED
    assert requested.estado is RunState.RUNNING, "still live: not CANCELLED by the request alone"
    assert requested.desenlace is None

    # The supervisor keeps reconciling: nothing terminal happened on its own.
    fetched = store.get_run(run_id)
    assert fetched is not None
    assert fetched.estado is RunState.RUNNING
    assert fetched.cancellation_status is CancellationStatus.UNCONFIRMED


def test_run_only_becomes_cancelled_after_explicit_confirmation(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    run_id = "RUN-CANCEL-CONFIRMED"
    make_run(run_id=run_id, now=now, deadline=now + timedelta(hours=1))
    store.dispatch_run(run_id, now=now)
    store.confirm_run_running(run_id, now=now)
    store.request_run_cancellation(run_id, now=now)

    confirmed = store.confirm_run_cancelled(run_id, now=now)
    assert confirmed.estado is RunState.FINISHED
    assert confirmed.desenlace is RunOutcome.CANCELLED


def test_confirm_cancelled_without_a_prior_request_is_illegal(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    run_id = "RUN-CANCEL-NO-REQUEST"
    make_run(run_id=run_id, now=now, deadline=now + timedelta(hours=1))
    store.dispatch_run(run_id, now=now)
    store.confirm_run_running(run_id, now=now)

    with pytest.raises(IllegalTransitionError):
        store.confirm_run_cancelled(run_id, now=now)


def test_the_mere_passage_of_time_never_confirms_a_cancellation(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    """A Run stays UNCONFIRMED however long it waits: only an explicit confirmation closes it."""
    run_id = "RUN-CANCEL-NO-AUTO-CONFIRM"
    make_run(run_id=run_id, now=now, deadline=now + timedelta(hours=1))
    store.dispatch_run(run_id, now=now)
    store.request_run_cancellation(run_id, now=now)

    much_later = now + timedelta(days=30)
    fetched = store.get_run(run_id)
    assert fetched is not None
    assert fetched.cancellation_status is CancellationStatus.UNCONFIRMED
    assert fetched.estado is RunState.DISPATCHED

    # Explicit confirmation still required, no matter how much time passed.
    confirmed = store.confirm_run_cancelled(run_id, now=much_later)
    assert confirmed.desenlace is RunOutcome.CANCELLED


# -- Requisito 4: recurso mutable protegido -------------------------------------------


def test_dispatch_rejected_while_another_run_has_unconfirmed_cancellation_on_same_resource(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    resource = "pr:owner/repo#42"
    deadline = now + timedelta(hours=1)

    make_run(
        run_id="RUN-A-CANCEL-PENDING",
        work_id="WI-SHARED",
        now=now,
        deadline=deadline,
        recurso_mutable=resource,
    )
    store.dispatch_run("RUN-A-CANCEL-PENDING", now=now)
    store.request_run_cancellation("RUN-A-CANCEL-PENDING", now=now)

    make_run(
        run_id="RUN-B-NEW-ATTEMPT",
        work_id="WI-SHARED",
        now=now,
        deadline=deadline,
        recurso_mutable=resource,
    )

    with pytest.raises(MutableResourceConflictError) as excinfo:
        store.dispatch_run("RUN-B-NEW-ATTEMPT", now=now)
    assert excinfo.value.recurso_mutable == resource
    assert excinfo.value.conflicting_run_id == "RUN-A-CANCEL-PENDING"

    # The dispatcher rejected it: the new run must still be sitting in PREPARED.
    fetched = store.get_run("RUN-B-NEW-ATTEMPT")
    assert fetched is not None
    assert fetched.estado is RunState.PREPARED


def test_dispatch_allowed_on_a_different_mutable_resource(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=1)
    make_run(
        run_id="RUN-A-CANCEL-PENDING",
        work_id="WI-SHARED",
        now=now,
        deadline=deadline,
        recurso_mutable="pr:owner/repo#42",
    )
    store.dispatch_run("RUN-A-CANCEL-PENDING", now=now)
    store.request_run_cancellation("RUN-A-CANCEL-PENDING", now=now)

    make_run(
        run_id="RUN-B-OTHER-RESOURCE",
        work_id="WI-SHARED",
        now=now,
        deadline=deadline,
        recurso_mutable="pr:owner/repo#99",
    )

    dispatched = store.dispatch_run("RUN-B-OTHER-RESOURCE", now=now)
    assert dispatched.estado is RunState.DISPATCHED


def test_dispatch_allowed_once_the_prior_cancellation_is_confirmed(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    resource = "pr:owner/repo#42"
    deadline = now + timedelta(hours=1)

    make_run(
        run_id="RUN-A-CANCEL-PENDING",
        work_id="WI-SHARED",
        now=now,
        deadline=deadline,
        recurso_mutable=resource,
    )
    store.dispatch_run("RUN-A-CANCEL-PENDING", now=now)
    store.request_run_cancellation("RUN-A-CANCEL-PENDING", now=now)
    store.confirm_run_cancelled("RUN-A-CANCEL-PENDING", now=now)

    make_run(
        run_id="RUN-B-NEW-ATTEMPT",
        work_id="WI-SHARED",
        now=now,
        deadline=deadline,
        recurso_mutable=resource,
    )

    dispatched = store.dispatch_run("RUN-B-NEW-ATTEMPT", now=now)
    assert dispatched.estado is RunState.DISPATCHED
