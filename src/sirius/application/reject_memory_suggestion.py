"""Explicit rejection of a pending memory suggestion (M5, SIRIUS-ARQ-0.2 §3.5).

Within a single ``UnitOfWork`` transaction: fetches the suggestion, checks
``ensure_can_reject``, opens a ``MEMORY_SUGGESTION_REJECTED_EVENT_TYPE``
event, and marks the suggestion REJECTED. Never creates a ``Memory``, never
writes to ``memory_repository`` — a rejected suggestion leaves no trace in
ordinary context, since neither ``ContextBuilder`` nor
``RankRelevantKnowledgeUseCase`` ever read ``MemorySuggestionRepository``
(§3.5, §4.4 of the Product definition).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sirius.domain.event import MEMORY_SUGGESTION_REJECTED_EVENT_TYPE, USER_ACTOR
from sirius.domain.memory_suggestion import MemorySuggestion, ensure_can_reject
from sirius.ports.unit_of_work import UnitOfWork

__all__ = ["RejectMemorySuggestionUseCase"]


class RejectMemorySuggestionUseCase:
    """Rechaza una sugerencia pendiente, sin dejar rastro en el contexto ordinario (§3.5)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def reject(self, suggestion_id: int) -> MemorySuggestion:
        """Reject a PENDING suggestion.

        Raises whatever ``ensure_can_reject`` raises (a plain ``ValueError``)
        if the suggestion is not PENDING — checked after fetching it, inside
        the transaction.

        The event and the suggestion's REJECTED transition are written and
        committed within a single transaction: if either write fails, both
        are rolled back and nothing persists.
        """
        with self._unit_of_work as uow:
            suggestion = uow.memory_suggestion_repository.get_suggestion(suggestion_id)
            ensure_can_reject(suggestion)

            uow.event_repository.append(
                event_type=MEMORY_SUGGESTION_REJECTED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=None,
            )
            rejected = uow.memory_suggestion_repository.reject_suggestion(
                suggestion_id,
                resolved_at=datetime.now(UTC),
            )
            uow.commit()

        return rejected
