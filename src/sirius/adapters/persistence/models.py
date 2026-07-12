"""SQLAlchemy ORM models for the main conversation and its messages."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sirius.domain.conversation import MessageRole


class Base(DeclarativeBase):
    """Declarative base shared by every Sirius persistence model."""


class ConversationModel(Base):
    """A conversation; exactly one row may have ``is_main`` set at any time."""

    __tablename__ = "conversations"
    __table_args__ = (
        Index(
            "uq_conversations_single_main",
            "is_main",
            unique=True,
            sqlite_where=text("is_main = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    is_main: Mapped[bool] = mapped_column(nullable=False, default=True)


class MessageModel(Base):
    """A single message belonging to a conversation, in stable order."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_messages_conversation_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(nullable=False)
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(
            MessageRole,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            length=16,
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
