"""SQLite-backed implementation of the FTS5 knowledge search port (B6b)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence import lexical_query_treatment
from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.domain.relevance import KnowledgeKind

__all__ = [
    "SqliteKnowledgeSearchRepository",
    "build_sqlite_knowledge_search_repository",
    "sanitize_fts5_query",
]


def sanitize_fts5_query(query_text: str) -> str:
    """Turn free-form user text into a safe FTS5 ``MATCH`` argument.

    Diagnosed in issue #455: joining every raw token with ``OR`` —
    including Spanish function words (articles, prepositions, ...) — made
    almost any query
    match almost the entire canon (~45 elements de más per case on the
    47-case bank, 1/47 exact hits). ``query_text`` is instead run through
    ``lexical_query_treatment`` (ported from
    ``experiments/adr002/candidates/adr002_a/lexical.py``,
    ``evidence/adr001-spikes``, PR #117): folded, tokenized, stripped of
    ``VACIAS`` (Spanish stopwords) and expanded to each remaining term's
    morphological variants (root plus flexive forms). Only those variants
    are individually double-quoted (an FTS5 string literal, never
    interpreted as an operator) and joined with ``OR`` — so a hit still
    requires a discriminating term of the query, or one of its inflected
    forms, never a bare stopword. Column filters (``content:``), boolean
    keywords (``AND``/``NOT``/``NEAR``) and stray punctuation (``"``, ``*``,
    ``(``, a leading ``-``, ...) can therefore never reach FTS5's own query
    parser — a message with special characters can never break the query's
    syntax.

    A query with no significant term at all (blank, only punctuation, or
    only stopwords) returns an empty string. Callers must treat that as "no
    FTS5 match" and never execute a ``MATCH ''`` — FTS5 itself rejects an
    empty match expression as a syntax error.
    """
    terms = lexical_query_treatment.terminos_significativos(query_text)
    if not terms:
        return ""
    seen: set[str] = set()
    expanded: list[str] = []
    for term in terms:
        for variant in lexical_query_treatment.variantes(term):
            if variant not in seen:
                seen.add(variant)
                expanded.append(variant)
    return " OR ".join(f'"{variant}"' for variant in expanded)


class SqliteKnowledgeSearchRepository:
    """Read-only FTS5 search over ``knowledge_fts`` (B6a), backed by SQLite.

    Owns its ``session_factory`` and opens/commits/closes one short session
    per call, via ``session_scope``.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None,
        engine: Engine | None,
    ) -> None:
        self._session_factory = session_factory
        self._engine = engine

    def close(self) -> None:
        """Release every pooled connection this repository's engine holds."""
        if self._engine is not None:
            self._engine.dispose()

    @contextmanager
    def _scope(self) -> Iterator[Session]:
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
