"""Lo que el modelo lee de quién hay, en «# Quién hay» (pieza E de la 0.4, ADR-263)."""

from __future__ import annotations

from sirius.application.presence import (
    HEADING,
    IN_FRONT_LINE,
    NOBODY_LINE,
    RULE,
    SOMEONE,
    SPEAKER_LINE,
    presence_block,
)
from sirius.application.recognition import UNKNOWN


def test_sin_turno_de_voz_ni_camara_no_hay_seccion() -> None:
    assert presence_block(speaker=None, in_front=None) == ""


def test_quien_le_habla_va_con_su_nombre_o_como_alguien_sin_identificar() -> None:
    assert presence_block(speaker="Marta", in_front=None) == "\n".join(
        [HEADING, SPEAKER_LINE.format(who="Marta"), RULE]
    )
    assert presence_block(speaker=UNKNOWN, in_front=None) == "\n".join(
        [HEADING, SPEAKER_LINE.format(who=SOMEONE), RULE]
    )
    assert SPEAKER_LINE.format(who=SOMEONE) == "Te habla alguien sin identificar."


def test_a_quienes_tiene_delante_primero_los_que_tienen_nombre_por_orden() -> None:
    bloque = presence_block(speaker=None, in_front=["Pepe", None, "Ana", UNKNOWN])

    assert bloque.splitlines() == [
        HEADING,
        IN_FRONT_LINE.format(who="Ana"),
        IN_FRONT_LINE.format(who="Pepe"),
        IN_FRONT_LINE.format(who=SOMEONE),
        IN_FRONT_LINE.format(who=SOMEONE),
        RULE,
    ]


def test_sin_nadie_delante_lo_dice() -> None:
    assert presence_block(speaker="Marta", in_front=[]).splitlines() == [
        HEADING,
        SPEAKER_LINE.format(who="Marta"),
        NOBODY_LINE,
        RULE,
    ]


def test_la_regla_dice_que_solo_reconoce_a_quien_dio_permiso() -> None:
    assert "permiso" in RULE
    assert "sin identificar" in RULE
    assert "\n" not in RULE, "va en una línea, detrás de las de quién hay"
