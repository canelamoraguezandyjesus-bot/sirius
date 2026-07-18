from datetime import UTC, datetime

import pytest

from sirius.domain.event import MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, Event


def _event(message_id: int | None = None) -> Event:
    return Event(
        id=1,
        event_type=MANUAL_MEMORY_SAVE_EVENT_TYPE,
        actor=USER_ACTOR,
        message_id=message_id,
        created_at=datetime.now(UTC),
        redacted_at=None,
    )


def test_event_is_immutable() -> None:
    event = _event()

    with pytest.raises(AttributeError):
        event.actor = "otro"  # type: ignore[misc]


def test_event_carries_an_optional_message_reference() -> None:
    assert _event().message_id is None
    assert _event(message_id=7).message_id == 7


def test_manual_memory_save_event_type_is_a_stable_non_empty_constant() -> None:
    assert MANUAL_MEMORY_SAVE_EVENT_TYPE == "memory.manual_save"
    assert USER_ACTOR == "user"
