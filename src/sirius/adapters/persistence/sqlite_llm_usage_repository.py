"""SQLite-backed implementation of the LLM usage-ledger port (DR-018)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import LLMUsageModel


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SqliteLLMUsageRepository:
    """Persists accumulated OpenAI spend per UTC calendar month."""

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._engine = engine

    def close(self) -> None:
        """Release every pooled connection this repository's engine holds."""
        self._engine.dispose()

    def get_spent_usd(self, year_month: str) -> float:
        with session_scope(self._session_factory) as session:
            model = session.scalars(
                select(LLMUsageModel).where(LLMUsageModel.year_month == year_month)
            ).first()
            return model.spent_usd if model is not None else 0.0

    def add_spent_usd(self, year_month: str, amount_usd: float) -> None:
        with session_scope(self._session_factory) as session:
            model = session.scalars(
                select(LLMUsageModel).where(LLMUsageModel.year_month == year_month)
            ).first()
            now = _utc_now_naive()
            if model is None:
                model = LLMUsageModel(year_month=year_month, spent_usd=amount_usd, updated_at=now)
                session.add(model)
            else:
                model.spent_usd += amount_usd
                model.updated_at = now


def build_sqlite_llm_usage_repository(database_path: Path) -> SqliteLLMUsageRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteLLMUsageRepository(session_factory, engine)
