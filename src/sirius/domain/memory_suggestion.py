"""Domain entities and transition rules for confirmable memory suggestions.

SIRIUS-ARQ-0.2 §3.2/§3.3: a suggestion is never a memory — it must never enter
``sirius.domain.precedence`` while ``PENDING`` or once ``REJECTED``; only
confirming it materializes a real ``Memory`` (§3.5, out of scope for this
module). Deliberately no revision table (§3.3): a suggestion's content is
fixed at proposal time and only has two possible destinations, confirm or
reject — a different content is reached by rejecting and using
``SaveManualMemoryUseCase`` directly, not by correcting the suggestion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MemorySuggestionStatus(StrEnum):
    """Lifecycle of a memory suggestion. There is no path back to PENDING
    from either terminal state — the same monotony principle as
    ``DecisionStatus`` (``src/sirius/domain/decision.py:43``)."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class MemorySuggestion:
    """A proposed memory awaiting the user's explicit confirmation or rejection.

    ``subject_key``/``project_id`` mirror ``Memory``'s optional "asunto"
    identification (``src/sirius/domain/memory.py``): carried through to the
    real ``Memory`` a confirmation creates, but never themselves compared for
    precedence or conflict while the suggestion is pending or rejected.
    """

    id: int
    content: str
    status: MemorySuggestionStatus
    source_event_id: int | None
    created_at: datetime
    resolved_at: datetime | None
    resulting_memory_id: int | None = None
    subject_key: str | None = None
    project_id: int | None = None


def ensure_can_confirm(suggestion: MemorySuggestion) -> None:
    """Only a PENDING suggestion can be confirmed."""
    if suggestion.status is not MemorySuggestionStatus.PENDING:
        msg = f"Cannot confirm a memory suggestion with status '{suggestion.status.value}'."
        raise ValueError(msg)


def ensure_can_reject(suggestion: MemorySuggestion) -> None:
    """Only a PENDING suggestion can be rejected."""
    if suggestion.status is not MemorySuggestionStatus.PENDING:
        msg = f"Cannot reject a memory suggestion with status '{suggestion.status.value}'."
        raise ValueError(msg)
