"""Pruebas de aceptación de la versión 0.4 del robot: la regla de los críos y los ancianos.

Salen de la sección 0.4 de ``docs/evolution/PLAN_DEL_ROBOT.md`` (§6, «Lo que se hace»,
3, y «Terminado cuando», 3): estima la edad con la cámara y, ante la duda, no insulta.
Llevan su ``PA-R04-13`` de ``docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md``. Lo que miran es
que la regla llega al modelo; que el modelo la cumpla lo dice E-R04-04.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_4 import ConductorDeOjos, Persona, pieza

pytestmark = pytest.mark.acceptance


def _lleva_la_regla(conductor: ConductorDeOjos, *delante: Persona) -> bool:
    conductor.delante(Persona("propietario", x=0.2), *delante)
    conductor.mira_y_oye("propietario", "Sirius, dime algo, anda.")
    [peticion] = conductor.peticiones_del_ultimo_turno()
    return conductor.lleva_la_regla_de_no_insultar(peticion)


@pieza("F", "con un crío delante, la petición lleva la regla de no insultar")
def test_con_un_crio_delante_la_peticion_lleva_la_regla_de_no_insultar(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)

    assert _lleva_la_regla(conductor, Persona("Lucas", x=0.8, edad=8))
    assert (8, True) in conductor.edades.estimadas
    assert "insightface" in conductor.herramientas_de_la_edad()


@pieza("F", "con un anciano delante, también")
def test_con_un_anciano_delante_tambien(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)

    assert _lleva_la_regla(conductor, Persona("Carmen", x=0.8, edad=86))
    assert (86, True) in conductor.edades.estimadas


@pieza("F", "ante la duda, también")
def test_ante_la_duda_tambien(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)

    assert _lleva_la_regla(conductor, Persona("alguien", x=0.8, edad=30, edad_segura=False))
    assert (30, False) in conductor.edades.estimadas


@pieza("F", "con solo adultos delante, no la lleva")
def test_con_solo_adultos_no_la_lleva(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)

    assert not _lleva_la_regla(conductor, Persona("Marta", x=0.8, edad=40))
    assert (40, True) in conductor.edades.estimadas
