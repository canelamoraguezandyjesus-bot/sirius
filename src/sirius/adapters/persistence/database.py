"""SQLite engine and session helpers for the persistence adapters."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# Floor SQLite has guaranteed for SQLITE_LIMIT_VARIABLE_NUMBER since before
# 3.32.0 (which raised the default to 32766). Used only if the DBAPI
# connection turns out not to be a sqlite3.Connection, which should not
# happen for this adapter but keeps the fallback from assuming an unverified,
# possibly higher limit.
_SQLITE_VARIABLE_LIMIT_FLOOR = 999


def build_engine(database_path: Path) -> Engine:
    """Create a SQLite engine bound to an explicit local file path."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{database_path}", future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: sqlite3.Connection, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        # RNF-006: fija explícitamente la durabilidad de cada commit en lugar
        # de depender del valor por defecto implícito de SQLite (que ya es
        # FULL fuera del modo WAL, pero afirmarlo aquí lo hace explícito y a
        # prueba de que un futuro cambio de configuración lo debilite sin que
        # nadie lo note). No se cambia el journal mode (sigue siendo el
        # rollback journal por defecto; WAL queda fuera de alcance de B11).
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.close()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the given engine."""
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Run a unit of work in a single transaction; roll back entirely on error."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def sqlite_variable_limit(session: Session) -> int:
    """Read the current connection's SQLITE_LIMIT_VARIABLE_NUMBER.

    Callers building an ``IN (...)`` clause from a caller-supplied list of ids
    must not exceed this many bound parameters per statement, or SQLite
    raises ``OperationalError: too many SQL variables``.
    """
    dbapi_connection = session.connection().connection.dbapi_connection
    if isinstance(dbapi_connection, sqlite3.Connection):
        return dbapi_connection.getlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER)
    return _SQLITE_VARIABLE_LIMIT_FLOOR


def chunked[T](items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Yield ``items`` in consecutive slices of at most ``size`` elements."""
    for start in range(0, len(items), size):
        yield items[start : start + size]
