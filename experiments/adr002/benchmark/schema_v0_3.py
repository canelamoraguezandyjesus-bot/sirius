"""Esquema v0.3 del benchmark de ADR-002.

Añade sobre el v0.2 —conservado intacto en ``schema_v0_2.py``— lo que el
paquete de trabajo 03C exige:

* **B-01** · invariantes mínimas del lector canónico y universos de identificador;
* **B-02** · contrato del corpus de rendimiento sintético **no degenerado**, con
  las invariantes distributivas que el validador calcula sobre los datos reales,
  y los parámetros de detección de contaminación por token, raíz, alias y
  n-grama;
* **B-03** · vocabulario de cierre `EXHAUSTIVA` verificable por cálculo;
* **B-04** · separación entre **casos funcionales** de nivel 1 y **reglas de
  protocolo del arnés**;
* la distinción entre `tolerancia_id` y `valor_pendiente_en`;
* la neutralidad tecnológica y entre `ADR002-A/B/C/D`.

Los vocabularios canónicos —modos, etapas, paradas, cardinalidad— no se
reproducen aquí: los lee ``canonical_source_v0_3`` directamente del DOCX.
"""

from __future__ import annotations

from typing import Final

from experiments.adr002.benchmark import schema as S

VERSION_CONTRATO: Final = "0.3"
VERSION_CORPUS_CONFORMIDAD: Final = "0.3"
VERSION_CORPUS_RENDIMIENTO: Final = "0.2"

# Semilla compartida por los dos corpus. Idéntica al v0.1 y al v0.2.
SEMILLA: Final = 20260726

# El "ahora" es un dato declarado, nunca la hora de ejecución.
AHORA_DECLARADO: Final = "2026-06-15T00:00:00Z"

ESTADO_NO_CONGELADO: Final = "PROPUESTO_NO_CONGELADO"
ESTADO_NO_NORMATIVO: Final = "NO_NORMATIVO_NO_CONGELABLE"

# --- Procedencia de cada campo ----------------------------------------------
FUENTE_CANONICA_CA: Final = "B04 v1.0 APROBADO §17/§17.1"
FUENTE_INSTANCIACION: Final = "Matriz/corpus ADR-002 v0.3 PROPUESTO"
FUENTE_CARDINALIDAD_B04: Final = "B04 v1.0 APROBADO §15.2"
FUENTE_PARADAS_B04: Final = "B04 v1.0 APROBADO §15.3"
FUENTE_ANEXO_B: Final = "Plan de Pruebas + RED/PDP v1.0 APROBADO · Anexo B"
FUENTE_PDP7: Final = "Plan de Pruebas + RED/PDP v1.0 APROBADO §7"
FUENTE_PDP9: Final = "Plan de Pruebas + RED/PDP v1.0 APROBADO §9 · casos transversales"
FUENTE_ARQ00_20: Final = "ARQ-00 v1.0 APROBADO §20"
FUENTE_ARQ00_23: Final = "ARQ-00 v1.0 APROBADO §23"

CAMPOS_CANONICOS: Final = ("riesgo", "entrada", "resultado_esperado", "fallo_observable")

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

# --- §4.3 · los catorce campos de la ficha del PDP §7 ------------------------
# Nombre canónico literal (columna «Campo» del DOCX) -> clave del artefacto.
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

CAMPO_INSUFICIENCIA: Final = "condicion_insuficiencia_para_expandir"

# Todo campo de la ficha declara fuente, sección, estado y justificación.
CLAVES_CAMPO: Final = ("valor", "fuente", "seccion", "estado", "justificacion")
ESTADOS_CAMPO: Final = ("CANONICO", "DERIVADO_PROPUESTO", "PENDIENTE_TOL209")

# Ningún campo de la ficha puede marcarse CANONICO sin texto literal que lo fije.
# La lista es la del §4.3 del paquete 03C, en claves de artefacto.
CAMPOS_SIN_CANONICO_AUTOMATICO: Final = (
    "objetivo",
    "unidad_de_trabajo",
    "entrada",
    "operacion_y_modo",
    "ambito",
    "tiempo_y_corte",
    "referencia",
    "criticidad",
    "tolerancias",
    "senales_observables",
    "id_y_familia",
    "evidencia",
    "resultado",
    "fallo",
    CAMPO_INSUFICIENCIA,
)

# --- Ramas -------------------------------------------------------------------
CLASES_RAMA: Final = ("CANONICA_REQUERIDA", "CONTROL_DIFERENCIAL")

