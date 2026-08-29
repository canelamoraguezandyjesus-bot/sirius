from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.delete_memory import (
    OLD_BACKUP_WARNING,
    DeleteMemoryUseCase,
    DeletionNotConfirmedError,
    InvalidSourceMessageChoiceError,
    MemoryNotDeletableError,
    UnknownMemoryError,
)
from sirius.domain.conversation import (
    Conversation,
    Message,
    MessageRole,
    MessageStatus,
    SourceMessageChoice,
)
from sirius.domain.decision import Decision
from sirius.domain.event import MEMORY_DELETED_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.domain.memory_suggestion import MemorySuggestion


def _memory(status: MemoryStatus, *, memory_id: int = 1, source_event_id: int | None = 3) -> Memory:
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=1,
        memory_id=memory_id,
        version=1,
        content="preferencia original",
        origin="Guardado manual del usuario",
        source_event_id=source_event_id,
        created_at=now,
    )
    return Memory(
        id=memory_id, status=status, current_revision=revision, created_at=now, updated_at=now
    )


class _RecordingEventRepository:
    def __init__(self, source_events: dict[int, Event] | None = None) -> None:
        self.calls: list[tuple[str, str, int | None]] = []
        self._next_id = 10
        self._source_events = source_events or {}

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
        return self._source_events.get(event_id)


class _StaticMemoryRepository:
    def __init__(self, memory: Memory | None, *, fail: bool = False) -> None:
        self._memory = memory
        self.fail = fail
        self.delete_calls: list[int] = []

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError("delete() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        if self._memory is None:
            msg = f"Unknown memory id: {memory_id}"
            raise ValueError(msg)
        return self._memory

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("delete() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("delete() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("delete() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("delete() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        self.delete_calls.append(memory_id)
        if self.fail:
            msg = "simulated deletion failure"
            raise RuntimeError(msg)
        assert self._memory is not None
        now = datetime.now(UTC)
        deleted_revision = MemoryRevision(
            id=self._memory.current_revision.id,
            memory_id=self._memory.id,
            version=self._memory.current_revision.version,
            content=None,
            origin=self._memory.current_revision.origin,
            source_event_id=self._memory.current_revision.source_event_id,
            created_at=self._memory.current_revision.created_at,
        )
        deleted = Memory(
            id=self._memory.id,
            status=MemoryStatus.DELETED,
            current_revision=deleted_revision,
            created_at=self._memory.created_at,
            updated_at=now,
        )
        self._memory = deleted
        return deleted

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("delete() must never list archived memories")

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("delete() must never set a category")

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError("delete() must never set a category")

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError("delete() must never list uncategorized memories")


class _UnusedDecisionRepository:
    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("delete() must never create a decision proposal")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("delete() must never read a decision")

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("delete() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("delete() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("delete() must never list decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("delete() must never read a superseding decision")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("delete() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("delete() must never list archived decisions")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("delete() must never list proposed decisions")

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("delete() must never set a category")

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError("delete() must never set a category")

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError("delete() must never list uncategorized decisions")


class _RecordingConversationRepository:
    def __init__(self, *, fail: bool = False) -> None:
        self.redact_calls: list[int] = []
        self.fail = fail

    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("delete() must never touch the conversation")

    def get_main_conversation(self) -> Conversation | None:
        raise AssertionError("delete() must never touch the conversation")

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
        raise AssertionError("delete() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        raise AssertionError("delete() must never list messages")

    def get_message(self, message_id: int) -> Message | None:
        raise AssertionError("delete() must never read a message directly")

    def redact_message(self, message_id: int) -> Message:
        self.redact_calls.append(message_id)
        if self.fail:
            msg = "simulated redaction failure"
            raise RuntimeError(msg)
        return Message(
            id=message_id,
            conversation_id=1,
            sequence=1,
            role=MessageRole.USER,
            content=None,
            created_at=datetime.now(UTC),
            status=MessageStatus.REDACTED,
            redacted_at=datetime.now(UTC),
        )


class _UnusedMemorySuggestionRepository:
    """M4's ``UnitOfWork.memory_suggestion_repository``; ``delete()`` never touches it."""

    def create_suggestion(
        self,
        content: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> MemorySuggestion:
        raise AssertionError("delete() must never create a memory suggestion")

    def get_suggestion(self, suggestion_id: int) -> MemorySuggestion:
        raise AssertionError("delete() must never read a memory suggestion")

    def list_pending_suggestions(self) -> list[MemorySuggestion]:
        raise AssertionError("delete() must never list memory suggestions")

    def confirm_suggestion(
        self, suggestion_id: int, *, resulting_memory_id: int, resolved_at: datetime
    ) -> MemorySuggestion:
        raise AssertionError("delete() must never confirm a memory suggestion")

    def reject_suggestion(self, suggestion_id: int, *, resolved_at: datetime) -> MemorySuggestion:
        raise AssertionError("delete() must never reject a memory suggestion")


class _FakeUnitOfWork:
    def __init__(
        self,
        memory_repository: _StaticMemoryRepository,
        event_repository: _RecordingEventRepository,
        conversation_repository: _RecordingConversationRepository | None = None,
    ) -> None:
        self.memory_repository = memory_repository
        self.event_repository = event_repository
        self.decision_repository = _UnusedDecisionRepository()
        self.conversation_repository = conversation_repository or _RecordingConversationRepository()
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
    memory: Memory | None,
    *,
    source_events: dict[int, Event] | None = None,
    conversation_repository: _RecordingConversationRepository | None = None,
) -> tuple[DeleteMemoryUseCase, _StaticMemoryRepository, _FakeUnitOfWork]:
    memory_repository = _StaticMemoryRepository(memory)
    event_repository = _RecordingEventRepository(source_events)
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository, conversation_repository)
    return DeleteMemoryUseCase(unit_of_work), memory_repository, unit_of_work


def test_delete_without_confirmation_raises_before_opening_a_transaction() -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    with pytest.raises(DeletionNotConfirmedError):
        use_case.delete(1, confirmed=False, source_message_choice=SourceMessageChoice.PRESERVE)

    assert unit_of_work.enter_count == 0
    assert memory_repository.delete_calls == []
    assert unit_of_work.event_repository.calls == []


def test_delete_with_an_invalid_source_message_choice_raises_before_opening_a_transaction() -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    with pytest.raises(InvalidSourceMessageChoiceError):
        use_case.delete(1, confirmed=True, source_message_choice="redact")  # type: ignore[arg-type]

    assert unit_of_work.enter_count == 0
    assert memory_repository.delete_calls == []
    assert unit_of_work.event_repository.calls == []


def test_delete_unknown_memory_id_fails_safely_without_writing_anything() -> None:
    use_case, memory_repository, unit_of_work = _use_case(None)

    with pytest.raises(UnknownMemoryError):
        use_case.delete(999, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE)

    assert memory_repository.delete_calls == []
    assert unit_of_work.event_repository.calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_deleting_an_already_deleted_memory_fails_safely_without_writing_anything() -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.DELETED))

    with pytest.raises(MemoryNotDeletableError):
        use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE)

    assert memory_repository.delete_calls == []
    assert unit_of_work.event_repository.calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_delete_accepts_an_archived_memory() -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.ARCHIVED))

    deleted = use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE)

    assert deleted.memory.status is MemoryStatus.DELETED
    assert memory_repository.delete_calls == [1]
    assert unit_of_work.committed is True


