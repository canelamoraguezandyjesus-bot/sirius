"""Pruebas de aceptación de la versión 0.2 del robot: lo que se ve en la ventana.

Los dos botones de cada respuesta, el indicador de modo y el aviso del juez son lo
que el propietario ve y toca. Salen de la sección 0.2 de
``docs/evolution/PLAN_DEL_ROBOT.md`` (§4: los pasos 4, 5 y 7 de la personalidad y lo
que se deja de hacer) y llevan su ``PA-R02-NN`` de
``docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_2 import Conductor, JuezDeMentira, OllamaDeMentira, pieza
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


@pieza("E", "mientras la media del juez sigue por debajo de 3,5, la ventana lo enseña")
def test_mientras_el_juez_dice_que_sirius_baja_la_ventana_lo_ensena(
    qtbot: QtBot, tmp_path: Path
) -> None:
    conductor = Conductor(tmp_path)
    conductor.con_juez(JuezDeMentira(notas=[5] * 10 + [2] * 6 + [5] * 5))
    for n in range(1, 11):
        conductor.di(f"Mensaje {n}.")
    assert conductor.ventana(qtbot).aviso_del_juez() == ""

    for n in range(11, 17):
        conductor.di(f"Mensaje {n}.")
    ventana = conductor.ventana(qtbot)
    # Las 10 últimas notas dan 3,2.
    assert "3,2" in ventana.aviso_del_juez()

    for n in range(17, 22):
        ventana.escribe(f"Mensaje {n}.")
    # Con cinco notas altas más, las 10 últimas dan 3,5: la misma ventana deja de enseñarlo.
    assert ventana.aviso_del_juez() == ""


@pieza("F", "con la ventana abierta, nada etiqueta los recuerdos por categorías ni se ofrece")
def test_con_la_ventana_abierta_no_se_pide_a_ollama_etiquetar_recuerdos(
    qtbot: QtBot, tmp_path: Path
) -> None:
    ollama = OllamaDeMentira()
    conductor = Conductor(tmp_path, ajustes={"category_matching_enabled": True})
    conductor.con_ollama_espia(ollama)
    conductor.guarda_recuerdo("Su hermana Lucía es enfermera.")

    ventana = conductor.ventana(qtbot)
    ventana.espera_al_trabajo_de_fondo()

    assert ollama.llamadas_a("/api/chat") == 0
    assert ollama.llamadas_a("/api/generate") == 0
    assert conductor.categoria_del_recuerdo("Su hermana Lucía es enfermera.") is None
    assert not ventana.ofrece_etiquetar_por_categorias()
