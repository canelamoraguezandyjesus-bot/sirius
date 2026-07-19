from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.application.memory_precedence import EvaluateMemoryPrecedenceUseCase
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.knowledge_precedence import PrecedenceOutcome
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus


def _memory(
    memory_id: int, *, subject_key: str | None = "tono", project_id: int | None = 1
) -> Memory:
    now = datetime.now(UTC)
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
        status=MemoryStatus.CURRENT,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        subject_key=subject_key,
        project_id=project_id,
    )


def _decision(decision_id: int, *, subject: str = "tono", project_id: int = 1) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content="decision",
        source_event_id=None,
        created_at=now,
    )
    return Decision(
        id=decision_id,
        subject=subject,
        project_id=project_id,
        status=DecisionStatus.APPROVED,
        current_revision=revision,
        created_at=now,
        updated_at=now,
    )


class _StaticMemoryRepository:
    def __init__(self, memories: list[Memory]) -> None:
        self._memories = memories
        self.list_current_memories_calls = 0

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError("evaluate() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("evaluate() must never read a single memory")

    def list_current_memories(self) -> list[Memory]:
        self.list_current_memories_calls += 1
        return self._memories

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("evaluate() must never list archived memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("evaluate() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("evaluate() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("evaluate() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("evaluate() must never delete a memory")


class _StaticDecisionRepository:
    def __init__(self, decisions: list[Decision]) -> None:
        self._decisions = decisions
        self.list_current_decisions_calls = 0

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("evaluate() must never create a decision proposal")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("evaluate() must never read a single decision")

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("evaluate() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("evaluate() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        self.list_current_decisions_calls += 1
        return self._decisions

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("evaluate() must never read a superseding decision")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("evaluate() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("evaluate() must never list archived decisions")


def test_evaluate_rejects_an_empty_subject_key_before_querying_anything() -> None:
    memory_repository = _StaticMemoryRepository([])
    decision_repository = _StaticDecisionRepository([])
    use_case = EvaluateMemoryPrecedenceUseCase(memory_repository, decision_repository)

    with pytest.raises(ValueError, match="non-empty"):
        use_case.evaluate("   ", 1)

    assert memory_repository.list_current_memories_calls == 0
    assert decision_repository.list_current_decisions_calls == 0


def test_evaluate_reports_no_contenders_for_a_single_uncontested_memory() -> None:
    use_case = EvaluateMemoryPrecedenceUseCase(
        _StaticMemoryRepository([_memory(1)]), _StaticDecisionRepository([])
    )

    resolution = use_case.evaluate("tono", 1)

    assert resolution.outcome is PrecedenceOutcome.NO_CONTENDERS


def test_evaluate_reports_conflict_for_two_incompatible_current_memories() -> None:
    use_case = EvaluateMemoryPrecedenceUseCase(
        _StaticMemoryRepository([_memory(1), _memory(2)]), _StaticDecisionRepository([])
    )

    resolution = use_case.evaluate("tono", 1)

    assert resolution.outcome is PrecedenceOutcome.CONFLICT
    assert resolution.conflict is not None
    assert {memory.id for memory in resolution.conflict.memories} == {1, 2}


def test_evaluate_reports_the_approved_decision_that_prevails() -> None:
    decision = _decision(10)
    use_case = EvaluateMemoryPrecedenceUseCase(
        _StaticMemoryRepository([_memory(1), _memory(2)]),
        _StaticDecisionRepository([decision]),
    )

    resolution = use_case.evaluate("tono", 1)

    assert resolution.outcome is PrecedenceOutcome.DECISION_PREVAILS
    assert resolution.prevailing_decision is decision


def test_evaluate_queries_both_repositories_exactly_once() -> None:
    memory_repository = _StaticMemoryRepository([_memory(1)])
    decision_repository = _StaticDecisionRepository([])
    use_case = EvaluateMemoryPrecedenceUseCase(memory_repository, decision_repository)

    use_case.evaluate("tono", 1)

    assert memory_repository.list_current_memories_calls == 1
    assert decision_repository.list_current_decisions_calls == 1
