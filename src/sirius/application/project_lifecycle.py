"""Presentation-facing use case for completing the active project (B3c, D-02).

RF-018 ("Marcarlo completado sin borrar su historial"): closes the current
``ACTIVE`` project without deleting any of its conserved history, and
without opening a replacement — creating the next project is a separate,
deliberate action the user takes afterward, through
``InitialProjectUseCase.create_initial_project``. Mirrors
``InitialProjectUseCase``/``ProjectContinuityUseCase``: ``MainWindow`` and
``ProjectContinuityWidget`` never touch ``ProjectRepository``, SQLAlchemy,
or SQLite directly (AGENTS.md: dependency direction presentation ->
application -> domain).
"""

from __future__ import annotations

from sirius.application.project_errors import ProjectLifecycleError, ProjectNotConfiguredError
from sirius.domain.project import Project, is_configured
from sirius.ports.project_repository import ProjectRepository

__all__ = [
    "ProjectLifecycleError",
    "ProjectLifecycleUseCase",
    "ProjectNotConfiguredError",
]


class ProjectLifecycleUseCase:
    """Completa el proyecto activo, conservando íntegramente su historial (RF-018)."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    def get_active_project(self) -> Project | None:
        """Return the active project, if any, without completing or creating one."""
        return self._project_repository.get_active_project()

    def complete_active_project(self) -> Project:
        """Mark the current ``ACTIVE``, configured project as ``COMPLETED``.

        Its full revision history stays exactly as it was — nothing is
        deleted, rewritten, or archived. Never creates a next project; that
        remains a separate, explicit step the user takes afterward.

        Raises ``ProjectNotConfiguredError`` if there is no ``ACTIVE``,
        configured project to complete (absent, or still the bootstrap
        placeholder).
        """
        project = self._project_repository.get_active_project()
        if project is None or not is_configured(project):
            raise ProjectNotConfiguredError("Todavía no hay un proyecto configurado.")

        try:
            return self._project_repository.complete_active_project(project.id)
        except Exception as exc:
            raise ProjectLifecycleError("No se pudo completar el proyecto.") from exc
