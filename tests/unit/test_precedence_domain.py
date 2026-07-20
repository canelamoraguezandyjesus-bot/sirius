"""Unit tests for the pure B4e precedence/conflict domain rule (RF-026,
PA-014, DR-011). Mirrors the eight mandatory minimal cases from the B4e
issue: no fakes, no SQLite — only ``Memory``/``Decision`` value objects.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.domain.precedence import (
    PrecedenceOutcome,
    evaluate_subject_precedence,
    find_prevailing_decision,
    find_subject_conflicts,
)

_SUBJECT = "Motor de persistencia"
_OTHER_SUBJECT = "Nombre del producto"
_PROJECT = 1
_OTHER_PROJECT = 2


def _memory(
    memory_id: int,
    status: MemoryStatus = MemoryStatus.CURRENT,
    *,
    subject_key: str | None = _SUBJECT,
    project_id: int | None = _PROJECT,
    content: str = "contenido",
) -> Memory:
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=memory_id,
        memory_id=memory_id,
        version=1,
        content=content,
        origin="manual",
        source_event_id=None,
        created_at=now,
    )
    return Memory(
        id=memory_id,
        status=status,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        subject_key=subject_key,
        project_id=project_id,
    )


def _decision(
    decision_id: int,
    status: DecisionStatus = DecisionStatus.APPROVED,
    *,
    subject: str = _SUBJECT,
    project_id: int = _PROJECT,
    content: str = "contenido",
) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content=content,
        source_event_id=None,
        created_at=now,
    )
    return Decision(
        id=decision_id,
        subject=subject,
        project_id=project_id,
        status=status,
        current_revision=revision,
        created_at=now,
        updated_at=now,
    )


# --- Caso 1: dos recuerdos vigentes incompatibles del mismo asunto y proyecto. ---


def test_two_current_memories_of_the_same_subject_and_project_conflict() -> None:
    first = _memory(1)
    second = _memory(2)

    result = evaluate_subject_precedence(_SUBJECT, _PROJECT, [first, second], [])

    assert result.outcome is PrecedenceOutcome.CONFLICT
    assert set(result.conflicting_memories) == {first, second}
    assert result.prevailing_decision is None


# --- Caso 2: una decisión APPROVED vigente prevalece sobre recuerdos de menor autoridad. ---


def test_a_single_approved_decision_prevails_over_incompatible_memories() -> None:
    memory = _memory(1)
    other_memory = _memory(2)
    decision = _decision(10, DecisionStatus.APPROVED)

    result = evaluate_subject_precedence(_SUBJECT, _PROJECT, [memory, other_memory], [decision])

    assert result.outcome is PrecedenceOutcome.DECISION_PRECEDENCE
    assert result.prevailing_decision == decision
    assert result.conflicting_memories == ()


def test_find_prevailing_decision_returns_the_single_approved_decision() -> None:
    decision = _decision(10, DecisionStatus.APPROVED)

    assert find_prevailing_decision(_SUBJECT, _PROJECT, [decision]) == decision


# --- Caso 3: PROPOSED, SUPERSEDED o ARCHIVED no conceden precedencia. ---


@pytest.mark.parametrize(
    "status", [DecisionStatus.PROPOSED, DecisionStatus.SUPERSEDED, DecisionStatus.ARCHIVED]
)
def test_a_non_approved_decision_grants_no_precedence(status: DecisionStatus) -> None:
    memory = _memory(1)
    decision = _decision(10, status)

    result = evaluate_subject_precedence(_SUBJECT, _PROJECT, [memory], [decision])

    assert result.outcome is PrecedenceOutcome.NO_CONFLICT
    assert result.prevailing_decision is None
    assert find_prevailing_decision(_SUBJECT, _PROJECT, [decision]) is None


# --- Caso 4: recuerdos ARCHIVED/DELETED no participan en conflicto. ---


@pytest.mark.parametrize("status", [MemoryStatus.ARCHIVED, MemoryStatus.DELETED])
def test_archived_or_deleted_memories_never_participate_in_conflict(
    status: MemoryStatus,
) -> None:
    current = _memory(1)
    non_current = _memory(2, status)

    result = evaluate_subject_precedence(_SUBJECT, _PROJECT, [current, non_current], [])

    assert result.outcome is PrecedenceOutcome.NO_CONFLICT
    assert result.conflicting_memories == ()


# --- Caso 5: asuntos o proyectos distintos no son conflicto entre sí. ---


def test_different_subjects_never_conflict() -> None:
    same_project_other_subject = _memory(2, subject_key=_OTHER_SUBJECT)
    memory = _memory(1)

    result = evaluate_subject_precedence(
        _SUBJECT, _PROJECT, [memory, same_project_other_subject], []
    )

    assert result.outcome is PrecedenceOutcome.NO_CONFLICT


def test_different_projects_never_conflict() -> None:
    same_subject_other_project = _memory(2, project_id=_OTHER_PROJECT)
    memory = _memory(1)

    result = evaluate_subject_precedence(
        _SUBJECT, _PROJECT, [memory, same_subject_other_project], []
    )

    assert result.outcome is PrecedenceOutcome.NO_CONFLICT


# --- Caso 6: nunca se desempata por fecha u orden de inserción. ---


def test_conflict_never_names_a_winner_regardless_of_creation_order() -> None:
    older = _memory(1)
    newer = _memory(2)

    result_a = evaluate_subject_precedence(_SUBJECT, _PROJECT, [older, newer], [])
    result_b = evaluate_subject_precedence(_SUBJECT, _PROJECT, [newer, older], [])

    assert result_a.outcome is result_b.outcome is PrecedenceOutcome.CONFLICT
    assert (
        set(result_a.conflicting_memories)
        == set(result_b.conflicting_memories)
        == {
            older,
            newer,
        }
    )


def test_more_than_one_approved_decision_for_the_same_subject_is_a_conflict_not_a_silent_pick() -> (
    None
):
    """An anomaly no documented flow can currently produce, but precedence
    must never silently prefer one APPROVED decision over another either."""
    first_decision = _decision(10, DecisionStatus.APPROVED)
    second_decision = _decision(11, DecisionStatus.APPROVED)

    result = evaluate_subject_precedence(_SUBJECT, _PROJECT, [], [first_decision, second_decision])

    assert result.outcome is PrecedenceOutcome.CONFLICT
    assert set(result.conflicting_decisions) == {first_decision, second_decision}
    assert find_prevailing_decision(_SUBJECT, _PROJECT, [first_decision, second_decision]) is None


# --- No conflict trivial case: zero or one current memory, no decision. ---


def test_a_single_current_memory_with_no_decision_is_not_a_conflict() -> None:
    result = evaluate_subject_precedence(_SUBJECT, _PROJECT, [_memory(1)], [])

    assert result.outcome is PrecedenceOutcome.NO_CONFLICT


def test_no_current_memories_and_no_decisions_is_not_a_conflict() -> None:
    result = evaluate_subject_precedence(_SUBJECT, _PROJECT, [], [])

    assert result.outcome is PrecedenceOutcome.NO_CONFLICT


# --- find_subject_conflicts: aggregate, deterministic scan. ---


def test_find_subject_conflicts_returns_only_conflicting_subjects() -> None:
    conflicting_a = _memory(1)
    conflicting_b = _memory(2)
    resolved = _memory(3, subject_key=_OTHER_SUBJECT)
    resolving_decision = _decision(10, DecisionStatus.APPROVED, subject=_OTHER_SUBJECT)

    conflicts = find_subject_conflicts(
        [conflicting_a, conflicting_b, resolved], [resolving_decision]
    )

    assert len(conflicts) == 1
    assert conflicts[0].subject_key == _SUBJECT
    assert conflicts[0].project_id == _PROJECT
    assert set(conflicts[0].conflicting_memories) == {conflicting_a, conflicting_b}


def test_find_subject_conflicts_ignores_memories_and_decisions_with_no_explicit_subject() -> None:
    unrelated_memory = _memory(1, subject_key=None, project_id=None)

    conflicts = find_subject_conflicts([unrelated_memory], [])

    assert conflicts == ()


def test_find_subject_conflicts_is_deterministic_regardless_of_input_order() -> None:
    conflicting_a = _memory(1)
    conflicting_b = _memory(2)
    other_conflicting_a = _memory(3, subject_key=_OTHER_SUBJECT)
    other_conflicting_b = _memory(4, subject_key=_OTHER_SUBJECT)

    forward = find_subject_conflicts(
        [conflicting_a, conflicting_b, other_conflicting_a, other_conflicting_b], []
    )
    backward = find_subject_conflicts(
        [other_conflicting_b, other_conflicting_a, conflicting_b, conflicting_a], []
    )

    assert forward == backward
    assert [r.subject_key for r in forward] == [_SUBJECT, _OTHER_SUBJECT]
