"""SQLite-backed implementation of the FTS5 knowledge search port (B6b)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.domain.relevance import KnowledgeKind

__all__ = [
    "SqliteKnowledgeSearchRepository",
    "bind_sqlite_knowledge_search_repository",
    "build_sqlite_knowledge_search_repository",
    "sanitize_fts5_query",
]

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


def sanitize_fts5_query(query_text: str) -> str:
    """Turn free-form user text into a safe FTS5 ``MATCH`` argument.

    Every alphanumeric token is extracted and individually double-quoted (an
    FTS5 string literal, never interpreted as an operator), then joined with
    ``OR`` so any one matching term counts as a hit. Column filters
    (``content:``), boolean keywords (``AND``/``NOT``/``NEAR``) and stray
    punctuation (``"``, ``*``, ``(``, a leading ``-``, ...) can therefore
    never reach FTS5's own query parser — a message with special characters
    can never break the query's syntax.

    A query with no alphanumeric token at all (blank, or only punctuation)
    returns an empty string. Callers must treat that as "no FTS5 match" and
    never execute a ``MATCH ''`` — FTS5 itself rejects an empty match
    expression as a syntax error.
    """
    tokens = _TOKEN_PATTERN.findall(query_text)
    return " OR ".join(f'"{token}"' for token in tokens)


class SqliteKnowledgeSearchRepository:
    """Read-only FTS5 search over ``knowledge_fts`` (B6a), backed by SQLite.

    Mirrors the other Sqlite*Repository classes' dual-mode constructor:
    normally owns its ``session_factory`` and opens/commits/closes one short
    session per call (via ``session_scope``); when ``session`` is given
    instead, it reads through that externally owned session — a read never
    needs its own transaction, but sharing an ongoing one (``SqliteUnitOfWork``)
    is harmless.
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

    def search_knowledge(self, query_text: str) -> frozenset[tuple[KnowledgeKind, int]]:
        sanitized = sanitize_fts5_query(query_text)
        if not sanitized:
            return frozenset()
        with self._scope() as session:
            rows = session.execute(
                text("SELECT kind, item_id FROM knowledge_fts WHERE knowledge_fts MATCH :query"),
                {"query": sanitized},
            ).all()
            return frozenset((KnowledgeKind(row.kind), row.item_id) for row in rows)


def build_sqlite_knowledge_search_repository(
    database_path: Path,
) -> SqliteKnowledgeSearchRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteKnowledgeSearchRepository(session_factory, engine)


def bind_sqlite_knowledge_search_repository(session: Session) -> SqliteKnowledgeSearchRepository:
    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
    return SqliteKnowledgeSearchRepository(None, None, session=session)
