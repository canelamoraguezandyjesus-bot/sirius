"""Persistence contract for manual, versioned memory, independent of SQLAlchemy."""

from __future__ import annotations

from typing import Protocol

from sirius.domain.memory import Memory, MemoryRevision


class MemoryRepository(Protocol):
    """Contract implemented by real and simulated memory stores.

    Transition rules (mandatory origin, legal status transitions, version
    numbering) live in ``sirius.domain.memory``; implementations are expected
    to enforce them before mutating storage.
    """

    def create_memory(
        self, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        """Record a new manual memory with its first revision.

        ``source_event_id`` (B4a) links the first revision to the event that
        recorded why it was created; ``None`` when the caller does not have
        one (e.g. a direct repository call with no explicit-save event).
        """
        ...

    def get_memory(self, memory_id: int) -> Memory:
        """Return a memory by id, whatever its status."""
        ...

    def list_current_memories(self) -> list[Memory]:
        """Return every memory whose status is CURRENT."""
        ...

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        """Return every revision of a memory, in stable version order."""
        ...

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        """Create a new revision superseding the current one, without overwriting it."""
        ...

    def archive_memory(self, memory_id: int) -> Memory:
        """Remove a memory from ordinary context while keeping its content."""
        ...

    def delete_memory(self, memory_id: int) -> Memory:
        """Redact the structured content of every revision and mark the memory deleted."""
        ...
