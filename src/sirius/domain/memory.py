"""Domain entities and transition rules for manual, versioned memory."""

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
    """

    id: int
    memory_id: int
    version: int
    content: str | None
    origin: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Memory:
    """A stable, manually recorded memory and its current revision."""

    id: int
    status: MemoryStatus
    current_revision: MemoryRevision
    created_at: datetime
    updated_at: datetime


def ensure_valid_origin(origin: str) -> None:
    """A memory, or a correction to it, can never be created without a real origin."""
    if not origin or not origin.strip():
        msg = "A memory revision requires a non-empty origin."
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
