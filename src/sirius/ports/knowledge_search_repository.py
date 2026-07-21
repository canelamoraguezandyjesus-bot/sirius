"""Read-only contract for FTS5 knowledge search (B6b), independent of
SQLAlchemy.

The only read B6b needs against ``knowledge_fts`` (B6a's search substrate):
every ``(kind, item_id)`` pair whose indexed content matches a query text.
"""

from __future__ import annotations

from typing import Protocol

from sirius.domain.relevance import KnowledgeKind


class KnowledgeSearchRepository(Protocol):
    """Contract implemented by real and simulated FTS5 knowledge search.

    Implementations must sanitize ``query_text`` themselves so a message
    with special characters never raises an FTS5 syntax error — a blank or
    all-punctuation query returns an empty result instead of ever executing
    a ``MATCH`` against the index.
    """

    def search_knowledge(self, query_text: str) -> frozenset[tuple[KnowledgeKind, int]]:
        """Return every ``(kind, item_id)`` pair whose indexed content
        matches ``query_text`` via a real FTS5 ``MATCH``.

        Deliberately unfiltered by status: ``knowledge_fts`` indexes an
        archived memory's content just as faithfully as a current one
        (B6a) — excluding non-vigente items is
        ``sirius.domain.relevance.rank_relevant_knowledge``'s job, not this
        repository's.
        """
        ...
