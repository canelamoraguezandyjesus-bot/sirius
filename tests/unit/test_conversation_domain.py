from datetime import UTC, datetime

import pytest

from sirius.domain.conversation import Conversation, Message, MessageRole


def test_message_role_values_are_stable_strings() -> None:
    assert MessageRole.USER.value == "user"
    assert MessageRole.SIRIUS.value == "sirius"


def test_conversation_is_immutable() -> None:
    conversation = Conversation(id=1, created_at=datetime.now(UTC))

    with pytest.raises(AttributeError):
        conversation.id = 2  # type: ignore[misc]


def test_message_is_immutable() -> None:
    message = Message(
        id=1,
        conversation_id=1,
        sequence=1,
        role=MessageRole.USER,
        content="Hola",
        created_at=datetime.now(UTC),
    )

    with pytest.raises(AttributeError):
        message.content = "otro"  # type: ignore[misc]
