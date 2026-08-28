"""Esquema v0.4 del benchmark de ADR-002 · paquete 03D.

Añade sobre el v0.3 —conservado intacto en ``schema_v0_3.py``— la tercera capa
del modelo: la **adjudicación**. El canon no se reescribe; la instanciación
declara las decisiones sintéticas; la adjudicación calcula qué elementos
entran, salen, se devuelven o quedan pendientes.

Novedades:

* vocabulario del bloque ``adjudicacion`` y de sus dominios;
* vocabulario cerrado de **variables observables** de la condición de
  insuficiencia: cualquier variable ajena falla;
* prohibición de **magnitudes numéricas** bajo ``PENDIENTE_TOL209``, con
  excepción explícita para identificadores;
* lista explícita ``CONGELABLES_V0_4`` — la proyección T0 no forma parte;
* huella congelada de ``performance_corpus_v0_2.json``;
* **guardas derivadas de neutralidad sintética** para el corpus de
  rendimiento: cotas absolutas calculables por un oráculo independiente del
  generador. No son canon: son guardas del arnés.
"""

from __future__ import annotations

import re
from typing import Final

from experiments.adr002.benchmark import schema_v0_3 as S3

VERSION_CONTRATO: Final = "0.4"
VERSION_CORPUS_CONFORMIDAD: Final = "0.4"
VERSION_CORPUS_RENDIMIENTO: Final = "0.2"  # sin cambios: byte a byte

SEMILLA: Final = S3.SEMILLA
AHORA_DECLARADO: Final = S3.AHORA_DECLARADO

ESTADO_NO_CONGELADO: Final = S3.ESTADO_NO_CONGELADO
ESTADO_NO_NORMATIVO: Final = S3.ESTADO_NO_NORMATIVO

FUENTE_CANONICA_CA: Final = S3.FUENTE_CANONICA_CA
FUENTE_INSTANCIACION: Final = "Matriz/corpus ADR-002 v0.4 PROPUESTO"
FUENTE_CARDINALIDAD_B04: Final = S3.FUENTE_CARDINALIDAD_B04
FUENTE_PARADAS_B04: Final = S3.FUENTE_PARADAS_B04
FUENTE_ANEXO_B: Final = S3.FUENTE_ANEXO_B
FUENTE_PDP7: Final = S3.FUENTE_PDP7
FUENTE_PDP9: Final = S3.FUENTE_PDP9
FUENTE_ARQ00_20: Final = S3.FUENTE_ARQ00_20

# ---------------------------------------------------------------------------
# Adjudicación · vocabularios del dominio y del cierre
# ---------------------------------------------------------------------------

CLAVES_ADJUDICACION: Final = (
    "dominio",
    "candidatos_considerados",
    "elegibles_semanticos",
    "resultado_esperado",
    "pendientes_por_limite",
    "excluidos_por_estado",
    "prohibidos_entre_candidatos",
    "decoys_fuera_de_ambito",
    "estado",
    "justificacion",
)

COLECCIONES: Final = ("items", "mensajes", "documentos")

REGLAS_MULTIPROYECTO: Final = (
    "SOLO_PROYECTO",
    "CON_GLOBAL",
    "CON_LISTAS_CERRADAS",
    "GLOBAL_TODOS",
)

OPERADORES_TEMPORALES: Final = (
    "SIN_FILTRO",
    "VIGENTE_EN_INSTANTE",
    "SOLAPA_INTERVALO",
    "OCCURRED_EN_INTERVALO",
    "REGISTRADO_HASTA",
)

TIPOS_LIMITE: Final = ("DURO", "OBJETIVO")
DESEMPATES: Final = ("ID", "CRITICOS_PRIMERO_LUEGO_ID")

# Dimensiones admisibles en `excluidos_por_estado`.
DIMENSIONES_DE_EXCLUSION: Final = (
    "confirmacion",
    "validez",
    "disponibilidad",
    "tiempo_valido",
    "occurred_at",
    "recorded_at",
    "accesible",
    "no_guardar",
    "redactado",
)

# Razones admisibles en `prohibidos_entre_candidatos` (puertas del arnés).
RAZONES_DE_PROHIBICION: Final = (
    "PUERTA_PROPOSITO_NO_AUTORIZADO",
    "PUERTA_NO_USAR_COMO_MEMORIA",
    "PUERTA_MARCA_EN_CONTENIDO",
    "DISTRACTOR_RUIDO",
)

