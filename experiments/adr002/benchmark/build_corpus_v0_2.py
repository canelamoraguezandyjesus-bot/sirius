"""Generador v0.2: corrige el corpus v0.1 sin rehacerlo y separa los dos corpus.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.build_corpus_v0_2

Qué corrige, y por qué así:

* **B-01** · las asignaciones `RED -> CA / métrica / familia` se leen del
  **Anexo B del DOCX**, no de una tabla escrita a mano. Lo que el v0.1 añadía
  por su cuenta se conserva como `..._adicional_derivada`, nunca sustituyendo
  al canon.
* **B-02 / M-07** · cada caso separa un bloque `canonico` —los cuatro campos
  que B04 §17/§17.1 fija literalmente, tomados del DOCX— de un bloque
  `instanciacion` con la **fuente individual de cada campo**. Cardinalidad,
  etapa, parada y modo solo se marcan `CANONICO` cuando el texto canónico del
  propio caso los nombra.
* **B-03** · desaparece todo veredicto frente a T0. Queda
  `estado_t0: NO_MEDIDO` más una previsión con su fundamento.
* **M-01 / M-02** · las ramas canónicas se instancian dentro del mismo ID
  canónico: M4 en CA-09/10/24/49 y las ramas diferenciadas de CA-36/47/48.
* **M-03** · los catorce campos de la ficha del PDP §7, más la condición de
  insuficiencia por transición que la Especificación §5 campo 12 exige.
* **M-04** · los `PDP-CA` aplicables se instancian; el resto va a una matriz
  de exclusión con su ADR responsable.
* **M-05** · dos corpus: conformidad y rendimiento a la escala de TOL-208.

No ejecuta T0, no ejecuta candidatos y no mide nada. El v0.1 queda intacto.
"""

from __future__ import annotations

import itertools
import json
import random
import re
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import build_corpus as V1
from experiments.adr002.benchmark import canonical_source as CS
from experiments.adr002.benchmark import schema_v0_2 as S2

AQUI = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 1. Anclajes añadidos para hacer falsables las ramas canónicas
# ---------------------------------------------------------------------------
# El §3.1 del paquete 03B autoriza ajustar el corpus «para hacer falsables las
# ramas canónicas». CA-47 exige que las consultas por occurred_at, valid_time y
# recorded_at devuelvan resultados DISTINTOS: con un solo elemento eso es
# imposible de comprobar, y el fallo observable «colapsa las tres fechas» sería
# indetectable por construcción.
#
#            occurred_at   valid_from..valid_to     recorded_at
# DEC-011    2026-01-12    2026-02-01 ..            2026-03-08
# DEC-014    2026-03-05    2026-01-15 .. 2026-01-31 2026-01-20
# DEC-015    2026-01-20    2026-03-01 ..            2026-01-25
#
# occurred_at en enero      -> {DEC-011, DEC-015}
# valid_time el 2026-01-20  -> {DEC-014}
# corte de registro 02-15   -> {DEC-014, DEC-015}
#
# Tres conjuntos distintos: ningún sistema que colapse los tres ejes en «más
# reciente» puede producirlos.

ITEMS_ANADIDOS: list[dict[str, Any]] = [
    V1._item(
        "DEC-014",
        "DECISION",
        "PRJ-BETA",
        "Se habilita el turno reducido de enero.",
        autoridad="DOCUMENTO_CANONICO",
        temporalidad=V1._temporalidad(
            valid_from="2026-01-15T00:00:00Z",
            valid_to="2026-01-31T00:00:00Z",
            occurred_at="2026-03-05T00:00:00Z",
            recorded_at="2026-01-20T00:00:00Z",
        ),
        traza=["B04-CA-47"],
    ),
    V1._item(
        "DEC-015",
        "DECISION",
        "PRJ-BETA",
        "Se adjudica la revisión trimestral al área de operaciones.",
        autoridad="DOCUMENTO_CANONICO",
        temporalidad=V1._temporalidad(
            valid_from="2026-03-01T00:00:00Z",
            occurred_at="2026-01-20T00:00:00Z",
            recorded_at="2026-01-25T00:00:00Z",
        ),
        traza=["B04-CA-47"],
    ),
]

# ---------------------------------------------------------------------------
# 2. Ramas canónicas requeridas
# ---------------------------------------------------------------------------
# Se instancian DENTRO del mismo identificador canónico: no se crea ningún CA
# nuevo. Cada rama declara la cláusula canónica de la que procede.


def _rama(
    sufijo: str,
    objetivo: str,
    fuente: str,
    *,
    modo: str,
    consulta: str,
    elegibles: list[str],
    prohibidos: list[str],
    esperado_rama: str,
    estado_suficiencia: str,
    clase: str = "CANONICA_REQUERIDA",
    ambito: str | None = None,
    tiempo_objetivo: str | None = None,
    corte_registro: str | None = None,
    proposito: str | None = None,
    permiso: str | None = None,
    tolerancia_pendiente: str | None = None,
) -> dict[str, Any]:
    return {
        "sufijo": sufijo,
        "clase": clase,
        "objetivo": objetivo,
        "fuente_canonica_de_la_rama": fuente,
        "modo": modo,
        "consulta": consulta,
        "proposito": proposito,
        "permiso": permiso,
        "ambito": ambito,
        "tiempo_objetivo": tiempo_objetivo,
        "corte_registro": corte_registro,
        "candidatos_elegibles": elegibles,
        "candidatos_prohibidos": prohibidos,
        "esperado_rama": esperado_rama,
        "estado_suficiencia_esperado": estado_suficiencia,
        "tolerancia_pendiente": tolerancia_pendiente,
    }


_AHORA = S2.AHORA_DECLARADO
TOLERANCIA_PENDIENTE_RAMA = "RED-032 / ADR002-TOL-201: banda de texto, estado, conteo y tiempo"

