"""Presentation-facing use case for observable project continuity (B3b, D-02).

RF-016 (state, blockers, next step — everything except decisions, which
belong to B4) and RF-017 (recover and summarize the project on resume).
Mirrors ``InitialProjectUseCase``: a small, explicit contract so
``ProjectContinuityWidget`` never touches ``ProjectRepository``, SQLAlchemy,
or SQLite directly (AGENTS.md: dependency direction presentation ->
application -> domain). Kept separate from ``InitialProjectUseCase``, whose
responsibility (first configuration) is distinct from this one (ongoing
continuity of an already-configured project).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius.domain.project import Project, is_configured
from sirius.ports.project_repository import ProjectRepository

__all__ = [
    "InvalidProjectContinuityDataError",
    "ProjectContinuityError",
    "ProjectContinuitySummary",
    "ProjectContinuityUseCase",
    "ProjectNotConfiguredError",
]


class ProjectContinuityError(RuntimeError):
    """Base error for project continuity operations. Messages are always safe:
    they never include tracebacks or infrastructure-specific detail."""


class ProjectNotConfiguredError(ProjectContinuityError):
    """Raised when there is no configured project yet (absent or still the
    bootstrap placeholder)."""


class InvalidProjectContinuityDataError(ProjectContinuityError):
    """Raised when ``current_state`` or ``next_step`` is empty after trimming."""


@dataclass(frozen=True, slots=True)
class ProjectContinuitySummary:
    """Immutable, presentation-ready snapshot of the active project's continuity fields."""

    project_id: int
    name: str
    objective: str
    current_state: str
    blockers: str
    next_step: str
    updated_at: datetime


def _to_summary(project: Project) -> ProjectContinuitySummary:
    return ProjectContinuitySummary(
        project_id=project.id,
        name=project.name,
        objective=project.objective,
        current_state=project.current_state,
        blockers=project.blockers,
        next_step=project.next_step,
        updated_at=project.updated_at,
    )


def _normalize_blockers(raw: str) -> str:
    """Trim exterior whitespace and leading/trailing blank lines, strip each
    remaining line's exterior spaces, and keep interior blank lines and order
    (never interpreted, never split on anything other than newlines).
    """
    lines = [line.strip() for line in raw.splitlines()]
    start = 0
    while start < len(lines) and lines[start] == "":
        start += 1
    end = len(lines)
    while end > start and lines[end - 1] == "":
        end -= 1
    return "\n".join(lines[start:end])


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
        """Update state, blockers, and next step together, in a single write.

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
        clean_blockers = _normalize_blockers(blockers)

        project = self._safe_get_active_project()
        if project is None or not is_configured(project):
            raise ProjectNotConfiguredError("Todavía no hay un proyecto configurado.")

        try:
            updated = self._project_repository.update_project(
                project.id,
                current_state=clean_state,
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
