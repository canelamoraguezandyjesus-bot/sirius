"""Indicación efímera de brevedad dentro de Model Studio (#126)."""

from __future__ import annotations

from sirius.application.studio_brief import MODEL_STUDIO_BRIEF
from sirius.domain.identity import INITIAL_PERSONALITY_INSTRUCTIONS


def test_it_asks_for_one_to_four_sentences() -> None:
    """#126: «respuestas normalmente de una a cuatro frases»."""
    assert "una a cuatro frases" in MODEL_STUDIO_BRIEF


def test_it_says_the_detail_stays_on_screen() -> None:
    """§4.1: resumen oral útil, contenido completo en pantalla."""
    assert "pantalla" in MODEL_STUDIO_BRIEF


def test_it_does_not_authorise_hiding_anything() -> None:
    """Efecto secundario peligroso de pedir brevedad: callarse un riesgo."""
    assert "riesgo" in MODEL_STUDIO_BRIEF
    assert "incertidumbre" in MODEL_STUDIO_BRIEF


def test_it_declares_itself_not_an_identity_change() -> None:
    """#126: «sin alterar la identidad canónica»."""
    assert "No cambia tu identidad" in MODEL_STUDIO_BRIEF


def test_it_never_restates_the_identity() -> None:
    """Es una indicación de extensión, no un segundo perfil de personalidad.

    Si repitiera rasgos, habría dos fuentes de identidad y podrían separarse.
    """
    for trait in ("cercano", "provocador", "ingenioso", "honesto", "crítico"):
        assert trait not in MODEL_STUDIO_BRIEF.lower()
    assert MODEL_STUDIO_BRIEF not in INITIAL_PERSONALITY_INSTRUCTIONS
