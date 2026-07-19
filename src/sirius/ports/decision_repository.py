"""Persistence contract for decisions, independent of SQLAlchemy."""

from __future__ import annotations

from typing import Protocol

from sirius.domain.decision import Decision


class DecisionRepository(Protocol):
    """Contract implemented by real and simulated decision stores.

    Transition rules (mandatory subject/content, legal status transitions)
    live in ``sirius.domain.decision``; implementations are expected to
    enforce them before mutating storage. B4b added proposing and approving;
    B4c (RF-023, PA-013) adds explicit substitution and the two ordinary
    queries substitution needs to keep superseded decisions out of the
    vigente set. Correction and archival/deletion belong to B4c (memory
    only) and B4d and are not part of this contract.
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

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        """Mark ``superseded_decision_id`` as SUPERSEDED and approve
        ``superseding_decision_id`` in its place, recording the persistent
        link between them (RF-023).

        Never creates a new revision on either decision. Raises
        ``ValueError`` if either id is unknown, or if
        ``sirius.domain.decision.ensure_can_supersede`` rejects the pair
        (self-supersession, wrong statuses, mismatched subject/project).
        Returns the now-APPROVED superseding decision.
        """
        ...

    def list_current_decisions(self) -> list[Decision]:
        """Return every decision whose status is APPROVED (vigente).

        Excludes PROPOSED and SUPERSEDED decisions — this is the ordinary
        query B4c requires to never surface a substituted decision as if it
        were still current.
        """
        ...

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        """Return the decision that supersedes ``decision_id``, or ``None``
        if it has not been superseded (or does not exist).

        Together with the returned decision's own
        ``supersedes_decision_id``, this makes the substitution link
        queryable from either side without a second, redundant column.
        """
        ...
