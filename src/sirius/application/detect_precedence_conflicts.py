"""Read-only detection of unresolved subject-level precedence conflicts
(B4e, RF-026, PA-014, DR-011).

Mirrors ``GetMemoryOriginUseCase``/``GetDecisionOriginUseCase``: a small,
explicit, read-only contract so a future caller (B4f) never touches
``MemoryRepository``/``DecisionRepository`` or the pure domain rule in
``sirius.domain.precedence`` directly (AGENTS.md: dependency direction
presentation -> application -> domain).

This use case only ever reports; it never mutates a memory or a decision and
never picks a winner among conflicting items itself — resolving a reported
conflict (correcting, archiving, approving a decision, ...) always goes
through the existing, separate use cases that already require an explicit
order or confirmation (B4a-B4d). Nothing in ``SendMessageUseCase`` calls this
either, so an ordinary conversation never triggers, resolves, or is blocked
by conflict detection on its own.
"""

from __future__ import annotations

from sirius.domain.precedence import SubjectPrecedenceResult, find_subject_conflicts
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.memory_repository import MemoryRepository

__all__ = ["DetectPrecedenceConflictsUseCase"]


class DetectPrecedenceConflictsUseCase:
    """Reporta los asuntos vigentes sin precedencia inequívoca (RF-026, PA-014)."""

    def __init__(
        self, memory_repository: MemoryRepository, decision_repository: DecisionRepository
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository

    def detect(self) -> tuple[SubjectPrecedenceResult, ...]:
        """Return every current, explicit subject/project pairing whose
        precedence is not unambiguous — two or more current memories with no
        prevailing decision, or more than one approved decision for the same
        subject/project. Empty when every explicit subject either has no
        competing current item or a single, unambiguous decision prevails.
        """
        memories = self._memory_repository.list_current_memories()
        decisions = self._decision_repository.list_current_decisions()
        return find_subject_conflicts(memories, decisions)
