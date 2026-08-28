"""Reejecuta ÚNICAMENTE el spike 7 corregido y produce la evidencia v0.2.

    uv run python -m experiments.adr001.run_spike7_v02

Los otros trece spikes NO se reejecutan: sus entradas se arrastran literalmente
desde ``evidencia_spikes.json`` (v0.1). Este runner solo sustituye la entrada
del spike 7 y vuelve a aplicar la regla de decisión del §5 del paquete
operativo sobre el conjunto resultante.
"""

from __future__ import annotations

import json
from typing import Any

from experiments.adr001.evidence import (
    ARTIFACTS_DIR,
    PASS,
    SpikeEvidence,
    run_twice,
    write_bundle,
)
from experiments.adr001.run_all import decide
from experiments.adr001.spikes_model import spike_07

BUNDLE_V01 = "evidencia_spikes.json"
BUNDLE_V02 = "evidencia_spikes_v0.2.json"
TRAZA = "06_spike7_corregido.txt"


def _cargar_v01() -> list[dict[str, Any]]:
    payload = json.loads((ARTIFACTS_DIR / BUNDLE_V01).read_text(encoding="utf-8"))
    return [dict(entry) for entry in payload]


def _como_evidencia(entry: dict[str, Any]) -> SpikeEvidence:
    return SpikeEvidence(**entry)


def main() -> int:
    # Evidencia oficial: dos pasadas desde bases limpias independientes.
    oficial = run_twice(spike_07)

    # Comprobación adicional de reproducibilidad: dos pasadas más, esta vez
    # comparando la evidencia COMPLETA y no solo el veredicto.
    primera = spike_07()
    segunda = spike_07()
    mismo_veredicto = primera.resultado == segunda.resultado
    misma_evidencia = primera.evidencia == segunda.evidencia

    v01 = _cargar_v01()
    arrastradas = [entry for entry in v01 if int(entry["numero"]) != 7]
    if len(arrastradas) != 13:
        raise SystemExit(f"se esperaban 13 spikes arrastrados, hay {len(arrastradas)}")

    evidencias = [_como_evidencia(entry) for entry in arrastradas]
    evidencias.append(oficial)
    evidencias.sort(key=lambda evidence: evidence.numero)

    destino = write_bundle(evidencias, BUNDLE_V02)
    decision = decide(evidencias)
    todos_pass = all(evidence.resultado == PASS for evidence in evidencias)

    lineas: list[str] = []
    add = lineas.append
    add("SPIKE 7 CORREGIDO — siete dimensiones canónicas")
    add("=" * 62)
    add("")
    add("Dimensiones canónicas empleadas (sustituyen a las experimentales de v0.1):")
    for indice, dimension in enumerate(oficial.evidencia["dimensiones_canonicas"], start=1):
        add(f"  {indice}. {dimension}")
    add("")
    add(f"resultado                 : {oficial.resultado}")
    add(f"repetición                : {oficial.repeticion_limpia}")
    add(f"mismo veredicto 3ª/4ª base: {mismo_veredicto}")
    add(f"evidencia íntegra idéntica: {misma_evidencia}")
    add("")
    add("Comprobaciones exigidas")
    add("-" * 62)
    for etiqueta, clave in (
        (
            "siete dimensiones representadas de forma independiente",
            "siete_dimensiones_representadas_de_forma_independiente",
        ),
        ("mutar una deja intactas las otras seis", "mutar_una_deja_intactas_las_otras_seis"),
        (
            "el enum monolítico no puede expresar las combinaciones",
            "el_enum_monolitico_no_puede_expresarlas",
        ),
        (
            "colapso incluso en una dimensión que el enum roza",
            "colapso_incluso_en_una_dimension_que_el_enum_roza",
        ),
        ("ámbito y autoridad no se colapsan", "ambito_y_autoridad_no_se_colapsan"),
        ("tablas heredadas no alteradas", "tablas_heredadas_no_alteradas"),
        ("huella de Sirius 0.1 idéntica", "0_1_intacto"),
        ("sigue siendo modelo experimental", "modelo_experimental"),
        ("DDL productivo fijado", "ddl_productivo_fijado"),
        ("nombres físicos productivos fijados", "nombres_fisicos_productivos_fijados"),
    ):
        add(f"  {oficial.evidencia[clave]!s:<6} {etiqueta}")
    add("")
    add("Barrido dimensión a dimensión")
    add("-" * 62)
    for dimension, medida in oficial.evidencia["barrido_una_dimension_a_la_vez"].items():
        add(
            f"  {dimension:<14} {medida['valor_anterior']} -> {medida['valor_nuevo']:<12} "
            f"otras {medida['otras_dimensiones_comprobadas']} intactas: "
            f"{medida['las_otras_seis_intactas']}"
        )
    add("")
    add("Expresividad comparada")
    add("-" * 62)
    add(
        f"  combinaciones canónicas distintas coexistiendo : "
        f"{oficial.evidencia['combinaciones_distintas_releidas']}"
    )
    add(
        f"  valores distintos del enum heredado            : "
        f"{oficial.evidencia['valores_distintos_del_enum_heredado']}"
    )
    add(
        f"  mayor grupo que colapsa al mismo valor         : "
        f"{oficial.evidencia['mayor_grupo_de_combinaciones_que_colapsan_al_mismo_valor']}"
    )
    add(
        f"  ámbitos distintos con el mismo triple heredado : "
        f"{oficial.evidencia['ambitos_distintos_con_confirmacion_validez_disponibilidad_iguales']}"
    )
    add(
        f"  autoridades distintas con el mismo triple      : "
        f"{oficial.evidencia['autoridades_distintas_con_confirmacion_validez_disponibilidad_iguales']}"
    )
    add(
        f"  valor heredado de todo ese grupo              : "
        f"{oficial.evidencia['valores_heredados_de_ese_grupo']}"
    )
    add("")
    add("Conjunto de los 14 spikes tras la corrección")
    add("-" * 62)
    for evidence in evidencias:
        add(f"  spike {evidence.numero:>2}  {evidence.resultado:<12} {evidence.nombre}")
    add("")
    add(f"los 14 en PASS : {todos_pass}")
    add(f"DECISIÓN       : {decision}")
    add(f"evidencia v0.2 : {destino}")
    add("")
    add("Los spikes 1-6, 8, 10 y 15-19 NO se reejecutaron: sus entradas se")
    add("arrastran literalmente desde evidencia_spikes.json (v0.1).")

    traza = ARTIFACTS_DIR / TRAZA
    traza.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    print("\n".join(lineas))
    print(f"\ntraza: {traza}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
