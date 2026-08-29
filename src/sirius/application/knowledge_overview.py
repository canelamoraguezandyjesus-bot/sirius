"""Read-only overview of memories and decisions for the observable surface
(B4f, RF-019 a RF-026, PA-010 a PA-016).

Mirrors ``DetectPrecedenceConflictsUseCase``: a small, explicit, read-only
contract so the presentation layer never touches ``MemoryRepository`` or
``DecisionRepository`` directly (AGENTS.md: dependency direction
presentación -> aplicación -> dominio). This is the single query the B4f
panel needs to render every recuerdo and decisión "con su origen, estado y
versión" (origin is opened separately, per item, through
``GetMemoryOriginUseCase``/``GetDecisionOriginUseCase`` — this use case only
lists identity, status and version, never a full origin lookup for every
row).

Never mutates anything and is never called by ``SendMessageUseCase``: an
ordinary conversation neither creates nor requires this overview.
"""

from __future__ import annotations

from dataclasses import dataclass

from sirius.domain.decision import Decision
from sirius.domain.memory import Memory
from sirius.domain.memory_suggestion import MemorySuggestion
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.memory_repository import MemoryRepository
from sirius.ports.memory_suggestion_repository import MemorySuggestionRepository

__all__ = ["GetKnowledgeOverviewUseCase", "KnowledgeOverview"]


@dataclass(frozen=True, slots=True)
class KnowledgeOverview:
    """Presentation-ready snapshot of every memory/decision the panel shows.

    ``proposed_decisions`` (PROPOSED) are the candidates a caller can approve
    or use to supersede a current decision; ``current_decisions`` (APPROVED)
    are the candidates a caller can archive or supersede. Superseded
    decisions are deliberately not listed here: they carry no action the
    panel exposes (see ``sirius.domain.decision``'s module docstring —
    deletion never applies to decisions), and their supersession link is
    already reachable, when needed, through
    ``DecisionRepository.get_superseding_decision``.

    ``pending_suggestions`` (SIRIUS-ARQ-0.2 §3.6, M6) are PENDING
    ``MemorySuggestion``s a caller can confirm or reject; a confirmed or
    rejected suggestion is never listed here, mirroring how superseded
    decisions are excluded above.
    """

    current_memories: tuple[Memory, ...]
    archived_memories: tuple[Memory, ...]
    proposed_decisions: tuple[Decision, ...]
    current_decisions: tuple[Decision, ...]
    archived_decisions: tuple[Decision, ...]
    pending_suggestions: tuple[MemorySuggestion, ...]


class GetKnowledgeOverviewUseCase:
    """Reúne los recuerdos, decisiones y sugerencias observables en una sola consulta."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        decision_repository: DecisionRepository,
        memory_suggestion_repository: MemorySuggestionRepository,
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository
        self._memory_suggestion_repository = memory_suggestion_repository

    def get_overview(self) -> KnowledgeOverview:
        """Return every memory/decision/suggestion the observable surface must render."""
        return KnowledgeOverview(
            current_memories=tuple(self._memory_repository.list_current_memories()),
            archived_memories=tuple(self._memory_repository.list_archived_memories()),
            proposed_decisions=tuple(self._decision_repository.list_proposed_decisions()),
            current_decisions=tuple(self._decision_repository.list_current_decisions()),
            archived_decisions=tuple(self._decision_repository.list_archived_decisions()),
            pending_suggestions=tuple(
                self._memory_suggestion_repository.list_pending_suggestions()
            ),
        )
