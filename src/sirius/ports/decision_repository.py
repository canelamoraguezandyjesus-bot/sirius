"""Persistence contract for decisions, independent of SQLAlchemy."""

from __future__ import annotations

from typing import Protocol

from sirius.domain.decision import Decision


class DecisionRepository(Protocol):
    """Contract implemented by real and simulated decision stores.

    Transition rules (mandatory subject/content, legal status transitions)
    live in ``sirius.domain.decision``; implementations are expected to
    enforce them before mutating storage. Only the two operations B4b needs:
    proposing a decision and approving an existing proposal. Correction,
    substitution, archival and deletion belong to later subblocks (B4c/B4d)
    and are not part of this contract yet.
    """

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        """Record a new PROPOSED decision with its first revision.

        ``source_event_id`` (B4b) links the first revision to the event that
        recorded why it was proposed; ``None`` when the caller does not have
        one (e.g. a direct repository call with no explicit-proposal event).
        """
        ...

    def get_decision(self, decision_id: int) -> Decision:
        """Return a decision by id, whatever its status."""
        ...

    def approve_decision(self, decision_id: int) -> Decision:
        """Transition a PROPOSED decision to APPROVED in place.

        Never creates a new revision: content and version stay exactly what
        they were at proposal time. Raises ``ValueError`` if the decision
        does not exist or is not currently PROPOSED.
        """
        ...
