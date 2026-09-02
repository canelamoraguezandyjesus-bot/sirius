"""Integration tests for the criticality signal (M18b, ADR-126).

Calcado de ``test_category_tagging.py``, sin la parte de escritura
condicional/candado: ``criticality`` no tiene análogo de
``category_locked`` ni de ``set_category`` — este encargo no introduce
clasificación automática, así que ``set_user_criticality`` siempre escribe
sin condición alguna.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.domain.criticality import Criticality
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


@pytest.mark.integration
def test_memory_criticality_defaults_to_none(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repository = build_sqlite_memory_repository(database_path)

    memory = repository.create_memory("contenido", "manual")

    assert memory.criticality is None
    assert repository.get_memory(memory.id).criticality is None


@pytest.mark.integration
def test_set_user_criticality_round_trips_through_sqlite_for_memories(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repository = build_sqlite_memory_repository(database_path)
    memory = repository.create_memory("contenido", "manual")

    updated = repository.set_user_criticality(memory.id, Criticality.CRITICO)

    assert updated.criticality is Criticality.CRITICO
    assert repository.get_memory(memory.id).criticality is Criticality.CRITICO


@pytest.mark.integration
def test_set_user_criticality_with_none_clears_the_mark_for_memories(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repository = build_sqlite_memory_repository(database_path)
    memory = repository.create_memory("contenido", "manual")
    repository.set_user_criticality(memory.id, Criticality.IMPORTANTE)

    cleared = repository.set_user_criticality(memory.id, None)

    assert cleared.criticality is None
    assert repository.get_memory(memory.id).criticality is None


@pytest.mark.integration
def test_decision_criticality_round_trips_through_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project_id = _project_id(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    event = event_repository.append(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)
    decision = decision_repository.create_proposal(
        "asunto", project_id, "contenido", source_event_id=event.id
    )
    assert decision.criticality is None

    updated = decision_repository.set_user_criticality(decision.id, Criticality.CRITICO)
    assert updated.criticality is Criticality.CRITICO

    cleared = decision_repository.set_user_criticality(decision.id, None)
    assert cleared.criticality is None
    assert decision_repository.get_decision(decision.id).criticality is None


@pytest.mark.integration
def test_unknown_criticality_value_in_database_fails_clearly_for_memories(
    tmp_path: Path,
) -> None:
    """M18b (ADR-126, nota de arranque punto 4): un valor corrupto o
    desconocido nunca se convierte en silencio en un ``Criticality``
    inventado ni en ``None`` — falla claro al cargar."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repository = build_sqlite_memory_repository(database_path)
    memory = repository.create_memory("contenido", "manual")

    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE memories SET criticality = :value WHERE id = :id"),
            {"value": "URGENTISIMO", "id": memory.id},
        )

    with pytest.raises(ValueError, match="URGENTISIMO"):
        repository.get_memory(memory.id)


@pytest.mark.integration
def test_unknown_criticality_value_in_database_fails_clearly_for_decisions(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project_id = _project_id(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    event = event_repository.append(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)
    decision = decision_repository.create_proposal(
        "asunto", project_id, "contenido", source_event_id=event.id
    )

    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE decisions SET criticality = :value WHERE id = :id"),
            {"value": "URGENTISIMO", "id": decision.id},
        )

    with pytest.raises(ValueError, match="URGENTISIMO"):
        decision_repository.get_decision(decision.id)


@pytest.mark.integration
def test_list_current_memories_by_criticality_returns_only_current_and_requested_levels(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repository = build_sqlite_memory_repository(database_path)

    critico = repository.create_memory("critica vigente", "manual")
    repository.set_user_criticality(critico.id, Criticality.CRITICO)

    importante = repository.create_memory("importante vigente", "manual")
    repository.set_user_criticality(importante.id, Criticality.IMPORTANTE)

    sin_marcar = repository.create_memory("sin marcar", "manual")
    assert sin_marcar.criticality is None

    critica_archivada = repository.create_memory("critica archivada", "manual")
    repository.set_user_criticality(critica_archivada.id, Criticality.CRITICO)
    repository.archive_memory(critica_archivada.id)

    solo_criticas = repository.list_current_memories_by_criticality([Criticality.CRITICO])
    assert [memory.id for memory in solo_criticas] == [critico.id]

    ambas = repository.list_current_memories_by_criticality(
        [Criticality.CRITICO, Criticality.IMPORTANTE]
    )
    assert {memory.id for memory in ambas} == {critico.id, importante.id}

    assert repository.list_current_memories_by_criticality([]) == []


@pytest.mark.integration
def test_list_current_decisions_by_criticality_returns_only_approved_and_requested_levels(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project_id = _project_id(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)

    def _propose_and_approve(content: str) -> int:
        event = event_repository.append(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)
        proposal = decision_repository.create_proposal(
            "asunto", project_id, content, source_event_id=event.id
        )
        decision_repository.approve_decision(proposal.id)
        return proposal.id

    critica_id = _propose_and_approve("decision critica")
    decision_repository.set_user_criticality(critica_id, Criticality.CRITICO)

    importante_id = _propose_and_approve("decision importante")
    decision_repository.set_user_criticality(importante_id, Criticality.IMPORTANTE)

    event = event_repository.append(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, None)
    aun_propuesta = decision_repository.create_proposal(
        "asunto", project_id, "decision critica pero solo propuesta", source_event_id=event.id
    )
    decision_repository.set_user_criticality(aun_propuesta.id, Criticality.CRITICO)

    solo_criticas = decision_repository.list_current_decisions_by_criticality([Criticality.CRITICO])
    assert [decision.id for decision in solo_criticas] == [critica_id]

    ambas = decision_repository.list_current_decisions_by_criticality(
        [Criticality.CRITICO, Criticality.IMPORTANTE]
    )
    assert {decision.id for decision in ambas} == {critica_id, importante_id}

    assert decision_repository.list_current_decisions_by_criticality([]) == []
