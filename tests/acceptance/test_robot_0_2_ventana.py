"""Pruebas de aceptación de la versión 0.2 del robot: lo que se ve en la ventana.

Los dos botones de cada respuesta y el indicador de modo son lo que el
propietario toca. Salen de la sección 0.2 de ``docs/evolution/PLAN_DEL_ROBOT.md``
(§4, pasos 4 y 5 de la personalidad) y llevan su ``PA-R02-NN`` de
``docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_2 import Conductor, pieza
from pytestqt.qtbot import QtBot

pytestmark = [pytest.mark.acceptance, pytest.mark.gui]


@pieza("D", "cada respuesta de Sirius en la ventana lleva «Eso es Sirius» y «Eso no»")
def test_cada_respuesta_de_sirius_en_la_ventana_lleva_los_dos_botones(
    qtbot: QtBot, tmp_path: Path
) -> None:
    conductor = Conductor(tmp_path)
    conductor.di("Buenos días, Sirius.")
    conductor.di("¿Qué estás haciendo?")
    ventana = conductor.ventana(qtbot)

    assert ventana.botones_de_la_respuesta(1) == ("Eso es Sirius", "Eso no")
    assert ventana.botones_de_la_respuesta(2) == ("Eso es Sirius", "Eso no")

    ventana.pulsa(2, "Eso no")
    assert conductor.marcas() == [(2, "eso no")]


@pieza("D", "el modo serio se ve en la ventana y se quita con un botón")
def test_el_modo_serio_se_ve_en_la_ventana_y_se_quita_con_un_boton(
    qtbot: QtBot, tmp_path: Path
) -> None:
    conductor = Conductor(tmp_path)
    serio = conductor.texto_del_modo("serio")
    conductor.di("Ponte serio, que tengo que decidir algo.")
    ventana = conductor.ventana(qtbot)

    assert ventana.indicador_de_modo() == "Modo serio"

    ventana.quita_el_modo()
    assert ventana.indicador_de_modo() == ""
    conductor.di("¿Y ahora qué?")
    assert serio not in conductor.peticiones[-1].instrucciones
