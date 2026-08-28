"""Adjudicación de cierre de `ADR-002`. **No mide: adjudica.**

Reúne todo lo medido —la ronda repetida, la readjudicación contra el canon, el
discriminante de nivel 4, los niveles 2 y 3, y el marcado de `M2`— y dice, por
participante, **si es conforme y por qué no**.

LA OBLIGACIÓN QUE SE PUBLICABA SIN ADJUDICAR
============================================

Las cinco puertas booleanas de la ronda son contaminación, fuga de ámbito,
fusión de polaridad, conformidad de etapa y borrado y regeneración.

**`B04-M01 · Recall crítico` no está entre ellas.** Su cifra
—``criticos_pendientes_total``— se publicó en todas las corridas y **nadie dijo
nunca si pasaba**. Y tiene umbral, y es el más duro del bloque:

    `B04-M01 · Recall crítico` — «Críticos recuperados / críticos elegibles»,
    umbral **«100% por caso»**.

    `§14 · R1 · Cobertura crítica` — «Puerta: una omisión crítica reproducible
    **elimina la alternativa**.»

    `§11 · G12` — «Todos los críticos elegibles se preservan o se declara
    desbordamiento bajo límite duro; **nunca se ocultan**.»

De modo que aquí se adjudica. Es el mismo hueco que tenía el marcado de `M2`
—obligación canónica publicada y sin veredicto—, y se cierra igual.

POR QUÉ ESTO NO ES CAMBIAR LA MEDICIÓN
======================================

Porque no se recalcula nada. ``metrics.criticos_pendientes`` ya contaba
exactamente lo que hace falta, y lo cuenta bien: excluye los críticos que el
límite duro dejó pendientes —el canon los permite si se declaran— y solo cuenta
los que la **referencia misma** esperaba y no se entregaron. Lo único que faltaba
era comparar esa cifra con su umbral y decirlo en voz alta.

El §8.1 prohíbe cambiar la medición después de observarla. Adjudicar una cifra ya
publicada con el umbral que su propia norma fija no es cambiarla: es terminar de
leerla.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]
SALIDA: Final = "artifacts/adr002_round/cierre_adr002_v0.1.json"

#: Lo medido, con su artefacto. Ninguno se recalcula aquí.
FUENTES: Final[Mapping[str, str]] = {
    "ronda": "artifacts/adr002_round/ronda_primaria_v0.4.json",
    "ronda_evidencia": "artifacts/adr002_round/ronda_primaria_v0.4_evidencia.json",
    "ronda_previa": "artifacts/adr002_round/ronda_primaria_v0.2.json",
    "readjudicacion": "artifacts/adr002_round/ronda_primaria_v0.3_readjudicada.json",
    "discriminante": "artifacts/adr002_round/discriminante_relacional_v0.1.json",
    "niveles_2_y_3": "artifacts/adr002_round/niveles_2_y_3_v0.2.json",
    "marcado_m2": "artifacts/adr002_round/marcado_de_m2_v0.2.json",
}

#: `B04-M01`, con su umbral literal y la consecuencia que el canon le asigna.
UMBRAL_DE_RECALL_CRITICO: Final = 0
CITA_M01: Final = (
    "B04-M01 · Recall critico: «Criticos recuperados / criticos elegibles», umbral "
    "«100% por caso». §14 R1 · Cobertura critica: «Puerta: una omision critica "
    "reproducible elimina la alternativa». §11 G12: «Todos los criticos elegibles se "
    "preservan o se declara desbordamiento bajo limite duro; nunca se ocultan»"
)

#: Por qué esta cifra no estaba adjudicada y ahora sí.
POR_QUE_NO_ESTABA: Final = (
    "las cinco puertas booleanas de la ronda no incluyen el recall critico: su cifra "
    "se publicaba en criticos_pendientes_total y nadie decia si pasaba. Es el mismo "
    "hueco que tenia el marcado de M2, y se cierra igual: comparando una cifra ya "
    "medida con el umbral que su propia norma fija"
)


@dataclass(frozen=True, slots=True)
class Veredicto:
    """Lo que un participante consigue, obligación por obligación."""

    participante: str
    contaminacion_cero: bool
    fuga_de_ambito_cero: bool
    confusion_de_polaridad_cero: bool
    conformidad_de_etapa: bool
    borrado_y_regeneracion: bool
    #: `B04-M01`, adjudicado por primera vez.
    recall_critico_completo: bool
    omisiones_criticas: int
    casos_con_omision_critica: tuple[str, ...]
    #: `B04 M2`, medido por el paquete de cierre.
    marcado_de_m2_completo: bool

    @property
    def conforme(self) -> bool:
        """Conforme es cumplirlas **todas**. Ninguna media compensa a otra."""
        return all(
            (
                self.contaminacion_cero,
                self.fuga_de_ambito_cero,
                self.confusion_de_polaridad_cero,
                self.conformidad_de_etapa,
                self.borrado_y_regeneracion,
                self.recall_critico_completo,
                self.marcado_de_m2_completo,
            )
        )

    @property
    def incumplimientos(self) -> tuple[str, ...]:
        nombres = (
            ("contaminacion_cero", self.contaminacion_cero),
            ("fuga_de_ambito_cero", self.fuga_de_ambito_cero),
            ("confusion_de_polaridad_cero", self.confusion_de_polaridad_cero),
            ("conformidad_de_etapa", self.conformidad_de_etapa),
            ("borrado_y_regeneracion", self.borrado_y_regeneracion),
            ("recall_critico_B04_M01", self.recall_critico_completo),
            ("marcado_de_M2", self.marcado_de_m2_completo),
        )
        return tuple(nombre for nombre, cumple in nombres if not cumple)


def omisiones_criticas_por_caso(
    evidencia: Mapping[str, Any], participante: str
) -> tuple[int, tuple[str, ...]]:
    """Los críticos que la referencia esperaba y no se entregaron.

    Se leen de la evidencia congelada, no se recalculan: ``metrics`` ya excluyó
    los que el límite duro dejó pendientes, que el canon permite **si se
    declaran**. Lo que queda son omisiones que ninguna norma excusa.
    """
    total = 0
    casos: list[str] = []
    for veredicto in evidencia["veredictos"][participante]:
        if not veredicto["adjudicable"]:
            continue
        pendientes = veredicto.get("criticos_pendientes") or ()
        if pendientes:
            total += len(pendientes)
            casos.append(veredicto["caso"])
    return total, tuple(casos)


def adjudicar(
    normativo: Mapping[str, Any],
    evidencia: Mapping[str, Any],
    readjudicacion: Mapping[str, Any],
    marcado: Mapping[str, Any],
) -> list[Veredicto]:
    """El veredicto de cierre. Lee lo medido y aplica los umbrales."""
    veredictos: list[Veredicto] = []
    for participante, resumen in normativo["conformidad"].items():
        puertas = resumen["puertas"]
        readjudicado = readjudicacion["por_participante"].get(participante, {})
        omisiones, casos = omisiones_criticas_por_caso(evidencia, participante)
        m2 = marcado["por_participante"].get(participante, {})
        veredictos.append(
            Veredicto(
                participante=participante,
                #: La readjudicación contra el canon manda donde se pronunció;
                #: donde no, rige la puerta tal como la ronda la midió.
                contaminacion_cero=bool(
                    readjudicado.get("contaminacion_cero", puertas["contaminacion_cero"])
                ),
                fuga_de_ambito_cero=bool(puertas["fuga_de_ambito_cero"]),
                confusion_de_polaridad_cero=bool(puertas["confusion_de_polaridad_cero"]),
                conformidad_de_etapa=bool(
                    readjudicado.get("conformidad_de_etapa", puertas["conformidad_de_etapa"])
                ),
                borrado_y_regeneracion=bool(puertas["borrado_y_regeneracion"]),
                recall_critico_completo=omisiones == UMBRAL_DE_RECALL_CRITICO,
                omisiones_criticas=omisiones,
                casos_con_omision_critica=casos,
                #: Quien no publica explicación no puede acreditar el marcado.
                #: No es un aprobado por omisión: es que no hay marca que leer.
                marcado_de_m2_completo=bool(m2.get("medible"))
                and bool(m2.get("m2_1_nunca_como_actual"))
                and bool(m2.get("m2_2_separa_tiempo_valido_de_corte"))
                and bool(m2.get("m2_3_distingue_los_tres_estados")),
            )
        )
    return veredictos


def documento(
    veredictos: Sequence[Veredicto], contraste: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """El artefacto de cierre. Dice qué falla y qué no separa a nadie."""
    incumplidas: dict[str, list[str]] = {}
    for veredicto in veredictos:
        for obligacion in veredicto.incumplimientos:
            incumplidas.setdefault(obligacion, []).append(veredicto.participante)
    candidatos = [v for v in veredictos if v.participante != "T0-control"]
    comunes = sorted(
        obligacion
        for obligacion, quienes in incumplidas.items()
        if all(c.participante in quienes for c in candidatos)
    )
    return {
        "documento": "Adjudicacion de cierre de ADR-002",
        "version_esquema": "cierre-adr002-0.1",
        "estado": "ADJUDICACION",
        "fuentes": dict(FUENTES),
        "no_mide": (
            "esta adjudicacion no ejecuta ninguna consulta ni recalcula ninguna cifra: "
            "lee lo medido y le aplica los umbrales que la norma fija"
        ),
        "obligacion_adjudicada_por_primera_vez": {
            "identificador": "B04-M01",
            "cita": CITA_M01,
            "por_que_no_estaba": POR_QUE_NO_ESTABA,
        },
        "por_participante": {
            v.participante: {
                "conforme": v.conforme,
                "incumple": list(v.incumplimientos),
                "omisiones_criticas": v.omisiones_criticas,
                "casos_con_omision_critica": list(v.casos_con_omision_critica),
                "marcado_de_m2_completo": v.marcado_de_m2_completo,
            }
            for v in veredictos
        },
        "incumplimientos_comunes_a_los_cuatro": comunes,
        "que_significa_lo_comun": (
            "una obligacion que los cuatro incumplen por igual no separa alternativas: "
            "no es un defecto que elegir otra evitaria, sino una condicion de cierre de "
            "ADR-002 que cualquiera arrastraria"
        ),
        "ninguno_conforme": not any(v.conforme for v in veredictos),
        "contraste_con_la_corrida_previa": dict(contraste or {}),
        "no_elige": (
            "esta adjudicacion no elige alternativa: dice quien es conforme, y si "
            "ninguno lo es, ADR-002 no puede cerrarse eligiendo"
        ),
    }


def cargar(nombre: str) -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(
        (RAIZ_REPOSITORIO / FUENTES[nombre]).read_text(encoding="utf-8")
    )
    return datos


def contraste_de_conformidad(
    actual: Mapping[str, Any], previa: Mapping[str, Any]
) -> dict[str, Any]:
    """Que la corrección **no movió** la conformidad. Es la comprobación clave.

    Si una sola cifra de conformidad hubiera cambiado, el paquete de cierre no
    habría sido de presentación: habría alterado la recuperación, y entonces la
    corrida previa dejaría de servir como término de comparación.
    """
    diferencias: dict[str, Any] = {}
    for participante, resumen in actual["conformidad"].items():
        antes = previa["conformidad"].get(participante, {})
        cambiadas = {
            clave: [antes.get(clave), valor]
            for clave, valor in resumen.items()
            if clave not in ("puertas",) and antes.get(clave) != valor
        }
        if cambiadas:
            diferencias[participante] = cambiadas
    return {
        "conformidad_identica": not diferencias,
        "diferencias": diferencias,
        "por_que_importa": (
            "el paquete de cierre solo cambio lo que se PUBLICA; si hubiera cambiado lo "
            "que se recupera, alguna cifra de conformidad se habria movido"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - punto de entrada
    del argv
    from experiments.adr002.tolerances.run_envelope import escribir_json_atomico

    normativo = cargar("ronda")
    evidencia = cargar("ronda_evidencia")
    previa = cargar("ronda_previa")
    veredictos = adjudicar(normativo, evidencia, cargar("readjudicacion"), cargar("marcado_m2"))
    contenido = documento(veredictos, contraste_de_conformidad(normativo, previa))
    escribir_json_atomico(RAIZ_REPOSITORIO / SALIDA, contenido)

    print(f"adjudicacion escrita: {SALIDA}")
    for veredicto in veredictos:
        marca = "CONFORME" if veredicto.conforme else "no conforme"
        print(
            f"  {veredicto.participante:12} {marca:12} incumple {list(veredicto.incumplimientos)}"
        )
    print(f"\ncomunes a los cuatro: {contenido['incumplimientos_comunes_a_los_cuatro']}")
    identica = contenido["contraste_con_la_corrida_previa"]["conformidad_identica"]
    print(f"conformidad identica a la corrida previa: {identica}")
    return 0


if __name__ == "__main__":  # pragma: no cover - punto de entrada
    raise SystemExit(main())
