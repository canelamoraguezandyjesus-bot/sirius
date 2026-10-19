"""Pruebas de aceptación de la versión 0.4 del robot: recuerda lo que ve, como texto.

Salen de la sección 0.4 de ``docs/evolution/PLAN_DEL_ROBOT.md`` (§6, «Lo que se hace»,
8): quién vino, a qué hora y qué cambió, sin guardar imágenes. Llevan su ``PA-R04-14``
de ``docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md``, que lee «qué cambió» como lo que las
herramientas del plan pueden ver cambiar: quién llega, quién se va y cuántos hay. Cada
cambio se mira medio minuto, para que quien ignore un parpadeo de la cámara lo vea.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_2 import Peticion
from conductor_robot_0_4 import ConductorDeOjos, Persona, pieza

pytestmark = pytest.mark.acceptance


def _una_linea_con(peticion: Peticion, *trozos: str) -> bool:
    """Si alguna línea de lo que recibió el modelo lleva todos los ``trozos``."""
    return any(
        all(trozo in linea for trozo in trozos)
        for linea in f"{peticion.instrucciones}\n{peticion.texto}".splitlines()
    )


@pieza("G", "recuerda quién vino y a qué hora, como texto, también tras volver a abrir")
def test_recuerda_quien_vino_y_a_que_hora(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("Marta", x=0.5))
    conductor.da_permiso("Marta")
    conductor.son_las("18:00")
    conductor.delante(Persona("propietario", x=0.3))
    conductor.mira_un_rato(30.0)

    conductor.son_las("18:02")
    conductor.delante(Persona("propietario", x=0.3), Persona("Marta", x=0.7))
    conductor.mira_un_rato(30.0)
    conductor.son_las("18:10")
    conductor.delante(
        Persona("propietario", x=0.3), Persona("Marta", x=0.7), Persona("Pepe", x=0.9)
    )
    conductor.mira_un_rato(30.0)
    conductor.reabre()
    conductor.mira_y_oye("propietario", "Sirius, ¿quién ha venido?")

    [peticion] = conductor.peticiones_del_ultimo_turno()
    assert _una_linea_con(peticion, "Marta", "18:02")
    assert _una_linea_con(peticion, "sin identificar", "18:10")
    assert "Pepe" not in f"{peticion.instrucciones}\n{peticion.texto}"
    assert conductor.imagenes_guardadas() == []


@pieza("G", "recuerda quién se fue y cuántos hay ahora")
def test_recuerda_quien_se_fue_y_cuantos_hay(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("Marta", x=0.5))
    conductor.da_permiso("Marta")
    conductor.son_las("18:00")
    conductor.delante(Persona("propietario", x=0.3), Persona("Marta", x=0.7))
    conductor.mira_un_rato(30.0)

    conductor.son_las("18:30")
    conductor.delante(Persona("propietario", x=0.3))
    conductor.mira_un_rato(30.0)
    conductor.mira_y_oye("propietario", "Sirius, ¿se ha ido alguien?")

    [peticion] = conductor.peticiones_del_ultimo_turno()
    assert _una_linea_con(peticion, "Marta", "18:30")
    assert conductor.quienes_tiene_delante(peticion) == ["sin identificar"]
    assert conductor.imagenes_guardadas() == []
