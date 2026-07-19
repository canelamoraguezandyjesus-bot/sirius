"""Unit tests for the composition root's B4d wiring.

Confirms ``archive_memory_use_case``, ``delete_memory_use_case`` and
``archive_decision_use_case`` are built and share the same underlying
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
from sirius.application.archive_decision import ArchiveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.delete_memory import DeleteMemoryUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.conversation import SourceMessageChoice
from sirius.domain.decision import DecisionStatus
from sirius.domain.memory import MemoryStatus


def test_build_conversation_dependencies_wires_archive_and_delete_use_cases(
    tmp_path: Path,
) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(dependencies.archive_memory_use_case, ArchiveMemoryUseCase)
    assert isinstance(dependencies.delete_memory_use_case, DeleteMemoryUseCase)
    assert isinstance(dependencies.archive_decision_use_case, ArchiveDecisionUseCase)


def test_a_saved_memory_can_be_archived_and_deleted_through_the_wired_use_cases(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    dependencies = build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )

    memory = dependencies.save_manual_memory_use_case.save("El usuario prefiere brevedad")
    archived = dependencies.archive_memory_use_case.archive(memory.id)
    assert archived.status is MemoryStatus.ARCHIVED

    result = dependencies.delete_memory_use_case.delete(
        memory.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )
    assert result.memory.status is MemoryStatus.DELETED
    assert result.memory.current_revision.content is None


def test_an_approved_decision_can_be_archived_through_the_wired_use_case(tmp_path: Path) -> None:
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
    dependencies.approve_decision_use_case.approve(proposed.id, confirmed=True)

    archived = dependencies.archive_decision_use_case.archive(proposed.id)

    assert archived.status is DecisionStatus.ARCHIVED
    assert archived.current_revision.content == "Usar SQLite local"
