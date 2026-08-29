"""Explicit, manual category edit (D7 point 3, SIRIUS-ARQ-0.2 §6.1).

Unlike ``TagCategoryUseCase``, this write is never conditional: a category
the user sets or corrects always wins, whatever ``category_locked`` currently
is, and it always sets ``category_locked`` to ``True`` in the same call —
after which ``TagCategoryUseCase`` can never write over it again (the
condition lives entirely in
``MemoryRepository.set_category``/``DecisionRepository.set_category``'s
atomic statement, never a separate check here).
"""

from __future__ import annotations

from sirius.application.tag_category import CategoryTargetKind
from sirius.domain.decision import Decision
from sirius.domain.memory import Memory
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.memory_repository import MemoryRepository

__all__ = ["SetCategoryUseCase"]


class SetCategoryUseCase:
    """Fija, de forma incondicional, la categoría de un recuerdo o decisión (D7 punto 3)."""

    def __init__(
        self, memory_repository: MemoryRepository, decision_repository: DecisionRepository
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository

    def set(self, kind: CategoryTargetKind, item_id: int, category: str) -> Memory | Decision:
        """Write ``category`` and lock it, unconditionally."""
        if kind is CategoryTargetKind.MEMORY:
            return self._memory_repository.set_user_category(item_id, category)
        return self._decision_repository.set_user_category(item_id, category)
