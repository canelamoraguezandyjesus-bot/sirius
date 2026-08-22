"""Esquema del corpus, los casos y las referencias del benchmark de ADR-002.

Las siete dimensiones son las canónicas de ADR-001 v1.1 y permanecen
ortogonales: confirmación, validez, disponibilidad, sensibilidad,
temporalidad, ámbito y autoridad. Ninguna se condensa en un enum monolítico.

Los vocabularios de modo, etapa, parada, puerta y cardinalidad se reproducen
de B04 v1.0 APROBADO. No se inventa ningún valor.
"""

from __future__ import annotations

from typing import Final

# --- B04 §5 · modos de recuperación --------------------------------------
MODOS: Final = ("M1", "M2", "M3", "M4", "M5")

# --- B04 §15.1 · etapas de la política aprobada --------------------------
ETAPAS: Final = ("E0", "E1", "E2", "E3", "E4", "E5")

# --- B04 §15.3 · criterios de parada -------------------------------------
PARADAS: Final = ("S1", "S2", "S3", "S4", "S5", "S6", "S7")

# --- B04 §11 · puertas ----------------------------------------------------
PUERTAS: Final = tuple(f"G{i}" for i in range(1, 13))

# --- B04 §15.2 · cardinalidad --------------------------------------------
CARDINALIDADES: Final = ("EXACTA", "ACOTADA", "EXHAUSTIVA")

# --- ADR-001 v1.1 · siete dimensiones ortogonales ------------------------
CONFIRMACION: Final = ("CONFIRMADA", "CANDIDATA", "RECHAZADA", "SUPRIMIDA")
VALIDEZ: Final = ("VIGENTE", "SUSTITUIDA", "INVALIDADA", "SIN_SOPORTE")
DISPONIBILIDAD: Final = (
    "DISPONIBLE",
    "ARCHIVADA",
    "ELIMINADA",
    "PURGADA",
    "NO_GUARDADA",
)
SENSIBILIDAD: Final = ("ORDINARIA", "RESTRINGIDA")
AMBITO: Final = ("GLOBAL", "PROYECTO", "MULTI_PROYECTO_CERRADO")
AUTORIDAD: Final = (
    "DOCUMENTO_CANONICO",
    "ACTO_EXPLICITO_USUARIO",
    "INFORMAL",
    "FUENTE_EXTERNA",
)
DIMENSIONES_CANONICAS: Final = (
    "confirmacion",
    "validez",
    "disponibilidad",
    "sensibilidad",
    "temporalidad",
    "ambito",
    "autoridad",
)

# --- B04 §6 · origen de la marca de criticidad ---------------------------
ORIGEN_CRITICIDAD: Final = (
    "EXPLICITO_USUARIO",
    "DOCUMENTO_O_DECISION_APROBADA",
    "CLASIFICACION_OPERATIVA",
    "ADJUDICACION_DE_PRUEBA",
)
NIVEL_CRITICIDAD: Final = ("CRITICO", "IMPORTANTE", "ORDINARIO")

# --- B04 §17 CA-17/CA-36 · taxonomía interna de ausencia -----------------
ESTADOS_SUFICIENCIA: Final = (
    "COMPLETO",
    "PARCIAL",
    "NINGUNO_EN_AMBITO",
    "SOLO_HISTORICO",
    "SOLO_CANDIDATA",
    "FUERA_DE_AMBITO",
    "FUENTE_INACCESIBLE",
    "CONSULTA_AMBIGUA",
    "NO_REPORTABLE",
)
# B04-RF-25 y B04-Q15: estado externo agregado y único.
ESTADO_EXTERNO_SEGURO: Final = "SIN_RESULTADO_UTILIZABLE"

# --- B04 §16 · requisitos funcionales ------------------------------------
RF_TOTALES: Final = tuple(f"B04-RF-{i:02d}" for i in range(1, 33))
# --- B04 §17 · casos de aceptación ---------------------------------------
CA_TOTALES: Final = tuple(f"B04-CA-{i:02d}" for i in range(1, 51))
# --- B04 §18 · métricas ---------------------------------------------------
M_TOTALES: Final = tuple(f"B04-M{i:02d}" for i in range(1, 22))
# --- B04 §19 · decisiones -------------------------------------------------
D_TOTALES: Final = tuple(f"B04-D{i:02d}" for i in range(1, 17))

# --- PDP-1.0 §8 · familias obligatorias del corpus -----------------------
FAMILIAS_PDP: Final = tuple(f"F{i:02d}" for i in range(1, 26))

# --- RED-1.0 · delegaciones que ADR-002 traza directamente ---------------
RED_ADR002: Final = (
    "RED-027",
    "RED-028",
    "RED-029",
    "RED-030",
    "RED-031",
    "RED-032",
    "RED-033",
    "RED-034",
)
# RED-040 pertenece a B05/ADR-003B; ADR-002 solo registra la interfaz.
RED_INTERFAZ_REGISTRADA: Final = ("RED-040",)

# --- Niveles de caso · Especificación de benchmark v0.2 §2 ---------------
NIVELES_CASO: Final = (1, 2, 3)

# --- Campos obligatorios ---------------------------------------------------
CAMPOS_CASO: Final = (
    "id",
    "nivel",
    "identificador_canonico",
    "requisito_verificado",
    "familia_pdp",
    "metrica_y_umbral",
    "datos_sinteticos",
    "consulta",
    "modo",
    "proposito",
    "permiso",
    "ambito",
    "tiempo_objetivo",
    "corte_registro",
    "candidatos_elegibles",
    "candidatos_prohibidos",
    "resultado_esperado",
    "orden_esperado",
    "explicacion_esperada",
    "etapa_esperada",
    "parada_esperada",
    "cardinalidad",
    "criticidad",
    "ejecutable_por_t0",
    "requiere_t1_t4",
    "evidencia_minima",
    "fallo_observable",
    "traza_red",
)

CAMPOS_ITEM: Final = (
    "id",
    "kind",
    "project_id",
    "entity_ids",
    "text",
    "polaridad",
    "condicion",
    "confirmacion",
    "validez",
    "disponibilidad",
    "sensibilidad",
    "temporalidad",
    "ambito",
    "autoridad",
    "no_usar_como_memoria",
    "no_consolidable",
    "criticidad",
    "procedencia",
    "traza",
)

CAMPOS_TEMPORALIDAD: Final = (
    "valid_from",
    "valid_to",
    "occurred_at",
    "recorded_at",
)

POLARIDAD: Final = ("AFIRMATIVA", "NEGATIVA")
KIND_ITEM: Final = ("MEMORIA", "DECISION")
TIPOS_RELACION: Final = (
    "APOYA",
    "REFUTA",
    "CONFLICTO_CON",
    "CORRIGE",
    "SUSTITUYE_A",
    "ALIAS_DE",
    "DERIVA_DE",
    "ORIGINA_CANDIDATA",
)


class ContratoCorpusError(AssertionError):
    """Violación del contrato canónico del corpus."""
