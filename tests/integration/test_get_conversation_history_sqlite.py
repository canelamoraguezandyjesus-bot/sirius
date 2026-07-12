from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import Base, ConversationModel, MessageModel
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.application.get_conversation_history import (
    ConversationNotInitializedError,
    GetConversationHistoryUseCase,
)
from sirius.domain.conversation import MessageRole


@pytest.mark.integration
def test_get_history_raises_before_bootstrap(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    use_case = GetConversationHistoryUseCase(build_sqlite_conversation_repository(database_path))

    with pytest.raises(ConversationNotInitializedError):
        use_case.get_history()


@pytest.mark.integration
def test_get_history_returns_persisted_messages_in_order(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    conversation_repository.append_message(conversation.id, MessageRole.USER, "uno")
    conversation_repository.append_message(conversation.id, MessageRole.SIRIUS, "dos")

    use_case = GetConversationHistoryUseCase(conversation_repository)
    history = use_case.get_history()

    assert [m.content for m in history] == ["uno", "dos"]


@pytest.mark.integration
def test_get_history_returns_empty_list_for_an_existing_conversation_without_messages(
    tmp_path: Path,
) -> None:
    """Only a missing main conversation is an error; zero messages is not."""
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation_repository.get_or_create_main_conversation()

    use_case = GetConversationHistoryUseCase(conversation_repository)
    history = use_case.get_history()

    assert history == []


@pytest.mark.integration
def test_get_history_does_not_write_anything(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    Base.metadata.create_all(build_engine(database_path))
    conversation_repository = build_sqlite_conversation_repository(database_path)
    conversation_repository.get_or_create_main_conversation()

    use_case = GetConversationHistoryUseCase(conversation_repository)
    use_case.get_history()
    use_case.get_history()

    # Still exactly one conversation and no messages: reading never creates data.
    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        assert len(session.scalars(select(ConversationModel)).all()) == 1
        assert session.scalars(select(MessageModel)).first() is None
