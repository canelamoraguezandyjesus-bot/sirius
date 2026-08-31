from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from sirius.application.memory_origin import GetMemoryOriginUseCase, MemoryOriginNotFoundError
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus
from sirius.domain.event import MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, Event
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus


def _memory(source_event_id: int | None) -> Memory:
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=1,
        memory_id=1,
        version=1,
        content="prefiere respuestas breves",
        origin="Guardado manual del usuario",
        source_event_id=source_event_id,
        created_at=now,
    )
    return Memory(
        id=1, status=MemoryStatus.CURRENT, current_revision=revision, created_at=now, updated_at=now
    )


def _event(event_id: int = 5, message_id: int | None = None) -> Event:
    return Event(
        id=event_id,
        event_type=MANUAL_MEMORY_SAVE_EVENT_TYPE,
        actor=USER_ACTOR,
        message_id=message_id,
        created_at=datetime.now(UTC),
        redacted_at=None,
    )


def _message(
    message_id: int = 3, content: str = "guarda que prefiero respuestas breves"
) -> Message:
    return Message(
        id=message_id,
        conversation_id=1,
        sequence=1,
        role=MessageRole.USER,
        content=content,
        created_at=datetime.now(UTC),
    )


class _StaticMemoryRepository:
    def __init__(self, memory: Memory | None) -> None:
        self._memory = memory

    def get_memory(self, memory_id: int) -> Memory:
        if self._memory is None:
            msg = f"Unknown memory id: {memory_id}"
            raise ValueError(msg)
        return self._memory

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError("get_origin() must never create a memory")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("get_origin() must never list memories")

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError("get_origin() must never list memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("get_origin() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("get_origin() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("get_origin() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("get_origin() must never delete a memory")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("get_origin() must never list archived memories")

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("get_origin() must never set a category")

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError("get_origin() must never set a category")

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError("get_origin() must never list uncategorized memories")


class _StaticEventRepository:
    def __init__(self, event: Event | None) -> None:
        self._event = event

    def append(self, event_type: str, actor: str, message_id: int | None) -> Event:
        raise AssertionError("get_origin() must never append an event")

    def get_source(self, event_id: int) -> Event | None:
        return self._event


class _StaticConversationRepository:
    def __init__(self, message: Message | None) -> None:
        self._message = message
        self.queried_message_ids: list[int] = []

    def get_or_create_main_conversation(self) -> Conversation:
        raise AssertionError("get_origin() must never create a conversation")

    def get_main_conversation(self) -> Conversation | None:
        raise AssertionError("get_origin() must never read the conversation")

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
        raise AssertionError("get_origin() must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        raise AssertionError("get_origin() must never list messages")

    def get_message(self, message_id: int) -> Message | None:
        self.queried_message_ids.append(message_id)
        return self._message

    def redact_message(self, message_id: int) -> Message:
        raise AssertionError("get_origin() must never redact a message")


def test_get_origin_raises_for_an_unknown_memory_id() -> None:
    use_case = GetMemoryOriginUseCase(
        _StaticMemoryRepository(None),
        _StaticEventRepository(None),
        _StaticConversationRepository(None),
    )

    with pytest.raises(MemoryOriginNotFoundError):
        use_case.get_origin(999)


def test_get_origin_raises_when_the_current_revision_has_no_recorded_origin() -> None:
    use_case = GetMemoryOriginUseCase(
        _StaticMemoryRepository(_memory(source_event_id=None)),
        _StaticEventRepository(None),
        _StaticConversationRepository(None),
    )

    with pytest.raises(MemoryOriginNotFoundError):
        use_case.get_origin(1)


def test_get_origin_raises_when_the_source_event_no_longer_exists() -> None:
    use_case = GetMemoryOriginUseCase(
        _StaticMemoryRepository(_memory(source_event_id=5)),
        _StaticEventRepository(None),
        _StaticConversationRepository(None),
    )

    with pytest.raises(MemoryOriginNotFoundError):
        use_case.get_origin(1)


def test_get_origin_opens_the_event_and_its_source_message() -> None:
    conversation_repository = _StaticConversationRepository(_message())
    use_case = GetMemoryOriginUseCase(
        _StaticMemoryRepository(_memory(source_event_id=5)),
        _StaticEventRepository(_event(event_id=5, message_id=3)),
        conversation_repository,
    )

    origin = use_case.get_origin(1)

    assert origin.event_id == 5
    assert origin.event_type == MANUAL_MEMORY_SAVE_EVENT_TYPE
    assert origin.actor == USER_ACTOR
    assert origin.message_id == 3
    assert origin.message_content == "guarda que prefiero respuestas breves"
    assert conversation_repository.queried_message_ids == [3]


def test_get_origin_without_a_source_message_leaves_message_content_none() -> None:
    conversation_repository = _StaticConversationRepository(None)
    use_case = GetMemoryOriginUseCase(
        _StaticMemoryRepository(_memory(source_event_id=5)),
        _StaticEventRepository(_event(event_id=5, message_id=None)),
        conversation_repository,
    )

    origin = use_case.get_origin(1)

    assert origin.message_id is None
    assert origin.message_content is None
    assert conversation_repository.queried_message_ids == []


def test_get_origin_handles_a_dangling_message_reference_safely() -> None:
    use_case = GetMemoryOriginUseCase(
        _StaticMemoryRepository(_memory(source_event_id=5)),
        _StaticEventRepository(_event(event_id=5, message_id=3)),
        _StaticConversationRepository(None),
    )

    origin = use_case.get_origin(1)

    assert origin.message_id == 3
    assert origin.message_content is None
