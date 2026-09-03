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
from sirius.application import rank_relevant_knowledge as rank_relevant_knowledge_module
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_decision import ArchiveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.delete_memory import DeleteMemoryUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.set_category import SetCategoryUseCase
from sirius.application.set_criticality import CriticalityTargetKind, SetCriticalityUseCase
from sirius.application.supersede_decision import SupersedeDecisionUseCase
from sirius.application.tag_category import CategoryTargetKind
from sirius.domain.conversation import SourceMessageChoice
from sirius.domain.criticality import Criticality
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
    criticality_vocabulary: frozenset[str] = frozenset(),
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
        criticality_vocabulary=criticality_vocabulary,
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

#: M19a (ADR-127, incidencia #512): el mismo vocabulario real que
#: ``composition_root._CRITICALITY_VOCABULARY``.
_CRITICALITY_VOCABULARY = frozenset(
    {"esencial", "restriccion", "critica", "obligatoria", "imprescindible"}
)


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
    en vez del filtro-y-orden de siempre.

    M16 (incidencia #504) cablea la petición con ámbito real derivado del
    proyecto activo: la memoria vive en ese mismo proyecto para que ``G4``
    (``src/sirius/domain/staged_engine_gates.py:135-152``) la admita — sin
    esto, ``G4`` la descartaría por no declarar ámbito global ni pertenecer
    al proyecto que la petición ahora autoriza."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, _ = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memoria = SaveManualMemoryUseCase(unit_of_work).save(
        "faroquenopalabraunica sobre la costa", project_id=active_project_id
    )

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
def test_staged_engine_rejects_a_motor_admitted_candidate_outside_the_active_project(
    tmp_path: Path,
) -> None:
    """M16 (§11.3/§11.5, incidencia #504): a diferencia de M14 (que ya
    restringe por ámbito solo la ampliación por categoría,
    ``candidate_in_declared_scope``), el ámbito real de la petición ahora
    alimenta también ``G4`` (``src/sirius/domain/staged_engine_gates.py:135-152``)
    dentro del motor por etapas mismo: la misma consulta contra la misma
    memoria cambia de resultado solo por el proyecto activo declarado — con
    un proyecto activo distinto del suyo, el motor deja de admitirla; sin
    proyecto activo (ámbito global, igual que antes de este encargo), vuelve
    a admitirla."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, other_project_id = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memoria_de_otro_proyecto = SaveManualMemoryUseCase(unit_of_work).save(
        "faroquenopalabraunica sobre la costa", project_id=other_project_id
    )

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        con_proyecto_activo_ajeno = _use_case(
            database_path,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("faroquenopalabraunica")

        build_sqlite_project_repository(database_path).complete_active_project(active_project_id)
        sin_proyecto_activo = _use_case(
            database_path,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("faroquenopalabraunica")
    finally:
        puerto.close()

    assert con_proyecto_activo_ajeno == ()
    assert [c.item_id for c in sin_proyecto_activo] == [memoria_de_otro_proyecto.id]


@pytest.mark.integration
def test_staged_engine_admits_a_globally_scoped_memory_with_an_active_project(
    tmp_path: Path,
) -> None:
    """CLAUDE-REV-M16-001/CODEX-001 (incidencia #504/#505): ``G4`` debe
    seguir la misma regla que ``candidate_in_declared_scope``
    (``src/sirius/domain/relevance.py:250-266``) ya aplica a la ampliación
    por categoría de M14 — un candidato sin ``project_id`` (ámbito global)
    se admite pase lo que pase con el ámbito de la petición. Antes de esta
    corrección, ``Ambito.autoriza`` (``src/sirius/domain/
    staged_engine_contracts.py``) exigía ``project_id is not None``, así que
    el motor por etapas descartaba por ``G4`` una memoria global en cuanto
    había un proyecto activo, aunque la encontrara por coincidencia literal."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memoria_global = SaveManualMemoryUseCase(unit_of_work).save(
        "faroglobalunicasola sobre la costa"
    )

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("faroglobalunicasola")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria_global.id]


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
def test_staged_engine_path_orders_by_the_full_m9_tuple_not_by_block(tmp_path: Path) -> None:
    """CODEX-001 (incidencia #457): con la puerta abierta y el motor
    cableado, ``_rank_via_staged_engine`` concatenaba ``ranked`` (lo
    admitido por el motor) delante de ``solo_por_categoria`` sin más,
    colocando siempre todo lo admitido por el motor antes que lo hallado
    solo por categoría con independencia de las demás señales (S7.5/M9:
    sujeto, proyecto activo, FTS5, categoría, recencia).

    M16 (incidencia #504) cablea el ámbito real de la petición: un candidato
    fuera del proyecto activo ya no lo admite ni siquiera el motor (``G4``),
    así que el proyecto deja de servir como señal que distinga los dos
    candidatos de esta prueba — los dos deben vivir en el proyecto activo
    para que el motor pueda admitir el suyo. La señal que ahora demuestra
    que el orden no es una concatenación de bloques es el sujeto (la
    primera del criterio S7.5/M9, por delante de proyecto/FTS5/categoría):
    la decisión hallada solo por categoría tiene un asunto que coincide con
    la consulta (``subject_matches_query``), una memoria nunca lo declara
    (``rank_relevant_knowledge.py``, ``subject_matches_query=False`` fijo
    para toda memoria) — así que el orden correcto antepone la decisión
    pese a haber llegado por el bloque de categoría, no por el del motor."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, _ = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    decision_por_categoria = ProposeDecisionUseCase(unit_of_work).propose(
        "trabajo cotidiano",
        active_project_id,
        "contenido sin ninguna palabra en comun con la consulta",
    )
    ApproveDecisionUseCase(unit_of_work).approve(decision_por_categoria.id, confirmed=True)
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.DECISION, decision_por_categoria.id, "trabajo")
    memoria_por_motor = SaveManualMemoryUseCase(unit_of_work).save(
        "trabajo intenso esta semana en la fabrica", project_id=active_project_id
    )

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

    assert [(c.kind.value, c.item_id) for c in resultado] == [
        ("decision", decision_por_categoria.id),
        ("memory", memoria_por_motor.id),
    ]
    encontrada_por_categoria = next(c for c in resultado if c.kind.value == "decision")
    encontrada_por_motor = next(c for c in resultado if c.kind.value == "memory")
    assert encontrada_por_categoria.category_match is True
    assert encontrada_por_categoria.subject_matches_query is True
    assert encontrada_por_motor.fts_match is True
    assert encontrada_por_motor.subject_matches_query is False


@pytest.mark.integration
def test_staged_engine_category_index_activates_for_two_vocabulary_terms_at_once(
    tmp_path: Path,
) -> None:
    """M14 (§11.2/§11.5, incidencia #486): a diferencia de la activación
    única de ``category_matches_query``, el índice de categoría buscable
    tras la puerta admite un candidato que el motor no encontró cuando la
    consulta contiene dos o más términos del vocabulario a la vez — réplica
    de ``activa_categoria_buscable`` (ADR-113) sobre el vocabulario real."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    solo_por_categoria = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, solo_por_categoria.id, "trabajo")

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            category_vocabulary=_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("trabajo y salud a la vez")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [solo_por_categoria.id]
    assert resultado[0].category_match is True


@pytest.mark.integration
def test_staged_engine_category_index_rejects_a_decision_scoped_to_a_different_project(
    tmp_path: Path,
) -> None:
    """M14 (§11.2/§11.5, incidencia #486): la restricción por ámbito —
    réplica de ``_en_ambito_declarado`` (ADR-114)— excluye un candidato de
    categoría no ordinaria cuyo ``project_id`` no coincide con el proyecto
    activo de la petición, aunque la consulta active la categoría. Una
    decisión siempre declara proyecto (nunca ``None``), así que nunca es de
    ámbito global por sí misma."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, other_project_id = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    decision_de_otro_proyecto = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto sin ninguna palabra en comun", other_project_id, "contenido"
    )
    ApproveDecisionUseCase(unit_of_work).approve(decision_de_otro_proyecto.id, confirmed=True)
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.DECISION, decision_de_otro_proyecto.id, "trabajo")

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

    assert active_project_id != other_project_id
    assert resultado == ()


@pytest.mark.integration
def test_staged_engine_category_index_admits_a_globally_scoped_memory_regardless_of_active_project(
    tmp_path: Path,
) -> None:
    """M14 (§11.2/§11.5, incidencia #486): un candidato de ámbito global
    (``project_id`` ``None``, solo posible para ``Memory``) se admite por
    categoría sin importar cuál sea el proyecto activo de la petición —
    misma excepción que ``G4`` ya aplica siempre."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_global = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, memoria_global.id, "trabajo")
    assert memoria_global.project_id is None

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

    assert [c.item_id for c in resultado] == [memoria_global.id]


@pytest.mark.integration
def test_staged_engine_category_index_scope_restriction_is_symmetric_between_two_projects(
    tmp_path: Path,
) -> None:
    """M14 (§11.2/§11.5, incidencia #486): la restricción de ámbito no
    favorece a ningún proyecto en particular — un candidato del proyecto que
    dejó de estar activo se excluye exactamente igual que uno que nunca lo
    estuvo, así que un candidato del proyecto A se rechaza cuando el ámbito
    declarado es el B, y viceversa cuando el ámbito activo vuelve a
    cambiar."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    project_repository = build_sqlite_project_repository(database_path)

    project_repository.ensure_bootstrap_project()
    proyecto_1 = project_repository.create_project(
        "Proyecto 1", "objetivo", state_summary="estado", blockers=(), next_step="siguiente"
    )
    memoria_1 = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta", project_id=proyecto_1.id
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, memoria_1.id, "trabajo")

    project_repository.complete_active_project(proyecto_1.id)
    proyecto_2 = project_repository.create_project(
        "Proyecto 2", "objetivo", state_summary="estado", blockers=(), next_step="siguiente"
    )
    memoria_2 = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta", project_id=proyecto_2.id
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, memoria_2.id, "trabajo")

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        # Ámbito activo: proyecto 2 — memoria_1 (proyecto 1) se rechaza,
        # memoria_2 (el propio proyecto activo) se admite.
        con_proyecto_2_activo = _use_case(
            database_path,
            category_vocabulary=_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("trabajo")

        # El ámbito activo cambia de nuevo: ahora ninguno de los dos es el
        # proyecto activo, así que ambos se rechazan — "ni al revés" no deja
        # a memoria_2 exenta solo por haber sido el ámbito activo antes.
        project_repository.complete_active_project(proyecto_2.id)
        project_repository.create_project(
            "Proyecto 3", "objetivo", state_summary="estado", blockers=(), next_step="siguiente"
        )
        con_proyecto_3_activo = _use_case(
            database_path,
            category_vocabulary=_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("trabajo")
    finally:
        puerto.close()

    assert [c.item_id for c in con_proyecto_2_activo] == [memoria_2.id]
    assert con_proyecto_3_activo == ()


@pytest.mark.integration
def test_staged_engine_path_with_the_gate_closed_never_runs_the_category_amplification(
    tmp_path: Path,
) -> None:
    """M14 (§11.2/§11.5, incidencia #486): con la puerta cerrada,
    ``_rank_via_staged_engine`` produce exactamente el mismo resultado que
    antes de este encargo, byte a byte, sobre el mismo caso — el bloque de
    ampliación (ahora el índice de activación múltiple con restricción de
    ámbito) solo se ejecuta cuando ``category_matching_enabled`` es
    ``True``, así que con la puerta cerrada el resultado depende
    exclusivamente de lo que el motor por etapas admitió, exactamente como
    siempre."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    admitida_por_el_motor = SaveManualMemoryUseCase(unit_of_work).save(
        "trabajo intenso en la fabrica"
    )
    solo_por_categoria = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, solo_por_categoria.id, "trabajo")

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        use_case = _use_case(
            database_path,
            category_vocabulary=_VOCABULARY,
            category_matching_enabled=False,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        )
        resultado = use_case._rank_via_staged_engine("trabajo")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [admitida_por_el_motor.id]


@pytest.mark.integration
def test_staged_engine_path_preserves_engine_order_between_two_admitted_candidates(
    tmp_path: Path,
) -> None:
    """CODEX-001 (incidencia #457, tercera ronda): la corrección anterior
    intercalaba ``solo_por_categoria`` volviendo a ordenar también
    ``ranked`` entero con ``rank_relevant_knowledge`` (sujeto, proyecto
    activo, FTS5, categoría, recencia), sustituyendo la prioridad que el
    motor ya adjudicó a lo que él mismo admitió —criticidad, representante y
    autoridad de la etapa de origen (``staged_engine.py``)— incluso cuando
    ``solo_por_categoria`` está vacío. Se reproduce con dos memorias que el
    motor admite en etapas distintas: una en ``E1`` (coincidencia literal,
    mayor autoridad) y otra en ``E2`` (variante morfológica "trabajos" de
    "trabajo", menor autoridad).

    M16 (incidencia #504) cablea el ámbito real de la petición: ``G4``
    (``src/sirius/domain/staged_engine_gates.py:135-152``) ya no admite un
    candidato fuera del proyecto activo, así que ambas memorias deben vivir
    en el proyecto activo para que el motor las admita — el proyecto deja
    de servir como señal que un resort global pudiera invertir. En su lugar,
    la de menor autoridad (``E2``) es más reciente que la de mayor autoridad
    (``E1``): un ``rank_relevant_knowledge`` global sobre ambas invertiría el
    orden por esa señal de recencia (la última del criterio S7.5/M9, con
    sujeto/proyecto/FTS5/categoría empatados entre las dos); el orden
    corregido debe conservar el que el motor ya fijó por autoridad de
    etapa."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, _ = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    encontrada_en_e1 = SaveManualMemoryUseCase(unit_of_work).save(
        "trabajo intenso en la fabrica", project_id=active_project_id
    )
    encontrada_en_e2 = SaveManualMemoryUseCase(unit_of_work).save(
        "trabajos pendientes de revision", project_id=active_project_id
    )
    _set_updated_at(database_path, "memories", encontrada_en_e1.id, "2020-01-01 00:00:00")
    _set_updated_at(database_path, "memories", encontrada_en_e2.id, "2026-01-01 00:00:00")

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("trabajo")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [encontrada_en_e1.id, encontrada_en_e2.id]
    encontrada_por_e1 = next(c for c in resultado if c.item_id == encontrada_en_e1.id)
    encontrada_por_e2 = next(c for c in resultado if c.item_id == encontrada_en_e2.id)
    assert encontrada_por_e1.project_matches_active is True
    assert encontrada_por_e2.project_matches_active is True
    assert encontrada_por_e1.item.updated_at < encontrada_por_e2.item.updated_at


# --- M19a (ADR-127, incidencia #512): solo_por_criticidad, el segundo -----
# --- bloque de ampliación, sobre Memory.criticality/Decision.criticality --
# --- (M18b) en vez de category — misma forma, mismo vocabulario propio. ---


@pytest.mark.integration
def test_staged_engine_path_still_finds_a_criticality_only_match(tmp_path: Path) -> None:
    """M19a: igual que un candidato solo por categoría, uno hallado solo por
    su criticidad se encuentra aunque el motor por etapas nunca lo admita —
    el motor nunca busca por ``criticality``, solo por asunto exacto y
    FTS5. Consulta real del banco de 47 (B04-CA-31)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_critica = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria_critica.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            category_vocabulary=_VOCABULARY,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("Dame todas las restricciones esenciales que debo respetar.")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria_critica.id]
    assert resultado[0].criticality_match is True
    assert resultado[0].fts_match is False
    assert resultado[0].category_match is False


