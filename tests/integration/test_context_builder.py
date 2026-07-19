import dataclasses
from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import (
    Base,
    ConversationModel,
    IdentityModel,
    IdentityVersionModel,
    MemoryModel,
    ProjectModel,
)
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.context import Context, ContextAssemblyError, ContextBuilder
from sirius.domain.conversation import MessageRole
from sirius.ports.decision_repository import DecisionRepository


def _prepare_schema(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


def _seed_bootstrap_singletons(
    database_path: Path,
    *,
    project_name: str = "Proyecto de prueba",
    project_objective: str = "Objetivo de prueba",
) -> None:
    """Mimic what initialize_persistence() does, plus a configured project:
    ContextBuilder (B3c) requires a configured, ``ACTIVE`` project, and never
    creates one itself — it is exercised separately against an unseeded
    database, and against an identity-only database, in the tests below.
    """
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project_repository.create_project(
        project_name,
        project_objective,
        state_summary="estado inicial",
        blockers=(),
        next_step="siguiente paso inicial",
    )
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()


def _build_context_builder(
    database_path: Path,
    recent_messages_limit: int = 20,
    *,
    decision_repository: DecisionRepository | None = None,
) -> ContextBuilder:
    return ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        memory_repository=build_sqlite_memory_repository(database_path),
        conversation_repository=build_sqlite_conversation_repository(database_path),
        decision_repository=decision_repository,
        recent_messages_limit=recent_messages_limit,
    )


def _row_counts(database_path: Path) -> dict[str, int]:
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        return {
            "conversations": len(session.scalars(select(ConversationModel)).all()),
            "projects": len(session.scalars(select(ProjectModel)).all()),
            "identities": len(session.scalars(select(IdentityModel)).all()),
            "identity_versions": len(session.scalars(select(IdentityVersionModel)).all()),
            "memories": len(session.scalars(select(MemoryModel)).all()),
        }


@pytest.mark.integration
def test_context_field_order_matches_the_defined_sections() -> None:
    assert [f.name for f in dataclasses.fields(Context)] == [
        "identity",
        "project",
        "memories",
        "recent_messages",
        "current_user_message",
    ]


