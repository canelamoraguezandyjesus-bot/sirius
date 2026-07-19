"""SQLite-backed implementation of the memory repository port."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import MemoryModel, MemoryRevisionModel
from sirius.domain.memory import (
    Memory,
    MemoryRevision,
    MemoryStatus,
    ensure_can_archive,
    ensure_can_correct,
    ensure_can_delete,
    ensure_valid_origin,
    next_revision_version,
)


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_domain_revision(model: MemoryRevisionModel) -> MemoryRevision:
    return MemoryRevision(
        id=model.id,
        memory_id=model.memory_id,
        version=model.version,
        content=model.content,
        origin=model.origin,
        source_event_id=model.source_event_id,
        created_at=model.created_at.replace(tzinfo=UTC),
    )


def _to_domain_memory(model: MemoryModel, revision_model: MemoryRevisionModel) -> Memory:
    return Memory(
        id=model.id,
        status=model.status,
        current_revision=_to_domain_revision(revision_model),
        created_at=model.created_at.replace(tzinfo=UTC),
        updated_at=model.updated_at.replace(tzinfo=UTC),
    )


def _get_current_revision_model(session: Session, memory_id: int) -> MemoryRevisionModel:
    revision_model = session.scalars(
        select(MemoryRevisionModel).where(
            MemoryRevisionModel.memory_id == memory_id,
            MemoryRevisionModel.is_current.is_(True),
        )
    ).first()
    if revision_model is None:
        msg = f"Memory {memory_id} has no current revision; data is corrupt."
        raise ValueError(msg)
    return revision_model


def _load_memory(session: Session, model: MemoryModel) -> Memory:
    revision_model = _get_current_revision_model(session, model.id)
    return _to_domain_memory(model, revision_model)


class SqliteMemoryRepository:
    """Memory repository backed by a local SQLite database.

    Normally owns its ``session_factory`` and opens/commits/closes one short
    session per call (via ``session_scope``). When ``session`` is given
    instead, every call writes through that externally owned session and
    never commits or closes it — this is how ``SqliteUnitOfWork`` binds this
    repository to the same transaction as ``SqliteEventRepository``, so both
    commit or roll back together.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None,
        engine: Engine | None,
        *,
        session: Session | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._external_session = session

    def close(self) -> None:
        """Release every pooled connection this repository's engine holds."""
        if self._engine is not None:
            self._engine.dispose()

    @contextmanager
    def _scope(self) -> Iterator[Session]:
        if self._external_session is not None:
            yield self._external_session
            return
        assert self._session_factory is not None
        with session_scope(self._session_factory) as session:
            yield session

    def create_memory(
        self, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        ensure_valid_origin(origin)
        with self._scope() as session:
            now = _utc_now_naive()
            memory_model = MemoryModel(
                status=MemoryStatus.CURRENT,
                created_at=now,
                updated_at=now,
            )
            session.add(memory_model)
            session.flush()

            revision_model = MemoryRevisionModel(
                memory_id=memory_model.id,
                version=1,
                content=content,
                origin=origin,
                source_event_id=source_event_id,
                is_current=True,
                created_at=now,
            )
            session.add(revision_model)
            session.flush()

            return _to_domain_memory(memory_model, revision_model)

    def get_memory(self, memory_id: int) -> Memory:
        with self._scope() as session:
            model = session.get(MemoryModel, memory_id)
            if model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            return _load_memory(session, model)

    def list_current_memories(self) -> list[Memory]:
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(MemoryModel.status == MemoryStatus.CURRENT)
                .order_by(MemoryModel.id)
            ).all()
            return [_load_memory(session, model) for model in models]

    def list_archived_memories(self) -> list[Memory]:
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(MemoryModel.status == MemoryStatus.ARCHIVED)
                .order_by(MemoryModel.id)
            ).all()
            return [_load_memory(session, model) for model in models]

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            revision_models = session.scalars(
                select(MemoryRevisionModel)
                .where(MemoryRevisionModel.memory_id == memory_id)
                .order_by(MemoryRevisionModel.version)
            ).all()
            return [_to_domain_revision(model) for model in revision_models]

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        ensure_valid_origin(origin)
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            memory = _load_memory(session, memory_model)
            ensure_can_correct(memory)

            current_revision_model = _get_current_revision_model(session, memory_id)
            current_revision_model.is_current = False
            session.flush()

            new_revision_model = MemoryRevisionModel(
                memory_id=memory_id,
                version=next_revision_version(memory.current_revision),
                content=content,
                origin=origin,
                source_event_id=source_event_id,
                is_current=True,
                created_at=_utc_now_naive(),
            )
            session.add(new_revision_model)
            memory_model.updated_at = _utc_now_naive()
            session.flush()

            return _to_domain_memory(memory_model, new_revision_model)

    def archive_memory(self, memory_id: int) -> Memory:
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            memory = _load_memory(session, memory_model)
            ensure_can_archive(memory)

            memory_model.status = MemoryStatus.ARCHIVED
            memory_model.updated_at = _utc_now_naive()
            session.flush()

            return _load_memory(session, memory_model)

    def delete_memory(self, memory_id: int) -> Memory:
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            memory = _load_memory(session, memory_model)
            ensure_can_delete(memory)

            # Redact structured content across the full history; is_current is
            # left untouched so exactly one revision stays marked as current.
            revision_models = session.scalars(
                select(MemoryRevisionModel).where(MemoryRevisionModel.memory_id == memory_id)
            ).all()
            for revision_model in revision_models:
                revision_model.content = None

            memory_model.status = MemoryStatus.DELETED
            memory_model.updated_at = _utc_now_naive()
            session.flush()

            return _load_memory(session, memory_model)


def build_sqlite_memory_repository(database_path: Path) -> SqliteMemoryRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteMemoryRepository(session_factory, engine)


def bind_sqlite_memory_repository(session: Session) -> SqliteMemoryRepository:
    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
    return SqliteMemoryRepository(None, None, session=session)
