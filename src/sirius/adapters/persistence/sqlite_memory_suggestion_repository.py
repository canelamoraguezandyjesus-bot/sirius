"""SQLite-backed implementation of the memory suggestion repository port."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import MemorySuggestionModel
from sirius.domain.memory_suggestion import (
    MemorySuggestion,
    MemorySuggestionStatus,
    ensure_can_confirm,
    ensure_can_reject,
)


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_naive_utc(instant: datetime) -> datetime:
    return instant.astimezone(UTC).replace(tzinfo=None)


def _to_domain(model: MemorySuggestionModel) -> MemorySuggestion:
    return MemorySuggestion(
        id=model.id,
        content=model.content,
        status=model.status,
        source_event_id=model.source_event_id,
        created_at=model.created_at.replace(tzinfo=UTC),
        resolved_at=(
            model.resolved_at.replace(tzinfo=UTC) if model.resolved_at is not None else None
        ),
        resulting_memory_id=model.resulting_memory_id,
        subject_key=model.subject_key,
        project_id=model.project_id,
    )


class SqliteMemorySuggestionRepository:
    """Memory suggestion repository backed by a local SQLite database.

    Normally owns its ``session_factory`` and opens/commits/closes one short
    session per call (via ``session_scope``). When ``session`` is given
    instead, every call writes through that externally owned session and
    never commits or closes it — this is how ``SqliteUnitOfWork`` binds this
    repository to the same transaction as the others it exposes.
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

    def _get_model(self, session: Session, suggestion_id: int) -> MemorySuggestionModel:
        model = session.get(MemorySuggestionModel, suggestion_id)
        if model is None:
            msg = f"Unknown memory suggestion id: {suggestion_id}"
            raise ValueError(msg)
        return model

    def create_suggestion(
        self,
        content: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> MemorySuggestion:
        with self._scope() as session:
            model = MemorySuggestionModel(
                content=content,
                status=MemorySuggestionStatus.PENDING,
                subject_key=subject_key,
                project_id=project_id,
                source_event_id=source_event_id,
                created_at=_utc_now_naive(),
            )
            session.add(model)
            session.flush()
            return _to_domain(model)

    def get_suggestion(self, suggestion_id: int) -> MemorySuggestion:
        with self._scope() as session:
            return _to_domain(self._get_model(session, suggestion_id))

    def list_pending_suggestions(self) -> list[MemorySuggestion]:
        with self._scope() as session:
            models = session.scalars(
                select(MemorySuggestionModel)
                .where(MemorySuggestionModel.status == MemorySuggestionStatus.PENDING)
                .order_by(MemorySuggestionModel.id)
            ).all()
            return [_to_domain(model) for model in models]

    def confirm_suggestion(
        self, suggestion_id: int, *, resulting_memory_id: int, resolved_at: datetime
    ) -> MemorySuggestion:
        with self._scope() as session:
            model = self._get_model(session, suggestion_id)
            ensure_can_confirm(_to_domain(model))

            model.status = MemorySuggestionStatus.CONFIRMED
            model.resulting_memory_id = resulting_memory_id
            model.resolved_at = _to_naive_utc(resolved_at)
            session.flush()
            return _to_domain(model)

    def reject_suggestion(self, suggestion_id: int, *, resolved_at: datetime) -> MemorySuggestion:
        with self._scope() as session:
            model = self._get_model(session, suggestion_id)
            ensure_can_reject(_to_domain(model))

            model.status = MemorySuggestionStatus.REJECTED
            model.resolved_at = _to_naive_utc(resolved_at)
            session.flush()
            return _to_domain(model)


def build_sqlite_memory_suggestion_repository(
    database_path: Path,
) -> SqliteMemorySuggestionRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteMemorySuggestionRepository(session_factory, engine)


def bind_sqlite_memory_suggestion_repository(session: Session) -> SqliteMemorySuggestionRepository:
    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
    return SqliteMemorySuggestionRepository(None, None, session=session)
