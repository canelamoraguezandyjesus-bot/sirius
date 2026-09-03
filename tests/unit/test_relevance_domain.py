"""Unit tests for the pure B6b relevance ordering rule (SIRIUS-ARQ-0.1 S7.5;
D-11). No fakes, no SQLite — only ``Memory``/``Decision`` value objects and
``RankedKnowledge`` wrappers, mirroring ``test_precedence_domain.py``.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from sirius.domain.criticality import Criticality
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.domain.relevance import (
    KnowledgeKind,
    RankedKnowledge,
    candidate_currently_valid,
    candidate_in_declared_scope,
    category_index_activated,
    category_index_matches_query,
    category_matches_query,
    pide_contexto,
    rank_relevant_knowledge,
    rescue_max_criticality_candidates,
    subject_matches_query,
    truncate_to_hard_limit,
)

_NOW = datetime(2026, 7, 21, tzinfo=UTC)
_PROJECT = 1
_OTHER_PROJECT = 2
_VOCABULARY = frozenset({"trabajo", "personal", "salud"})
#: M19a (ADR-127, incidencia #512): el mismo vocabulario que
#: ``composition_root._CRITICALITY_VOCABULARY`` — repetido aquí, no
#: importado, porque este módulo prueba el dominio puro sin depender de la
#: raíz de composición, igual que ``_VOCABULARY`` de arriba repite (no
#: importa) el vocabulario de categoría.
_CRITICALITY_VOCABULARY = frozenset(
    {"esencial", "restriccion", "critica", "obligatoria", "imprescindible"}
)


def _memory(
    memory_id: int,
    status: MemoryStatus = MemoryStatus.CURRENT,
    *,
    project_id: int | None = _PROJECT,
    updated_at: datetime = _NOW,
) -> Memory:
    revision = MemoryRevision(
        id=memory_id,
        memory_id=memory_id,
        version=1,
        content="contenido",
        origin="manual",
        source_event_id=None,
        created_at=updated_at,
    )
    return Memory(
        id=memory_id,
        status=status,
        current_revision=revision,
        created_at=updated_at,
        updated_at=updated_at,
        subject_key=None,
        project_id=project_id,
    )


def _decision(
    decision_id: int,
    status: DecisionStatus = DecisionStatus.APPROVED,
    *,
    subject: str = "asunto de la decisión",
    project_id: int = _PROJECT,
    updated_at: datetime = _NOW,
) -> Decision:
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content="contenido",
        source_event_id=None,
        created_at=updated_at,
    )
    return Decision(
        id=decision_id,
        subject=subject,
        project_id=project_id,
        status=status,
        current_revision=revision,
        created_at=updated_at,
        updated_at=updated_at,
    )


def _ranked_memory(
    memory: Memory,
    *,
    project_matches_active: bool = False,
    fts_match: bool = False,
    category_match: bool = False,
    criticality_match: bool = False,
    seeded: bool = False,
) -> RankedKnowledge:
    return RankedKnowledge(
        kind=KnowledgeKind.MEMORY,
        item=memory,
        subject_matches_query=False,
        project_matches_active=project_matches_active,
        fts_match=fts_match,
        category_match=category_match,
        criticality_match=criticality_match,
        seeded=seeded,
    )


def _ranked_decision(
    decision: Decision,
    *,
    subject_matches_query: bool = False,
    project_matches_active: bool = False,
    fts_match: bool = False,
    category_match: bool = False,
    criticality_match: bool = False,
    seeded: bool = False,
) -> RankedKnowledge:
    return RankedKnowledge(
        kind=KnowledgeKind.DECISION,
        item=decision,
        subject_matches_query=subject_matches_query,
        project_matches_active=project_matches_active,
        fts_match=fts_match,
        category_match=category_match,
        criticality_match=criticality_match,
        seeded=seeded,
    )


# --- subject_matches_query: plain, case-insensitive, bidirectional containment. ---


def test_subject_matches_query_when_subject_is_contained_in_the_query() -> None:
    assert subject_matches_query(
        "arquitectura de datos", "hablemos de la ARQUITECTURA DE DATOS hoy"
    )


def test_subject_matches_query_when_query_is_contained_in_the_subject() -> None:
    assert subject_matches_query("arquitectura de datos y almacenamiento", "arquitectura de datos")


def test_subject_matches_query_is_false_for_unrelated_text() -> None:
    assert not subject_matches_query("arquitectura de datos", "receta de cocina")


@pytest.mark.parametrize(
    "subject,query", [("", "algo"), ("algo", ""), ("   ", "algo"), ("algo", "   ")]
)
def test_subject_matches_query_is_false_when_either_side_is_blank(subject: str, query: str) -> None:
    assert not subject_matches_query(subject, query)


# --- Invariante: subject_matches_query nunca aplica a un recuerdo (S7.5: "tipo DECISIÓN"). ---


def test_a_memory_can_never_be_constructed_with_subject_matches_query_true() -> None:
    with pytest.raises(ValueError, match="only ever applies to a decision"):
        RankedKnowledge(
            kind=KnowledgeKind.MEMORY,
            item=_memory(1),
            subject_matches_query=True,
            project_matches_active=False,
            fts_match=False,
        )


# --- Criterio 1: decisión vigente de asunto coincidente por encima de recuerdo general. ---


def test_a_subject_matching_decision_outranks_a_general_memory() -> None:
    memory = _ranked_memory(_memory(1, updated_at=_NOW + timedelta(days=1)), fts_match=True)
    decision = _ranked_decision(_decision(10), subject_matches_query=True)

    result = rank_relevant_knowledge([memory, decision])

    assert result == (decision, memory)


# --- Criterio 2: proyecto activo por encima de otro proyecto (resto empatado). ---


def test_active_project_membership_outranks_another_project() -> None:
    same_project = _ranked_decision(
        _decision(1, project_id=_PROJECT), fts_match=True, project_matches_active=True
    )
    other_project = _ranked_decision(
        _decision(2, project_id=_OTHER_PROJECT), fts_match=True, project_matches_active=False
    )

    result = rank_relevant_knowledge([other_project, same_project])

    assert result == (same_project, other_project)


# --- Criterio 3: coincidencia FTS5 por encima de no-coincidencia (resto empatado). ---


def test_an_fts_match_outranks_a_non_match() -> None:
    matching = _ranked_decision(_decision(1), subject_matches_query=True, fts_match=True)
    non_matching = _ranked_decision(_decision(2), subject_matches_query=True, fts_match=False)

    result = rank_relevant_knowledge([non_matching, matching])

    assert result == (matching, non_matching)


# --- Criterio 4: más reciente por encima de más antiguo (resto empatado). ---


def test_more_recent_recency_outranks_older_recency() -> None:
    older = _ranked_memory(_memory(1, updated_at=_NOW), fts_match=True)
    newer = _ranked_memory(_memory(2, updated_at=_NOW + timedelta(days=1)), fts_match=True)

    result = rank_relevant_knowledge([older, newer])

    assert result == (newer, older)


# --- Desempate final: estable y determinista por el id sintético de knowledge_fts. ---


def test_tie_break_is_stable_and_deterministic_by_synthetic_id() -> None:
    first = _ranked_memory(_memory(1), fts_match=True)
    second = _ranked_memory(_memory(2), fts_match=True)

    result_a = rank_relevant_knowledge([second, first])
    result_b = rank_relevant_knowledge([first, second])

    assert result_a == (first, second)
    assert result_b == (first, second)


def test_tie_break_never_collides_a_memory_and_a_decision_of_the_same_id() -> None:
    memory = _ranked_memory(_memory(5), fts_match=True)
    decision = _ranked_decision(_decision(5), fts_match=True)

    result = rank_relevant_knowledge([decision, memory])

    # memory_id * 2 = 10 (even) sorts before decision_id * 2 + 1 = 11 (odd).
    assert result == (memory, decision)


# --- Filtro (no resta): elementos no vigentes se excluyen antes de ordenar. ---


@pytest.mark.parametrize("status", [MemoryStatus.ARCHIVED, MemoryStatus.DELETED])
def test_a_non_current_memory_is_excluded_even_with_a_matching_fts_hit(
    status: MemoryStatus,
) -> None:
    candidate = _ranked_memory(_memory(1, status), fts_match=True)

    assert rank_relevant_knowledge([candidate]) == ()


@pytest.mark.parametrize(
    "status", [DecisionStatus.PROPOSED, DecisionStatus.SUPERSEDED, DecisionStatus.ARCHIVED]
)
def test_a_non_approved_decision_is_excluded_even_with_a_matching_subject(
    status: DecisionStatus,
) -> None:
    candidate = _ranked_decision(_decision(1, status), subject_matches_query=True, fts_match=True)

    assert rank_relevant_knowledge([candidate]) == ()


# --- Filtro (no resta): elemento general no relacionado se excluye antes de ordenar. ---


def test_an_unrelated_current_item_is_excluded_even_though_it_is_vigente() -> None:
    unrelated = _ranked_memory(_memory(1), fts_match=False)
    related = _ranked_decision(_decision(2), subject_matches_query=True)

    result = rank_relevant_knowledge([unrelated, related])

    assert result == (related,)


def test_an_empty_candidate_list_ranks_to_nothing() -> None:
    assert rank_relevant_knowledge([]) == ()


# --- M9 (§6.2): category_matches_query, la clasificación determinista de la ---
# --- consulta contra el vocabulario cerrado — sin modelo, sin puerto. ---


def test_category_matches_query_when_the_single_activated_category_equals_the_candidate() -> None:
    assert category_matches_query("trabajo", "hablemos de trabajo hoy", _VOCABULARY)


def test_category_matches_query_is_false_when_the_candidate_has_no_category_yet() -> None:
    assert not category_matches_query(None, "hablemos de trabajo hoy", _VOCABULARY)


def test_category_matches_query_is_false_when_the_query_activates_no_category() -> None:
    assert not category_matches_query("trabajo", "receta de cocina", _VOCABULARY)


def test_category_matches_query_is_false_when_the_activated_category_differs() -> None:
    assert not category_matches_query("salud", "hablemos de trabajo hoy", _VOCABULARY)


def test_category_matches_query_is_false_when_the_query_activates_more_than_one_category() -> None:
    assert not category_matches_query("trabajo", "trabajo y salud a la vez", _VOCABULARY)


@pytest.mark.parametrize("query_text", ["", "   "])
def test_category_matches_query_is_false_for_a_blank_query(query_text: str) -> None:
    assert not category_matches_query("trabajo", query_text, _VOCABULARY)


def test_category_matches_query_is_case_insensitive_against_the_persisted_category() -> None:
    # The persisted category (SetCategoryUseCase accepts any string, D7 punto
    # 3) may differ in capitalization from the closed vocabulary's own term.
    assert category_matches_query("Trabajo", "hablemos de Trabajo hoy", _VOCABULARY)


# --- M14 (§11.2/§11.5, incidencia #486): category_index_matches_query, la ---
# --- activación múltiple del índice de categoría buscable tras la puerta, ---
# --- réplica de activa_categoria_buscable (ADR-113). ---


def test_category_index_matches_query_activates_for_two_vocabulary_terms_at_once() -> None:
    # A diferencia de category_matches_query (que exige activación única),
    # una consulta con dos o más términos del vocabulario sigue activando la
    # categoría para toda identidad ya clasificada.
    assert category_index_matches_query("trabajo", "trabajo y salud a la vez", _VOCABULARY)


def test_category_index_matches_query_does_not_require_the_category_to_equal_a_term() -> None:
    # activa_categoria_buscable ignora por completo el valor de la categoría:
    # el índice guarda el vocabulario entero como el mismo contenido para
    # toda identidad no ordinaria.
    assert category_index_matches_query("personal", "hablemos de trabajo hoy", _VOCABULARY)


def test_category_index_matches_query_is_false_when_the_candidate_has_no_category_yet() -> None:
    assert not category_index_matches_query(None, "trabajo y salud a la vez", _VOCABULARY)


def test_category_index_matches_query_is_false_when_the_query_activates_no_vocabulary_term() -> (
    None
):
    assert not category_index_matches_query("trabajo", "receta de cocina", _VOCABULARY)


@pytest.mark.parametrize("query_text", ["", "   "])
def test_category_index_matches_query_is_false_for_a_blank_query(query_text: str) -> None:
    assert not category_index_matches_query("trabajo", query_text, _VOCABULARY)


def test_category_index_matches_query_is_case_insensitive_against_the_vocabulary() -> None:
    assert category_index_matches_query("trabajo", "TRABAJO y SALUD a la vez", _VOCABULARY)


# --- M14 (§11.2/§11.5, incidencia #486): candidate_in_declared_scope, la ---
# --- restricción de ámbito sobre esa activación, réplica de ---
# --- _en_ambito_declarado (ADR-114). ---


def test_candidate_in_declared_scope_admits_everything_without_an_active_project() -> None:
    assert candidate_in_declared_scope(_OTHER_PROJECT, active_project_id=None)
    assert candidate_in_declared_scope(None, active_project_id=None)


def test_candidate_in_declared_scope_admits_a_candidate_of_the_active_project() -> None:
    assert candidate_in_declared_scope(_PROJECT, active_project_id=_PROJECT)


def test_candidate_in_declared_scope_rejects_a_candidate_of_a_different_project() -> None:
    assert not candidate_in_declared_scope(_OTHER_PROJECT, active_project_id=_PROJECT)


def test_candidate_in_declared_scope_admits_a_global_candidate_with_an_active_project() -> None:
    assert candidate_in_declared_scope(None, active_project_id=_PROJECT)


# --- Criterio 3.5 (M9, §6.2): category_match entra después de fts_match y ---
# --- antes de la recencia en la tupla de orden. ---


def test_a_category_match_outranks_a_non_match_when_everything_else_ties() -> None:
    matching = _ranked_decision(_decision(1), fts_match=True, category_match=True)
    non_matching = _ranked_decision(_decision(2), fts_match=True, category_match=False)

    result = rank_relevant_knowledge([non_matching, matching])

    assert result == (matching, non_matching)


def test_active_project_membership_still_outranks_a_category_match() -> None:
    other_project_with_category = _ranked_decision(
        _decision(1, project_id=_OTHER_PROJECT),
        fts_match=True,
        project_matches_active=False,
        category_match=True,
    )
    active_project_without_category = _ranked_decision(
        _decision(2, project_id=_PROJECT),
        fts_match=True,
        project_matches_active=True,
        category_match=False,
    )

    result = rank_relevant_knowledge([other_project_with_category, active_project_without_category])

    assert result == (active_project_without_category, other_project_with_category)


def test_a_category_match_still_outranks_a_more_recent_non_match() -> None:
    older_with_category = _ranked_memory(
        _memory(1, updated_at=_NOW), fts_match=True, category_match=True
    )
    newer_without_category = _ranked_memory(
        _memory(2, updated_at=_NOW + timedelta(days=1)), fts_match=True, category_match=False
    )

    result = rank_relevant_knowledge([newer_without_category, older_with_category])

    assert result == (older_with_category, newer_without_category)


# --- Criterio 3.6 (M9, §6.2): category_match también amplía "relacionado" ---
# --- (is_related), no solo el orden — un candidato puede encontrarse solo ---
# --- por su categoría, sin asunto ni FTS5. ---


def test_a_category_match_alone_makes_an_otherwise_unrelated_candidate_related() -> None:
    candidate = _ranked_memory(_memory(1), fts_match=False, category_match=True)

    assert rank_relevant_knowledge([candidate]) == (candidate,)


def test_a_category_match_alone_is_not_enough_when_the_gate_is_closed() -> None:
    # category_match is always False for every real candidate while D7
    # punto 6's activation gate stays closed (application layer) — this
    # documents the domain side of that: without any of the three signals,
    # a candidate stays excluded exactly like before M9.
    candidate = _ranked_memory(_memory(1), fts_match=False, category_match=False)

    assert rank_relevant_knowledge([candidate]) == ()


# --- M19a (ADR-127, incidencia #512): the criticality index's activation ---
# --- rule — category_index_activated reused as-is with the criticality ---
# --- vocabulary instead of a new function (issue #512, item b). ---


def test_criticality_index_activates_for_a_query_naming_two_criticality_terms_at_once() -> None:
    # incidencia #512: "Dame todas las restricciones esenciales que debo
    # respetar" — el caso real del banco (B04-CA-31) que hoy no activa
    # ningún índice porque el vocabulario de categoría es temático.
    assert category_index_activated(
        "Dame todas las restricciones esenciales que debo respetar.",
        _CRITICALITY_VOCABULARY,
    )


def test_criticality_index_activates_for_a_single_criticality_term() -> None:
    # incidencia #512: "¿Qué restricciones de transporte tengo?" (B04-CA-02).
    assert category_index_activated(
        "¿Qué restricciones de transporte tengo?", _CRITICALITY_VOCABULARY
    )


def test_criticality_index_does_not_activate_for_a_query_naming_no_criticality_term() -> None:
    # incidencia #512: "Prepara el contexto de planificación de Alfa"
    # (B04-CA-34) — la siembra (M20), no el índice de este encargo.
    assert not category_index_activated(
        "Prepara el contexto de planificación de Alfa.", _CRITICALITY_VOCABULARY
    )


def test_criticality_index_activation_is_plain_substring_without_diacritic_folding() -> None:
    # Limitación conocida y compartida con el índice de categoría (issue
    # #512, item b): la coincidencia es subcadena tal cual, sin normalizar
    # tildes — "crítica" con tilde NO activa el término "critica" del
    # vocabulario. No se arregla aquí.
    assert not category_index_activated("es una decisión crítica", _CRITICALITY_VOCABULARY)
    assert category_index_activated("es una decision critica", _CRITICALITY_VOCABULARY)


# --- M19a (ADR-127, incidencia #512): criticality_match, the fifth ---
# --- structural signal, parallel to category_match — enters _sort_key ---
# --- right after it and also widens is_related. ---


def test_a_criticality_match_outranks_a_non_match_when_everything_else_ties() -> None:
    matching = _ranked_decision(_decision(1), fts_match=True, criticality_match=True)
    non_matching = _ranked_decision(_decision(2), fts_match=True, criticality_match=False)

    result = rank_relevant_knowledge([non_matching, matching])

    assert result == (matching, non_matching)


def test_a_category_match_still_outranks_a_criticality_match() -> None:
    # criticality_match sits right after category_match in _sort_key: weaker
    # than it, exactly like category_match is weaker than an FTS5 hit.
    with_category = _ranked_decision(
        _decision(1), fts_match=True, category_match=True, criticality_match=False
    )
    with_criticality = _ranked_decision(
        _decision(2), fts_match=True, category_match=False, criticality_match=True
    )

    result = rank_relevant_knowledge([with_criticality, with_category])

    assert result == (with_category, with_criticality)


def test_active_project_membership_still_outranks_a_criticality_match() -> None:
    other_project_with_criticality = _ranked_decision(
        _decision(1, project_id=_OTHER_PROJECT),
        fts_match=True,
        project_matches_active=False,
        criticality_match=True,
    )
    active_project_without_criticality = _ranked_decision(
        _decision(2, project_id=_PROJECT),
        fts_match=True,
        project_matches_active=True,
        criticality_match=False,
    )

    result = rank_relevant_knowledge(
        [other_project_with_criticality, active_project_without_criticality]
    )

    assert result == (active_project_without_criticality, other_project_with_criticality)


def test_a_criticality_match_still_outranks_a_more_recent_non_match() -> None:
    older_with_criticality = _ranked_memory(
        _memory(1, updated_at=_NOW), fts_match=True, criticality_match=True
    )
    newer_without_criticality = _ranked_memory(
        _memory(2, updated_at=_NOW + timedelta(days=1)), fts_match=True, criticality_match=False
    )

    result = rank_relevant_knowledge([newer_without_criticality, older_with_criticality])

    assert result == (older_with_criticality, newer_without_criticality)


def test_a_criticality_match_alone_makes_an_otherwise_unrelated_candidate_related() -> None:
    candidate = _ranked_memory(_memory(1), fts_match=False, criticality_match=True)

    assert rank_relevant_knowledge([candidate]) == (candidate,)


def test_a_criticality_match_alone_is_not_enough_when_the_gate_is_closed() -> None:
    # criticality_match is always False for every real candidate while D7
    # punto 6's activation gate stays closed (application layer), exactly
    # like category_match — this documents the domain side of that.
    candidate = _ranked_memory(_memory(1), fts_match=False, criticality_match=False)

    assert rank_relevant_knowledge([candidate]) == ()


# --- M20 (ADR-129, incidencia #516): pide_contexto — the request's own ---
# --- proposito, never a guess over the query text, replica of the ---
# --- harness's _pide_contexto (staged_engine_category_and_relevance.py: ---
# --- 403-409). ---


def test_pide_contexto_is_true_when_proposito_names_context() -> None:
    assert pide_contexto("ensamblar_contexto_b05")


def test_pide_contexto_is_true_for_the_real_production_purpose() -> None:
    # M16 (ADR-124): la única llamada real a rank() declara este propósito,
    # que contiene la subcadena "contexto" a propósito.
    assert pide_contexto("recuperacion de contexto relevante (B6b)")


def test_pide_contexto_is_case_insensitive() -> None:
    assert pide_contexto("ENSAMBLAR EL CONTEXTO")
    assert pide_contexto("Contexto")


def test_pide_contexto_is_false_without_the_word_contexto() -> None:
    assert not pide_contexto("consultar")
    assert not pide_contexto("")


# --- M20 (ADR-129, incidencia #516): seeded, the sixth structural signal, --
# --- parallel to category_match/criticality_match — enters _sort_key -----
# --- right after criticality_match and also widens is_related. -----------


def test_a_seeded_candidate_outranks_a_non_seeded_one_when_everything_else_ties() -> None:
    seeded = _ranked_decision(_decision(1), fts_match=True, seeded=True)
    non_seeded = _ranked_decision(_decision(2), fts_match=True, seeded=False)

    result = rank_relevant_knowledge([non_seeded, seeded])

    assert result == (seeded, non_seeded)


def test_a_criticality_match_still_outranks_seeded() -> None:
    # seeded sits right after criticality_match in _sort_key: weaker than
    # it, exactly like criticality_match is weaker than category_match.
    with_criticality = _ranked_decision(
        _decision(1), fts_match=True, criticality_match=True, seeded=False
    )
    only_seeded = _ranked_decision(
        _decision(2), fts_match=True, criticality_match=False, seeded=True
    )

    result = rank_relevant_knowledge([only_seeded, with_criticality])

    assert result == (with_criticality, only_seeded)


def test_active_project_membership_still_outranks_seeded() -> None:
    other_project_seeded = _ranked_decision(
        _decision(1, project_id=_OTHER_PROJECT),
        fts_match=True,
        project_matches_active=False,
        seeded=True,
    )
    active_project_not_seeded = _ranked_decision(
        _decision(2, project_id=_PROJECT),
        fts_match=True,
        project_matches_active=True,
        seeded=False,
    )

    result = rank_relevant_knowledge([other_project_seeded, active_project_not_seeded])

    assert result == (active_project_not_seeded, other_project_seeded)


def test_seeded_still_outranks_a_more_recent_non_seeded_candidate() -> None:
    older_seeded = _ranked_memory(_memory(1, updated_at=_NOW), fts_match=True, seeded=True)
    newer_not_seeded = _ranked_memory(
        _memory(2, updated_at=_NOW + timedelta(days=1)), fts_match=True, seeded=False
    )

    result = rank_relevant_knowledge([newer_not_seeded, older_seeded])

    assert result == (older_seeded, newer_not_seeded)


def test_seeded_alone_makes_an_otherwise_unrelated_candidate_related() -> None:
    candidate = _ranked_memory(_memory(1), fts_match=False, seeded=True)

    assert rank_relevant_knowledge([candidate]) == (candidate,)


def test_seeded_alone_is_not_enough_when_the_gate_is_closed() -> None:
    # seeded is always False for every real candidate while D7 punto 6's
    # activation gate stays closed (application layer) — this documents the
    # domain side of that, exactly like category_match/criticality_match.
    candidate = _ranked_memory(_memory(1), fts_match=False, seeded=False)

    assert rank_relevant_knowledge([candidate]) == ()


# --- M15 (§11.2/§11.5, incidencia #490): candidate_currently_valid, the ---
# --- temporal-applicability half of G8, replica of vigente_en_tiempo_ ---
# --- objetivo (ADR-115). ---

_TARGET_TIME = _NOW


def test_candidate_currently_valid_with_no_axes_declared_at_all() -> None:
    # SIN_EJES: every real Memory/Decision today (no valid_from/valid_to
    # persisted yet) always passes this — the gate runs, faithfully, but
    # degrades to always True until a schema migration adds the axis.
    assert candidate_currently_valid(None, None, target_time=_TARGET_TIME)


def test_candidate_currently_valid_rejects_a_valid_from_after_the_target_time() -> None:
    assert not candidate_currently_valid(
        _TARGET_TIME + timedelta(days=1), None, target_time=_TARGET_TIME
    )


def test_candidate_currently_valid_admits_a_valid_from_at_or_before_the_target_time() -> None:
    assert candidate_currently_valid(_TARGET_TIME, None, target_time=_TARGET_TIME)
    assert candidate_currently_valid(
        _TARGET_TIME - timedelta(days=1), None, target_time=_TARGET_TIME
    )


def test_candidate_currently_valid_rejects_a_valid_to_at_or_before_the_target_time() -> None:
    assert not candidate_currently_valid(None, _TARGET_TIME, target_time=_TARGET_TIME)
    assert not candidate_currently_valid(
        None, _TARGET_TIME - timedelta(days=1), target_time=_TARGET_TIME
    )


def test_candidate_currently_valid_admits_a_valid_to_after_the_target_time() -> None:
    assert candidate_currently_valid(
        None, _TARGET_TIME + timedelta(days=1), target_time=_TARGET_TIME
    )


# --- M15 (§11.2/§11.5, incidencia #490): truncate_to_hard_limit, the hard- ---
# --- limit half of G12, replica of truncar_por_limite_duro (ADR-115). Since ---
# --- M19b (ADR-128, incidencia #514) the priority is caller-supplied -------
# --- (``protection_rank``) instead of a fixed ``max_criticality_category`` -
# --- these tests exercise it with the same criticality-based rank ---------
# --- ContextBuilder itself builds for the open-gate path: CRITICO (0) -----
# --- outranks IMPORTANTE (1), which outranks ordinary (2) — fixed in ------
# --- this incidencia's review round 2 after a first, boolean version ------
# --- (is_protected) could only ever tell "protected" from "ordinary", -----
# --- never CRITICO from IMPORTANTE. ----------------------------------------


def _is_not_ordinary(candidate: RankedKnowledge) -> bool:
    """The M19b (ADR-128) predicate ``ContextBuilder`` builds for
    ``rescue_max_criticality_candidates`` (RF-25/RF-26): "no ordinario" is
    ``criticality is not None`` (CRITICO or IMPORTANTE), never a category
    comparison. RF-25/RF-26 only ever need "protected or not" — unlike G12
    below, this stays a boolean."""
    return candidate.item.criticality is not None


def _criticality_rank(candidate: RankedKnowledge) -> int:
    """The M19b (ADR-128, review round 2) priority ``ContextBuilder`` builds
    for ``truncate_to_hard_limit`` (G12): CRITICO (0) outranks IMPORTANTE
    (1), which outranks every ordinary candidate (2) — mirrors
    ``aplicar_g12``'s own ``-ORDEN_DE_CRITICIDAD.index(...)`` sort key
    (``src/sirius/domain/staged_engine_gates.py:333``)."""
    criticality = candidate.item.criticality
    if criticality is Criticality.CRITICO:
        return 0
    if criticality is Criticality.IMPORTANTE:
        return 1
    return 2


def test_truncate_to_hard_limit_keeps_everything_under_the_limit() -> None:
    ordinary = _ranked_memory(_memory(1))
    critical = _ranked_memory(dataclasses.replace(_memory(2), criticality=Criticality.CRITICO))

    result = truncate_to_hard_limit(
        [ordinary, critical], hard_limit=5, protection_rank=_criticality_rank
    )

    assert result == (ordinary, critical)


def test_truncate_to_hard_limit_keeps_the_protected_candidate_over_an_ordinary_one() -> None:
    ordinary = _ranked_memory(_memory(1))
    critical = _ranked_memory(dataclasses.replace(_memory(2), criticality=Criticality.CRITICO))

    result = truncate_to_hard_limit(
        [ordinary, critical], hard_limit=1, protection_rank=_criticality_rank
    )

    assert result == (critical,)


def test_truncate_to_hard_limit_prioritises_critico_over_importante_even_when_importante_arrives_first() -> (  # noqa: E501
    None
):
    """CODEX-001 (revisión de la incidencia #514, PR #515): con el límite
    duro atado y un IMPORTANTE precedente a un CRITICO, un ``is_protected``
    booleano agrupaba ambos como igualmente protegidos y conservaba el
    orden de llegada, devolviendo el IMPORTANTE. G12 ordena por criticidad
    (``docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:1737-1742``):
    CRITICO debe desplazar a IMPORTANTE aunque este llegue antes."""
    importante_first = _ranked_memory(
        dataclasses.replace(_memory(1), criticality=Criticality.IMPORTANTE)
    )
    critico_second = _ranked_memory(
        dataclasses.replace(_memory(2), criticality=Criticality.CRITICO)
    )

    result = truncate_to_hard_limit(
        [importante_first, critico_second], hard_limit=1, protection_rank=_criticality_rank
    )

    assert result == (critico_second,)


def test_truncate_to_hard_limit_preserves_original_relative_order_of_survivors() -> None:
    # G12 decides WHO survives (criticidad-first); it never reorders the
    # result into that criticidad-first order — same "who, not how it's
    # displayed" contract the candado/filter union already relies on.
    first_ordinary = _ranked_memory(_memory(1))
    critical = _ranked_memory(dataclasses.replace(_memory(2), criticality=Criticality.CRITICO))
    second_ordinary = _ranked_memory(_memory(3))

    result = truncate_to_hard_limit(
        [first_ordinary, critical, second_ordinary],
        hard_limit=3,
        protection_rank=_criticality_rank,
    )

    assert result == (first_ordinary, critical, second_ordinary)


def test_truncate_to_hard_limit_without_any_protected_candidate() -> None:
    first = _ranked_memory(dataclasses.replace(_memory(1), criticality=Criticality.CRITICO))
    second = _ranked_memory(_memory(2))

    result = truncate_to_hard_limit([first, second], hard_limit=1, protection_rank=lambda _: 0)

    # With every candidate ranked identically, the first hard_limit
    # candidates in their original order survive — same stable-sort
    # guarantee as before.
    assert result == (first,)


# --- M15 (RF-25/RF-26, §11.2/§11.5, incidencia #490): rescue_max_criticality ---
# --- _candidates, replica of aplicar_regla_de_criticas_original (ADR-112/113). ---
# --- Since M19b (ADR-128, incidencia #514), "máxima criticidad" is decided ---
# --- by the caller-supplied ``is_protected`` predicate; ContextBuilder's ----
# --- own predicate is ``criticality is not None`` (CRITICO or IMPORTANTE), -
# --- exactly what the laboratory's own ``restriccion`` tag protected -------
# --- (tests/acceptance/staged_engine_category_and_relevance.py:472-513). ---


def test_rf25_rescues_a_discarded_critico_when_the_filter_kept_something() -> None:
    kept = _ranked_memory(_memory(1))
    discarded_critico = _ranked_memory(
        dataclasses.replace(_memory(2), criticality=Criticality.CRITICO)
    )

    rescued = rescue_max_criticality_candidates(
        [kept, discarded_critico], [kept], is_protected=_is_not_ordinary
    )

    assert rescued == (discarded_critico,)


def test_rf25_rescues_a_discarded_importante_when_the_filter_kept_something() -> None:
    """RF-25 protects both non-ordinary levels alike, not just CRITICO —
    exactly what the mutation below (narrowing the predicate to CRITICO
    only) is meant to catch."""
    kept = _ranked_memory(_memory(1))
    discarded_importante = _ranked_memory(
        dataclasses.replace(_memory(2), criticality=Criticality.IMPORTANTE)
    )

    rescued = rescue_max_criticality_candidates(
        [kept, discarded_importante], [kept], is_protected=_is_not_ordinary
    )

    assert rescued == (discarded_importante,)


def test_rf25_rescue_mutation_excluding_importante_is_caught_by_the_importante_test() -> None:
    """Prueba por mutación (ADR-001): un predicado que solo protege CRITICO
    (excluyendo IMPORTANTE, la mutación que sugiere la incidencia #514) deja
    de rescatar un IMPORTANTE descartado — confirma que
    ``test_rf25_rescues_a_discarded_importante_when_the_filter_kept_something``
    detecta esa ausencia de protección."""
    kept = _ranked_memory(_memory(1))
    discarded_importante = _ranked_memory(
        dataclasses.replace(_memory(2), criticality=Criticality.IMPORTANTE)
    )

    def only_critico(candidate: RankedKnowledge) -> bool:
        return candidate.item.criticality is Criticality.CRITICO

    rescued = rescue_max_criticality_candidates(
        [kept, discarded_importante], [kept], is_protected=only_critico
    )

    assert rescued == ()


def test_rf26_does_not_rescue_when_the_filter_conserved_nothing_at_all() -> None:
    discarded_critico = _ranked_memory(
        dataclasses.replace(_memory(1), criticality=Criticality.CRITICO)
    )

    rescued = rescue_max_criticality_candidates(
        [discarded_critico], [], is_protected=_is_not_ordinary
    )

    assert rescued == ()


def test_rescue_never_rescues_an_ordinary_candidate_even_with_the_max_criticality_category() -> (
    None
):
    """An ordinary candidate (``criticality is None``) is never rescued by
    the M19b predicate even if it still carries the thematic
    max-criticality category (``"salud"``, ADR-116) — that category no
    longer decides anything on the open-gate path."""
    kept = _ranked_memory(_memory(1))
    discarded_ordinary = _ranked_memory(dataclasses.replace(_memory(2), category="salud"))

    rescued = rescue_max_criticality_candidates(
        [kept, discarded_ordinary], [kept], is_protected=_is_not_ordinary
    )

    assert rescued == ()


def test_rescue_never_rescues_anything_when_nothing_is_protected() -> None:
    kept = _ranked_memory(_memory(1))
    discarded_critico = _ranked_memory(
        dataclasses.replace(_memory(2), criticality=Criticality.CRITICO)
    )

    rescued = rescue_max_criticality_candidates(
        [kept, discarded_critico], [kept], is_protected=lambda _: False
    )

    assert rescued == ()


# --- M15 (§11.5, incidencia #490): G12's hard-limit exclusion (truncate_to_ ---
# --- hard_limit) runs BEFORE RF-25/RF-26 (rescue_max_criticality_candidates) ---
# --- and is final — a candidate G12 already dropped is never brought back ---
# --- by RF-25, even when the filter conserved something else for the same ---
# --- query (the exact condition that would trigger RF-25 if the candidate ---
# --- were still available). This is a domain-only test of the two pure ---
# --- functions and the union this test reconstructs by hand — it does not ---
# --- call ContextBuilder._apply_relevance_filter, so it cannot catch a ---
# --- wiring regression there that leaks a G12-excluded candidate back into ---
# --- the result through RF-25's rescue path. That composition is exercised ---
# --- for real, through ContextBuilder itself, by ---
# --- test_g12_hard_limit_exclusion_survives_the_real_context_builder_composition ---
# --- in tests/integration/test_context_builder.py. ---


def test_g12_hard_limit_exclusion_is_final_and_is_never_undone_by_rf25_rescue() -> None:
    kept_by_filter = _ranked_memory(
        dataclasses.replace(_memory(1), criticality=Criticality.CRITICO)
    )
    rescuable_by_rf25 = _ranked_memory(
        dataclasses.replace(_memory(2), criticality=Criticality.CRITICO)
    )
    excluded_by_g12 = _ranked_memory(
        dataclasses.replace(_memory(3), criticality=Criticality.CRITICO)
    )

    # G12 first: only two of the three protected candidates fit the hard
    # limit, so `excluded_by_g12` never reaches the filter or RF-25.
    gated = truncate_to_hard_limit(
        [kept_by_filter, rescuable_by_rf25, excluded_by_g12],
        hard_limit=2,
        protection_rank=_criticality_rank,
    )
    assert excluded_by_g12 not in gated

    # The filter conserves `kept_by_filter` and drops `rescuable_by_rf25` —
    # exactly the "conserved something else for this query" condition that
    # makes RF-25 rescue a discarded max-criticality candidate.
    filtered = (kept_by_filter,)
    rescued = rescue_max_criticality_candidates(gated, filtered, is_protected=_is_not_ordinary)
    assert rescued == (rescuable_by_rf25,)

    kept_positions = {id(candidate) for candidate in filtered}
    kept_positions.update(id(candidate) for candidate in rescued)
    kept_positions.update(id(candidate) for candidate in gated if candidate.item.category is None)
    result = tuple(candidate for candidate in gated if id(candidate) in kept_positions)

    assert result == (kept_by_filter, rescuable_by_rf25)
    assert excluded_by_g12 not in result
