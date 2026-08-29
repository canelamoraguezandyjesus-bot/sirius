"""Integration tests for D7's category writes (SIRIUS-ARQ-0.2 §6.1/§8-M8).

Two race conditions the atomic conditional statement
(``MemoryRepository.set_category``/``DecisionRepository.set_category``)
exists to close, reproduced deterministically against a real SQLite database
— never with real Ollama, never with real threads: the "pause" the
architecture describes is simply not calling ``set_category`` until after
the competing write has already committed, which is exactly what a paused
worker's late write looks like once it finally runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.set_category import SetCategoryUseCase
from sirius.application.tag_category import CategoryTargetKind, TagCategoryUseCase
from sirius.domain.event import DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


def _project_id(database_path: Path) -> int:
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="en curso",
        blockers=(),
        next_step="siguiente paso",
    )
    return project.id


class _FakeClassifier:
    """A ``CategoryClassifierPort`` double: one canned answer, never Ollama."""

    def __init__(self, result: str | None) -> None:
        self._result = result

    def classify(self, content: str) -> str | None:
        return self._result


@pytest.mark.integration
def test_set_category_writes_when_unlocked_and_the_revision_still_matches(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repository = build_sqlite_memory_repository(database_path)
    memory = repository.create_memory("contenido original", "manual")

    wrote = repository.set_category(
        memory.id, "trabajo", observed_revision_version=memory.current_revision.version
    )

    assert wrote is True
    assert repository.get_memory(memory.id).category == "trabajo"
    assert repository.get_memory(memory.id).category_locked is False


@pytest.mark.integration
def test_set_category_loses_the_race_to_a_user_correction(tmp_path: Path) -> None:
    """§8-M8 criterio de aceptación: pausar TagCategoryUseCase justo después
    de invocar classify() y antes de su intento de escritura, ejecutar
    SetCategoryUseCase.set() con una categoría distinta, y solo entonces
    dejar que TagCategoryUseCase continúe — la categoría final es la del
    usuario, nunca la de Ollama."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repository = build_sqlite_memory_repository(database_path)
    memory = repository.create_memory("contenido original", "manual")
    observed_version = memory.current_revision.version  # classify() already ran on this revision

    # The user corrects the category while the automatic write is "paused".
    repository.set_user_category(memory.id, "personal")

    # The paused automatic write finally runs, with a different category.
    wrote = repository.set_category(
        memory.id, "trabajo", observed_revision_version=observed_version
    )

    assert wrote is False
    final = repository.get_memory(memory.id)
    assert final.category == "personal"
    assert final.category_locked is True


@pytest.mark.integration
def test_set_category_loses_the_race_to_a_newer_generation_of_automatic_tagging(
    tmp_path: Path,
) -> None:
    """§8-M8 criterio de aceptación: sobre una memoria en revisión 1, un
    primer TagCategoryUseCase se pausa justo después de classify(); la
    memoria se corrige (revisión 2); un segundo TagCategoryUseCase clasifica
    y escribe sobre la revisión 2; solo entonces el primero intenta su
    escritura tardía — que no encuentra fila que actualizar porque la
    revisión vigente ya no es la 1."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repository = build_sqlite_memory_repository(database_path)
    memory = repository.create_memory("contenido original", "manual")
    first_generation_version = memory.current_revision.version  # 1

    corrected = repository.correct_memory(memory.id, "contenido corregido", "manual")
    assert corrected.current_revision.version == 2
    assert corrected.category is None  # cleared by the correction (D7, §6.1)

    second_generation_wrote = repository.set_category(
        memory.id, "trabajo", observed_revision_version=corrected.current_revision.version
    )
    assert second_generation_wrote is True

    first_generation_wrote = repository.set_category(
        memory.id, "personal", observed_revision_version=first_generation_version
    )

    assert first_generation_wrote is False
    final = repository.get_memory(memory.id)
    assert final.category == "trabajo"
    assert final.category_locked is False


@pytest.mark.integration
def test_a_user_locked_category_survives_a_later_automatic_tag_attempt(tmp_path: Path) -> None:
    """Prueba de dominio (§8-M8): category_locked se fija al establecer una
    categoría manual, y ninguna llamada posterior de TagCategoryUseCase lo
    sobrescribe — incluida una que llega después, simulando una respuesta de
    Ollama en vuelo con una categoría distinta a la del usuario."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    memory = memory_repository.create_memory("contenido original", "manual")

    set_category_use_case = SetCategoryUseCase(memory_repository, decision_repository)
    locked = set_category_use_case.set(CategoryTargetKind.MEMORY, memory.id, "personal")
    assert locked.category == "personal"
    assert locked.category_locked is True

    # An automatic classification that started before the user's edit (or
    # simply runs later) still tries to write, with a different category.
    tag_category_use_case = TagCategoryUseCase(
        memory_repository, decision_repository, _FakeClassifier("trabajo")
    )
    tagged = tag_category_use_case.tag(CategoryTargetKind.MEMORY, memory.id)

    assert tagged is False
    final = memory_repository.get_memory(memory.id)
    assert final.category == "personal"
    assert final.category_locked is True


@pytest.mark.integration
def test_list_uncategorized_excludes_tagged_and_locked_memories(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repository = build_sqlite_memory_repository(database_path)

    never_categorized = repository.create_memory("sin categoría todavía", "manual")
    auto_tagged = repository.create_memory("ya clasificada", "manual")
    repository.set_category(
        auto_tagged.id, "trabajo", observed_revision_version=auto_tagged.current_revision.version
    )
    user_locked = repository.create_memory("bloqueada por el usuario", "manual")
    repository.set_user_category(user_locked.id, "personal")

    uncategorized = repository.list_uncategorized()

    assert [memory.id for memory in uncategorized] == [never_categorized.id]


@pytest.mark.integration
def test_decision_set_category_loses_the_race_to_a_user_correction(tmp_path: Path) -> None:
    """Mirrors the memory race test for ``DecisionRepository``."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project_id = _project_id(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    event = event_repository.append(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)
    decision = decision_repository.create_proposal(
        "asunto", project_id, "usar SQLite local", source_event_id=event.id
    )
    observed_version = decision.current_revision.version

    decision_repository.set_user_category(decision.id, "proyecto")
    wrote = decision_repository.set_category(
        decision.id, "otros", observed_revision_version=observed_version
    )

    assert wrote is False
    final = decision_repository.get_decision(decision.id)
    assert final.category == "proyecto"
    assert final.category_locked is True


@pytest.mark.integration
def test_list_uncategorized_excludes_tagged_and_locked_decisions(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project_id = _project_id(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)

    def _propose(content: str) -> int:
        event = event_repository.append(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)
        return decision_repository.create_proposal(
            "asunto", project_id, content, source_event_id=event.id
        ).id

    never_categorized_id = _propose("sin categoría todavía")
    auto_tagged = decision_repository.create_proposal(
        "asunto",
        project_id,
        "ya clasificada",
        source_event_id=event_repository.append(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, None).id,
    )
    decision_repository.set_category(
        auto_tagged.id, "proyecto", observed_revision_version=auto_tagged.current_revision.version
    )
    locked_id = _propose("bloqueada")
    decision_repository.set_user_category(locked_id, "otros")

    uncategorized = decision_repository.list_uncategorized()

    assert [decision.id for decision in uncategorized] == [never_categorized_id]
