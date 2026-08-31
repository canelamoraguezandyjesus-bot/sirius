"""Unit tests for ``TagCategoryUseCase`` (D7 punto 2, SIRIUS-ARQ-0.2 §6.1).

Every repository here is a minimal, hand-rolled fake — no SQLite involved
(the atomic conditional write itself is covered at the repository level, see
``tests/integration/test_category_tagging.py``). These tests pin what
``TagCategoryUseCase`` itself is responsible for: reading the item and its
current revision version *before* classifying, calling the classifier
exactly once, writing only when it returned a category, and returning
whether the write actually happened.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from sirius.application.tag_category import CategoryTargetKind, TagCategoryUseCase
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus


def _memory(*, memory_id: int = 1, version: int = 1, content: str = "contenido") -> Memory:
    now = datetime.now(UTC)
    revision = MemoryRevision(
        id=version,
        memory_id=memory_id,
        version=version,
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
    )


def _decision(*, decision_id: int = 1, version: int = 1, content: str = "contenido") -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=version,
        decision_id=decision_id,
        version=version,
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
    )


class _FakeMemoryRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, memory: Memory, *, set_category_result: bool = True) -> None:
        self._memory = memory
        self.set_category_result = set_category_result
        self.set_category_calls: list[tuple[int, str, int]] = []

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        raise AssertionError("tag() must never create a memory")

    def get_memory(self, memory_id: int) -> Memory:
        assert memory_id == self._memory.id
        return self._memory

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("tag() must never list memories")

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError("tag() must never list memories")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("tag() must never list archived memories")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("tag() must never read history")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("tag() must never correct a memory")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("tag() must never archive a memory")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("tag() must never delete a memory")

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        self.set_category_calls.append((memory_id, category, observed_revision_version))
        return self.set_category_result

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError("tag() must never set a user category")

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError("tag() must never list uncategorized memories")


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
        raise AssertionError("tag() must never touch a memory when kind is DECISION")

    def get_memory(self, memory_id: int) -> Memory:
        raise AssertionError("tag() must never read a memory when kind is DECISION")

    def list_current_memories(self) -> list[Memory]:
        raise AssertionError("tag() must never touch a memory when kind is DECISION")

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        raise AssertionError("tag() must never touch a memory when kind is DECISION")

    def list_archived_memories(self) -> list[Memory]:
        raise AssertionError("tag() must never touch a memory when kind is DECISION")

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        raise AssertionError("tag() must never touch a memory when kind is DECISION")

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        raise AssertionError("tag() must never touch a memory when kind is DECISION")

    def archive_memory(self, memory_id: int) -> Memory:
        raise AssertionError("tag() must never touch a memory when kind is DECISION")

    def delete_memory(self, memory_id: int) -> Memory:
        raise AssertionError("tag() must never touch a memory when kind is DECISION")

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("tag() must never write a memory when kind is DECISION")

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        raise AssertionError("tag() must never touch a memory when kind is DECISION")

    def list_uncategorized(self) -> list[Memory]:
        raise AssertionError("tag() must never touch a memory when kind is DECISION")


class _FakeDecisionRepository:
    """Minimal Protocol-compliant fake; no SQLite involved."""

    def __init__(self, decision: Decision, *, set_category_result: bool = True) -> None:
        self._decision = decision
        self.set_category_result = set_category_result
        self.set_category_calls: list[tuple[int, str, int]] = []

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("tag() must never create a decision proposal")

    def get_decision(self, decision_id: int) -> Decision:
        assert decision_id == self._decision.id
        return self._decision

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("tag() must never approve a decision")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("tag() must never supersede a decision")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("tag() must never list decisions")

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        raise AssertionError("tag() must never list decisions")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("tag() must never list proposed decisions")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("tag() must never archive a decision")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("tag() must never list archived decisions")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("tag() must never read a superseding decision")

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        self.set_category_calls.append((decision_id, category, observed_revision_version))
        return self.set_category_result

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError("tag() must never set a user category")

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError("tag() must never list uncategorized decisions")


class _UnusedDecisionRepository:
    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def get_decision(self, decision_id: int) -> Decision:
        raise AssertionError("tag() must never read a decision when kind is MEMORY")

    def approve_decision(self, decision_id: int) -> Decision:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def list_current_decisions(self) -> list[Decision]:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def list_proposed_decisions(self) -> list[Decision]:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def archive_decision(self, decision_id: int) -> Decision:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def list_archived_decisions(self) -> list[Decision]:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        raise AssertionError("tag() must never write a decision when kind is MEMORY")

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")

    def list_uncategorized(self) -> list[Decision]:
        raise AssertionError("tag() must never touch a decision when kind is MEMORY")


class _FakeClassifier:
    def __init__(self, result: str | None) -> None:
        self.result = result
        self.classified_content: list[str] = []

    def classify(self, content: str) -> str | None:
        self.classified_content.append(content)
        return self.result


def test_tag_writes_the_classified_category_for_a_memory() -> None:
    memory = _memory(memory_id=7, version=3, content="recuerda comprar leche")
    memory_repository = _FakeMemoryRepository(memory)
    classifier = _FakeClassifier("trabajo")
    use_case = TagCategoryUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    wrote = use_case.tag(CategoryTargetKind.MEMORY, 7)

    assert wrote is True
    assert classifier.classified_content == ["recuerda comprar leche"]
    assert memory_repository.set_category_calls == [(7, "trabajo", 3)]


def test_tag_writes_nothing_when_the_classifier_is_unavailable() -> None:
    """Ollama no instalado, conexión rechazada o tiempo agotado: el
    adaptador ya normaliza cualquiera de esos casos a ``None``."""
    memory = _memory()
    memory_repository = _FakeMemoryRepository(memory)
    classifier = _FakeClassifier(None)
    use_case = TagCategoryUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    wrote = use_case.tag(CategoryTargetKind.MEMORY, 1)

    assert wrote is False
    assert memory_repository.set_category_calls == []


def test_tag_writes_nothing_when_the_classifier_response_is_outside_the_vocabulary() -> None:
    """Una respuesta fuera del vocabulario cerrado se trata exactamente
    igual que ``None`` (D7 §6.1 punto 2): el adaptador ya la normaliza antes
    de que ``classify`` devuelva nada."""
    memory = _memory()
    memory_repository = _FakeMemoryRepository(memory)
    classifier = _FakeClassifier(None)
    use_case = TagCategoryUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    wrote = use_case.tag(CategoryTargetKind.MEMORY, 1)

    assert wrote is False
    assert memory_repository.set_category_calls == []


def test_tag_returns_false_when_the_conditional_write_did_not_happen() -> None:
    """El clasificador decidió una categoría, pero la escritura condicional
    del repositorio no encontró fila que actualizar (ya bloqueada, o
    revisión ya superada) — tag() lo refleja fielmente, nunca lo esconde."""
    memory = _memory()
    memory_repository = _FakeMemoryRepository(memory, set_category_result=False)
    classifier = _FakeClassifier("personal")
    use_case = TagCategoryUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    wrote = use_case.tag(CategoryTargetKind.MEMORY, 1)

    assert wrote is False
    assert memory_repository.set_category_calls == [(1, "personal", 1)]


def test_tag_reads_the_revision_version_before_writing_a_decision() -> None:
    decision = _decision(decision_id=9, version=4, content="usar SQLite local")
    decision_repository = _FakeDecisionRepository(decision)
    classifier = _FakeClassifier("proyecto")
    use_case = TagCategoryUseCase(_UnusedMemoryRepository(), decision_repository, classifier)

    wrote = use_case.tag(CategoryTargetKind.DECISION, 9)

    assert wrote is True
    assert classifier.classified_content == ["usar SQLite local"]
    assert decision_repository.set_category_calls == [(9, "proyecto", 4)]


def test_tag_writes_nothing_for_a_decision_when_the_classifier_is_unavailable() -> None:
    decision = _decision()
    decision_repository = _FakeDecisionRepository(decision)
    classifier = _FakeClassifier(None)
    use_case = TagCategoryUseCase(_UnusedMemoryRepository(), decision_repository, classifier)

    wrote = use_case.tag(CategoryTargetKind.DECISION, 1)

    assert wrote is False
    assert decision_repository.set_category_calls == []


@pytest.mark.parametrize("deleted_content", [None])
def test_tag_classifies_an_empty_string_when_a_deleted_memory_has_no_content(
    deleted_content: str | None,
) -> None:
    """A deleted memory's current revision content is ``None``
    (``sirius.domain.memory``); ``classify`` must never receive ``None``."""
    memory = _memory()
    revision = MemoryRevision(
        id=1,
        memory_id=memory.id,
        version=1,
        content=deleted_content,
        origin=memory.current_revision.origin,
        source_event_id=None,
        created_at=memory.created_at,
    )
    deleted_memory = Memory(
        id=memory.id,
        status=MemoryStatus.DELETED,
        current_revision=revision,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )
    memory_repository = _FakeMemoryRepository(deleted_memory)
    classifier = _FakeClassifier(None)
    use_case = TagCategoryUseCase(memory_repository, _UnusedDecisionRepository(), classifier)

    use_case.tag(CategoryTargetKind.MEMORY, deleted_memory.id)

    assert classifier.classified_content == [""]
