"""Presentation-facing use case for the first configured project (B3a, D-02).

RF-014 (create with name and objective), RF-015 (a single active project),
and the initial slice of RF-016 (a minimal, safe initial state and next
step). Mirrors ``ApiKeySettingsUseCase``: a small, explicit contract so
``InitialProjectWindow`` never touches ``ProjectRepository``, SQLAlchemy, or
SQLite directly (AGENTS.md: dependency direction presentation -> application
-> domain).
"""

from __future__ import annotations

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


class InvalidInitialProjectDataError(RuntimeError):
    """Raised when the candidate name or objective is empty after trimming."""


class InitialProjectAlreadyConfiguredError(RuntimeError):
    """Raised when a project is already configured.

    The existing project is left completely untouched: this is checked
    before any write, never after.
    """


class InitialProjectUseCase:
    """Consulta, crea y expone el proyecto activo único de Sirius (B3a)."""

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
        """Create the user's first project.

        Completes the bootstrap placeholder transactionally (a single row
        may ever have ``is_active`` set — see the database's own unique
        partial index) instead of inserting a second row, so a base created
        before this feature existed stays compatible without migration.

        Raises ``InvalidInitialProjectDataError`` if ``name`` or
        ``objective`` is empty after trimming (checked before touching the
        repository at all), and ``InitialProjectAlreadyConfiguredError`` if a
        project is already configured (checked before any write, so a
        rejected attempt never modifies the existing project).
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
                "Ya existe un proyecto activo configurado. Complétalo o archívalo "
                "antes de crear uno nuevo."
            )

        placeholder = current or self._project_repository.get_or_create_active_project()
        return self._project_repository.update_project(
            placeholder.id,
            name=clean_name,
            objective=clean_objective,
            current_state=INITIAL_PROJECT_STATE,
            next_step=INITIAL_PROJECT_NEXT_STEP,
        )
