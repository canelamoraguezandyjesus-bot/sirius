"""Pruebas de aceptación de la versión 0.4 del robot: los gestos de una lista cerrada.

Salen de la sección 0.4 de ``docs/evolution/PLAN_DEL_ROBOT.md`` (§6, «Lo que se hace»,
7): el modelo escribe la respuesta con etiquetas como ``[ceja_arriba]``, la cara las hace
y lo que no está en la lista se ignora. Llevan su ``PA-R04-05`` de
``docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_4 import ConductorDeOjos, pieza
from pytestqt.qtbot import QtBot

pytestmark = [pytest.mark.acceptance, pytest.mark.gui]

_CON_GESTO = "Hombre, [ceja_arriba] eso habrá que verlo."
_CON_GESTO_DESCONOCIDO = "Vale, [bailar] lo que tú digas."


@pieza("C", "el modelo sabe qué gestos hay, porque la lista va en sus instrucciones")
def test_el_modelo_sabe_que_gestos_hay(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)

    conductor.oye("Sirius, ¿qué tal?")

    gestos = conductor.gestos()
    assert "ceja_arriba" in gestos, "el ejemplo del plan no está en la lista"
    [peticion] = conductor.peticiones_del_ultimo_turno()
    assert all(f"[{gesto}]" in peticion.instrucciones for gesto in gestos)


@pieza("C", "la cara hace el gesto de la lista que escribe el modelo")
def test_la_cara_hace_el_gesto_que_escribe_el_modelo(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path, respuestas=[_CON_GESTO])
    conductor.ventana(qtbot)

    conductor.oye("Sirius, me voy a comprar un barco.")

    assert "ceja_arriba" in conductor.gestos_dibujados()


@pieza("C", "un gesto que no está en la lista se ignora: ni se hace, ni se ve, ni se dice")
def test_un_gesto_que_no_esta_en_la_lista_se_ignora(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path, respuestas=[_CON_GESTO_DESCONOCIDO])
    ventana = conductor.ventana(qtbot)

    turno = conductor.oye("Sirius, me apetece salir.")

    assert "bailar" not in conductor.gestos()
    assert conductor.gestos_dibujados() == ()
    assert turno.contestado is not None
    visto = ventana.mensajes()[-1][1]
    assert "[" not in visto and "bailar" not in visto
    assert "lo que tú digas" in visto
    assert all("bailar" not in frase.texto for frase in conductor.voz.frases)


@pieza("C", "las etiquetas ni se ven en la ventana, ni las dice la voz, ni quedan en la charla")
def test_las_etiquetas_ni_se_ven_ni_se_dicen_ni_se_guardan(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path, respuestas=[_CON_GESTO])
    ventana = conductor.ventana(qtbot)

    conductor.oye("Sirius, me voy a comprar un barco.")

    visto = ventana.mensajes()[-1][1]
    assert "[" not in visto and "ceja_arriba" not in visto
    assert "Hombre," in visto and "eso habrá que verlo." in visto
    dicho = " ".join(frase.texto for frase in conductor.voz.frases)
    assert "eso habrá que verlo" in dicho
    assert "[" not in dicho and "ceja" not in dicho
    assert conductor.busca_en_toda_la_base("ceja_arriba") == []
