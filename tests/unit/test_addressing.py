"""A quién le hablan: a Sirius, con su nombre o mientras dura la charla (ADR-244,
PA-R03-06).

La regla sola, con la hora que se le da. Con el oído entero se prueba en
``test_local_listening.py``, y con el conductor, en las pruebas de aceptación de la pieza D.
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
def test_con_su_nombre_siempre_es_para_el(dicho: str) -> None:
    # Ni ha hablado nunca ni hay charla: su nombre basta.
    assert says_his_name(dicho)
    assert Addressing().is_for_sirius(dicho, began=1_000_000.0)


@pytest.mark.parametrize("dicho", ["Siriusito", "Sirio", "Cirius", "siriusa", "Sir ius"])
def test_su_nombre_es_una_palabra_suelta_y_entera(dicho: str) -> None:
    assert not says_his_name(dicho)
    assert not Addressing().is_for_sirius(dicho, began=0.0)


def test_sin_su_nombre_y_sin_que_haya_hablado_no_es_para_el() -> None:
    assert not Addressing().is_for_sirius("¿Has dormido bien?", began=0.0)


def test_sin_su_nombre_es_para_el_mientras_dura_la_charla_y_no_despues() -> None:
    a_quien = Addressing(conversation_seconds=10.0)
    a_quien.fell_silent(100.0)

    assert a_quien.is_for_sirius("¿Has dormido bien?", began=100.0)
    # Lo que empieza justo al acabar la charla aún es de ella.
    assert a_quien.is_for_sirius("¿Has dormido bien?", began=110.0)
    assert not a_quien.is_for_sirius("¿Has dormido bien?", began=110.5)


def test_la_charla_cuenta_desde_la_ultima_vez_que_calla() -> None:
    a_quien = Addressing(conversation_seconds=10.0)
    a_quien.fell_silent(100.0)
    a_quien.fell_silent(200.0)

    assert a_quien.is_for_sirius("¿Y luego?", began=205.0)
    assert not a_quien.is_for_sirius("¿Y luego?", began=215.0)


def test_la_charla_dura_lo_que_se_le_diga() -> None:
    a_quien = Addressing(conversation_seconds=5.0)
    a_quien.fell_silent(0.0)

    assert a_quien.conversation_seconds == 5.0
    assert a_quien.is_for_sirius("¿Y luego?", began=5.0)
    assert not a_quien.is_for_sirius("¿Y luego?", began=6.0)


def test_la_charla_dura_diez_segundos_dentro_de_lo_que_pide_pa_r03_06() -> None:
    # PA-R03-06: ni cero, que obligaría a decir su nombre siempre, ni más de 2 min.
    assert CONVERSATION_SECONDS == 10.0
    assert Addressing().conversation_seconds == CONVERSATION_SECONDS
    assert 5 <= CONVERSATION_SECONDS <= 120
