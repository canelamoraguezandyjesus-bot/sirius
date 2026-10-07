"""«Ponte serio», «para» y «vuelve a ser tú» (pieza D de ADR-233, PA-R02-04)."""

from __future__ import annotations

import pytest

from sirius.domain.conversation_mode import ConversationMode, detect_mode_command


@pytest.mark.parametrize(
    "texto",
    [
        "Ponte serio, que tengo que decidir si cambio de coche.",
        "ponte serio",
        "Oye, PONTE SERIO un momento.",
        "Venga, ponte   serio: ¿qué hago con el alquiler?",
    ],
)
def test_ponte_serio_pone_el_modo_serio(texto: str) -> None:
    assert detect_mode_command(texto) is ConversationMode.SERIO


@pytest.mark.parametrize(
    "texto",
    [
        "Para.",
        "Para ya, que hoy no estoy para bromas.",
        "para",
        "PARA!",
        "Para, que me tienes harto.",
        "Para de picarme.",
        "  ¡Para ya!",
    ],
)
def test_para_al_empezar_el_mensaje_corta_el_pique(texto: str) -> None:
    assert detect_mode_command(texto) is ConversationMode.PARA


@pytest.mark.parametrize(
    "texto",
    [
        "Para mañana tengo que llevar el coche al taller.",
        "Para que lo sepas, ayer gané al pádel.",
        "Esto es para ti.",
        "No estoy para bromas.",
        "Buenos días, Sirius.",
        "Me he puesto serio con mi jefe.",
    ],
)
def test_lo_que_no_es_una_orden_no_cambia_el_modo(texto: str) -> None:
    assert detect_mode_command(texto) is None


@pytest.mark.parametrize(
    "texto",
    [
        "Vale, ya está. Ya puedes volver a ser tú.",
        "vuelve a ser tu",
        "Venga, quiero que vuelvas a ser tú.",
    ],
)
def test_volver_a_ser_tu_suelta_el_modo(texto: str) -> None:
    assert detect_mode_command(texto) is ConversationMode.NORMAL


def test_soltar_gana_a_pedir_en_el_mismo_mensaje() -> None:
    assert (
        detect_mode_command("Ya no hace falta que te pongas serio, vuelve a ser tú.")
        is ConversationMode.NORMAL
    )
