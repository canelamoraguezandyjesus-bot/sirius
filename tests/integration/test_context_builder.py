import dataclasses
from collections.abc import Sequence
from pathlib import Path

import pytest
from sqlalchemy import select, text

from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.models import (
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
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.context import Context, ContextAssemblyError, ContextBuilder
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.domain.conversation import MessageRole
from sirius.domain.identity import (
    INITIAL_IDENTITY_DESCRIPTION,
    INITIAL_IDENTITY_NAME,
    INITIAL_PERSONALITY_INSTRUCTIONS,
)
from sirius.domain.project import blockers_to_text
from sirius.domain.relevance import RankedKnowledge
from sirius.ports.relevance_filter import RelevanceFilterPort


def _prepare_schema(database_path: Path) -> None:
    # B6d: ContextBuilder now depends on knowledge_fts (B6a) through B6b's
    # relevance ranking, so the real Alembic migration must run — the plain
    # Base.metadata.create_all() this used before never creates the
    # hand-written FTS5 virtual tables/triggers.
    upgrade_to_head(database_path)


def _seed_bootstrap_singletons(
    database_path: Path,
    *,
    project_name: str = "Proyecto de prueba",
    project_objective: str = "Objetivo de prueba",
) -> int:
    """Mimic what initialize_persistence() does, plus a configured project:
    ContextBuilder (B3c) requires a configured, ``ACTIVE`` project, and never
    creates one itself — it is exercised separately against an unseeded
    database, and against an identity-only database, in the tests below.

    Returns the created project's id, so B4e tests can associate a memory or
    a decision with it.
    """
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        project_name,
        project_objective,
        state_summary="estado inicial",
        blockers=(),
        next_step="siguiente paso inicial",
    )
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    return project.id


def _build_context_builder(
    database_path: Path,
    recent_messages_limit: int = 20,
    *,
    token_budget: int = 12000,
    max_knowledge_items: int = 12,
    relevance_filter_port: RelevanceFilterPort | None = None,
    max_criticality_category: str | None = None,
) -> ContextBuilder:
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    rank_relevant_knowledge_use_case = RankRelevantKnowledgeUseCase(
        memory_repository=memory_repository,
        decision_repository=decision_repository,
        project_repository=project_repository,
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
    )
    return ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=project_repository,
        memory_repository=memory_repository,
        conversation_repository=build_sqlite_conversation_repository(database_path),
        decision_repository=decision_repository,
        rank_relevant_knowledge_use_case=rank_relevant_knowledge_use_case,
        event_repository=build_sqlite_event_repository(database_path),
        token_counter=CharacterHeuristicTokenCounter(),
        recent_messages_limit=recent_messages_limit,
        token_budget=token_budget,
        max_knowledge_items=max_knowledge_items,
        relevance_filter_port=relevance_filter_port,
        max_criticality_category=max_criticality_category,
    )


def _set_updated_at(database_path: Path, row_id: int, updated_at: str) -> None:
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE memories SET updated_at = :updated_at WHERE id = :id"),
            {"updated_at": updated_at, "id": row_id},
        )


class _ExcludeAllRelevanceFilterPort:
    """Test double for RelevanceFilterPort (§8-M10): discards every
    candidate it sees, standing in for whatever destructive verdict a real
    Ollama response might produce — proves the candado actually adds
    candidates back, never a lenient double that happens to keep them."""

    def filter_candidates(
        self, query_text: str, candidates: Sequence[RankedKnowledge]
    ) -> Sequence[RankedKnowledge]:
        return ()