# Estados eligibles por defecto: un dominio puede sobreescribirlos declarando
# su justificación (p. ej. CA-05 pide expresamente lo SUSTITUIDO).
ESTADOS_ELEGIBLES_DEFECTO: Final = {
    "confirmacion": ("CONFIRMADA",),
    "validez": ("VIGENTE",),
    "disponibilidad": ("DISPONIBLE",),
    "sensibilidad": ("ORDINARIA",),
}

# ---------------------------------------------------------------------------
# Universo crítico · censo puente canon <-> corpus (paquete 03D)
# ---------------------------------------------------------------------------

# Premisa numérica literal de cada caso, contra la que el validador cuenta.
PREMISAS_CRITICAS: Final = {
    "B04-CA-31": {"ambito": "PRJ-ALFA", "elegibles": 5, "devueltos": 5, "pendientes": 0},
    "B04-CA-44": {"ambito": "PRJ-GAMMA", "elegibles": 6, "devueltos": 5, "pendientes": 1},
    "B04-CA-26": {"ambito": "PRJ-GAMMA", "elegibles": 11, "devueltos": 11, "pendientes": 0},
    "B04-CA-38": {"ambito": "PRJ-GAMMA", "elegibles": 12, "devueltos": 10, "pendientes": 2},
}

CRITICOS_ALFA_V0_4: Final = ("DEC-003", "DEC-010", "MEM-014", "MEM-016", "MEM-025")
CRITICOS_GAMMA_V0_4: Final = tuple(f"MEM-{n}" for n in range(101, 113))

FECHAS_CRITICOS_GAMMA: Final = {
    **{f"MEM-{n}": "2026-01-05T00:00:00Z" for n in range(101, 107)},
    **{f"MEM-{n}": "2026-03-01T00:00:00Z" for n in range(107, 112)},
    "MEM-112": "2026-05-01T00:00:00Z",
}

FUENTE_CRITICIDAD_COMPARTIDA: Final = (
    "Instanciación compartida por B04-CA-26, B04-CA-38 y B04-CA-44"
)

# ---------------------------------------------------------------------------
# Insuficiencia · vocabulario cerrado de variables observables
# ---------------------------------------------------------------------------

VARIABLES_INSUFICIENCIA: Final = frozenset(
    (
        "resultado_estructurado_exacto",
        "criticos_elegibles_pendientes",
        "cardinalidad",
        "cobertura_lexica_directa",
        "variantes_y_alias_autorizados_no_explorados",
        "suficiencia_tras_expansion_lexica",
        "espacio_autorizado_no_agotado",
        "ausencia_de_resultado_utilizable",
        "evidencia_no_canonica_atribuible",
        "insuficiencia_persistente_tras_fallback",
        "ultimo_espacio_autorizado",
    )
)

# Modos que no recorren la escalera E0-E5 de recuperación ordinaria: sus ramas
# declaran NO_APLICA con razón verificable, nunca una cadena heredada.
MODOS_SIN_ESCALERA: Final = ("M3", "M4")

# ---------------------------------------------------------------------------
# Tolerancias pendientes · prohibición de magnitudes
# ---------------------------------------------------------------------------

# Identificadores permitidos dentro de un texto PENDIENTE_TOL209. Se eliminan
# antes de buscar dígitos: lo que quede con un dígito es una magnitud inventada.
RX_IDENTIFICADORES_PERMITIDOS: Final = re.compile(
    r"(?:ADR002-)?TOL-\d+[A-Z]?"
    r"|RED-\d{3}"
    r"|B\d{2}-(?:RF|CA|M|Q|D)-?\d+"
    r"|B\d{2}\b"  # identificador de bloque desnudo: «B04/B05»
    r"|PDP-(?:CA|M)-?\d+"
    r"|CRIT-\d+"
    r"|§\s*\d+(?:\.\d+)*"
    r"|v\d+\.\d+"
)
RX_DIGITO: Final = re.compile(r"\d")

CLAVES_TEXTO_TOLERANCIA: Final = ("regla", "condicion_aplicada")

# ---------------------------------------------------------------------------
# PDP-CA funcionales · referencia de recuento, no de recuperación
# ---------------------------------------------------------------------------

TIPO_REFERENCIA_RECUPERACION: Final = "RECUPERACION_B04"
TIPO_REFERENCIA_RECUENTO: Final = "RECUENTO_INDEPENDENCIA_DE_CONSUMIDORES"

# Claves de vocabulario de recuperación que un caso de recuento NO puede
# instanciar con valor: se declaran NO_APLICA.
CAMPOS_RECUPERACION_NO_APLICABLES: Final = (
    "modo",
    "cardinalidad",
    "etapa",
    "parada",
    "elegibles",
    "prohibidos",
    "orden",
)

