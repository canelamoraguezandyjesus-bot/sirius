"""Unit tests for ``SetCategoryUseCase`` (D7 punto 3, SIRIUS-ARQ-0.2 §6.1).

Unlike ``TagCategoryUseCase``, this write is never conditional: dispatch to
the right repository method is all this use case does, so these tests pin
exactly that — which repository gets called, with which arguments, for each
``CategoryTargetKind``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sirius.application.set_category import SetCategoryUseCase
from sirius.application.tag_category import CategoryTargetKind
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
        self.calls: list[tuple[int, str]] = []

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
        raise AssertionError("set() must never write a conditional (automatic) category")

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        self.calls.append((memory_id, category))
        return self._result

    def list_uncategorized(self) -> list[Memory]:
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


class _FakeDecisionRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, result: Decision) -> None:
        self._result = result
        self.calls: list[tuple[int, str]] = []

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
        raise AssertionError("set() must never write a conditional (automatic) category")

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        self.calls.append((decision_id, category))
        return self._result

    def list_uncategorized(self) -> list[Decision]:
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


def test_set_writes_a_memory_category_unconditionally() -> None:
    result = Memory(
        id=1,
        status=MemoryStatus.CURRENT,
        current_revision=_memory().current_revision,
        created_at=_memory().created_at,
        updated_at=_memory().updated_at,
        category="trabajo",
        category_locked=True,
    )
    memory_repository = _FakeMemoryRepository(result)
    use_case = SetCategoryUseCase(memory_repository, _UnusedDecisionRepository())

    written = use_case.set(CategoryTargetKind.MEMORY, 1, "trabajo")

    assert written is result
    assert memory_repository.calls == [(1, "trabajo")]


def test_set_writes_a_decision_category_unconditionally() -> None:
    result = Decision(
        id=1,
        subject="asunto",
        project_id=1,
        status=DecisionStatus.APPROVED,
        current_revision=_decision().current_revision,
        created_at=_decision().created_at,
        updated_at=_decision().updated_at,
        category="proyecto",
        category_locked=True,
    )
    decision_repository = _FakeDecisionRepository(result)
    use_case = SetCategoryUseCase(_UnusedMemoryRepository(), decision_repository)

    written = use_case.set(CategoryTargetKind.DECISION, 1, "proyecto")

    assert written is result
    assert decision_repository.calls == [(1, "proyecto")]
