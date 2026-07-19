"""Unit tests for the composition root's B4e wiring.

Confirms ``evaluate_memory_precedence_use_case`` is built and shares the
same underlying repositories as the rest of the application (AGENTS.md:
"No accedas a SQLite... desde la interfaz"), and that the minimal
connection into ``ContextBuilder`` (also wired here) actually excludes an
unresolved conflict from an assembled ``Context`` while leaving a
decision-settled memory in place.
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
from sirius.application.context import ContextBuilder
from sirius.application.memory_precedence import EvaluateMemoryPrecedenceUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.knowledge_precedence import PrecedenceOutcome


def _bootstrap(tmp_path: Path) -> Path:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    return database_path


def test_build_conversation_dependencies_wires_the_precedence_use_case(tmp_path: Path) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(
        dependencies.evaluate_memory_precedence_use_case, EvaluateMemoryPrecedenceUseCase
    )
    assert isinstance(dependencies.send_message_use_case._context_builder, ContextBuilder)


def test_two_incompatible_memories_on_the_same_subject_are_reported_as_a_conflict(
    tmp_path: Path,
) -> None:
    database_path = _bootstrap(tmp_path)
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

    dependencies.save_manual_memory_use_case.save(
        "Responder de forma breve", subject_key="tono", project_id=project.id
    )
    dependencies.save_manual_memory_use_case.save(
        "Responder de forma extensa", subject_key="tono", project_id=project.id
    )

    resolution = dependencies.evaluate_memory_precedence_use_case.evaluate("tono", project.id)

    assert resolution.outcome is PrecedenceOutcome.CONFLICT
    assert resolution.conflict is not None
    assert len(resolution.conflict.memories) == 2


def test_an_approved_decision_prevails_over_incompatible_memories_through_the_wired_use_cases(
    tmp_path: Path,
) -> None:
    database_path = _bootstrap(tmp_path)
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

    dependencies.save_manual_memory_use_case.save(
        "Responder de forma breve", subject_key="tono", project_id=project.id
    )
    dependencies.save_manual_memory_use_case.save(
        "Responder de forma extensa", subject_key="tono", project_id=project.id
    )
    proposed = dependencies.propose_decision_use_case.propose(
        "tono", project.id, "Responder siempre de forma breve"
    )
    approved = dependencies.approve_decision_use_case.approve(proposed.id, confirmed=True)

    resolution = dependencies.evaluate_memory_precedence_use_case.evaluate("tono", project.id)

    assert resolution.outcome is PrecedenceOutcome.DECISION_PREVAILS
    assert resolution.prevailing_decision is not None
    assert resolution.prevailing_decision.id == approved.id


def test_a_conflicting_memory_group_is_excluded_from_the_assembled_context(
    tmp_path: Path,
) -> None:
    database_path = _bootstrap(tmp_path)
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

    conflicting_one = dependencies.save_manual_memory_use_case.save(
        "Responder de forma breve", subject_key="tono", project_id=project.id
    )
    conflicting_two = dependencies.save_manual_memory_use_case.save(
        "Responder de forma extensa", subject_key="tono", project_id=project.id
    )
    uncontested = dependencies.save_manual_memory_use_case.save("Prefiere el idioma español")

    result = dependencies.send_message_use_case.send_message("hola")

    memory_ids = {memory.id for memory in result.context.memories}
    assert conflicting_one.id not in memory_ids
    assert conflicting_two.id not in memory_ids
    assert uncontested.id in memory_ids
