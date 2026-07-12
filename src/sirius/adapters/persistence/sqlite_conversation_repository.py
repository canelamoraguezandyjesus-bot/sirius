"""SQLite-backed implementation of the conversation repository port."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import ConversationModel, MessageModel
from sirius.domain.conversation import Conversation, Message, MessageRole, MessageStatus


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_domain_conversation(model: ConversationModel) -> Conversation:
    return Conversation(id=model.id, created_at=model.created_at.replace(tzinfo=UTC))


def _to_domain_message(model: MessageModel) -> Message:
    return Message(
        id=model.id,
        conversation_id=model.conversation_id,
        sequence=model.sequence,
        role=model.role,
        content=model.content,
        created_at=model.created_at.replace(tzinfo=UTC),
        operation_id=model.operation_id,
        identity_version=model.identity_version,
        status=model.status,
    )


def _find_main_conversation_model(session: Session) -> ConversationModel | None:
    return session.scalars(
        select(ConversationModel).where(ConversationModel.is_main.is_(True)).limit(1)
    ).first()


class SqliteConversationRepository:
    """Conversation repository backed by a local SQLite database."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_or_create_main_conversation(self) -> Conversation:
        with session_scope(self._session_factory) as session:
            model = _find_main_conversation_model(session)
            if model is None:
                model = ConversationModel(created_at=_utc_now_naive(), is_main=True)
                session.add(model)
                session.flush()
            return _to_domain_conversation(model)

    def get_main_conversation(self) -> Conversation | None:
        with session_scope(self._session_factory) as session:
            model = _find_main_conversation_model(session)
            if model is None:
                return None
            return _to_domain_conversation(model)

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
        with session_scope(self._session_factory) as session:
            conversation = session.get(ConversationModel, conversation_id)
            if conversation is None:
                msg = f"Unknown conversation id: {conversation_id}"
                raise ValueError(msg)

            if operation_id is not None:
                # Idempotent per (conversation, operation, role): retrying an
                # operation after a persistence failure must not duplicate a
                # message that already made it in. The unique constraint on
                # the table is the backstop against any race.
                existing = session.scalars(
                    select(MessageModel).where(
                        MessageModel.conversation_id == conversation_id,
                        MessageModel.operation_id == operation_id,
                        MessageModel.role == role,
                    )
                ).first()
                if existing is not None:
                    return _to_domain_message(existing)

            last_sequence = session.scalars(
                select(MessageModel.sequence)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(MessageModel.sequence.desc())
                .limit(1)
            ).first()
            next_sequence = (last_sequence or 0) + 1

            model = MessageModel(
                conversation_id=conversation_id,
                sequence=next_sequence,
                role=role,
                content=content,
                created_at=_utc_now_naive(),
                operation_id=operation_id,
                identity_version=identity_version,
                status=status,
            )
            session.add(model)
            session.flush()
            return _to_domain_message(model)

    def list_messages(self, conversation_id: int) -> list[Message]:
        with session_scope(self._session_factory) as session:
            models = session.scalars(
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(MessageModel.sequence)
            ).all()
            return [_to_domain_message(model) for model in models]


def build_sqlite_conversation_repository(database_path: Path) -> SqliteConversationRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteConversationRepository(session_factory)
