"""Pruebas de aceptación de la versión 0.4 del robot: la cámara y la mirada.

Salen de la sección 0.4 de ``docs/evolution/PLAN_DEL_ROBOT.md`` (§6, «Lo que se hace»,
1 y 6, y «Terminado cuando», 1), de la 0.3 («desde 0.4, si le miran») y del §2 (el vídeo
no sale nunca), y llevan su ``PA-R04-NN`` de ``docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_4 import ConductorDeOjos, Persona, pieza
from pytestqt.qtbot import QtBot

pytestmark = [pytest.mark.acceptance, pytest.mark.gui]


@pieza("D", "lo que ve la cámara pasa por el detector de caras, en local y con MediaPipe")
def test_lo_que_ve_la_camara_pasa_por_el_detector_de_caras(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("propietario", x=0.5))
    conductor.ventana(qtbot)

    conductor.mira_un_rato(2.0)

    dados = {fotograma.numero for fotograma in conductor.camara.dados}
    detectados = {numero for numero, _ in conductor.detector.detecciones}
    assert detectados, "no ha buscado caras"
    assert detectados <= dados, "ha buscado caras en algo que no dio la cámara"
    assert all(caras == 1 for _, caras in conductor.detector.detecciones)
    assert "mediapipe" in conductor.herramientas_de_los_ojos()
    assert conductor.conexiones_de_red() == []


@pieza("D", "sin cámara al abrir, lo dice, y sigue oyendo y hablando")
def test_sin_camara_al_abrir_lo_dice_y_sigue_oyendo(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.sin_camara()

    ventana = conductor.ventana(qtbot)
    conductor.mira_un_rato(1.0)

    assert "cámara" in ventana.indicador_de_la_camara().lower()
    assert conductor.camara.dados == ()
    turno = conductor.oye("Sirius, ¿me oyes?")
    assert turno.contestado is not None


@pieza("D", "si se desenchufa la cámara, lo dice, y sigue oyendo y hablando")
def test_si_se_desenchufa_la_camara_lo_dice_y_sigue_oyendo(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("propietario", x=0.5))
    ventana = conductor.ventana(qtbot)
    conductor.mira_un_rato(1.0)
    con_camara = ventana.indicador_de_la_camara()
    assert conductor.camara.dados, "no miraba"

    conductor.sin_camara()
    conductor.mira_un_rato(1.0)

    sin_camara = ventana.indicador_de_la_camara()
    assert "cámara" in sin_camara.lower()
    assert sin_camara != con_camara, "dice lo mismo con cámara que sin ella"
    turno = conductor.oye("Sirius, ¿me oyes?")
    assert turno.contestado is not None


@pieza("D", "con dos delante, mira a la que habla")
def test_mira_a_quien_habla(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("propietario", x=0.2), Persona("Marta", x=0.8))
    conductor.ventana(qtbot)

    con_el = conductor.mira_y_oye("propietario", "Sirius, ¿me ves?")
    con_ella = conductor.mira_y_oye("Marta", "Sirius, ¿y a mí?")

    assert con_el.oyendo is not None and con_ella.oyendo is not None
    assert conductor.a_quien_mira(con_el.oyendo) == "propietario"
    assert conductor.a_quien_mira(con_ella.oyendo) == "Marta"


@pieza("D", "aparta la vista al pensar, y al contestar vuelve a mirar a quien le habló")
def test_aparta_la_vista_al_pensar_y_vuelve_al_contestar(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("propietario", x=0.3), Persona("Marta", x=0.8))
    conductor.ventana(qtbot)

    turno = conductor.mira_y_oye("propietario", "Sirius, ¿cuánto es siete por ocho?")

    assert turno.pensando, "no se dibujó la cara mientras pensaba"
    assert any(conductor.a_quien_mira(dibujo) is None for dibujo in turno.pensando)
    assert turno.contestando is not None
    assert conductor.a_quien_mira(turno.contestando) == "propietario"


@pieza("D", "si le miran, le hablan a él aunque no digan su nombre")
def test_si_le_miran_le_hablan_a_el_aunque_no_digan_su_nombre(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("propietario", x=0.5, mira_a_sirius=True))
    conductor.oye("Buenos días, Sirius.")
    conductor.reloj.avanza(conductor.segundos_de_charla() + 1)

    turno = conductor.mira_y_oye("propietario", "¿Qué hora es?")

    assert turno.turno.para_el
    [peticion] = conductor.peticiones_del_ultimo_turno()
    assert "¿Qué hora es?" in peticion.texto


@pieza("D", "si quien habla no le mira ni dice su nombre, fuera de la charla no es para él")
def test_si_quien_habla_no_le_mira_ni_dice_su_nombre_no_es_para_el(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(
        Persona("propietario", x=0.3, mira_a_sirius=False),
        Persona("Marta", x=0.8, mira_a_sirius=True),
    )
    conductor.oye("Buenos días, Sirius.")
    conductor.reloj.avanza(conductor.segundos_de_charla() + 1)

    turno = conductor.mira_y_oye("propietario", "¿Qué hora es?")

    assert not turno.turno.para_el
    assert turno.turno.contestado is None
    assert conductor.peticiones_del_ultimo_turno() == []


@pieza("D", "ninguna imagen sale ni se guarda mientras la cámara ve")
def test_ninguna_imagen_sale_ni_se_guarda(qtbot: QtBot, tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("propietario", x=0.3), Persona("Marta", x=0.7))
    conductor.ventana(qtbot)

    conductor.mira_un_rato(5.0)
    conductor.mira_y_oye("propietario", "Sirius, ¿quién hay aquí?")

    assert len(conductor.camara.dados) >= 2, "no ha mirado"
    assert conductor.conexiones_de_red() == []
    assert conductor.escrituras_en_disco() == []
    assert conductor.ficheros_nuevos() == []
    assert conductor.imagenes_guardadas() == []
