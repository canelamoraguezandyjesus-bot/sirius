from datetime import UTC, datetime

import pytest

from sirius.application.get_conversation_history import (
    ConversationNotInitializedError,
    GetConversationHistoryUseCase,
)
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus


class _InMemoryConversationRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, conversation: Conversation | None, messages: list[Message]) -> None:
        self._conversation = conversation
        self._messages = messages

    def get_or_create_main_conversation(self) -> Conversation:
        if self._conversation is None:
            raise AssertionError("the use case must never call get_or_create_*")
        return self._conversation

    def get_main_conversation(self) -> Conversation | None:
        return self._conversation

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
        raise AssertionError("a read-only use case must never append a message")

    def list_messages(self, conversation_id: int) -> list[Message]:
        return [m for m in self._messages if m.conversation_id == conversation_id]

    def get_message(self, message_id: int) -> Message | None:
        return next((m for m in self._messages if m.id == message_id), None)


def _message(conversation_id: int, sequence: int, role: MessageRole, content: str) -> Message:
    return Message(
        id=sequence,
        conversation_id=conversation_id,
        sequence=sequence,
        role=role,
        content=content,
        created_at=datetime.now(UTC),
    )


def test_get_history_raises_when_no_conversation_exists() -> None:
    use_case = GetConversationHistoryUseCase(_InMemoryConversationRepository(None, []))

    with pytest.raises(ConversationNotInitializedError):
        use_case.get_history()


def test_get_history_returns_messages_in_stable_order() -> None:
    conversation = Conversation(id=1, created_at=datetime.now(UTC))
    messages = [
        _message(1, 1, MessageRole.USER, "uno"),
        _message(1, 2, MessageRole.SIRIUS, "dos"),
        _message(1, 3, MessageRole.USER, "tres"),
    ]
    use_case = GetConversationHistoryUseCase(
        _InMemoryConversationRepository(conversation, messages)
    )

    history = use_case.get_history()

    assert [m.content for m in history] == ["uno", "dos", "tres"]
