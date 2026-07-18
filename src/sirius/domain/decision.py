"""Domain entities and transition rules for decisions (B4b/B4c, RF-020,
RF-023, PA-011, PA-013).

Product doc S6 "Modelo conceptual": "Decisión — Recuerdo especializado que
expresa una elección propuesta, aprobada, sustituida o archivada." B4b
implemented the first two states — PROPOSED and APPROVED — mirroring the
architecture's ``knowledge_item``/``knowledge_revision`` split
(SIRIUS-ARQ-0.1 S7.1/S7.3): subject, project and status are properties of
the decision itself (like ``knowledge_item.subject_key``/``project_id``/
``status``); content and origin live on its revision (like
``knowledge_revision.content``/``source_event_id``). B4c adds the third
state substitution requires — SUPERSEDED, the architecture's "SUSTITUIDA"
(S7.4) — and ``Decision.supersedes_decision_id``, this codebase's
decision-granularity equivalent of the architecture's
``knowledge_revision.supersedes_revision_id`` (S7.3): B4b never gave
decisions more than one revision (approving does not create one), so the
substitution link this cut needs is between two ``Decision`` rows, not two
``DecisionRevision`` rows. Archival (ARCHIVED) still belongs to B4d and is
not modeled here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DecisionStatus(StrEnum):
    """Lifecycle of a decision. A decision is either still a proposal, has
    been explicitly approved, or (B4c) has been explicitly superseded by a
    later approved decision of the same subject and project. There is no
    path back from APPROVED or SUPERSEDED to PROPOSED, and no path from
    SUPERSEDED back to APPROVED."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class DecisionRevision:
    """One immutable, versioned content snapshot of a decision.

    ``source_event_id`` is the real, queryable link to the event that
    recorded why this revision exists — set when the proposal was created
    through ``ProposeDecisionUseCase``. Approving a decision does not create
    a new revision (RF-020's "versión" stays what it was at proposal time
    until a B4c correction); it only changes ``Decision.status``.
    """

    id: int
    decision_id: int
    version: int
    content: str
    source_event_id: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Decision:
    """A decision: its stable identity (subject, project) and current revision.

    ``status`` lives on the decision itself, not the revision — mirroring
    ``Project.status`` (B3c), not ``Memory.status``'s "current revision
    pointer" split, since approving never changes which revision is current.

    ``supersedes_decision_id`` (B4c) is ``None`` for every decision except
    one that became APPROVED by explicitly superseding another; it is the
    persistent, queryable link RF-023 requires between a substitute and the
    decision it replaces. The reverse link (which decision superseded a
    given one, if any) is not stored redundantly here — it is derived by
    querying for the decision whose ``supersedes_decision_id`` matches.
    """

    id: int
    subject: str
    project_id: int
    status: DecisionStatus
    current_revision: DecisionRevision
    created_at: datetime
    updated_at: datetime
    supersedes_decision_id: int | None = None


def ensure_valid_subject(subject: str) -> None:
    """A decision can never be proposed without a non-empty subject (asunto)."""
    if not subject or not subject.strip():
        msg = "A decision requires a non-empty subject."
        raise ValueError(msg)


def ensure_valid_content(content: str) -> None:
    """A decision can never be proposed without non-empty content."""
    if not content or not content.strip():
        msg = "A decision requires non-empty content."
        raise ValueError(msg)


def ensure_can_approve(decision: Decision) -> None:
    """Only a PROPOSED decision can be approved (PA-011: debating never
    approves anything; only an explicit, valid approval call can)."""
    if decision.status is not DecisionStatus.PROPOSED:
        msg = f"Cannot approve a decision with status '{decision.status.value}'."
        raise ValueError(msg)


def ensure_can_supersede(superseded: Decision, superseding: Decision) -> None:
    """Validate that ``superseding`` may explicitly supersede ``superseded``
    (RF-023, PA-013).

    Only an APPROVED decision can be superseded, and only by a still-PROPOSED
    decision (substitution and approval happen together, see
    ``SupersedeDecisionUseCase``) of the same conceptual subject and project
    — never by itself. A decision can never move back to PROPOSED once
    APPROVED or SUPERSEDED, so no chain of valid supersessions can loop back
    on itself: a decision that has ever superseded another can never again
    become PROPOSED, so it can never later be used as the ``superseding``
    side of a call against one of its own ancestors. This function does not
    need a separate cycle check as a result — the ``superseding.status``
    check below already rejects any such attempt.
    """
    if superseded.id == superseding.id:
        msg = "A decision cannot supersede itself."
        raise ValueError(msg)
    if superseded.status is not DecisionStatus.APPROVED:
        msg = f"Cannot supersede a decision with status '{superseded.status.value}'."
        raise ValueError(msg)
    if superseding.status is not DecisionStatus.PROPOSED:
        msg = (
            "Only a PROPOSED decision can supersede another; got status "
            f"'{superseding.status.value}'."
        )
        raise ValueError(msg)
    if superseding.subject != superseded.subject or superseding.project_id != superseded.project_id:
        msg = "A decision can only supersede another decision of the same subject and project."
        raise ValueError(msg)
