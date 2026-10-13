"""Pruebas de aceptación de la versión 0.3 del robot: lo que se ve en la ventana.

El indicador de que escucha, el botón que lo calla y la charla por voz vista
como la escrita salen de la sección 0.3 de ``docs/evolution/PLAN_DEL_ROBOT.md``
(§5, «Lo que se hace», 4) y de EV-022, y llevan su ``PA-R03-NN`` de
``docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_3 import ConductorDeVoz, pieza
from pytestqt.qtbot import QtBot

pytestmark = [pytest.mark.acceptance, pytest.mark.gui]


@pieza("D", "al abrir la ventana escucha sin pulsar nada y lo dice")
def test_al_abrir_la_ventana_escucha_sin_pulsar_nada_y_lo_dice(
    qtbot: QtBot, tmp_path: Path
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    assert not conductor.micro.abierto

    ventana = conductor.ventana(qtbot)

    assert conductor.micro.abierto
    assert ventana.indicador_de_escucha() == "Escuchando"


@pieza("D", "el botón de silencio cierra el micrófono y lo dice")
def test_el_boton_de_silencio_cierra_el_microfono_y_lo_dice(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    ventana = conductor.ventana(qtbot)

    ventana.pulsa_silencio()

    assert not conductor.micro.abierto
    assert ventana.indicador_de_escucha() == "En silencio"
    callado = conductor.oye("Sirius, ¿me oyes?")
    # Con el micro cerrado lo que suena se pierde: nadie lo lee, ni llega al
    # transcriptor ni al modelo.
    assert callado.oido is None
    assert [s.texto for s in conductor.micro.perdidos if not s.es_silencio] == ["Sirius, ¿me oyes?"]
    assert conductor.micro.leidos == ()
    assert conductor.transcriptor.transcritos == ()
    assert conductor.peticiones == []

    ventana.pulsa_silencio()

    assert conductor.micro.abierto
    assert ventana.indicador_de_escucha() == "Escuchando"
    de_nuevo = conductor.oye("Sirius, ¿me oyes ahora?")
    # Y lo que sonó en silencio no se atiende tarde: solo lo dicho ahora.
    assert de_nuevo.contestado == "Respuesta 1 de Sirius."
    assert conductor.transcriptor.transcritos == ("Sirius, ¿me oyes ahora?",)
    assert [p.texto for p in conductor.peticiones] == ["Sirius, ¿me oyes ahora?"]


@pieza("D", "lo oído y lo contestado se ven en la ventana como la charla escrita, con sus botones")
def test_lo_oido_y_lo_contestado_se_ven_en_la_ventana_con_sus_dos_botones(
    qtbot: QtBot, tmp_path: Path
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    ventana = conductor.ventana(qtbot)

    conductor.oye("Buenos días, Sirius.")

    assert ventana.mensajes()[-2:] == (
        ("propietario", "Buenos días, Sirius."),
        ("Sirius", "Respuesta 1 de Sirius."),
    )
    assert ventana.botones_de_la_respuesta(1) == ("Eso es Sirius", "Eso no")
