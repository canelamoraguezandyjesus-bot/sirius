"""Domain entities for the single active project and its revision history (B3c)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ProjectStatus(StrEnum):
    """Structural lifecycle state of a project — distinct from
    ``ProjectRevision.state_summary``, which is a free-text work summary.

    Only two values exist in this cut (B3c): a project is either the single
    ``ACTIVE`` one, or ``COMPLETED``. RF-018's approved text is "Marcarlo
    completado sin borrar su historial" — completing only; archiving a
    project is not part of Sirius 0.1 (RF-024's "archivar" applies to
    memories/decisions, not to a project's own lifecycle).
    """

    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class ProjectRevision:
    """One immutable, versioned snapshot of a project's continuity fields.

    Every confirmed update to objective, state, blockers, or next step
    creates a new revision; an existing revision is never modified in place.
    ``source_event_id`` is reserved for the event infrastructure B4 will
    introduce — always ``None`` until then, never a fabricated reference.
    """

    id: int
    project_id: int
    version: int
    objective: str
    state_summary: str
    blockers: tuple[str, ...]
    next_step: str
    source_event_id: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Project:
    """The single active project Sirius helps carry forward across sessions,
    plus whichever project has since been completed.

    ``current_revision`` is ``None`` only for the neutral bootstrap
    placeholder (no name, no objective, never configured by the user) —
    every configured project always has one. There is no ``is_active``
    field here: activity is derived from ``status`` alone
    (``status is ProjectStatus.ACTIVE``); ``is_active`` remains a
    persistence-only projection confined to the SQLite adapter, kept in
    sync with ``status`` in the same transaction.
    """

    id: int
    name: str
    status: ProjectStatus
    current_revision: ProjectRevision | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


def is_configured(project: Project) -> bool:
    """Whether the user has actually set up this project.

    A bootstrap placeholder — ``ACTIVE`` with no revision, or an empty name —
    does not count, and must never be presented, or sent to the provider, as
    a real project. ``status`` alone never implies configuration: an
    ``ACTIVE`` placeholder is not configured, and a completed project (never
    returned by ``get_active_project()``) is deliberately excluded from
    "currently usable" regardless of how well-formed its history is.
    """
    return (
        bool(project.name.strip())
        and project.current_revision is not None
        and bool(project.current_revision.objective.strip())
    )


def next_project_revision_version(current: ProjectRevision) -> int:
    """The next version number in a project's append-only revision chain."""
    return current.version + 1


def normalize_blockers(raw: str) -> tuple[str, ...]:
    """Parse free multiline text into the domain's structured blocker list.

    Trims exterior whitespace and leading/trailing blank lines, strips each
    remaining line's exterior spaces, and keeps interior blank lines,
    duplicates, and order exactly as typed. Never interprets natural
    language; never invents or drops a blocker beyond blank-line trimming.
    """
    lines = [line.strip() for line in raw.splitlines()]
    start = 0
    while start < len(lines) and lines[start] == "":
        start += 1
    end = len(lines)
    while end > start and lines[end - 1] == "":
        end -= 1
    return tuple(lines[start:end])


def blockers_to_text(blockers: tuple[str, ...]) -> str:
    """Render the structured blocker list back as multiline text for display."""
    return "\n".join(blockers)


# --- Canonical initial values (B3a) -----------------------------------------
# No canonical document defines specific wording for a project's initial
# state or next step (unlike sirius.domain.identity's seed, which is copied
# verbatim from an approved source): these are Sirius's own minimal,
# centralized values, kept here so application, presentation, and tests share
# exactly one definition instead of duplicating the strings.

INITIAL_PROJECT_STATE = "Recién creado; todavía sin actualizar."

INITIAL_PROJECT_NEXT_STEP = "Definir cuál será el primer paso concreto."
