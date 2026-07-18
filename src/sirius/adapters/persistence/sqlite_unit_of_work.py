"""SQLite-backed ``UnitOfWork``: one session/transaction shared by its repositories.

SIRIUS-ARQ-0.1 S4/S8.1: the memory, event and decision repositories it
exposes write through the exact same SQLAlchemy ``Session`` — hence the same
connection and transaction — so ``commit()`` confirms all of them together
and any exception rolls all of them back together.
"""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Self

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import build_engine, build_session_factory
from sirius.adapters.persistence.sqlite_decision_repository import (
    SqliteDecisionRepository,
    bind_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import (
    SqliteEventRepository,
    bind_sqlite_event_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import (
    SqliteMemoryRepository,
    bind_sqlite_memory_repository,
)

__all__ = ["SqliteUnitOfWork", "build_sqlite_unit_of_work"]


class SqliteUnitOfWork:
    """Groups the memory, event and decision repositories into one SQLite transaction.

    One instance is reusable across many, unrelated operations: each
    ``with`` block opens its own fresh session (``begin()``), so a rollback
    in one operation never affects the next one entered afterwards.
    """

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._session: Session | None = None
        self._committed = False
        self.memory_repository: SqliteMemoryRepository
        self.event_repository: SqliteEventRepository
        self.decision_repository: SqliteDecisionRepository

    def close(self) -> None:
        """Release every pooled connection this unit of work's engine holds."""
        self._engine.dispose()

    def begin(self) -> None:
        """Open a new session and bind the repositories to it."""
        self._session = self._session_factory()
        self._committed = False
        self.memory_repository = bind_sqlite_memory_repository(self._session)
        self.event_repository = bind_sqlite_event_repository(self._session)
        self.decision_repository = bind_sqlite_decision_repository(self._session)

    def __enter__(self) -> Self:
        self.begin()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None or not self._committed:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None

    def commit(self) -> None:
        """Confirm every write made through this unit of work's repositories."""
        assert self._session is not None
        self._session.commit()
        self._committed = True

    def rollback(self) -> None:
        """Discard every write made through this unit of work's repositories."""
        assert self._session is not None
        self._session.rollback()
        self._committed = False


def build_sqlite_unit_of_work(database_path: Path) -> SqliteUnitOfWork:
    """Build a unit of work backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteUnitOfWork(session_factory, engine)
