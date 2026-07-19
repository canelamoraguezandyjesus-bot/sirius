"""Domain tests for B4e's precedence/conflict rule (RF-026, PA-014, DR-011).

Covers every "caso mínimo obligatorio" from the B4e issue: two incompatible
current memories with no precedence conflict explicitly; an approved
current decision on the same subject/project prevails traceably; a
non-approved decision never grants precedence; archived/deleted memories
never participate; different subjects/projects never collide; and the rule
never breaks a tie by date or insertion order.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.knowledge_precedence import (
    MemoryConflict,
    PrecedenceOutcome,
    PrecedenceResolution,
    resolve_memory_precedence,
)
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus


def _memory(
    *,
    memory_id: int,
    status: MemoryStatus = MemoryStatus.CURRENT,
    subject_key: str | None = "tono de las respuestas",
    project_id: int | None = 1,
    created_at: datetime | None = None,
) -> Memory:
    now = created_at or datetime.now(UTC)
    revision = MemoryRevision(
        id=memory_id,
        memory_id=memory_id,
        version=1,
        content=f"contenido {memory_id}",
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
    *,
    decision_id: int,
    status: DecisionStatus = DecisionStatus.APPROVED,
    subject: str = "tono de las respuestas",
    project_id: int = 1,
) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content=f"decision {decision_id}",
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


# --- Caso 1: dos recuerdos vigentes del mismo asunto y proyecto en conflicto ---


def test_two_current_memories_same_subject_and_project_produce_explicit_conflict() -> None:
    first = _memory(memory_id=1)
    second = _memory(memory_id=2)

    resolution = resolve_memory_precedence("tono de las respuestas", 1, [first, second], [])

    assert resolution.outcome is PrecedenceOutcome.CONFLICT
    assert resolution.prevailing_decision is None
    assert resolution.conflict is not None
    assert set(resolution.conflict.memories) == {first, second}
    assert resolution.conflict.decisions == ()


def test_conflict_never_names_a_single_memory_as_the_winner() -> None:
    """Neither memory is ever selected as vigente for a response: both stay
    in ``conflict.memories``, and ``prevailing_decision`` stays ``None``."""
    first = _memory(memory_id=1)
    second = _memory(memory_id=2)

    resolution = resolve_memory_precedence("tono de las respuestas", 1, [first, second], [])

    assert resolution.prevailing_decision is None
    assert len(resolution.conflict.memories) == 2  # type: ignore[union-attr]


# --- Caso 2: una decisión APROBADA vigente prevalece, de forma trazable ---


def test_approved_current_decision_prevails_over_incompatible_memories() -> None:
    memory = _memory(memory_id=1)
    other_memory = _memory(memory_id=2)
    decision = _decision(decision_id=10)

    resolution = resolve_memory_precedence(
        "tono de las respuestas", 1, [memory, other_memory], [decision]
    )

    assert resolution.outcome is PrecedenceOutcome.DECISION_PREVAILS
    assert resolution.prevailing_decision is decision
    assert resolution.conflict is None


def test_decision_prevailing_is_traceable_to_the_exact_decision() -> None:
    decision = _decision(decision_id=42, subject="ruta de datos", project_id=2)

    resolution = resolve_memory_precedence("ruta de datos", 2, [], [decision])

    assert resolution.prevailing_decision is not None
    assert resolution.prevailing_decision.id == 42


# --- Caso 3: una decisión no aprobada (o no vigente) no concede precedencia ---


@pytest.mark.parametrize(
    "status", [DecisionStatus.PROPOSED, DecisionStatus.SUPERSEDED, DecisionStatus.ARCHIVED]
)
def test_non_approved_decision_grants_no_precedence(status: DecisionStatus) -> None:
    first = _memory(memory_id=1)
    second = _memory(memory_id=2)
    decision = _decision(decision_id=10, status=status)

    resolution = resolve_memory_precedence("tono de las respuestas", 1, [first, second], [decision])

    # The non-approved decision does not settle the ambiguity: two current
    # memories on the same subject/project with no valid arbiter conflict.
    assert resolution.outcome is PrecedenceOutcome.CONFLICT
    assert resolution.prevailing_decision is None
    assert resolution.conflict is not None
    assert decision not in resolution.conflict.decisions


@pytest.mark.parametrize(
    "status", [DecisionStatus.PROPOSED, DecisionStatus.SUPERSEDED, DecisionStatus.ARCHIVED]
)
def test_non_approved_decision_alone_with_a_single_memory_is_uncontended(
    status: DecisionStatus,
) -> None:
    memory = _memory(memory_id=1)
    decision = _decision(decision_id=10, status=status)

    resolution = resolve_memory_precedence("tono de las respuestas", 1, [memory], [decision])

    assert resolution.outcome is PrecedenceOutcome.NO_CONTENDERS


# --- Caso 4: ARCHIVED/DELETED no participan en conflicto ---


@pytest.mark.parametrize("status", [MemoryStatus.ARCHIVED, MemoryStatus.DELETED])
def test_archived_or_deleted_memories_never_participate_in_conflict(
    status: MemoryStatus,
) -> None:
    current = _memory(memory_id=1)
    historical = _memory(memory_id=2, status=status)

    resolution = resolve_memory_precedence("tono de las respuestas", 1, [current, historical], [])

    assert resolution.outcome is PrecedenceOutcome.NO_CONTENDERS


@pytest.mark.parametrize("status", [MemoryStatus.ARCHIVED, MemoryStatus.DELETED])
def test_two_non_current_memories_never_conflict_with_each_other(status: MemoryStatus) -> None:
    first = _memory(memory_id=1, status=status)
    second = _memory(memory_id=2, status=status)

    resolution = resolve_memory_precedence("tono de las respuestas", 1, [first, second], [])

    assert resolution.outcome is PrecedenceOutcome.NO_CONTENDERS


# --- Caso 5: asuntos o proyectos distintos no colisionan ---


def test_different_subject_keys_never_conflict() -> None:
    first = _memory(memory_id=1, subject_key="tono de las respuestas")
    second = _memory(memory_id=2, subject_key="ruta de datos")

    resolution = resolve_memory_precedence("tono de las respuestas", 1, [first, second], [])

    assert resolution.outcome is PrecedenceOutcome.NO_CONTENDERS


def test_different_project_ids_never_conflict() -> None:
    first = _memory(memory_id=1, project_id=1)
    second = _memory(memory_id=2, project_id=2)

    resolution = resolve_memory_precedence("tono de las respuestas", 1, [first, second], [])

    assert resolution.outcome is PrecedenceOutcome.NO_CONTENDERS


def test_a_project_scoped_memory_never_collides_with_a_project_less_one() -> None:
    project_scoped = _memory(memory_id=1, project_id=1)
    unscoped = _memory(memory_id=2, project_id=None)

    resolution = resolve_memory_precedence(
        "tono de las respuestas", 1, [project_scoped, unscoped], []
    )

    assert resolution.outcome is PrecedenceOutcome.NO_CONTENDERS


def test_two_project_less_memories_on_the_same_subject_do_conflict() -> None:
    """``None`` project means "no project boundary", not "wildcard": two
    memories that both explicitly have no project still share that
    boundary and are compared."""
    first = _memory(memory_id=1, project_id=None)
    second = _memory(memory_id=2, project_id=None)

    resolution = resolve_memory_precedence("tono de las respuestas", None, [first, second], [])

    assert resolution.outcome is PrecedenceOutcome.CONFLICT


def test_memories_with_no_subject_key_are_never_selected_by_a_subject_query() -> None:
    unrelated = _memory(memory_id=1, subject_key=None)

    resolution = resolve_memory_precedence("tono de las respuestas", 1, [unrelated], [])

    assert resolution.outcome is PrecedenceOutcome.NO_CONTENDERS


# --- Caso 6: nunca se usa fecha u orden de inserción como desempate ---


def test_precedence_ignores_creation_date_ordering() -> None:
    older = _memory(memory_id=1, created_at=datetime(2020, 1, 1, tzinfo=UTC))
    newer = _memory(memory_id=2, created_at=datetime(2026, 1, 1, tzinfo=UTC))

    # Reversed insertion order must not change the outcome or pick a winner.
    resolution_newest_first = resolve_memory_precedence(
        "tono de las respuestas", 1, [newer, older], []
    )
    resolution_oldest_first = resolve_memory_precedence(
        "tono de las respuestas", 1, [older, newer], []
    )

    assert resolution_newest_first.outcome is PrecedenceOutcome.CONFLICT
    assert resolution_oldest_first.outcome is PrecedenceOutcome.CONFLICT
    assert set(resolution_newest_first.conflict.memories) == {older, newer}  # type: ignore[union-attr]
    assert set(resolution_oldest_first.conflict.memories) == {older, newer}  # type: ignore[union-attr]


# --- Additional robustness: an inconsistent multi-approved-decision state also conflicts ---


def test_more_than_one_approved_decision_on_the_same_boundary_is_a_conflict_too() -> None:
    """An already-inconsistent state (two APPROVED decisions claiming the
    same subject/project — structurally possible even though the ordinary
    supersession flow never produces it) is never silently arbitrated
    either."""
    first_decision = _decision(decision_id=10)
    second_decision = _decision(decision_id=11)

    resolution = resolve_memory_precedence(
        "tono de las respuestas", 1, [], [first_decision, second_decision]
    )

    assert resolution.outcome is PrecedenceOutcome.CONFLICT
    assert resolution.conflict is not None
    assert set(resolution.conflict.decisions) == {first_decision, second_decision}


# --- Result shape sanity ---


def test_no_contenders_when_nothing_matches() -> None:
    resolution = resolve_memory_precedence("asunto sin recuerdos", 1, [], [])

    assert resolution == PrecedenceResolution(outcome=PrecedenceOutcome.NO_CONTENDERS)


def test_memory_conflict_is_immutable() -> None:
    conflict = MemoryConflict(subject_key="x", project_id=1, memories=(), decisions=())

    with pytest.raises(AttributeError):
        conflict.subject_key = "y"  # type: ignore[misc]
