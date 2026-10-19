"""La cara de Sirius como widget, sin el resto de la ventana (piezas B y C de la 0.4,
ADR-260 y ADR-261).

Las pruebas de aceptación (``tests/acceptance/test_robot_0_4_cara.py`` y
``test_robot_0_4_gestos.py``) miran la cara en la ventana de verdad con el conductor.
Estas miran el widget solo: que se redibuja por su cuenta, que dibuja lo que dice su vida
con el reloj, el volumen y los gestos que le dan, que lo apunta, y que al pararlo deja de
dibujarse.
"""

from __future__ import annotations

import logging

import pytest
from pytestqt.qtbot import QtBot

from sirius.domain.face import FaceLife
from sirius.domain.gestures import GESTURES
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


# --- Los gestos (pieza C de la 0.4, ADR-261) ---


class _Dicho:
    """Lo que da el oído de los gestos de lo que dice: el turno y los que ya suenan."""

    def __init__(self) -> None:
        self.turno = ""
        self.suenan: tuple[str, ...] = ()

    def __call__(self) -> tuple[str, tuple[str, ...]]:
        return self.turno, self.suenan


def _cara_con_gestos(qtbot: QtBot, reloj: _Reloj, dicho: _Dicho) -> FaceWidget:
    cara = FaceWidget(reloj, lambda: 0.0, dicho, life=FaceLife(seed=1))
    qtbot.addWidget(cara)
    cara.resize(400, 180)
    return cara


def _gesto_dibujado(cara: FaceWidget) -> str | None:
    cara.grab()
    assert cara.last_drawn is not None
    return cara.last_drawn[1].gesture


def test_hace_cada_gesto_de_lo_que_dice_una_vez_cuando_empieza_a_sonar(qtbot: QtBot) -> None:
    reloj, dicho = _Reloj(), _Dicho()
    cara = _cara_con_gestos(qtbot, reloj, dicho)
    assert _gesto_dibujado(cara) is None

    dicho.turno, dicho.suenan = "op-1", ("sonrisa",)
    assert _gesto_dibujado(cara) == "sonrisa"
    reloj.ahora += 5.0
    assert _gesto_dibujado(cara) is None, "el mismo gesto se hace otra vez"

    dicho.turno, dicho.suenan = "op-2", ("sonrisa",)
    assert _gesto_dibujado(cara) == "sonrisa", "el de un turno nuevo no se hace"


def test_lo_escrito_en_la_ventana_hace_su_gesto_al_llegar(qtbot: QtBot) -> None:
    cara = _cara_con_gestos(qtbot, _Reloj(), _Dicho())

    cara.make("guino")

    assert _gesto_dibujado(cara) == "guino"


def test_si_no_puede_leer_los_gestos_sigue_viva_y_lo_apunta_una_vez(
    qtbot: QtBot, caplog: pytest.LogCaptureFixture
) -> None:
    def falla() -> tuple[str, tuple[str, ...]]:
        raise RuntimeError("el oído se ha ido")

    cara = FaceWidget(_Reloj(), lambda: 0.0, falla, life=FaceLife(seed=1))
    qtbot.addWidget(cara)
    cara.resize(400, 180)

    with caplog.at_level(logging.WARNING):
        cara.grab()
        cara.grab()

    assert cara.paints == 2, "la cara se para si los gestos fallan"
    assert len([r for r in caplog.records if "gestos" in r.getMessage()]) == 1


@pytest.mark.parametrize("gesto", GESTURES)
def test_cada_gesto_cambia_lo_que_se_ve(qtbot: QtBot, gesto: str) -> None:
    reloj = _Reloj()
    quieta, con_gesto = (_cara_con_gestos(qtbot, reloj, _Dicho()) for _ in range(2))
    quieta.grab()
    con_gesto.grab()

    con_gesto.make(gesto)
    con_gesto.grab()
    quieta.grab()
    reloj.ahora += 0.3

    assert con_gesto.grab().toImage() != quieta.grab().toImage(), "el gesto no se ve"
