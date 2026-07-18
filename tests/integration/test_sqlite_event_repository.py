from pathlib import Path

import pytest

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import (
    SqliteEventRepository,
    build_sqlite_event_repository,
)
from sirius.domain.conversation import MessageRole
from sirius.domain.event import MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR


def _build_repository(database_path: Path) -> SqliteEventRepository:
    repository = build_sqlite_event_repository(database_path)
    Base.metadata.create_all(build_engine(database_path))
    return repository


@pytest.mark.integration
def test_append_persists_and_returns_the_event(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    event = repository.append(MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, message_id=None)

    assert event.id is not None
    assert event.event_type == MANUAL_MEMORY_SAVE_EVENT_TYPE
    assert event.actor == USER_ACTOR
    assert event.message_id is None
    assert event.redacted_at is None


@pytest.mark.integration
def test_append_records_an_optional_message_reference(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    message = conversation_repository.append_message(conversation.id, MessageRole.USER, "hola")

    event = repository.append(MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, message_id=message.id)

    assert event.message_id == message.id


@pytest.mark.integration
def test_get_source_returns_a_persisted_event(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = repository.append(MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, message_id=None)

    fetched = repository.get_source(created.id)

    assert fetched == created


@pytest.mark.integration
def test_get_source_returns_none_for_an_unknown_id(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    assert repository.get_source(999) is None


@pytest.mark.integration
def test_events_persist_across_reopening_the_repository(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    created = repository.append(MANUAL_MEMORY_SAVE_EVENT_TYPE, USER_ACTOR, message_id=None)

    reopened = build_sqlite_event_repository(database_path)

    assert reopened.get_source(created.id) == created
