"""Unit tests for the composition root's B4b wiring.

Confirms ``propose_decision_use_case``, ``approve_decision_use_case`` and
``get_decision_origin_use_case`` are built and share the same underlying
``UnitOfWork``/repositories as the rest of the application — no SQLite
adapter is exposed to a caller, only the use cases (AGENTS.md: "No accedas a
SQLite... desde la interfaz").
"""

from __future__ import annotations

from pathlib import Path

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.decision_origin import GetDecisionOriginUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.decision import DecisionStatus


def test_build_conversation_dependencies_wires_decision_use_cases(tmp_path: Path) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(dependencies.propose_decision_use_case, ProposeDecisionUseCase)
    assert isinstance(dependencies.approve_decision_use_case, ApproveDecisionUseCase)
    assert isinstance(dependencies.get_decision_origin_use_case, GetDecisionOriginUseCase)


def test_proposed_and_approved_decision_is_queryable_through_the_wired_use_cases(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="En curso",
        blockers=(),
        next_step="Siguiente paso",
    )
    dependencies = build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )

    proposed = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project.id, "Usar SQLite local"
    )
    assert proposed.status is DecisionStatus.PROPOSED

    approved = dependencies.approve_decision_use_case.approve(proposed.id, confirmed=True)
    assert approved.status is DecisionStatus.APPROVED

    origin = dependencies.get_decision_origin_use_case.get_origin(proposed.id)

    assert origin.subject == "Motor de persistencia"
    assert origin.project_id == project.id
    assert origin.status is DecisionStatus.APPROVED