@pytest.mark.integration
def test_staged_engine_importante_criticality_also_activates_the_criticality_index(
    tmp_path: Path,
) -> None:
    """M19a: IMPORTANTE, no solo CRITICO, amplía — el canon reconoce dos
    niveles no ordinarios (M18b) y ``_NIVELES_DE_CRITICIDAD_NO_ORDINARIOS``
    pide los dos."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_importante = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria_importante.id, Criticality.IMPORTANTE)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("restricciones obligatorias")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria_importante.id]


@pytest.mark.integration
def test_staged_engine_criticality_index_rejects_a_decision_scoped_to_a_different_project(
    tmp_path: Path,
) -> None:
    """M19a: la misma restricción de ámbito (``candidate_in_declared_scope``)
    que protege el bloque de categoría protege también el de criticidad."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, other_project_id = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    decision_de_otro_proyecto = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto sin ninguna palabra en comun", other_project_id, "contenido"
    )
    ApproveDecisionUseCase(unit_of_work).approve(decision_de_otro_proyecto.id, confirmed=True)
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.DECISION, decision_de_otro_proyecto.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("restricciones esenciales")
    finally:
        puerto.close()

    assert active_project_id != other_project_id
    assert resultado == ()


@pytest.mark.integration
def test_staged_engine_criticality_index_admits_a_globally_scoped_memory(
    tmp_path: Path,
) -> None:
    """M19a: un candidato de ámbito global (``project_id`` ``None``) se
    admite por criticidad sin importar cuál sea el proyecto activo — misma
    excepción que ``G4`` ya aplica siempre, réplica de la equivalente para
    categoría."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_global = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria_global.id, Criticality.CRITICO)
    assert memoria_global.project_id is None

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("restricciones esenciales")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria_global.id]


@pytest.mark.integration
def test_staged_engine_path_with_the_gate_closed_never_runs_the_criticality_amplification(
    tmp_path: Path,
) -> None:
    """M19a: con la puerta cerrada, ``_rank_via_staged_engine`` nunca
    ejecuta ``solo_por_criticidad`` — depende exclusivamente de lo que el
    motor admitió, exactamente como el bloque de categoría."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    admitida_por_el_motor = SaveManualMemoryUseCase(unit_of_work).save(
        "trabajo intenso en la fabrica"
    )
    solo_por_criticidad = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, solo_por_criticidad.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        use_case = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=False,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        )
        resultado = use_case._rank_via_staged_engine("trabajo restricciones esenciales")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [admitida_por_el_motor.id]


