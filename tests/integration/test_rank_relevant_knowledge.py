"""B6b: end-to-end retrieval and relevance ordering over vigente knowledge
(SIRIUS-ARQ-0.1 S7.5; D-11).

Every write goes through the real use cases and repositories — no fake
adapter — against a database migrated with real Alembic, exactly like
``test_search_index_sync.py`` (B6a): ``knowledge_fts`` only exists once the
hand-written migration runs, so this is the only way to exercise a real FTS5
``MATCH`` rather than a Python approximation of one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
    sanitize_fts5_query,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_decision import ArchiveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.delete_memory import DeleteMemoryUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.supersede_decision import SupersedeDecisionUseCase
from sirius.domain.conversation import SourceMessageChoice


def _bootstrap(database_path: Path) -> None:
    upgrade_to_head(database_path)


def _two_projects(database_path: Path) -> tuple[int, int]:
    """Return ``(active_project_id, other_project_id)`` — two real project
    rows, satisfying the ``project_id`` foreign key both ``memories`` and
    ``decisions`` enforce, with only the first left ``ACTIVE`` (SQLite
    itself rejects a second active project)."""
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    other = project_repository.create_project(
        "Otro proyecto", "objetivo", state_summary="estado", blockers=(), next_step="siguiente"
    )
    project_repository.complete_active_project(other.id)
    active = project_repository.create_project(
        "Proyecto activo", "objetivo", state_summary="estado", blockers=(), next_step="siguiente"
    )
    return active.id, other.id


def _use_case(database_path: Path) -> RankRelevantKnowledgeUseCase:
    return RankRelevantKnowledgeUseCase(
        memory_repository=build_sqlite_memory_repository(database_path),
        decision_repository=build_sqlite_decision_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
    )


def _set_updated_at(database_path: Path, table: str, row_id: int, updated_at: str) -> None:
    engine = build_engine(database_path)
    with engine.begin() as connection:
        connection.execute(
            text(f"UPDATE {table} SET updated_at = :updated_at WHERE id = :id"),
            {"updated_at": updated_at, "id": row_id},
        )


@pytest.mark.integration
def test_only_vigente_knowledge_is_ever_returned(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, _ = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    current_memory = SaveManualMemoryUseCase(unit_of_work).save("recuerdovigenteunico")
    archived_memory = SaveManualMemoryUseCase(unit_of_work).save("recuerdoarchivadounico")
    ArchiveMemoryUseCase(unit_of_work).archive(archived_memory.id)
    deleted_memory = SaveManualMemoryUseCase(unit_of_work).save("recuerdoeliminadounico")
    DeleteMemoryUseCase(unit_of_work).delete(
        deleted_memory.id, confirmed=True, source_message_choice=SourceMessageChoice.PRESERVE
    )

    proposed_decision = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto propuesto", active_project_id, "decisionpropuestaunica"
    )
    approved_decision = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto aprobado", active_project_id, "decisionaprobadaunica"
    )
    ApproveDecisionUseCase(unit_of_work).approve(approved_decision.id, confirmed=True)
    archived_decision = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto archivado", active_project_id, "decisionarchivadaunica"
    )
    ApproveDecisionUseCase(unit_of_work).approve(archived_decision.id, confirmed=True)
    ArchiveDecisionUseCase(unit_of_work).archive(archived_decision.id)
    superseded_decision = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto sustituido", active_project_id, "decisionsustituidaunica"
    )
    ApproveDecisionUseCase(unit_of_work).approve(superseded_decision.id, confirmed=True)
    superseding_decision = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto sustituido", active_project_id, "decisionsustitutaunica"
    )
    SupersedeDecisionUseCase(unit_of_work).supersede(
        superseded_decision.id, superseding_decision.id, confirmed=True
    )

    query = (
        "recuerdovigenteunico recuerdoarchivadounico recuerdoeliminadounico "
        "decisionpropuestaunica decisionaprobadaunica decisionarchivadaunica "
        "decisionsustituidaunica decisionsustitutaunica"
    )
    result = _use_case(database_path).rank(query)

    returned_ids = {(candidate.kind.value, candidate.item_id) for candidate in result}
    assert ("memory", current_memory.id) in returned_ids
    assert ("memory", archived_memory.id) not in returned_ids
    assert ("memory", deleted_memory.id) not in returned_ids
    assert ("decision", proposed_decision.id) not in returned_ids
    assert ("decision", approved_decision.id) in returned_ids
    assert ("decision", archived_decision.id) not in returned_ids
    assert ("decision", superseded_decision.id) not in returned_ids
    assert ("decision", superseding_decision.id) in returned_ids


@pytest.mark.integration
def test_a_subject_matching_decision_outranks_a_general_memory(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, _ = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "palabraclavecompartida contenido de un recuerdo general"
    )
    decision = ProposeDecisionUseCase(unit_of_work).propose(
        "palabraclavecompartida", active_project_id, "contenido de la decisión"
    )
    ApproveDecisionUseCase(unit_of_work).approve(decision.id, confirmed=True)

    result = _use_case(database_path).rank("hablemos de palabraclavecompartida hoy")

    assert [(candidate.kind.value, candidate.item_id) for candidate in result] == [
        ("decision", decision.id),
        ("memory", memory.id),
    ]


@pytest.mark.integration
def test_active_project_membership_outranks_another_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, other_project_id = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    other_project_decision = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto de otro proyecto", other_project_id, "palabraunicacompartida en otro proyecto"
    )
    ApproveDecisionUseCase(unit_of_work).approve(other_project_decision.id, confirmed=True)
    active_project_decision = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto del proyecto activo", active_project_id, "palabraunicacompartida en el activo"
    )
    ApproveDecisionUseCase(unit_of_work).approve(active_project_decision.id, confirmed=True)

    result = _use_case(database_path).rank("palabraunicacompartida")

    assert [(candidate.kind.value, candidate.item_id) for candidate in result] == [
        ("decision", active_project_decision.id),
        ("decision", other_project_decision.id),
    ]


@pytest.mark.integration
def test_recency_outranks_older_when_every_other_criterion_ties(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    older_memory = SaveManualMemoryUseCase(unit_of_work).save("recuerdocompartidounico antiguo")
    newer_memory = SaveManualMemoryUseCase(unit_of_work).save("recuerdocompartidounico reciente")
    _set_updated_at(database_path, "memories", older_memory.id, "2020-01-01 00:00:00")
    _set_updated_at(database_path, "memories", newer_memory.id, "2026-01-01 00:00:00")

    result = _use_case(database_path).rank("recuerdocompartidounico")

    assert [(candidate.kind.value, candidate.item_id) for candidate in result] == [
        ("memory", newer_memory.id),
        ("memory", older_memory.id),
    ]


@pytest.mark.integration
def test_tie_break_is_stable_and_deterministic_by_id(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    first_memory = SaveManualMemoryUseCase(unit_of_work).save("empatadaspalabraunica primero")
    second_memory = SaveManualMemoryUseCase(unit_of_work).save("empatadaspalabraunica segundo")
    same_moment = "2026-01-01 00:00:00"
    _set_updated_at(database_path, "memories", first_memory.id, same_moment)
    _set_updated_at(database_path, "memories", second_memory.id, same_moment)

    result = _use_case(database_path).rank("empatadaspalabraunica")

    assert [(candidate.kind.value, candidate.item_id) for candidate in result] == [
        ("memory", first_memory.id),
        ("memory", second_memory.id),
    ]


@pytest.mark.integration
def test_fts5_match_comes_from_the_real_index_not_a_python_substring_filter(
    tmp_path: Path,
) -> None:
    """FTS5's default tokenizer matches whole tokens, never a substring of
    one: "traordin" never matches "extraordinariopalabra" via FTS5, even
    though a naive ``"traordin" in content`` Python check would wrongly
    match it. Proving this holds end to end confirms the ranking really
    goes through ``knowledge_fts``'s own ``MATCH``, not a Python filter over
    fetched content (an explicit B6b acceptance requirement)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    SaveManualMemoryUseCase(unit_of_work).save("extraordinariopalabra")

    assert _use_case(database_path).rank("traordin") == ()
    assert _use_case(database_path).rank("extraordinariopalabra") != ()


@pytest.mark.integration
@pytest.mark.parametrize(
    "query_text", ['"raro"', "a* AND (b) - OR", 'content:"x"', "***", "-", "()"]
)
def test_special_characters_in_the_query_never_break_the_search(
    tmp_path: Path, query_text: str
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)

    result = _use_case(database_path).rank(query_text)

    assert result == ()


@pytest.mark.integration
def test_an_empty_query_returns_no_matches_without_erroring(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    SaveManualMemoryUseCase(unit_of_work).save("cualquier contenido")

    assert _use_case(database_path).rank("") == ()
    assert sanitize_fts5_query("") == ""
    assert sanitize_fts5_query("   ") == ""
    assert sanitize_fts5_query("***") == ""
