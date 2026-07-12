"""SQLAlchemy ORM models for the main conversation and its messages."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sirius.domain.conversation import MessageRole
from sirius.domain.memory import MemoryStatus


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


class ProjectModel(Base):
    """A project; exactly one row may have ``is_active`` set at any time."""

    __tablename__ = "projects"
    __table_args__ = (
        Index(
            "uq_projects_single_active",
            "is_active",
            unique=True,
            sqlite_where=text("is_active = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    current_state: Mapped[str] = mapped_column(Text, nullable=False)
    next_step: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)


class MemoryModel(Base):
    """A stable memory item. Its current revision is found in ``memory_revisions``
    by querying ``memory_id`` together with ``is_current = True``.
    """

    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[MemoryStatus] = mapped_column(
        SAEnum(
            MemoryStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            length=16,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)


class MemoryRevisionModel(Base):
    """One immutable, versioned content snapshot of a memory; at most one row
    per ``memory_id`` may have ``is_current`` set at any time.

    ``content`` becomes NULL when the owning memory is deleted: structured
    content is redacted, but the row (version, origin, created_at) remains as
    a minimal marker.
    """

    __tablename__ = "memory_revisions"
    __table_args__ = (
        UniqueConstraint("memory_id", "version", name="uq_memory_revisions_memory_version"),
        Index(
            "uq_memory_revisions_single_current_per_memory",
            "memory_id",
            unique=True,
            sqlite_where=text("is_current = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    memory_id: Mapped[int] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class IdentityModel(Base):
    """Sirius's single identity. Its current version is found in
    ``identity_versions`` by querying ``identity_id`` together with
    ``is_current = True``.
    """

    __tablename__ = "identities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class IdentityVersionModel(Base):
    """One immutable, versioned snapshot of Sirius's identity; at most one row
    per ``identity_id`` may have ``is_current`` set at any time.
    """

    __tablename__ = "identity_versions"
    __table_args__ = (
        UniqueConstraint("identity_id", "version", name="uq_identity_versions_identity_version"),
        Index(
            "uq_identity_versions_single_current_per_identity",
            "identity_id",
            unique=True,
            sqlite_where=text("is_current = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    identity_id: Mapped[int] = mapped_column(
        ForeignKey("identities.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    personality_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    is_current: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
