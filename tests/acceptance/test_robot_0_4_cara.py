"""Pruebas de aceptación de la versión 0.4 del robot: su cara.

La cara dibujada, la vida en reposo, que no se congele y la boca con su voz salen de la
sección 0.4 de ``docs/evolution/PLAN_DEL_ROBOT.md`` (§6, «Lo que se hace», 4 a 6, y
«Terminado cuando», 4), y llevan su ``PA-R04-NN`` de
``docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md``. La cara se lee de la ventana de verdad.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations, pairwise
from pathlib import Path

import pytest
from conductor_robot_0_4 import ConductorDeOjos, Dibujo, pieza
from pytestqt.qtbot import QtBot

pytestmark = [pytest.mark.acceptance, pytest.mark.gui]


def _cierres(dibujos: Sequence[Dibujo]) -> list[float]:
    """Cuándo empieza cada parpadeo: los ojos pasan de abiertos a casi cerrados."""
    cierres: list[float] = []
    abiertos = True
    for dibujo in dibujos:
        if abiertos and dibujo.ojos <= 0.2:
            cierres.append(dibujo.momento)
            abiertos = False
        elif not abiertos and dibujo.ojos >= 0.8:
            abiertos = True
    return cierres


def _saltos(miradas: Sequence[tuple[float, float]]) -> int:
    """Cuántas veces se va la mirada a más de 0,05 de donde estaba, a saltos o poco a poco."""
    saltos = 0
    desde = miradas[0]
    for mirada in miradas[1:]:
        if abs(mirada[0] - desde[0]) + abs(mirada[1] - desde[1]) > 0.05:
            saltos += 1
            desde = mirada
    return saltos


def _subidas(valores: Sequence[tuple[float, float]]) -> list[float]:
    """Cuándo sube cada respiración: el valor pasa del tercio de abajo al de arriba de lo
    que recorre, para que un temblor alrededor del medio no cuente como otra."""
    bajo = min(valor for _, valor in valores)
    alto = max(valor for _, valor in valores)
    arriba, abajo = alto - (alto - bajo) / 3, bajo + (alto - bajo) / 3
    subidas: list[float] = []
    bajando = False
    for momento, valor in valores:
        if valor <= abajo:
            bajando = True
        elif bajando and valor >= arriba:
            subidas.append(momento)
            bajando = False
    return subidas


@pieza("B", "su cara está en la ventana, dibujada: ojos, párpados, cejas y boca")
def test_su_cara_esta_en_la_ventana_con_ojos_parpados_cejas_y_boca(
    qtbot: QtBot, tmp_path: Path
) -> None:
    conductor = ConductorDeOjos(tmp_path)

    ventana = conductor.ventana(qtbot)

    assert ventana.partes_de_la_cara() >= {"ojos", "párpados", "cejas", "boca"}
    assert not ventana.la_cara_usa_imagenes()
    dibujo = ventana.cara()
    assert ventana.dibujos() >= 1
    assert 0.0 <= dibujo.ojos <= 1.0
    assert 0.0 <= dibujo.boca <= 1.0
    assert -1.0 <= dibujo.cejas <= 1.0


@pieza("B", "en reposo parpadea sin ritmo fijo")
def test_en_reposo_parpadea_sin_ritmo_fijo(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.ventana(qtbot)

    dibujos = conductor.pasa_el_tiempo(60.0)

    cierres = _cierres(dibujos)
    assert 6 <= len(cierres) <= 30, f"{len(cierres)} parpadeos en un minuto"
    entre = [despues - antes for antes, despues in pairwise(cierres)]
    assert max(entre) <= 10.0, entre
    # Sin ritmo fijo: entre el hueco más corto y el más largo hay al menos medio segundo.
    assert max(entre) - min(entre) >= 0.5, entre


@pieza("B", "en reposo mueve un poco los ojos y respira")
def test_en_reposo_mueve_un_poco_los_ojos_y_respira(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.ventana(qtbot)

    dibujos = conductor.pasa_el_tiempo(60.0)

    assert dibujos, "no se ha dibujado"
    miradas = [dibujo.mirada for dibujo in dibujos]
    assert _saltos(miradas) >= 2, "los ojos no se mueven"
    assert all(abs(x) <= 0.3 and abs(y) <= 0.3 for x, y in miradas), "se mueven demasiado"
    subidas = _subidas([(dibujo.momento, dibujo.respira) for dibujo in dibujos])
    periodos = [despues - antes for antes, despues in pairwise(subidas)]
    assert len(periodos) >= 6, f"respira {len(subidas)} veces en un minuto"
    assert all(2.0 <= periodo <= 8.0 for periodo in periodos), periodos


@pieza("B", "la cara no se congela aunque el modelo tarde")
def test_la_cara_no_se_congela_aunque_el_modelo_tarde(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path, respuestas=["Pues ya lo he pensado."])
    conductor.ventana(qtbot)

    veces, dibujos = conductor.dibujos_mientras_contesta_despacio(
        qtbot, "Piensa bien esto, Sirius.", segundos=3.0
    )

    assert veces >= 30, f"{veces} dibujos en 3 s: se ha congelado"
    assert len({(d.ojos, d.mirada, d.respira) for d in dibujos}) > 1, "dibuja siempre lo mismo"
    assert "Piensa bien esto, Sirius." in conductor.peticiones[-1].texto


@pieza("B", "la boca se mueve con el volumen de su voz")
def test_la_boca_se_mueve_con_el_volumen_de_su_voz(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.ventana(qtbot)
    niveles = (0.0, 0.2, 0.9, 0.9, 0.1, 0.0, 0.6, 0.3, 0.0)

    dibujos = conductor.habla_con_volumen("Hombre, ¿qué tal estás?", niveles)

    assert len(dibujos) == len(niveles) + 1
    bocas = [(nivel, dibujo.boca) for nivel, dibujo in zip(niveles, dibujos, strict=False)]
    for nivel, boca in bocas:
        if nivel == 0.0:
            assert boca <= 0.1, "en silencio la boca se queda abierta"
    # Con dos décimas o más de volumen de diferencia, la boca más abierta con el más alto.
    for (nivel_a, boca_a), (nivel_b, boca_b) in combinations(bocas, 2):
        if abs(nivel_a - nivel_b) > 0.15:
            assert (boca_a > boca_b) == (nivel_a > nivel_b), "más alto no abre más la boca"
    assert dibujos[-1].boca <= 0.1, "al callar la boca se queda abierta"
