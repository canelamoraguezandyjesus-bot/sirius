"""End-to-end integration tests for M5 (SIRIUS-ARQ-0.2 §3.5, §8-M5).

Wires the real SQLite adapters (no fakes) behind ``ProposeMemorySuggestionUseCase``,
``ConfirmMemorySuggestionUseCase``, and ``RejectMemorySuggestionUseCase``, proving
the two literal acceptance criteria of §8-M5:

* propose → confirm produces a CURRENT ``Memory`` with the same content and a
  traceable origin (same mechanism as ``GetMemoryOriginUseCase``).
* propose → reject creates no ``Memory``, and ``ContextBuilder.build()`` over
  that same store never references the rejected suggestion in any field of
  ``Context``.
"""

from pathlib import Path

import pytest

from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.models import Base
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
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.confirm_memory_suggestion import (
    CONFIRMED_MEMORY_SUGGESTION_ORIGIN,
    ConfirmMemorySuggestionUseCase,
)
from sirius.application.context import ContextBuilder
from sirius.application.memory_origin import GetMemoryOriginUseCase
from sirius.application.propose_memory_suggestion import ProposeMemorySuggestionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.reject_memory_suggestion import RejectMemorySuggestionUseCase
from sirius.domain.memory import MemoryStatus
from sirius.domain.memory_suggestion import MemorySuggestionStatus


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


def _build_context_builder(database_path: Path) -> ContextBuilder:
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
    )


def _seed_bootstrap_singletons(database_path: Path) -> None:
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()


@pytest.mark.integration
def test_proposing_and_confirming_a_suggestion_creates_a_traceable_current_memory(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)

    propose_use_case = ProposeMemorySuggestionUseCase(unit_of_work)
    confirm_use_case = ConfirmMemorySuggestionUseCase(unit_of_work)

    suggestion = propose_use_case.propose("El usuario prefiere respuestas breves")
    assert suggestion.status is MemorySuggestionStatus.PENDING

    memory = confirm_use_case.confirm(suggestion.id)

    # §4.4: confirmarla la deja como memoria vigente con el mismo contenido.
    assert memory.status is MemoryStatus.CURRENT
    assert memory.current_revision.content == "El usuario prefiere respuestas breves"
    assert memory.current_revision.origin == CONFIRMED_MEMORY_SUGGESTION_ORIGIN
    assert memory.current_revision.source_event_id is not None

    # §4.4: origen trazable, mismo mecanismo que GetMemoryOriginUseCase.
    origin_use_case = GetMemoryOriginUseCase(
        memory_repository, event_repository, conversation_repository
    )
    origin = origin_use_case.get_origin(memory.id)
    assert origin.event_id == memory.current_revision.source_event_id

    resolved_suggestion = unit_of_work.memory_suggestion_repository.get_suggestion(suggestion.id)
    assert resolved_suggestion.status is MemorySuggestionStatus.CONFIRMED
    assert resolved_suggestion.resulting_memory_id == memory.id


@pytest.mark.integration
def test_proposing_and_rejecting_a_suggestion_creates_no_memory_and_leaves_no_trace_in_context(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    _seed_bootstrap_singletons(database_path)

    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)

    propose_use_case = ProposeMemorySuggestionUseCase(unit_of_work)
    reject_use_case = RejectMemorySuggestionUseCase(unit_of_work)

    suggestion = propose_use_case.propose("Evaluar una herramienta de terceros")
    rejected = reject_use_case.reject(suggestion.id)

    assert rejected.status is MemorySuggestionStatus.REJECTED
    # §4.4: rechazarla no crea ninguna Memory.
    assert memory_repository.list_current_memories() == []

    context_builder = _build_context_builder(database_path)
    context = context_builder.build("¿qué herramientas de terceros hemos evaluado?")

    # §4.4: ni rastro de la sugerencia rechazada en ningún campo del Context.
    assert context.memories == ()
    assert all(
        message.content is None or "Evaluar una herramienta de terceros" not in message.content
        for message in context.recent_messages
    )
    assert all(
        decision.current_revision.content is None
        or "Evaluar una herramienta de terceros" not in decision.current_revision.content
        for decision in context.decisions
    )
