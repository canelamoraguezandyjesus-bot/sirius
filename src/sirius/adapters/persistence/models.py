"""SQLAlchemy ORM models for the main conversation and its messages."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.domain.memory import MemoryStatus
from sirius.domain.project import ProjectStatus


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
    """A single message belonging to a conversation, in stable order.

    ``uq_messages_operation_role`` protects real idempotency: the USER
    message and the SIRIUS message of one turn share ``operation_id`` but
    differ in ``role``, so at most one row of each role may exist per
    ``operation_id``. Rows predating V6B keep ``operation_id`` NULL; SQL
    treats every NULL as distinct, so old rows never collide with each
    other or with new ones.
    """

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_messages_conversation_sequence"),
        UniqueConstraint(
            "conversation_id", "operation_id", "role", name="uq_messages_operation_role"
        ),
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
    operation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    identity_version: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[MessageStatus] = mapped_column(
        SAEnum(
            MessageStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            length=16,
        ),
        nullable=False,
        default=MessageStatus.COMPLETED,
        server_default=MessageStatus.COMPLETED.value,
    )


class EventModel(Base):
    """Immutable audit record of the action that produced a memory revision.

    SIRIUS-ARQ-0.1 S7.1/S7.3 minimal ``event`` fields; B4a populates only the
    subset RF-019/RF-021 need (``event_type``, ``actor``, a single
    ``message_id`` reference instead of the architecture's generic ``refs``
    JSON blob, since a real foreign key gives a stronger "enlace real" than a
    JSON reference for the one reference kind this cut requires).
    ``redacted_at`` stays ``NULL`` until B4d adds redaction.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    redacted_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ProjectModel(Base):
    """A project; exactly one row may have ``is_active`` set at any time.

    ``status``/``completed_at``/``current_revision_id`` are the authoritative
    lifecycle fields since B3c (SIRIUS-ARQ-0.1 S7.3 "Campos mínimos":
    ``project: id, name, status, current_revision_id, created_at,
    completed_at"). ``current_revision_id`` points at the single vigente row
    in ``project_revisions`` — ``NULL`` only for the neutral bootstrap
    placeholder, which has no revision yet. This is the sole authoritative
    mechanism for "which revision is current": there is no second,
    competing flag on ``ProjectRevisionModel``. ``is_active`` remains as a
    persistence-only projection kept in sync with ``status`` in the same
    transaction (``ACTIVE`` implies ``is_active = True``, ``COMPLETED``
    implies ``is_active = False``), because the SQLite partial unique index
    below can only express uniqueness over a plain boolean column — this
    field is additional to, not a substitute for, the architecture's minimum
    field list. ``objective``, ``current_state``, ``blockers``, and
    ``next_step`` are B3b's flat legacy columns, kept for non-destructive
    migration compatibility; they are no longer written or read by any code
    path added in B3c or later — ``ProjectRevisionModel`` is the sole
    authoritative source for that content going forward.
    """

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
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(
            ProjectStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            length=16,
        ),
        nullable=False,
    )
    current_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_revisions.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # --- Legacy B3b columns: compatibility only, see class docstring. ---
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    current_state: Mapped[str] = mapped_column(Text, nullable=False)
    blockers: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    next_step: Mapped[str] = mapped_column(Text, nullable=False)


class ProjectRevisionModel(Base):
    """One immutable, versioned snapshot of a project's continuity fields.

    Which revision is "current" is determined exclusively by
    ``ProjectModel.current_revision_id`` pointing at this row's ``id`` — this
    table carries no ``is_current`` flag or other second source of truth.
    ``blockers_json`` is a JSON array of strings — the sole place in Sirius
    that serializes blockers; every other layer works with the domain's
    ``tuple[str, ...]`` (application) or plain multiline text (presentation).
    ``source_event_id`` has no foreign key yet: the events table B4 will add
    does not exist in this cut.
    """

    __tablename__ = "project_revisions"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_project_revisions_project_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    state_summary: Mapped[str] = mapped_column(Text, nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    next_step: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


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

    ``source_event_id`` (B4a) is the real link to ``events`` RF-021 needs to
    open a memory's origin; ``NULL`` for every revision that predates B4a or
    was created through a path with no event yet (e.g. a B4c correction).
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
    source_event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)
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


class LLMUsageModel(Base):
    """Accumulated OpenAI spend for one UTC calendar month (DR-018).

    The minimal persistence a *monthly* budget envelope requires: without
    it, the cap would silently reset on every restart and stop being
    monthly at all. One row per ``year_month`` (e.g. ``"2026-07"``).
    """

    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    year_month: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    spent_usd: Mapped[float] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
