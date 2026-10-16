"""A quién le hablan: a Sirius, con su nombre o mientras dura la charla (ADR-244,
PA-R03-06).

Las dos mitades de la regla, solas: su nombre en lo oído y la charla con la hora que se le
da. Juntas, con el oído entero, se prueban en ``test_local_listening.py``, y con el
conductor, en las pruebas de aceptación de la pieza D.
"""

from __future__ import annotations

import pytest

from sirius.application.addressing import CONVERSATION_SECONDS, Addressing, says_his_name


@pytest.mark.parametrize(
    "dicho",
    [
        "Sirius",
        "sirius",
        "SIRIUS, ven",
        "Oye, Sirius, ¿qué hora es?",
        "¿Y tú qué opinas, sirius?",
        "¡Sirius!",
    ],
)
def test_su_nombre_se_oye_sin_distinguir_mayusculas_ni_donde_vaya(dicho: str) -> None:
    assert says_his_name(dicho)


@pytest.mark.parametrize("dicho", ["Siriusito", "Sirio", "Cirius", "siriusa", "Sir ius"])
def test_su_nombre_es_una_palabra_suelta_y_entera(dicho: str) -> None:
    assert not says_his_name(dicho)


def test_sin_que_haya_hablado_no_hay_charla() -> None:
    assert not Addressing().in_conversation(0.0)


def test_es_de_la_charla_lo_que_empieza_mientras_dura_y_no_despues() -> None:
    a_quien = Addressing(conversation_seconds=10.0)
    a_quien.fell_silent(100.0)

    assert a_quien.in_conversation(100.0)
    # Lo que empieza justo al acabar la charla aún es de ella.
    assert a_quien.in_conversation(110.0)
    assert not a_quien.in_conversation(110.5)


def test_lo_que_empezo_antes_de_que_callara_no_es_de_esta_charla() -> None:
    # Ronda 1 de Codex sobre la PR #689: si atendiendo un turno no dijo nada, la charla
    # empieza al acabarlo, y lo que sonó mientras tanto ya había empezado.
    a_quien = Addressing(conversation_seconds=10.0)
    a_quien.fell_silent(100.0)

    assert not a_quien.in_conversation(99.5)


def test_la_charla_cuenta_desde_la_ultima_vez_que_calla() -> None:
    a_quien = Addressing(conversation_seconds=10.0)
    a_quien.fell_silent(100.0)
    a_quien.fell_silent(200.0)

    assert a_quien.in_conversation(205.0)
    assert not a_quien.in_conversation(215.0)


def test_la_charla_dura_lo_que_se_le_diga() -> None:
    a_quien = Addressing(conversation_seconds=5.0)
    a_quien.fell_silent(0.0)

    assert a_quien.conversation_seconds == 5.0
    assert a_quien.in_conversation(5.0)
    assert not a_quien.in_conversation(6.0)


def test_la_charla_dura_diez_segundos_dentro_de_lo_que_pide_pa_r03_06() -> None:
    # PA-R03-06: ni cero, que obligaría a decir su nombre siempre, ni más de 2 min.
    assert CONVERSATION_SECONDS == 10.0
    assert Addressing().conversation_seconds == CONVERSATION_SECONDS
    assert 5 <= CONVERSATION_SECONDS <= 120