# ---------------------------------------------------------------------------
# Reglas del arnés · estado de la fuente que importa cada regla
# ---------------------------------------------------------------------------

ESTADOS_FUENTE_REGLA: Final = ("APROBADO", "PROPUESTO", "PUERTA_NO_SATISFECHA")

ESTADO_FUENTE_POR_REGLA: Final = {
    # Registro de Tolerancias v0.4: APROBADO el 26-07-2026 (acta y Nota de
    # superación 02 §2, blob verificado). El nombre del fichero conserva
    # PROPUESTO como instantánea histórica (docs/canonical/STATUS.md).
    "PDP-CA-02": (
        "APROBADO",
        "Registro de Tolerancias v0.4 §9 regla 1 · aprobado el 26-07-2026 "
        "(SIRIUS_0.2_ADR_002_REGISTRO_TOLERANCIAS_APROBACION_v1.0.md)",
    ),
    "PDP-CA-03": ("PROPUESTO", "Protocolo de medición v0.1 PROPUESTO §6.5/§6.6"),
    "PDP-CA-06": (
        "PUERTA_NO_SATISFECHA",
        "ADR002-TOL-210: la regla está aprobada dentro del Registro v0.4, pero la "
        "puerta que gobierna sigue NO SATISFECHA",
    ),
    "PDP-CA-16": ("PROPUESTO", "Protocolo de medición v0.1 PROPUESTO §7"),
    "PDP-CA-17": (
        "APROBADO",
        "Registro de Tolerancias v0.4 §9 reglas 1 y 10 · aprobado el 26-07-2026",
    ),
    "PDP-CA-18": (
        "APROBADO",
        "ADR002-TOL-107 · fila del Registro de Tolerancias v0.4 aprobado",
    ),
}

# ---------------------------------------------------------------------------
# T0 · lista explícita de congelables y claves prohibidas
# ---------------------------------------------------------------------------

CONGELABLES_V0_4: Final = (
    "conformance_corpus_v0_4.json",
    "cases_v0_4.json",
    "references_v0_4.json",
    "pdp_cases_v0_3.json",
    "pdp_harness_rules_v0_2.json",
    "performance_corpus_v0_2.json",
    "benchmark_manifest_v0_4.json",
)
# La proyección T0 queda expresamente FUERA de los congelables.
NO_CONGELABLES_V0_4: Final = ("t0_preexecution_projection_v0_2.json",)

CLAVES_PREVISION_T0: Final = S3.CLAVES_PREVISION_T0
# Valores de previsión que ningún congelable puede contener como texto.
VALORES_PREVISION_T0: Final = (
    "EXPRESABLE_PREVISTO",
    "PARCIALMENTE_EXPRESABLE_PREVISTO",
    "NO_EXPRESABLE_PREVISTO",
    "NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION",
)

# ---------------------------------------------------------------------------
# Corpus de rendimiento · huella congelada, alcance y guardas
# ---------------------------------------------------------------------------

SHA256_PERFORMANCE_V0_2: Final = "c5a161cbdaa7ee150c08e663fa72663324375aa6654f3216a73e90d6b182666b"

ALCANCE_RENDIMIENTO: Final = {
    "mide": (
        "coste",
        "almacenamiento",
        "latencia",
        "construccion",
        "reconstruccion",
        "estabilidad",
        "escalabilidad_sintetica",
    ),
    "no_mide": (
        "calidad_funcional",
        "exactitud_semantica",
        "comparacion_de_senales_entre_ADR002_A_B_C_D",
        "validacion_de_los_tres_ejes_temporales",
    ),
    "motivo": (
        "Corpus semánticamente inerte por construcción: las entidades no se "
        "mencionan en los textos, las relaciones no comparten léxico y los tres "
        "ejes temporales son monotónicos. Sirve para magnitudes, nunca para "
        "adjudicar calidad."
    ),
}

# Guardas del arnés, no canon. Calculadas por oráculo independiente.
NOMBRE_GUARDAS: Final = "GUARDAS_DERIVADAS_DE_NEUTRALIDAD_SINTETICA"
GUARDAS_RENDIMIENTO: Final = {
    "im_tema_proyecto_bits_max": 0.01,
    "exceso_estado_palabra_max": 0.25,
    "n_minimo_exceso": 40,
    "proyectos_minimos_por_entidad_con_alias": 2,
    "cuota_maxima_tipo_relacion": 0.40,
    "intra_proyecto_min": 0.35,
    "intra_proyecto_max": 0.65,
}

