from datetime import UTC, datetime

import pytest

from sirius.domain.conversation import (
    Conversation,
    Message,
    MessageRole,
    MessageStatus,
    SourceMessageChoice,
)


def test_message_role_values_are_stable_strings() -> None:
    assert MessageRole.USER.value == "user"
    assert MessageRole.SIRIUS.value == "sirius"


def test_message_status_has_the_four_states_b4d_needs() -> None:
    assert {member.value for member in MessageStatus} == {
        "completed",
        "cancelled",
        "failed",
        "redacted",
    }


def test_source_message_choice_has_exactly_the_two_states_rf_025_needs() -> None:
    assert {member.value for member in SourceMessageChoice} == {"preserve", "redact"}


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


def test_message_redacted_at_defaults_to_none_and_round_trips() -> None:
    now = datetime.now(UTC)
    message = Message(
        id=1, conversation_id=1, sequence=1, role=MessageRole.USER, content="Hola", created_at=now
    )
    assert message.redacted_at is None

    redacted = Message(
        id=1,
        conversation_id=1,
        sequence=1,
        role=MessageRole.USER,
        content=None,
        created_at=now,
        status=MessageStatus.REDACTED,
        redacted_at=now,
    )
    assert redacted.content is None
    assert redacted.status is MessageStatus.REDACTED
    assert redacted.redacted_at == now