# --- T0 · en los artefactos congelables solo cabe el estado ------------------
ESTADO_T0: Final = "NO_MEDIDO"
EXPRESABILIDAD: Final = (
    "EXPRESABLE_PREVISTO",
    "PARCIALMENTE_EXPRESABLE_PREVISTO",
    "NO_EXPRESABLE_PREVISTO",
    "NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION",
)
# Claves que un artefacto congelable NO puede contener: son previsión, no estado.
CLAVES_PREVISION_T0: Final = (
    "expresabilidad_prevista",
    "fundamento_de_prevision",
    "estado_por_requisito",
    "ejes_inseguros_medidos",
    "ejecutable_por_t0",
    "requiere_t1_t4",
)

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

CA_REQUIEREN_DOS_IMPLEMENTACIONES: Final = ("B04-CA-39",)

# --- §7.2 · tolerancia frente a valor pendiente ------------------------------
TOL_ORDEN_EQUIVALENCIA: Final = "ADR002-TOL-001"
TOL_BANDA_DIFERENCIAL: Final = "ADR002-TOL-201"
TOL_VALOR_PENDIENTE: Final = "ADR002-TOL-209"

# La regla existe y está identificada; lo que falta es su **valor**.
TOLERANCIA_POR_CASO: Final = {
    "B04-CA-37": TOL_BANDA_DIFERENCIAL,
    "B04-CA-48": TOL_BANDA_DIFERENCIAL,
    "B04-CA-39": TOL_ORDEN_EQUIVALENCIA,
}

# --- §4.2 · casos funcionales frente a reglas de protocolo del arnés ---------
# Solo estos dos PDP-CA tienen anclaje canónico vía Anexo B / RED-017.
PDP_CA_FUNCIONALES: Final = ("PDP-CA-09", "PDP-CA-22")
PDP_CA_REGLAS_DE_ARNES: Final = (
    "PDP-CA-02",
    "PDP-CA-03",
    "PDP-CA-06",
    "PDP-CA-16",
    "PDP-CA-17",
    "PDP-CA-18",
)
# Campos que una regla de arnés NO puede llevar: no es una consulta funcional.
CAMPOS_PROHIBIDOS_EN_REGLA: Final = (
    "consulta",
    "modo",
    "cardinalidad",
    "etapa",
    "parada",
    "elegibles",
    "prohibidos",
    "orden",
    "candidatos_elegibles",
    "candidatos_prohibidos",
    "t0",
    "prevision_t0",
    "expresabilidad_prevista",
    "ficha_pdp_7",
)
ESTADOS_APLICABILIDAD_REGLA: Final = ("APLICABLE", "APLICABLE_TRAS_CONGELACION", "NO_APLICA")

# --- Familias PDP · denominadores --------------------------------------------
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

# --- B-02 · corpus de rendimiento --------------------------------------------
ESCALA_RENDIMIENTO: Final = {
    "mensajes": 5000,
    "recuerdos": 500,
    "decisiones": 50,
    "proyectos": 2,
}
FUENTE_ESCALA: Final = "SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md · ADR002-TOL-208"
ESCALAS_PROYECCION: Final = (500, 5000, 50000)

# Los dos proyectos reales del corpus de rendimiento. No hay un tercero, y no
# existe un proyecto artificial único de volumen.
PROYECTOS_RENDIMIENTO: Final = ("PRJ-ARRECIFE", "PRJ-CUMBRE")

# Intervalo temporal declarado del corpus de rendimiento.
RENDIMIENTO_FECHA_INICIO: Final = "2025-03-01"
RENDIMIENTO_FECHA_FIN: Final = "2026-05-31"

# Invariantes distributivas: el validador las calcula **sobre los datos**.
INVARIANTES_DISTRIBUCION: Final = {
    "longitudes_distintas_min": 20,
    "desviacion_longitud_min": 15.0,
    "vocabulario_min": 150,
    "frecuencia_relativa_maxima_token": 0.06,
    "zipf_pendiente_min": -1.45,
    "zipf_pendiente_max": -0.55,
    "fechas_distintas_min": 60,
    "meses_distintos_min": 6,
    "cuota_maxima_por_proyecto": 0.60,
    "valores_min_por_eje": 2,
    "cuota_minima_valor_secundario": 0.02,
    "tipos_de_relacion_min": 4,
    "densidad_relaciones_min": 0.10,
    "proporcion_minima_entidades": 0.20,
    "proporcion_minima_alias": 0.05,
    "proporcion_minima_procedencias": 0.20,
    "proporcion_minima_criticidad": 0.10,
    "familias_tematicas_min": 5,
    "estructuras_gramaticales_min": 6,
    "textos_distintos_min": 0.98,
}

