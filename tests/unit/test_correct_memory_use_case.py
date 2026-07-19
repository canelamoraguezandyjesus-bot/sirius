from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.correct_memory import (
    INVALID_MEMORY_CORRECTION_CONTENT_MESSAGE,
    MEMORY_CORRECTION_ORIGIN,
    CorrectMemoryUseCase,
    InvalidMemoryCorrectionDataError,
    MemoryNotCorrectableError,
    UnknownMemoryError,
)
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision
from sirius.domain.event import MEMORY_CORRECTED_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus


def _memory(status: MemoryStatus, *, memory_id: int = 1, version: int = 1) -> Memory:
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=version,
        memory_id=memory_id,
        version=version,
        content="preferencia original",
        origin="Guardado manual del usuario",
        source_event_id=3,
        created_at=now,
    )
    return Memory(
        id=memory_id,
        status=status,
        current_revision=revision,
        created_at=now,
        updated_at=now,
    )


class _RecordingEventRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

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
        raise AssertionError("correct() must never read an event back")


class _StaticMemoryRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, memory: Memory | None, *, fail: bool = False) -> None:
        self._memory = memory
        self.fail = fail
        self.correct_calls: list[tuple[int, str, str, int | None]] = []

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError("correct() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        if self._memory is None:
            msg = f"Unknown memory id: {memory_id}"
            raise ValueError(msg)
        return self._memory

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("correct() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("correct() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        self.correct_calls.append((memory_id, content, origin, source_event_id))
        if self.fail:
            msg = "simulated correction failure"
            raise RuntimeError(msg)
        assert self._memory is not None
        now = datetime.now(UTC)
        new_version = self._memory.current_revision.version + 1
        revision = MemoryRevision(
            id=new_version,
            memory_id=memory_id,
            version=new_version,
            content=content,
            origin=origin,
            source_event_id=source_event_id,
            created_at=now,
        )
        corrected = Memory(
            id=self._memory.id,
            status=self._memory.status,
            current_revision=revision,
            created_at=self._memory.created_at,
            updated_at=now,
        )
        self._memory = corrected
        return corrected

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("correct() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("correct() must never delete a memory")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("correct() must never list archived memories")


class _UnusedDecisionRepository:
    """B4b/B4c's ``UnitOfWork.decision_repository``; ``correct()`` never touches it."""

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("correct() must never create a decision proposal")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("correct() must never read a decision")

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("correct() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("correct() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("correct() must never list decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("correct() must never read a superseding decision")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("correct() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("correct() must never list archived decisions")


class _UnusedConversationRepository:
    """B4d's ``UnitOfWork.conversation_repository``; ``correct()`` never touches it."""

    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("correct() must never touch the conversation")

    def get_main_conversation(self) -> Conversation | None:
        raise AssertionError("correct() must never touch the conversation")

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
        raise AssertionError("correct() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        raise AssertionError("correct() must never list messages")

    def get_message(self, message_id: int) -> Message | None:
        raise AssertionError("correct() must never read a message")

    def redact_message(self, message_id: int) -> Message:
        raise AssertionError("correct() must never redact a message")


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
) -> tuple[CorrectMemoryUseCase, _StaticMemoryRepository, _FakeUnitOfWork]:
    memory_repository = _StaticMemoryRepository(memory)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository)
    return CorrectMemoryUseCase(unit_of_work), memory_repository, unit_of_work


@pytest.mark.parametrize("content", ["", "   ", "\t\n"])
def test_correct_rejects_empty_content_without_opening_a_transaction(content: str) -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    with pytest.raises(InvalidMemoryCorrectionDataError) as exc_info:
        use_case.correct(1, content)

    assert str(exc_info.value) == INVALID_MEMORY_CORRECTION_CONTENT_MESSAGE
    assert memory_repository.correct_calls == []
    assert unit_of_work.enter_count == 0


def test_correct_unknown_memory_id_fails_safely_without_writing_anything() -> None:
    use_case, memory_repository, unit_of_work = _use_case(None)

    with pytest.raises(UnknownMemoryError):
        use_case.correct(999, "contenido nuevo")

    assert memory_repository.correct_calls == []
    assert unit_of_work.event_repository.calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


@pytest.mark.parametrize("status", [MemoryStatus.ARCHIVED, MemoryStatus.DELETED])
def test_correct_a_non_correctable_memory_fails_safely_without_writing_anything(
    status: MemoryStatus,
) -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(status))

    with pytest.raises(MemoryNotCorrectableError):
        use_case.correct(1, "contenido nuevo")

    assert memory_repository.correct_calls == []
    assert unit_of_work.event_repository.calls == []
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_correct_records_the_event_before_the_revision_and_links_them() -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    corrected = use_case.correct(1, "preferencia corregida", message_id=7)

    assert unit_of_work.event_repository.calls == [(MEMORY_CORRECTED_EVENT_TYPE, USER_ACTOR, 7)]
    assert len(memory_repository.correct_calls) == 1
    memory_id, content, origin, source_event_id = memory_repository.correct_calls[0]
    assert memory_id == 1
    assert content == "preferencia corregida"
    assert origin == MEMORY_CORRECTION_ORIGIN
    assert source_event_id is not None
    assert corrected.current_revision.source_event_id == source_event_id
    assert corrected.current_revision.version == 2


def test_correct_commits_the_unit_of_work_exactly_once_on_success() -> None:
    use_case, _, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    use_case.correct(1, "preferencia corregida")

    assert unit_of_work.enter_count == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


def test_correct_trims_surrounding_whitespace_from_content() -> None:
    use_case, memory_repository, _ = _use_case(_memory(MemoryStatus.CURRENT))

    corrected = use_case.correct(1, "  preferencia corregida  ")

    assert corrected.current_revision.content == "preferencia corregida"
    assert memory_repository.correct_calls[0][1] == "preferencia corregida"


def test_correct_without_a_message_id_still_records_an_event() -> None:
    use_case, _, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))

    corrected = use_case.correct(1, "preferencia corregida")

    assert unit_of_work.event_repository.calls == [(MEMORY_CORRECTED_EVENT_TYPE, USER_ACTOR, None)]
    assert corrected.current_revision.source_event_id is not None


def test_correct_never_commits_when_revision_creation_fails_after_the_event_was_recorded() -> None:
    memory_repository = _StaticMemoryRepository(_memory(MemoryStatus.CURRENT), fail=True)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository)
    use_case = CorrectMemoryUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.correct(1, "preferencia corregida")

    # The event write was attempted (source_event_id must exist before the
    # revision write), but the unit of work was never committed — a real
    # SqliteUnitOfWork rolls back both writes together in this situation
    # (see the integration-level atomicity tests).
    assert event_repository.calls == [(MEMORY_CORRECTED_EVENT_TYPE, USER_ACTOR, None)]
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_correct_after_a_failed_attempt_can_still_succeed_with_a_fresh_transaction() -> None:
    use_case, memory_repository, unit_of_work = _use_case(_memory(MemoryStatus.CURRENT))
    memory_repository.fail = True
    with pytest.raises(RuntimeError):
        use_case.correct(1, "primer intento, falla")

    memory_repository.fail = False
    corrected = use_case.correct(1, "segundo intento, correcto")

    assert unit_of_work.enter_count == 2
    assert unit_of_work.committed is True
    assert corrected.current_revision.content == "segundo intento, correcto"
