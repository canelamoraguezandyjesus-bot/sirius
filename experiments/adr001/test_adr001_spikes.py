"""Pruebas de los spikes decisivos de ADR-001.

Se ejecutan de forma independiente y NO forman parte de la suite de Sirius
0.1: `pyproject.toml` fija `testpaths = ["tests"]`, asi que `uv run pytest`
no las recoge. Para lanzarlas explicitamente:

    uv run pytest experiments/adr001 -q

Cada spike se ejecuta dos veces desde una base limpia (``run_twice``); si
las dos pasadas no coinciden, el resultado se degrada a INCONCLUSIVE y la
prueba falla.
"""

from __future__ import annotations

import pytest
from experiments.adr001 import xmodel
from experiments.adr001.evidence import PASS, run_twice
from experiments.adr001.spikes_deletion import spike_10, spike_19
from experiments.adr001.spikes_migration import spike_15, spike_16
from experiments.adr001.spikes_model import (
    spike_01,
    spike_02,
    spike_03,
    spike_04,
    spike_05,
    spike_06,
    spike_07,
    spike_08,
    spike_17,
    spike_18,
)

# Las siete dimensiones canonicas, en su orden canonico.
DIMENSIONES_CANONICAS = (
    "confirmación",
    "validez",
    "disponibilidad",
    "sensibilidad",
    "temporalidad",
    "ámbito",
    "autoridad",
)

MODEL_SPIKES = [
    (1, spike_01),
    (2, spike_02),
    (3, spike_03),
    (4, spike_04),
    (5, spike_05),
    (6, spike_06),
    (7, spike_07),
    (8, spike_08),
    (17, spike_17),
    (18, spike_18),
]


@pytest.mark.parametrize(("numero", "spike"), MODEL_SPIKES, ids=[str(n) for n, _ in MODEL_SPIKES])
def test_spike_de_modelo_fisico_pasa(numero: int, spike) -> None:
    evidence = run_twice(spike)
    assert evidence.numero == numero
    assert evidence.resultado == PASS, (
        f"spike {numero} ({evidence.nombre}) termino en {evidence.resultado}: {evidence.evidencia}"
    )


@pytest.mark.parametrize(("numero", "spike"), [(10, spike_10), (19, spike_19)], ids=["10", "19"])
def test_spike_de_borrado_pasa(numero: int, spike) -> None:
    evidence = spike()
    assert evidence.numero == numero
    assert evidence.resultado == PASS, (
        f"spike {numero} ({evidence.nombre}) termino en {evidence.resultado}: {evidence.evidencia}"
    )


@pytest.mark.parametrize(("numero", "spike"), [(15, spike_15), (16, spike_16)], ids=["15", "16"])
def test_spike_de_migracion_pasa(numero: int, spike) -> None:
    evidence = run_twice(spike)
    assert evidence.numero == numero
    assert evidence.resultado == PASS, (
        f"spike {numero} ({evidence.nombre}) termino en {evidence.resultado}: {evidence.evidencia}"
    )


def test_spike_7_usa_exactamente_las_siete_dimensiones_canonicas() -> None:
    """Las siete canonicas sustituyen a las dimensiones experimentales de la v0.1."""
    assert xmodel.STATE_DIMENSIONS == DIMENSIONES_CANONICAS

    evidence = spike_07()
    assert evidence.evidencia["dimensiones_canonicas"] == list(DIMENSIONES_CANONICAS)
    assert evidence.evidencia["son_exactamente_siete"] is True
    assert evidence.evidencia["dimensiones_persistidas"] == 7
    assert evidence.evidencia["siete_dimensiones_representadas_de_forma_independiente"] is True


def test_spike_7_mutar_una_dimension_deja_intactas_las_otras_seis() -> None:
    evidence = spike_07()
    barrido = evidence.evidencia["barrido_una_dimension_a_la_vez"]

    assert set(barrido) == set(DIMENSIONES_CANONICAS)
    for dimension, medida in barrido.items():
        assert medida["cambio_aplicado"] is True, dimension
        assert medida["otras_dimensiones_comprobadas"] == 6, dimension
        assert medida["las_otras_seis_intactas"] is True, dimension
    assert evidence.evidencia["mutar_una_deja_intactas_las_otras_seis"] is True