@pytest.mark.integration
def test_staged_engine_criticality_block_never_duplicates_a_candidate_the_motor_already_admitted(
    tmp_path: Path,
) -> None:
    """M19a: el dedup del bloque de criticidad comprueba también contra lo
    admitido por el motor (no solo contra el bloque de categoría) — un
    candidato con FTS5 real y criticidad no ordinaria aparece una sola vez,
    con la señal ``fts_match=True`` que el motor ya le dio, nunca sustituida
    por una entrada de solo-criticidad con ``fts_match=False``."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    admitida_por_motor_y_critica = SaveManualMemoryUseCase(unit_of_work).save(
        "trabajo intenso en la fabrica"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, admitida_por_motor_y_critica.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("trabajo y restricciones esenciales")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [admitida_por_motor_y_critica.id]
    assert resultado[0].fts_match is True


@pytest.mark.integration
def test_staged_engine_criticality_block_dedups_against_the_category_block(
    tmp_path: Path,
) -> None:
    """M19a: un candidato con categoría (activada por su propio vocabulario)
    Y criticidad no ordinaria, con una consulta que activa los dos índices a
    la vez, aparece una sola vez — el dedup del bloque de criticidad
    comprueba también contra lo que el bloque de categoría ya trajo."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, memoria.id, "trabajo")
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            category_vocabulary=_VOCABULARY,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("trabajo y restricciones esenciales")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria.id]
    assert resultado[0].category_match is True
    assert resultado[0].criticality_match is False


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


