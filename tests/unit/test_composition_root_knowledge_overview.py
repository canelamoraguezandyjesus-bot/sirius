"""Unit tests for the composition root's B4f knowledge-overview wiring.

Confirms ``get_knowledge_overview_use_case`` is built and shares the same
underlying repositories as the rest of the application — no SQLite adapter is
exposed to a caller, only the use case (AGENTS.md: "No accedas a SQLite...
desde la interfaz").
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
from sirius.application.knowledge_overview import GetKnowledgeOverviewUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.decision import DecisionStatus
from sirius.domain.memory import MemoryStatus


def test_build_conversation_dependencies_wires_the_knowledge_overview_use_case(
    tmp_path: Path,
) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(dependencies.get_knowledge_overview_use_case, GetKnowledgeOverviewUseCase)


def test_knowledge_overview_reflects_memories_and_decisions_through_the_wired_use_case(
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
        state_summary="en curso",
        blockers=(),
        next_step="siguiente paso",
    )
    dependencies = build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )

    current_memory = dependencies.save_manual_memory_use_case.save("recuerdo vigente")
    archived_memory = dependencies.save_manual_memory_use_case.save("recuerdo a archivar")
    dependencies.archive_memory_use_case.archive(archived_memory.id)

    proposed_decision = dependencies.propose_decision_use_case.propose(
        "Asunto propuesto", project.id, "contenido propuesto"
    )
    to_approve = dependencies.propose_decision_use_case.propose(
        "Asunto aprobado", project.id, "contenido aprobado"
    )
    dependencies.approve_decision_use_case.approve(to_approve.id, confirmed=True)
    to_archive = dependencies.propose_decision_use_case.propose(
        "Asunto archivado", project.id, "contenido archivado"
    )
    dependencies.approve_decision_use_case.approve(to_archive.id, confirmed=True)
    dependencies.archive_decision_use_case.archive(to_archive.id)

    overview = dependencies.get_knowledge_overview_use_case.get_overview()

    assert [memory.id for memory in overview.current_memories] == [current_memory.id]
    assert [memory.id for memory in overview.archived_memories] == [archived_memory.id]
    assert all(memory.status is MemoryStatus.CURRENT for memory in overview.current_memories)
    assert all(memory.status is MemoryStatus.ARCHIVED for memory in overview.archived_memories)

    assert [decision.id for decision in overview.proposed_decisions] == [proposed_decision.id]
    assert [decision.id for decision in overview.current_decisions] == [to_approve.id]
    assert [decision.id for decision in overview.archived_decisions] == [to_archive.id]
    assert all(
        decision.status is DecisionStatus.PROPOSED for decision in overview.proposed_decisions
    )
    assert all(
        decision.status is DecisionStatus.APPROVED for decision in overview.current_decisions
    )
    assert all(
        decision.status is DecisionStatus.ARCHIVED for decision in overview.archived_decisions
    )
