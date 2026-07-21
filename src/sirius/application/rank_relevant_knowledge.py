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
"""

from __future__ import annotations

from sirius.domain.relevance import (
    KnowledgeKind,
    RankedKnowledge,
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
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository
        self._project_repository = project_repository
        self._knowledge_search_repository = knowledge_search_repository

    def rank(self, query_text: str) -> tuple[RankedKnowledge, ...]:
        """Return every vigente memory/decision related to ``query_text``,
        ordered by S7.5's explicit criteria tuple.

        A blank or all-punctuation ``query_text`` never raises: it simply
        matches nothing via FTS5, and any candidate that also has no
        matching subject is filtered out as "no relacionado" (see
        ``sirius.domain.relevance``) — an empty result, never an error.
        """
        active_project = self._project_repository.get_active_project()
        active_project_id = active_project.id if active_project is not None else None

        fts_hits = self._knowledge_search_repository.search_knowledge(query_text)

        candidates: list[RankedKnowledge] = [
            RankedKnowledge(
                kind=KnowledgeKind.MEMORY,
                item=memory,
                subject_matches_query=False,
                project_matches_active=(
                    active_project_id is not None and memory.project_id == active_project_id
                ),
                fts_match=(KnowledgeKind.MEMORY, memory.id) in fts_hits,
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
            )
            for decision in self._decision_repository.list_current_decisions()
        )

        return rank_relevant_knowledge(candidates)
