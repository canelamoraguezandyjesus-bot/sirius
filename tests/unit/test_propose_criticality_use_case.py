"""Unit tests for ``ProposeCriticalityUseCase`` (M21a, ADR-130).

Calcado de ``test_tag_category_use_case.py`` en su estilo de dobles, pero
para un caso de uso que nunca escribe (regla «Sirius propone, el usuario
decide», M18b/ADR-126): cada repositorio fake hace saltar ``AssertionError``
en cualquier método de escritura (``set_user_criticality``, ``create_*``,
``correct_*``, ``archive_*``, ``delete_*``, ``approve_*``,
``supersede_*``, ``set_category``, ``set_user_category``), de modo que una
regresión que empezara a escribir haría fallar la prueba inmediatamente, no
solo dejaría pasar una aserción vacía.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sirius.application.propose_criticality import (
    CriticalityProposalTargetKind,
    ProposeCriticalityUseCase,
)
from sirius.domain.criticality import Criticality
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus

_WRITE_MESSAGE = "propose() must never write anything"


def _memory(
    *, memory_id: int = 1, content: str = "contenido", criticality: Criticality | None = None
) -> Memory:
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=1,
        memory_id=memory_id,
        version=1,
        content=content,
        origin="Guardado manual del usuario",
        source_event_id=None,
        created_at=now,
    )
    return Memory(
        id=memory_id,
        status=MemoryStatus.CURRENT,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        criticality=criticality,
    )


def _decision(
    *, decision_id: int = 1, content: str = "contenido", criticality: Criticality | None = None
) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=1,
        decision_id=decision_id,
        version=1,
        content=content,
        source_event_id=None,
        created_at=now,
    )
    return Decision(
        id=decision_id,
        subject="asunto",
        project_id=1,
        status=DecisionStatus.APPROVED,
        current_revision=revision,
        created_at=now,
        updated_at=now,
        criticality=criticality,
    )


class _FakeMemoryRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, memory: Memory) -> None:
        self._memory = memory

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError(_WRITE_MESSAGE)

    def get_memory(self, memory_id: int) -> Memory:
        assert memory_id == self._memory.id
        return self._memory

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("propose() must never list memories")

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError("propose() must never list memories")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("propose() must never list archived memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("propose() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError(_WRITE_MESSAGE)

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError(_WRITE_MESSAGE)

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError(_WRITE_MESSAGE)

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError(_WRITE_MESSAGE)

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError(_WRITE_MESSAGE)

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError("propose() must never list uncategorized memories")

    def set_user_criticality(self, memory_id: int, criticality: Criticality | None) -> Memory:
        raise AssertionError(_WRITE_MESSAGE)

    def list_current_memories_by_criticality(self, levels: Sequence[Criticality]) -> list[Memory]:
        raise AssertionError("propose() must never list memories by criticality")


class _UnusedMemoryRepository:
    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("propose() must never read a memory when kind is DECISION")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def set_user_criticality(self, memory_id: int, criticality: Criticality | None) -> Memory:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")

    def list_current_memories_by_criticality(self, levels: Sequence[Criticality]) -> list[Memory]:
        raise AssertionError("propose() must never touch a memory when kind is DECISION")


class _FakeDecisionRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, decision: Decision) -> None:
        self._decision = decision

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError(_WRITE_MESSAGE)

    def get_decision(self, decision_id: int) -> Decision:
        assert decision_id == self._decision.id
        return self._decision

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError(_WRITE_MESSAGE)

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError(_WRITE_MESSAGE)

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("propose() must never list decisions")

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        raise AssertionError("propose() must never list decisions")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("propose() must never list proposed decisions")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError(_WRITE_MESSAGE)

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("propose() must never list archived decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("propose() must never read a superseding decision")

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError(_WRITE_MESSAGE)

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError(_WRITE_MESSAGE)

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError("propose() must never list uncategorized decisions")

    def set_user_criticality(self, decision_id: int, criticality: Criticality | None) -> Decision:
        raise AssertionError(_WRITE_MESSAGE)

    def list_current_decisions_by_criticality(
        self, levels: Sequence[Criticality]
    ) -> list[Decision]:
        raise AssertionError("propose() must never list decisions by criticality")


class _UnusedDecisionRepository:
    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("propose() must never read a decision when kind is MEMORY")

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def set_user_criticality(self, decision_id: int, criticality: Criticality | None) -> Decision:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")

    def list_current_decisions_by_criticality(
        self, levels: Sequence[Criticality]
    ) -> list[Decision]:
        raise AssertionError("propose() must never touch a decision when kind is MEMORY")


class _FakeClassifier:
    def __init__(self, result: Criticality | None) -> None:
        self.result = result
        self.proposed_content: list[str] = []

    def propose(self, content: str) -> Criticality | None:
        self.proposed_content.append(content)
        return self.result


def test_propose_returns_the_classifiers_proposal_for_an_unmarked_memory() -> None:
    memory = _memory(memory_id=7, content="no volver a exponer la clave en texto plano")
    memory_repository = _FakeMemoryRepository(memory)
    classifier = _FakeClassifier(Criticality.CRITICO)
    use_case = ProposeCriticalityUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    proposal = use_case.propose(CriticalityProposalTargetKind.MEMORY, 7)

    assert proposal is Criticality.CRITICO
    assert classifier.proposed_content == ["no volver a exponer la clave en texto plano"]


def test_propose_skips_the_classifier_for_an_already_marked_memory() -> None:
    """Lo que el usuario ya decidió no se vuelve a proponer (M21a): el
    clasificador ni siquiera se invoca. Mutación sugerida por el ADR: si se
    quita la comprobación "ya marcada", esta aserción sobre
    ``proposed_content`` empieza a fallar porque el doble sí registra una
    llamada."""
    memory = _memory(criticality=Criticality.IMPORTANTE)
    memory_repository = _FakeMemoryRepository(memory)
    classifier = _FakeClassifier(Criticality.CRITICO)
    use_case = ProposeCriticalityUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    proposal = use_case.propose(CriticalityProposalTargetKind.MEMORY, 1)

    assert proposal is None
    assert classifier.proposed_content == []


def test_propose_returns_none_for_a_memory_when_the_classifier_cannot_decide() -> None:
    memory = _memory()
    memory_repository = _FakeMemoryRepository(memory)
    classifier = _FakeClassifier(None)
    use_case = ProposeCriticalityUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    proposal = use_case.propose(CriticalityProposalTargetKind.MEMORY, 1)

    assert proposal is None
    assert classifier.proposed_content == ["contenido"]


def test_propose_never_writes_a_memory_criticality() -> None:
    """``_FakeMemoryRepository.set_user_criticality`` haría saltar
    ``AssertionError`` si ``propose()`` lo llamara; que la llamada termine
    limpiamente ya confirma que no lo hizo. Comprueba además que el elemento
    sigue con la misma ``criticality`` después de la llamada."""
    memory = _memory(criticality=None)
    memory_repository = _FakeMemoryRepository(memory)
    classifier = _FakeClassifier(Criticality.CRITICO)
    use_case = ProposeCriticalityUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    use_case.propose(CriticalityProposalTargetKind.MEMORY, 1)

    assert memory_repository.get_memory(1).criticality is None


def test_propose_classifies_an_empty_string_when_a_deleted_memory_has_no_content() -> None:
    """A deleted memory's current revision content is ``None``
    (``sirius.domain.memory``); ``propose`` must never receive ``None``."""
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=1,
        memory_id=1,
        version=1,
        content=None,
        origin="Guardado manual del usuario",
        source_event_id=None,
        created_at=now,
    )
    deleted_memory = Memory(
        id=1, status=MemoryStatus.DELETED, current_revision=revision, created_at=now, updated_at=now
    )
    memory_repository = _FakeMemoryRepository(deleted_memory)
    classifier = _FakeClassifier(None)
    use_case = ProposeCriticalityUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    use_case.propose(CriticalityProposalTargetKind.MEMORY, 1)

    assert classifier.proposed_content == [""]


def test_propose_returns_the_classifiers_proposal_for_an_unmarked_decision() -> None:
    decision = _decision(decision_id=9, content="usar SQLite local")
    decision_repository = _FakeDecisionRepository(decision)
    classifier = _FakeClassifier(Criticality.IMPORTANTE)
    use_case = ProposeCriticalityUseCase(_UnusedMemoryRepository(), decision_repository, classifier)

    proposal = use_case.propose(CriticalityProposalTargetKind.DECISION, 9)

    assert proposal is Criticality.IMPORTANTE
    assert classifier.proposed_content == ["usar SQLite local"]


def test_propose_skips_the_classifier_for_an_already_marked_decision() -> None:
    decision = _decision(criticality=Criticality.CRITICO)
    decision_repository = _FakeDecisionRepository(decision)
    classifier = _FakeClassifier(Criticality.IMPORTANTE)
    use_case = ProposeCriticalityUseCase(_UnusedMemoryRepository(), decision_repository, classifier)

    proposal = use_case.propose(CriticalityProposalTargetKind.DECISION, 1)

    assert proposal is None
    assert classifier.proposed_content == []


def test_propose_never_writes_a_decision_criticality() -> None:
    decision = _decision(criticality=None)
    decision_repository = _FakeDecisionRepository(decision)
    classifier = _FakeClassifier(Criticality.CRITICO)
    use_case = ProposeCriticalityUseCase(_UnusedMemoryRepository(), decision_repository, classifier)

    use_case.propose(CriticalityProposalTargetKind.DECISION, 1)

    assert decision_repository.get_decision(1).criticality is None
