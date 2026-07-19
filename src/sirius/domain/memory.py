"""Domain entities and transition rules for manual, versioned memory.

``subject_key``/``project_id`` (B4e, RF-026, DR-011) are the memory-side
counterpart of ``Decision.subject``/``Decision.project_id`` — the same
explicit "asunto y proyecto" boundary the architecture's ``knowledge_item``
uses (SIRIUS-ARQ-0.1 S7.3: ``subject_key``), added here as the minimal
persistent identification B4e's precedence/conflict rule
(``sirius.domain.knowledge_precedence``) needs to compare memories of "el
mismo asunto". Both are optional and ``None`` by default: a memory recorded
before B4e, or one that simply has no meaningful subject boundary, never
participates in precedence/conflict detection — it is neither excluded from
context nor treated as agreeing or conflicting with anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MemoryStatus(StrEnum):
    """Lifecycle of a memory item. Superseded revisions are a history concern,
    not a status of the memory itself: the memory stays CURRENT while its
    ``current_revision`` pointer advances."""

    CURRENT = "current"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class MemoryRevision:
    """One immutable, versioned content snapshot of a memory.

    ``content`` is ``None`` only when the memory was deleted: deletion redacts
    structured content across the whole history but keeps a minimal marker
    (id, version, origin, created_at) for traceability.

    ``origin`` is the free-text description V4 already required (non-empty,
    see ``ensure_valid_origin``). ``source_event_id`` (B4a) is the real,
    queryable link RF-021 needs to "open" the origin: it is set whenever the
    revision was created through the explicit manual-save use case, and
    ``None`` for every revision created before B4a or through a path that
    does not (yet) record an event, such as a B4c correction.
    """

    id: int
    memory_id: int
    version: int
    content: str | None
    origin: str
    source_event_id: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Memory:
    """A stable, manually recorded memory and its current revision.

    ``subject_key``/``project_id`` are fixed at creation and never change
    across corrections (mirroring ``Decision.subject``/``project_id``,
    themselves immutable across a decision's lifecycle) — a correction
    replaces content, never the identity boundary a memory was filed under.
    """

    id: int
    status: MemoryStatus
    current_revision: MemoryRevision
    created_at: datetime
    updated_at: datetime
    subject_key: str | None = None
    project_id: int | None = None


def ensure_valid_origin(origin: str) -> None:
    """A memory, or a correction to it, can never be created without a real origin."""
    if not origin or not origin.strip():
        msg = "A memory revision requires a non-empty origin."
        raise ValueError(msg)


def ensure_valid_subject_key(subject_key: str) -> None:
    """When a memory is given a subject key, it can never be empty (B4e).

    Mirrors ``sirius.domain.decision.ensure_valid_subject``. Unlike a
    decision's ``subject``, a memory's ``subject_key`` itself remains
    optional — this guard only applies once a caller has chosen to supply
    one, never forcing every memory to declare a subject.
    """
    if not subject_key or not subject_key.strip():
        msg = "A memory subject key, when given, must be non-empty."
        raise ValueError(msg)


def ensure_can_correct(memory: Memory) -> None:
    """Only a current memory can be corrected; archived/deleted memories are frozen."""
    if memory.status is not MemoryStatus.CURRENT:
        msg = f"Cannot correct a memory with status '{memory.status.value}'."
        raise ValueError(msg)


def ensure_can_archive(memory: Memory) -> None:
    """Only a current memory can be archived."""
    if memory.status is not MemoryStatus.CURRENT:
        msg = f"Cannot archive a memory with status '{memory.status.value}'."
        raise ValueError(msg)


def ensure_can_delete(memory: Memory) -> None:
    """A memory can be deleted from any status except one that is already deleted."""
    if memory.status is MemoryStatus.DELETED:
        msg = "Memory is already deleted."
        raise ValueError(msg)


def next_revision_version(current_revision: MemoryRevision) -> int:
    """The next version number in a memory's append-only revision chain."""
    return current_revision.version + 1
