"""Transformación determinista del texto para leerlo en voz alta."""

from __future__ import annotations

import pytest

from sirius.application.prepare_speech_text import (
    CODE_BLOCK_SPOKEN_AS,
    LINK_SPOKEN_AS,
    prepare_speech_text,
)


def test_plain_text_passes_through_unchanged() -> None:
    """Lo que Sirius dijo es lo que se oye: aquí no reescribe nadie."""
    assert prepare_speech_text("Monta el Uno y carga el Blink.") == (
        "Monta el Uno y carga el Blink."
    )


def test_it_is_deterministic() -> None:
    """Sin modelo por medio: el mismo texto da siempre el mismo resultado."""
    source = "**Primero** el `led`, luego el servo.\n\nY nada más."

    assert prepare_speech_text(source) == prepare_speech_text(source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("**negrita**", "negrita"),
        ("*cursiva*", "cursiva"),
        ("***las dos***", "las dos"),
        ("_subrayado_", "subrayado"),
        ("`monospace`", "monospace"),
        ("# Un título", "Un título"),
        ("### Otro título", "Otro título"),
        ("> una cita", "una cita"),
        ("- un punto", "un punto"),
        ("* otro punto", "otro punto"),
    ],
)
def test_markdown_marks_are_not_pronounced(source: str, expected: str) -> None:
    assert prepare_speech_text(source) == expected


def test_a_code_block_is_announced_not_read_aloud() -> None:
    """Leer código carácter a carácter es inservible al grabar."""
    spoken = prepare_speech_text("Prueba esto:\n\n```python\nprint('hola')\n```\n\nY me cuentas.")

    assert "print" not in spoken
    assert CODE_BLOCK_SPOKEN_AS in spoken
    assert "Y me cuentas" in spoken


def test_links_are_not_spelled_out() -> None:
    spoken = prepare_speech_text("Mira https://ejemplo.test/una/ruta/larga para verlo.")

    assert "https" not in spoken
    assert LINK_SPOKEN_AS in spoken


def test_a_markdown_link_keeps_its_words() -> None:
    spoken = prepare_speech_text("Mira [la documentación](https://ejemplo.test/doc).")

    assert "la documentación" in spoken
    assert "ejemplo.test" not in spoken


def test_paragraph_breaks_become_pauses() -> None:
    spoken = prepare_speech_text("Primero esto.\n\nDespués lo otro.")

    assert "\n" not in spoken
    assert "Primero esto" in spoken
    assert "Después lo otro" in spoken


def test_empty_or_blank_text_says_nothing() -> None:
    assert prepare_speech_text("") == ""
    assert prepare_speech_text("   \n\n  ") == ""


def test_a_response_that_is_only_code_leaves_nothing_worth_saying() -> None:
    """No es un fallo: el contenido ya está en pantalla."""
    spoken = prepare_speech_text("```\nls -la\n```")

    assert spoken in ("", CODE_BLOCK_SPOKEN_AS)


def test_a_horizontal_rule_disappears() -> None:
    spoken = prepare_speech_text("Antes.\n\n---\n\nDespués.")

    assert "---" not in spoken
    assert "Antes" in spoken
    assert "Después" in spoken


def test_no_double_punctuation_is_left_behind() -> None:
    spoken = prepare_speech_text("Una frase.\n\nOtra frase.")

    assert ".." not in spoken
    assert " ." not in spoken
