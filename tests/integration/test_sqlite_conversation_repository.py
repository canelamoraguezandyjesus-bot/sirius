from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import Base, ConversationModel
from sirius.adapters.persistence.sqlite_conversation_repository import (
    SqliteConversationRepository,
    build_sqlite_conversation_repository,
)
from sirius.domain.conversation import MessageRole


def _build_repository(database_path: Path) -> SqliteConversationRepository:
    repository = build_sqlite_conversation_repository(database_path)
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    return repository


@pytest.mark.integration
def test_get_or_create_main_conversation_creates_exactly_one_row(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    conversation = repository.get_or_create_main_conversation()

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        rows = session.scalars(select(ConversationModel)).all()

    assert len(rows) == 1
    assert rows[0].id == conversation.id


@pytest.mark.integration
def test_get_or_create_main_conversation_is_idempotent_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    first_repository = _build_repository(database_path)
    first_conversation = first_repository.get_or_create_main_conversation()

    # Simulate closing the app and reopening the store with a brand-new engine.
    second_repository = build_sqlite_conversation_repository(database_path)
    second_conversation = second_repository.get_or_create_main_conversation()

    assert second_conversation.id == first_conversation.id

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        rows = session.scalars(select(ConversationModel)).all()
    assert len(rows) == 1


@pytest.mark.integration
def test_messages_are_recovered_in_stable_order_after_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation = repository.get_or_create_main_conversation()

    repository.append_message(conversation.id, MessageRole.USER, "Hola Sirius")
    repository.append_message(conversation.id, MessageRole.SIRIUS, "Hola, ¿en qué trabajamos?")
    repository.append_message(conversation.id, MessageRole.USER, "Quiero revisar el plan")

    # A brand-new repository/engine simulates the app being closed and reopened.
    reopened_repository = build_sqlite_conversation_repository(database_path)
    messages = reopened_repository.list_messages(conversation.id)

    assert [message.sequence for message in messages] == [1, 2, 3]
    assert [message.role for message in messages] == [
        MessageRole.USER,
        MessageRole.SIRIUS,
        MessageRole.USER,
    ]
    assert [message.content for message in messages] == [
        "Hola Sirius",
        "Hola, ¿en qué trabajamos?",
        "Quiero revisar el plan",
    ]


@pytest.mark.integration
def test_append_message_rejects_unknown_conversation(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown conversation"):
        repository.append_message(999, MessageRole.USER, "huérfano")


@pytest.mark.integration
def test_database_rejects_a_second_main_conversation(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    with session_scope(session_factory) as session:
        session.add(
            ConversationModel(created_at=datetime.now(UTC).replace(tzinfo=None), is_main=True)
        )

    with (
        pytest.raises(IntegrityError),
        session_scope(session_factory) as session,
    ):
        session.add(
            ConversationModel(created_at=datetime.now(UTC).replace(tzinfo=None), is_main=True)
        )
        session.flush()

    with session_scope(session_factory) as session:
        rows = session.scalars(select(ConversationModel)).all()
    assert len(rows) == 1


@pytest.mark.integration
def test_failed_operation_leaves_no_partial_data(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    class Boom(Exception):
        pass

    with pytest.raises(Boom), session_scope(session_factory) as session:
        session.add(ConversationModel(created_at=datetime.now(UTC).replace(tzinfo=None)))
        session.flush()
        raise Boom

    with session_scope(session_factory) as session:
        rows = session.scalars(select(ConversationModel)).all()
    assert rows == []
