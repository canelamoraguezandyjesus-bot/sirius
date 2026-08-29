"""Read-only access to completed projects and their revision history (§5.3).

Mirrors ``DetectPrecedenceConflictsUseCase``: a small, explicit, read-only
contract so a future caller never touches ``ProjectRepository`` directly
(AGENTS.md: dependency direction presentation -> application -> domain).

Neither method ever writes. Deliberately not injected into ``ContextBuilder``
or ``SendMessageUseCase`` — consulting a closed project's history must never
contaminate the active project's context or an ongoing conversation.
"""

from __future__ import annotations

from sirius.domain.project import Project, ProjectRevision
from sirius.ports.project_repository import ProjectRepository

__all__ = ["HistoricalProjectsUseCase"]


class HistoricalProjectsUseCase:
    """Consulta de solo lectura de proyectos completados y su historial."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    def list_completed(self) -> tuple[Project, ...]:
        """Every ``COMPLETED`` project; never the ``ACTIVE`` one, never a side effect."""
        return self._project_repository.list_completed_projects()

    def get_revision_history(self, project_id: int) -> tuple[ProjectRevision, ...]:
        """Full revision history of one project, whatever its status."""
        return self._project_repository.list_project_revisions(project_id)
