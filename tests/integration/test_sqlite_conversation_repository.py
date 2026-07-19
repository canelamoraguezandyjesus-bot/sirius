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
from sirius.adapters.persistence.models import Base, ConversationModel, MessageModel
from sirius.adapters.persistence.sqlite_conversation_repository import (
    SqliteConversationRepository,
    build_sqlite_conversation_repository,
)
from sirius.domain.conversation import MessageRole, MessageStatus


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


@pytest.mark.integration
def test_append_message_is_idempotent_per_operation_id_and_role(tmp_path: Path) -> None:
    """Retrying an operation after a persistence failure must not duplicate
    the message: calling ``append_message`` again with the same
    ``(conversation, operation_id, role)`` returns the existing row.
    """
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation = repository.get_or_create_main_conversation()

    first = repository.append_message(
        conversation.id, MessageRole.USER, "hola", operation_id="op-1"
    )
    second = repository.append_message(
        conversation.id, MessageRole.USER, "hola de nuevo (reintento)", operation_id="op-1"
    )

    assert second.id == first.id
    assert second.content == "hola"

    messages = repository.list_messages(conversation.id)
    assert len(messages) == 1


@pytest.mark.integration
def test_append_message_retry_is_idempotent_after_reopening_the_store(tmp_path: Path) -> None:
    """The idempotency check must survive an app restart, not just an
    in-memory retry within the same repository instance.
    """
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    first = repository.append_message(
        conversation.id, MessageRole.USER, "hola", operation_id="op-restart"
    )

    reopened_repository = build_sqlite_conversation_repository(database_path)
    second = reopened_repository.append_message(
        conversation.id, MessageRole.USER, "hola", operation_id="op-restart"
    )

    assert second.id == first.id
    assert len(reopened_repository.list_messages(conversation.id)) == 1


@pytest.mark.integration
def test_append_message_allows_several_null_operation_id_rows(tmp_path: Path) -> None:
    """Rows predating V6B keep ``operation_id`` NULL; SQL treats every NULL
    as distinct, so pre-existing rows never collide with each other.
    """
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation = repository.get_or_create_main_conversation()

    first = repository.append_message(conversation.id, MessageRole.USER, "uno")
    second = repository.append_message(conversation.id, MessageRole.USER, "dos")

    assert first.id != second.id
    assert first.operation_id is None
    assert second.operation_id is None


@pytest.mark.integration
def test_append_message_persists_the_given_status(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation = repository.get_or_create_main_conversation()

    cancelled = repository.append_message(
        conversation.id,
        MessageRole.SIRIUS,
        "texto parcial",
        operation_id="op-cancel",
        status=MessageStatus.CANCELLED,
    )

    assert cancelled.status is MessageStatus.CANCELLED
    reopened = build_sqlite_conversation_repository(database_path)
    (reloaded,) = reopened.list_messages(conversation.id)
    assert reloaded.status is MessageStatus.CANCELLED
    assert reloaded.content == "texto parcial"


@pytest.mark.integration
def test_append_message_defaults_status_to_completed(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation = repository.get_or_create_main_conversation()

    message = repository.append_message(conversation.id, MessageRole.USER, "hola")

    assert message.status is MessageStatus.COMPLETED


@pytest.mark.integration
def test_database_rejects_a_second_row_for_the_same_operation_and_role(tmp_path: Path) -> None:
    """The unique constraint is the backstop even if some caller bypasses the
    repository's own pre-check and inserts directly.
    """
    database_path = tmp_path / "sirius.db"
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    repository = build_sqlite_conversation_repository(database_path)
    conversation = repository.get_or_create_main_conversation()

    now = datetime.now(UTC).replace(tzinfo=None)
    with session_scope(session_factory) as session:
        session.add(
            MessageModel(
                conversation_id=conversation.id,
                sequence=1,
                role=MessageRole.USER,
                content="uno",
                created_at=now,
                operation_id="op-dup",
                status=MessageStatus.COMPLETED,
            )
        )

    with (
        pytest.raises(IntegrityError),
        session_scope(session_factory) as session,
    ):
        session.add(
            MessageModel(
                conversation_id=conversation.id,
                sequence=2,
                role=MessageRole.USER,
                content="dos",
                created_at=now,
                operation_id="op-dup",
                status=MessageStatus.COMPLETED,
            )
        )
        session.flush()


@pytest.mark.integration
def test_redact_message_nulls_content_and_sets_status_and_timestamp(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    message = repository.append_message(conversation.id, MessageRole.USER, "recuerda esto")

    redacted = repository.redact_message(message.id)

    assert redacted.content is None
    assert redacted.status is MessageStatus.REDACTED
    assert redacted.redacted_at is not None
    assert redacted.sequence == message.sequence
    assert redacted.created_at == message.created_at


@pytest.mark.integration
def test_redact_message_never_touches_a_different_message(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    target = repository.append_message(conversation.id, MessageRole.USER, "redactar este")
    other = repository.append_message(conversation.id, MessageRole.SIRIUS, "conservar este")

    repository.redact_message(target.id)

    untouched = repository.get_message(other.id)
    assert untouched is not None
    assert untouched.content == "conservar este"
    assert untouched.status is MessageStatus.COMPLETED
    assert untouched.redacted_at is None


@pytest.mark.integration
def test_redact_message_rejects_an_unknown_id(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown message"):
        repository.redact_message(999)


@pytest.mark.integration
def test_redaction_persists_after_closing_and_reopening_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    message = repository.append_message(conversation.id, MessageRole.USER, "recuerda esto")
    repository.redact_message(message.id)
    repository.close()

    reopened = build_sqlite_conversation_repository(database_path)
    (reloaded,) = reopened.list_messages(conversation.id)
    assert reloaded.content is None
    assert reloaded.status is MessageStatus.REDACTED
    reopened.close()
