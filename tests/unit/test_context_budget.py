"""Unit tests for the pure B6c budget/trim rule (SIRIUS-ARQ-0.1 S6.2/S6.3;
D-11; ATD-007). No fakes beyond a controlled ``TokenCounter``, no SQLite —
only value objects, mirroring ``test_relevance_domain.py``/
``test_precedence_domain.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.application.context_budget import (
    DEFAULT_MAX_KNOWLEDGE_ITEMS,
    DEFAULT_TOKEN_BUDGET,
    ContextBudgetSelection,
    apply_context_budget,
)
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.event import Event
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.domain.relevance import KnowledgeKind, RankedKnowledge

_NOW = datetime(2026, 7, 21, tzinfo=UTC)


class _OneTokenPerCharacterCounter:
    """A controlled ``TokenCounter``: exactly one token per character, so
    every test's arithmetic is exact and independent of the real (heuristic)
    estimator's rounding."""

    def count_tokens(self, text: str) -> int:
        return len(text)


def _memory(memory_id: int, content: str = "x", *, source_event_id: int | None = None) -> Memory:
    revision = MemoryRevision(
        id=memory_id,
        memory_id=memory_id,
        version=1,
        content=content,
        origin="manual",
        source_event_id=source_event_id,
        created_at=_NOW,
    )
    return Memory(
        id=memory_id,
        status=MemoryStatus.CURRENT,
        current_revision=revision,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _decision(
    decision_id: int, content: str = "x", *, source_event_id: int | None = None
) -> Decision:
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content=content,
        source_event_id=source_event_id,
        created_at=_NOW,
    )
    return Decision(
        id=decision_id,
        subject="asunto",
        project_id=1,
        status=DecisionStatus.APPROVED,
        current_revision=revision,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _ranked_memory(memory: Memory) -> RankedKnowledge:
    return RankedKnowledge(
        kind=KnowledgeKind.MEMORY,
        item=memory,
        subject_matches_query=False,
        project_matches_active=False,
        fts_match=True,
    )


def _ranked_decision(decision: Decision) -> RankedKnowledge:
    return RankedKnowledge(
        kind=KnowledgeKind.DECISION,
        item=decision,
        subject_matches_query=False,
        project_matches_active=False,
        fts_match=True,
    )


def _message(
    message_id: int,
    sequence: int,
    content: str = "x",
    *,
    status: MessageStatus = MessageStatus.COMPLETED,
) -> Message:
    return Message(
        id=message_id,
        conversation_id=1,
        sequence=sequence,
        role=MessageRole.USER,
        content=content,
        created_at=_NOW,
        status=status,
    )


_COUNTER = _OneTokenPerCharacterCounter()


# --- Defaults match the approved values (S6.2). ---


def test_defaults_are_the_approved_values() -> None:
    assert DEFAULT_TOKEN_BUDGET == 12000
    assert DEFAULT_MAX_KNOWLEDGE_ITEMS == 12


# --- Generous budget: everything given is selected, untouched. ---


def test_everything_fits_when_the_budget_is_generous() -> None:
    knowledge = (_ranked_memory(_memory(1, "abc")), _ranked_decision(_decision(2, "de")))
    messages = (_message(1, 1, "hola"), _message(2, 2, "adios"))

    result = apply_context_budget(
        protected_tokens=10,
        ranked_knowledge=knowledge,
        recent_messages=messages,
        token_counter=_COUNTER,
        token_budget=1000,
    )

    assert result == ContextBudgetSelection(knowledge=knowledge, recent_messages=messages)


# --- Count cap: at most max_knowledge_items, least relevant dropped first. ---


def test_the_count_cap_drops_the_least_relevant_knowledge_first() -> None:
    knowledge = tuple(_ranked_memory(_memory(i, "x")) for i in range(1, 5))

    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=knowledge,
        recent_messages=(),
        token_counter=_COUNTER,
        token_budget=1000,
        max_knowledge_items=2,
    )

    assert result.knowledge == knowledge[:2]


def test_zero_max_knowledge_items_selects_no_knowledge() -> None:
    knowledge = (_ranked_memory(_memory(1, "x")),)

    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=knowledge,
        recent_messages=(),
        token_counter=_COUNTER,
        token_budget=1000,
        max_knowledge_items=0,
    )

    assert result.knowledge == ()


# --- Token trim: a current decision is never dropped before a general memory. ---


def test_token_trim_drops_a_general_memory_before_a_more_relevant_decision() -> None:
    # B6b order: memory ranks first (more relevant), decision ranks second —
    # yet only one of the two ten-token items fits the budget.
    memory = _ranked_memory(_memory(1, "m" * 10))
    decision = _ranked_decision(_decision(2, "d" * 10))

    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=(memory, decision),
        recent_messages=(),
        token_counter=_COUNTER,
        token_budget=10,
    )

    assert result.knowledge == (decision,)


