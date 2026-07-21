"""Deterministic context budget and trim (B6c; SIRIUS-ARQ-0.1 S6.2 "Límite de
tokens" / S6.3 "Reglas de recorte"; D-11; ATD-007).

Given the knowledge B6b already ranked (``sirius.domain.relevance``, never
reimplemented here) and the conversation's full recent messages, select what
fits an input token budget alongside the sections that are already fixed and
never trimmed: identity, rules/permissions, and the current user message.
This is a pure, isolated selection: it never touches a repository,
``ContextBuilder``, or the provider — wiring it into context assembly is
B6d.

S6.3's rules, as implemented here:

- At most ``max_knowledge_items`` (default 12) knowledge candidates, taken in
  B6b's relevance order — the least relevant are dropped first purely by
  that order.
- If the remaining token budget still cannot fit every capped candidate,
  general memories are dropped (least relevant first) before any current
  decision is: a current decision "prima" over a general memory when
  trimming, never the reverse.
- Recent messages fill whatever budget remains, newest first: the oldest
  non-source message is dropped before any other. A message that is the
  recorded source (``source_event_id`` -> ``Event.message_id``) of an
  already-selected knowledge item is never dropped while an older non-source
  message remains to drop instead — but it is not otherwise exempt, since
  only identity, rules/permissions, and the current user message are never
  trimmed at all.
- A ``CANCELLED``/``FAILED``/``REDACTED`` message is never selected,
  mirroring ``ContextBuilder``'s own re-check today (SIRIUS-ARQ-0.1
  S5.1/S5.2): this module re-verifies ``status`` itself instead of trusting
  the caller, the same guarantee ``sirius.domain.relevance`` already gives
  for vigente knowledge.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sirius.domain.conversation import Message, MessageStatus
from sirius.domain.event import Event
from sirius.domain.relevance import KnowledgeKind, RankedKnowledge
from sirius.ports.token_counter import TokenCounter

__all__ = [
    "DEFAULT_MAX_KNOWLEDGE_ITEMS",
    "DEFAULT_TOKEN_BUDGET",
    "ContextBudgetSelection",
    "apply_context_budget",
]

DEFAULT_TOKEN_BUDGET = 12000
DEFAULT_MAX_KNOWLEDGE_ITEMS = 12


@dataclass(frozen=True, slots=True)
class ContextBudgetSelection:
    """What ``apply_context_budget`` chose: B6b-ranked knowledge, still in its
    original relevance order, and recent messages, still in chronological
    (oldest-first) order — both are subsequences of the caller's input,
    never reordered."""

    knowledge: tuple[RankedKnowledge, ...]
    recent_messages: tuple[Message, ...]


def _knowledge_text(candidate: RankedKnowledge) -> str:
    return candidate.item.current_revision.content or ""


def _cap_and_trim_knowledge(
    ranked_knowledge: Sequence[RankedKnowledge],
    token_counter: TokenCounter,
    max_knowledge_items: int,
    remaining_budget: int,
) -> tuple[tuple[RankedKnowledge, ...], int]:
    """Apply the count cap, then the token trim that favours a current
    decision over a general memory, returning the selection and its total
    token cost."""
    included = list(ranked_knowledge[: max(max_knowledge_items, 0)])
    costs = {
        candidate: token_counter.count_tokens(_knowledge_text(candidate)) for candidate in included
    }
    total_cost = sum(costs.values())

    def _drop_least_relevant_of(kind: KnowledgeKind) -> bool:
        nonlocal total_cost
        for index in range(len(included) - 1, -1, -1):
            if included[index].kind is kind:
                dropped = included.pop(index)
                total_cost -= costs[dropped]
                return True
        return False

    while total_cost > remaining_budget and _drop_least_relevant_of(KnowledgeKind.MEMORY):
        pass
    while total_cost > remaining_budget and _drop_least_relevant_of(KnowledgeKind.DECISION):
        pass

    return tuple(included), total_cost


def _resolve_source_message_ids(
    knowledge: Sequence[RankedKnowledge], source_events: Sequence[Event]
) -> frozenset[int]:
    """Which recent-message ids are the recorded source of a selected
    knowledge item's current revision, via ``source_event_id`` ->
    ``Event.message_id``. ``source_events`` is whatever the caller already
    resolved (an event with no match, or no linked message, is simply
    ignored) — this module never queries ``EventRepository`` itself."""
    events_by_id = {event.id: event for event in source_events}
    source_message_ids: set[int] = set()
    for candidate in knowledge:
        source_event_id = candidate.item.current_revision.source_event_id
        if source_event_id is None:
            continue
        event = events_by_id.get(source_event_id)
        if event is not None and event.message_id is not None:
            source_message_ids.add(event.message_id)
    return frozenset(source_message_ids)


def _trim_messages(
    recent_messages: Sequence[Message],
    token_counter: TokenCounter,
    remaining_budget: int,
    source_message_ids: frozenset[int],
) -> tuple[Message, ...]:
    """Drop the oldest non-source message first, newest turns last; a source
    message is only dropped once no older non-source message remains."""
    completed = [
        message for message in recent_messages if message.status is MessageStatus.COMPLETED
    ]
    costs = {message.id: token_counter.count_tokens(message.content or "") for message in completed}
    included = list(completed)
    total_cost = sum(costs.values())

    while total_cost > remaining_budget and included:
        drop_index = min(
            range(len(included)),
            key=lambda i: (included[i].id in source_message_ids, included[i].sequence),
        )
        total_cost -= costs[included[drop_index].id]
        del included[drop_index]

    return tuple(included)


def apply_context_budget(
    *,
    protected_tokens: int,
    ranked_knowledge: Sequence[RankedKnowledge],
    recent_messages: Sequence[Message],
    token_counter: TokenCounter,
    source_events: Sequence[Event] = (),
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    max_knowledge_items: int = DEFAULT_MAX_KNOWLEDGE_ITEMS,
) -> ContextBudgetSelection:
    """Select the knowledge and recent messages that fit ``token_budget``
    alongside ``protected_tokens`` (the already-fixed cost of identity,
    rules/permissions, and the current user message — never part of the
    selection and never trimmed here).

    ``ranked_knowledge`` must already be in B6b's relevance order (most
    relevant first); it is never reordered, only capped and trimmed.
    ``recent_messages`` must be in chronological order (newest last).
    ``source_events`` lets a message that originated an included knowledge
    item survive longer than other old messages (S6.3) — omit it (or pass
    events with no bearing on ``ranked_knowledge``) and that protection
    simply does not apply.

    Never raises for a too-small budget: ``protected_tokens`` alone may
    already exceed ``token_budget``, in which case both ``knowledge`` and
    ``recent_messages`` come back empty rather than encroaching on the
    protected sections.
    """
    if protected_tokens < 0:
        msg = "protected_tokens cannot be negative."
        raise ValueError(msg)
    if token_budget < 0:
        msg = "token_budget cannot be negative."
        raise ValueError(msg)

    remaining_after_protected = token_budget - protected_tokens
    selected_knowledge, knowledge_cost = _cap_and_trim_knowledge(
        ranked_knowledge, token_counter, max_knowledge_items, remaining_after_protected
    )

    remaining_for_messages = remaining_after_protected - knowledge_cost
    source_message_ids = _resolve_source_message_ids(selected_knowledge, source_events)
    selected_messages = _trim_messages(
        recent_messages, token_counter, remaining_for_messages, source_message_ids
    )

    return ContextBudgetSelection(knowledge=selected_knowledge, recent_messages=selected_messages)
