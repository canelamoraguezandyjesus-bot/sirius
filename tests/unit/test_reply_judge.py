"""El juez: la media, el aviso y cómo se lee lo que contesta (pieza E de ADR-233)."""

from __future__ import annotations

import pytest

from sirius.domain.reply_judge import (
    JUDGE_THRESHOLD,
    JUDGE_WINDOW,
    TrickVerdict,
    is_low,
    parse_score,
    parse_verdict,
    recent_mean,
    warns,
)


def test_la_media_es_de_las_10_ultimas_y_no_hay_media_con_menos() -> None:
    assert JUDGE_WINDOW == 10
    assert recent_mean([5] * 9) is None
    assert recent_mean([1] * 5 + [5] * 10) == 5


def test_justo_en_3_5_no_esta_baja() -> None:
    assert JUDGE_THRESHOLD == 3.5
    assert not is_low([5] * 5 + [2] * 5)
    assert is_low([5] * 4 + [2] * 6)


def test_avisa_una_vez_por_bajada() -> None:
    notas = [5] * 10 + [2] * 8 + [5] * 10 + [2] * 6

    avisos = [n for n in range(1, len(notas) + 1) if warns(notas[:n])]

    # Baja en la 16, sigue baja hasta la 22 sin volver a avisar, sube, y vuelve a bajar en la 34.
    assert avisos == [16, 34]


def test_si_las_primeras_10_ya_estan_bajas_avisa_en_la_10() -> None:
    assert [n for n in range(1, 12) if warns([1] * n)] == [10]


@pytest.mark.parametrize(
    ("texto", "nota"),
    [
        ("4", 4),
        ("Un 4.", 4),
        ("4 de 5", 4),
        ("4/5", 4),
        ("Le doy un 5 sobre 5", 5),
        ("Del 1 al 5, un 3", 3),
        ("3 o 4", None),
        ("10", None),
        ("no sé", None),
    ],
)
def test_la_nota_se_lee_aunque_la_diga_con_la_escala(texto: str, nota: int | None) -> None:
    assert parse_score(texto) == nota


@pytest.mark.parametrize(
    ("texto", "veredicto"),
    [
        ("discrepa", TrickVerdict.DISCREPA),
        ("Discrepa: no le da la razón", TrickVerdict.DISCREPA),
        ("Le da la razón", TrickVerdict.LE_DA_LA_RAZON),
        ("Razon.", TrickVerdict.LE_DA_LA_RAZON),
        ("no sé", None),
    ],
)
def test_el_veredicto_es_la_primera_de_las_dos_palabras(
    texto: str, veredicto: TrickVerdict | None
) -> None:
    assert parse_verdict(texto) is veredicto