# Ejes de estado cuya variación el validador mide sobre los datos.
EJES_ESTADO: Final = (
    "confirmacion",
    "validez",
    "disponibilidad",
    "sensibilidad",
    "polaridad",
    "condicion_presente",
    "temporalidad_cerrada",
)

# --- §6.3 · contaminación -----------------------------------------------------
LONGITUD_RAIZ: Final = 6
LONGITUD_TOKEN_INFORMATIVO: Final = 4
SUFIJOS_FLEXIVOS: Final = (
    "s",
    "es",
    "a",
    "as",
    "o",
    "os",
    "al",
    "ales",
    "es",
)
# Pares mínimos que el paquete 03C exige detectar expresamente.
PARES_MINIMOS_DE_CONTAMINACION: Final = (
    ("turno", "turnos"),
    ("registro", "registrado"),
)

VACIAS: Final = frozenset(
    (
        "a",
        "al",
        "algo",
        "alguna",
        "algunas",
        "alguno",
        "algunos",
        "ante",
        "antes",
        "aqui",
        "aquel",
        "aquella",
        "aquello",
        "asi",
        "aun",
        "aunque",
        "bajo",
        "bien",
        "cada",
        "casi",
        "como",
        "con",
        "contra",
        "cual",
        "cuales",
        "cuando",
        "cuanto",
        "de",
        "del",
        "desde",
        "donde",
        "dos",
        "durante",
        "el",
        "ella",
        "ellas",
        "ello",
        "ellos",
        "en",
        "entre",
        "era",
        "eran",
        "eres",
        "es",
        "esa",
        "esas",
        "ese",
        "eso",
        "esos",
        "esta",
        "estan",
        "estas",
        "este",
        "esto",
        "estos",
        "fue",
        "fueron",
        "ha",
        "haber",
        "habia",
        "han",
        "hasta",
        "hay",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "mas",
        "me",
        "mi",
        "mientras",
        "muy",
        "nada",
        "ni",
        "no",
        "nos",
        "nuestra",
        "nuestro",
        "o",
        "os",
        "otra",
        "otras",
        "otro",
        "otros",
        "para",
        "pero",
        "poco",
        "por",
        "porque",
        "que",
        "quien",
        "se",
        "sea",
        "segun",
        "ser",
        "si",
        "sin",
        "sobre",
        "solo",
        "son",
        "su",
        "sus",
        "tambien",
        "tan",
        "tanto",
        "te",
        "tiene",
        "tienen",
        "todo",
        "todos",
        "tras",
        "un",
        "una",
        "uno",
        "unos",
        "y",
        "ya",
    )
)

# --- §7.2 · neutralidad -------------------------------------------------------
CANDIDATOS_ADR002: Final = ("ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D")
# Descriptores que identifican a un candidato concreto de ARQ-00 §23.
DESCRIPTORES_DE_CANDIDATO: Final = (
    "vectorial",
    "embedding",
    "embeddings",
    "relacional explicita",
    "senal semantica",
    "rrf",
    "reciprocal rank fusion",
    "grafo",
    "rdf",
    "sparql",
)
# Productos y motores concretos: ARQ-00 §23 los deja fuera hasta que la
# evidencia los justifique.
TECNOLOGIAS_CONCRETAS: Final = (
    "sqlite",
    "sqlite vec",
    "fts5",
    "postgresql",
    "postgres",
    "pgvector",
    "mysql",
    "mariadb",
    "duckdb",
    "elasticsearch",
    "opensearch",
    "lucene",
    "solr",
    "faiss",
    "annoy",
    "hnsw",
    "chroma",
    "qdrant",
    "weaviate",
    "pinecone",
    "milvus",
    "redis",
    "neo4j",
    "mongodb",
    "openai",
    "bm25",
)

# --- Vocabularios reutilizados sin cambios -----------------------------------
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
CONFIRMACION: Final = S.CONFIRMACION
VALIDEZ: Final = S.VALIDEZ
DISPONIBILIDAD: Final = S.DISPONIBILIDAD
SENSIBILIDAD: Final = S.SENSIBILIDAD
POLARIDAD: Final = S.POLARIDAD
AUTORIDAD: Final = S.AUTORIDAD
TIPOS_RELACION: Final = S.TIPOS_RELACION
CAMPOS_TEMPORALIDAD: Final = S.CAMPOS_TEMPORALIDAD


class ContratoCorpusV03Error(AssertionError):
    """Violación del contrato canónico del corpus v0.3."""
