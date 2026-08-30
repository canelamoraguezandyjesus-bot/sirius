"""Unit tests for the lexical query treatment ported for ADR-108/ADR-109
(``experiments/adr002/candidates/adr002_a/lexical.py``,
``evidence/adr001-spikes``, PR #117) into
``sirius.adapters.persistence.lexical_query_treatment``. Pure functions, no
SQLite, no FTS5 — the adapter-level behaviour these support is exercised in
``tests/integration/test_rank_relevant_knowledge.py``.
"""

from __future__ import annotations

from sirius.adapters.persistence.lexical_query_treatment import (
    RAIZ_MINIMA,
    VACIAS,
    plegar,
    raiz,
    terminos_significativos,
    tokenizar,
    variantes,
)


def test_plegar_lowercases_and_strips_diacritics() -> None:
    assert plegar("POLÍTICA") == "politica"
    assert plegar("señal") == "senal"


def test_tokenizar_extracts_alphanumeric_runs_folded_in_order() -> None:
    assert tokenizar("¿Qué política de teletrabajo en Alfa?") == (
        "que",
        "politica",
        "de",
        "teletrabajo",
        "en",
        "alfa",
    )


def test_terminos_significativos_drops_vacias_short_tokens_and_duplicates() -> None:
    # "que", "de", "en" are VACIAS (Spanish function words); "a" is both
    # VACIA and shorter than 2 characters; "alfa" repeats and is kept once.
    assert terminos_significativos("¿Qué política de teletrabajo en Alfa? Alfa.") == (
        "politica",
        "teletrabajo",
        "alfa",
    )


def test_terminos_significativos_of_only_stopwords_is_empty() -> None:
    assert terminos_significativos("de la el en") == ()


def test_vacias_is_a_closed_lowercase_ascii_set() -> None:
    assert "de" in VACIAS
    assert "la" in VACIAS
    assert "el" in VACIAS
    # Never a real discriminating word.
    assert "presupuesto" not in VACIAS


def test_raiz_strips_a_flexive_suffix_only_above_raiz_minima() -> None:
    # "reglas" -> base "regl" has 4 chars, exactly RAIZ_MINIMA: stripped.
    assert raiz("reglas") == "regl"
    assert len(raiz("reglas")) >= RAIZ_MINIMA
    # A short word never loses its only distinguishing letters.
    assert raiz("mas") == "mas"


def test_raiz_never_recognizes_a_dictionary_only_a_shape() -> None:
    # "presupuesto" -> "presupuest" (trailing "o"), well above RAIZ_MINIMA.
    assert raiz("presupuesto") == "presupuest"


def test_variantes_always_includes_the_original_term_and_its_root() -> None:
    resultado = variantes("presupuesto")
    assert "presupuesto" in resultado
    assert "presupuest" in resultado


def test_variantes_of_a_short_term_is_just_itself() -> None:
    assert variantes("hoy") == ("hoy",)
