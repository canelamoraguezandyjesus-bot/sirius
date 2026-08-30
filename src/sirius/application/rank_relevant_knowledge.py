"""Read-only, checkable relevance ranking over vigente knowledge (B6b;
SIRIUS-ARQ-0.1 S7.5; D-11).

Combines the structured filters (proyecto activo, decisión vigente cuyo
asunto coincide) with a real FTS5 ``MATCH`` against ``knowledge_fts`` (B6a)
purely through ``sirius.domain.relevance.rank_relevant_knowledge``: this use
case only fetches the vigente candidates and the explicit booleans that
function needs per candidate (subject match, FTS5 hit), computed once here
so the pure domain function never has to know about a repository.

Read-only: never mutates a memory, a decision, or an index. Not called by
``SendMessageUseCase`` or ``ContextBuilder`` — connecting either to this
retrieval is budget/trim (B6c) and context assembly (B6d), not this cut.

M9 (SIRIUS-ARQ-0.2 §6.2, D7) adds ``category_match``, the fourth structural
signal, computed here exactly like the other three. It stays behind the D7
point 6 activation gate — ``category_matching_enabled``, ``False`` by
default — that §6.2/§6.3 and ``docs/evolution/STATUS.md`` fix: until the
owner registers the matching threshold there, the gate must stay closed, and
``category_match`` is inert for every real candidate (never computed from
``category``/``query_text`` at all, so it can never accidentally reorder
anything) — the safest fallback the design describes. Wiring the real
category vocabulary and flipping the gate from persisted settings is M11's
job (``composition_root``), not this one: both constructor parameters below
default to the closed state, so every existing caller keeps building the
exact same behaviour it has today.
"""

from __future__ import annotations

from sirius.domain.relevance import (
    KnowledgeKind,
    RankedKnowledge,
    category_matches_query,
    rank_relevant_knowledge,
    subject_matches_query,
)
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.knowledge_search_repository import KnowledgeSearchRepository
from sirius.ports.memory_repository import MemoryRepository
from sirius.ports.project_repository import ProjectRepository

__all__ = ["RankRelevantKnowledgeUseCase"]


class RankRelevantKnowledgeUseCase:
    """Ordena el conocimiento vigente relacionado con una consulta (S7.5)."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        decision_repository: DecisionRepository,
        project_repository: ProjectRepository,
        knowledge_search_repository: KnowledgeSearchRepository,
        *,
        category_vocabulary: frozenset[str] = frozenset(),
        category_matching_enabled: bool = False,
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository
        self._project_repository = project_repository
        self._knowledge_search_repository = knowledge_search_repository
        self._category_vocabulary = category_vocabulary
        self._category_matching_enabled = category_matching_enabled

    def rank(self, query_text: str) -> tuple[RankedKnowledge, ...]:
        """Return every vigente memory/decision related to ``query_text``,
        ordered by S7.5's explicit criteria tuple plus M9's category_match.

        A blank or all-punctuation ``query_text`` never raises: it simply
        matches nothing via FTS5, and any candidate that also has no
        matching subject is filtered out as "no relacionado" (see
        ``sirius.domain.relevance``) — an empty result, never an error.
        """
        active_project = self._project_repository.get_active_project()
        active_project_id = active_project.id if active_project is not None else None

        fts_hits = self._knowledge_search_repository.search_knowledge(query_text)

        def category_match(category: str | None) -> bool:
            # D7 point 6's activation gate (§6.2/§6.3): closed by default,
            # and closed until docs/evolution/STATUS.md registers the
            # matching threshold — category_match must stay False for every
            # real candidate while it is, never compared at all.
            return self._category_matching_enabled and category_matches_query(
                category, query_text, self._category_vocabulary
            )

        candidates: list[RankedKnowledge] = [
            RankedKnowledge(
                kind=KnowledgeKind.MEMORY,
                item=memory,
                subject_matches_query=False,
                project_matches_active=(
                    active_project_id is not None and memory.project_id == active_project_id
                ),
                fts_match=(KnowledgeKind.MEMORY, memory.id) in fts_hits,
                category_match=category_match(memory.category),
            )
            for memory in self._memory_repository.list_current_memories()
        ]
        candidates.extend(
            RankedKnowledge(
                kind=KnowledgeKind.DECISION,
                item=decision,
                subject_matches_query=subject_matches_query(decision.subject, query_text),
                project_matches_active=(
                    active_project_id is not None and decision.project_id == active_project_id
                ),
                fts_match=(KnowledgeKind.DECISION, decision.id) in fts_hits,
                category_match=category_match(decision.category),
            )
            for decision in self._decision_repository.list_current_decisions()
        )

        return rank_relevant_knowledge(candidates)
