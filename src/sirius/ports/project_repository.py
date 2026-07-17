"""Persistence contract for the single active project and its revision
history (B3c), independent of SQLAlchemy.
"""

from __future__ import annotations

from typing import Protocol

from sirius.domain.project import Project, ProjectRevision


class ProjectRepository(Protocol):
    """Contract implemented by real and simulated project stores.

    Every write here is transactional and explicit: there is no generic
    ``update_project(**kwargs)`` that could express an arbitrary lifecycle
    transition. Legacy B3b behavior (a single mutable row) is gone —
    continuity updates now append an immutable ``ProjectRevision`` instead
    of overwriting fields in place.
    """

    def get_active_project(self) -> Project | None:
        """Return the single ``ACTIVE`` project, if any, without creating one.

        Never returns a ``COMPLETED`` project. May return an unconfigured
        placeholder (``ACTIVE`` with no revision yet).
        """
        ...

    def get_project(self, project_id: int) -> Project | None:
        """Return a project by id regardless of status, or ``None`` if unknown.

        Used to inspect a closed (``COMPLETED``) project's conserved history;
        never creates anything.
        """
        ...

    def list_project_revisions(self, project_id: int) -> tuple[ProjectRevision, ...]:
        """Return every revision of a project, oldest first.

        Empty for an unconfigured placeholder. Raises ``ValueError`` for an
        unknown project id.
        """
        ...

    def ensure_bootstrap_project(self) -> None:
        """Seed one neutral ``ACTIVE`` placeholder only if the table is
        completely empty; otherwise a strict no-op.

        Never creates a second row, and never touches an existing row —
        active, placeholder, or closed. Intended for
        ``initialize_persistence()`` alone.
        """
        ...

    def create_project(
        self,
        name: str,
        objective: str,
        *,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
    ) -> Project:
        """Create a configured project: the first one ever, or the next one
        after the previous ``ACTIVE`` project was completed.

        Reuses the existing unconfigured ``ACTIVE`` placeholder row (if any)
        by completing it in place with revision 1; inserts a brand-new row
        (new id, revision 1) when no placeholder exists. Never reuses,
        modifies, or reactivates a ``COMPLETED`` project. Raises
        ``ValueError`` if an ``ACTIVE`` *configured* project already exists —
        callers are expected to have already checked this before calling.
        """
        ...

    def append_revision(
        self,
        project_id: int,
        *,
        objective: str,
        state_summary: str,
        blockers: tuple[str, ...],
        next_step: str,
        source_event_id: int | None = None,
    ) -> Project:
        """Create the next revision of an ``ACTIVE``, configured project.

        Never modifies an earlier revision. Raises ``ValueError`` if the
        project does not exist, is not configured, or is not ``ACTIVE``.
        """
        ...

    def complete_active_project(self, project_id: int) -> Project:
        """Mark an ``ACTIVE``, configured project as ``COMPLETED``.

        Changes ``status``, ``is_active``, and ``completed_at`` together, in
        one transaction; never touches the current revision's content or
        creates a new one. Raises ``ValueError`` if the project does not
        exist, is not configured, or is not currently ``ACTIVE``.
        """
        ...
