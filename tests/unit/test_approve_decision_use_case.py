from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.approve_decision import (
    ApprovalNotConfirmedError,
    ApproveDecisionUseCase,
    InvalidDecisionStatusError,
    UnknownDecisionError,
)
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.event import DECISION_APPROVED_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision


def _decision(decision_id: int, status: DecisionStatus) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content="Usar SQLite local",
        source_event_id=3,
        created_at=now,
    )
    return Decision(
        id=decision_id,
        subject="Motor de persistencia",
        project_id=1,
        status=status,
        current_revision=revision,
        created_at=now,
        updated_at=now,
    )


class _RecordingEventRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | None]] = []
        self._next_id = 10

    def append(self, event_type: str, actor: str, message_id: int | None) -> Event:
        self.calls.append((event_type, actor, message_id))
        event = Event(
            id=self._next_id,
            event_type=event_type,
            actor=actor,
            message_id=message_id,
            created_at=datetime.now(UTC),
            redacted_at=None,
        )
        self._next_id += 1
        return event

    def get_source(self, event_id: int) -> Event | None:
        raise AssertionError("approve() must never read an event back")


class _StaticDecisionRepository:
    def __init__(self, decision: Decision | None) -> None:
        self._decision = decision
        self.approve_calls: list[int] = []

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("approve() must never create a proposal")

    def get_decision(self, decision_id: int) -> Decision:
        if self._decision is None:
            msg = f"Unknown decision id: {decision_id}"
            raise ValueError(msg)
        return self._decision

    def approve_decision(self, decision_id: int) -> Decision:
        self.approve_calls.append(decision_id)
        assert self._decision is not None
        approved = Decision(
            id=self._decision.id,
            subject=self._decision.subject,
            project_id=self._decision.project_id,
            status=DecisionStatus.APPROVED,
            current_revision=self._decision.current_revision,
            created_at=self._decision.created_at,
            updated_at=datetime.now(UTC),
        )
        self._decision = approved
        return approved


class _UnusedMemoryRepository:
    """B4a's ``UnitOfWork.memory_repository``; ``approve()`` never touches it."""

    def create_memory(
        self, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("approve() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("approve() must never read a memory")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("approve() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("approve() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("approve() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("approve() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("approve() must never delete a memory")


class _FakeUnitOfWork:
    def __init__(
        self,
        decision_repository: _StaticDecisionRepository,
        event_repository: _RecordingEventRepository,
    ) -> None:
        self.decision_repository = decision_repository
        self.event_repository = event_repository
        self.memory_repository = _UnusedMemoryRepository()
        self.enter_count = 0
        self.committed = False
        self.rollback_count = 0

    def __enter__(self) -> Self:
        self.enter_count += 1
        self.committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self.committed:
            self.rollback_count += 1

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False
        self.rollback_count += 1


def test_approve_without_confirmation_raises_before_opening_a_transaction() -> None:
    decision_repository = _StaticDecisionRepository(_decision(1, DecisionStatus.PROPOSED))
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    use_case = ApproveDecisionUseCase(unit_of_work)

    with pytest.raises(ApprovalNotConfirmedError):
        use_case.approve(1, confirmed=False)

    assert unit_of_work.enter_count == 0
    assert event_repository.calls == []
    assert decision_repository.approve_calls == []


def test_approve_unknown_decision_id_fails_safely_without_writing_anything() -> None:
    decision_repository = _StaticDecisionRepository(None)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    use_case = ApproveDecisionUseCase(unit_of_work)

    with pytest.raises(UnknownDecisionError):
        use_case.approve(999, confirmed=True)

    assert event_repository.calls == []
    assert decision_repository.approve_calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_approve_an_already_approved_decision_fails_safely_without_writing_anything() -> None:
    decision_repository = _StaticDecisionRepository(_decision(1, DecisionStatus.APPROVED))
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    use_case = ApproveDecisionUseCase(unit_of_work)

    with pytest.raises(InvalidDecisionStatusError):
        use_case.approve(1, confirmed=True)

    assert event_repository.calls == []
    assert decision_repository.approve_calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_approve_a_proposed_decision_records_an_event_and_flips_status() -> None:
    decision_repository = _StaticDecisionRepository(_decision(1, DecisionStatus.PROPOSED))
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    use_case = ApproveDecisionUseCase(unit_of_work)

    approved = use_case.approve(1, confirmed=True, message_id=42)

    assert approved.status is DecisionStatus.APPROVED
    assert event_repository.calls == [(DECISION_APPROVED_EVENT_TYPE, USER_ACTOR, 42)]
    assert decision_repository.approve_calls == [1]
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


def test_approve_after_a_failed_attempt_can_still_succeed_with_a_fresh_transaction() -> None:
    decision_repository = _StaticDecisionRepository(None)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    use_case = ApproveDecisionUseCase(unit_of_work)

    with pytest.raises(UnknownDecisionError):
        use_case.approve(999, confirmed=True)

    decision_repository._decision = _decision(1, DecisionStatus.PROPOSED)
    approved = use_case.approve(1, confirmed=True)

    assert approved.status is DecisionStatus.APPROVED
    assert unit_of_work.committed is True
