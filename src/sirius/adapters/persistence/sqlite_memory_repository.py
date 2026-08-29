"""SQLite-backed implementation of the memory repository port."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import CursorResult, Engine, exists, select, update
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    chunked,
    session_scope,
    sqlite_variable_limit,
)
from sirius.adapters.persistence.models import MemoryModel, MemoryRevisionModel
from sirius.domain.memory import (
    Memory,
    MemoryRevision,
    MemoryStatus,
    ensure_can_archive,
    ensure_can_correct,
    ensure_can_delete,
    ensure_subject_key_has_a_project,
    ensure_valid_origin,
    ensure_valid_subject_key,
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
        subject_key=model.subject_key,
        project_id=model.project_id,
        category=model.category,
        category_locked=model.category_locked,
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


def _load_memories(session: Session, models: Sequence[MemoryModel]) -> list[Memory]:
    """Load the current revision of every model in a bounded number of queries.

    ``_load_memory`` issues one query per model; called from a list method
    that turns into N+1 queries for N models. This loads every current
    revision the set needs via ``IN (...)`` queries instead, batched to the
    connection's ``SQLITE_LIMIT_VARIABLE_NUMBER`` so a large set doesn't blow
    past SQLite's bound-parameter limit in a single statement.
    """
    if not models:
        return []
    memory_ids = [model.id for model in models]
    revisions_by_memory_id: dict[int, MemoryRevisionModel] = {}
    for batch in chunked(memory_ids, sqlite_variable_limit(session)):
        revision_models = session.scalars(
            select(MemoryRevisionModel).where(
                MemoryRevisionModel.memory_id.in_(batch),
                MemoryRevisionModel.is_current.is_(True),
            )
        ).all()
        revisions_by_memory_id.update(
            (revision.memory_id, revision) for revision in revision_models
        )
    memories = []
    for model in models:
        revision_model = revisions_by_memory_id.get(model.id)
        if revision_model is None:
            msg = f"Memory {model.id} has no current revision; data is corrupt."
            raise ValueError(msg)
        memories.append(_to_domain_memory(model, revision_model))
    return memories


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
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        ensure_valid_origin(origin)
        ensure_valid_subject_key(subject_key)
        ensure_subject_key_has_a_project(subject_key, project_id)
        with self._scope() as session:
            now = _utc_now_naive()
            memory_model = MemoryModel(
                status=MemoryStatus.CURRENT,
                subject_key=subject_key,
                project_id=project_id,
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
            return _load_memories(session, models)

    def list_archived_memories(self) -> list[Memory]:
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(MemoryModel.status == MemoryStatus.ARCHIVED)
                .order_by(MemoryModel.id)
            ).all()
            return _load_memories(session, models)

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
            # D7, "Corrección de contenido y reetiquetado" (SIRIUS-ARQ-0.2
            # §6.1): the content that produced the current category no
            # longer describes this memory once corrected. If the category
            # is still the automatic one (category_locked is False), clear
            # it in this same transaction; a user-locked category is never
            # touched by a correction (point 3).
            if not memory_model.category_locked:
                memory_model.category = None
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

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        with self._scope() as session:
            # Single atomic UPDATE: the EXISTS subquery re-checks, in the
            # same statement, that the current revision is still the one
            # that was classified — comprobar y escribir son una sola
            # operación atómica de la base de datos (D7 point 2), never a
            # read in Python followed by a separate write.
            statement = (
                update(MemoryModel)
                .where(
                    MemoryModel.id == memory_id,
                    MemoryModel.category_locked.is_(False),
                    exists().where(
                        MemoryRevisionModel.memory_id == MemoryModel.id,
                        MemoryRevisionModel.is_current.is_(True),
                        MemoryRevisionModel.version == observed_revision_version,
                    ),
                )
                .values(category=category)
            )
            result = cast(CursorResult[None], session.execute(statement))
            return result.rowcount > 0

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            memory_model.category = category
            memory_model.category_locked = True
            session.flush()
            return _load_memory(session, memory_model)

    def list_uncategorized(self) -> list[Memory]:
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(
                    MemoryModel.category.is_(None),
                    MemoryModel.category_locked.is_(False),
                )
                .order_by(MemoryModel.id)
            ).all()
            return _load_memories(session, models)


def build_sqlite_memory_repository(database_path: Path) -> SqliteMemoryRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteMemoryRepository(session_factory, engine)


def bind_sqlite_memory_repository(session: Session) -> SqliteMemoryRepository:
    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
    return SqliteMemoryRepository(None, None, session=session)
