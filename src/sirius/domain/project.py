"""Domain entity for the single active project."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Project:
    """The single active project Sirius helps carry forward across sessions."""

    id: int
    name: str
    objective: str
    current_state: str
    next_step: str
    created_at: datetime
    updated_at: datetime


def is_configured(project: Project) -> bool:
    """Whether the user has actually set up this project.

    ``ProjectRepository.get_or_create_active_project()`` seeds a neutral
    placeholder (empty name and objective) at bootstrap, before any project
    is configured (SIRIUS-ARQ-0.1: identity/main conversation/active project
    singletons must exist for ``ContextBuilder`` to run). That placeholder
    must never be presented, or sent to the provider, as a real project —
    this is the single source of truth for telling the two apart.
    """
    return bool(project.name.strip()) and bool(project.objective.strip())


# --- Canonical initial values (B3a) -----------------------------------------
# No canonical document defines specific wording for a project's initial
# state or next step (unlike sirius.domain.identity's seed, which is copied
# verbatim from an approved source): these are Sirius's own minimal,
# centralized values, kept here so application, presentation, and tests share
# exactly one definition instead of duplicating the strings.

INITIAL_PROJECT_STATE = "Recién creado; todavía sin actualizar."

INITIAL_PROJECT_NEXT_STEP = "Definir cuál será el primer paso concreto."
