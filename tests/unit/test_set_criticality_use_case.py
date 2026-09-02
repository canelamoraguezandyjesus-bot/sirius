"""Unit tests for ``SetCriticalityUseCase`` (M18b, ADR-126).

Calcado de ``test_set_category_use_case.py``: dispatch to the right
repository method is all this use case does, so these tests pin exactly
that — which repository gets called, with which arguments (including
``None`` to clear the mark), for each ``CriticalityTargetKind``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sirius.application.set_criticality import CriticalityTargetKind, SetCriticalityUseCase
from sirius.domain.criticality import Criticality
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus

_UNUSED_MEMORY_MESSAGE = "set() must never touch a memory when kind is DECISION"
_UNUSED_DECISION_MESSAGE = "set() must never touch a decision when kind is MEMORY"


def _memory() -> Memory:
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=1,
        memory_id=1,
        version=1,
        content="contenido",
        origin="Guardado manual del usuario",
        source_event_id=None,
        created_at=now,
    )
    return Memory(
        id=1, status=MemoryStatus.CURRENT, current_revision=revision, created_at=now, updated_at=now
    )


def _decision() -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=1, decision_id=1, version=1, content="contenido", source_event_id=None, created_at=now
    )
    return Decision(
        id=1,
        subject="asunto",
        project_id=1,
        status=DecisionStatus.APPROVED,
        current_revision=revision,
        created_at=now,
        updated_at=now,
    )


class _FakeMemoryRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, result: Memory) -> None:
        self._result = result
        self.calls: list[tuple[int, Criticality | None]] = []

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def set_user_criticality(self, memory_id: int, criticality: Criticality | None) -> Memory:
        self.calls.append((memory_id, criticality))
        return self._result

    def list_current_memories_by_criticality(self, levels: Sequence[Criticality]) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)


class _UnusedMemoryRepository:
    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def set_user_criticality(self, memory_id: int, criticality: Criticality | None) -> Memory:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)

    def list_current_memories_by_criticality(self, levels: Sequence[Criticality]) -> list[Memory]:
        raise AssertionError(_UNUSED_MEMORY_MESSAGE)


class _FakeDecisionRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, result: Decision) -> None:
        self._result = result
        self.calls: list[tuple[int, Criticality | None]] = []

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def set_user_criticality(self, decision_id: int, criticality: Criticality | None) -> Decision:
        self.calls.append((decision_id, criticality))
        return self._result

    def list_current_decisions_by_criticality(
        self, levels: Sequence[Criticality]
    ) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)


class _UnusedDecisionRepository:
    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def set_user_criticality(self, decision_id: int, criticality: Criticality | None) -> Decision:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)

    def list_current_decisions_by_criticality(
        self, levels: Sequence[Criticality]
    ) -> list[Decision]:
        raise AssertionError(_UNUSED_DECISION_MESSAGE)


def test_set_writes_a_memory_criticality_unconditionally() -> None:
    result = Memory(
        id=1,
        status=MemoryStatus.CURRENT,
        current_revision=_memory().current_revision,
        created_at=_memory().created_at,
        updated_at=_memory().updated_at,
        criticality=Criticality.CRITICO,
    )
    memory_repository = _FakeMemoryRepository(result)
    use_case = SetCriticalityUseCase(memory_repository, _UnusedDecisionRepository())

    outcome = use_case.set(CriticalityTargetKind.MEMORY, 1, Criticality.CRITICO)

    assert outcome is result
    assert memory_repository.calls == [(1, Criticality.CRITICO)]


def test_set_with_none_clears_a_memory_criticality() -> None:
    result = Memory(
        id=1,
        status=MemoryStatus.CURRENT,
        current_revision=_memory().current_revision,
        created_at=_memory().created_at,
        updated_at=_memory().updated_at,
        criticality=None,
    )
    memory_repository = _FakeMemoryRepository(result)
    use_case = SetCriticalityUseCase(memory_repository, _UnusedDecisionRepository())

    outcome = use_case.set(CriticalityTargetKind.MEMORY, 1, None)

    assert outcome is result
    assert memory_repository.calls == [(1, None)]


def test_set_writes_a_decision_criticality_unconditionally() -> None:
    result = Decision(
        id=1,
        subject="asunto",
        project_id=1,
        status=DecisionStatus.APPROVED,
        current_revision=_decision().current_revision,
        created_at=_decision().created_at,
        updated_at=_decision().updated_at,
        criticality=Criticality.IMPORTANTE,
    )
    decision_repository = _FakeDecisionRepository(result)
    use_case = SetCriticalityUseCase(_UnusedMemoryRepository(), decision_repository)

    outcome = use_case.set(CriticalityTargetKind.DECISION, 1, Criticality.IMPORTANTE)

    assert outcome is result
    assert decision_repository.calls == [(1, Criticality.IMPORTANTE)]
