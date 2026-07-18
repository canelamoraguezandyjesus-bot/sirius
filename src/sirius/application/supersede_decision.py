"""Explicit decision supersession (B4c, RF-023, PA-013).

RF-023 "Sustituir: Relacionar la decisión vigente con la sustituida." PA-013
"Aprobar una decisión que reemplaza otra: solo la nueva entra en contexto y
existe enlace de sustitución." Substitution and the approval it requires
happen together, in one explicit call: the decision being replaced must
already be APPROVED, and the decision replacing it must still be PROPOSED —
this use case is what turns the latter into APPROVED while marking the
former SUPERSEDED and recording the persistent link between them.

Nothing in the ordinary conversation flow (``SendMessageUseCase``) calls
this — the absence of any automatic call site is what keeps free-form
conversation, including debating alternatives, from ever superseding a
decision on its own (mirrors B4a/B4b's PA-010/PA-011 guarantee).

``confirmed`` mirrors ``ApproveDecisionUseCase``/``RestoreBackupUseCase``: a
caller must pass an explicit ``True`` and cannot supersede (which approves
the substitute) merely by calling ``supersede()`` with default arguments —
required because this call, like a plain approval, moves a decision to
APPROVED.

SIRIUS-ARQ-0.1 S8.1's transactional rule still applies: the audit event,
the status change on both decisions, and the substitution link are written
through the same ``UnitOfWork`` and committed together; any failure leaves
the transaction uncommitted and everything rolls back — the superseded
decision stays APPROVED, the substitute stays PROPOSED, and no link is
recorded.
"""

from __future__ import annotations

from sirius.domain.decision import Decision, ensure_can_supersede
from sirius.domain.event import DECISION_SUPERSEDED_EVENT_TYPE, USER_ACTOR
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "DecisionSupersessionNotConfirmedError",
    "InvalidDecisionSupersessionError",
    "SupersedeDecisionUseCase",
    "UnknownDecisionError",
]


class UnknownDecisionError(LookupError):
    """Raised when either decision id does not refer to an existing decision."""


class InvalidDecisionSupersessionError(ValueError):
    """Raised when the two decisions cannot legally form a supersession relationship."""


class DecisionSupersessionNotConfirmedError(ValueError):
    """Raised when a supersession is requested without an explicit confirmation."""


class SupersedeDecisionUseCase:
    """Sustituye explícitamente una decisión aprobada por otra propuesta (RF-023)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def supersede(
        self,
        superseded_decision_id: int,
        superseding_decision_id: int,
        *,
        confirmed: bool,
        message_id: int | None = None,
    ) -> Decision:
        """Mark ``superseded_decision_id`` as SUPERSEDED and approve
        ``superseding_decision_id`` in its place.

        Raises ``DecisionSupersessionNotConfirmedError`` if ``confirmed`` is
        not ``True``, before touching the database. Raises
        ``UnknownDecisionError`` if either id does not refer to an existing
        decision, or ``InvalidDecisionSupersessionError`` if the pair does
        not satisfy ``sirius.domain.decision.ensure_can_supersede`` (the
        superseded decision is not currently APPROVED, the superseding one
        is not currently PROPOSED, they are the same decision, or they do
        not share the same subject and project) — in every case nothing is
        written: both checks happen before the audit event is recorded, and
        the whole attempt still runs inside one transaction that only
        commits on success.
        """
        if not confirmed:
            msg = "Sustituir una decisión aprobada exige una confirmación explícita."
            raise DecisionSupersessionNotConfirmedError(msg)

        with self._unit_of_work as uow:
            try:
                superseded = uow.decision_repository.get_decision(superseded_decision_id)
                superseding = uow.decision_repository.get_decision(superseding_decision_id)
            except Exception as exc:
                raise UnknownDecisionError(
                    f"Decisión desconocida: {superseded_decision_id} o {superseding_decision_id}"
                ) from exc

            try:
                ensure_can_supersede(superseded, superseding)
            except ValueError as exc:
                raise InvalidDecisionSupersessionError(str(exc)) from exc

            uow.event_repository.append(
                event_type=DECISION_SUPERSEDED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            result = uow.decision_repository.supersede_decision(
                superseded_decision_id, superseding_decision_id
            )
            uow.commit()

        return result
