"""Reintento y sustitución de Worker (incidencia #177, requisitos 5-6).

Ambos crean un Run nuevo con el intento incrementado y nunca mutan el Run
anterior (arquitectura §3.2, §3.3: "Un Run nunca resucita").
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sirius_engine.domain.errors import IllegalTransitionError
from sirius_engine.domain.run import RunOutcome, RunState
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeRun


def test_retry_creates_a_new_run_with_incremented_attempt(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=1)
    original = make_run(run_id="RUN-1", now=now, deadline=deadline)
    store.dispatch_run("RUN-1", now=now)
    store.confirm_run_running("RUN-1", now=now)
    failed_original = store.fail_run("RUN-1", diagnostico="timeout de red", now=now)
    assert failed_original.intento == 1

    retried = store.retry_run(
        "RUN-1", new_run_id="RUN-2", deadline=deadline + timedelta(hours=1), now=now
    )

    assert retried.run_id == "RUN-2"
    assert retried.intento == 2
    assert retried.estado is RunState.PREPARED
    assert retried.paso == original.paso
    assert retried.work_id == original.work_id
    assert retried.worker == original.worker

    # The previous run's history is untouched by the retry.
    still_failed = store.get_run("RUN-1")
    assert still_failed is not None
    assert still_failed.estado is RunState.FINISHED
    assert still_failed.desenlace is RunOutcome.FAILED
    assert still_failed.intento == 1


def test_retry_requires_the_previous_run_to_have_finished(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-1", now=now, deadline=deadline)
    store.dispatch_run("RUN-1", now=now)  # still DISPATCHED, not FINISHED

    with pytest.raises(IllegalTransitionError):
        store.retry_run("RUN-1", new_run_id="RUN-2", deadline=deadline, now=now)


def test_third_attempt_keeps_incrementing_from_the_latest_retry(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-1", now=now, deadline=deadline)
    store.dispatch_run("RUN-1", now=now)
    store.fail_run("RUN-1", diagnostico="primer fallo", now=now)
    store.retry_run("RUN-1", new_run_id="RUN-2", deadline=deadline, now=now)
    store.dispatch_run("RUN-2", now=now)
    store.fail_run("RUN-2", diagnostico="segundo fallo", now=now)

    third = store.retry_run("RUN-2", new_run_id="RUN-3", deadline=deadline, now=now)
    assert third.intento == 3


# -- Requisito 6: sustitución de Worker -------------------------------------------------


def test_worker_substitution_creates_a_new_run_recording_the_motive(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-1", now=now, deadline=deadline, worker="claude-code")
    store.dispatch_run("RUN-1", now=now)
    store.fail_run("RUN-1", diagnostico="el Worker no responde", now=now)

    substituted = store.substitute_run_worker(
        "RUN-1",
        new_run_id="RUN-2",
        worker="codex",
        motivo="claude-code dejó de responder tras dos intentos",
        deadline=deadline + timedelta(hours=1),
        now=now,
    )

    assert substituted.run_id == "RUN-2"
    assert substituted.worker == "codex"
    assert substituted.intento == 2
    assert substituted.sustituye_a == "RUN-1"
    assert substituted.motivo_sustitucion == "claude-code dejó de responder tras dos intentos"
    assert substituted.estado is RunState.PREPARED

    # The previous run — including its original worker — is untouched.
    original = store.get_run("RUN-1")
    assert original is not None
    assert original.worker == "claude-code"
    assert original.estado is RunState.FINISHED


def test_worker_substitution_requires_a_different_worker(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-1", now=now, deadline=deadline, worker="claude-code")
    store.dispatch_run("RUN-1", now=now)
    store.fail_run("RUN-1", diagnostico="fallo", now=now)

    with pytest.raises(ValueError, match="different worker"):
        store.substitute_run_worker(
            "RUN-1",
            new_run_id="RUN-2",
            worker="claude-code",
            motivo="motivo inválido",
            deadline=deadline,
            now=now,
        )