RAMAS: dict[str, list[dict[str, Any]]] = {
    # -- M-01 · el lado M4 que el canon exige y el v0.1 no instanciaba -------
    "B04-CA-09": [
        _rama(
            "R1",
            "Comprobar que la candidata no entra en recuperación ordinaria.",
            "B04 §17 CA-09 «Fuera de M1»",
            modo="M1",
            consulta="¿Qué preferencia de reuniones tengo?",
            elegibles=[],
            prohibidos=["MEM-007"],
            esperado_rama="La candidata no aparece en M1.",
            estado_suficiencia="NINGUNO_EN_AMBITO",
            proposito="responder_al_usuario",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
        _rama(
            "R2",
            "Comprobar que la misma candidata SÍ es visible en gestión de memoria.",
            "B04 §17 CA-09 «visible en M4» + B04 §5 M4",
            modo="M4",
            consulta="[gestión de memoria] candidatas pendientes de preferencia de reuniones",
            elegibles=["MEM-007"],
            prohibidos=[],
            esperado_rama="M4 devuelve la candidata con su estado, sin activarla ni elevarla.",
            estado_suficiencia="SOLO_CANDIDATA",
            proposito="gestionar_memoria",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
    ],
    "B04-CA-10": [
        _rama(
            "R1",
            "Comprobar que la rechazada no se recupera como conocimiento.",
            "B04 §17 CA-10 «No recupera como conocimiento»",
            modo="M1",
            consulta="¿Qué horario de entrega tengo fijado?",
            elegibles=[],
            prohibidos=["MEM-008"],
            esperado_rama="La rechazada no se recupera como conocimiento.",
            estado_suficiencia="NINGUNO_EN_AMBITO",
            proposito="responder_al_usuario",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
        _rama(
            "R2",
            "Comprobar que M4 muestra su estado cuando se pide expresamente.",
            "B04 §17 CA-10 «M4 muestra estado si se pide» + B04 §5 M4",
            modo="M4",
            consulta="[gestión de memoria] estado de la candidata de horario de entrega",
            elegibles=["MEM-008"],
            prohibidos=[],
            esperado_rama="M4 muestra el estado RECHAZADA sin elevarlo ni reactivarlo.",
            estado_suficiencia="SOLO_CANDIDATA",
            proposito="gestionar_memoria",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
    ],
    "B04-CA-24": [
        _rama(
            "R1",
            "Comprobar que el resumen sin soporte sale de M1.",
            "B04 §17 CA-24 «Fuera de M1»",
            modo="M1",
            consulta="¿Cada cuánto revisamos el alcance?",
            elegibles=[],
            prohibidos=["MEM-017"],
            esperado_rama="El resumen sin soporte no entra en M1.",
            estado_suficiencia="NINGUNO_EN_AMBITO",
            proposito="responder_al_usuario",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
        _rama(
            "R2",
            "Comprobar que sigue siendo visible en la vista de gestión autorizada.",
            "B04 §17 CA-24 «visible en auditoría» + B04 §5 M4 «sin soporte»",
            modo="M4",
            consulta="[gestión de memoria] elementos sin soporte del expediente Alfa",
            elegibles=["MEM-017"],
            prohibidos=[],
            esperado_rama=(
                "M4 devuelve el elemento con validez SIN_SOPORTE, sin restituir autoridad."
            ),
            estado_suficiencia="PARCIAL",
            proposito="gestionar_memoria",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
    ],
    "B04-CA-49": [
        _rama(
            "R1",
            "Comprobar que E4 devuelve evidencia atribuida y enlaza la candidata.",
            "B04 §17.1 CA-49 «E4 devuelve evidencia no canónica y enlace a la candidata»",
            modo="M3",
            consulta="¿Hay algo sobre mi preferencia de reuniones?",
            elegibles=["MSG-020"],
            prohibidos=["MEM-007"],
            esperado_rama="Evidencia no canónica atribuida con enlace explícito a la candidata.",
            estado_suficiencia="PARCIAL",
            proposito="verificar_fuente",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
        _rama(
            "R2",
            "Comprobar que la candidata enlazada es visible en M4 y sigue pendiente.",
            "B04 §17.1 CA-49 «candidata pendiente visible en M4» + B04 §5 M4",
            modo="M4",
            consulta="[gestión de memoria] candidata originada por el fragmento MSG-020",
            elegibles=["MEM-007"],
            prohibidos=[],
            esperado_rama="M4 muestra la candidata pendiente y su origen, sin consolidarla.",
            estado_suficiencia="SOLO_CANDIDATA",
            proposito="gestionar_memoria",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
    ],
    # El canon nombra M3 en el resultado esperado de CA-35: la rama de
    # inspección autorizada es tan canónica como la exclusión en M1. La detectó
    # el propio validador al comparar contra el DOCX, no una lista escrita a mano.
    "B04-CA-35": [
        _rama(
            "R1",
            "Comprobar que el fallback de M1 excluye el fragmento marcado «no usar».",
            "B04 §17 CA-35 «M1 fallback lo excluye»",
            modo="M1",
            consulta="¿Qué nota interna hay sobre la prueba?",
            elegibles=[],
            prohibidos=["MEM-021", "MSG-012"],
            esperado_rama="Ni E4 ni ninguna etapa resucita el contenido marcado «no usar».",
            estado_suficiencia="NINGUNO_EN_AMBITO",
            proposito="responder_al_usuario",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
        _rama(
            "R2",
            "Comprobar que M3 puede inspeccionarlo cuando se pide expresamente.",
            "B04 §17 CA-35 «M3 puede inspeccionarlo si se pide»",
            modo="M3",
            consulta="[verificación de fuente] muéstrame la nota marcada «no usar como memoria»",
            elegibles=["MSG-012"],
            prohibidos=[],
            esperado_rama=(
                "M3 devuelve el fragmento como evidencia atribuida, sin convertirlo en memoria."
            ),
            estado_suficiencia="PARCIAL",
            proposito="verificar_fuente",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
    ],
    # -- M-02 · casos multirrama que el v0.1 aplanaba -----------------------
    "B04-CA-36": [
        _rama(
            "R1",
            "Variante cuyo único hallazgo es histórico.",
            "B04 §17 CA-36 «Dato está solo histórico»",
            modo="M1",
            consulta="¿Cuál es el presupuesto vigente del expediente Alfa según lo anterior?",
            elegibles=[],
            prohibidos=["DEC-002"],
            esperado_rama="Estado interno SOLO_HISTORICO, distinto de ausencia real.",
            estado_suficiencia="SOLO_HISTORICO",
            proposito="responder_al_usuario",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
        _rama(
            "R2",
            "Variante cuyo único hallazgo es una candidata.",
            "B04 §17 CA-36 «candidata»",
            modo="M1",
            consulta="¿Qué preferencia de reuniones tengo registrada?",
            elegibles=[],
            prohibidos=["MEM-007"],
            esperado_rama="Estado interno SOLO_CANDIDATA, distinto de ausencia real.",
            estado_suficiencia="SOLO_CANDIDATA",
            proposito="responder_al_usuario",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
        _rama(
            "R3",
            "Variante cuyo único hallazgo está fuera del ámbito solicitado.",
            "B04 §17 CA-36 «fuera de ámbito»",
            modo="M1",
            consulta="¿Cuál es el nombre en clave del entregable?",
            elegibles=[],
            prohibidos=["MEM-018"],
            esperado_rama="Estado interno FUERA_DE_AMBITO, distinto de ausencia real.",
            estado_suficiencia="FUERA_DE_AMBITO",
            proposito="responder_al_usuario",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
    ],
    "B04-CA-47": [
        _rama(
            "R1",
            "Consulta por occurred_at: qué ocurrió en enero.",
            "B04 §17.1 CA-47 «Consultas por occurred_at … devuelven resultados distintos»",
            modo="M2",
            consulta="¿Qué decisiones ocurrieron en enero?",
            elegibles=["DEC-011", "DEC-015"],
            prohibidos=["DEC-014"],
            esperado_rama="Solo las decisiones cuyo occurred_at cae en enero.",
            estado_suficiencia="COMPLETO",
            proposito="revisar_historial",
            permiso="AUTORIZADO",
            ambito="PRJ-BETA",
            tiempo_objetivo=_AHORA,
        ),
        _rama(
            "R2",
            "Consulta por tiempo válido: qué era aplicable el 20 de enero.",
            "B04 §17.1 CA-47 «… valid_time …»",
            modo="M2",
            consulta="¿Qué decisiones eran válidas el 20 de enero?",
            elegibles=["DEC-014"],
            prohibidos=["DEC-011", "DEC-015"],
            esperado_rama="Solo la decisión aplicable a esa fecha por tiempo válido.",
            estado_suficiencia="COMPLETO",
            proposito="revisar_historial",
            permiso="AUTORIZADO",
            ambito="PRJ-BETA",
            tiempo_objetivo="2026-01-20T00:00:00Z",
        ),
        _rama(
            "R3",
            "Consulta por corte de registro: qué sabía Sirius el 15 de febrero.",
            "B04 §17.1 CA-47 «… y recorded_at devuelven resultados distintos y correctos»",
            modo="M2",
            consulta="¿Qué decisiones había registrado Sirius el 15 de febrero?",
            elegibles=["DEC-014", "DEC-015"],
            prohibidos=["DEC-011"],
            esperado_rama="Solo lo registrado hasta el corte, aunque hoy exista más.",
            estado_suficiencia="COMPLETO",
            proposito="revisar_historial",
            permiso="AUTORIZADO",
            ambito="PRJ-BETA",
            tiempo_objetivo=_AHORA,
            corte_registro="2026-02-15T00:00:00Z",
        ),
    ],
    "B04-CA-48": [
        _rama(
            "R1",
            "Rama autorizada: demuestra que el contenido restringido existe.",
            "B04 §17.1 CA-48 «Misma consulta con dos propósitos»",
            modo="M1",
            consulta="¿Hay algo sobre el tema sensible del titular?",
            elegibles=["MEM-010"],
            prohibidos=[],
            esperado_rama="Con propósito autorizado el contenido restringido es recuperable.",
            estado_suficiencia="COMPLETO",
            clase="CONTROL_DIFERENCIAL",
            proposito="revisar_dato_sensible_autorizado",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
        ),
        _rama(
            "R2",
            "Rama no autorizada sobre contenido restringido que sí existe.",
            "B04 §17.1 CA-48 «uno no autoriza contenido restringido»",
            modo="M1",
            consulta="¿Hay algo sobre el tema sensible del titular?",
            elegibles=[],
            prohibidos=["MEM-010"],
            esperado_rama="SIN_RESULTADO_UTILIZABLE, sin revelar existencia, conteo ni categoría.",
            estado_suficiencia="NO_REPORTABLE",
            proposito="responder_al_usuario",
            permiso="NO_AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
            tolerancia_pendiente=TOLERANCIA_PENDIENTE_RAMA,
        ),
        _rama(
            "R3",
            "Rama de ausencia real, indistinguible de la anterior.",
            "B04 §17.1 CA-48 «una ausencia real comparten estado, conteo, redacción y latencia»",
            modo="M1",
            consulta="¿Hay algo sobre el tema clínico del proveedor?",
            elegibles=[],
            prohibidos=[],
            esperado_rama=(
                "SIN_RESULTADO_UTILIZABLE idéntico al de la rama R2 dentro de tolerancia."
            ),
            estado_suficiencia="NINGUNO_EN_AMBITO",
            clase="CONTROL_DIFERENCIAL",
            proposito="responder_al_usuario",
            permiso="AUTORIZADO",
            ambito="PRJ-ALFA",
            tiempo_objetivo=_AHORA,
            tolerancia_pendiente=TOLERANCIA_PENDIENTE_RAMA,
        ),
    ],
}

# Ramas M4 exigidas nominalmente por el paquete 03B §4.3.
CA_CON_RAMA_M4_OBLIGATORIA: tuple[str, ...] = (
    "B04-CA-09",
    "B04-CA-10",
    "B04-CA-24",
    "B04-CA-49",
)
# Casos multirrama exigidos nominalmente por el paquete 03B §4.4.
CA_MULTIRRAMA_OBLIGATORIA: tuple[str, ...] = ("B04-CA-36", "B04-CA-47", "B04-CA-48")

# ---------------------------------------------------------------------------
# 3. M-07 · cardinalidad y parada de CA-39
# ---------------------------------------------------------------------------
# CA-39 es un arnés de equivalencia entre dos realizaciones, no una consulta de
# recuperación. El canon no le asigna cardinalidad ni parada, y el paquete 03B
# §4.8 prohíbe atribuírselas.
CA_SIN_VOCABULARIO_DE_PARADA: tuple[str, ...] = ("B04-CA-39",)

# ---------------------------------------------------------------------------
# 4. Objetivo y unidad de trabajo por caso (ficha PDP §7)
# ---------------------------------------------------------------------------

TOLERANCIA_EXACTA = (
    "Conjunto elegible, estados, criticidad y suficiencia exactamente equivalentes; "
    "orden total cuando la instanciación lo declara."
)
TOLERANCIA_PENDIENTE_ORDEN = (
    "Clase de equivalencia de orden entre implementaciones: NO CONGELADA. "
    "Depende de RED-033 y de ADR002-TOL-209."
)
TOLERANCIA_PENDIENTE_DIFERENCIAL = (
    "Banda de texto, estado, conteo y tiempo entre ausencia real y no reportable: "
    "NO CONGELADA. Depende de RED-032, B04-RF-26 y ADR002-TOL-209."
)

CA_TOLERANCIA_PENDIENTE: dict[str, str] = {
    "B04-CA-37": TOLERANCIA_PENDIENTE_DIFERENCIAL,
    "B04-CA-48": TOLERANCIA_PENDIENTE_DIFERENCIAL,
    "B04-CA-39": TOLERANCIA_PENDIENTE_ORDEN,
}

# ---------------------------------------------------------------------------
# 5. M-04 · PDP-CA aplicables a ADR-002
# ---------------------------------------------------------------------------
# Criterio 2: disciplina de congelación que los propios artefactos aprobados de
# ADR-002 importan. Cada entrada cita la regla que la importa.
PDP_CA_DISCIPLINA: dict[str, str] = {
    "PDP-CA-02": "Registro de Tolerancias v0.4 §9 regla 1 y Especificación §3 principio 2",
    "PDP-CA-03": "Protocolo de medición v0.1 §6.5, §6.6 y prohibición 8",
    "PDP-CA-06": "ADR002-TOL-210 · punto de congelación antes de la primera ejecución",
    "PDP-CA-16": "Protocolo de medición v0.1 §7 · registro obligatorio de cada medición",
    "PDP-CA-17": "Registro de Tolerancias v0.4 §9 reglas 1 y 10",
    "PDP-CA-18": "ADR002-TOL-107 · salida NO EVALUABLE permanece en el denominador",
}
CRITERIO_ANEXO_B = "ANEXO_B_RED_CON_CASO_O_METRICA_DE_B04"
CRITERIO_DISCIPLINA = "DISCIPLINA_DE_CONGELACION_IMPORTADA_POR_ADR002"


def pdp_ca_aplicables(canon: CS.Canon) -> dict[str, dict[str, Any]]:
    """Determina qué `PDP-CA` son aplicables a ADR-002 y por qué."""
    aplicables: dict[str, dict[str, Any]] = {}
    for red, fila in sorted(canon.anexo.items()):
        if not (fila.casos_b04() or fila.metricas_b04()):
            continue
        for pdp in fila.casos_pdp():
            entrada = aplicables.setdefault(
                pdp, {"criterios": [], "red": [], "metricas": [], "familias": [], "casos_b04": []}
            )
            if CRITERIO_ANEXO_B not in entrada["criterios"]:
                entrada["criterios"].append(CRITERIO_ANEXO_B)
            entrada["red"].append(red)
            entrada["metricas"].extend(fila.metricas_b04())
            entrada["familias"].extend(fila.familias)
            entrada["casos_b04"].extend(fila.casos_b04())
    for pdp, regla in PDP_CA_DISCIPLINA.items():
        entrada = aplicables.setdefault(
            pdp, {"criterios": [], "red": [], "metricas": [], "familias": [], "casos_b04": []}
        )
        if CRITERIO_DISCIPLINA not in entrada["criterios"]:
            entrada["criterios"].append(CRITERIO_DISCIPLINA)
        entrada["regla_que_lo_importa"] = regla
    return {
        pdp: {
            **{
                k: (sorted(set(v)) if isinstance(v, list) else v)
                for k, v in datos.items()
                if k != "criterios"
            },
            "criterios": sorted(datos["criterios"]),
        }
        for pdp, datos in sorted(aplicables.items())
    }


def pdp_ca_excluidos(canon: CS.Canon, aplicables: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Matriz de exclusión: cada `PDP-CA` no aplicable con su responsable."""
    salida: dict[str, dict[str, Any]] = {}
    for pdp, caso in sorted(canon.casos_pdp.items()):
        if pdp in aplicables:
            continue
        filas = [f for f in canon.anexo.values() if pdp in f.casos_pdp()]
        familias = sorted({fam for f in filas for fam in f.familias})
        destinos: list[str] = []
        for familia in familias:
            info = canon.destinos.get(familia)
            if info:
                destinos.extend(CS.expandir_destinos(info["destino"]))
        if not destinos:
            destinos = ["PDP · Plan de Pruebas completo"]
        salida[pdp] = {
            "entrada_adversarial": caso.entrada_adversarial,
            "resultado_esperado": caso.resultado_esperado,
            "red_que_lo_asigna": sorted(f.red for f in filas),
            "familias": familias,
            "responsable": sorted(set(destinos)),
            "motivo": (
                "Ninguna fila del Anexo B que lo asigna cita un caso B04-CA ni una métrica "
                "B04-M, y ADR-002 no importa su regla. No se afirma cobertura."
            ),
        }
    return salida


# ---------------------------------------------------------------------------
# 6. B-03 · previsión frente a T0, sin veredicto
# ---------------------------------------------------------------------------


def prevision_t0(identificador: str, requisitos: list[str]) -> dict[str, Any]:
    """Criterio único de expresabilidad. Devuelve previsión, nunca veredicto."""
    estados = {rf: S2.ESTADO_RF_EN_T0.get(rf, "DESCONOCIDO") for rf in requisitos}
    inseguros = sorted(rf for rf, e in estados.items() if e == "INSEGURO")
    if identificador in S2.CA_REQUIEREN_DOS_IMPLEMENTACIONES:
        prevision = "NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION"
        fundamento = (
            "El enunciado canónico exige «dos implementaciones distintas sobre el mismo "
            "corpus». T0 es una sola realización: la comparación no existe."
        )
    elif "AUSENTE" in estados.values():
        ausentes = sorted(rf for rf, e in estados.items() if e == "AUSENTE")
        prevision = "NO_EXPRESABLE_PREVISTO"
        fundamento = (
            f"Alguna dimensión requerida no existe en la línea base: {', '.join(ausentes)} "
            f"con estado AUSENTE según {S2.FUENTE_INVENTARIO}. Un resultado coincidente "
            "no demostraría conformidad."
        )
    elif "PARCIAL" in estados.values():
        parciales = sorted(rf for rf, e in estados.items() if e == "PARCIAL")
        prevision = "PARCIALMENTE_EXPRESABLE_PREVISTO"
        fundamento = (
            f"Dimensiones presentes de forma incompleta: {', '.join(parciales)} con estado "
            f"PARCIAL según {S2.FUENTE_INVENTARIO}."
        )
    else:
        prevision = "EXPRESABLE_PREVISTO"
        fundamento = (
            "Todas las dimensiones requeridas existen en la línea base según "
            f"{S2.FUENTE_INVENTARIO}."
        )
    return {
        "estado_t0": S2.ESTADO_T0,
        "expresabilidad_prevista": prevision,
        "fundamento_de_prevision": fundamento,
        "estado_por_requisito": dict(sorted(estados.items())),
        "ejes_inseguros_medidos": inseguros,
        "no_es_veredicto": True,
        "nota": (
            "La clasificación real solo se crea tras ejecutar T0 sobre el corpus congelado "
            "(ADR002-TOL-208). T0 no se ha ejecutado."
        ),
    }


# ---------------------------------------------------------------------------
# 7. Construcción de los casos de nivel 1
# ---------------------------------------------------------------------------

_RX_MODO = re.compile(r"\bM[1-5]\b")
_RX_ETAPA = re.compile(r"\bE[0-5]\b")
_RX_PARADA = re.compile(r"\bS[1-7]\b")


def _texto_canonico(caso: CS.CasoCanonico) -> str:
    return " ".join([caso.entrada, caso.resultado_esperado, caso.fallo_observable])


def _campo(valor: Any, fuente: str, estado: str) -> dict[str, Any]:
    return {"valor": valor, "fuente": fuente, "estado": estado}


def _campo_derivado(valor: Any, motivo: str) -> dict[str, Any]:
    return _campo(valor, f"{S2.FUENTE_INSTANCIACION} · {motivo}", "DERIVADO_PROPUESTO")


def _campo_vocabulario(
    valor: Any, caso: CS.CasoCanonico, patron: re.Pattern[str], fuente_canonica: str, motivo: str
) -> dict[str, Any]:
    """`CANONICO` solo si el texto canónico del propio caso nombra el valor."""
    if valor is None:
        return _campo(None, f"{S2.FUENTE_INSTANCIACION} · {motivo}", "DERIVADO_PROPUESTO")
    nombrados = set(patron.findall(_texto_canonico(caso)))
    if valor in nombrados:
        return _campo(valor, f"{caso.seccion} · literal en el propio caso", "CANONICO")
    return _campo(valor, f"{fuente_canonica} · {motivo}", "DERIVADO_PROPUESTO")


def _campo_cardinalidad(valor: Any, caso: CS.CasoCanonico) -> dict[str, Any]:
    if valor is None:
        return _campo(
            None,
            f"{S2.FUENTE_INSTANCIACION} · el caso no es una consulta de recuperación",
            "DERIVADO_PROPUESTO",
        )
    texto = _texto_canonico(caso)
    if valor in texto:
        return _campo(valor, f"{caso.seccion} · literal en el propio caso", "CANONICO")
    return _campo(
        valor,
        (
            f"{S2.FUENTE_INSTANCIACION} · elección de instanciación. "
            f"El canon no fija cardinalidad para este caso; la regla canónica aplicable es "
            f"{S2.FUENTE_CARDINALIDAD_B04}: si la instanciación es EXHAUSTIVA, S1 está prohibida"
        ),
        "DERIVADO_PROPUESTO",
    )


def _tipo_orden(orden: list[str] | None) -> str:
    if orden is None:
        return "CONJUNTO"
    return "VACIO" if not orden else "ORDEN_TOTAL"


def _ficha_pdp7(
    fila: dict[str, Any], caso: CS.CasoCanonico, canon: CS.Canon, ramas: list[dict[str, Any]]
) -> dict[str, Any]:
    """Los catorce campos del PDP §7, con fuente y estado por campo."""
    ident = caso.identificador
    familias = sorted(set(fila["fam"]) | set(canon_familias(canon, ident)))
    pendiente = CA_TOLERANCIA_PENDIENTE.get(ident)
    modos = sorted({fila["modo"]} | {r["modo"] for r in ramas})
    return {
        "id_y_familia": _campo(
            {"id": ident, "familias": familias}, S2.FUENTE_PDP7, "DERIVADO_PROPUESTO"
        ),
        "objetivo": _campo(
            f"Demostrar o romper: {caso.resultado_esperado}",
            f"{caso.seccion} · derivado del resultado esperado canónico",
            "DERIVADO_PROPUESTO",
        ),
        "entrada": _campo(caso.entrada, S2.FUENTE_CANONICA_CA, "CANONICO"),
        "unidad_de_trabajo": _campo(
            {
                "objetivo": f"Adjudicar {ident} sobre el corpus de conformidad congelable.",
                "inicio": "alta de la petición de recuperación instanciada",
                "cierre": "adjudicación registrada de todas las ramas del caso",
            },
            f"{S2.FUENTE_PDP7} · unidad declarada por el arnés, no por el producto",
            "DERIVADO_PROPUESTO",
        ),
        "operacion_y_modo": _campo(
            {"modos": modos, "operacion": "recuperacion_b04"},
            f"{caso.seccion} y B04 §5",
            "CANONICO" if _RX_MODO.findall(_texto_canonico(caso)) else "DERIVADO_PROPUESTO",
        ),
        "ambito": _campo_derivado(
            sorted({fila["ambito"]} | {r["ambito"] for r in ramas if r["ambito"]}),
            "ámbito sintético del corpus",
        ),
        "tiempo_y_corte": _campo_derivado(
            {
                "tiempo_objetivo": fila["t_obj"],
                "corte_registro": fila["corte"],
                "por_rama": [
                    {
                        "rama": r["sufijo"],
                        "tiempo_objetivo": r["tiempo_objetivo"],
                        "corte_registro": r["corte_registro"],
                    }
                    for r in ramas
                ],
            },
            "fechas sintéticas declaradas, nunca el reloj",
        ),
        "referencia": _campo(
            {
                "resultado_esperado_canonico": caso.resultado_esperado,
                "elegibles": fila["eleg"],
                "prohibidos": fila["prohib"],
                "orden": fila["orden"],
                "tipo_orden": _tipo_orden(fila["orden"]),
            },
            f"{S2.FUENTE_CANONICA_CA} para el esperado; {S2.FUENTE_INSTANCIACION} para los ids",
            "DERIVADO_PROPUESTO",
        ),
        "criticidad": _campo_derivado(
            fila["crit"], "adjudicación de prueba del corpus, B04 §6 cuarto origen"
        ),
        "tolerancias": _campo(
            pendiente or TOLERANCIA_EXACTA,
            "RED-032/RED-033 y ADR002-TOL-209" if pendiente else "ADR002-TOL-201 condición (1)",
            "PENDIENTE_TOL209" if pendiente else "DERIVADO_PROPUESTO",
        ),
        "senales_observables": _campo_derivado(
            [
                "conjunto de ids elegibles devueltos",
                "ids prohibidos que aparecieron",
                "estado interno de suficiencia adjudicado",
                "estado externo emitido",
                "modo adjudicado y puertas aplicadas",
                "etapas recorridas y parada",
                "razón por resultado y razón de orden",
            ],
            "señales que el arnés puede observar sin revelar contenido protegido",
        ),
        "fallo": _campo(caso.fallo_observable, S2.FUENTE_CANONICA_CA, "CANONICO"),
        "evidencia": _campo_derivado(
            "Registro por rama: petición efectiva, plan, puertas, etapas, parada, suficiencia, "
            "resultado obtenido y esperado, veredicto y razón. No altera la referencia.",
            "PDP §7 exige evidencia posterior sin alterar referencia",
        ),
        "resultado": _campo(
            None,
            f"{S2.FUENTE_PDP7} · se rellena tras adjudicar; hoy no hay ejecución",
            "DERIVADO_PROPUESTO",
        ),
        S2.CAMPO_INSUFICIENCIA: _campo_derivado(
            _condicion_insuficiencia(fila["etapa"]),
            "Especificación de benchmark §5 campo 12: condición que autoriza cada transición",
        ),
    }


def _condicion_insuficiencia(etapa: str | None) -> list[dict[str, str]]:
    """Condición que autoriza pasar de cada etapa a la siguiente, hasta la esperada."""
    orden = ["E0", "E1", "E2", "E3", "E4", "E5"]
    if etapa is None or etapa not in orden:
        return []
    salida: list[dict[str, str]] = []
    for actual, siguiente in itertools.pairwise(orden):
        if orden.index(actual) >= orden.index(etapa):
            break
        salida.append(
            {
                "transicion": f"{actual}->{siguiente}",
                "condicion": (
                    "insuficiencia contrastada respecto de la cardinalidad declarada o "
                    "críticos elegibles pendientes, con el siguiente espacio autorizado"
                ),
            }
        )
    return salida


def canon_familias(canon: CS.Canon, identificador: str) -> list[str]:
    return CS.asignaciones_canonicas_por_ca().get(identificador, {}).get("familias", [])


def _trazabilidad(fila: dict[str, Any], identificador: str) -> dict[str, Any]:
    """B-01 · el Anexo B manda; lo añadido se marca como derivado."""
    asignaciones = CS.asignaciones_canonicas_por_ca().get(
        identificador, {"red": [], "metricas": [], "familias": []}
    )
    red_canonica = asignaciones["red"]
    m_canonicas = asignaciones["metricas"]
    f_canonicas = asignaciones["familias"]
    return {
        "requisito_verificado": fila["rf"],
        "traza_red_canonica_anexo_b": red_canonica,
        "traza_red_adicional_derivada": sorted(set(fila["red"]) - set(red_canonica)),
        "metrica_canonica_anexo_b": m_canonicas,
        "metrica_adicional_derivada": sorted(set(fila["m"]) - set(m_canonicas)),
        "familia_canonica_anexo_b": f_canonicas,
        "familia_adicional_derivada": sorted(set(fila["fam"]) - set(f_canonicas)),
        "fuente_canonica": S2.FUENTE_ANEXO_B,
        "fuente_adicional": S2.FUENTE_INSTANCIACION,
        "nota": (
            "Las asignaciones canónicas del Anexo B no se sustituyen. Lo adicional es "
            "cobertura extra del arnés y no cuenta como cumplimiento del Anexo B."
        ),
    }


def _caso_nivel1(fila: dict[str, Any], canon: CS.Canon) -> dict[str, Any]:
    ident = fila["ca"]
    caso = canon.casos[ident]
    numero = int(ident.rsplit("-", 1)[1])
    ramas = RAMAS.get(ident, [])
    sin_parada = ident in CA_SIN_VOCABULARIO_DE_PARADA
    cardinalidad = None if sin_parada else fila["card"]
    parada = None if sin_parada else fila["parada"]
    trazas = _trazabilidad(fila, ident)
    return {
        "id": f"N1-{numero:02d}",
        "nivel": 1,
        "identificador_canonico": ident,
        "canonico": {
            "fuente": S2.FUENTE_CANONICA_CA,
            "seccion_exacta": caso.seccion,
            "riesgo": caso.riesgo,
            "entrada": caso.entrada,
            "resultado_esperado": caso.resultado_esperado,
            "fallo_observable": caso.fallo_observable,
            "modificable": False,
        },
        "instanciacion": {
            "fuente": S2.FUENTE_INSTANCIACION,
            "estado": S2.ESTADO_NO_CONGELADO,
            "consulta": _campo_derivado(fila["consulta"], "consulta sintética instanciada"),
            "modo": _campo_vocabulario(
                fila["modo"], caso, _RX_MODO, "B04 §5", "modo elegido por la instanciación"
            ),
            "proposito": _campo_derivado(fila["proposito"], "propósito autorizado del arnés"),
            "permiso": _campo_derivado(fila["permiso"], "permiso declarado por el arnés"),
            "ambito": _campo_derivado(fila["ambito"], "ámbito sintético del corpus"),
            "tiempo_objetivo": _campo_derivado(fila["t_obj"], "fecha declarada, no el reloj"),
            "corte_registro": _campo_derivado(fila["corte"], "fecha declarada, no el reloj"),
            "cardinalidad": _campo_cardinalidad(cardinalidad, caso),
            "etapa": _campo_vocabulario(
                fila["etapa"], caso, _RX_ETAPA, "B04 §15.1", "etapa elegida por la instanciación"
            ),
            "parada": _campo_vocabulario(
                parada,
                caso,
                _RX_PARADA,
                S2.FUENTE_PARADAS_B04,
                "parada elegida por la instanciación",
            ),
            "orden": _campo_derivado(
                {"valor": fila["orden"], "tipo": _tipo_orden(fila["orden"])},
                "ids sintéticos; el canon no fija secuencia",
            ),
            "elegibles": _campo_derivado(fila["eleg"], "ids sintéticos del corpus"),
            "prohibidos": _campo_derivado(fila["prohib"], "ids sintéticos del corpus"),
            "explicacion_esperada": _campo_derivado(
                fila["expl"], "explicación mínima exigida por B04-RF-28"
            ),
            "ramas": ramas,
        },
        "trazabilidad": trazas,
        "ficha_pdp_7": _ficha_pdp7(fila, caso, canon, ramas),
        "t0": prevision_t0(ident, fila["rf"]),
        "datos_sinteticos": fila["datos"],
        "corpus": "conformidad",
    }


# ---------------------------------------------------------------------------
# 8. Casos PDP-CA aplicables (nivel 1)
# ---------------------------------------------------------------------------

INSTANCIACION_PDP: dict[str, dict[str, Any]] = {
    "PDP-CA-02": {
        "objetivo": "Que cambiar una referencia tras ver la salida invalide la ejecución.",
        "senal": "hash de la referencia antes y después de la ejecución",
        "aplica_a": "toda ejecución de ADR002-A/B/C/D y de T0",
    },
    "PDP-CA-03": {
        "objetivo": "Que una repetición sin cambio ni defecto documentado sea inválida.",
        "senal": "registro de repeticiones con su causa declarada",
        "aplica_a": "repetición única del protocolo §6.5",
    },
    "PDP-CA-06": {
        "objetivo": "Que cambiar el candidato durante la ejecución invalide la ejecución.",
        "senal": "huella de ficha de candidato referenciada por cada medición",
        "aplica_a": "ficha de candidato de ADR002-TOL-210",
    },
    "PDP-CA-09": {
        "objetivo": (
            "Que dos consumidores con librería específica compartida no cuenten como "
            "independientes."
        ),
        "senal": "inventario de dependencias de cada implementación del puerto",
        "aplica_a": "B04-CA-39 y B04-M16, neutralidad del contrato",
    },
    "PDP-CA-16": {
        "objetivo": "Que una evidencia que no reproduce versión y configuración no cuente.",
        "senal": "versión de corpus, commit, head de esquema y protocolo en cada registro",
        "aplica_a": "registro obligatorio de cada medición",
    },
    "PDP-CA-17": {
        "objetivo": "Que cambiar una tolerancia después de la salida invalide la ejecución.",
        "senal": "versión del Registro de Tolerancias y de la ficha en cada medición",
        "aplica_a": "todas las cifras del benchmark",
    },
    "PDP-CA-18": {
        "objetivo": "Que un caso marcado no evaluable siga en el denominador.",
        "senal": "denominador declarado frente a casos adjudicados",
        "aplica_a": "salida NO EVALUABLE de ADR002-TOL-107",
    },
    "PDP-CA-22": {
        "objetivo": (
            "Que dos consumidores con el mismo intérprete y distinta configuración cuenten "
            "como uno."
        ),
        "senal": "intérprete, versión y configuración de cada consumidor",
        "aplica_a": "B04-CA-39 y B04-M16, portabilidad observable",
    },
}


def _casos_pdp(canon: CS.Canon, aplicables: dict[str, Any]) -> list[dict[str, Any]]:
    salida: list[dict[str, Any]] = []
    for orden, (pdp, motivo) in enumerate(sorted(aplicables.items()), start=1):
        caso = canon.casos_pdp[pdp]
        extra = INSTANCIACION_PDP.get(pdp, {})
        salida.append(
            {
                "id": f"N1-PDP-{orden:02d}",
                "nivel": 1,
                "identificador_canonico": pdp,
                "canonico": {
                    "fuente": "Plan de Pruebas + RED/PDP v1.0 APROBADO §9 · casos transversales",
                    "entrada_adversarial": caso.entrada_adversarial,
                    "resultado_esperado": caso.resultado_esperado,
                    "modificable": False,
                },
                "aplicabilidad_adr002": {
                    "criterios": motivo["criterios"],
                    "red_que_lo_asigna": motivo.get("red", []),
                    "metricas_b04": motivo.get("metricas", []),
                    "casos_b04": motivo.get("casos_b04", []),
                    "familias": motivo.get("familias", []),
                    "regla_que_lo_importa": motivo.get("regla_que_lo_importa"),
                },
                "instanciacion": {
                    "fuente": S2.FUENTE_INSTANCIACION,
                    "estado": S2.ESTADO_NO_CONGELADO,
                    "objetivo": extra.get("objetivo"),
                    "senal_observable": extra.get("senal"),
                    "aplica_a": extra.get("aplica_a"),
                    "nota": (
                        "Caso de disciplina del arnés: se adjudica sobre el registro de ejecución, "
                        "no sobre el contenido recuperado."
                    ),
                },
                "t0": {
                    "estado_t0": S2.ESTADO_T0,
                    "expresabilidad_prevista": "NO_EXPRESABLE_PREVISTO",
                    "fundamento_de_prevision": (
                        "Adjudica disciplina de ejecución del benchmark, que T0 no tiene."
                    ),
                    "no_es_veredicto": True,
                },
                "corpus": "conformidad",
            }
        )
    return salida


# ---------------------------------------------------------------------------
# 9. Corpus de conformidad
# ---------------------------------------------------------------------------


def construir_corpus_conformidad(canon: CS.Canon) -> dict[str, Any]:
    base = V1.construir_corpus()
    items = list(base["items"]) + ITEMS_ANADIDOS
    memorias = [i for i in items if i["kind"] == "MEMORIA"]
    decisiones = [i for i in items if i["kind"] == "DECISION"]
    return {
        "documento": "Corpus de CONFORMIDAD del benchmark de ADR-002",
        "proposito": (
            "Adjudicar puertas, exactitud, contaminación, negación, ámbito, tiempo, conflicto, "
            "ausencia y explicación. NO se usa para fijar cifras de rendimiento absoluto."
        ),
        "version": S2.VERSION_CORPUS_CONFORMIDAD,
        "version_contrato": S2.VERSION_CONTRATO,
        "estado": S2.ESTADO_NO_CONGELADO,
        "semilla": S2.SEMILLA,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_2.py",
        "hereda_de": "corpus_v0_1.json",
        "fuente_canonica": {n: h["sha256_real"] for n, h in sorted(canon.huellas.items())},
        "datos_reales": "ninguno; corpus sintético determinista",
        "red": "no utilizada",
        "ahora_declarado": S2.AHORA_DECLARADO,
        "anclajes_anadidos": {
            "items": [i["id"] for i in ITEMS_ANADIDOS],
            "motivo": (
                "Paquete 03B §3.1: hacer falsable la rama triple de B04-CA-47. Con un solo "
                "elemento el fallo observable «colapsa las tres fechas» es indetectable."
            ),
        },
        "conteos": {
            "proyectos": len(base["proyectos"]),
            "entidades": len(base["entidades"]),
            "items": len(items),
            "recuerdos": len(memorias),
            "decisiones": len(decisiones),
            "items_heredados_v0_1": len(base["items"]),
            "items_anadidos_v0_2": len(ITEMS_ANADIDOS),
            "mensajes": len(base["mensajes"]),
            "documentos": len(base["documentos"]),
            "relaciones": len(base["relaciones"]),
        },
        "proyectos": base["proyectos"],
        "entidades": base["entidades"],
        "items": items,
        "mensajes": base["mensajes"],
        "documentos": base["documentos"],
        "relaciones": base["relaciones"],
    }


# ---------------------------------------------------------------------------
# 10. Corpus de rendimiento
# ---------------------------------------------------------------------------

# Vocabulario disjunto de todo anclaje canónico: el validador comprueba que
# ningún término de `S2.TERMINOS_ANCLA` aparece en el relleno de volumen.
_TEMAS_VOLUMEN = (
    "registro de turnos",
    "control de inventario menor",
    "seguimiento de incidencias leves",
    "plantillas de acta",
    "catálogo de consumibles",
    "programación de tareas rutinarias",
    "lista de apertura diaria",
    "registro de visitas",
)


def _texto_volumen(prefijo: str, idx: int, tema: str) -> str:
    return f"{prefijo} {idx:05d} de la serie de volumen sobre {tema}, sin valor canónico."


def construir_corpus_rendimiento(canon: CS.Canon, escala: int = 500) -> dict[str, Any]:
    """Corpus de volumen a la escala de `ADR002-TOL-208`.

    Regla de proyección declarada, determinista y reproducible:

        recuerdos(N)  = N
        decisiones(N) = N // 10
        mensajes(N)   = N * 10

    Para `N = 500` produce exactamente **500 recuerdos, 50 decisiones y 5.000
    mensajes**, la escala del corpus que produjo las cifras `LAB-LINUX` del
    Registro de Tolerancias v0.4.

    Los anclajes del corpus de conformidad se incluyen **sin alterar**, y el
    relleno vive en un proyecto reservado con vocabulario disjunto: ninguna
    respuesta canónica cambia.
    """
    conformidad = construir_corpus_conformidad(canon)
    anclajes = conformidad["items"]
    memorias_ancla = [i for i in anclajes if i["kind"] == "MEMORIA"]
    decisiones_ancla = [i for i in anclajes if i["kind"] == "DECISION"]

    objetivo_recuerdos = escala
    objetivo_decisiones = escala // 10
    objetivo_mensajes = escala * 10

    rng = random.Random(S2.SEMILLA)
    relleno: list[dict[str, Any]] = []
    for idx in range(1, max(0, objetivo_recuerdos - len(memorias_ancla)) + 1):
        tema = _TEMAS_VOLUMEN[rng.randrange(len(_TEMAS_VOLUMEN))]
        relleno.append(
            V1._item(
                f"VOL-MEM-{idx:05d}",
                "MEMORIA",
                S2.PROYECTO_VOLUMEN,
                _texto_volumen("Anotación", idx, tema),
                traza=["VOLUMEN"],
            )
        )
    for idx in range(1, max(0, objetivo_decisiones - len(decisiones_ancla)) + 1):
        tema = _TEMAS_VOLUMEN[rng.randrange(len(_TEMAS_VOLUMEN))]
        relleno.append(
            V1._item(
                f"VOL-DEC-{idx:05d}",
                "DECISION",
                S2.PROYECTO_VOLUMEN,
                _texto_volumen("Acuerdo menor", idx, tema),
                autoridad="DOCUMENTO_CANONICO",
                traza=["VOLUMEN"],
            )
        )

    mensajes = list(conformidad["mensajes"])
    for idx in range(1, max(0, objetivo_mensajes - len(mensajes)) + 1):
        tema = _TEMAS_VOLUMEN[rng.randrange(len(_TEMAS_VOLUMEN))]
        mensajes.append(
            {
                "id": f"VOL-MSG-{idx:05d}",
                "project_id": S2.PROYECTO_VOLUMEN,
                "texto": _texto_volumen("Mensaje", idx, tema),
                "recorded_at": "2026-01-01T00:00:00Z",
                "no_guardar": False,
                "redactado": False,
                "traza": ["VOLUMEN"],
            }
        )

    items = anclajes + relleno
    proyectos = [
        *conformidad["proyectos"],
        {
            "id": S2.PROYECTO_VOLUMEN,
            "nombre": "Serie de volumen del corpus de rendimiento",
            "alias": [],
            "tipo": "PROYECTO",
            "miembros_lista_cerrada": [],
        },
    ]
    longitudes = [len(i["text"]) for i in items if i["text"]]
    return {
        "documento": "Corpus de RENDIMIENTO del benchmark de ADR-002",
        "proposito": (
            "Latencia, tamaño, construcción, reconstrucción y estabilidad a la escala del "
            "corpus que produjo las cifras LAB-LINUX. NO crea referencias funcionales y NO "
            "sustituye al corpus de conformidad."
        ),
        "version": S2.VERSION_CORPUS_RENDIMIENTO,
        "version_contrato": S2.VERSION_CONTRATO,
        "estado": S2.ESTADO_NO_CONGELADO,
        "semilla": S2.SEMILLA,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_2.py",
        "escala_declarada": {
            "n": escala,
            "regla": "recuerdos(N)=N · decisiones(N)=N//10 · mensajes(N)=N*10",
            "objetivo": {
                "recuerdos": objetivo_recuerdos,
                "decisiones": objetivo_decisiones,
                "mensajes": objetivo_mensajes,
            },
            "escala_de_referencia": S2.ESCALA_RENDIMIENTO,
            "fuente_de_la_escala": S2.FUENTE_ESCALA,
            "escalas_proyectables": list(S2.ESCALAS_PROYECCION),
        },
        "relacion_con_conformidad": {
            "corpus_de_conformidad": "conformance_corpus_v0_2.json",
            "anclajes_incluidos_sin_alterar": len(anclajes),
            "proyecto_reservado_al_relleno": S2.PROYECTO_VOLUMEN,
            "regla": (
                "El relleno no comparte vocabulario con ningún anclaje canónico y vive en un "
                "proyecto propio: ninguna respuesta canónica cambia por añadir volumen."
            ),
        },
        "datos_reales": "ninguno; corpus sintético determinista",
        "red": "no utilizada",
        "ahora_declarado": S2.AHORA_DECLARADO,
        "conteos": {
            "proyectos": len(proyectos),
            "items": len(items),
            "recuerdos": sum(1 for i in items if i["kind"] == "MEMORIA"),
            "decisiones": sum(1 for i in items if i["kind"] == "DECISION"),
            "mensajes": len(mensajes),
            "documentos": len(conformidad["documentos"]),
            "relaciones": len(conformidad["relaciones"]),
            "longitud_media_texto": round(sum(longitudes) / len(longitudes), 2),
            "longitud_minima_texto": min(longitudes),
            "longitud_maxima_texto": max(longitudes),
        },
        "proyectos": proyectos,
        "entidades": conformidad["entidades"],
        "items": items,
        "mensajes": mensajes,
        "documentos": conformidad["documentos"],
        "relaciones": conformidad["relaciones"],
    }


# ---------------------------------------------------------------------------
# 11. Casos, referencias y manifiesto
# ---------------------------------------------------------------------------

EVIDENCIA_MINIMA = [
    "petición efectiva y operation_id",
    "modo adjudicado y puertas aplicadas",
    "etapas recorridas y condición de insuficiencia de cada transición",
    "resultado obtenido, esperado, veredicto y razón, por rama",
    "por resultado: por qué entró y por qué ocupa esa posición",
    "prohibidos que aparecieron y por qué no fueron excluidos",
    "suficiencia adjudicada y razón de la parada",
    "tolerancia aplicada y su versión, o la dependencia pendiente que la bloquea",
]


def construir_casos(canon: CS.Canon) -> dict[str, Any]:
    nivel1 = [_caso_nivel1(fila, canon) for fila in V1.CA]
    for caso in nivel1:
        caso["evidencia_minima"] = EVIDENCIA_MINIMA
    aplicables = pdp_ca_aplicables(canon)
    nivel1_pdp = _casos_pdp(canon, aplicables)
    return {
        "documento": "Casos del benchmark de ADR-002",
        "version": S2.VERSION_CONTRATO,
        "estado": S2.ESTADO_NO_CONGELADO,
        "hereda_de": "cases_v0_1.json",
        "regla_de_separacion": (
            "El bloque `canonico` de cada caso procede literalmente de las fuentes DOCX y no se "
            "reescribe. El bloque `instanciacion` es arquitectónico y registra la fuente de cada "
            "campo. Solo los campos del bloque canónico pueden declararse congelados por "
            "B04 §17/§17.1."
        ),
        "niveles": {
            "1": (
                "Casos canónicos reutilizados: B04-CA-01-50 y los PDP-CA aplicables a ADR-002. "
                "El benchmark los ejecuta, no los reescribe."
            ),
            "2": "Casos arquitectónicos nuevos. Solo cuando ningún caso canónico los cubre.",
            "3": (
                "Ablaciones técnicas. Instrumentos de medida; nunca producen veredicto de "
                "conformidad, y por eso no llevan ficha de caso del PDP §7."
            ),
        },
        "conteos": {
            "nivel_1_b04": len(nivel1),
            "nivel_1_pdp": len(nivel1_pdp),
            "nivel_2": len(V1.NIVEL2),
            "nivel_3": len(V1.NIVEL3),
            "ramas_canonicas": sum(len(c["instanciacion"]["ramas"]) for c in nivel1),
        },
        "nivel_1": nivel1,
        "nivel_1_pdp": nivel1_pdp,
        "nivel_2": V1.NIVEL2,
        "nivel_3": V1.NIVEL3,
    }


def construir_referencias(casos: dict[str, Any]) -> dict[str, Any]:
    refs: list[dict[str, Any]] = []
    for caso in casos["nivel_1"]:
        inst = caso["instanciacion"]
        refs.append(
            {
                "caso": caso["id"],
                "identificador_canonico": caso["identificador_canonico"],
                "canonico": {
                    "fuente": S2.FUENTE_CANONICA_CA,
                    "seccion_exacta": caso["canonico"]["seccion_exacta"],
                    "riesgo": caso["canonico"]["riesgo"],
                    "entrada": caso["canonico"]["entrada"],
                    "resultado_esperado": caso["canonico"]["resultado_esperado"],
                    "fallo_observable": caso["canonico"]["fallo_observable"],
                    "modificable": False,
                },
                "instanciacion": {
                    "fuente": S2.FUENTE_INSTANCIACION,
                    "estado": S2.ESTADO_NO_CONGELADO,
                    "modificable": True,
                    "ramas": [
                        {
                            "sufijo": r["sufijo"],
                            "clase": r["clase"],
                            "modo": r["modo"],
                            "elegibles": r["candidatos_elegibles"],
                            "prohibidos": r["candidatos_prohibidos"],
                            "estado_suficiencia_esperado": r["estado_suficiencia_esperado"],
                            "tolerancia_pendiente": r["tolerancia_pendiente"],
                        }
                        for r in inst["ramas"]
                    ],
                    "cardinalidad": inst["cardinalidad"]["valor"],
                    "etapa": inst["etapa"]["valor"],
                    "parada": inst["parada"]["valor"],
                    "orden": inst["orden"]["valor"]["valor"],
                    "tipo_orden": inst["orden"]["valor"]["tipo"],
                    "elegibles": inst["elegibles"]["valor"],
                    "prohibidos": inst["prohibidos"]["valor"],
                    "fuente_por_campo": {
                        campo: {
                            "fuente": inst[campo]["fuente"],
                            "estado": inst[campo]["estado"],
                        }
                        for campo in S2.CAMPOS_INSTANCIACION
                    },
                },
            }
        )
    return {
        "documento": "Referencias del benchmark de ADR-002",
        "version": S2.VERSION_CONTRATO,
        "estado": S2.ESTADO_NO_CONGELADO,
        "hereda_de": "references_v0_1.json",
        "regla": (
            "El bloque `canonico` no cambia nunca: procede literalmente de B04 §17/§17.1. El "
            "bloque `instanciacion` está PROPUESTO y NO CONGELADO: puede corregirse mientras no "
            "se haya observado ninguna salida. Cambiar cualquiera de los dos después de observar "
            "la salida está prohibido (RED-004, PDP-CA-02, Registro v0.4 §9 regla 1)."
        ),
        "conteos": {
            "referencias_nivel_1": len(refs),
            "referencias_con_ramas": sum(1 for r in refs if r["instanciacion"]["ramas"]),
        },
        "referencias_nivel_1": refs,
    }


def construir_casos_pdp(canon: CS.Canon) -> dict[str, Any]:
    aplicables = pdp_ca_aplicables(canon)
    excluidos = pdp_ca_excluidos(canon, aplicables)
    familias_destino = CS.familias_destino_adr002()
    tocadas: set[str] = set()
    for fila in V1.CA:
        tocadas.update(fila["fam"])
    for caso in V1.NIVEL2 + V1.NIVEL3:
        tocadas.update(caso.get("fam", []))
    for asignacion in CS.asignaciones_canonicas_por_ca().values():
        tocadas.update(asignacion["familias"])
    todas = set(canon.familias)
    return {
        "documento": "Casos transversales del Plan de Pruebas y su aplicabilidad a ADR-002",
        "version": S2.VERSION_CORPUS_RENDIMIENTO,
        "estado": S2.ESTADO_NO_CONGELADO,
        "fuente": "Plan de Pruebas + RED/PDP v1.0 APROBADO · §9 y Anexo B",
        "advertencia": (
            "ADR-002 NO cubre los 304 casos del Plan completo (276 heredados + 28 "
            "transversales). Aquí solo se declaran los PDP-CA aplicables a ADR-002 y la "
            "exclusión justificada del resto."
        ),
        "criterios_de_aplicabilidad": {
            CRITERIO_ANEXO_B: (
                "El Anexo B lo asigna en una fila que cita un caso B04-CA o una métrica B04-M."
            ),
            CRITERIO_DISCIPLINA: (
                "Un artefacto aprobado de ADR-002 importa su regla de forma expresa."
            ),
        },
        "conteos": {
            "pdp_ca_totales": len(canon.casos_pdp),
            "casos_ejecutados_por_ADR002": len(aplicables),
            "casos_tocados_por_dependencia": 0,
            "casos_fuera_de_alcance": len(excluidos),
        },
        "casos_ejecutados_por_ADR002": aplicables,
        "casos_fuera_de_alcance": excluidos,
        "familias_pdp": {
            "advertencia": (
                "No existe una sola cifra de «cobertura de familias de ADR-002». Se reportan "
                "cuatro denominadores distintos y no se agregan."
            ),
            "1_destino_directo_adr002_arq00_20": {
                "fuente": S2.FUENTE_ARQ00_20,
                "familias": familias_destino,
                "de": len(todas),
            },
            "2_entradas_obligatorias_declaradas": {
                "fuente": S2.FUENTE_FAMILIAS_ENTRADA,
                "familias": list(S2.FAMILIAS_ENTRADA_ADR002),
                "de": len(todas),
            },
            "3_tocadas_por_casos_sin_atribuir_cierre": {
                "fuente": S2.FUENTE_INSTANCIACION,
                "familias": sorted(tocadas),
                "de": len(todas),
                "nota": (
                    "Que un caso canónico toque una familia no cierra esa familia ni la "
                    "atribuye a ADR-002. El mínimo canónico por familia del PDP §8 exige "
                    "ejecutar todos sus casos asignados del banco de 304."
                ),
            },
            "4_fuera_de_alcance_de_adr002": {
                "familias": sorted(todas - set(familias_destino)),
                "responsables": {
                    f: CS.expandir_destinos(canon.destinos[f]["destino"])
                    for f in sorted(todas - set(familias_destino))
                },
            },
        },
    }


def construir_manifiesto(
    canon: CS.Canon,
    conformidad: dict[str, Any],
    rendimiento: dict[str, Any],
    casos: dict[str, Any],
    referencias: dict[str, Any],
    pdp: dict[str, Any],
) -> dict[str, Any]:
    return {
        "documento": "Manifiesto del benchmark de ADR-002",
        "version_contrato": S2.VERSION_CONTRATO,
        "estado": S2.ESTADO_NO_CONGELADO,
        "semilla_compartida": S2.SEMILLA,
        "advertencia": (
            "Ninguna puerta de arranque queda satisfecha por este manifiesto. "
            "ADR002-TOL-207 no está aprobada; TOL-208, TOL-209 y TOL-210 siguen NO SATISFECHAS. "
            "T0 no se ha ejecutado."
        ),
        "fuentes_canonicas": canon.huellas,
        "artefactos": {
            "corpus_conformidad": {
                "fichero": "conformance_corpus_v0_2.json",
                "version": conformidad["version"],
                "proposito": conformidad["proposito"],
                "conteos": conformidad["conteos"],
            },
            "corpus_rendimiento": {
                "fichero": "performance_corpus_v0_1.json",
                "version": rendimiento["version"],
                "proposito": rendimiento["proposito"],
                "escala_declarada": rendimiento["escala_declarada"],
                "conteos": rendimiento["conteos"],
            },
            "casos": {"fichero": "cases_v0_2.json", "conteos": casos["conteos"]},
            "referencias": {
                "fichero": "references_v0_2.json",
                "conteos": referencias["conteos"],
            },
            "casos_pdp": {"fichero": "pdp_cases_v0_1.json", "conteos": pdp["conteos"]},
        },
        "relacion_entre_corpus": {
            "regla": (
                "Los dos corpus comparten versión de contrato, semilla y anclajes. El de "
                "conformidad adjudica comportamiento; el de rendimiento mide magnitudes. "
                "Cambiar cualquiera exige nueva versión explícita de ambos."
            ),
            "anclajes_compartidos": conformidad["conteos"]["items"],
            "prohibicion": (
                "Prohibido fijar cifras de rendimiento sobre el corpus de conformidad y "
                "prohibido adjudicar conformidad sobre el corpus de rendimiento."
            ),
        },
        "artefactos_v0_1_conservados": [
            "corpus_v0_1.json",
            "cases_v0_1.json",
            "references_v0_1.json",
        ],
        "hallazgos_de_auditoria_cerrados": {
            "B-01": "Asignaciones RED<->CA<->M<->F leídas del Anexo B del DOCX y comparadas.",
            "B-02": "Bloques `canonico` e `instanciacion` separados, con fuente por campo.",
            "B-03": "estado_t0 = NO_MEDIDO en todos los casos; previsiones sin veredicto.",
            "M-01": "Ramas M4 instanciadas en CA-09, CA-10, CA-24 y CA-49.",
            "M-02": "Ramas diferenciadas en CA-36, CA-47 y CA-48.",
            "M-03": "Los catorce campos del PDP §7 más la condición de insuficiencia.",
            "M-04": "PDP-CA aplicables instanciados; el resto en matriz de exclusión.",
            "M-05": "Corpus de conformidad y de rendimiento separados.",
            "M-07": "Cardinalidad y parada sin atribución canónica indebida.",
            "menores": "Literalidad carácter a carácter y denominadores de familias por criterio.",
        },
        "hallazgos_no_tratados_en_esta_ronda": {
            "M-06": (
                "Presupuesto absoluto de almacenamiento: ADR002-TOL-207 no se aprueba ni se "
                "modifica en esta ronda."
            )
        },
    }


# ---------------------------------------------------------------------------
# 12. Volcado
# ---------------------------------------------------------------------------


def _volcar(ruta: Path, datos: dict[str, Any]) -> int:
    texto = json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    ruta.write_text(texto, encoding="utf-8")
    return len(texto.encode("utf-8"))


def construir_todo() -> dict[str, dict[str, Any]]:
    canon = CS.cargar_canon()
    conformidad = construir_corpus_conformidad(canon)
    rendimiento = construir_corpus_rendimiento(canon)
    casos = construir_casos(canon)
    referencias = construir_referencias(casos)
    pdp = construir_casos_pdp(canon)
    manifiesto = construir_manifiesto(canon, conformidad, rendimiento, casos, referencias, pdp)
    return {
        "conformance_corpus_v0_2.json": conformidad,
        "performance_corpus_v0_1.json": rendimiento,
        "cases_v0_2.json": casos,
        "references_v0_2.json": referencias,
        "pdp_cases_v0_1.json": pdp,
        "benchmark_manifest_v0_2.json": manifiesto,
    }


def main() -> None:
    for nombre, datos in construir_todo().items():
        n = _volcar(AQUI / nombre, datos)
        print(f"{nombre}: {n} bytes")


if __name__ == "__main__":
    main()
