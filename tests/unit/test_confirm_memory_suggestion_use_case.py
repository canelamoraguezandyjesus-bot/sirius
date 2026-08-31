from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.confirm_memory_suggestion import (
    CONFIRMED_MEMORY_SUGGESTION_ORIGIN,
    ConfirmMemorySuggestionUseCase,
)
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision
from sirius.domain.event import MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
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
        raise AssertionError("confirm() must never read an event back")


class _RecordingMemoryRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, str, int | None, str | None, int | None]] = []
        self._next_id = 1
        self.fail = fail

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        self.calls.append((content, origin, source_event_id, subject_key, project_id))
        if self.fail:
            msg = "simulated memory-creation failure"
            raise RuntimeError(msg)
        now = datetime.now(UTC)
        revision = MemoryRevision(
            id=self._next_id,
            memory_id=self._next_id,
            version=1,
            content=content,
            origin=origin,
            source_event_id=source_event_id,
            created_at=now,
        )
        memory = Memory(
            id=self._next_id,
            status=MemoryStatus.CURRENT,
            current_revision=revision,
            created_at=now,
            updated_at=now,
            subject_key=subject_key,
            project_id=project_id,
        )
        self._next_id += 1
        return memory

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("confirm() must never read a memory back")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("confirm() must never list memories")

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError("confirm() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("confirm() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("confirm() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("confirm() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("confirm() must never delete a memory")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("confirm() must never list archived memories")

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("confirm() must never set a category")

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError("confirm() must never set a category")

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError("confirm() must never list uncategorized memories")


class _RecordingMemorySuggestionRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, suggestion: MemorySuggestion) -> None:
        self._suggestion = suggestion
        self.confirm_calls: list[tuple[int, int, datetime]] = []

    def create_suggestion(
        self,
        content: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> MemorySuggestion:
        raise AssertionError("confirm() must never create a memory suggestion")

    def get_suggestion(self, suggestion_id: int) -> MemorySuggestion:
        assert suggestion_id == self._suggestion.id
        return self._suggestion

    def list_pending_suggestions(self) -> list[MemorySuggestion]:
        raise AssertionError("confirm() must never list memory suggestions")

    def confirm_suggestion(
        self, suggestion_id: int, *, resulting_memory_id: int, resolved_at: datetime
    ) -> MemorySuggestion:
        self.confirm_calls.append((suggestion_id, resulting_memory_id, resolved_at))
        return MemorySuggestion(
            id=self._suggestion.id,
            content=self._suggestion.content,
            status=MemorySuggestionStatus.CONFIRMED,
            source_event_id=self._suggestion.source_event_id,
            created_at=self._suggestion.created_at,
            resolved_at=resolved_at,
            resulting_memory_id=resulting_memory_id,
            subject_key=self._suggestion.subject_key,
            project_id=self._suggestion.project_id,
        )

    def reject_suggestion(self, suggestion_id: int, *, resolved_at: datetime) -> MemorySuggestion:
        raise AssertionError("confirm() must never reject a memory suggestion")


class _UnusedDecisionRepository:
    """``UnitOfWork.decision_repository``; ``confirm()`` never touches it."""

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("confirm() must never create a decision proposal")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("confirm() must never read a decision")

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("confirm() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("confirm() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("confirm() must never list decisions")

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        raise AssertionError("confirm() must never list decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("confirm() must never read a superseding decision")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("confirm() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("confirm() must never list archived decisions")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("confirm() must never list proposed decisions")

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("confirm() must never set a category")

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError("confirm() must never set a category")

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError("confirm() must never list uncategorized decisions")


class _UnusedConversationRepository:
    """``UnitOfWork.conversation_repository``; ``confirm()`` never touches it."""

    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("confirm() must never touch the conversation")

    def get_main_conversation(self) -> Conversation | None:
        raise AssertionError("confirm() must never touch the conversation")

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
        raise AssertionError("confirm() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        raise AssertionError("confirm() must never list messages")

    def get_message(self, message_id: int) -> Message | None:
        raise AssertionError("confirm() must never read a message")

    def redact_message(self, message_id: int) -> Message:
        raise AssertionError("confirm() must never redact a message")


class _FakeUnitOfWork:
    """In-memory stand-in for ``SqliteUnitOfWork``: same commit/rollback contract."""

    def __init__(
        self,
        memory_repository: _RecordingMemoryRepository,
        event_repository: _RecordingEventRepository,
        memory_suggestion_repository: _RecordingMemorySuggestionRepository,
    ) -> None:
        self.memory_repository = memory_repository
        self.event_repository = event_repository
        self.memory_suggestion_repository = memory_suggestion_repository
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
        "content": "prefiere respuestas breves",
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
    suggestion: MemorySuggestion,
) -> tuple[
    ConfirmMemorySuggestionUseCase,
    _RecordingMemoryRepository,
    _RecordingMemorySuggestionRepository,
    _FakeUnitOfWork,
]:
    memory_repository = _RecordingMemoryRepository()
    event_repository = _RecordingEventRepository()
    memory_suggestion_repository = _RecordingMemorySuggestionRepository(suggestion)
    unit_of_work = _FakeUnitOfWork(
        memory_repository, event_repository, memory_suggestion_repository
    )
    return (
        ConfirmMemorySuggestionUseCase(unit_of_work),
        memory_repository,
        memory_suggestion_repository,
        unit_of_work,
    )


def test_confirm_creates_a_current_memory_with_the_suggestions_content_and_a_traceable_origin() -> (
    None
):
    suggestion = _pending_suggestion(
        content="usar SQLite local", subject_key="Motor de persistencia", project_id=1
    )
    use_case, memory_repository, memory_suggestion_repository, unit_of_work = _use_case(suggestion)

    memory = use_case.confirm(suggestion.id)

    assert unit_of_work.event_repository.calls == [
        (MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE, USER_ACTOR, None)
    ]
    assert len(memory_repository.calls) == 1
    content, origin, source_event_id, subject_key, project_id = memory_repository.calls[0]
    assert content == "usar SQLite local"
    assert origin == CONFIRMED_MEMORY_SUGGESTION_ORIGIN
    assert source_event_id is not None
    assert subject_key == "Motor de persistencia"
    assert project_id == 1
    assert memory.status is MemoryStatus.CURRENT
    assert memory.current_revision.content == "usar SQLite local"

    assert memory_suggestion_repository.confirm_calls == [
        (suggestion.id, memory.id, memory_suggestion_repository.confirm_calls[0][2])
    ]


def test_confirm_commits_the_unit_of_work_exactly_once_on_success() -> None:
    suggestion = _pending_suggestion()
    use_case, _, _, unit_of_work = _use_case(suggestion)

    use_case.confirm(suggestion.id)

    assert unit_of_work.enter_count == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


@pytest.mark.parametrize(
    "status", [MemorySuggestionStatus.CONFIRMED, MemorySuggestionStatus.REJECTED]
)
def test_confirm_rejects_a_non_pending_suggestion_without_creating_a_memory(
    status: MemorySuggestionStatus,
) -> None:
    suggestion = _pending_suggestion(status=status, resolved_at=datetime.now(UTC))
    use_case, memory_repository, memory_suggestion_repository, unit_of_work = _use_case(suggestion)

    with pytest.raises(ValueError, match="Cannot confirm"):
        use_case.confirm(suggestion.id)

    assert memory_repository.calls == []
    assert memory_suggestion_repository.confirm_calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_confirm_never_commits_when_memory_creation_fails() -> None:
    suggestion = _pending_suggestion()
    use_case, memory_repository, memory_suggestion_repository, unit_of_work = _use_case(suggestion)
    memory_repository.fail = True

    with pytest.raises(RuntimeError):
        use_case.confirm(suggestion.id)

    assert memory_suggestion_repository.confirm_calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1
