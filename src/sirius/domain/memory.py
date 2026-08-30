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

    ``subject_key``/``project_id`` (B4e, RF-026, DR-011) are the minimal,
    explicit "asunto" identification precedence and conflict detection need
    to compare memories: the same conceptual pairing
    ``Decision.subject``/``Decision.project_id`` already uses. Both are
    optional and independent of content or origin — most memories predate
    B4e or are never meant to be compared against anything else, and stay
    ``None`` (never considered for precedence or conflict against any other
    item; see ``sirius.domain.precedence``). They live on the memory itself,
    not its revision, mirroring ``Decision.subject``/``Decision.project_id``:
    correcting a memory's content (B4c) never changes what asunto it is
    about.

    ``category``/``category_locked`` (D7, SIRIUS-ARQ-0.2 §6.1) are likewise
    optional and live on the memory itself, not its revision: classifying a
    memory's category is not correcting its content. ``category`` is
    ``None`` until something writes it — automatically
    (``TagCategoryUseCase``) or manually (``SetCategoryUseCase``).
    ``category_locked`` starts ``False`` and becomes ``True`` only through an
    explicit user edit (``SetCategoryUseCase``); once ``True``, no automatic
    classification may ever overwrite ``category`` again.
    """

    id: int
    status: MemoryStatus
    current_revision: MemoryRevision
    created_at: datetime
    updated_at: datetime
    subject_key: str | None = None
    project_id: int | None = None
    category: str | None = None
    category_locked: bool = False


def ensure_valid_origin(origin: str) -> None:
    """A memory, or a correction to it, can never be created without a real origin."""
    if not origin or not origin.strip():
        msg = "A memory revision requires a non-empty origin."
        raise ValueError(msg)


def ensure_valid_subject_key(subject_key: str | None) -> None:
    """A memory's ``subject_key`` is optional, but never blank when given
    (B4e): the same non-empty rule ``Decision.subject`` enforces via
    ``sirius.domain.decision.ensure_valid_subject``, since both identify the
    same conceptual "asunto"."""
    if subject_key is not None and not subject_key.strip():
        msg = "A memory's subject_key, when given, cannot be blank."
        raise ValueError(msg)


def ensure_subject_key_has_a_project(subject_key: str | None, project_id: int | None) -> None:
    """An explicit ``subject_key`` requires an explicit ``project_id`` (B4e):
    precedence and conflict detection compare memories within the same
    subject *and* project boundary decisions already use — a subject with no
    project would have no boundary to compare within."""
    if subject_key is not None and project_id is None:
        msg = "A memory with an explicit subject_key must also be associated with a project."
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
