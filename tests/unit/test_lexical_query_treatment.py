"""Unit tests for the lexical query treatment ported for issue #455 (see
ADR-109) (``experiments/adr002/candidates/adr002_a/lexical.py``,
``evidence/adr001-spikes``, PR #117) into
``sirius.adapters.persistence.lexical_query_treatment``. Pure functions, no
SQLite, no FTS5 — the adapter-level behaviour these support is exercised in
``tests/integration/test_rank_relevant_knowledge.py``.

``polaridad_negativa``/``condicion_declarada``/``sujeto_estructural`` were
added for issue #457 (ADR-109/ADR-110): the reading ``G11``
(``sirius.domain.staged_engine_gates``) needs before ordering.
"""

from __future__ import annotations

from sirius.adapters.persistence.lexical_query_treatment import (
    RAIZ_MINIMA,
    VACIAS,
    condicion_declarada,
    ordenar_estable,
    plegar,
    polaridad_negativa,
    raiz,
    sujeto_estructural,
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


# -- polaridad_negativa: las cuatro reglas de ADR-109 ------------------------


def test_polaridad_negativa_of_a_plain_affirmation_is_false() -> None:
    assert polaridad_negativa("Se renovo el contrato.") is False


def test_polaridad_negativa_regla_1_sin_como_preposicion_no_niega() -> None:
    # "sin" introduce un complemento ("sin adornos"): sigue siendo afirmativo.
    assert polaridad_negativa("El usuario prefiere tono directo y sin adornos.") is False


def test_polaridad_negativa_regla_2_marcador_tras_subordinante_niega_la_subordinada() -> None:
    # "no" aparece detras de "pero" (subordinante): niega la subordinada, no
    # la principal, que sigue afirmada.
    assert polaridad_negativa("Se renovo, pero no consta desde cuando.") is False


def test_polaridad_negativa_regla_3_marcador_en_la_principal_si_niega() -> None:
    assert polaridad_negativa("No uses opciones de vuelo con escala.") is True


def test_polaridad_negativa_regla_4_lo_citado_tras_dos_puntos_no_cambia_la_principal() -> None:
    # La afirmacion ("la nota esta marcada") va antes de los dos puntos; el
    # imperativo citado despues es lo marcado, no lo afirmado.
    assert polaridad_negativa("Nota marcada por el usuario: no uses esto como memoria.") is False


def test_polaridad_negativa_sin_dos_puntos_el_mismo_imperativo_si_niega() -> None:
    assert polaridad_negativa("No uses esto como memoria.") is True


# -- condicion_declarada ------------------------------------------------------


def test_condicion_declarada_devuelve_el_marcador_no_la_clausula() -> None:
    assert condicion_declarada("Si el cliente lo pide, aplica el descuento.") == "si"


def test_condicion_declarada_sin_marcador_es_none() -> None:
    assert condicion_declarada("Se renovo el contrato.") is None


# -- sujeto_estructural --------------------------------------------------------


def test_sujeto_estructural_prefiere_la_clave_declarada() -> None:
    assert sujeto_estructural("faro-costa", "cualquier texto") == "faro-costa"


def test_sujeto_estructural_sin_clave_usa_el_primer_termino_significativo() -> None:
    assert sujeto_estructural(None, "El presupuesto anual se revisa en enero.") == "presupuesto"


def test_sujeto_estructural_sin_clave_ni_terminos_es_vacio() -> None:
    assert sujeto_estructural(None, "de la el en") == ""


# -- ordenar_estable ------------------------------------------------------------


def test_ordenar_estable_es_determinista_y_sin_duplicados() -> None:
    assert ordenar_estable(["b", "a", "b", "c"]) == ("a", "b", "c")
