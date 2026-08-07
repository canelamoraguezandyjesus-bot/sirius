"""Readjudicación de la ronda contra el canon. **No mide nada.**

Las tres resoluciones de
`SIRIUS_0.2_ADR_002_TRES_PREGUNTAS_ABIERTAS_RESUELTAS_CONTRA_EL_CANON_v1.0.md`
no cambian **lo que los participantes hicieron**: cambian **cómo se juzga**. Las
recuperaciones ya están medidas y publicadas, de modo que aquí no se ejecuta una
sola consulta: se releen los veredictos congelados de la corrida `v0.2` y se
vuelven a adjudicar con la lectura que el canon respalda.

POR QUÉ READJUDICAR Y NO VOLVER A MEDIR
=======================================

Porque volver a medir insinuaría que hay cifras nuevas, y no las hay. La
conformidad es determinista: una tercera corrida devolvería exactamente los
mismos conjuntos. Lo único que cambia es el criterio, y separar el criterio de
la medición es justamente lo que permite comprobar que **la medición no se tocó**.

POR QUÉ LA MÉTRICA ORIGINAL NO SE MODIFICA
==========================================

``metrics.etapa_conforme`` es la que produjo las cifras publicadas de `v0.1` y
`v0.2`. Reescribirla dejaría el repositorio sin forma de recomputar lo que se
publicó, y el §8.1 del protocolo prohíbe cambiar la medición después de
observarla —con más razón si el cambio sube los números, aunque el cambio sea
correcto—. De modo que **no se toca**: la lectura corregida vive aquí, aparte,
y las dos conviven.

LAS TRES RESOLUCIONES, CADA UNA CON SU CITA
===========================================

1. **`B04-CA-04` deja de puntuar.** El canon ordena «completitud crítica antes
   que reducción de ruido» y la pertinencia que nombra es **al ámbito**; los dos
   distractores están en ámbito. No hay eje canónico por el que un candidato
   pueda excluirlos sin leer el oráculo.
2. **`DEC-003` deja de estar prohibida en `B04-CA-05`.** `M2` «permite archivado,
   sustituido y finalizado… y nunca lo presenta como actual»: amplía la
   elegibilidad, no la restringe. La exclusión de lo vigente no está escrita.
3. **La etapa declarada se lee como cota.** «Solo se expande cuando falta
   suficiencia o críticos», y el ejemplo canónico resuelve una consulta `EXACTA`
   en `E1`. Resolver antes de lo declarado es obedecer la política escalonada.

Y una guarda que la primera versión de este cálculo no tenía: **quien no recorre
`E0-E5` no conforma**. Sin ella, el control pasaba de `0/46` a `46/46` por
cumplir «sin saltos» en el vacío, que es peor defecto que el que se venía a
corregir.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

#: Corrida readjudicada y destino. La `v0.2` no se toca.
ORIGEN: Final = "artifacts/adr002_round/ronda_primaria_v0.2_evidencia.json"
ORIGEN_NORMATIVO: Final = "artifacts/adr002_round/ronda_primaria_v0.2.json"
SALIDA: Final = "artifacts/adr002_round/ronda_primaria_v0.3_readjudicada.json"

VERSION_ESQUEMA: Final = "readjudicacion-ronda-adr002-0.1"
RESOLUCIONES: Final = "SIRIUS_0.2_ADR_002_TRES_PREGUNTAS_ABIERTAS_RESUELTAS_CONTRA_EL_CANON_v1.0.md"

ORDEN: Final[tuple[str, ...]] = ("E0", "E1", "E2", "E3", "E4", "E5")
EXPANSION: Final[tuple[str, ...]] = ("E1", "E2", "E3", "E4")

#: Casos que dejan de puntuar, con la cita que lo justifica.
NO_ADJUDICABLES_ANADIDOS: Final[Mapping[str, str]] = {
    "B04-CA-04": (
        "B04: «Completitud critica antes que reduccion de ruido» y elegibilidad "
        "«pertinente al ambito»; los dos DISTRACTOR_RUIDO estan en ambito y no hay "
        "eje canonico por el que excluirlos sin leer el oraculo"
    ),
}

#: Prohibidos que se retiran, con la cita que lo justifica. Retirar un prohibido
#: **afloja** un control, de modo que la cita tiene que ser literal o no vale.
PROHIBIDOS_RETIRADOS: Final[Mapping[str, tuple[tuple[str, ...], str]]] = {
    "B04-CA-05": (
        ("DECISION:3",),
        "B04 M2 · Historico explicito: «Permite archivado, sustituido y finalizado "
        "con marcas temporales; separa tiempo valido de corte de registro y nunca lo "
        "presenta como actual». M2 amplia la elegibilidad; la exclusion de lo vigente "
        "no esta escrita",
    ),
}

#: Lo que el canon **si** exige de `M2` y ninguna metrica comprueba todavia.
PENDIENTE_DE_MEDIR: Final[tuple[str, ...]] = (
    "en M2, lo sustituido debe volver marcado y nunca presentarse como actual "
    "(B04 M2): ninguna metrica de esta ronda lo comprueba",
)


@dataclass(frozen=True, slots=True)
class Readjudicado:
    """Lo que la lectura corregida da para un participante."""

    participante: str
    casos_adjudicados: int
    contaminacion_total: int
    contaminacion_por_caso: Mapping[str, tuple[str, ...]]
    etapa_conforme: int
    etapa_puntuable: int
    casos_retirados: tuple[str, ...]


def _origen_de(razon: str) -> str | None:
    """La etapa que aportó el resultado, tal como el veredicto la registró."""
    if "resuelto en " not in razon:
        return None
    return razon.split("resuelto en ")[1][:2]


def etapa_conforme_por_cota(
    etapas_recorridas: Sequence[str], etapa_declarada: str, razon: str
) -> bool:
    """Sin saltos y resuelto **en o antes** de la etapa declarada.

    Quien no recorre ninguna etapa **no conforma**: no es que conforme pronto,
    es que no hay política escalonada que juzgar. Sin esta guarda el control de
    falsación pasaba de cero a pleno por cumplir «sin saltos» en el vacío.
    """
    if not etapas_recorridas:
        return False
    recorridas = [e for e in etapas_recorridas if e in EXPANSION]
    posiciones = [EXPANSION.index(e) for e in recorridas]
    if posiciones != sorted(posiciones) or len(set(posiciones)) != len(posiciones):
        return False
    if posiciones and posiciones != list(range(len(posiciones))):
        return False
    if etapa_declarada in ("E0", "E5"):
        return True
    origen = _origen_de(razon)
    if origen is None:
        return True
    return ORDEN.index(origen) <= ORDEN.index(etapa_declarada)


def readjudicar(evidencia: Mapping[str, Any]) -> dict[str, Readjudicado]:
    """Vuelve a adjudicar los veredictos congelados. **No ejecuta nada.**"""
    casos = {c["caso"]: c for c in evidencia["casos"]}
    canonicos = {c["caso"]: c["canonico"] for c in evidencia["casos"]}

    resultado: dict[str, Readjudicado] = {}
    for participante, veredictos in evidencia["veredictos"].items():
        contaminacion: dict[str, tuple[str, ...]] = {}
        retirados: list[str] = []
        conformes = puntuables = adjudicados = 0
        for v in veredictos:
            canonico = canonicos[v["caso"]]
            if not v["adjudicable"] or canonico in NO_ADJUDICABLES_ANADIDOS:
                if canonico in NO_ADJUDICABLES_ANADIDOS and v["adjudicable"]:
                    retirados.append(v["caso"])
                continue
            adjudicados += 1

            perdonados = frozenset(PROHIBIDOS_RETIRADOS.get(canonico, ((), ""))[0])
            restantes = tuple(i for i in v["contaminacion"] if i not in perdonados)
            if restantes:
                contaminacion[v["caso"]] = restantes

            if v["etapa_puntua"]:
                puntuables += 1
                conformes += etapa_conforme_por_cota(
                    v["etapas_recorridas"], casos[v["caso"]]["etapa_esperada"], v["razon_de_etapa"]
                )
        resultado[participante] = Readjudicado(
            participante=participante,
            casos_adjudicados=adjudicados,
            contaminacion_total=sum(len(v) for v in contaminacion.values()),
            contaminacion_por_caso=contaminacion,
            etapa_conforme=conformes,
            etapa_puntuable=puntuables,
            casos_retirados=tuple(sorted(set(retirados))),
        )
    return resultado


def documento(
    publicado: Mapping[str, Any], readjudicado: Mapping[str, Readjudicado]
) -> dict[str, Any]:
    """El artefacto de readjudicación. Publica **las dos** lecturas."""
    return {
        "documento": "Readjudicacion de la ronda primaria de ADR-002 contra el canon",
        "version_esquema": VERSION_ESQUEMA,
        "estado": "READJUDICACION",
        "resoluciones": RESOLUCIONES,
        "origen": ORIGEN,
        "no_es_una_medicion": (
            "no se ejecuto ninguna consulta: se releen los veredictos congelados de "
            "la corrida v0.2 y se vuelven a adjudicar. Las cifras publicadas de v0.1 "
            "y v0.2 no se modifican"
        ),
        "resoluciones_aplicadas": {
            "casos_que_dejan_de_puntuar": dict(NO_ADJUDICABLES_ANADIDOS),
            "prohibidos_retirados": {
                caso: {"identidades": list(ids), "cita": cita}
                for caso, (ids, cita) in PROHIBIDOS_RETIRADOS.items()
            },
            "etapa_declarada_leida_como_cota": (
                "B04: «Solo se expande cuando falta suficiencia o criticos». Resolver "
                "antes de la etapa declarada es obedecer la politica escalonada, no "
                "incumplir RF-14, que prohibe el salto y el barrido"
            ),
        },
        "pendiente_de_medir": list(PENDIENTE_DE_MEDIR),
        "por_participante": {
            p: {
                "casos_adjudicados": r.casos_adjudicados,
                "casos_retirados": list(r.casos_retirados),
                "contaminacion_publicada": publicado["conformidad"][p]["contaminacion_total"],
                "contaminacion_readjudicada": r.contaminacion_total,
                "contaminacion_por_caso": {k: list(v) for k, v in r.contaminacion_por_caso.items()},
                "etapa_publicada": publicado["conformidad"][p]["casos_con_etapa_conforme"],
                "etapa_readjudicada": r.etapa_conforme,
                "etapa_puntuable": r.etapa_puntuable,
                "contaminacion_cero": r.contaminacion_total == 0,
                "conformidad_de_etapa": r.etapa_conforme == r.etapa_puntuable,
            }
            for p, r in readjudicado.items()
        },
        "no_elige": (
            "esta readjudicacion no elige alternativa ni cierra ADR-002: corrige el "
            "criterio con el que se leen unas cifras que no cambian"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Lee la evidencia congelada, readjudica y escribe. No mide."""
    del argv
    from experiments.adr002.tolerances.run_envelope import escribir_json_atomico

    evidencia = json.loads((RAIZ_REPOSITORIO / ORIGEN).read_text(encoding="utf-8"))
    publicado = json.loads((RAIZ_REPOSITORIO / ORIGEN_NORMATIVO).read_text(encoding="utf-8"))
    resultado = readjudicar(evidencia)
    escribir_json_atomico(RAIZ_REPOSITORIO / SALIDA, documento(publicado, resultado))

    print(f"readjudicacion escrita: {SALIDA}")
    for p, r in resultado.items():
        print(
            f"  {p:12} contaminacion {publicado['conformidad'][p]['contaminacion_total']}"
            f" -> {r.contaminacion_total}   etapa "
            f"{publicado['conformidad'][p]['casos_con_etapa_conforme']}"
            f" -> {r.etapa_conforme}/{r.etapa_puntuable}"
        )
    print("Ninguna cifra medida ha cambiado: solo el criterio con que se leen.")
    return 0


if __name__ == "__main__":  # pragma: no cover - punto de entrada
    raise SystemExit(main())
