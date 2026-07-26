"""Esquema v0.2 del benchmark de ADR-002.

Añade sobre el esquema v0.1 —que se conserva intacto en ``schema.py``— lo que
la auditoría adversarial independiente dejó abierto:

* separación explícita entre **canon** e **instanciación** (B-02, M-07);
* vocabulario de **ramas** canónicas requeridas (M-01, M-02);
* los catorce campos de la **ficha obligatoria de caso del PDP §7** (M-03);
* vocabulario de **previsión** frente a T0, sin veredicto (B-03);
* denominadores de **familias PDP** por criterio (defecto de cobertura);
* separación entre corpus de **conformidad** y corpus de **rendimiento**
  (M-05), con la escala de referencia del Registro de Tolerancias.

Los vocabularios canónicos —modos, etapas, paradas, cardinalidad— no se
reproducen aquí: los lee ``canonical_source`` directamente del DOCX.
"""

from __future__ import annotations

from typing import Final

from experiments.adr002.benchmark import schema as S

VERSION_CONTRATO: Final = "0.2"
VERSION_CORPUS_CONFORMIDAD: Final = "0.2"
VERSION_CORPUS_RENDIMIENTO: Final = "0.1"

# La semilla es la misma del v0.1: los dos corpus comparten generación.
SEMILLA: Final = 20260726

# El "ahora" es un dato declarado, nunca la hora de ejecución.
AHORA_DECLARADO: Final = "2026-06-15T00:00:00Z"

# --- Estado de los artefactos -----------------------------------------------
ESTADO_NO_CONGELADO: Final = "PROPUESTO_NO_CONGELADO"

# --- B-02 · procedencia de cada campo ---------------------------------------
FUENTE_CANONICA_CA: Final = "B04 v1.0 APROBADO §17/§17.1"
FUENTE_INSTANCIACION: Final = "Matriz/corpus ADR-002 v0.2 PROPUESTO"
FUENTE_CARDINALIDAD_B04: Final = "B04 v1.0 APROBADO §15.2"
FUENTE_PARADAS_B04: Final = "B04 v1.0 APROBADO §15.3"
FUENTE_ANEXO_B: Final = "Plan de Pruebas + RED/PDP v1.0 APROBADO · Anexo B"
FUENTE_PDP7: Final = "Plan de Pruebas + RED/PDP v1.0 APROBADO §7"
FUENTE_ARQ00_20: Final = "ARQ-00 v1.0 APROBADO §20"

# Los cinco únicos campos que B04 §17/§17.1 fija literalmente.
CAMPOS_CANONICOS: Final = (
    "riesgo",
    "entrada",
    "resultado_esperado",
    "fallo_observable",
)

# Campos de instanciación: arquitectónicos salvo que una fuente canónica
# concreta los fije literalmente. Cada uno registra su fuente individual.
CAMPOS_INSTANCIACION: Final = (
    "consulta",
    "modo",
    "proposito",
    "permiso",
    "ambito",
    "tiempo_objetivo",
    "corte_registro",
    "cardinalidad",
    "etapa",
    "parada",
    "orden",
    "elegibles",
    "prohibidos",
    "explicacion_esperada",
)

# --- M-03 · ficha obligatoria del PDP §7 ------------------------------------
# Nombre canónico del campo -> clave usada en el artefacto.
CAMPOS_PDP7: Final = {
    "ID y familia": "id_y_familia",
    "Objetivo": "objetivo",
    "Entrada": "entrada",
    "Unidad de trabajo": "unidad_de_trabajo",
    "Operación y modo": "operacion_y_modo",
    "Ámbito": "ambito",
    "Tiempo y corte": "tiempo_y_corte",
    "Referencia": "referencia",
    "Criticidad": "criticidad",
    "Tolerancias": "tolerancias",
    "Señales observables": "senales_observables",
    "Fallo": "fallo",
    "Evidencia": "evidencia",
    "Resultado": "resultado",
}

# Campos que la Especificación §5 campo 12 exige y el v0.1 no instanciaba.
CAMPO_INSUFICIENCIA: Final = "condicion_insuficiencia_para_expandir"

ESTADOS_CAMPO: Final = ("CANONICO", "DERIVADO_PROPUESTO", "PENDIENTE_TOL209")

# --- M-01 / M-02 · ramas ----------------------------------------------------
CLASES_RAMA: Final = ("CANONICA_REQUERIDA", "CONTROL_DIFERENCIAL")

# --- B-03 · previsión frente a T0, nunca veredicto --------------------------
ESTADO_T0: Final = "NO_MEDIDO"
EXPRESABILIDAD: Final = (
    "EXPRESABLE_PREVISTO",
    "PARCIALMENTE_EXPRESABLE_PREVISTO",
    "NO_EXPRESABLE_PREVISTO",
    "NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION",
)

