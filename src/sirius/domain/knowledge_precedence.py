"""Deterministic precedence and conflict rule across current memories and
approved decisions sharing the same subject and project (B4e, RF-026,
PA-014, DR-011).

DR-011 "Precedencia y conflictos de memoria": "una decisión aprobada
vigente prevalece sobre recuerdos generales incompatibles del mismo
asunto; sin precedencia clara, Sirius pregunta." This module reasons only
about that *structural* boundary — which currently live items share the
same explicit ``subject_key``/``project_id`` (memory) or ``subject``/
``project_id`` (decision), and whether a single approved decision on that
boundary settles the ambiguity. It never inspects free-text content to
judge semantic compatibility: classifying whether two memories "really"
disagree would need an LLM, embeddings or another classifier, explicitly
out of scope for B4e (see the issue's "Fuera de alcance"). Two or more
current memories sharing a subject/project boundary are therefore always
treated as needing a clarifying question unless exactly one approved
decision on that same boundary exists to arbitrate — this function never
picks a "winner" by date, insertion order or any other opaque heuristic
(RF-026: "no elegir silenciosamente").
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from sirius.domain.decision import Decision, DecisionStatus
from sirius.domain.memory import Memory, MemoryStatus

__all__ = [
    "MemoryConflict",
    "PrecedenceOutcome",
    "PrecedenceResolution",
    "resolve_memory_precedence",
]


class PrecedenceOutcome(StrEnum):
    """Result of comparing every current item on one subject/project boundary."""

    NO_CONTENDERS = "no_contenders"
    DECISION_PREVAILS = "decision_prevails"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class MemoryConflict:
    """The exact items an unresolved conflict involves, for a minimal
    clarifying question (PA-014). ``decisions`` is only ever non-empty when
    the ambiguity is between competing decisions themselves (more than one
    approved decision claims the same boundary, an already-inconsistent
    state this rule refuses to arbitrate silently either)."""

    subject_key: str
    project_id: int | None
    memories: tuple[Memory, ...]
    decisions: tuple[Decision, ...]


@dataclass(frozen=True, slots=True)
class PrecedenceResolution:
    """Outcome of ``resolve_memory_precedence``.

    Exactly one of ``prevailing_decision``/``conflict`` is set, matching
    ``outcome``: both ``None`` for ``NO_CONTENDERS``, only
    ``prevailing_decision`` for ``DECISION_PREVAILS``, only ``conflict``
    for ``CONFLICT``.
    """

    outcome: PrecedenceOutcome
    prevailing_decision: Decision | None = None
    conflict: MemoryConflict | None = None


def resolve_memory_precedence(
    subject_key: str,
    project_id: int | None,
    candidate_memories: Iterable[Memory],
    candidate_decisions: Iterable[Decision],
) -> PrecedenceResolution:
    """Decide precedence among every current item on one subject/project.

    Only ``MemoryStatus.CURRENT`` memories and ``DecisionStatus.APPROVED``
    decisions whose subject and project both match are compared; archived,
    deleted, proposed, superseded and archived-decision items never
    participate, regardless of what the caller passes in — callers may pass
    an unfiltered list and rely on this rule to apply the historical
    exclusion itself.

    - Exactly one matching approved decision: it prevails
      (``DECISION_PREVAILS``), traceably (the decision itself is returned).
    - More than one matching approved decision, or two or more matching
      current memories with no single decision to arbitrate: an explicit
      ``CONFLICT``, naming every implicated item.
    - Otherwise (zero or one matching current memory, no decision):
      ``NO_CONTENDERS`` — nothing to resolve.
    """
    same_boundary_memories = tuple(
        memory
        for memory in candidate_memories
        if memory.status is MemoryStatus.CURRENT
        and memory.subject_key == subject_key
        and memory.project_id == project_id
    )
    same_boundary_decisions = tuple(
        decision
        for decision in candidate_decisions
        if decision.status is DecisionStatus.APPROVED
        and decision.subject == subject_key
        and decision.project_id == project_id
    )

    if len(same_boundary_decisions) == 1:
        return PrecedenceResolution(
            outcome=PrecedenceOutcome.DECISION_PREVAILS,
            prevailing_decision=same_boundary_decisions[0],
        )

    if same_boundary_decisions or len(same_boundary_memories) >= 2:
        return PrecedenceResolution(
            outcome=PrecedenceOutcome.CONFLICT,
            conflict=MemoryConflict(
                subject_key=subject_key,
                project_id=project_id,
                memories=same_boundary_memories,
                decisions=same_boundary_decisions,
            ),
        )

    return PrecedenceResolution(outcome=PrecedenceOutcome.NO_CONTENDERS)