# --- M20 (ADR-129, incidencia #516, Decisión 2 del propietario del ---------
# --- 02-09-2026): siembra, el tercer bloque de ampliación — activado por ---
# --- el PROPÓSITO de la petición (pide_contexto), no por vocabulario. ------

#: `_peticion_ordinaria` declara siempre este propósito fijo (M16, ADR-124),
#: que ya contiene la subcadena "contexto" — así que toda llamada real a
#: ``rank()`` siembra por defecto. Estas pruebas lo confirman con el mismo
#: propósito real de producción, sin monkeypatch, salvo la única prueba que
#: comprueba el caso contrario (sin propósito de contexto).
_PROPOSITO_SIN_CONTEXTO = "consultar"


@pytest.mark.integration
def test_siembra_finds_a_criticality_only_match_with_a_query_naming_no_vocabulary_term(
    tmp_path: Path,
) -> None:
    """M20: a diferencia de ``solo_por_criticidad`` (activado por
    vocabulario), la siembra encuentra un candidato CRITICO aunque la
    consulta no nombre ninguna palabra de ningún vocabulario — B04-CA-34
    ("Prepara el contexto de planificación de Alfa") es exactamente ese
    caso real del banco (incidencia #516, objetivo, punto d)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_critica = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria_critica.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("Prepara el contexto de planificacion de Alfa.")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria_critica.id]
    assert resultado[0].seeded is True
    assert resultado[0].criticality_match is False
    assert resultado[0].fts_match is False
    assert resultado[0].category_match is False


@pytest.mark.integration
def test_siembra_never_seeds_an_ordinary_candidate(tmp_path: Path) -> None:
    """M20: la siembra solo amplía lo no ordinario
    (``_NIVELES_DE_CRITICIDAD_NO_ORDINARIOS``) — un recuerdo sin
    ``criticality`` (``None``, el nivel ordinario implícito) nunca se
    siembra, aunque el propósito declare contexto."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    SaveManualMemoryUseCase(unit_of_work).save(
        "recuerdo ordinario sin ninguna palabra en comun con la consulta"
    )

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("Prepara el contexto de planificacion de Alfa.")
    finally:
        puerto.close()

    assert resultado == ()


