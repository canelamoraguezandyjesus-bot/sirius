"""Atomicity of decision archival, via ``SqliteUnitOfWork`` (B4d)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence import sqlite_decision_repository
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import Base, DecisionModel, EventModel
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_decision import ArchiveDecisionUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
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


def _row_counts(database_path: Path) -> tuple[int, int]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        events = len(session.scalars(select(EventModel)).all())
        decisions = len(session.scalars(select(DecisionModel)).all())
        return events, decisions


def _decision_status(database_path: Path, decision_id: int) -> DecisionStatus:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        model = session.get(DecisionModel, decision_id)
        assert model is not None
        return DecisionStatus(model.status)


def _create_approved_decision(database_path: Path, project_id: int) -> int:
    unit_of_work = build_sqlite_unit_of_work(database_path)
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)
    return proposed.id


@pytest.mark.integration
def test_event_and_status_change_commit_together_in_one_transaction(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    decision_id = _create_approved_decision(database_path, project_id)
    events_before, decisions_before = _row_counts(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    unit_of_work.begin()
    unit_of_work.event_repository.append("decision.archived", "user", None)

    assert _row_counts(database_path) == (events_before, decisions_before)
    assert _decision_status(database_path, decision_id) is DecisionStatus.APPROVED

    unit_of_work.decision_repository.archive_decision(decision_id)
    unit_of_work.commit()
    unit_of_work.close()

    events_after, decisions_after = _row_counts(database_path)
    assert events_after == events_before + 1
    assert decisions_after == decisions_before
    assert _decision_status(database_path, decision_id) is DecisionStatus.ARCHIVED


def _boom_archive_decision(self: object, decision_id: int) -> None:
    msg = "simulated archive failure"
    raise RuntimeError(msg)


@pytest.mark.integration
def test_archive_rolls_back_the_event_when_the_status_change_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    decision_id = _create_approved_decision(database_path, project_id)
    counts_before = _row_counts(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = ArchiveDecisionUseCase(unit_of_work)

    monkeypatch.setattr(
        sqlite_decision_repository.SqliteDecisionRepository,
        "archive_decision",
        _boom_archive_decision,
    )

    with pytest.raises(RuntimeError):
        use_case.archive(decision_id)

    assert _row_counts(database_path) == counts_before
    monkeypatch.undo()
    assert _decision_status(database_path, decision_id) is DecisionStatus.APPROVED


@pytest.mark.integration
def test_a_valid_archive_succeeds_after_a_rolled_back_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    decision_id = _create_approved_decision(database_path, project_id)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    use_case = ArchiveDecisionUseCase(unit_of_work)

    monkeypatch.setattr(
        sqlite_decision_repository.SqliteDecisionRepository,
        "archive_decision",
        _boom_archive_decision,
    )
    with pytest.raises(RuntimeError):
        use_case.archive(decision_id)

    monkeypatch.undo()
    archived = use_case.archive(decision_id)

    assert archived.status is DecisionStatus.ARCHIVED
