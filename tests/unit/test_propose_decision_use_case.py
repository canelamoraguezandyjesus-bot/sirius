from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.propose_decision import (
    InvalidDecisionProposalDataError,
    ProposeDecisionUseCase,
)
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.event import DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision


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


class _RecordingDecisionRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, int, str, int | None]] = []
        self._next_id = 1
        self.fail = fail

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        self.calls.append((subject, project_id, content, source_event_id))
        if self.fail:
            msg = "simulated decision-creation failure"
            raise RuntimeError(msg)
        now = datetime.now(UTC)
        revision = DecisionRevision(
            id=self._next_id,
            decision_id=self._next_id,
            version=1,
            content=content,
            source_event_id=source_event_id,
            created_at=now,
        )
        decision = Decision(
            id=self._next_id,
            subject=subject,
            project_id=project_id,
            status=DecisionStatus.PROPOSED,
            current_revision=revision,
            created_at=now,
            updated_at=now,
        )
        self._next_id += 1
        return decision

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("propose() must never read a decision back")

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


class _UnusedMemoryRepository:
    """B4a's ``UnitOfWork.memory_repository``; ``propose()`` never touches it."""

    def create_memory(
        self, content: str, origin: str, *, source_event_id: int | None = None
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


class _UnusedConversationRepository:
    """B4d's ``UnitOfWork.conversation_repository``; ``propose()`` never touches it."""

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
        decision_repository: _RecordingDecisionRepository,
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


def _use_case() -> tuple[ProposeDecisionUseCase, _RecordingDecisionRepository, _FakeUnitOfWork]:
    decision_repository = _RecordingDecisionRepository()
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    return ProposeDecisionUseCase(unit_of_work), decision_repository, unit_of_work


@pytest.mark.parametrize("subject", ["", "   ", "\t\n"])
def test_propose_rejects_empty_subject_without_opening_a_transaction(subject: str) -> None:
    use_case, decision_repository, unit_of_work = _use_case()

    with pytest.raises(InvalidDecisionProposalDataError):
        use_case.propose(subject, 1, "contenido válido")

    assert decision_repository.calls == []
    assert unit_of_work.enter_count == 0


@pytest.mark.parametrize("content", ["", "   ", "\t\n"])
def test_propose_rejects_empty_content_without_opening_a_transaction(content: str) -> None:
    use_case, decision_repository, unit_of_work = _use_case()

    with pytest.raises(InvalidDecisionProposalDataError):
        use_case.propose("Motor de persistencia", 1, content)

    assert decision_repository.calls == []
    assert unit_of_work.enter_count == 0


def test_propose_records_the_event_before_the_decision_and_links_them() -> None:
    use_case, decision_repository, unit_of_work = _use_case()

    decision = use_case.propose("Motor de persistencia", 1, "Usar SQLite local", message_id=7)

    assert unit_of_work.event_repository.calls == [(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, 7)]
    assert len(decision_repository.calls) == 1
    subject, project_id, content, source_event_id = decision_repository.calls[0]
    assert subject == "Motor de persistencia"
    assert project_id == 1
    assert content == "Usar SQLite local"
    assert source_event_id is not None
    assert decision.current_revision.source_event_id == source_event_id
    assert decision.status is DecisionStatus.PROPOSED


def test_propose_commits_the_unit_of_work_exactly_once_on_success() -> None:
    use_case, _, unit_of_work = _use_case()

    use_case.propose("Motor de persistencia", 1, "Usar SQLite local")

    assert unit_of_work.enter_count == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


def test_propose_trims_surrounding_whitespace_from_subject_and_content() -> None:
    use_case, decision_repository, _ = _use_case()

    decision = use_case.propose("  Motor de persistencia  ", 1, "  Usar SQLite local  ")

    assert decision.subject == "Motor de persistencia"
    assert decision.current_revision.content == "Usar SQLite local"
    assert decision_repository.calls[0][0] == "Motor de persistencia"
    assert decision_repository.calls[0][2] == "Usar SQLite local"


def test_propose_without_a_message_id_still_records_an_event() -> None:
    use_case, _, unit_of_work = _use_case()

    decision = use_case.propose("Motor de persistencia", 1, "Usar SQLite local")

    assert unit_of_work.event_repository.calls == [(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)]
    assert decision.current_revision.source_event_id is not None


def test_propose_never_commits_when_decision_creation_fails_after_the_event_was_recorded() -> None:
    decision_repository = _RecordingDecisionRepository(fail=True)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(decision_repository, event_repository)
    use_case = ProposeDecisionUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.propose("Motor de persistencia", 1, "Usar SQLite local")

    assert event_repository.calls == [(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)]
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_propose_after_a_failed_attempt_can_still_succeed_with_a_fresh_transaction() -> None:
    use_case, decision_repository, unit_of_work = _use_case()
    decision_repository.fail = True
    with pytest.raises(RuntimeError):
        use_case.propose("Motor de persistencia", 1, "primer intento, falla")

    decision_repository.fail = False
    decision = use_case.propose("Motor de persistencia", 1, "segundo intento, correcto")

    assert unit_of_work.enter_count == 2
    assert unit_of_work.committed is True
    assert decision.current_revision.content == "segundo intento, correcto"
