"""SQLite-backed implementation of the event repository port."""

from __future__ import annotations

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
    """Event repository backed by a local SQLite database."""

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._engine = engine

    def close(self) -> None:
        """Release every pooled connection this repository's engine holds."""
        self._engine.dispose()

    def append(self, event_type: str, actor: str, message_id: int | None) -> Event:
        with session_scope(self._session_factory) as session:
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
        with session_scope(self._session_factory) as session:
            model = session.get(EventModel, event_id)
            if model is None:
                return None
            return _to_domain_event(model)


def build_sqlite_event_repository(database_path: Path) -> SqliteEventRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteEventRepository(session_factory, engine)
