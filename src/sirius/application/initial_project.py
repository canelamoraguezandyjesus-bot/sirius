"""Presentation-facing use case for the first configured project (B3a, D-02).

RF-014 (create with name and objective), RF-015 (a single active project),
and the initial slice of RF-016 (a minimal, safe initial state and next
step). Mirrors ``ApiKeySettingsUseCase``: a small, explicit contract so
``InitialProjectWindow`` never touches ``ProjectRepository``, SQLAlchemy, or
SQLite directly (AGENTS.md: dependency direction presentation -> application
-> domain).

Since B3c, "create the initial project" and "create the next project after
completing the previous one" are the same operation from this use case's
point of view: both go through ``ProjectRepository.create_project``, which
transparently reuses an unconfigured placeholder or opens a brand-new row
depending on what it finds. This use case never re-activates, overwrites, or
otherwise touches a ``COMPLETED`` project.
"""

from __future__ import annotations

from sirius.application.project_errors import (
    InitialProjectAlreadyConfiguredError,
    InvalidInitialProjectDataError,
)
from sirius.domain.project import (
    INITIAL_PROJECT_NEXT_STEP,
    INITIAL_PROJECT_STATE,
    Project,
    is_configured,
)
from sirius.ports.project_repository import ProjectRepository

__all__ = [
    "InitialProjectAlreadyConfiguredError",
    "InitialProjectUseCase",
    "InvalidInitialProjectDataError",
]


class InitialProjectUseCase:
    """Consulta, crea y expone el proyecto activo único de Sirius (B3a/B3c)."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    def is_configured(self) -> bool:
        """Return whether the active project has already been set up by the user.

        A bootstrap placeholder (empty name/objective) does not count.
        """
        project = self._project_repository.get_active_project()
        return project is not None and is_configured(project)

    def get_active_project(self) -> Project | None:
        """Return the active project, if any, without creating one."""
        return self._project_repository.get_active_project()

    def create_initial_project(self, name: str, objective: str) -> Project:
        """Create the user's next configured project.

        The first time this runs, it completes the bootstrap placeholder
        (or opens a fresh row if none exists). After a project has been
        completed, this creates a new, independent project — the closed one
        is never reused, reactivated, or modified.

        Raises ``InvalidInitialProjectDataError`` if ``name`` or
        ``objective`` is empty after trimming (checked before touching the
        repository at all), and ``InitialProjectAlreadyConfiguredError`` if a
        project is already configured and ``ACTIVE`` (checked before any
        write, so a rejected attempt never modifies the existing project).
        """
        clean_name = name.strip()
        clean_objective = objective.strip()
        if not clean_name or not clean_objective:
            raise InvalidInitialProjectDataError(
                "El nombre y el objetivo del proyecto no pueden estar vacíos."
            )

        current = self._project_repository.get_active_project()
        if current is not None and is_configured(current):
            raise InitialProjectAlreadyConfiguredError(
                "Ya existe un proyecto activo configurado. Complétalo antes de crear uno nuevo."
            )

        return self._project_repository.create_project(
            clean_name,
            clean_objective,
            state_summary=INITIAL_PROJECT_STATE,
            blockers=(),
            next_step=INITIAL_PROJECT_NEXT_STEP,
        )
