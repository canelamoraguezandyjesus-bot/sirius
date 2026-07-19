"""Deterministic subject-level precedence and conflict detection (B4e, RF-026,
PA-014, DR-011).

DR-011 "Precedencia y conflictos de memoria": "una decisión aprobada vigente
prevalece sobre recuerdos generales incompatibles del mismo asunto; sin
precedencia clara, Sirius pregunta." RF-026 "Detectar conflicto: no elegir
silenciosamente entre recuerdos vigentes incompatibles."

Sirius has no semantic understanding of memory content (no LLM judgement, no
embeddings, no classifier — see B4_EXECUTION.md's explicit exclusions), so
this module never tries to decide *whether* two records are about the same
thing from their text. It only compares the explicit, caller-supplied
``subject_key``/``project_id`` pairing memories (``sirius.domain.memory``)
and decisions (``sirius.domain.decision``) already carry: two or more current
records sharing that same explicit pairing, with no unambiguous prevailing
decision, are exactly the ambiguity DR-011 requires Sirius to surface instead
of resolving. This is a deliberate, minimal, structural reading of
"incompatible": nothing here inspects ``content`` or ``origin``, and nothing
here picks a winner by ``created_at``, insertion order, or any other opaque
score — the functions below only ever report ``NO_CONFLICT``,
``DECISION_PRECEDENCE`` (naming which decision prevails and why), or
``CONFLICT`` (naming every item involved), never a chosen memory.

Only items that are actually vigente participate: ``MemoryStatus.CURRENT``
memories and ``DecisionStatus.APPROVED`` decisions. A ``PROPOSED``,
``SUPERSEDED`` or ``ARCHIVED`` decision grants no precedence (mirrors
``sirius.domain.decision.DecisionStatus``'s own state machine); an
``ARCHIVED`` or ``DELETED`` memory never enters conflict or ordinary context
(already excluded by ``list_current_memories``/``ContextBuilder``, see
B4d) — this module re-checks status itself so it stays correct even when
called with an unfiltered list.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from sirius.domain.decision import Decision, DecisionStatus
from sirius.domain.memory import Memory, MemoryStatus

__all__ = [
    "PrecedenceOutcome",
    "SubjectPrecedenceResult",
    "evaluate_subject_precedence",
    "find_prevailing_decision",
    "find_subject_conflicts",
]


class PrecedenceOutcome(StrEnum):
    """The three, and only three, results precedence evaluation can reach."""

    NO_CONFLICT = "no_conflict"
    DECISION_PRECEDENCE = "decision_precedence"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class SubjectPrecedenceResult:
    """The precedence outcome for one explicit ``(subject_key, project_id)``
    pairing.

    ``prevailing_decision`` is set only for ``DECISION_PRECEDENCE`` — the
    single, unambiguous APPROVED decision that prevails, kept for
    traceability (DR-011: "queda trazable como fuente de precedencia").
    ``conflicting_memories``/``conflicting_decisions`` are set only for
    ``CONFLICT`` — every current item sharing the subject with no
    unambiguous precedent, so a future caller (B4f) can present exactly what
    needs clarification without re-deriving it.
    """

    subject_key: str
    project_id: int
    outcome: PrecedenceOutcome
    prevailing_decision: Decision | None = None
    conflicting_memories: tuple[Memory, ...] = field(default_factory=tuple)
    conflicting_decisions: tuple[Decision, ...] = field(default_factory=tuple)


def _current_memories_for_subject(
    subject_key: str, project_id: int, memories: Sequence[Memory]
) -> tuple[Memory, ...]:
    matching = (
        memory
        for memory in memories
        if memory.status is MemoryStatus.CURRENT
        and memory.subject_key == subject_key
        and memory.project_id == project_id
    )
    # Sorted by id, never left in caller-supplied order: the result must be
    # exactly reproducible regardless of how the caller happened to list its
    # memories, matching this module's determinism guarantee.
    return tuple(sorted(matching, key=lambda memory: memory.id))


def _approved_decisions_for_subject(
    subject_key: str, project_id: int, decisions: Sequence[Decision]
) -> tuple[Decision, ...]:
    matching = (
        decision
        for decision in decisions
        if decision.status is DecisionStatus.APPROVED
        and decision.subject == subject_key
        and decision.project_id == project_id
    )
    return tuple(sorted(matching, key=lambda decision: decision.id))


def find_prevailing_decision(
    subject_key: str, project_id: int, decisions: Sequence[Decision]
) -> Decision | None:
    """Return the single APPROVED decision for this subject/project, or
    ``None`` when there is none — or, deliberately, when more than one
    exists: that anomaly is itself an unresolved ambiguity this function
    refuses to pick a winner from silently. Callers that need that detail use
    ``evaluate_subject_precedence`` instead."""
    approved = _approved_decisions_for_subject(subject_key, project_id, decisions)
    return approved[0] if len(approved) == 1 else None


def evaluate_subject_precedence(
    subject_key: str,
    project_id: int,
    memories: Sequence[Memory],
    decisions: Sequence[Decision],
) -> SubjectPrecedenceResult:
    """Decide the precedence outcome for one explicit subject/project pairing.

    - Exactly one APPROVED decision for this subject/project prevails over
      every current memory of the same subject/project, regardless of how
      many there are (DR-011).
    - More than one APPROVED decision, or (with none prevailing) more than
      one current memory, is a ``CONFLICT``: Sirius never picks among them.
    - Otherwise (zero or one current memory, no decision) there is nothing to
      resolve.
    """
    current_memories = _current_memories_for_subject(subject_key, project_id, memories)
    approved_decisions = _approved_decisions_for_subject(subject_key, project_id, decisions)

    if len(approved_decisions) == 1:
        return SubjectPrecedenceResult(
            subject_key=subject_key,
            project_id=project_id,
            outcome=PrecedenceOutcome.DECISION_PRECEDENCE,
            prevailing_decision=approved_decisions[0],
        )

    if len(approved_decisions) > 1 or len(current_memories) > 1:
        return SubjectPrecedenceResult(
            subject_key=subject_key,
            project_id=project_id,
            outcome=PrecedenceOutcome.CONFLICT,
            conflicting_memories=current_memories,
            conflicting_decisions=approved_decisions,
        )

    return SubjectPrecedenceResult(
        subject_key=subject_key,
        project_id=project_id,
        outcome=PrecedenceOutcome.NO_CONFLICT,
    )


def find_subject_conflicts(
    memories: Sequence[Memory], decisions: Sequence[Decision]
) -> tuple[SubjectPrecedenceResult, ...]:
    """Evaluate every explicit ``(subject_key, project_id)`` pairing that
    appears in a current memory or an approved decision, returning only the
    ones whose outcome is ``CONFLICT`` (PA-014).

    Deterministic regardless of input order: subjects are evaluated in
    sorted order, never insertion or discovery order.
    """
    subjects: set[tuple[str, int]] = set()
    for memory in memories:
        if (
            memory.status is MemoryStatus.CURRENT
            and memory.subject_key is not None
            and memory.project_id is not None
        ):
            subjects.add((memory.subject_key, memory.project_id))
    for decision in decisions:
        if decision.status is DecisionStatus.APPROVED:
            subjects.add((decision.subject, decision.project_id))

    results = (
        evaluate_subject_precedence(subject_key, project_id, memories, decisions)
        for subject_key, project_id in sorted(subjects)
    )
    return tuple(result for result in results if result.outcome is PrecedenceOutcome.CONFLICT)