class _FailOpenRelevanceFilterPort:
    """Test double standing in for an adapter that already failed open
    (§6.3 scenarios (ii)-(iv): not installed/connection refused, timed out,
    malformed response) — its contract-mandated answer to any internal
    problem is ``candidates`` unmodified."""

    def filter_candidates(
        self, query_text: str, candidates: Sequence[RankedKnowledge]
    ) -> Sequence[RankedKnowledge]:
        return candidates


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
        "decisions",
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
    project_id = _seed_bootstrap_singletons(
        database_path, project_name="Sirius 0.1", project_objective="cerrar V5"
    )
    builder = _build_context_builder(database_path)

    memory_repository = build_sqlite_memory_repository(database_path)
    memory_repository.create_memory("prefiere respuestas breves", "manual")
    decision_repository = build_sqlite_decision_repository(database_path)
    decision = decision_repository.create_proposal(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    decision_repository.approve_decision(decision.id)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "hola")
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, "hola de vuelta")

    # A query whose tokens hit both the memory's and the decision's indexed
    # content (B6a/B6b): only a *pertinent* query is expected to surface them.
    context = builder.build("¿prefieres respuestas breves sobre SQLite?")

    assert context.identity.current_version.name == "Sirius"
    assert context.project is not None
    assert context.project.name == "Sirius 0.1"
    assert len(context.decisions) == 1
    assert context.decisions[0].id == decision.id
    assert len(context.memories) == 1
    assert context.memories[0].current_revision.content == "prefiere respuestas breves"
    assert [m.content for m in context.recent_messages] == ["hola", "hola de vuelta"]
    assert context.current_user_message == "¿prefieres respuestas breves sobre SQLite?"


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

    context = builder.build("vigente")

    assert [m.id for m in context.memories] == [current.id]


@pytest.mark.integration
def test_build_excludes_a_memory_superseded_by_a_prevailing_decision(tmp_path: Path) -> None:
    """B4e, DR-011: a current memory whose explicit subject/project matches a
    single APPROVED decision is excluded from context — that decision
    already prevails, so presenting both would contradict the precedence
    Sirius already established through an explicit approval."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    project_id = _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)

    unrelated = memory_repository.create_memory("recordatorio sin asunto", "manual")
    memory_repository.create_memory(
        "usar un servidor remoto",
        "manual",
        subject_key="Motor de persistencia",
        project_id=project_id,
    )
    decision = decision_repository.create_proposal(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    decision_repository.approve_decision(decision.id)

    # Both memories are made pertinent to the query on purpose: this proves
    # the second is excluded by B4e precedence, not merely by being
    # unrelated to "hola" as before B6d.
    context = builder.build("recordatorio remoto")

    assert [m.id for m in context.memories] == [unrelated.id]


@pytest.mark.integration
def test_build_keeps_unresolved_conflicting_memories(tmp_path: Path) -> None:
    """B4e never resolves a genuine memory-memory conflict itself (no
    decision to prevail): both stay in context exactly as before — silently
    picking or dropping one would be exactly the "elección silenciosa" B4e
    forbids."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    project_id = _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)

    first = memory_repository.create_memory(
        "usar SQLite local", "manual", subject_key="Motor de persistencia", project_id=project_id
    )
    second = memory_repository.create_memory(
        "usar un servidor remoto",
        "manual",
        subject_key="Motor de persistencia",
        project_id=project_id,
    )

    context = builder.build("sqlite remoto")

    assert {m.id for m in context.memories} == {first.id, second.id}


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

    context = builder.build("recordatorio")

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
def test_build_excludes_memories_and_decisions_unrelated_to_the_query(tmp_path: Path) -> None:
    """B6b/B6d: the context is *pertinent*, not "every current memory" —
    a memory/decision with neither a matching subject nor an FTS5 hit for
    the query is "elemento general no relacionado" (S7.5) and never
    appears, even though it is vigente."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    project_id = _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)

    memory_repository.create_memory("prefiere respuestas breves", "manual")
    decision = decision_repository.create_proposal(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    decision_repository.approve_decision(decision.id)

    context = builder.build("¿qué tiempo hace hoy en la costa?")

    assert context.memories == ()
    assert context.decisions == ()


@pytest.mark.integration
def test_build_caps_pertinent_knowledge_to_max_knowledge_items(tmp_path: Path) -> None:
    """S6.3: at most ``max_knowledge_items`` knowledge candidates enter the
    context, even when many more are vigente and pertinent."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    builder = _build_context_builder(database_path, max_knowledge_items=2)
    memory_repository = build_sqlite_memory_repository(database_path)
    for index in range(5):
        memory_repository.create_memory(f"recordatorio pertinente numero {index}", "manual")

    context = builder.build("recordatorio pertinente")

    assert len(context.memories) == 2


