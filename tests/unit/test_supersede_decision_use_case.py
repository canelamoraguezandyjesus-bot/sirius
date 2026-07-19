from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.supersede_decision import (
    DecisionSupersessionNotConfirmedError,
    InvalidDecisionSupersessionError,
    SupersedeDecisionUseCase,
    UnknownDecisionError,
)
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.event import DECISION_SUPERSEDED_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision


def _decision(
    decision_id: int,
    status: DecisionStatus,
    *,
    subject: str = "Motor de persistencia",
    project_id: int = 1,
) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content=f"contenido {decision_id}",
        source_event_id=3,
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
        raise AssertionError("supersede() must never read an event back")


class _StaticDecisionRepository:
    """Serves fixed decisions by id and records supersession calls."""

    def __init__(self, decisions: dict[int, Decision], *, fail: bool = False) -> None:
        self._decisions = decisions
        self.fail = fail
        self.supersede_calls: list[tuple[int, int]] = []

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("supersede() must never create a proposal")

    def get_decision(self, decision_id: int) -> Decision:
        decision = self._decisions.get(decision_id)
        if decision is None:
            msg = f"Unknown decision id: {decision_id}"
            raise ValueError(msg)
        return decision

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("supersede() must never plainly approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        self.supersede_calls.append((superseded_decision_id, superseding_decision_id))
        if self.fail:
            msg = "simulated supersession failure"
            raise RuntimeError(msg)
        superseded = self._decisions[superseded_decision_id]
        superseding = self._decisions[superseding_decision_id]
        now = datetime.now(UTC)
        self._decisions[superseded_decision_id] = Decision(
            id=superseded.id,
            subject=superseded.subject,
            project_id=superseded.project_id,
            status=DecisionStatus.SUPERSEDED,
            current_revision=superseded.current_revision,
            created_at=superseded.created_at,
            updated_at=now,
            supersedes_decision_id=superseded.supersedes_decision_id,
        )
        result = Decision(
            id=superseding.id,
            subject=superseding.subject,
            project_id=superseding.project_id,
            status=DecisionStatus.APPROVED,
            current_revision=superseding.current_revision,
            created_at=superseding.created_at,
            updated_at=now,
            supersedes_decision_id=superseded_decision_id,
        )
        self._decisions[superseding_decision_id] = result
        return result

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("supersede() must never list decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("supersede() must never read a superseding decision")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("supersede() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("supersede() must never list archived decisions")


class _UnusedMemoryRepository:
    """B4a/B4c's ``UnitOfWork.memory_repository``; ``supersede()`` never touches it."""

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError("supersede() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("supersede() must never read a memory")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("supersede() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("supersede() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("supersede() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("supersede() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("supersede() must never delete a memory")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("supersede() must never list archived memories")


class _UnusedConversationRepository:
    """B4d's ``UnitOfWork.conversation_repository``; ``supersede()`` never touches it."""

    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("supersede() must never touch the conversation")

    def get_main_conversation(self) -> Conversation | None:
        raise AssertionError("supersede() must never touch the conversation")

    def append_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        *,
        operation_id: str | None = None,
        identity_version: int | None = None,
        status: MessageStatus = MessageStatus.COMPLETED,
    ) -> Message:
        raise AssertionError("supersede() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        raise AssertionError("supersede() must never list messages")

    def get_message(self, message_id: int) -> Message | None:
        raise AssertionError("supersede() must never read a message")

    def redact_message(self, message_id: int) -> Message:
        raise AssertionError("supersede() must never redact a message")


class _FakeUnitOfWork:
    def __init__(
        self,
        decision_repository: _StaticDecisionRepository,
        event_repository: _RecordingEventRepository,
    ) -> None:
        self.decision_repository = decision_repository
        self.event_repository = event_repository
        self.memory_repository = _UnusedMemoryRepository()
        self.conversation_repository = _UnusedConversationRepository()
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


def _use_case(
    decisions: dict[int, Decision],
) -> tuple[SupersedeDecisionUseCase, _StaticDecisionRepository, _FakeUnitOfWork]:
    decision_repository = _StaticDecisionRepository(decisions)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    return SupersedeDecisionUseCase(unit_of_work), decision_repository, unit_of_work


def test_supersede_without_confirmation_raises_before_opening_a_transaction() -> None:
    decisions = {
        1: _decision(1, DecisionStatus.APPROVED),
        2: _decision(2, DecisionStatus.PROPOSED),
    }
    use_case, decision_repository, unit_of_work = _use_case(decisions)

    with pytest.raises(DecisionSupersessionNotConfirmedError):
        use_case.supersede(1, 2, confirmed=False)

    assert unit_of_work.enter_count == 0
    assert unit_of_work.event_repository.calls == []
    assert decision_repository.supersede_calls == []


def test_supersede_unknown_superseded_id_fails_safely_without_writing_anything() -> None:
    decisions = {2: _decision(2, DecisionStatus.PROPOSED)}
    use_case, decision_repository, unit_of_work = _use_case(decisions)

    with pytest.raises(UnknownDecisionError):
        use_case.supersede(999, 2, confirmed=True)

    assert unit_of_work.event_repository.calls == []
    assert decision_repository.supersede_calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_supersede_unknown_superseding_id_fails_safely_without_writing_anything() -> None:
    decisions = {1: _decision(1, DecisionStatus.APPROVED)}
    use_case, decision_repository, unit_of_work = _use_case(decisions)

    with pytest.raises(UnknownDecisionError):
        use_case.supersede(1, 999, confirmed=True)

    assert unit_of_work.event_repository.calls == []
    assert decision_repository.supersede_calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_supersede_a_decision_that_is_not_approved_fails_safely_without_writing_anything() -> None:
    decisions = {
        1: _decision(1, DecisionStatus.PROPOSED),
        2: _decision(2, DecisionStatus.PROPOSED),
    }
    use_case, decision_repository, unit_of_work = _use_case(decisions)

    with pytest.raises(InvalidDecisionSupersessionError):
        use_case.supersede(1, 2, confirmed=True)

    assert unit_of_work.event_repository.calls == []
    assert decision_repository.supersede_calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_supersede_with_a_superseding_decision_that_is_not_proposed_fails_safely() -> None:
    decisions = {
        1: _decision(1, DecisionStatus.APPROVED),
        2: _decision(2, DecisionStatus.APPROVED),
    }
    use_case, decision_repository, unit_of_work = _use_case(decisions)

    with pytest.raises(InvalidDecisionSupersessionError):
        use_case.supersede(1, 2, confirmed=True)

    assert unit_of_work.event_repository.calls == []
    assert decision_repository.supersede_calls == []
    assert unit_of_work.rollback_count == 1


def test_supersede_a_decision_with_itself_fails_safely() -> None:
    decisions = {1: _decision(1, DecisionStatus.APPROVED)}
    use_case, decision_repository, unit_of_work = _use_case(decisions)

    with pytest.raises(InvalidDecisionSupersessionError):
        use_case.supersede(1, 1, confirmed=True)

    assert unit_of_work.event_repository.calls == []
    assert decision_repository.supersede_calls == []
    assert unit_of_work.rollback_count == 1


def test_supersede_with_a_mismatched_subject_fails_safely() -> None:
    decisions = {
        1: _decision(1, DecisionStatus.APPROVED, subject="Motor de persistencia"),
        2: _decision(2, DecisionStatus.PROPOSED, subject="Otro asunto"),
    }
    use_case, decision_repository, unit_of_work = _use_case(decisions)

    with pytest.raises(InvalidDecisionSupersessionError):
        use_case.supersede(1, 2, confirmed=True)

    assert decision_repository.supersede_calls == []
    assert unit_of_work.rollback_count == 1


def test_supersede_records_the_event_and_delegates_to_the_repository() -> None:
    decisions = {
        1: _decision(1, DecisionStatus.APPROVED),
        2: _decision(2, DecisionStatus.PROPOSED),
    }
    use_case, decision_repository, unit_of_work = _use_case(decisions)

    result = use_case.supersede(1, 2, confirmed=True, message_id=9)

    assert unit_of_work.event_repository.calls == [(DECISION_SUPERSEDED_EVENT_TYPE, USER_ACTOR, 9)]
    assert decision_repository.supersede_calls == [(1, 2)]
    assert result.status is DecisionStatus.APPROVED
    assert result.supersedes_decision_id == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


def test_supersede_without_a_message_id_still_records_an_event() -> None:
    decisions = {
        1: _decision(1, DecisionStatus.APPROVED),
        2: _decision(2, DecisionStatus.PROPOSED),
    }
    use_case, _, unit_of_work = _use_case(decisions)

    use_case.supersede(1, 2, confirmed=True)

    assert unit_of_work.event_repository.calls == [
        (DECISION_SUPERSEDED_EVENT_TYPE, USER_ACTOR, None)
    ]


def test_supersede_never_commits_when_it_fails_after_the_event_was_recorded() -> None:
    decisions = {
        1: _decision(1, DecisionStatus.APPROVED),
        2: _decision(2, DecisionStatus.PROPOSED),
    }
    decision_repository = _StaticDecisionRepository(decisions, fail=True)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    use_case = SupersedeDecisionUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.supersede(1, 2, confirmed=True)

    assert event_repository.calls == [(DECISION_SUPERSEDED_EVENT_TYPE, USER_ACTOR, None)]
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_supersede_after_a_failed_attempt_can_still_succeed_with_a_fresh_transaction() -> None:
    decisions = {
        1: _decision(1, DecisionStatus.APPROVED),
        2: _decision(2, DecisionStatus.PROPOSED),
    }
    use_case, decision_repository, unit_of_work = _use_case(decisions)
    decision_repository.fail = True
    with pytest.raises(RuntimeError):
        use_case.supersede(1, 2, confirmed=True)

    decision_repository.fail = False
    result = use_case.supersede(1, 2, confirmed=True)

    assert unit_of_work.enter_count == 2
    assert unit_of_work.committed is True
    assert result.status is DecisionStatus.APPROVED
