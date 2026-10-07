"""El banco de las 40 preguntas trampa (pieza E de ADR-233, PA-R02-09)."""

from __future__ import annotations

from sirius.domain.trick_questions import TRICK_QUESTIONS


def test_son_40_numeradas_seguidas_y_ninguna_repetida() -> None:
    assert [question.id for question in TRICK_QUESTIONS] == [f"T{n:02d}" for n in range(1, 41)]
    assert len({question.bad_idea for question in TRICK_QUESTIONS}) == 40


def test_cada_idea_mala_va_con_su_porque_y_en_boca_del_propietario() -> None:
    for question in TRICK_QUESTIONS:
        assert question.bad_idea.strip().endswith(".")
        assert question.why_bad.strip()
        assert question.why_bad != question.bad_idea
