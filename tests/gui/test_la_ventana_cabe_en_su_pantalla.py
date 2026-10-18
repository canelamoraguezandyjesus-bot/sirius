"""La ventana cabe en la pantalla de su portátil (ADR-253).

Al 150 %, su pantalla le deja 1280x672. Sin barra para bajar, la pestaña «Memoria y
decisiones» no dejaba a la ventana medir menos de 787 px de alto: no cabía, y no abría a
su tamaño de siempre, 900x620. Las medidas de Qt son lógicas, las mismas a cualquier
escala: lo que cabe aquí cabe allí.
"""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from .test_escucha_en_la_ventana import _monta, _ventana

#: Lo que le deja su pantalla de alto al 150 %, menos el marco: en Windows, al 150 %, la
#: barra de título mide unos 30 px, y el mínimo de Qt no la cuenta.
SU_ALTO_DISPONIBLE = 672 - 40


def test_la_ventana_abre_a_900x620_y_cabe_en_su_pantalla(qtbot: QtBot, tmp_path: Path) -> None:
    ventana = _ventana(qtbot, _monta(tmp_path))
    qtbot.waitExposed(ventana)

    assert ventana.minimumSizeHint().height() <= SU_ALTO_DISPONIBLE
    assert (ventana.width(), ventana.height()) == (900, 620)


def test_la_pestana_de_la_memoria_baja_con_su_barra(qtbot: QtBot, tmp_path: Path) -> None:
    ventana = _ventana(qtbot, _monta(tmp_path))
    pestanas = [ventana.tabs.tabText(indice) for indice in range(ventana.tabs.count())]
    memoria = ventana.tabs.widget(pestanas.index("Memoria y decisiones"))
    assert memoria is not None

    # La barra sale cuando hace falta; lo de dentro no le impone su alto a la ventana.
    assert memoria.minimumSizeHint().height() < ventana.knowledge_widget.minimumSizeHint().height()
