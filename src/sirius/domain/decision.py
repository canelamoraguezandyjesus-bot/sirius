"""Domain entities and transition rules for decisions (B4b, RF-020, PA-011).

Product doc S6 "Modelo conceptual": "Decisión — Recuerdo especializado que
expresa una elección propuesta, aprobada, sustituida o archivada." B4b
implements only the first two states — PROPOSED and APPROVED — mirroring the
architecture's ``knowledge_item``/``knowledge_revision`` split
(SIRIUS-ARQ-0.1 S7.1/S7.3): subject, project and status are properties of
the decision itself (like ``knowledge_item.subject_key``/``project_id``/
``status``); content and origin live on its revision (like
``knowledge_revision.content``/``source_event_id``). Substitution
(SUPERSEDED) and archival (ARCHIVED) belong to B4c/B4d and are not modeled
here — adding those states now would be exactly the kind of unrequested
expansion AGENTS.md forbids.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DecisionStatus(StrEnum):
    """Lifecycle of a decision. Only the two states B4b needs: a decision is
    either still a proposal, or has been explicitly approved. There is no
    path back from APPROVED to PROPOSED."""

    PROPOSED = "proposed"
    APPROVED = "approved"


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
    """

    id: int
    subject: str
    project_id: int
    status: DecisionStatus
    current_revision: DecisionRevision
    created_at: datetime
    updated_at: datetime


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