@pytest.mark.integration
def test_siembra_rejects_a_critico_decision_scoped_to_a_different_project(
    tmp_path: Path,
) -> None:
    """M20: la misma restricción de ámbito (``candidate_in_declared_scope``)
    que protege categoría/criticidad protege también la siembra — un CRITICO
    de otro proyecto no entra, aunque el propósito declare contexto (mismo
    caso que ``test_siembra_de_contexto_respeta_el_ambito_declarado`` del
    arnés de examen)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    active_project_id, other_project_id = _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    decision_de_otro_proyecto = ProposeDecisionUseCase(unit_of_work).propose(
        "asunto sin ninguna palabra en comun", other_project_id, "contenido"
    )
    ApproveDecisionUseCase(unit_of_work).approve(decision_de_otro_proyecto.id, confirmed=True)
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.DECISION, decision_de_otro_proyecto.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("Prepara el contexto de planificacion de Alfa.")
    finally:
        puerto.close()

    assert active_project_id != other_project_id
    assert resultado == ()


@pytest.mark.integration
def test_siembra_admits_a_globally_scoped_critico_memory(tmp_path: Path) -> None:
    """M20: un candidato de ámbito global (``project_id`` ``None``) se
    siembra sin importar cuál sea el proyecto activo — misma excepción que
    ``G4`` ya aplica siempre, réplica de la equivalente para categoría y
    criticidad."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_global = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria_global.id, Criticality.CRITICO)
    assert memoria_global.project_id is None

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("Prepara el contexto de planificacion de Alfa.")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria_global.id]
    assert resultado[0].seeded is True


