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

from sirius.adapters.persistence import staged_engine_candidate
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
from sirius.adapters.persistence.staged_engine_port import build_staged_engine_port
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_decision import ArchiveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.delete_memory import DeleteMemoryUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.set_category import SetCategoryUseCase
from sirius.application.supersede_decision import SupersedeDecisionUseCase
from sirius.application.tag_category import CategoryTargetKind
from sirius.domain.conversation import SourceMessageChoice
from sirius.domain.staged_engine_contracts import PuertoDeRecuperacion, SenalesDeCandidato


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


def _use_case(
    database_path: Path,
    *,
    category_vocabulary: frozenset[str] = frozenset(),
    category_matching_enabled: bool = False,
    staged_engine_port: PuertoDeRecuperacion | None = None,
    staged_engine_candidate: SenalesDeCandidato | None = None,
) -> RankRelevantKnowledgeUseCase:
    return RankRelevantKnowledgeUseCase(
        memory_repository=build_sqlite_memory_repository(database_path),
        decision_repository=build_sqlite_decision_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
        category_vocabulary=category_vocabulary,
        category_matching_enabled=category_matching_enabled,
        staged_engine_port=staged_engine_port,
        staged_engine_candidate=staged_engine_candidate,
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


@pytest.mark.integration
def test_a_query_made_only_of_spanish_stopwords_matches_nothing(tmp_path: Path) -> None:
    """Issue #455 (ADR-109): before the lexical treatment, ``sanitize_fts5_query``
    OR-ed every raw token, so a query of only function words ("de", "la",
    "el", ...) would match any memory that happened to contain one of them —
    virtually the entire canon. Once VACIAS is stripped, a query with no
    discriminating term matches nothing, exactly like a blank query."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    SaveManualMemoryUseCase(unit_of_work).save("contenido de la reunión de mañana")

    assert sanitize_fts5_query("de la el en") == ""
    assert _use_case(database_path).rank("¿De qué se trata?") == ()


@pytest.mark.integration
def test_stopwords_shared_with_unrelated_content_never_match_by_themselves(
    tmp_path: Path,
) -> None:
    """Issue #455 (ADR-109): joining every raw token with ``OR`` meant a query
    sharing only Spanish function words with an unrelated memory ("de", "en",
    "la", ...) still matched it via FTS5. Cleaning the query of ``VACIAS``
    before building the ``MATCH`` expression means only a memory that shares
    an actual discriminating term (or one of its morphological variants) is
    returned."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    unrelated = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido de la reunión sobre otro asunto en la oficina"
    )
    matching = SaveManualMemoryUseCase(unit_of_work).save(
        "política de teletrabajo vigente en la sede"
    )

    result = _use_case(database_path).rank("¿Qué política de teletrabajo tenemos?")

    returned_ids = {(candidate.kind.value, candidate.item_id) for candidate in result}
    assert ("memory", matching.id) in returned_ids
    assert ("memory", unrelated.id) not in returned_ids


# --- M9 (§6.2, D7 punto 6): category_match y su puerta de activación, en --
# --- ambos estados — cerrada (por defecto) y abierta. -----------------------

_VOCABULARY = frozenset({"trabajo", "personal", "salud"})


@pytest.mark.integration
def test_category_match_is_inert_against_a_real_candidate_while_the_gate_stays_closed(
    tmp_path: Path,
) -> None:
    """D7 punto 6: mientras el propietario no registre el umbral de
    coincidencia en STATUS.md, la puerta se queda cerrada — el repliegue más
    seguro del diseño (§6.2/§6.3) — y ``category_match`` es ``False`` para
    todo candidato real, sin alterar el orden de ninguno, aunque su
    categoría persistida coincida exactamente con la que activa la
    consulta. ``_use_case`` sin argumentos reproduce exactamente la
    construcción de producción de hoy (los dos parámetros nuevos son
    ``False``/vacío por defecto)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    matching_category = SaveManualMemoryUseCase(unit_of_work).save(
        "palabraunicacompartida con categoría trabajo"
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, matching_category.id, "trabajo")
    no_category = SaveManualMemoryUseCase(unit_of_work).save("palabraunicacompartida sin categoría")
    _set_updated_at(database_path, "memories", matching_category.id, "2020-01-01 00:00:00")
    _set_updated_at(database_path, "memories", no_category.id, "2026-01-01 00:00:00")

    result = _use_case(database_path).rank("palabraunicacompartida trabajo")

    # Only recency (the categorized memory is older) decides — exactly the
    # order the pipeline would produce with no category signal at all.
    assert [candidate.item_id for candidate in result] == [no_category.id, matching_category.id]
    assert all(candidate.category_match is False for candidate in result)


@pytest.mark.integration
def test_category_match_reorders_a_real_candidate_once_the_gate_is_open(tmp_path: Path) -> None:
    """Simétrica de la anterior: con ``category_matching_enabled=True`` y el
    vocabulario real, ``category_match`` sí compara la categoría persistida
    de un candidato real contra la que activa la consulta, y sí decide el
    orden — la misma pareja de recuerdos que, con la puerta cerrada, solo se
    ordenaba por recencia."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    matching_category = SaveManualMemoryUseCase(unit_of_work).save(
        "palabraunicacompartida con categoría trabajo"
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, matching_category.id, "trabajo")
    no_category = SaveManualMemoryUseCase(unit_of_work).save("palabraunicacompartida sin categoría")
    _set_updated_at(database_path, "memories", matching_category.id, "2020-01-01 00:00:00")
    _set_updated_at(database_path, "memories", no_category.id, "2026-01-01 00:00:00")

    result = _use_case(
        database_path, category_vocabulary=_VOCABULARY, category_matching_enabled=True
    ).rank("palabraunicacompartida trabajo")

    # The older, categorized memory now outranks the newer, uncategorized
    # one: category_match sits above recency in the sort tuple (§6.2).
    assert [candidate.item_id for candidate in result] == [matching_category.id, no_category.id]
    matched = next(c for c in result if c.item_id == matching_category.id)
    uncategorized = next(c for c in result if c.item_id == no_category.id)
    assert matched.category_match is True
    assert uncategorized.category_match is False


