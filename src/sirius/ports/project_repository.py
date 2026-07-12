"""Persistence contract for the single active project, independent of SQLAlchemy."""

from __future__ import annotations

from typing import Protocol

from sirius.domain.project import Project


class ProjectRepository(Protocol):
    """Contract implemented by real and simulated project stores."""

    def get_or_create_active_project(self) -> Project:
        """Return the single active project, creating it with neutral values if absent."""
        ...

    def get_active_project(self) -> Project | None:
        """Return the active project if it exists, without creating it."""
        ...

    def update_project(
        self,
        project_id: int,
        *,
        name: str | None = None,
        objective: str | None = None,
        current_state: str | None = None,
        next_step: str | None = None,
    ) -> Project:
        """Update the given fields of a project, leaving the rest untouched.

        Any argument left as ``None`` is not modified. ``updated_at`` always advances.
        """
        ...