@pytest.mark.integration
def test_siembra_never_duplicates_a_candidate_the_motor_already_admitted(tmp_path: Path) -> None:
    """M20: el dedup de la siembra comprueba también contra lo admitido por
    el motor — un candidato con FTS5 real y criticidad no ordinaria aparece
    una sola vez, con la señal ``fts_match=True`` que el motor ya le dio,
    nunca sustituida por una entrada de siembra con ``fts_match=False``."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    admitida_por_motor_y_critica = SaveManualMemoryUseCase(unit_of_work).save(
        "trabajo intenso en la fabrica"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, admitida_por_motor_y_critica.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("trabajo intenso en la fabrica")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [admitida_por_motor_y_critica.id]
    assert resultado[0].fts_match is True
    assert resultado[0].seeded is False


@pytest.mark.integration
def test_siembra_never_duplicates_a_candidate_the_criticality_block_already_admitted(
    tmp_path: Path,
) -> None:
    """M20: el dedup de la siembra comprueba también contra
    ``solo_por_criticidad`` — un candidato que la consulta ya activa por
    vocabulario de criticidad aparece una sola vez, sin una segunda entrada
    de siembra."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_critica = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria_critica.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("Dame todas las restricciones esenciales que debo respetar.")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria_critica.id]
    assert resultado[0].criticality_match is True
    assert resultado[0].seeded is False


