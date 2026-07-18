"""SQLite-backed implementation of the event repository port."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import EventModel
from sirius.domain.event import Event


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_domain_event(model: EventModel) -> Event:
    return Event(
        id=model.id,
        event_type=model.event_type,
        actor=model.actor,
        message_id=model.message_id,
        created_at=model.created_at.replace(tzinfo=UTC),
        redacted_at=(
            model.redacted_at.replace(tzinfo=UTC) if model.redacted_at is not None else None
        ),
    )


class SqliteEventRepository:
    """Event repository backed by a local SQLite database.

    Normally owns its ``session_factory`` and opens/commits/closes one short
    session per call (via ``session_scope``). When ``session`` is given
    instead, every call writes through that externally owned session and
    never commits or closes it — this is how ``SqliteUnitOfWork`` binds this
    repository to the same transaction as ``SqliteMemoryRepository``, so both
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

    def append(self, event_type: str, actor: str, message_id: int | None) -> Event:
        with self._scope() as session:
            model = EventModel(
                event_type=event_type,
                actor=actor,
                message_id=message_id,
                created_at=_utc_now_naive(),
                redacted_at=None,
            )
            session.add(model)
            session.flush()
            return _to_domain_event(model)

    def get_source(self, event_id: int) -> Event | None:
        with self._scope() as session:
            model = session.get(EventModel, event_id)
            if model is None:
                return None
            return _to_domain_event(model)


def build_sqlite_event_repository(database_path: Path) -> SqliteEventRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteEventRepository(session_factory, engine)


def bind_sqlite_event_repository(session: Session) -> SqliteEventRepository:
    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
    return SqliteEventRepository(None, None, session=session)
