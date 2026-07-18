"""Presentation-facing use case for observable project continuity (B3b/B3c, D-02).

RF-016 (state, blockers, next step — everything except decisions, which
belong to B4) and RF-017 (recover and summarize the project on resume).
Mirrors ``InitialProjectUseCase``: a small, explicit contract so
``ProjectContinuityWidget`` never touches ``ProjectRepository``, SQLAlchemy,
or SQLite directly (AGENTS.md: dependency direction presentation ->
application -> domain). Kept separate from ``InitialProjectUseCase``, whose
responsibility (first configuration) is distinct from this one (ongoing
continuity of an already-configured project).

Since B3c, ``update()`` never overwrites the active project's fields in
place: it appends a new, immutable ``ProjectRevision`` on top of the current
one. The project's ``objective`` is preserved from the current revision —
this use case never changes it (only ``InitialProjectUseCase`` sets an
objective, at creation time).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius.application.project_errors import (
    InvalidProjectContinuityDataError,
    ProjectContinuityError,
    ProjectNotConfiguredError,
)
from sirius.domain.project import Project, blockers_to_text, is_configured, normalize_blockers
from sirius.ports.project_repository import ProjectRepository

__all__ = [
    "InvalidProjectContinuityDataError",
    "ProjectContinuityError",
    "ProjectContinuitySummary",
    "ProjectContinuityUseCase",
    "ProjectNotConfiguredError",
]


@dataclass(frozen=True, slots=True)
class ProjectContinuitySummary:
    """Immutable, presentation-ready snapshot of the active project's continuity fields."""

    project_id: int
    name: str
    objective: str
    current_state: str
    blockers: str
    next_step: str
    revision_version: int
    updated_at: datetime


def _to_summary(project: Project) -> ProjectContinuitySummary:
    revision = project.current_revision
    assert revision is not None  # guaranteed by is_configured() checks below
    return ProjectContinuitySummary(
        project_id=project.id,
        name=project.name,
        objective=revision.objective,
        current_state=revision.state_summary,
        blockers=blockers_to_text(revision.blockers),
        next_step=revision.next_step,
        revision_version=revision.version,
        updated_at=project.updated_at,
    )


class ProjectContinuityUseCase:
    """Consulta y actualiza la continuidad (estado, bloqueos, siguiente paso)
    del proyecto activo ya configurado."""

    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    def get_summary(self) -> ProjectContinuitySummary:
        """Return the authoritative continuity summary.

        Never creates a project as a side effect of reading. Raises
        ``ProjectNotConfiguredError`` if no project exists yet or it is
        still the neutral bootstrap placeholder — that placeholder is never
        returned as a valid summary.
        """
        project = self._safe_get_active_project()
        if project is None or not is_configured(project):
            raise ProjectNotConfiguredError("Todavía no hay un proyecto configurado.")
        return _to_summary(project)

    def update(self, current_state: str, blockers: str, next_step: str) -> ProjectContinuitySummary:
        """Append a new revision with an updated state, blockers, and next step.

        Raises ``InvalidProjectContinuityDataError`` if ``current_state`` or
        ``next_step`` is empty after trimming (checked before touching the
        repository at all; blank blockers are allowed). Raises
        ``ProjectNotConfiguredError`` if no project is configured yet.
        """
        clean_state = current_state.strip()
        clean_next_step = next_step.strip()
        if not clean_state:
            raise InvalidProjectContinuityDataError("El estado actual no puede estar vacío.")
        if not clean_next_step:
            raise InvalidProjectContinuityDataError("El siguiente paso no puede estar vacío.")
        clean_blockers = normalize_blockers(blockers)

        project = self._safe_get_active_project()
        if project is None or not is_configured(project):
            raise ProjectNotConfiguredError("Todavía no hay un proyecto configurado.")
        assert project.current_revision is not None

        try:
            updated = self._project_repository.append_revision(
                project.id,
                objective=project.current_revision.objective,
                state_summary=clean_state,
                blockers=clean_blockers,
                next_step=clean_next_step,
            )
        except Exception as exc:
            raise ProjectContinuityError("No se pudo actualizar el proyecto.") from exc
        return _to_summary(updated)

    def _safe_get_active_project(self) -> Project | None:
        try:
            return self._project_repository.get_active_project()
        except Exception as exc:
            raise ProjectContinuityError("No se pudo consultar el proyecto activo.") from exc
