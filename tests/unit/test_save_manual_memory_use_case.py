from datetime import UTC, datetime

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

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | None]] = []
        self._next_id = 1

    def create_memory(
        self, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        self.calls.append((content, origin, source_event_id))
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


def _use_case() -> tuple[
    SaveManualMemoryUseCase, _RecordingMemoryRepository, _RecordingEventRepository
]:
    memory_repository = _RecordingMemoryRepository()
    event_repository = _RecordingEventRepository()
    return (
        SaveManualMemoryUseCase(memory_repository, event_repository),
        memory_repository,
        event_repository,
    )


@pytest.mark.parametrize("content", ["", "   ", "\t\n"])
def test_save_rejects_empty_content_without_touching_any_repository(content: str) -> None:
    use_case, memory_repository, event_repository = _use_case()

    with pytest.raises(InvalidManualMemoryDataError):
        use_case.save(content)

    assert memory_repository.calls == []
    assert event_repository.calls == []


def test_save_records_the_event_before_the_memory_and_links_them() -> None:
    use_case, memory_repository, event_repository = _use_case()

    memory = use_case.save("prefiere respuestas breves", message_id=7)

    assert event_repository.calls == [(MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, 7)]
    assert len(memory_repository.calls) == 1
    content, origin, source_event_id = memory_repository.calls[0]
    assert content == "prefiere respuestas breves"
    assert origin == MANUAL_MEMORY_ORIGIN
    assert source_event_id is not None
    assert memory.current_revision.source_event_id == source_event_id


def test_save_trims_surrounding_whitespace_from_content() -> None:
    use_case, memory_repository, _ = _use_case()

    memory = use_case.save("  prefiere respuestas breves  ")

    assert memory.current_revision.content == "prefiere respuestas breves"
    assert memory_repository.calls[0][0] == "prefiere respuestas breves"


def test_save_without_a_message_id_still_records_an_event() -> None:
    use_case, _, event_repository = _use_case()

    memory = use_case.save("un hecho cualquiera")

    assert event_repository.calls == [(MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, None)]
    assert memory.current_revision.source_event_id is not None
