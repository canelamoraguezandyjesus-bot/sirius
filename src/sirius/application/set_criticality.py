"""Explicit, manual criticality edit (M18b, ADR-126).

Calcado de ``SetCategoryUseCase``: a diferencia de ella, no hay ningún
candado que fijar junto a la escritura — este encargo no introduce
clasificación automática de criticidad (eso es M21), así que no hay nada de
lo que proteger un valor manual. La escritura es siempre incondicional:
``None`` quita la marca.
"""

from __future__ import annotations

from enum import StrEnum

from sirius.domain.criticality import Criticality
from sirius.domain.decision import Decision
from sirius.domain.memory import Memory
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.memory_repository import MemoryRepository

__all__ = ["CriticalityTargetKind", "SetCriticalityUseCase"]


class CriticalityTargetKind(StrEnum):
    """Which repository ``SetCriticalityUseCase`` targets. Mirrors
    ``sirius.application.tag_category.CategoryTargetKind``."""

    MEMORY = "memory"
    DECISION = "decision"


class SetCriticalityUseCase:
    """Fija o quita, de forma incondicional, la criticidad de un recuerdo o
    decisión (M18b)."""

    def __init__(
        self, memory_repository: MemoryRepository, decision_repository: DecisionRepository
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository

    def set(
        self, kind: CriticalityTargetKind, item_id: int, criticality: Criticality | None
    ) -> Memory | Decision:
        """Write ``criticality`` unconditionally. ``None`` clears the mark."""
        if kind is CriticalityTargetKind.MEMORY:
            return self._memory_repository.set_user_criticality(item_id, criticality)
        return self._decision_repository.set_user_criticality(item_id, criticality)
