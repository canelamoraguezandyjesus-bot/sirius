"""Persistence contract for decisions, independent of SQLAlchemy."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sirius.domain.decision import Decision


class DecisionRepository(Protocol):
    """Contract implemented by real and simulated decision stores.

    Transition rules (mandatory subject/content, legal status transitions)
    live in ``sirius.domain.decision``; implementations are expected to
    enforce them before mutating storage. B4b added proposing and approving;
    B4c (RF-023, PA-013) adds explicit substitution and the two ordinary
    queries substitution needs to keep superseded decisions out of the
    vigente set. B4d (RF-024, PA-015) adds explicit archival and the query
    that recovers archived decisions. Correction belongs to memories only
    (B4c); deletion is not part of this contract — approved sources scope
    RF-025/DR-012 elimination to memories only (see
    ``sirius.domain.decision``'s module docstring).
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

        Excludes PROPOSED, SUPERSEDED and ARCHIVED decisions — this is the
        ordinary query B4c/B4d require to never surface a substituted or
        archived decision as if it were still current.
        """
        ...

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        """Return every APPROVED decision with a non-``None`` ``category``,
        filtered in SQL (ADR-121/M13; CODEX-001, incidencia #489). Mirrors
        ``MemoryRepository.list_current_memories_by_category``.
        """
        ...

    def list_proposed_decisions(self) -> list[Decision]:
        """Return every decision whose status is PROPOSED (B4f, RF-020).

        The explicit query the observable surface needs to find decisions
        awaiting an approval or a supersession — mirrors
        ``list_archived_decisions``'s "consulta explícita" pattern for a
        different status.
        """
        ...

    def archive_decision(self, decision_id: int) -> Decision:
        """Remove an APPROVED decision from ordinary context while keeping
        its content (B4d, RF-024). Raises ``ValueError`` if the decision
        does not exist or is not currently APPROVED
        (``sirius.domain.decision.ensure_can_archive``).
        """
        ...

    def list_archived_decisions(self) -> list[Decision]:
        """Return every decision whose status is ARCHIVED (B4d, RF-024).

        The explicit "consulta de archivados" RF-024 requires: unlike
        ``list_current_decisions``, callers use this only when they
        deliberately want archived decisions.
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

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        """Conditionally write an automatic category (D7 point 2,
        SIRIUS-ARQ-0.2 §6.1), for ``TagCategoryUseCase`` only. Mirrors
        ``MemoryRepository.set_category``: a single atomic conditional
        statement, never a read followed by a separate write.
        """
        ...

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        """Unconditionally write ``category`` and set ``category_locked`` to
        ``True``, in the same call, for ``SetCategoryUseCase`` only (D7 point
        3). Mirrors ``MemoryRepository.set_user_category``.
        """
        ...

    def list_uncategorized(self) -> list[Decision]:
        """Return every decision with ``category is None`` and
        ``category_locked is False`` (D7 point 4). Mirrors
        ``MemoryRepository.list_uncategorized``.
        """
        ...