def test_delete_preserving_the_source_message_never_calls_redact() -> None:
    conversation_repository = _RecordingConversationRepository()
    use_case, memory_repository, _unit_of_work = _use_case(
        _memory(MemoryStatus.CURRENT, source_event_id=3),
        source_events={3: Event(3, "memory.manual_save", "user", 42, datetime.now(UTC), None)},
        conversation_repository=conversation_repository,
    )

    result = use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE)

    assert conversation_repository.redact_calls == []
    assert result.memory.current_revision.content is None
    assert memory_repository.delete_calls == [1]


def test_delete_redacting_the_source_message_calls_redact_with_the_right_id() -> None:
    conversation_repository = _RecordingConversationRepository()
    use_case, _, unit_of_work = _use_case(
        _memory(MemoryStatus.CURRENT, source_event_id=3),
        source_events={3: Event(3, "memory.manual_save", "user", 42, datetime.now(UTC), None)},
        conversation_repository=conversation_repository,
    )

    use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.REDACT)

    assert conversation_repository.redact_calls == [42]
    assert unit_of_work.committed is True


def test_delete_redacting_with_no_recorded_source_message_is_a_safe_no_op() -> None:
    """A memory with no ``source_event_id`` (predates B4a) has nothing to
    redact; choosing REDACT must not fail, only skip the message step."""
    conversation_repository = _RecordingConversationRepository()
    use_case, _memory_repository, unit_of_work = _use_case(
        _memory(MemoryStatus.CURRENT, source_event_id=None),
        conversation_repository=conversation_repository,
    )

    result = use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.REDACT)

    assert conversation_repository.redact_calls == []
    assert result.memory.status is MemoryStatus.DELETED
    assert unit_of_work.committed is True


