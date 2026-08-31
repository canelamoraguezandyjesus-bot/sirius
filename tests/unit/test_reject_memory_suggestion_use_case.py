from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.reject_memory_suggestion import RejectMemorySuggestionUseCase
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision
from sirius.domain.event import MEMORY_SUGGESTION_REJECTED_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision
from sirius.domain.memory_suggestion import MemorySuggestion, MemorySuggestionStatus


class _RecordingEventRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | None]] = []
        self._next_id = 1

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
        raise AssertionError("reject() must never read an event back")


class _UnusedMemoryRepository:
    """``UnitOfWork.memory_repository``; ``reject()`` must never touch it (§3.5, §4.4)."""

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError("reject() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("reject() must never read a memory")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("reject() must never list memories")

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError("reject() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("reject() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("reject() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("reject() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("reject() must never delete a memory")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("reject() must never list archived memories")

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("reject() must never set a category")

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError("reject() must never set a category")

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError("reject() must never list uncategorized memories")


class _RecordingMemorySuggestionRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, suggestion: MemorySuggestion, *, fail: bool = False) -> None:
        self._suggestion = suggestion
        self.fail = fail
        self.reject_calls: list[tuple[int, datetime]] = []

    def create_suggestion(
        self,
        content: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> MemorySuggestion:
        raise AssertionError("reject() must never create a memory suggestion")

    def get_suggestion(self, suggestion_id: int) -> MemorySuggestion:
        assert suggestion_id == self._suggestion.id
        return self._suggestion

    def list_pending_suggestions(self) -> list[MemorySuggestion]:
        raise AssertionError("reject() must never list memory suggestions")

    def confirm_suggestion(
        self, suggestion_id: int, *, resulting_memory_id: int, resolved_at: datetime
    ) -> MemorySuggestion:
        raise AssertionError("reject() must never confirm a memory suggestion")

    def reject_suggestion(self, suggestion_id: int, *, resolved_at: datetime) -> MemorySuggestion:
        self.reject_calls.append((suggestion_id, resolved_at))
        if self.fail:
            msg = "simulated reject failure"
            raise RuntimeError(msg)
        return MemorySuggestion(
            id=self._suggestion.id,
            content=self._suggestion.content,
            status=MemorySuggestionStatus.REJECTED,
            source_event_id=self._suggestion.source_event_id,
            created_at=self._suggestion.created_at,
            resolved_at=resolved_at,
            resulting_memory_id=None,
            subject_key=self._suggestion.subject_key,
            project_id=self._suggestion.project_id,
        )


class _UnusedDecisionRepository:
    """``UnitOfWork.decision_repository``; ``reject()`` never touches it."""

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("reject() must never create a decision proposal")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("reject() must never read a decision")

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("reject() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("reject() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("reject() must never list decisions")

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        raise AssertionError("reject() must never list decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("reject() must never read a superseding decision")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("reject() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("reject() must never list archived decisions")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("reject() must never list proposed decisions")

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("reject() must never set a category")

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError("reject() must never set a category")

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError("reject() must never list uncategorized decisions")


class _UnusedConversationRepository:
    """``UnitOfWork.conversation_repository``; ``reject()`` never touches it."""

    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("reject() must never touch the conversation")

    def get_main_conversation(self) -> Conversation | None:
        raise AssertionError("reject() must never touch the conversation")

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
        raise AssertionError("reject() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        raise AssertionError("reject() must never list messages")

    def get_message(self, message_id: int) -> Message | None:
        raise AssertionError("reject() must never read a message")

    def redact_message(self, message_id: int) -> Message:
        raise AssertionError("reject() must never redact a message")


class _FakeUnitOfWork:
    """In-memory stand-in for ``SqliteUnitOfWork``: same commit/rollback contract."""

    def __init__(
        self,
        memory_suggestion_repository: _RecordingMemorySuggestionRepository,
        event_repository: _RecordingEventRepository,
    ) -> None:
        self.memory_suggestion_repository = memory_suggestion_repository
        self.event_repository = event_repository
        self.memory_repository = _UnusedMemoryRepository()
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


def _pending_suggestion(**overrides: object) -> MemorySuggestion:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": 1,
        "content": "evaluar una herramienta de terceros",
        "status": MemorySuggestionStatus.PENDING,
        "source_event_id": 9,
        "created_at": now,
        "resolved_at": None,
        "resulting_memory_id": None,
        "subject_key": None,
        "project_id": None,
    }
    defaults.update(overrides)
    return MemorySuggestion(**defaults)  # type: ignore[arg-type]


def _use_case(
    suggestion: MemorySuggestion, *, fail: bool = False
) -> tuple[RejectMemorySuggestionUseCase, _RecordingMemorySuggestionRepository, _FakeUnitOfWork]:
    memory_suggestion_repository = _RecordingMemorySuggestionRepository(suggestion, fail=fail)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(memory_suggestion_repository, event_repository)
    return RejectMemorySuggestionUseCase(unit_of_work), memory_suggestion_repository, unit_of_work


def test_reject_records_the_event_and_marks_the_suggestion_rejected_without_creating_a_memory() -> (
    None
):
    suggestion = _pending_suggestion()
    use_case, memory_suggestion_repository, unit_of_work = _use_case(suggestion)

    rejected = use_case.reject(suggestion.id)

    assert unit_of_work.event_repository.calls == [
        (MEMORY_SUGGESTION_REJECTED_EVENT_TYPE, USER_ACTOR, None)
    ]
    assert rejected.status is MemorySuggestionStatus.REJECTED
    assert memory_suggestion_repository.reject_calls[0][0] == suggestion.id


def test_reject_commits_the_unit_of_work_exactly_once_on_success() -> None:
    suggestion = _pending_suggestion()
    use_case, _, unit_of_work = _use_case(suggestion)

    use_case.reject(suggestion.id)

    assert unit_of_work.enter_count == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


@pytest.mark.parametrize(
    "status", [MemorySuggestionStatus.CONFIRMED, MemorySuggestionStatus.REJECTED]
)
def test_reject_rejects_a_non_pending_suggestion_without_writing_anything(
    status: MemorySuggestionStatus,
) -> None:
    suggestion = _pending_suggestion(status=status, resolved_at=datetime.now(UTC))
    use_case, memory_suggestion_repository, unit_of_work = _use_case(suggestion)

    with pytest.raises(ValueError, match="Cannot reject"):
        use_case.reject(suggestion.id)

    assert memory_suggestion_repository.reject_calls == []
    assert unit_of_work.event_repository.calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_reject_never_commits_when_the_repository_write_fails() -> None:
    suggestion = _pending_suggestion()
    use_case, _, unit_of_work = _use_case(suggestion, fail=True)

    with pytest.raises(RuntimeError):
        use_case.reject(suggestion.id)

    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1
