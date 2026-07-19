"""End-to-end integration tests for B4d decision archival (RF-024, PA-015).

Wires the real SQLite adapters (no fakes) behind ``ProposeDecisionUseCase``,
``ApproveDecisionUseCase``, ``ArchiveDecisionUseCase`` and
``GetDecisionOriginUseCase`` exactly as ``composition_root`` does, mirroring
``test_memory_archive_delete_lifecycle.py`` for the decision side.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_decision import (
    ArchiveDecisionUseCase,
    DecisionNotArchivableError,
    UnknownDecisionError,
)
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


@pytest.mark.integration
def test_archiving_an_approved_decision_keeps_content_but_leaves_ordinary_queries(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)

    archived = ArchiveDecisionUseCase(unit_of_work).archive(proposed.id)

    assert archived.status is DecisionStatus.ARCHIVED
    assert archived.current_revision.content == "Usar SQLite local"

    fetched = decision_repository.get_decision(proposed.id)
    assert fetched.current_revision.content == "Usar SQLite local"

    assert proposed.id not in [d.id for d in decision_repository.list_current_decisions()]
    assert [d.id for d in decision_repository.list_archived_decisions()] == [proposed.id]


@pytest.mark.integration
def test_archiving_an_unknown_decision_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    with pytest.raises(UnknownDecisionError):
        ArchiveDecisionUseCase(unit_of_work).archive(999)


@pytest.mark.integration
def test_archiving_a_still_proposed_decision_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )

    with pytest.raises(DecisionNotArchivableError):
        ArchiveDecisionUseCase(unit_of_work).archive(proposed.id)

    decision_repository = build_sqlite_decision_repository(database_path)
    assert decision_repository.get_decision(proposed.id).status is DecisionStatus.PROPOSED


@pytest.mark.integration
def test_an_ordinary_conversation_never_archives_a_decision_or_memory_on_its_own(
    tmp_path: Path,
) -> None:
    """PA-015's implicit negative case, mirroring PA-010/PA-011: nothing in
    ``ProposeDecisionUseCase``/``ApproveDecisionUseCase`` (the only decision
    write paths a conversation could reach) ever calls
    ``ArchiveDecisionUseCase``."""
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)

    decision_repository = build_sqlite_decision_repository(database_path)
    assert decision_repository.get_decision(proposed.id).status is DecisionStatus.APPROVED
    assert decision_repository.list_archived_decisions() == []


@pytest.mark.integration
def test_archived_decision_survives_closing_and_reopening_the_store(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)
    ArchiveDecisionUseCase(unit_of_work).archive(proposed.id)

    decision_repository.close()
    unit_of_work.close()

    reopened = build_sqlite_decision_repository(database_path)
    fetched = reopened.get_decision(proposed.id)
    assert fetched.status is DecisionStatus.ARCHIVED
    assert fetched.current_revision.content == "Usar SQLite local"
    assert [d.id for d in reopened.list_archived_decisions()] == [proposed.id]
