"""Domain errors for the Sirius Work Engine core (arquitectura §3.2-3.3).

Every illegal operation raises one of these instead of silently coercing
state, so "toda transición fuera del grafo aprobado falla de forma
explícita" (incidencia #177, requisito 1) holds for both ``WorkItem`` and
``Run``.
"""

from __future__ import annotations


class EngineError(Exception):
    """Base class for every error raised by the Work Engine core."""


class IllegalTransitionError(EngineError):
    """Raised when an operation is attempted from a state the approved graph forbids."""

    def __init__(self, aggregate: str, operation: str, current_state: str) -> None:
        super().__init__(f"cannot {operation} {aggregate} while in state {current_state!r}")
        self.aggregate = aggregate
        self.operation = operation
        self.current_state = current_state


class IllegalPhaseTransitionError(EngineError):
    """Raised when a phase-advancing operation is attempted from a phase the approved cycle forbids.

    Mirrors :class:`IllegalTransitionError` but for the ``fase`` axis
    (arquitectura §3.4: ``PREPARAR -> EJECUTAR -> COMPROBAR -> REVISAR ->
    (REPARAR -> COMPROBAR -> REVISAR)* -> ENTREGAR``), which advances
    independently of ``estado``.
    """

    def __init__(self, aggregate: str, operation: str, current_phase: str) -> None:
        super().__init__(f"cannot {operation} {aggregate} while in phase {current_phase!r}")
        self.aggregate = aggregate
        self.operation = operation
        self.current_phase = current_phase


class DeadlineNotExceededError(EngineError):
    """Raised by ``mark_lost`` when the Run's absolute deadline has not passed yet.

    Arquitectura §3.3: ``LOST`` requires both a state that lacks a
    conclusive ``STATUS`` (checked as an ``IllegalTransitionError``) and the
    absolute deadline having elapsed. The two are independent guards, kept
    as distinct errors so a test can tell which one failed.
    """

    def __init__(self, run_id: str) -> None:
        super().__init__(f"run {run_id} cannot be marked LOST before its deadline elapses")
        self.run_id = run_id


class MutableResourceConflictError(EngineError):
    """Raised when dispatching a Run would collide with an unconfirmed cancellation.

    Arquitectura §3.3: "el despachador tiene prohibido lanzar un sustituto o
    un paso nuevo sobre el mismo recurso mutable" while another Run on that
    resource is ``CANCELLATION_UNCONFIRMED``.
    """

    def __init__(self, recurso_mutable: str, conflicting_run_id: str) -> None:
        super().__init__(
            f"cannot dispatch a run on mutable resource {recurso_mutable!r}: "
            f"run {conflicting_run_id} has an unconfirmed cancellation pending on it"
        )
        self.recurso_mutable = recurso_mutable
        self.conflicting_run_id = conflicting_run_id


class UnknownWorkItemError(EngineError):
    """Raised when a ``work_id`` does not refer to a known WorkItem."""

    def __init__(self, work_id: str) -> None:
        super().__init__(f"unknown work item {work_id!r}")
        self.work_id = work_id


class UnknownRunError(EngineError):
    """Raised when a ``run_id`` does not refer to a known Run."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"unknown run {run_id!r}")
        self.run_id = run_id


class DuplicateIdError(EngineError):
    """Raised when creating an aggregate whose id already exists."""

    def __init__(self, aggregate: str, aggregate_id: str) -> None:
        super().__init__(f"{aggregate} {aggregate_id!r} already exists")
        self.aggregate = aggregate
        self.aggregate_id = aggregate_id
