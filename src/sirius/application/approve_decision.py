"""Explicit decision approval (B4b, RF-020, PA-011).

PA-011 "No convertir exploración en decisión aprobada": debating or exploring
alternatives never calls this use case, and no other code path transitions a
decision to APPROVED — this is the single, explicit gate RF-020 requires.
``confirmed`` mirrors ``RestoreBackupUseCase.restore_backup(...,
confirmed=True)`` (V7): a caller must pass an explicit ``True`` and cannot
approve merely by calling ``approve()`` with default arguments, so accidental
or implicit approval is not possible even from within this codebase.

Approving never creates a new revision (content and version stay exactly
what they were at proposal time — only a B4c correction changes those); it
only flips ``Decision.status``. SIRIUS-ARQ-0.1 S8.1's rule still applies to
this cross-repository write: the audit event recording the approval and the
decision's status change are written through the same ``UnitOfWork`` and
committed together, mirroring ``SaveManualMemoryUseCase``/
``ProposeDecisionUseCase``.
"""

from __future__ import annotations

from sirius.domain.decision import Decision, ensure_can_approve
from sirius.domain.event import DECISION_APPROVED_EVENT_TYPE, USER_ACTOR
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "ApprovalNotConfirmedError",
    "ApproveDecisionUseCase",
    "InvalidDecisionStatusError",
    "UnknownDecisionError",
]


class UnknownDecisionError(LookupError):
    """Raised when ``decision_id`` does not refer to an existing decision."""


class InvalidDecisionStatusError(ValueError):
    """Raised when the decision exists but is not currently PROPOSED."""


class ApprovalNotConfirmedError(ValueError):
    """Raised when approval is requested without an explicit confirmation."""


class ApproveDecisionUseCase:
    """Aprueba explícitamente una propuesta de decisión ya existente (RF-020)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def approve(
        self, decision_id: int, *, confirmed: bool, message_id: int | None = None
    ) -> Decision:
        """Transition an existing PROPOSED decision to APPROVED.

        Raises ``ApprovalNotConfirmedError`` if ``confirmed`` is not
        ``True``, before touching the database. Raises
        ``UnknownDecisionError`` for an unknown ``decision_id``, or
        ``InvalidDecisionStatusError`` if the decision is not currently
        PROPOSED (for example, already APPROVED) — in both cases nothing is
        written: the check happens before the audit event is recorded, and
        the whole attempt still runs inside one transaction that only
        commits on success.
        """
        if not confirmed:
            msg = "Aprobar una decisión exige una confirmación explícita."
            raise ApprovalNotConfirmedError(msg)

        with self._unit_of_work as uow:
            try:
                decision = uow.decision_repository.get_decision(decision_id)
            except Exception as exc:
                raise UnknownDecisionError(f"Decisión desconocida: {decision_id}") from exc

            try:
                ensure_can_approve(decision)
            except ValueError as exc:
                raise InvalidDecisionStatusError(str(exc)) from exc

            uow.event_repository.append(
                event_type=DECISION_APPROVED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            approved = uow.decision_repository.approve_decision(decision_id)
            uow.commit()

        return approved