@pytest.mark.integration
def test_category_match_stays_false_for_a_candidate_without_category_yet_even_with_the_gate_open(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    SaveManualMemoryUseCase(unit_of_work).save("recuerdosincategoriaunico trabajo")

    result = _use_case(
        database_path, category_vocabulary=_VOCABULARY, category_matching_enabled=True
    ).rank("recuerdosincategoriaunico trabajo")

    assert len(result) == 1
    assert result[0].category_match is False


@pytest.mark.integration
def test_category_match_stays_false_when_the_query_activates_no_vocabulary_category(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    categorized = SaveManualMemoryUseCase(unit_of_work).save("recuerdoetiquetadounico")
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, categorized.id, "trabajo")

    result = _use_case(
        database_path, category_vocabulary=_VOCABULARY, category_matching_enabled=True
    ).rank("recuerdoetiquetadounico sin ninguna categoría del vocabulario")

    assert len(result) == 1
    assert result[0].category_match is False


# -- El motor por etapas detrás de la puerta D7 punto 6 (incidencia #457) ----


@pytest.mark.integration
def test_staged_engine_stays_unused_with_the_gate_closed_even_if_wired(tmp_path: Path) -> None:
    """Con la puerta cerrada (el valor por defecto que
    ``composition_root`` sigue construyendo), ``rank()`` da exactamente el
    mismo resultado tenga o no un puerto/candidato del motor por etapas
    configurados — la garantía literal de "con la puerta cerrada, el
    comportamiento del producto es idéntico al de hoy" (incidencia #457)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    SaveManualMemoryUseCase(unit_of_work).save("faroquenopalabraunica sobre la costa")

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        sin_motor = _use_case(database_path).rank("faroquenopalabraunica")
        con_motor_pero_cerrada = _use_case(
            database_path, staged_engine_port=puerto, staged_engine_candidate=candidato
        ).rank("faroquenopalabraunica")
    finally:
        puerto.close()

    assert con_motor_pero_cerrada == sin_motor


@pytest.mark.integration
def test_staged_engine_is_used_with_the_gate_open_and_wired(tmp_path: Path) -> None:
    """Con la puerta abierta y el puerto/candidato configurados,
    ``rank()`` delega en ``sirius.domain.staged_engine.recuperar`` (ADR-109)
    en vez del filtro-y-orden de siempre."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memoria = SaveManualMemoryUseCase(unit_of_work).save("faroquenopalabraunica sobre la costa")

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("faroquenopalabraunica")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria.id]


@pytest.mark.integration
def test_staged_engine_path_still_finds_a_category_only_match(tmp_path: Path) -> None:
    """CODEX-001 (incidencia #457): el motor por etapas solo genera
    candidatos por asunto exacto o FTS5, nunca por categoría, así que con
    la puerta abierta y el motor cableado un candidato que solo coincide
    por categoría (M9, §6.2) desaparecía en vez de encontrarse, contra
    ``test_a_category_match_alone_makes_an_otherwise_unrelated_candidate_
    related`` (``tests/unit/test_relevance_domain.py``)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_categorizada = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, memoria_categorizada.id, "trabajo")

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            category_vocabulary=_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("trabajo")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria_categorizada.id]
    assert resultado[0].category_match is True


@pytest.mark.integration
def test_staged_engine_gate_open_without_a_configured_port_falls_back_to_current_pipeline(
    tmp_path: Path,
) -> None:
    """La puerta sola no basta: sin puerto/candidato configurados (ningún
    caller real de hoy los construye), ``rank()`` sigue el camino de
    siempre en vez de fallar."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    SaveManualMemoryUseCase(unit_of_work).save("faroquenopalabraunica sobre la costa")

    con_puerta_abierta_sin_motor = _use_case(database_path, category_matching_enabled=True).rank(
        "faroquenopalabraunica"
    )
    sin_puerta = _use_case(database_path).rank("faroquenopalabraunica")

    assert con_puerta_abierta_sin_motor == sin_puerta
