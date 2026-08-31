"""Persistence contract for manual, versioned memory, independent of SQLAlchemy."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sirius.domain.memory import Memory, MemoryRevision


class MemoryRepository(Protocol):
    """Contract implemented by real and simulated memory stores.

    Transition rules (mandatory origin, legal status transitions, version
    numbering) live in ``sirius.domain.memory``; implementations are expected
    to enforce them before mutating storage.
    """

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        """Record a new manual memory with its first revision.

        ``source_event_id`` (B4a) links the first revision to the event that
        recorded why it was created; ``None`` when the caller does not have
        one (e.g. a direct repository call with no explicit-save event).

        ``subject_key``/``project_id`` (B4e) are the optional, explicit
        "asunto" identification precedence and conflict detection compare
        memories on (``sirius.domain.precedence``); ``None`` by default,
        like every memory created before B4e.
        """
        ...

    def get_memory(self, memory_id: int) -> Memory:
        """Return a memory by id, whatever its status."""
        ...

    def list_current_memories(self) -> list[Memory]:
        """Return every memory whose status is CURRENT."""
        ...

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        """Return every CURRENT memory with a non-``None`` ``category``,
        filtered in SQL (ADR-122/M13; CODEX-001, incidencia #489).

        ``categories`` (the closed vocabulary) is only ever an activation
        gate here, mirroring ``category_index_matches_query``'s own
        condition (``category is not None``, never compared against a
        specific vocabulary term): empty returns an empty list without
        querying, exactly like that function's "no vocabulary term
        activated, matches nothing" rule. When non-empty, every memory whose
        persisted ``category`` is not ``None`` is returned, even one that no
        longer belongs to the current vocabulary — ``SetCategoryUseCase``
        never validates the category it writes, and the vocabulary itself is
        a provisional constant a later milestone can replace, so a legacy,
        out-of-vocabulary category is reachable state and must still widen
        the category-only match (M9 §6.2), not be silently dropped.
        """
        ...

    def list_archived_memories(self) -> list[Memory]:
        """Return every memory whose status is ARCHIVED (B4d, RF-024).

        The explicit "consulta de archivados" RF-024 requires: unlike
        ``list_current_memories``, callers use this only when they
        deliberately want archived memories, never as part of ordinary
        context assembly.
        """
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
        """Remove a memory from ordinary context while keeping its content (RF-024)."""
        ...

    def delete_memory(self, memory_id: int) -> Memory:
        """Redact the structured content of every revision and mark the memory deleted."""
        ...

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        """Conditionally write an automatic category (D7 point 2,
        SIRIUS-ARQ-0.2 §6.1), for ``TagCategoryUseCase`` only.

        A single atomic conditional statement in the persistence engine —
        never a read in Python followed by a separate write — writes
        ``category`` only if, in that same statement, ``category_locked`` is
        still ``False`` **and** the memory's current revision is still the
        one whose version is ``observed_revision_version``. Returns ``True``
        if the write happened, ``False`` otherwise (the user already locked
        the category, or a newer revision superseded the one that was
        classified) — in the ``False`` case nothing is written, so neither a
        user's correction nor a newer generation of automatic tagging can
        ever be overwritten by a stale classification.
        """
        ...

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        """Unconditionally write ``category`` and set ``category_locked`` to
        ``True``, in the same call, for ``SetCategoryUseCase`` only (D7 point
        3): a user's category always wins, whatever the current value of
        ``category_locked`` was.
        """
        ...

    def list_uncategorized(self) -> list[Memory]:
        """Return every memory with ``category is None`` and
        ``category_locked is False`` (D7 point 4): the retroactive pass's
        input, and a memory already tagged or already locked is excluded
        even without a category.
        """
        ...
