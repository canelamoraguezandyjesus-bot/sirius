"""Integration tests for InitialProjectUseCase against real SQLite (B3a/B3c, D-02).

Demonstrates the requirement that a base created before B3a existed — which
already had ``initialize_persistence()`` seed an empty placeholder row via
``ensure_bootstrap_project()`` — stays compatible: no migration, no second
row, no data loss.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.models import ProjectModel
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.context import ContextBuilder
from sirius.application.initial_project import (
    InitialProjectAlreadyConfiguredError,
    InitialProjectUseCase,
    InvalidInitialProjectDataError,
)
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.domain.project import INITIAL_PROJECT_NEXT_STEP, INITIAL_PROJECT_STATE


def _prepare_schema(database_path: Path) -> None:
    upgrade_to_head(database_path)


def _row_count(database_path: Path) -> int:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        return len(session.scalars(select(ProjectModel)).all())


@pytest.mark.integration
def test_is_configured_is_false_right_after_bootstrap_seeds_the_placeholder(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()  # mimics initialize_persistence()
    use_case = InitialProjectUseCase(project_repository)

    assert use_case.is_configured() is False


@pytest.mark.integration
def test_create_initial_project_completes_the_historic_placeholder_without_a_second_row(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    placeholder = project_repository.get_active_project()
    assert placeholder is not None
    use_case = InitialProjectUseCase(project_repository)

    created = use_case.create_initial_project("  Mi Proyecto  ", "  Aprender Sirius  ")

    assert created.id == placeholder.id
    assert created.name == "Mi Proyecto"
    assert created.current_revision is not None
    assert created.current_revision.objective == "Aprender Sirius"
    assert created.current_revision.state_summary == INITIAL_PROJECT_STATE
    assert created.current_revision.next_step == INITIAL_PROJECT_NEXT_STEP
    assert _row_count(database_path) == 1


@pytest.mark.integration
def test_configured_project_is_recovered_after_reconstructing_repositories(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    first_repository = build_sqlite_project_repository(database_path)
    InitialProjectUseCase(first_repository).create_initial_project("Mi Proyecto", "Aprender Sirius")

    reopened_repository = build_sqlite_project_repository(database_path)
    reopened_use_case = InitialProjectUseCase(reopened_repository)

    assert reopened_use_case.is_configured() is True
    project = reopened_use_case.get_active_project()
    assert project is not None
    assert project.name == "Mi Proyecto"
    assert project.current_revision is not None
    assert project.current_revision.objective == "Aprender Sirius"
    assert project.current_revision.state_summary == INITIAL_PROJECT_STATE
    assert project.current_revision.next_step == INITIAL_PROJECT_NEXT_STEP


@pytest.mark.integration
def test_create_initial_project_rejects_empty_fields_without_touching_the_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    use_case = InitialProjectUseCase(project_repository)

    with pytest.raises(InvalidInitialProjectDataError):
        use_case.create_initial_project("   ", "Aprender Sirius")

    assert use_case.is_configured() is False
    assert _row_count(database_path) == 1


@pytest.mark.integration
def test_create_initial_project_rejects_a_second_project_and_keeps_the_first_intact(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    use_case = InitialProjectUseCase(project_repository)
    first = use_case.create_initial_project("Primero", "Objetivo original")

    with pytest.raises(InitialProjectAlreadyConfiguredError):
        use_case.create_initial_project("Segundo", "Otro objetivo")

    current = use_case.get_active_project()
    assert current is not None
    assert current.id == first.id
    assert current.name == "Primero"
    assert current.current_revision is not None
    assert current.current_revision.objective == "Objetivo original"
    assert _row_count(database_path) == 1


@pytest.mark.integration
def test_configured_project_enters_the_context_via_context_builder(tmp_path: Path) -> None:
    """The configured project (not the empty placeholder) flows into Context
    through the existing, unmodified ContextBuilder mechanism."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation_repository.get_or_create_main_conversation()
    identity_repository = build_sqlite_identity_repository(database_path)
    identity_repository.get_or_create_current_identity()
    project_repository = build_sqlite_project_repository(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)

    InitialProjectUseCase(project_repository).create_initial_project(
        "Mi Proyecto", "Aprender Sirius"
    )

    rank_relevant_knowledge_use_case = RankRelevantKnowledgeUseCase(
        memory_repository=memory_repository,
        decision_repository=decision_repository,
        project_repository=project_repository,
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
    )
    builder = ContextBuilder(
        identity_repository=identity_repository,
        project_repository=project_repository,
        memory_repository=memory_repository,
        conversation_repository=conversation_repository,
        decision_repository=decision_repository,
        rank_relevant_knowledge_use_case=rank_relevant_knowledge_use_case,
        event_repository=build_sqlite_event_repository(database_path),
        token_counter=CharacterHeuristicTokenCounter(),
    )

    context = builder.build("hola")

    assert context.project is not None
    assert context.project.name == "Mi Proyecto"
    assert context.project.current_revision is not None
    assert context.project.current_revision.objective == "Aprender Sirius"