def test_token_trim_drops_the_least_relevant_memory_first_among_several() -> None:
    most_relevant_memory = _ranked_memory(_memory(1, "m" * 5))
    least_relevant_memory = _ranked_memory(_memory(2, "m" * 5))
    decision = _ranked_decision(_decision(3, "d" * 5))

    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=(most_relevant_memory, least_relevant_memory, decision),
        recent_messages=(),
        token_counter=_COUNTER,
        token_budget=10,
    )

    assert result.knowledge == (most_relevant_memory, decision)


def test_token_trim_drops_decisions_too_once_no_memory_remains() -> None:
    decision_a = _ranked_decision(_decision(1, "d" * 5))
    decision_b = _ranked_decision(_decision(2, "d" * 5))

    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=(decision_a, decision_b),
        recent_messages=(),
        token_counter=_COUNTER,
        token_budget=5,
    )

    assert result.knowledge == (decision_a,)


# --- Recent messages fill whatever budget remains, newest turns first. ---


def test_messages_fill_the_remaining_budget_dropping_the_oldest_first() -> None:
    oldest = _message(1, 1, "a" * 5)
    middle = _message(2, 2, "b" * 5)
    newest = _message(3, 3, "c" * 5)

    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=(),
        recent_messages=(oldest, middle, newest),
        token_counter=_COUNTER,
        token_budget=10,
    )

    assert result.recent_messages == (middle, newest)


# --- Source-message exemption: survives older non-source messages, not forever. ---


def test_a_source_message_survives_a_more_recent_non_source_message() -> None:
    # The source message (sequence 1) is older than the plain one (sequence
    # 2) — a pure recency rule would drop it first. S6.3 says otherwise:
    # while any non-source message remains, that is dropped instead.
    source_message = _message(1, 1, "a" * 5)
    newer_non_source = _message(2, 2, "b" * 5)
    memory = _ranked_memory(_memory(10, "m", source_event_id=99))
    event = Event(
        id=99,
        event_type="memory.manual_save",
        actor="user",
        message_id=1,
        created_at=_NOW,
        redacted_at=None,
    )

    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=(memory,),
        recent_messages=(source_message, newer_non_source),
        token_counter=_COUNTER,
        source_events=(event,),
        token_budget=1 + 5,  # room for the memory (1) plus exactly one message.
    )

    assert result.recent_messages == (source_message,)


def test_a_source_message_is_dropped_once_no_non_source_message_remains() -> None:
    source_message = _message(1, 1, "a" * 5)
    memory = _ranked_memory(_memory(10, "m", source_event_id=99))
    event = Event(
        id=99,
        event_type="memory.manual_save",
        actor="user",
        message_id=1,
        created_at=_NOW,
        redacted_at=None,
    )

    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=(memory,),
        recent_messages=(source_message,),
        token_counter=_COUNTER,
        source_events=(event,),
        token_budget=1,  # only room for the memory itself.
    )

    assert result.recent_messages == ()


# --- Protected sections are never encroached upon, even at a tiny budget. ---


def test_a_tiny_budget_still_never_raises_and_selects_nothing_else() -> None:
    knowledge = (_ranked_memory(_memory(1, "m" * 50)),)
    messages = (_message(1, 1, "a" * 50),)

    result = apply_context_budget(
        protected_tokens=1_000_000,
        ranked_knowledge=knowledge,
        recent_messages=messages,
        token_counter=_COUNTER,
        token_budget=1,
    )

    assert result == ContextBudgetSelection(knowledge=(), recent_messages=())


@pytest.mark.parametrize("protected_tokens,token_budget", [(-1, 100), (10, -1)])
def test_negative_protected_tokens_or_budget_raises(
    protected_tokens: int, token_budget: int
) -> None:
    with pytest.raises(ValueError):
        apply_context_budget(
            protected_tokens=protected_tokens,
            ranked_knowledge=(),
            recent_messages=(),
            token_counter=_COUNTER,
            token_budget=token_budget,
        )


# --- Re-check (mirrors sirius.domain.relevance): a partial message is never selected. ---


@pytest.mark.parametrize(
    "status",
    [MessageStatus.CANCELLED, MessageStatus.FAILED, MessageStatus.REDACTED],
)
def test_a_non_completed_message_is_never_selected_even_with_room_to_spare(
    status: MessageStatus,
) -> None:
    partial = _message(1, 1, "x", status=status)

    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=(),
        recent_messages=(partial,),
        token_counter=_COUNTER,
        token_budget=1000,
    )

    assert result.recent_messages == ()


def test_an_empty_input_selects_nothing() -> None:
    result = apply_context_budget(
        protected_tokens=0,
        ranked_knowledge=(),
        recent_messages=(),
        token_counter=_COUNTER,
    )

    assert result == ContextBudgetSelection(knowledge=(), recent_messages=())
