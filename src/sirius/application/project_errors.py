"""Errors shared by every project use case (B3a/B3b/B3c, D-02).

Consolidated here because ``InitialProjectUseCase``, ``ProjectContinuityUseCase``,
and ``ProjectLifecycleUseCase`` all need to signal "no configured active
project" with identical semantics; duplicating the class across three
sibling modules would let their behavior drift apart over time.
"""

from __future__ import annotations

__all__ = [
    "InitialProjectAlreadyConfiguredError",
    "InvalidInitialProjectDataError",
    "InvalidProjectContinuityDataError",
    "ProjectContinuityError",
    "ProjectLifecycleError",
    "ProjectNotActiveError",
    "ProjectNotConfiguredError",
]


class ProjectContinuityError(RuntimeError):
    """Base error for project use-case operations. Messages are always safe:
    they never include tracebacks or infrastructure-specific detail."""


class ProjectNotConfiguredError(ProjectContinuityError):
    """Raised when there is no configured active project yet (absent or
    still the bootstrap placeholder)."""


class InvalidProjectContinuityDataError(ProjectContinuityError):
    """Raised when ``current_state`` or ``next_step`` is empty after trimming."""


class InvalidInitialProjectDataError(ProjectContinuityError):
    """Raised when the candidate name or objective is empty after trimming."""


class InitialProjectAlreadyConfiguredError(ProjectContinuityError):
    """Raised when a project is already configured.

    The existing project is left completely untouched: this is checked
    before any write, never after.
    """


class ProjectLifecycleError(ProjectContinuityError):
    """Base error for project lifecycle operations (completing a project)."""


class ProjectNotActiveError(ProjectLifecycleError):
    """Raised when the target project is not the current ``ACTIVE`` project
    (already completed, or an unknown id)."""