# ---------------------------------------------------------------------------
# Reutilizado sin cambios del v0.3
# ---------------------------------------------------------------------------

CAMPOS_CANONICOS: Final = S3.CAMPOS_CANONICOS
CAMPOS_INSTANCIACION: Final = S3.CAMPOS_INSTANCIACION
CAMPOS_PDP7: Final = S3.CAMPOS_PDP7
CAMPO_INSUFICIENCIA: Final = S3.CAMPO_INSUFICIENCIA
CLAVES_CAMPO: Final = S3.CLAVES_CAMPO
ESTADOS_CAMPO: Final = S3.ESTADOS_CAMPO
CLASES_RAMA: Final = S3.CLASES_RAMA
ESTADO_T0: Final = S3.ESTADO_T0
EXPRESABILIDAD: Final = S3.EXPRESABILIDAD
FUENTE_INVENTARIO: Final = S3.FUENTE_INVENTARIO
ESTADO_RF_EN_T0: Final = S3.ESTADO_RF_EN_T0
CA_REQUIEREN_DOS_IMPLEMENTACIONES: Final = S3.CA_REQUIEREN_DOS_IMPLEMENTACIONES
TOL_ORDEN_EQUIVALENCIA: Final = S3.TOL_ORDEN_EQUIVALENCIA
TOL_BANDA_DIFERENCIAL: Final = S3.TOL_BANDA_DIFERENCIAL
TOL_VALOR_PENDIENTE: Final = S3.TOL_VALOR_PENDIENTE
TOLERANCIA_POR_CASO: Final = S3.TOLERANCIA_POR_CASO
PDP_CA_FUNCIONALES: Final = S3.PDP_CA_FUNCIONALES
PDP_CA_REGLAS_DE_ARNES: Final = S3.PDP_CA_REGLAS_DE_ARNES
CAMPOS_PROHIBIDOS_EN_REGLA: Final = S3.CAMPOS_PROHIBIDOS_EN_REGLA
ESTADOS_APLICABILIDAD_REGLA: Final = S3.ESTADOS_APLICABILIDAD_REGLA
FAMILIAS_ENTRADA_ADR002: Final = S3.FAMILIAS_ENTRADA_ADR002
FUENTE_FAMILIAS_ENTRADA: Final = S3.FUENTE_FAMILIAS_ENTRADA
ESCALA_RENDIMIENTO: Final = S3.ESCALA_RENDIMIENTO
FUENTE_ESCALA: Final = S3.FUENTE_ESCALA
INVARIANTES_DISTRIBUCION: Final = S3.INVARIANTES_DISTRIBUCION
EJES_ESTADO: Final = S3.EJES_ESTADO
LONGITUD_RAIZ: Final = S3.LONGITUD_RAIZ
LONGITUD_TOKEN_INFORMATIVO: Final = S3.LONGITUD_TOKEN_INFORMATIVO
SUFIJOS_FLEXIVOS: Final = S3.SUFIJOS_FLEXIVOS
PARES_MINIMOS_DE_CONTAMINACION: Final = S3.PARES_MINIMOS_DE_CONTAMINACION
VACIAS: Final = S3.VACIAS
CANDIDATOS_ADR002: Final = S3.CANDIDATOS_ADR002
DESCRIPTORES_DE_CANDIDATO: Final = S3.DESCRIPTORES_DE_CANDIDATO
TECNOLOGIAS_CONCRETAS: Final = S3.TECNOLOGIAS_CONCRETAS
MODOS: Final = S3.MODOS
ETAPAS: Final = S3.ETAPAS
PARADAS: Final = S3.PARADAS
CARDINALIDADES: Final = S3.CARDINALIDADES
CA_TOTALES: Final = S3.CA_TOTALES
RF_TOTALES: Final = S3.RF_TOTALES
ESTADOS_SUFICIENCIA: Final = S3.ESTADOS_SUFICIENCIA
NIVEL_CRITICIDAD: Final = S3.NIVEL_CRITICIDAD
TIPOS_RELACION: Final = S3.TIPOS_RELACION


def magnitud_inventada(texto: str) -> bool:
    """True si el texto contiene un dígito que no pertenece a un identificador."""
    limpio = RX_IDENTIFICADORES_PERMITIDOS.sub(" ", texto or "")
    return bool(RX_DIGITO.search(limpio))


class ContratoCorpusV04Error(AssertionError):
    """Violación del contrato canónico del corpus v0.4."""
