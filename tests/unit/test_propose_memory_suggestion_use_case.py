from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.propose_memory_suggestion import (
    InvalidMemorySuggestionProposalDataError,
    ProposeMemorySuggestionUseCase,
)
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision
from sirius.domain.event import MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE, USER_ACTOR, Event
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
        raise AssertionError("propose() must never read an event back")


class _RecordingMemorySuggestionRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, int | None, str | None, int | None]] = []
        self._next_id = 1
        self.fail = fail

    def create_suggestion(
        self,
        content: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> MemorySuggestion:
        self.calls.append((content, source_event_id, subject_key, project_id))
        if self.fail:
            msg = "simulated suggestion-creation failure"
            raise RuntimeError(msg)
        now = datetime.now(UTC)
        suggestion = MemorySuggestion(
            id=self._next_id,
            content=content,
            status=MemorySuggestionStatus.PENDING,
            source_event_id=source_event_id,
            created_at=now,
            resolved_at=None,
            subject_key=subject_key,
            project_id=project_id,
        )
        self._next_id += 1
        return suggestion

    def get_suggestion(self, suggestion_id: int) -> MemorySuggestion:
        raise AssertionError("propose() must never read a memory suggestion back")

    def list_pending_suggestions(self) -> list[MemorySuggestion]:
        raise AssertionError("propose() must never list memory suggestions")

    def confirm_suggestion(
        self, suggestion_id: int, *, resulting_memory_id: int, resolved_at: datetime
    ) -> MemorySuggestion:
        raise AssertionError("propose() must never confirm a memory suggestion")

    def reject_suggestion(self, suggestion_id: int, *, resolved_at: datetime) -> MemorySuggestion:
        raise AssertionError("propose() must never reject a memory suggestion")


class _UnusedMemoryRepository:
    """``UnitOfWork.memory_repository``; ``propose()`` never touches it."""

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError("propose() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("propose() must never read a memory")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("propose() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("propose() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("propose() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("propose() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("propose() must never delete a memory")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("propose() must never list archived memories")


class _UnusedDecisionRepository:
    """``UnitOfWork.decision_repository``; ``propose()`` never touches it."""

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("propose() must never create a decision proposal")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("propose() must never read a decision")

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("propose() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("propose() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("propose() must never list decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("propose() must never read a superseding decision")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("propose() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("propose() must never list archived decisions")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("propose() must never list proposed decisions")


class _UnusedConversationRepository:
    """``UnitOfWork.conversation_repository``; ``propose()`` never touches it."""

    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("propose() must never touch the conversation")

    def get_main_conversation(self) -> Conversation | None:
        raise AssertionError("propose() must never touch the conversation")

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
        raise AssertionError("propose() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        raise AssertionError("propose() must never list messages")

    def get_message(self, message_id: int) -> Message | None:
        raise AssertionError("propose() must never read a message")

    def redact_message(self, message_id: int) -> Message:
        raise AssertionError("propose() must never redact a message")


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


def _use_case() -> tuple[
    ProposeMemorySuggestionUseCase, _RecordingMemorySuggestionRepository, _FakeUnitOfWork
]:
    memory_suggestion_repository = _RecordingMemorySuggestionRepository()
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(memory_suggestion_repository, event_repository)
    return ProposeMemorySuggestionUseCase(unit_of_work), memory_suggestion_repository, unit_of_work


@pytest.mark.parametrize("content", ["", "   ", "\t\n"])
def test_propose_rejects_empty_content_without_opening_a_transaction(content: str) -> None:
    use_case, memory_suggestion_repository, unit_of_work = _use_case()

    with pytest.raises(InvalidMemorySuggestionProposalDataError):
        use_case.propose(content)

    assert memory_suggestion_repository.calls == []
    assert unit_of_work.enter_count == 0


def test_propose_records_the_event_before_the_suggestion_and_links_them() -> None:
    use_case, memory_suggestion_repository, unit_of_work = _use_case()

    suggestion = use_case.propose("prefiere respuestas breves", message_id=7)

    assert unit_of_work.event_repository.calls == [
        (MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE, USER_ACTOR, 7)
    ]
    assert len(memory_suggestion_repository.calls) == 1
    content, source_event_id, subject_key, project_id = memory_suggestion_repository.calls[0]
    assert content == "prefiere respuestas breves"
    assert source_event_id is not None
    assert suggestion.source_event_id == source_event_id
    assert suggestion.status is MemorySuggestionStatus.PENDING
    assert subject_key is None
    assert project_id is None


def test_propose_commits_the_unit_of_work_exactly_once_on_success() -> None:
    use_case, _, unit_of_work = _use_case()

    use_case.propose("un apunte cualquiera")

    assert unit_of_work.enter_count == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


def test_propose_trims_surrounding_whitespace_from_content() -> None:
    use_case, memory_suggestion_repository, _ = _use_case()

    suggestion = use_case.propose("  prefiere respuestas breves  ")

    assert suggestion.content == "prefiere respuestas breves"
    assert memory_suggestion_repository.calls[0][0] == "prefiere respuestas breves"


def test_propose_without_a_message_id_still_records_an_event() -> None:
    use_case, _, unit_of_work = _use_case()

    suggestion = use_case.propose("un apunte cualquiera")

    assert unit_of_work.event_repository.calls == [
        (MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)
    ]
    assert suggestion.source_event_id is not None


def test_propose_never_commits_when_suggestion_creation_fails_after_the_event_was_recorded() -> (
    None
):
    memory_suggestion_repository = _RecordingMemorySuggestionRepository(fail=True)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(memory_suggestion_repository, event_repository)
    use_case = ProposeMemorySuggestionUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.propose("prefiere respuestas breves")

    assert event_repository.calls == [(MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)]
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_propose_after_a_failed_attempt_can_still_succeed_with_a_fresh_transaction() -> None:
    use_case, memory_suggestion_repository, unit_of_work = _use_case()
    memory_suggestion_repository.fail = True
    with pytest.raises(RuntimeError):
        use_case.propose("primer intento, falla")

    memory_suggestion_repository.fail = False
    suggestion = use_case.propose("segundo intento, correcto")

    assert unit_of_work.enter_count == 2
    assert unit_of_work.committed is True
    assert suggestion.content == "segundo intento, correcto"
