"""Pruebas de aceptación de la versión 0.4 del robot: reconocer a quien dé permiso.

Salen de la sección 0.4 de ``docs/evolution/PLAN_DEL_ROBOT.md`` (§6, «Lo que se hace»,
2, y «Terminado cuando», 2), y llevan su ``PA-R04-NN`` de
``docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md``. Quien no ha dado permiso, el propietario
incluido, es «sin identificar»: Sirius no tiene con qué reconocerle.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_4 import ConductorDeOjos, Persona, huella_de_cara, huella_de_voz, pieza

pytestmark = pytest.mark.acceptance


@pieza("E", "reconoce por la cara a quien dio permiso")
def test_reconoce_por_la_cara_a_quien_dio_permiso(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("Marta", x=0.5))
    conductor.da_permiso("Marta")

    conductor.delante(Persona("propietario", x=0.3), Persona("Marta", x=0.7))
    conductor.mira_y_oye("propietario", "Sirius, ¿quién está conmigo?")

    [peticion] = conductor.peticiones_del_ultimo_turno()
    assert huella_de_cara("Marta") in conductor.caras.dadas
    assert conductor.quienes_tiene_delante(peticion) == ["Marta", "sin identificar"]
    assert conductor.quien_le_habla(peticion) == "sin identificar"
    assert "insightface" in conductor.herramientas_de_reconocer()


@pieza("E", "reconoce por la voz a quien dio permiso")
def test_reconoce_por_la_voz_a_quien_dio_permiso(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("Marta", x=0.5))
    conductor.da_permiso("Marta")
    conductor.delante()

    conductor.oye_a("Marta", "Sirius, ¿sabes quién soy?")

    [peticion] = conductor.peticiones_del_ultimo_turno()
    assert huella_de_voz("Marta") in conductor.voces.dadas
    assert conductor.quien_le_habla(peticion) == "Marta"
    assert "speechbrain-ecapa" in conductor.herramientas_de_reconocer()


@pieza("E", "a un desconocido lo trata como «sin identificar» y no guarda su huella")
def test_a_un_desconocido_lo_trata_como_sin_identificar_y_no_guarda_su_huella(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("Marta", x=0.5))
    conductor.da_permiso("Marta")
    antes = conductor.huellas_guardadas()
    conductor.delante(Persona("Marta", x=0.3), Persona("Pepe", x=0.7))

    conductor.mira_y_oye("Pepe", "Sirius, hola, soy yo.")

    [peticion] = conductor.peticiones_del_ultimo_turno()
    assert huella_de_cara("Pepe") in conductor.caras.dadas, "no le ha mirado la cara"
    assert huella_de_voz("Pepe") in conductor.voces.dadas, "no le ha oído la voz"
    assert conductor.quien_le_habla(peticion) == "sin identificar"
    assert conductor.quienes_tiene_delante(peticion) == ["Marta", "sin identificar"]
    assert conductor.huellas_guardadas() == antes
    assert conductor.huellas_en_claro() == []


@pieza("E", "las huellas van cifradas, no salen del ordenador y sirven al volver a abrir")
def test_las_huellas_van_cifradas_y_no_salen_del_ordenador(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("Marta", x=0.5))

    conductor.da_permiso("Marta")

    assert huella_de_cara("Marta") in conductor.caras.dadas
    assert huella_de_voz("Marta") in conductor.voces.dadas
    assert conductor.huellas_guardadas() >= 2, "la de su cara y la de su voz"
    assert conductor.huellas_en_claro() == []
    assert conductor.escrituras_en_disco() == []
    assert conductor.conexiones_de_red() == []
    conductor.reabre()
    conductor.delante(Persona("propietario", x=0.3), Persona("Marta", x=0.7))
    conductor.mira_y_oye("propietario", "Sirius, ¿quién está conmigo?")
    [peticion] = conductor.peticiones_del_ultimo_turno()
    assert conductor.quienes_tiene_delante(peticion) == ["Marta", "sin identificar"]


@pieza("E", "al quitar el permiso se borran sus huellas y deja de reconocerle")
def test_al_quitar_el_permiso_se_borran_sus_huellas(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("Marta", x=0.5))
    conductor.da_permiso("Marta")
    assert conductor.huellas_guardadas() >= 2

    conductor.quita_el_permiso("Marta")

    assert conductor.huellas_guardadas() == 0
    conductor.delante(Persona("propietario", x=0.3), Persona("Marta", x=0.7))
    conductor.mira_y_oye("Marta", "Sirius, ¿todavía me conoces?")
    [peticion] = conductor.peticiones_del_ultimo_turno()
    assert conductor.quien_le_habla(peticion) == "sin identificar"
    assert conductor.quienes_tiene_delante(peticion) == ["sin identificar", "sin identificar"]
