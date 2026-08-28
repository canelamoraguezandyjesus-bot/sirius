"""Ejecuta los 14 spikes decisivos y vuelca la evidencia reproducible.

uv run python -m experiments.adr001.run_all
"""

from __future__ import annotations

import time

from experiments.adr001.evidence import (
    FAIL_ENGINE_SQLITE,
    FAIL_STRUCTURAL_MODEL,
    INCONCLUSIVE,
    PASS,
    SpikeEvidence,
    run_twice,
    write_bundle,
)
from experiments.adr001.spikes_deletion import spike_10, spike_19
from experiments.adr001.spikes_migration import spike_15, spike_16
from experiments.adr001.spikes_model import ALL_MODEL_SPIKES

DECISION_RATIFICAR_A = "RATIFICAR A"
DECISION_ESCALAR_B = "ESCALAR A B"
DECISION_ABRIR_C = "ABRIR CONTINGENCIA C"
DECISION_BLOQUEADA = "DECISION BLOQUEADA"


def decide(evidences: list[SpikeEvidence]) -> str:
    """Aplica literalmente la regla final del §5 del paquete operativo."""
    por_numero = {evidence.numero: evidence.resultado for evidence in evidences}

    if any(resultado == INCONCLUSIVE for resultado in por_numero.values()):
        return DECISION_BLOQUEADA

    estructurales = [1, 2, 3, 4, 5, 6, 7, 8, 15, 16, 17, 18]
    if any(por_numero.get(numero) == FAIL_STRUCTURAL_MODEL for numero in estructurales):
        return DECISION_ESCALAR_B

    if any(por_numero.get(numero) == FAIL_ENGINE_SQLITE for numero in (10, 19)):
        return DECISION_ABRIR_C

    if all(resultado == PASS for resultado in por_numero.values()):
        return DECISION_RATIFICAR_A

    return DECISION_BLOQUEADA


def main() -> int:
    started = time.perf_counter()
    evidences: list[SpikeEvidence] = []

    for spike in ALL_MODEL_SPIKES:
        evidences.append(run_twice(spike))
    # Los spikes de borrado ya ejecutan internamente dos bases limpias
    # (con y sin rebuild de FTS5, y dos escenarios de journal), asi que su
    # repeticion se declara a partir de esas pasadas.
    for spike in (spike_10, spike_19):
        evidence = spike()
        evidence.repeticion_limpia = (
            "ejecutado sobre bases limpias independientes dentro del propio spike "
            "(dos pasadas en el 10; escenarios WAL y secure_delete=0 en el 19)"
        )
        evidences.append(evidence)
    for spike in (spike_15, spike_16):
        evidences.append(run_twice(spike))

    evidences.sort(key=lambda evidence: evidence.numero)
    bundle = write_bundle(evidences, "evidencia_spikes.json")
    decision = decide(evidences)
    elapsed = time.perf_counter() - started

    print(f"evidencia: {bundle}")
    for evidence in evidences:
        print(f"  spike {evidence.numero:>2}  {evidence.resultado:<22} {evidence.nombre}")
    print(f"\nDECISION: {decision}")
    print(f"duracion total: {elapsed:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
