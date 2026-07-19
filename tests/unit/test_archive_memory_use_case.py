from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.archive_memory import (
    ArchiveMemoryUseCase,
    MemoryNotArchivableError,
    UnknownMemoryError,
)
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision
from sirius.domain.event import MEMORY_ARCHIVED_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus


def _memory(status: MemoryStatus, *, memory_id: int = 1) -> Memory:
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=1,
        memory_id=memory_id,
        version=1,
        content="preferencia original",
        origin="Guardado manual del usuario",
        source_event_id=3,
        created_at=now,
    )
    return Memory(
        id=memory_id, status=status, current_revision=revision, created_at=now, updated_at=now
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


class _StaticMemoryRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, memory: Memory | None, *, fail: bool = False) -> None:
        self._memory = memory
        self.fail = fail
        self.archive_calls: list[int] = []

    def create_memory(
        self, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("archive() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        if self._memory is None:
            msg = f"Unknown memory id: {memory_id}"
            raise ValueError(msg)
        return self._memory

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("archive() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("archive() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("archive() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        self.archive_calls.append(memory_id)
        if self.fail:
            msg = "simulated archive failure"
            raise RuntimeError(msg)
        assert self._memory is not None
        now = datetime.now(UTC)
        archived = Memory(
            id=self._memory.id,
            status=MemoryStatus.ARCHIVED,
            current_revision=self._memory.current_revision,
            created_at=self._memory.created_at,
            updated_at=now,
        )
        self._memory = archived
        return archived

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("archive() must never delete a memory")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("archive() must never list archived memories")


class _UnusedDecisionRepository:
    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("archive() must never create a decision proposal")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("archive() must never read a decision")

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
        raise AssertionError("archive() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("archive() must never list archived decisions")


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


class _FakeUnitOfWork:
    """In-memory stand-in for ``SqliteUnitOfWork``: same commit/rollback contract."""

    def __init__(
        self,
        memory_repository: _StaticMemoryRepository,
        event_repository: _RecordingEventRepository,
    ) -> None:
        self.memory_repository = memory_repository
        self.event_repository = event_repository
        self.decision_repository = _UnusedDecisionRepository()
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
    memory: Memory | None,
) -> tuple[ArchiveMemoryUseCase, _StaticMemoryRepository, _FakeUnitOfWork]:
    memory_repository = _StaticMemoryRepository(memory)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository)
    return ArchiveMemoryUseCase(unit_of_work), memory_repository, unit_of_work


def test_archive_unknown_memory_id_fails_safely_without_writing_anything() -> None:
    use_case, memory_repository, unit_of_work = _use_case(None)

    with pytest.raises(UnknownMemoryError):
        use_case.archive(999)

    assert memory_repository.archive_calls == []
    assert unit_of_work.event_repository.calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


@pytest.mark.parametrize("status", [MemoryStatus.ARCHIVED, MemoryStatus.DELETED])
def test_archive_a_non_archivable_memory_fails_safely_without_writing_anything(
    status: MemoryStatus,
) -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(status))

    with pytest.raises(MemoryNotArchivableError):
        use_case.archive(1)

    assert memory_repository.archive_calls == []
    assert unit_of_work.event_repository.calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_archive_records_the_event_and_delegates_to_the_repository() -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    archived = use_case.archive(1, message_id=7)

    assert unit_of_work.event_repository.calls == [(MEMORY_ARCHIVED_EVENT_TYPE, USER_ACTOR, 7)]
    assert memory_repository.archive_calls == [1]
    assert archived.status is MemoryStatus.ARCHIVED
    assert archived.current_revision.content == "preferencia original"


def test_archive_commits_the_unit_of_work_exactly_once_on_success() -> None:
    use_case, _, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    use_case.archive(1)

    assert unit_of_work.enter_count == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


def test_archive_without_a_message_id_still_records_an_event() -> None:
    use_case, _, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    use_case.archive(1)

    assert unit_of_work.event_repository.calls == [(MEMORY_ARCHIVED_EVENT_TYPE, USER_ACTOR, None)]


def test_archive_never_commits_when_the_status_change_fails_after_the_event_was_recorded() -> None:
    memory_repository = _StaticMemoryRepository(_memory(MemoryStatus.CURRENT), fail=True)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository)
    use_case = ArchiveMemoryUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.archive(1)

    assert event_repository.calls == [(MEMORY_ARCHIVED_EVENT_TYPE, USER_ACTOR, None)]
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_archive_after_a_failed_attempt_can_still_succeed_with_a_fresh_transaction() -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))
    memory_repository.fail = True
    with pytest.raises(RuntimeError):
        use_case.archive(1)

    memory_repository.fail = False
    archived = use_case.archive(1)

    assert unit_of_work.enter_count == 2
    assert unit_of_work.committed is True
    assert archived.status is MemoryStatus.ARCHIVED