@pytest.mark.integration
def test_build_never_trims_protected_sections_even_with_a_tiny_budget(tmp_path: Path) -> None:
    """S6.2/S6.3: identity/rules, the active project, and the current user
    message are never trimmed — a budget too small even for them alone
    simply empties every selected section instead of raising or invading
    them."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(
        database_path, project_name="Sirius 0.1", project_objective="cerrar B6d"
    )
    builder = _build_context_builder(database_path, token_budget=1)
    memory_repository = build_sqlite_memory_repository(database_path)
    memory_repository.create_memory("recordatorio pertinente", "manual")
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "hola")

    context = builder.build("recordatorio pertinente")

    assert context.identity.current_version.name == "Sirius"
    assert context.project is not None
    assert context.project.name == "Sirius 0.1"
    assert context.current_user_message == "recordatorio pertinente"
    assert context.memories == ()
    assert context.decisions == ()
    assert context.recent_messages == ()


@pytest.mark.integration
def test_build_fills_remaining_budget_with_recent_messages_dropping_oldest_first(
    tmp_path: Path,
) -> None:
    """S6.3: once the protected sections and the pertinent knowledge are
    paid for, recent messages fill whatever budget remains, oldest first —
    exercised here through the real wiring, not just B6c's pure unit
    tests."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "antiguo")
    conversation_repository.append_message(conversation.id, MessageRole.USER, "reciente")

    query = "sin conocimiento pertinente"
    token_counter = CharacterHeuristicTokenCounter()
    protected_tokens = token_counter.count_tokens(
        "\n".join(
            [INITIAL_IDENTITY_NAME, INITIAL_IDENTITY_DESCRIPTION, INITIAL_PERSONALITY_INSTRUCTIONS]
        )
    ) + token_counter.count_tokens(query)
    # A project is configured by _seed_bootstrap_singletons(), so its
    # rendered fields are protected too; mirror ContextBuilder._protected_tokens.
    project_repository = build_sqlite_project_repository(database_path)
    active_project = project_repository.get_active_project()
    assert active_project is not None
    revision = active_project.current_revision
    assert revision is not None
    protected_tokens += token_counter.count_tokens(
        "\n".join(
            [
                active_project.name,
                revision.objective,
                revision.state_summary,
                blockers_to_text(revision.blockers),
                revision.next_step,
            ]
        )
    )
    recent_cost = token_counter.count_tokens("reciente")
    # Budget for the protected sections plus only the newest message.
    builder = _build_context_builder(
        database_path, token_budget=protected_tokens + recent_cost, max_knowledge_items=0
    )

    context = builder.build(query)

    assert [m.content for m in context.recent_messages] == ["reciente"]


# --- M10 (SIRIUS-ARQ-0.2 §6.3, §8): the relevance filter's candado -----------


@pytest.mark.integration
def test_no_relevance_filter_port_leaves_ranking_untouched(tmp_path: Path) -> None:
    """Default constructors keep today's exact behaviour (§6.3): with no
    ``relevance_filter_port`` at all, the second filter step never runs."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    memory = memory_repository.create_memory("candidato sin filtro", "manual")
    builder = _build_context_builder(database_path)

    context = builder.build("candidato")

    assert [m.id for m in context.memories] == [memory.id]


@pytest.mark.integration
def test_relevance_filter_excludes_a_non_critical_candidate_the_double_discards(
    tmp_path: Path,
) -> None:
    """§8-M10 criterion (i): a filter double that discards every candidate
    it sees still excludes one whose category is neither ``None`` nor the
    max-criticality category — the candado only ever adds candidates back,
    never overrides a discard for one it does not protect."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    non_critical = memory_repository.create_memory("candidato descartable", "manual")
    memory_repository.set_user_category(non_critical.id, "otros")
    builder = _build_context_builder(
        database_path,
        relevance_filter_port=_ExcludeAllRelevanceFilterPort(),
        max_criticality_category="salud",
    )

    context = builder.build("candidato")

    assert context.memories == ()


