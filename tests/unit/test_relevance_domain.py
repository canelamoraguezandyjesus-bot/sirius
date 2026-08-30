"""Unit tests for the pure B6b relevance ordering rule (SIRIUS-ARQ-0.1 S7.5;
D-11). No fakes, no SQLite — only ``Memory``/``Decision`` value objects and
``RankedKnowledge`` wrappers, mirroring ``test_precedence_domain.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.domain.relevance import (
    KnowledgeKind,
    RankedKnowledge,
    category_matches_query,
    rank_relevant_knowledge,
    subject_matches_query,
)

_NOW = datetime(2026, 7, 21, tzinfo=UTC)
_PROJECT = 1
_OTHER_PROJECT = 2
_VOCABULARY = frozenset({"trabajo", "personal", "salud"})


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
) -> RankedKnowledge:
    return RankedKnowledge(
        kind=KnowledgeKind.MEMORY,
        item=memory,
        subject_matches_query=False,
        project_matches_active=project_matches_active,
        fts_match=fts_match,
        category_match=category_match,
    )


def _ranked_decision(
    decision: Decision,
    *,
    subject_matches_query: bool = False,
    project_matches_active: bool = False,
    fts_match: bool = False,
    category_match: bool = False,
) -> RankedKnowledge:
    return RankedKnowledge(
        kind=KnowledgeKind.DECISION,
        item=decision,
        subject_matches_query=subject_matches_query,
        project_matches_active=project_matches_active,
        fts_match=fts_match,
        category_match=category_match,
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
