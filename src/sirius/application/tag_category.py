"""Automatic, asynchronous category classification (D7, SIRIUS-ARQ-0.2 §6.1).

``TagCategoryUseCase`` is the use case ``CategoryTaggingWorker``
(``sirius.presentation``) calls off the GUI thread, after a save/confirm/
propose use case has already returned its result (D7 point 2): it reads the
element — recording, at that same instant and before calling
``CategoryClassifierPort.classify``, the version of the revision it is about
to classify —, invokes the classifier, and, if it returned a category, writes
it through the repository's single atomic conditional statement
(``MemoryRepository.set_category``/``DecisionRepository.set_category``): that
statement is what stops an in-flight classification from ever winning a race
against a user's correction (§6.1 point 3) or against a newer generation of
automatic tagging (§6.1 point 2) — never a check performed here in Python.

This use case never opens a ``UnitOfWork``: writing a plain classification
field is neither "event + memory" nor "event + decision" (SIRIUS-ARQ-0.1 S8.1,
§0.1 point 4 — the pairing ``UnitOfWork`` exists to guarantee), and running
the classifier's network call inside an open database transaction would hold
a connection for no reason.
"""

from __future__ import annotations

from enum import StrEnum

from sirius.domain.decision import Decision
from sirius.domain.memory import Memory
from sirius.ports.category_classifier import CategoryClassifierPort
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.memory_repository import MemoryRepository

__all__ = ["CategoryTargetKind", "TagCategoryUseCase"]


class CategoryTargetKind(StrEnum):
    """Which repository ``TagCategoryUseCase``/``SetCategoryUseCase`` target."""

    MEMORY = "memory"
    DECISION = "decision"


class TagCategoryUseCase:
    """Clasifica automáticamente un recuerdo o decisión y escribe el resultado (D7 punto 2)."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        decision_repository: DecisionRepository,
        classifier: CategoryClassifierPort,
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository
        self._classifier = classifier

    def tag(self, kind: CategoryTargetKind, item_id: int) -> bool:
        """Classify ``item_id`` and write the result if the classifier
        decided one. Returns ``True`` only if a category was actually
        written — ``False`` if the classifier could not decide, or if the
        conditional write found the element already locked or already on a
        newer revision. Never raises: the classifier never propagates an
        exception (``CategoryClassifierPort``), and a repository failure is
        an infrastructure problem this use case does not swallow.
        """
        if kind is CategoryTargetKind.MEMORY:
            memory = self._memory_repository.get_memory(item_id)
            category = self._classifier.classify(memory.current_revision.content or "")
            if category is None:
                return False
            return self._memory_repository.set_category(
                item_id,
                category,
                observed_revision_version=memory.current_revision.version,
            )

        decision = self._decision_repository.get_decision(item_id)
        category = self._classifier.classify(decision.current_revision.content)
        if category is None:
            return False
        return self._decision_repository.set_category(
            item_id,
            category,
            observed_revision_version=decision.current_revision.version,
        )

    def list_uncategorized_memories(self) -> list[Memory]:
        """Recuerdos sin categoría automática ni manual (§6.1 punto 4): los
        candidatos del pase retroactivo de arranque que encola un
        ``CategoryTaggingWorker`` por elemento, exactamente igual que tras un
        guardado o corrección."""
        return self._memory_repository.list_uncategorized()

    def list_uncategorized_decisions(self) -> list[Decision]:
        """Mirrors ``list_uncategorized_memories`` for decisions."""
        return self._decision_repository.list_uncategorized()
