"""SQLite engine and session helpers for the persistence adapters."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


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
