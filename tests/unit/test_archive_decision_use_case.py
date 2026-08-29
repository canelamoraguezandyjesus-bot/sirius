from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.archive_decision import (
    ArchiveDecisionUseCase,
    DecisionNotArchivableError,
    UnknownDecisionError,
)
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.event import DECISION_ARCHIVED_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision
from sirius.domain.memory_suggestion import MemorySuggestion


def _decision(status: DecisionStatus, *, decision_id: int = 1) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=1,
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
        raise AssertionError("archive() must never read an event back")


class _StaticDecisionRepository:
    def __init__(self, decision: Decision | None, *, fail: bool = False) -> None:
        self._decision = decision
        self.fail = fail
        self.archive_calls: list[int] = []

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("archive() must never create a proposal")

    def get_decision(self, decision_id: int) -> Decision:
        if self._decision is None:
            msg = f"Unknown decision id: {decision_id}"
            raise ValueError(msg)
        return self._decision

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("archive() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("archive() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("archive() must never list decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("archive() must never read a superseding decision")

    def archive_decision(self, decision_id: int) -> Decision:
        self.archive_calls.append(decision_id)
        if self.fail:
            msg = "simulated archive failure"
            raise RuntimeError(msg)
        assert self._decision is not None
        now = datetime.now(UTC)
        archived = Decision(
            id=self._decision.id,
            subject=self._decision.subject,
            project_id=self._decision.project_id,
            status=DecisionStatus.ARCHIVED,
            current_revision=self._decision.current_revision,
            created_at=self._decision.created_at,
            updated_at=now,
            supersedes_decision_id=self._decision.supersedes_decision_id,
        )
        self._decision = archived
        return archived

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("archive() must never list archived decisions")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("archive() must never list proposed decisions")


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
        raise AssertionError("archive() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("archive() must never read a memory")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("archive() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("archive() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("archive() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("archive() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("archive() must never delete a memory")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("archive() must never list archived memories")


class _UnusedConversationRepository:
    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("archive() must never touch the conversation")

    def get_main_conversation(self) -> Conversation | None:
        raise AssertionError("archive() must never touch the conversation")

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
        raise AssertionError("archive() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        raise AssertionError("archive() must never list messages")

    def get_message(self, message_id: int) -> Message | None:
        raise AssertionError("archive() must never read a message")

    def redact_message(self, message_id: int) -> Message:
        raise AssertionError("archive() must never redact a message")


class _UnusedMemorySuggestionRepository:
    """M4's ``UnitOfWork.memory_suggestion_repository``; ``archive()`` never touches it."""

    def create_suggestion(
        self,
        content: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> MemorySuggestion:
        raise AssertionError("archive() must never create a memory suggestion")

    def get_suggestion(self, suggestion_id: int) -> MemorySuggestion:
        raise AssertionError("archive() must never read a memory suggestion")

    def list_pending_suggestions(self) -> list[MemorySuggestion]:
        raise AssertionError("archive() must never list memory suggestions")

    def confirm_suggestion(
        self, suggestion_id: int, *, resulting_memory_id: int, resolved_at: datetime
    ) -> MemorySuggestion:
        raise AssertionError("archive() must never confirm a memory suggestion")

    def reject_suggestion(self, suggestion_id: int, *, resolved_at: datetime) -> MemorySuggestion:
        raise AssertionError("archive() must never reject a memory suggestion")


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
        self.memory_suggestion_repository = _UnusedMemorySuggestionRepository()
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
    decision: Decision | None,
) -> tuple[ArchiveDecisionUseCase, _StaticDecisionRepository, _FakeUnitOfWork]:
    decision_repository = _StaticDecisionRepository(decision)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    return ArchiveDecisionUseCase(unit_of_work), decision_repository, unit_of_work


def test_archive_unknown_decision_id_fails_safely_without_writing_anything() -> None:
    use_case, decision_repository, unit_of_work = _use_case(None)

    with pytest.raises(UnknownDecisionError):
        use_case.archive(999)

    assert decision_repository.archive_calls == []
    assert unit_of_work.event_repository.calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


@pytest.mark.parametrize(
    "status", [DecisionStatus.PROPOSED, DecisionStatus.SUPERSEDED, DecisionStatus.ARCHIVED]
)
def test_archive_a_non_approved_decision_fails_safely_without_writing_anything(
    status: DecisionStatus,
) -> None:
    use_case, decision_repository, unit_of_work = _use_case(_decision(status))

    with pytest.raises(DecisionNotArchivableError):
        use_case.archive(1)

    assert decision_repository.archive_calls == []
    assert unit_of_work.event_repository.calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_archive_records_the_event_and_delegates_to_the_repository() -> None:
    use_case, decision_repository, unit_of_work = _use_case(_decision(DecisionStatus.APPROVED))

    archived = use_case.archive(1, message_id=7)

    assert unit_of_work.event_repository.calls == [(DECISION_ARCHIVED_EVENT_TYPE, USER_ACTOR, 7)]
    assert decision_repository.archive_calls == [1]
    assert archived.status is DecisionStatus.ARCHIVED
    assert archived.current_revision.content == "Usar SQLite local"


def test_archive_commits_the_unit_of_work_exactly_once_on_success() -> None:
    use_case, _, unit_of_work = _use_case(_decision(DecisionStatus.APPROVED))

    use_case.archive(1)

    assert unit_of_work.enter_count == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


def test_archive_never_commits_when_the_status_change_fails_after_the_event_was_recorded() -> None:
    decision_repository = _StaticDecisionRepository(_decision(DecisionStatus.APPROVED), fail=True)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    use_case = ArchiveDecisionUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.archive(1)

    assert event_repository.calls == [(DECISION_ARCHIVED_EVENT_TYPE, USER_ACTOR, None)]
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_archive_after_a_failed_attempt_can_still_succeed_with_a_fresh_transaction() -> None:
    use_case, decision_repository, unit_of_work = _use_case(_decision(DecisionStatus.APPROVED))
    decision_repository.fail = True
    with pytest.raises(RuntimeError):
        use_case.archive(1)

    decision_repository.fail = False
    archived = use_case.archive(1)

    assert unit_of_work.enter_count == 2
    assert unit_of_work.committed is True
    assert archived.status is DecisionStatus.ARCHIVED
