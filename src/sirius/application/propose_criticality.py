"""Automatic criticality proposal, without writing it (M21a, ADR-130).

Sirius propone, el usuario decide (M18b, ADR-126): ``ProposeCriticalityUseCase``
lee un recuerdo o decisión y devuelve lo que ``CriticalityClassifierPort``
propone para su contenido vigente — nunca escribe nada. La única escritura de
``criticality`` sigue siendo, exclusivamente, ``SetCriticalityUseCase``, y es
siempre manual e incondicional. A diferencia de ``TagCategoryUseCase``, este
caso de uso no tiene un candado que respetar ni una escritura condicional que
hacer: no hay ningún camino de código, aquí, por el que una propuesta pueda
llegar a persistirse.

Si el elemento ya tiene ``criticality`` marcada, esta clase devuelve ``None``
*sin* invocar al clasificador: lo que el usuario ya decidió no se vuelve a
proponer, y no tiene sentido pagar una llamada de red por una propuesta que
nunca se mostraría.

This use case never opens a ``UnitOfWork``: no hay escritura que emparejar
con un evento (SIRIUS-ARQ-0.1 §8.1, §0.1 punto 4), y ejecutar la llamada de
red del clasificador dentro de una transacción abierta retendría una conexión
sin motivo — el mismo razonamiento que ``TagCategoryUseCase``.
"""

from __future__ import annotations

from enum import StrEnum

from sirius.domain.criticality import Criticality
from sirius.ports.criticality_classifier import CriticalityClassifierPort
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.memory_repository import MemoryRepository

__all__ = ["CriticalityProposalTargetKind", "ProposeCriticalityUseCase"]


class CriticalityProposalTargetKind(StrEnum):
    """Which repository ``ProposeCriticalityUseCase`` targets. Mirrors
    ``sirius.application.tag_category.CategoryTargetKind``."""

    MEMORY = "memory"
    DECISION = "decision"


class ProposeCriticalityUseCase:
    """Propone, sin escribir, la criticidad de un recuerdo o decisión (M21a)."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        decision_repository: DecisionRepository,
        classifier: CriticalityClassifierPort,
    ) -> None:
        self._memory_repository = memory_repository
        self._decision_repository = decision_repository
        self._classifier = classifier

    def propose(self, kind: CriticalityProposalTargetKind, item_id: int) -> Criticality | None:
        """Return the proposed ``Criticality`` for ``item_id``, or ``None``.

        ``None`` covers two different cases, and this method never
        distinguishes them for the caller (neither is "an escalation the
        user should see"): the element already has a ``criticality`` the
        user set (the classifier is never even called), or the classifier
        itself could not decide. Never writes anything, and never raises:
        the classifier never propagates an exception
        (``CriticalityClassifierPort``), and a repository failure is an
        infrastructure problem this use case does not swallow.
        """
        if kind is CriticalityProposalTargetKind.MEMORY:
            memory = self._memory_repository.get_memory(item_id)
            if memory.criticality is not None:
                return None
            return self._classifier.propose(memory.current_revision.content or "")

        decision = self._decision_repository.get_decision(item_id)
        if decision.criticality is not None:
            return None
        return self._classifier.propose(decision.current_revision.content)
