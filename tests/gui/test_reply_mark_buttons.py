"""Los botones «Eso es Sirius» y «Eso no» de cada respuesta (pieza D de ADR-233, PA-R02-06)."""

from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from sirius.domain.reply_mark import ReplyMark
from sirius.presentation.message_view import MessageItemWidget

pytestmark = pytest.mark.gui


def _respuesta(qtbot: QtBot, *, marcas: bool, marca: ReplyMark | None = None) -> MessageItemWidget:
    widget = MessageItemWidget()
    qtbot.addWidget(widget)
    widget.set_message(
        "Sirius",
        "Buenos días, jefe.",
        bold=True,
        message_id=7,
        show_propose_suggestion=True,
        show_marks=marcas,
        current_mark=marca,
    )
    return widget


def test_solo_las_respuestas_completas_llevan_los_dos_botones(qtbot: QtBot) -> None:
    con = _respuesta(qtbot, marcas=True)
    sin = _respuesta(qtbot, marcas=False)

    assert [b.text() for b in con.mark_buttons] == ["Eso es Sirius", "Eso no"]
    assert all(not b.isHidden() for b in con.mark_buttons)
    assert all(b.isHidden() for b in sin.mark_buttons)


def test_pulsar_avisa_con_el_mensaje_y_la_marca_y_deja_solo_ese_pulsado(qtbot: QtBot) -> None:
    widget = _respuesta(qtbot, marcas=True)
    avisos: list[tuple[int, str]] = []
    widget.mark_requested.connect(lambda mensaje, marca: avisos.append((mensaje, marca)))
    es_sirius, eso_no = widget.mark_buttons

    eso_no.click()
    es_sirius.click()

    assert avisos == [(7, "eso no"), (7, "eso es Sirius")]
    assert es_sirius.isChecked() and not eso_no.isChecked()


def test_la_marca_guardada_se_ve_al_cargar_la_charla(qtbot: QtBot) -> None:
    widget = _respuesta(qtbot, marcas=True, marca=ReplyMark.NO_ES_SIRIUS)

    es_sirius, eso_no = widget.mark_buttons
    assert eso_no.isChecked() and not es_sirius.isChecked()
