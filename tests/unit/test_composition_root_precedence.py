"""Unit tests for the composition root's B4e wiring.

Confirms ``detect_precedence_conflicts_use_case`` is built and shares the
same underlying repositories as the rest of the application — no SQLite
adapter is exposed to a caller, only the use case (AGENTS.md: "No accedas a
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
from sirius.application.detect_precedence_conflicts import DetectPrecedenceConflictsUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.precedence import PrecedenceOutcome


def test_build_conversation_dependencies_wires_the_precedence_use_case(tmp_path: Path) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(
        dependencies.detect_precedence_conflicts_use_case, DetectPrecedenceConflictsUseCase
    )


def test_precedence_conflicts_are_detectable_through_the_wired_use_case(tmp_path: Path) -> None:
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

    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project.id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto",
        subject_key="Motor de persistencia",
        project_id=project.id,
    )

    conflicts = dependencies.detect_precedence_conflicts_use_case.detect()

    assert len(conflicts) == 1
    assert conflicts[0].subject_key == "Motor de persistencia"
    assert conflicts[0].project_id == project.id
    assert conflicts[0].outcome is PrecedenceOutcome.CONFLICT
    assert len(conflicts[0].conflicting_memories) == 2


def test_an_approved_decision_resolves_a_previously_conflicting_subject(tmp_path: Path) -> None:
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
    dependencies.save_manual_memory_use_case.save(
        "usar SQLite local", subject_key="Motor de persistencia", project_id=project.id
    )
    dependencies.save_manual_memory_use_case.save(
        "usar un servidor remoto",
        subject_key="Motor de persistencia",
        project_id=project.id,
    )

    proposed = dependencies.propose_decision_use_case.propose(
        "Motor de persistencia", project.id, "Usar SQLite local"
    )
    dependencies.approve_decision_use_case.approve(proposed.id, confirmed=True)

    conflicts = dependencies.detect_precedence_conflicts_use_case.detect()

    assert conflicts == ()
