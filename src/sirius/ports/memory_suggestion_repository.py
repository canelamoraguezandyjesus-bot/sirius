"""Persistence contract for confirmable memory suggestions, independent of SQLAlchemy."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sirius.domain.memory_suggestion import MemorySuggestion


class MemorySuggestionRepository(Protocol):
    """Contract implemented by real and simulated memory suggestion stores.

    Transition rules (only a PENDING suggestion may be confirmed or rejected,
    no path back from either terminal state) live in
    ``sirius.domain.memory_suggestion``; implementations are expected to
    enforce them before mutating storage.
    """

    def create_suggestion(
        self,
        content: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> MemorySuggestion:
        """Record a new PENDING memory suggestion.

        ``source_event_id`` links the suggestion to the event that recorded
        why it was proposed; ``None`` when the caller does not have one.

        ``subject_key``/``project_id`` are carried through unchanged to the
        real ``Memory`` a later confirmation creates.
        """
        ...

    def get_suggestion(self, suggestion_id: int) -> MemorySuggestion:
        """Return a memory suggestion by id, whatever its status."""
        ...

    def list_pending_suggestions(self) -> list[MemorySuggestion]:
        """Return every memory suggestion whose status is PENDING."""
        ...

    def confirm_suggestion(
        self, suggestion_id: int, *, resulting_memory_id: int, resolved_at: datetime
    ) -> MemorySuggestion:
        """Mark a PENDING suggestion CONFIRMED, linking the real memory it produced."""
        ...

    def reject_suggestion(self, suggestion_id: int, *, resolved_at: datetime) -> MemorySuggestion:
        """Mark a PENDING suggestion REJECTED. Never creates a memory."""
        ...