def test_delete_redacting_when_the_source_event_has_no_message_is_a_safe_no_op() -> None:
    conversation_repository = _RecordingConversationRepository()
    use_case, _, unit_of_work = _use_case(
        _memory(MemoryStatus.CURRENT, source_event_id=3),
        source_events={3: Event(3, "memory.manual_save", "user", None, datetime.now(UTC), None)},
        conversation_repository=conversation_repository,
    )

    use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.REDACT)

    assert conversation_repository.redact_calls == []
    assert unit_of_work.committed is True


def test_delete_records_the_event_before_redacting_the_message() -> None:
    conversation_repository = _RecordingConversationRepository()
    use_case, _, unit_of_work = _use_case(
        _memory(MemoryStatus.CURRENT, source_event_id=3),
        source_events={3: Event(3, "memory.manual_save", "user", 42, datetime.now(UTC), None)},
        conversation_repository=conversation_repository,
    )

    use_case.delete(
        1, confirmed=True, source_message_choice=SourceMessageChoice.REDACT, message_id=9
    )

    assert unit_of_work.event_repository.calls == [(MEMORY_DELETED_EVENT_TYPE, USER_ACTOR, 9)]
    assert conversation_repository.redact_calls == [42]


def test_delete_exposes_the_old_backup_warning() -> None:
    use_case, _, _ = _use_case(_memory(MemoryStatus.CURRENT))

    result = use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE)

    assert result.old_backup_warning == OLD_BACKUP_WARNING
    assert result.old_backup_warning
    assert "copia" in result.old_backup_warning.lower()


def test_delete_commits_the_unit_of_work_exactly_once_on_success() -> None:
    use_case, _, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE)

    assert unit_of_work.enter_count == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


def test_delete_never_commits_when_content_removal_fails_after_the_event_was_recorded() -> None:
    memory_repository = _StaticMemoryRepository(_memory(MemoryStatus.CURRENT), fail=True)
    event_repository = _RecordingEventRepository()
    conversation_repository = _RecordingConversationRepository()
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository, conversation_repository)
    use_case = DeleteMemoryUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE)

    assert event_repository.calls == [(MEMORY_DELETED_EVENT_TYPE, USER_ACTOR, None)]
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_delete_reverts_an_already_applied_message_redaction_when_content_removal_fails() -> None:
    """The message redaction step runs (against the shared, not-yet-committed
    session) before the memory's own content removal; if that later step
    fails, a real ``SqliteUnitOfWork`` rolls both back together — this fake
    only proves the use case never calls ``commit()`` in that case, leaving
    the whole attempt reversible."""
    memory_repository = _StaticMemoryRepository(
        _memory(MemoryStatus.CURRENT, source_event_id=3), fail=True
    )
    event_repository = _RecordingEventRepository(
        {3: Event(3, "memory.manual_save", "user", 42, datetime.now(UTC), None)}
    )
    conversation_repository = _RecordingConversationRepository()
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository, conversation_repository)
    use_case = DeleteMemoryUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.REDACT)

    assert conversation_repository.redact_calls == [42]
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_delete_never_commits_when_redacting_the_message_fails() -> None:
    conversation_repository = _RecordingConversationRepository(fail=True)
    memory_repository = _StaticMemoryRepository(_memory(MemoryStatus.CURRENT, source_event_id=3))
    event_repository = _RecordingEventRepository(
        {3: Event(3, "memory.manual_save", "user", 42, datetime.now(UTC), None)}
    )
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository, conversation_repository)
    use_case = DeleteMemoryUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.REDACT)

    assert event_repository.calls == [(MEMORY_DELETED_EVENT_TYPE, USER_ACTOR, None)]
    assert memory_repository.delete_calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_delete_after_a_failed_attempt_can_still_succeed_with_a_fresh_transaction() -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))
    memory_repository.fail = True
    with pytest.raises(RuntimeError):
        use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE)

    memory_repository.fail = False
    result = use_case.delete(1, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE)

    assert unit_of_work.enter_count == 2
    assert unit_of_work.committed is True
    assert result.memory.status is MemoryStatus.DELETED
