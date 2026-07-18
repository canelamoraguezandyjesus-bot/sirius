"""Explicit decision proposal (B4b, RF-020 subset, PA-011).

RF-020 "Guardar decisión: Registrar estado, asunto, versión, fecha, proyecto
y origen." PA-011 "No convertir exploración: debatir opciones sin aprobar no
debe dejar ninguna decisión aprobada" — this use case only ever *proposes*:
the decision it creates is always PROPOSED, never APPROVED. Approval is a
separate, later, explicit call (see ``ApproveDecisionUseCase``). Nothing in
the ordinary conversation flow (``SendMessageUseCase``) calls this — the
absence of any automatic call site is what keeps free-form conversation,
including debating or exploring alternatives, from ever creating a decision
on its own.

Mirrors ``SaveManualMemoryUseCase`` (B4a): the event, the decision and its
first revision are written through the same ``UnitOfWork`` and committed
together; any failure leaves nothing behind.
"""

from __future__ import annotations

from sirius.domain.decision import Decision, ensure_valid_content, ensure_valid_subject
from sirius.domain.event import DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "InvalidDecisionProposalDataError",
    "ProposeDecisionUseCase",
]


class InvalidDecisionProposalDataError(ValueError):
    """Raised when the subject or content of a proposed decision is empty."""


class ProposeDecisionUseCase:
    """Registra una propuesta de decisión, sin aprobarla (RF-020, PA-011)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def propose(
        self, subject: str, project_id: int, content: str, *, message_id: int | None = None
    ) -> Decision:
        """Create a new PROPOSED decision from an explicit proposal order.

        ``message_id`` identifies the user message that gave the order, when
        the caller has one; it becomes the real, queryable origin link the
        decision's revision exposes. Raises
        ``InvalidDecisionProposalDataError`` if ``subject`` or ``content`` is
        empty after trimming, checked before any write.

        The event and the decision (with its first revision) are created and
        committed within a single transaction: if either write fails, both
        are rolled back and nothing persists.
        """
        clean_subject = subject.strip()
        clean_content = content.strip()
        try:
            ensure_valid_subject(clean_subject)
            ensure_valid_content(clean_content)
        except ValueError as exc:
            raise InvalidDecisionProposalDataError(str(exc)) from exc

        with self._unit_of_work as uow:
            event = uow.event_repository.append(
                event_type=DECISION_PROPOSED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            decision = uow.decision_repository.create_proposal(
                clean_subject,
                project_id,
                clean_content,
                source_event_id=event.id,
            )
            uow.commit()

        return decision