@pytest.mark.integration
def test_siembra_never_duplicates_a_candidate_the_category_block_already_admitted(
    tmp_path: Path,
) -> None:
    """M20: el dedup de la siembra comprueba también contra
    ``solo_por_categoria`` — un candidato con categoría (activada por su
    propio vocabulario) Y criticidad no ordinaria, con una consulta que
    activa el índice de categoría, aparece una sola vez."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCategoryUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CategoryTargetKind.MEMORY, memoria.id, "trabajo")
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            category_vocabulary=_VOCABULARY,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("trabajo, por favor")
    finally:
        puerto.close()

    assert [c.item_id for c in resultado] == [memoria.id]
    assert resultado[0].category_match is True
    assert resultado[0].seeded is False


@pytest.mark.integration
def test_siembra_seeds_nothing_without_a_context_purpose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M20: sin propósito de contexto (``pide_contexto`` falso), la siembra
    no aporta nada — réplica de
    ``test_siembra_de_contexto_respeta_el_ambito_declarado``'s segunda mitad
    en el arnés de examen. ``_peticion_ordinaria`` fija el propósito real de
    producción (M16), así que esta prueba lo sustituye por uno sin la
    subcadena "contexto" para poder ejercitar la rama contraria."""
    monkeypatch.setattr(
        rank_relevant_knowledge_module,
        "_PROPOSITO_RECUPERACION_ORDINARIA",
        _PROPOSITO_SIN_CONTEXTO,
    )
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_critica = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria_critica.id, Criticality.CRITICO)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        resultado = _use_case(
            database_path,
            criticality_vocabulary=_CRITICALITY_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        ).rank("Prepara el contexto de planificacion de Alfa.")
    finally:
        puerto.close()

    assert resultado == ()


@pytest.mark.integration
def test_siembra_seeds_nothing_with_the_gate_closed(tmp_path: Path) -> None:
    """M20: con ``category_matching_enabled=False``,
    ``_rank_via_staged_engine`` ni siquiera se ejecuta —``rank()`` sigue
    ``_rank_via_current_pipeline`` en su lugar—, así que la siembra nunca
    puede aportar nada, aunque el propósito real ya declare contexto."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _two_projects(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    memoria_critica = SaveManualMemoryUseCase(unit_of_work).save(
        "contenido sin ninguna palabra en comun con la consulta"
    )
    SetCriticalityUseCase(
        build_sqlite_memory_repository(database_path),
        build_sqlite_decision_repository(database_path),
    ).set(CriticalityTargetKind.MEMORY, memoria_critica.id, Criticality.CRITICO)

    resultado = _use_case(database_path, category_matching_enabled=False).rank(
        "Prepara el contexto de planificacion de Alfa."
    )

    assert resultado == ()