@pytest.mark.integration
def test_build_on_unseeded_storage_raises_and_creates_no_rows(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    builder = _build_context_builder(database_path)

    with pytest.raises(ContextAssemblyError):
        builder.build("hola")

    assert _row_counts(database_path) == {
        "conversations": 0,
        "projects": 0,
        "identities": 0,
        "identity_versions": 0,
        "memories": 0,
    }


@pytest.mark.integration
def test_build_failure_is_clear_and_deterministic_about_the_missing_piece(
    tmp_path: Path,
) -> None:
    """The active project's absence never blocks build() (see the tests
    below) — with only the identity seeded, the next actually-required
    piece is the main conversation."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    builder = _build_context_builder(database_path)

    with pytest.raises(ContextAssemblyError, match="main conversation"):
        builder.build("hola")

    # Repeating the same call raises the exact same, deterministic error.
    with pytest.raises(ContextAssemblyError, match="main conversation"):
        builder.build("hola")


@pytest.mark.integration
def test_build_succeeds_with_no_active_project_at_all(tmp_path: Path) -> None:
    """SIRIUS-ARQ-0.1 S3 (LLMRequest.project_context: str | None): zero
    configured ACTIVE projects is a normal state, not a bootstrap failure —
    build() must never raise for this alone."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    builder = _build_context_builder(database_path)

    context = builder.build("hola")

    assert context.project is None


@pytest.mark.integration
def test_build_succeeds_with_only_the_bootstrap_placeholder(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_project_repository(database_path).ensure_bootstrap_project()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    builder = _build_context_builder(database_path)

    context = builder.build("hola")

    assert context.project is None


@pytest.mark.integration
def test_build_excludes_a_completed_project(tmp_path: Path) -> None:
    """A COMPLETED project is never recovered by ContextBuilder, and its
    absence never creates a replacement placeholder."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto cerrado",
        "objetivo",
        state_summary="estado",
        blockers=(),
        next_step="siguiente",
    )
    project_repository.complete_active_project(project.id)
    builder = _build_context_builder(database_path)

    counts_before = _row_counts(database_path)
    context = builder.build("hola")
    counts_after = _row_counts(database_path)

    assert context.project is None
    assert counts_after == counts_before  # no placeholder created as a side effect


@pytest.mark.integration
def test_build_assembles_every_section(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(
        database_path, project_name="Sirius 0.1", project_objective="cerrar V5"
    )
    builder = _build_context_builder(database_path)

    memory_repository = build_sqlite_memory_repository(database_path)
    memory_repository.create_memory("prefiere respuestas breves", "manual")

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "hola")
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, "hola de vuelta")

    context = builder.build("¿seguimos con V5?")

    assert context.identity.current_version.name == "Sirius"
    assert context.project is not None
    assert context.project.name == "Sirius 0.1"
    assert len(context.memories) == 1
    assert context.memories[0].current_revision.content == "prefiere respuestas breves"
    assert [m.content for m in context.recent_messages] == ["hola", "hola de vuelta"]
    assert context.current_user_message == "¿seguimos con V5?"


@pytest.mark.integration
def test_build_excludes_archived_and_deleted_memories(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)

    current = memory_repository.create_memory("vigente", "manual")
    archived = memory_repository.create_memory("archivada", "manual")
    memory_repository.archive_memory(archived.id)
    deleted = memory_repository.create_memory("eliminada", "manual")
    memory_repository.delete_memory(deleted.id)

    context = builder.build("hola")

    assert [m.id for m in context.memories] == [current.id]


@pytest.mark.integration
def test_recent_messages_respect_conversation_order(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "uno")
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, "dos")
    conversation_repository.append_message(conversation.id, MessageRole.USER, "tres")

    context = builder.build("cuatro")

    assert [m.content for m in context.recent_messages] == ["uno", "dos", "tres"]
    assert [m.sequence for m in context.recent_messages] == [1, 2, 3]


@pytest.mark.integration
def test_recent_messages_are_capped_to_the_configured_limit(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path, recent_messages_limit=2)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "uno")
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, "dos")
    conversation_repository.append_message(conversation.id, MessageRole.USER, "tres")

    context = builder.build("cuatro")

    assert [m.content for m in context.recent_messages] == ["dos", "tres"]


@pytest.mark.integration
def test_context_includes_traceable_identifiers(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    memory = memory_repository.create_memory("recordatorio", "manual")

    context = builder.build("hola")

    assert context.identity.current_version.version >= 1
    assert context.project is not None
    assert context.project.id is not None
    assert context.memories[0].id == memory.id
    assert context.memories[0].current_revision.version == 1


@pytest.mark.integration
def test_build_does_not_modify_data_and_is_deterministic(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    memory_repository.create_memory("recordatorio", "manual")

    counts_before = _row_counts(database_path)
    first = builder.build("misma entrada")
    second = builder.build("misma entrada")
    counts_after = _row_counts(database_path)

    assert first == second
    assert counts_after == counts_before


@pytest.mark.integration
def test_build_after_bootstrap_does_not_change_any_row_count(tmp_path: Path) -> None:
    """Requirement: after bootstrap, building context leaves every count unchanged."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path)

    counts_before = _row_counts(database_path)
    builder.build("hola")
    builder.build("otra vez")
    counts_after = _row_counts(database_path)

    assert counts_after == counts_before


@pytest.mark.integration
def test_build_without_a_decision_repository_never_excludes_conflicting_memories(
    tmp_path: Path,
) -> None:
    """B4e: omitting ``decision_repository`` (the default) leaves build()
    byte-for-byte identical to pre-B4e behaviour — even memories that would
    otherwise conflict stay in context, since there is nothing available to
    resolve them against."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)

    first = memory_repository.create_memory(
        "responder breve", "manual", subject_key="tono", project_id=1
    )
    second = memory_repository.create_memory(
        "responder extenso", "manual", subject_key="tono", project_id=1
    )

    context = builder.build("hola")

    assert {m.id for m in context.memories} == {first.id, second.id}


@pytest.mark.integration
def test_build_excludes_a_conflicting_group_when_a_decision_repository_is_given(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    builder = _build_context_builder(database_path, decision_repository=decision_repository)

    conflicting_first = memory_repository.create_memory(
        "responder breve", "manual", subject_key="tono", project_id=1
    )
    conflicting_second = memory_repository.create_memory(
        "responder extenso", "manual", subject_key="tono", project_id=1
    )
    uncontested = memory_repository.create_memory("prefiere el idioma español", "manual")

    context = builder.build("hola")

    memory_ids = {m.id for m in context.memories}
    assert conflicting_first.id not in memory_ids
    assert conflicting_second.id not in memory_ids
    assert uncontested.id in memory_ids


@pytest.mark.integration
def test_build_keeps_a_memory_settled_by_an_approved_decision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    builder = _build_context_builder(database_path, decision_repository=decision_repository)

    settled_first = memory_repository.create_memory(
        "responder breve", "manual", subject_key="tono", project_id=1
    )
    settled_second = memory_repository.create_memory(
        "responder extenso", "manual", subject_key="tono", project_id=1
    )
    proposal = decision_repository.create_proposal("tono", 1, "responder siempre breve")
    decision_repository.approve_decision(proposal.id)

    context = builder.build("hola")

    memory_ids = {m.id for m in context.memories}
    assert settled_first.id in memory_ids
    assert settled_second.id in memory_ids


@pytest.mark.integration
def test_build_different_subject_keys_never_conflict_with_each_other(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    builder = _build_context_builder(database_path, decision_repository=decision_repository)

    tone = memory_repository.create_memory(
        "responder breve", "manual", subject_key="tono", project_id=1
    )
    path = memory_repository.create_memory(
        "usar ruta personalizada", "manual", subject_key="ruta de datos", project_id=1
    )

    context = builder.build("hola")

    assert {m.id for m in context.memories} == {tone.id, path.id}
