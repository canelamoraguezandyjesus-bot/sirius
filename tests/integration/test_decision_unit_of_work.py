"""Atomicity of decision proposal and approval, via ``SqliteUnitOfWork`` (B4b).

SIRIUS-ARQ-0.1 S4/S8.1 require the event and the change to the decision to
share one transaction — B4b extends the same guarantee B4a already proved
for memory to decisions. These tests exercise it directly against the real
SQLite adapters (no fakes): the event, the decision, and its first revision
commit together or not at all; approving an event and a status change commit
together or not at all; a mid-transaction failure at any write point leaves
the database exactly as it was before the attempt; and a following valid
attempt still succeeds.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence import sqlite_decision_repository
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import (
    Base,
    DecisionModel,
    DecisionRevisionModel,
    EventModel,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.supersede_decision import SupersedeDecisionUseCase
from sirius.domain.decision import DecisionStatus


def _bootstrap(database_path: Path) -> int:
    Base.metadata.create_all(build_engine(database_path))
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="En curso",
        blockers=(),
        next_step="Siguiente paso",
    )
    return project.id


def _row_counts(database_path: Path) -> tuple[int, int, int]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        events = len(session.scalars(select(EventModel)).all())
        decisions = len(session.scalars(select(DecisionModel)).all())
        revisions = len(session.scalars(select(DecisionRevisionModel)).all())
        return events, decisions, revisions


@pytest.mark.integration
def test_event_decision_and_revision_commit_together_in_one_transaction(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    unit_of_work.begin()
    event = unit_of_work.event_repository.append("decision.proposed", "user", None)
    unit_of_work.decision_repository.create_proposal(
        "Motor de persistencia", project_id, "Usar SQLite local", source_event_id=event.id
    )

    # Nothing is visible from an independent connection before commit: both
    # writes live in the same, still-open transaction.
    events_before, decisions_before, revisions_before = _row_counts(database_path)
    assert (events_before, decisions_before, revisions_before) == (0, 0, 0)

    unit_of_work.commit()
    unit_of_work.close()

    assert _row_counts(database_path) == (1, 1, 1)


@pytest.mark.integration
def test_propose_rolls_back_the_event_when_decision_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = ProposeDecisionUseCase(unit_of_work)

    def _boom(subject: str) -> None:
        msg = "simulated decision-creation failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(sqlite_decision_repository, "ensure_valid_subject", _boom)

    with pytest.raises(RuntimeError):
        use_case.propose("Motor de persistencia", project_id, "no debería persistir")

    assert _row_counts(database_path) == (0, 0, 0)


@pytest.mark.integration
def test_propose_rolls_back_everything_when_revision_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = ProposeDecisionUseCase(unit_of_work)

    class _FailingRevisionModel:
        def __init__(self, *args: object, **kwargs: object) -> None:
            msg = "simulated revision-creation failure"
            raise RuntimeError(msg)

    monkeypatch.setattr(sqlite_decision_repository, "DecisionRevisionModel", _FailingRevisionModel)

    with pytest.raises(RuntimeError):
        use_case.propose("Motor de persistencia", project_id, "cuya revisión nunca persiste")

    # The event and the decision row were both written inside the same
    # not-yet-committed transaction as the failed revision write; none of
    # the three may survive.
    assert _row_counts(database_path) == (0, 0, 0)


@pytest.mark.integration
def test_a_valid_proposal_succeeds_after_a_rolled_back_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = ProposeDecisionUseCase(unit_of_work)

    def _boom(subject: str) -> None:
        msg = "simulated decision-creation failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(sqlite_decision_repository, "ensure_valid_subject", _boom)
    with pytest.raises(RuntimeError):
        use_case.propose("Motor de persistencia", project_id, "primer intento, falla")

    monkeypatch.undo()
    decision = use_case.propose("Motor de persistencia", project_id, "segundo intento, correcto")

    assert decision.current_revision.content == "segundo intento, correcto"
    assert _row_counts(database_path) == (1, 1, 1)


@pytest.mark.integration
def test_approve_rolls_back_the_event_and_status_change_together_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    events_after_proposal, _, _ = _row_counts(database_path)

    approve_use_case = ApproveDecisionUseCase(unit_of_work)

    def _boom(self: object, decision_id: int) -> None:
        msg = "simulated approval failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        sqlite_decision_repository.SqliteDecisionRepository, "approve_decision", _boom
    )

    with pytest.raises(RuntimeError):
        approve_use_case.approve(proposed.id, confirmed=True)

    monkeypatch.undo()

    # The approval event must not have survived; the decision must still be
    # PROPOSED, exactly as it was before the failed approval attempt.
    events_after_failed_approve, _, _ = _row_counts(database_path)
    assert events_after_failed_approve == events_after_proposal

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        model = session.get(DecisionModel, proposed.id)
        assert model is not None
        assert model.status is DecisionStatus.PROPOSED


@pytest.mark.integration
def test_a_valid_approval_succeeds_after_a_rolled_back_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    approve_use_case = ApproveDecisionUseCase(unit_of_work)

    def _boom(self: object, decision_id: int) -> None:
        msg = "simulated approval failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        sqlite_decision_repository.SqliteDecisionRepository, "approve_decision", _boom
    )
    with pytest.raises(RuntimeError):
        approve_use_case.approve(proposed.id, confirmed=True)

    monkeypatch.undo()
    approved = approve_use_case.approve(proposed.id, confirmed=True)

    assert approved.status is DecisionStatus.APPROVED


@pytest.mark.integration
def test_supersede_rolls_back_the_event_and_both_status_changes_together_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    original = ApproveDecisionUseCase(unit_of_work).approve(
        ProposeDecisionUseCase(unit_of_work)
        .propose("Motor de persistencia", project_id, "Usar SQLite local")
        .id,
        confirmed=True,
    )
    substitute = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )
    events_before, _, _ = _row_counts(database_path)

    supersede_use_case = SupersedeDecisionUseCase(unit_of_work)

    def _boom(self: object, superseded_decision_id: int, superseding_decision_id: int) -> None:
        msg = "simulated supersession failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        sqlite_decision_repository.SqliteDecisionRepository, "supersede_decision", _boom
    )

    with pytest.raises(RuntimeError):
        supersede_use_case.supersede(original.id, substitute.id, confirmed=True)

    monkeypatch.undo()

    events_after_failed_supersede, _, _ = _row_counts(database_path)
    assert events_after_failed_supersede == events_before

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        original_model = session.get(DecisionModel, original.id)
        substitute_model = session.get(DecisionModel, substitute.id)
        assert original_model is not None
        assert substitute_model is not None
        assert original_model.status is DecisionStatus.APPROVED
        assert substitute_model.status is DecisionStatus.PROPOSED
        assert substitute_model.supersedes_decision_id is None


@pytest.mark.integration
def test_a_valid_supersession_succeeds_after_a_rolled_back_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    original = ApproveDecisionUseCase(unit_of_work).approve(
        ProposeDecisionUseCase(unit_of_work)
        .propose("Motor de persistencia", project_id, "Usar SQLite local")
        .id,
        confirmed=True,
    )
    substitute = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )
    supersede_use_case = SupersedeDecisionUseCase(unit_of_work)

    def _boom(self: object, superseded_decision_id: int, superseding_decision_id: int) -> None:
        msg = "simulated supersession failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        sqlite_decision_repository.SqliteDecisionRepository, "supersede_decision", _boom
    )
    with pytest.raises(RuntimeError):
        supersede_use_case.supersede(original.id, substitute.id, confirmed=True)

    monkeypatch.undo()
    result = supersede_use_case.supersede(original.id, substitute.id, confirmed=True)

    assert result.status is DecisionStatus.APPROVED
    assert result.supersedes_decision_id == original.id
