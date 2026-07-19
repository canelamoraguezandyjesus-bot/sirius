"""Explicit decision archival (B4d, RF-024, PA-015).

Product S6 "Modelo conceptual": "Decisión — Recuerdo especializado que
expresa una elección propuesta, aprobada, sustituida o archivada." Only an
APPROVED (vigente) decision can be archived
(``sirius.domain.decision.ensure_can_archive``) — mirroring
``ArchiveMemoryUseCase``'s restriction to CURRENT memories: a still-PROPOSED
decision was never part of ordinary context to begin with, and a SUPERSEDED
one is already excluded from it, so archiving neither is a meaningful
transition.

Archiving never touches content or creates a new revision — it only moves
``Decision.status`` from APPROVED to ARCHIVED, which is enough for
``DecisionRepository.list_current_decisions`` to stop surfacing it, while
``get_decision`` keeps it fully consultable
(``list_archived_decisions`` recovers it explicitly).

Nothing in the ordinary conversation flow (``SendMessageUseCase``) calls
this — the absence of any automatic call site is what keeps a conversation
from ever archiving a decision on its own, mirroring PA-011/PA-015's
negative-case guarantee for the other explicit decision/memory operations.

SIRIUS-ARQ-0.1 S8.1's transactional rule still applies: the audit event and
the status change are written through the same ``UnitOfWork`` and committed
together; any failure leaves the transaction uncommitted, so
``UnitOfWork.__exit__`` rolls back everything.
"""

from __future__ import annotations

from sirius.domain.decision import Decision, ensure_can_archive
from sirius.domain.event import DECISION_ARCHIVED_EVENT_TYPE, USER_ACTOR
from sirius.ports.unit_of_work import UnitOfWork

__all__ = [
    "ArchiveDecisionUseCase",
    "DecisionNotArchivableError",
    "UnknownDecisionError",
]


class UnknownDecisionError(LookupError):
    """Raised when ``decision_id`` does not refer to an existing decision."""


class DecisionNotArchivableError(ValueError):
    """Raised when the decision exists but is not currently APPROVED."""


class ArchiveDecisionUseCase:
    """Archiva una decisión aprobada, retirándola del contexto ordinario (RF-024)."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def archive(self, decision_id: int, *, message_id: int | None = None) -> Decision:
        """Move an existing APPROVED decision to ARCHIVED.

        ``message_id`` identifies the user message that gave the explicit
        archive order, when the caller has one; it is recorded on the audit
        event. Raises ``UnknownDecisionError`` for an unknown
        ``decision_id``, or ``DecisionNotArchivableError`` if the decision
        is not currently APPROVED (for example, still PROPOSED or already
        SUPERSEDED/ARCHIVED) — in both cases nothing is written: the check
        happens before the audit event is recorded, and the whole attempt
        still runs inside one transaction that only commits on success.
        """
        with self._unit_of_work as uow:
            try:
                decision = uow.decision_repository.get_decision(decision_id)
            except Exception as exc:
                raise UnknownDecisionError(f"Decisión desconocida: {decision_id}") from exc

            try:
                ensure_can_archive(decision)
            except ValueError as exc:
                raise DecisionNotArchivableError(str(exc)) from exc

            uow.event_repository.append(
                event_type=DECISION_ARCHIVED_EVENT_TYPE,
                actor=USER_ACTOR,
                message_id=message_id,
            )
            archived = uow.decision_repository.archive_decision(decision_id)
            uow.commit()

        return archived
