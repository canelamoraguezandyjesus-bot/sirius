"""Reconocer las órdenes de memoria (pieza G de ADR-233, ADR-239)."""

from __future__ import annotations

import pytest

from sirius.domain.facts import mentioned_people, person_key
from sirius.domain.memory_commands import MemoryCommand, MemoryCommandKind, detect_memory_command
from sirius.domain.plain_text import nfc, plain

K = MemoryCommandKind


@pytest.mark.parametrize(
    ("texto", "orden"),
    [
        ("Olvida eso.", MemoryCommand(K.FORGET_LAST)),
        ("olvídalo", MemoryCommand(K.FORGET_LAST)),
        ("Olvídate de eso, por favor.", MemoryCommand(K.FORGET_LAST)),
        ("Sirius, olvida esto", MemoryCommand(K.FORGET_LAST)),
        ("Borra lo que te acabo de decir", MemoryCommand(K.FORGET_LAST)),
        ("Olvida lo de mi vecino Ramiro.", MemoryCommand(K.FORGET_ABOUT, "mi vecino Ramiro")),
        ("¡Olvida todo lo del Préstamo!", MemoryCommand(K.FORGET_ABOUT, "Préstamo")),
        ("Eso no es así: soy del Betis.", MemoryCommand(K.CORRECT, "soy del Betis")),
        ("Eso no es verdad, vivo en Valencia", MemoryCommand(K.CORRECT, "vivo en Valencia")),
        ("Eso no es así.", MemoryCommand(K.CORRECT, "")),
        ("¿Qué sabes de mí?", MemoryCommand(K.ABOUT_ME)),
        ("¿Y qué recuerdas de mi?", MemoryCommand(K.ABOUT_ME)),
        ("¿Qué sabes de Lucía?", MemoryCommand(K.ABOUT_PERSON, "Lucía")),
        ("Sí.", MemoryCommand(K.YES)),
        ("sí, cámbialo", MemoryCommand(K.YES)),
        ("No", MemoryCommand(K.NO)),
    ],
)
def test_reconoce_cada_orden_y_recorta_lo_que_dijo_con_sus_palabras(
    texto: str, orden: MemoryCommand
) -> None:
    assert detect_memory_command(texto) == orden


@pytest.mark.parametrize(
    "texto",
    [
        "No olvides eso que te dije.",
        "Olvida lo de a",
        "La clave de la alarma es Zarzamora.",
        "¿Qué tal estará Lucía?",
        "Eso no es asunto tuyo",
        "Sí que me acuerdo de aquello",
        "",
        "   ",
    ],
)
def test_lo_que_no_es_entero_una_orden_va_a_la_charla(texto: str) -> None:
    assert detect_memory_command(texto) is None


def test_el_texto_llano_mide_lo_mismo_que_el_texto() -> None:
    """Sin eso, recortar lo que dijo con sus tildes cortaría por otro sitio."""
    for texto in ("Ñandú y cigüeña", "ÁÉÍÓÚ áéíóú", "é descompuesta"):
        assert len(plain(texto)) == len(nfc(texto))
    assert plain("Lucía, ÑO") == "lucia, no"


def test_una_persona_se_nombra_por_palabras_enteras_y_sin_tildes() -> None:
    gente = ["Lucía", "Juan Pedro", "propietario"]
    assert mentioned_people("¿Qué tal estará lucia?", gente) == ["Lucía"]
    assert mentioned_people("Ha venido Luciano", gente) == []
    assert mentioned_people("He visto a juan  pedro hoy", gente) == ["Juan Pedro"]
    assert mentioned_people("Juan vino solo", gente) == []
    assert mentioned_people("El propietario soy yo", gente) == []
    assert person_key("  Lucía ") == person_key("lucia")
