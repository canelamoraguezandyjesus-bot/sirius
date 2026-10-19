"""La cara de Sirius como widget, sin el resto de la ventana (pieza B de la 0.4, ADR-260).

Las pruebas de aceptación (``tests/acceptance/test_robot_0_4_cara.py``) miran la cara en la
ventana de verdad con el conductor. Estas miran el widget solo: que se redibuja por su
cuenta, que dibuja lo que dice su vida con el reloj y el volumen que le dan, que lo
apunta, y que al pararlo deja de dibujarse.
"""

from __future__ import annotations

import logging

import pytest
from pytestqt.qtbot import QtBot

from sirius.domain.face import FaceLife
from sirius.presentation.face_widget import PARTS, FaceWidget


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 500.0

    def __call__(self) -> float:
        return self.ahora


def _cara(qtbot: QtBot, reloj: _Reloj, nivel: list[float]) -> FaceWidget:
    cara = FaceWidget(reloj, lambda: nivel[0], life=FaceLife(seed=1))
    qtbot.addWidget(cara)
    cara.resize(400, 180)
    cara.show()
    qtbot.waitExposed(cara)
    return cara


def test_se_redibuja_por_su_cuenta_unas_treinta_veces_por_segundo(qtbot: QtBot) -> None:
    cara = _cara(qtbot, _Reloj(), [0.0])
    antes = cara.paints

    qtbot.wait(500)

    assert cara.paints - antes >= 5, "con el temporizador parado no hay cara viva"
    assert cara.drawn_parts == PARTS == frozenset({"ojos", "párpados", "cejas", "boca"})


def test_dibuja_con_el_reloj_y_el_volumen_que_le_dan_y_lo_apunta(qtbot: QtBot) -> None:
    reloj, nivel = _Reloj(), [0.0]
    cara = _cara(qtbot, reloj, nivel)
    cara.grab()

    reloj.ahora = 500.5
    nivel[0] = 0.7
    cara.grab()

    assert cara.last_drawn is not None
    momento, pose = cara.last_drawn
    assert momento == 500.5
    assert pose.mouth > 0.6, "la boca no sigue al volumen"


def test_al_pararla_deja_de_dibujarse_sola(qtbot: QtBot) -> None:
    cara = _cara(qtbot, _Reloj(), [0.0])

    cara.stop()
    # Lo que el sistema de ventanas ya tuviera pedido se dibuja igual; después, nada.
    qtbot.wait(100)
    antes = cara.paints
    qtbot.wait(300)

    assert cara.paints == antes


def test_si_no_puede_leer_el_volumen_sigue_viva_con_la_boca_cerrada_y_lo_apunta_una_vez(
    qtbot: QtBot, caplog: pytest.LogCaptureFixture
) -> None:
    def falla() -> float:
        raise RuntimeError("el altavoz se ha ido")

    cara = FaceWidget(_Reloj(), falla, life=FaceLife(seed=1))
    qtbot.addWidget(cara)
    cara.resize(400, 180)

    with caplog.at_level(logging.WARNING):
        cara.grab()
        cara.grab()

    assert cara.paints == 2, "la cara se para si el volumen falla"
    assert cara.last_drawn is not None and cara.last_drawn[1].mouth == 0.0
    avisos = [r for r in caplog.records if "volumen" in r.getMessage()]
    assert len(avisos) == 1
