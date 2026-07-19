"""Application-layer entry point for RF-026/PA-014: evaluating whether the
current memories and decisions on one subject/project boundary are settled,
governed by an approved decision, or in explicit conflict.

Read-only, like ``GetMemoryOriginUseCase``/``GetDecisionOriginUseCase``: it
takes repositories directly rather than a ``UnitOfWork``, since it never
writes anything. ``SendMessageUseCase`` never calls this — an ordinary
conversation never resolves a conflict, approves a decision or corrects a
memory by itself (PA-014's negative case mirrors PA-011's for decisions).
"""

from __future__ import annotations

from sirius.domain.knowledge_precedence import PrecedenceResolution, resolve_memory_precedence
from sirius.domain.memory import ensure_valid_subject_key
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.memory_repository import MemoryRepository

__all__ = ["EvaluateMemoryPrecedenceUseCase"]


class EvaluateMemoryPrecedenceUseCase:
    """Evaluates precedence/conflict for one subject/project boundary."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        decision_repository: DecisionRepository,
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository

    def evaluate(self, subject_key: str, project_id: int | None) -> PrecedenceResolution:
        """Compare every current memory and approved decision on
        ``subject_key``/``project_id`` (RF-026, DR-011).

        Raises ``ValueError`` if ``subject_key`` is empty after trimming,
        checked before either repository is queried.
        """
        ensure_valid_subject_key(subject_key)
        memories = self._memory_repository.list_current_memories()
        decisions = self._decision_repository.list_current_decisions()
        return resolve_memory_precedence(subject_key, project_id, memories, decisions)