# Estado medido de cada RF en Sirius 0.1, según el Inventario normativo v0.2
# §4 del repositorio. Es una medición registrada, no una fuente canónica: se
# usa solo para derivar una PREVISIÓN de expresabilidad, nunca un veredicto.
FUENTE_INVENTARIO: Final = "SIRIUS_0.2_ADR_002_INVENTARIO_NORMATIVO_v0.2_PROPUESTO.md §4"

RF_EXISTENTE: Final = ("B04-RF-31",)
RF_INSEGURO: Final = ("B04-RF-06", "B04-RF-14", "B04-RF-19")
RF_PARCIAL: Final = (
    "B04-RF-05",
    "B04-RF-09",
    "B04-RF-10",
    "B04-RF-15",
    "B04-RF-18",
    "B04-RF-21",
    "B04-RF-22",
    "B04-RF-24",
    "B04-RF-27",
    "B04-RF-28",
    "B04-RF-32",
)
RF_AUSENTE: Final = (
    "B04-RF-01",
    "B04-RF-02",
    "B04-RF-03",
    "B04-RF-04",
    "B04-RF-07",
    "B04-RF-08",
    "B04-RF-11",
    "B04-RF-12",
    "B04-RF-13",
    "B04-RF-16",
    "B04-RF-17",
    "B04-RF-20",
    "B04-RF-23",
    "B04-RF-25",
    "B04-RF-26",
    "B04-RF-29",
    "B04-RF-30",
)

ESTADO_RF_EN_T0: Final = {
    **{rf: "EXISTENTE" for rf in RF_EXISTENTE},
    **{rf: "INSEGURO" for rf in RF_INSEGURO},
    **{rf: "PARCIAL" for rf in RF_PARCIAL},
    **{rf: "AUSENTE" for rf in RF_AUSENTE},
}

# CA-39 compara dos realizaciones entre sí: no es ejecutable con una sola.
CA_REQUIEREN_DOS_IMPLEMENTACIONES: Final = ("B04-CA-39",)

# --- Familias PDP · entradas obligatorias declaradas por ADR-002 ------------
# `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.3_ABIERTO.md` §2.
FAMILIAS_ENTRADA_ADR002: Final = (
    "F01",
    "F02",
    "F03",
    "F04",
    "F05",
    "F06",
    "F10",
    "F11",
    "F14",
    "F15",
    "F22",
    "F23",
    "F24",
)
FUENTE_FAMILIAS_ENTRADA: Final = (
    "SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.3_ABIERTO.md §2"
)

# --- M-05 · escala del corpus de rendimiento --------------------------------
# `ADR002-TOL-208`: corpus de las cifras del Registro de Tolerancias v0.4.
ESCALA_RENDIMIENTO: Final = {
    "mensajes": 5000,
    "recuerdos": 500,
    "decisiones": 50,
    "proyectos": 2,
}
FUENTE_ESCALA: Final = "SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md · ADR002-TOL-208"
ESCALAS_PROYECCION: Final = (500, 5000, 50000)

# Proyecto reservado al volumen: aísla el relleno de todo ámbito canónico.
PROYECTO_VOLUMEN: Final = "PRJ-VOLUMEN"

# Términos que el relleno de volumen NO puede contener, porque son los
# anclajes léxicos de los casos canónicos. El validador lo comprueba.
TERMINOS_ANCLA: Final = (
    "atlas",
    "juan",
    "coche",
    "automóvil",
    "vehículo",
    "postgresql",
    "postgres",
    "presupuesto",
    "escala",
    "nimbo",
    "madeira",
    "canarias",
    "teletrabajo",
    "aforo",
    "mensajería",
    "embalaje",
    "nómina",
    "almacén",
    "firmas",
    "paa",
    "redactes",
    "reuniones",
    "descuento",
    "mantenimiento",
    "migración",
    "faro",
)

# --- Vocabularios reutilizados del v0.1, sin cambios ------------------------
MODOS: Final = S.MODOS
ETAPAS: Final = S.ETAPAS
PARADAS: Final = S.PARADAS
CARDINALIDADES: Final = S.CARDINALIDADES
CA_TOTALES: Final = S.CA_TOTALES
RF_TOTALES: Final = S.RF_TOTALES
M_TOTALES: Final = S.M_TOTALES
FAMILIAS_PDP: Final = S.FAMILIAS_PDP
RED_ADR002: Final = S.RED_ADR002
RED_INTERFAZ_REGISTRADA: Final = S.RED_INTERFAZ_REGISTRADA
ESTADOS_SUFICIENCIA: Final = S.ESTADOS_SUFICIENCIA
ESTADO_EXTERNO_SEGURO: Final = S.ESTADO_EXTERNO_SEGURO
NIVEL_CRITICIDAD: Final = S.NIVEL_CRITICIDAD
CAMPOS_TEMPORALIDAD: Final = S.CAMPOS_TEMPORALIDAD


class ContratoCorpusV02Error(AssertionError):
    """Violación del contrato canónico del corpus v0.2."""