def test_spike_7_coexisten_combinaciones_que_el_enum_monolitico_no_expresa() -> None:
    evidence = spike_07()

    distintas = evidence.evidencia["combinaciones_distintas_releidas"]
    assert distintas == evidence.evidencia["combinaciones_coexistentes_persistidas"]
    assert distintas > len(evidence.evidencia["valores_distintos_del_enum_heredado"])
    assert evidence.evidencia["mayor_grupo_de_combinaciones_que_colapsan_al_mismo_valor"] >= 2
    assert evidence.evidencia["el_enum_monolitico_no_puede_expresarlas"] is True
    assert evidence.evidencia["colapso_incluso_en_una_dimension_que_el_enum_roza"] is True


def test_spike_7_ambito_y_autoridad_no_se_colapsan() -> None:
    """Ni con confirmacion, ni con validez, ni con disponibilidad."""
    evidence = spike_07()
    evidencia = evidence.evidencia

    assert "ámbito" not in evidencia["dimensiones_que_el_enum_heredado_alcanza"]
    assert "autoridad" not in evidencia["dimensiones_que_el_enum_heredado_alcanza"]
    # Mismo triple (confirmacion, validez, disponibilidad) y aun asi ambito y
    # autoridad toman valores distintos: no son derivables de el.
    assert len(evidencia["ambitos_distintos_con_confirmacion_validez_disponibilidad_iguales"]) == 3
    assert (
        len(evidencia["autoridades_distintas_con_confirmacion_validez_disponibilidad_iguales"]) == 3
    )
    assert evidencia["valores_heredados_de_ese_grupo"] == ["current"]
    assert evidencia["enum_invariante_ante_ambito"] is True
    assert evidencia["enum_invariante_ante_autoridad"] is True
    assert evidencia["ambito_y_autoridad_no_se_colapsan"] is True


def test_spike_7_no_altera_las_tablas_heredadas() -> None:
    evidence = spike_07()

    assert evidence.evidencia["esquema_heredado_sin_cambios"] is True
    assert evidence.evidencia["recuentos_heredados_sin_cambios"] is True
    assert evidence.evidencia["tablas_heredadas_no_alteradas"] is True
    assert evidence.evidencia["0_1_intacto"] is True


def test_spike_7_sigue_siendo_experimental() -> None:
    """La correccion no fija DDL definitivo ni nombres fisicos productivos."""
    evidence = spike_07()

    assert evidence.evidencia["modelo_experimental"] is True
    assert evidence.evidencia["ddl_productivo_fijado"] is False
    assert evidence.evidencia["nombres_fisicos_productivos_fijados"] is False


def test_spike_7_se_repite_desde_base_limpia() -> None:
    evidence = run_twice(spike_07)

    assert evidence.resultado == PASS
    assert evidence.repeticion_limpia.startswith("reproducido desde base limpia")


def test_el_borrado_logico_no_purga_el_fichero() -> None:
    """Comprobacion explicita del hallazgo central del spike 10: marcar como
    borrado no elimina nada del fichero."""
    evidence = spike_10()
    assert evidence.evidencia["el_borrado_logico_no_purga"] is True


def test_el_dato_sobrevive_en_los_derivados_tras_borrar_lo_canonico() -> None:
    """Riesgo D-09: eliminar el contenido canonico no basta; los derivados
    conservan el dato hasta que se destruyen explicitamente."""
    evidence = spike_10()
    assert evidence.evidencia["tras_borrar_lo_canonico_el_dato_sobrevive_en_derivados"] is True


def test_la_migracion_no_escribe_en_sirius_0_1() -> None:
    evidence = spike_15()
    assert evidence.evidencia["0_1_byte_a_byte_igual"] is True
    assert evidence.evidencia["head_sin_cambios"] is True


def test_el_rollback_no_deja_residuo() -> None:
    evidence = spike_16()
    assert evidence.evidencia["residuo_experimental"] == []
    assert evidence.evidencia["esquema_completo_identico_al_inicial"] is True
