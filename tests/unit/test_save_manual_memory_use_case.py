from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self

import pytest

from sirius.application.save_manual_memory import (
    MANUAL_MEMORY_ORIGIN,
    InvalidManualMemoryDataError,
    SaveManualMemoryUseCase,
)
from sirius.domain.event import MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus


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
        raise AssertionError("save() must never read an event back")


class _RecordingMemoryRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, str, int | None]] = []
        self._next_id = 1
        self.fail = fail

    def create_memory(
        self, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        self.calls.append((content, origin, source_event_id))
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
        )
        self._next_id += 1
        return memory

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("save() must never read a memory back")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("save() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("save() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("save() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("save() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("save() must never delete a memory")


class _FakeUnitOfWork:
    """In-memory stand-in for ``SqliteUnitOfWork``: same commit/rollback contract.

    ``committed``/``rollback_count`` let tests observe whether the use case
    confirmed or discarded a transaction without needing a real database.
    """

    def __init__(
        self,
        memory_repository: _RecordingMemoryRepository,
        event_repository: _RecordingEventRepository,
    ) -> None:
        self.memory_repository = memory_repository
        self.event_repository = event_repository
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


def _use_case() -> tuple[SaveManualMemoryUseCase, _RecordingMemoryRepository, _FakeUnitOfWork]:
    memory_repository = _RecordingMemoryRepository()
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository)
    return SaveManualMemoryUseCase(unit_of_work), memory_repository, unit_of_work


@pytest.mark.parametrize("content", ["", "   ", "\t\n"])
def test_save_rejects_empty_content_without_opening_a_transaction(content: str) -> None:
    use_case, memory_repository, unit_of_work = _use_case()

    with pytest.raises(InvalidManualMemoryDataError):
        use_case.save(content)

    assert memory_repository.calls == []
    assert unit_of_work.enter_count == 0


def test_save_records_the_event_before_the_memory_and_links_them() -> None:
    use_case, memory_repository, unit_of_work = _use_case()

    memory = use_case.save("prefiere respuestas breves", message_id=7)

    assert unit_of_work.event_repository.calls == [(MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, 7)]
    assert len(memory_repository.calls) == 1
    content, origin, source_event_id = memory_repository.calls[0]
    assert content == "prefiere respuestas breves"
    assert origin == MANUAL_MEMORY_ORIGIN
    assert source_event_id is not None
    assert memory.current_revision.source_event_id == source_event_id


def test_save_commits_the_unit_of_work_exactly_once_on_success() -> None:
    use_case, _, unit_of_work = _use_case()

    use_case.save("un hecho cualquiera")

    assert unit_of_work.enter_count == 1
    assert unit_of_work.committed is True
    assert unit_of_work.rollback_count == 0


def test_save_trims_surrounding_whitespace_from_content() -> None:
    use_case, memory_repository, _ = _use_case()

    memory = use_case.save("  prefiere respuestas breves  ")

    assert memory.current_revision.content == "prefiere respuestas breves"
    assert memory_repository.calls[0][0] == "prefiere respuestas breves"


def test_save_without_a_message_id_still_records_an_event() -> None:
    use_case, _, unit_of_work = _use_case()

    memory = use_case.save("un hecho cualquiera")

    assert unit_of_work.event_repository.calls == [
        (MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, None)
    ]
    assert memory.current_revision.source_event_id is not None


def test_save_never_commits_when_memory_creation_fails_after_the_event_was_recorded() -> None:
    memory_repository = _RecordingMemoryRepository(fail=True)
    event_repository = _RecordingEventRepository()
    unit_of_work = _FakeUnitOfWork(memory_repository, event_repository)
    use_case = SaveManualMemoryUseCase(unit_of_work)

    with pytest.raises(RuntimeError):
        use_case.save("prefiere respuestas breves")

    # The event write was attempted (source_event_id must exist before the
    # memory write), but the unit of work was never committed — a real
    # SqliteUnitOfWork rolls back both writes together in this situation
    # (see the integration-level atomicity tests).
    assert event_repository.calls == [(MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, None)]
    assert unit_of_work.committed is False
    assert unit_of_work.rollback_count == 1


def test_save_after_a_failed_attempt_can_still_succeed_with_a_fresh_transaction() -> None:
    use_case, memory_repository, unit_of_work = _use_case()
    memory_repository.fail = True
    with pytest.raises(RuntimeError):
        use_case.save("primer intento, falla")

    memory_repository.fail = False
    memory = use_case.save("segundo intento, correcto")

    assert unit_of_work.enter_count == 2
    assert unit_of_work.committed is True
    assert memory.current_revision.content == "segundo intento, correcto"
