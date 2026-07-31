"""Domain entities and transition rules for decisions (B4b/B4c/B4d, RF-020,
RF-023, RF-024, PA-011, PA-013, PA-015).

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
``DecisionRevision`` rows. B4d adds the fourth and final state the product
doc's enumeration names — ARCHIVED, the architecture's "ARCHIVADA" (S7.4):
only an APPROVED (vigente) decision can be archived, mirroring
``sirius.domain.memory.ensure_can_archive``'s restriction to CURRENT — a
still-PROPOSED decision was never part of ordinary context to begin with,
and a SUPERSEDED one is already excluded from it. Deletion is deliberately
*not* modeled for decisions in this cut: PA-016 and Product S7 "Reglas de
memoria" both scope elimination to "un recuerdo", and S6's decision-state
enumeration above does not list an eliminated state the way it explicitly
lists "archivada" — so RF-025/DR-012 elimination applies to ``Memory``
only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DecisionStatus(StrEnum):
    """Lifecycle of a decision. A decision is either still a proposal, has
    been explicitly approved, has (B4c) been explicitly superseded by a
    later approved decision of the same subject and project, or has (B4d)
    been explicitly archived. There is no path back from APPROVED or
    SUPERSEDED to PROPOSED, and no path from SUPERSEDED back to APPROVED."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


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


#: Estados desde los que una decisión puede pasar a ser la sustituta vigente.
#: PROPOSED es el caso original de B4c (sustituir aprueba a la vez). APPROVED
#: se admite porque el usuario puede haber aprobado ya la decisión nueva antes
#: de ordenar la sustitución: exigir PROPOSED dejaba las dos vigentes con el
#: mismo peso y sin vínculo, que era exactamente el defecto observado. SUPERSEDED
#: y ARCHIVED quedan fuera: ninguna de las dos es vigente, y de SUPERSEDED no
#: hay camino de vuelta.
SUPERSEDING_STATUSES: frozenset[DecisionStatus] = frozenset(
    {DecisionStatus.PROPOSED, DecisionStatus.APPROVED}
)


def ensure_can_supersede(superseded: Decision, superseding: Decision) -> None:
    """Validate that ``superseding`` may explicitly supersede ``superseded``
    (RF-023, PA-013).

    Solo una decisión APPROVED puede ser sustituida, y solo por una decisión
    PROPOSED o APPROVED (ver ``SUPERSEDING_STATUSES``) del mismo asunto y
    proyecto, nunca por sí misma. Una contradicción entre dos decisiones no
    basta: la sustitución la ordena el usuario de forma explícita, y esta
    función solo valida que el par sea legal.

    Los estados no vuelven atrás (de APPROVED o SUPERSEDED no se regresa a
    PROPOSED, y de SUPERSEDED no se regresa a APPROVED), de modo que la
    monotonía de estados ya impide por sí sola que una cadena de sustituciones
    válidas se cierre sobre sí misma. Aun así, ``SupersedeDecisionUseCase``
    recorre la cadena y rechaza el ciclo de forma explícita, porque esta
    función solo ve dos decisiones y no puede comprobar la cadena completa.
    """
    if superseded.id == superseding.id:
        msg = "A decision cannot supersede itself."
        raise ValueError(msg)
    if superseded.status is not DecisionStatus.APPROVED:
        msg = f"Cannot supersede a decision with status '{superseded.status.value}'."
        raise ValueError(msg)
    if superseding.status not in SUPERSEDING_STATUSES:
        msg = (
            "Only a PROPOSED or APPROVED decision can supersede another; got status "
            f"'{superseding.status.value}'."
        )
        raise ValueError(msg)
    if superseding.subject != superseded.subject or superseding.project_id != superseded.project_id:
        msg = "A decision can only supersede another decision of the same subject and project."
        raise ValueError(msg)


def is_same_subject_and_project(first: Decision, second: Decision) -> bool:
    """Whether two decisions share the conceptual identity
    ``ensure_can_supersede`` requires (RF-023): same subject and project.

    Exposed so callers that need to *narrow* a set of candidates before
    attempting a supersession (e.g. populating a picker) can reuse this
    single criterion instead of re-deriving it from the two fields
    themselves; ``ensure_can_supersede`` remains the authority that
    actually validates and rejects an attempt.
    """
    return first.subject == second.subject and first.project_id == second.project_id


def ensure_can_archive(decision: Decision) -> None:
    """Only an APPROVED (vigente) decision can be archived (RF-024, B4d).

    Mirrors ``sirius.domain.memory.ensure_can_archive``'s restriction to
    CURRENT: a PROPOSED decision was never part of ordinary context, and a
    SUPERSEDED one is already excluded from it, so archiving neither is a
    meaningful transition.
    """
    if decision.status is not DecisionStatus.APPROVED:
        msg = f"Cannot archive a decision with status '{decision.status.value}'."
        raise ValueError(msg)