@pytest.mark.integration
def test_relevance_filter_fail_open_result_matches_no_filter_at_all(tmp_path: Path) -> None:
    """§8-M10 criteria (ii)-(iv): whatever internal problem made the real
    adapter fail open, ``ContextBuilder`` only ever sees ``candidates``
    unmodified come back — the result is identical to never having invoked
    the filter, with no exception propagated out of ``build()``."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    non_critical = memory_repository.create_memory("candidato normal", "manual")
    memory_repository.set_user_category(non_critical.id, "otros")
    builder = _build_context_builder(
        database_path,
        relevance_filter_port=_FailOpenRelevanceFilterPort(),
        max_criticality_category="salud",
    )

    context = builder.build("candidato")

    assert [m.id for m in context.memories] == [non_critical.id]


@pytest.mark.integration
def test_relevance_filter_candado_protects_the_max_criticality_category(tmp_path: Path) -> None:
    """§8-M10: a candidate whose category equals the max-criticality
    category (persisted by M8) survives even though the filter double
    explicitly discards every candidate it sees."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    critical = memory_repository.create_memory("candidato critico", "manual")
    memory_repository.set_user_category(critical.id, "salud")
    builder = _build_context_builder(
        database_path,
        relevance_filter_port=_ExcludeAllRelevanceFilterPort(),
        max_criticality_category="salud",
    )

    context = builder.build("candidato")

    assert [m.id for m in context.memories] == [critical.id]


@pytest.mark.integration
def test_relevance_filter_candado_protects_a_candidate_without_a_category_yet(
    tmp_path: Path,
) -> None:
    """§8-M10: a candidate with ``category is None`` (classification still
    pending, or Ollama never available) survives even though the filter
    double explicitly discards every candidate it sees — until
    ``TagCategoryUseCase`` assigns it a non-critical category, it is never
    exposed to the destructive filter."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    _seed_bootstrap_singletons(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    uncategorized = memory_repository.create_memory("candidato sin categoria", "manual")
    builder = _build_context_builder(
        database_path,
        relevance_filter_port=_ExcludeAllRelevanceFilterPort(),
        max_criticality_category="salud",
    )

    context = builder.build("candidato")

    assert [m.id for m in context.memories] == [uncategorized.id]


@pytest.mark.integration
def test_relevance_filter_candado_preserves_rank_order_not_the_filter_or_set_order(
    tmp_path: Path,
) -> None:
    """The candado is a union of three sets recombined over ``candidates``,
    never a second call to the filter and never a reorder: the result keeps
    the same relative order §6.2 already fixed, oldest-created last once
    every other ranking criterion ties."""
    database_path = tmp_path / "sirius.db"
    _prepare_schema(database_path)
    project_id = _seed_bootstrap_singletons(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    critical = memory_repository.create_memory("candidato uno", "manual", project_id=project_id)
    memory_repository.set_user_category(critical.id, "salud")
    uncategorized = memory_repository.create_memory(
        "candidato dos", "manual", project_id=project_id
    )
    non_critical = memory_repository.create_memory(
        "candidato tres", "manual", project_id=project_id
    )
    memory_repository.set_user_category(non_critical.id, "otros")
    # Pin recency so the rank is deterministic and known ahead of time
    # (newest first): critical, then uncategorized, then non_critical.
    _set_updated_at(database_path, critical.id, "2026-01-03T00:00:00")
    _set_updated_at(database_path, uncategorized.id, "2026-01-02T00:00:00")
    _set_updated_at(database_path, non_critical.id, "2026-01-01T00:00:00")
    builder = _build_context_builder(
        database_path,
        relevance_filter_port=_ExcludeAllRelevanceFilterPort(),
        max_criticality_category="salud",
    )

    context = builder.build("candidato")

    assert [m.id for m in context.memories] == [critical.id, uncategorized.id]
