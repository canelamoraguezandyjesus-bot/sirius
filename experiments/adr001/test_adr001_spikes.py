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
