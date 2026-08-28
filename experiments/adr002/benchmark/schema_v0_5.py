"""Esquema v0.5 del benchmark de ADR-002 · familia sucesora de conformidad.

Añade sobre el v0.4 —conservado intacto en ``schema_v0_4.py``— lo que el paso 1
del plan aprobado por la Resolución pre-benchmark v1.0 exige materializar:

* los **canales laterales** ``property_key`` y ``subject_key_experimental``, que
  no son campos del registro de ítem y que un candidato no puede leer porque no
  los recibe;
* el **plano común seguro** de criticidad y la tabla cerrada que lo produce;
* el **delta relacional discriminante** de ``ADR002-C``, con su condición léxica
  medida contra el tokenizador real del índice;
* la **clasificación por terna** ``(campo, consumidor, uso)``, con sus cinco
  capacidades y su fallo cerrado ante un campo sin clasificar.

Custodia: la familia es **append-only**. Los siete artefactos congelados de la
v0.4 se declaran aquí por blob y no se tocan; los tres heredados sin cambio
conservan su nombre y su número. Nada de este módulo mide rendimiento, ejecuta
candidatos ni autoriza el benchmark.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Final

from experiments.adr002.benchmark import schema as S1
from experiments.adr002.benchmark import schema_v0_3 as S3
from experiments.adr002.benchmark import schema_v0_4 as S4

VERSION_CONTRATO: Final = "0.5"
VERSION_CORPUS_CONFORMIDAD: Final = "0.5"
VERSION_CORPUS_RENDIMIENTO: Final = S4.VERSION_CORPUS_RENDIMIENTO  # 0.2, sin cambios

#: Se conserva la semilla de la v0.4: cambiarla regeneraría material congelado.
SEMILLA: Final = S4.SEMILLA
AHORA_DECLARADO: Final = S4.AHORA_DECLARADO

ESTADO_NO_CONGELADO: Final = S4.ESTADO_NO_CONGELADO
ESTADO_NO_NORMATIVO: Final = S4.ESTADO_NO_NORMATIVO

FUENTE_INSTANCIACION: Final = "Matriz/corpus ADR-002 v0.5 PROPUESTO"

# ---------------------------------------------------------------------------
# Vocabularios P2 · convenciones locales del banco, NO productivas
# ---------------------------------------------------------------------------

#: Se congelan como **convenciones locales experimentales**. No se atribuyen a
#: ADR-001 como vocabularios productivos y no deciden el vocabulario productivo
#: de Sirius: la familia sucesora los fija para poder validar contra algo
#: cerrado, no para legislar sobre el producto.
CONFIRMACION: Final = S3.CONFIRMACION
VALIDEZ: Final = S3.VALIDEZ
DISPONIBILIDAD: Final = S3.DISPONIBILIDAD
SENSIBILIDAD: Final = S3.SENSIBILIDAD
AUTORIDAD: Final = S3.AUTORIDAD
AMBITO: Final = S1.AMBITO
POLARIDAD: Final = S3.POLARIDAD
TIPOS_RELACION: Final = S3.TIPOS_RELACION
NIVEL_CRITICIDAD: Final = S3.NIVEL_CRITICIDAD
VACIAS: Final = S4.VACIAS
FUENTE_CRITICIDAD_COMPARTIDA: Final = S4.FUENTE_CRITICIDAD_COMPARTIDA
LONGITUD_RAIZ: Final = S4.LONGITUD_RAIZ
LONGITUD_TOKEN_INFORMATIVO: Final = S4.LONGITUD_TOKEN_INFORMATIVO
SHA256_PERFORMANCE_V0_2: Final = S4.SHA256_PERFORMANCE_V0_2

# ---------------------------------------------------------------------------
# Custodia append-only · qué se hereda y qué se materializa
# ---------------------------------------------------------------------------

#: Los siete congelables de la v0.4, por blob Git. La familia sucesora **no
#: reescribe ninguno**: un solo byte distinto invalida su congelación y este
#: mapa es lo que lo hace comprobable en cualquier momento.
BLOBS_V0_4: Final[Mapping[str, str]] = {
    "conformance_corpus_v0_4.json": "c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48",
    "cases_v0_4.json": "072753b96f4162fe88ce9c96660296349225c7be",
    "references_v0_4.json": "3fc9a63705144bf543266de129e17a17ab31c568",
    "pdp_cases_v0_3.json": "2eee45a04dee3d72f52ad00dfd46023d7c5e2199",
    "pdp_harness_rules_v0_2.json": "86e4f4ea6b4af3d445ec0f71c9772b46751a202b",
    "performance_corpus_v0_2.json": "4e9e2746e49b158a43eda7826b47c78c41b36e90",
    "benchmark_manifest_v0_4.json": "fa9a2f2b5d8d65aed811f039b2b279c5350d2132",
}

#: Artefactos que la v0.5 hereda **sin cambiar un byte** y que por tanto
#: conservan su propio número: la convención del repositorio versiona la familia
#: una vez y cada artefacto solo cuando su contenido cambia.
HEREDADOS_V0_5: Final[tuple[str, ...]] = (
    "pdp_cases_v0_3.json",
    "pdp_harness_rules_v0_2.json",
    "performance_corpus_v0_2.json",
)

#: Artefactos propios de la familia sucesora.
CONGELABLES_V0_5: Final[tuple[str, ...]] = (
    "conformance_corpus_v0_5.json",
    "subject_keys_v0_1.json",
    "property_keys_v0_1.json",
    "applied_criticality_v0_1.json",
    "cases_v0_5.json",
    "references_v0_5.json",
    "benchmark_manifest_v0_5.json",
)

#: Orden de materialización. **No es estilo**: es el mecanismo por el que la
#: anterioridad de los canales laterales respecto de casos y referencias queda
#: demostrada en vez de declarada (Resolución v0.4 §5.4).
ORDEN_DE_MATERIALIZACION: Final[tuple[str, ...]] = CONGELABLES_V0_5

#: La familia sucesora **no regenera** la proyección T0: hacerlo presupondría el
#: arnés de conformidad de T0, que no existe y cuya adjudicación es un paso
#: separado del plan aprobado. Su blob se registra como observación sin valor
#: vinculante, nunca como evidencia congelada.
PROYECCION_T0_NO_REGENERADA: Final = "t0_preexecution_projection_v0_2.json"
PROYECCION_T0_BLOB_OBSERVADO: Final = "3a241839b7eba84f12a3bbb3c643a17f7b0d0f91"
PROYECCION_T0_MOTIVO: Final = (
    "Regenerarla exigiria proyectar el caso discriminante sobre T0, y esa "
    "proyeccion presupondria el arnes de conformidad de T0, que NO EXISTE. El "
    "acta de congelacion v0.4 §6 prohibe ademas modificar el fichero original. "
    "La familia v0.5 declara expresamente que NO lleva proyeccion T0."
)

# ---------------------------------------------------------------------------
# Delta relacional discriminante de ADR002-C
# ---------------------------------------------------------------------------

#: Tipos que el delta **no** puede usar: la resolución exige un tipo distinto de
#: la supersesión y del conflicto, que ya están representados en la v0.4.
TIPOS_EXCLUIDOS_DEL_DELTA: Final[tuple[str, ...]] = ("SUSTITUYE_A", "CONFLICTO_CON")

#: Dependencia explícita, tipada y dirigida. Es el fenómeno que ``B04 §15.1``
#: asigna a ``E3``, y por tanto el que hace honesto al discriminante: no se pone
#: a prueba una relación exótica, sino la que la etapa debe cubrir.
TIPO_RELACION_DELTA: Final = "DERIVA_DE"

PROYECTO_DELTA: Final = "PRJ-DELTA"
ENTIDAD_ORIGEN_DELTA: Final = "ENT-ROTOR"
ENTIDAD_DESTINO_DELTA: Final = "ENT-BITACORA"
ITEM_ORIGEN_DELTA: Final = "MEM-950"
ITEM_DESTINO_DELTA: Final = "MEM-951"
RELACION_DELTA: Final = "REL-010"

TEXTO_ORIGEN_DELTA: Final = "El calibrado del rotor exige una holgura escalonada."
TEXTO_DESTINO_DELTA: Final = (
    "Cada bitacora municipal permanece archivada junto al deposito comarcal."
)
CONSULTA_DELTA: Final = "calibrado del rotor"
CONSULTA_PROPIA_DEL_DESTINO: Final = "bitacora municipal"

#: Instante declarado del delta. Anterior al ``AHORA_DECLARADO`` y sin cierre,
#: de modo que el operador ``VIGENTE_EN_INSTANTE`` lo admita sin ambigüedad.
INSTANTE_DELTA: Final = "2026-01-10T00:00:00Z"

#: Número de dominios de la v0.4 —``DOMINIOS`` más ``DOMINIOS_RAMA``— que el
#: barrido de impacto recalcula con y sin delta exigiendo **cero** cambios.
DOMINIOS_RECALCULADOS: Final = 66

# ---------------------------------------------------------------------------
# property_key · canal lateral
# ---------------------------------------------------------------------------

PREFIJO_PROPERTY_KEY: Final = "PK-"
LONGITUD_PROPERTY_KEY: Final = 12
RX_PROPERTY_KEY: Final = re.compile(rf"^{PREFIJO_PROPERTY_KEY}[0-9a-f]{{{LONGITUD_PROPERTY_KEY}}}$")

VERSION_VOCABULARIO_PROPERTY_KEY: Final = "P2-PROPERTY-KEY-0.1"
FUENTE_DE_ASIGNACION_PROPERTY_KEY: Final = (
    "Contenido y sujeto declarado del propio item del corpus de conformidad "
    "v0.5. Ningun artefacto de oraculo participa: la funcion generadora recibe "
    "el corpus y nada mas."
)
REGLA_DE_VALIDACION_PROPERTY_KEY: Final = (
    "Frontera estructural declarada: un item admite predicado sobre sujeto si y "
    "solo si declara EXACTAMENTE UNA entidad y conserva al menos una raiz "
    "discriminante tras retirar palabras funcionales y tokens del propio "
    "sujeto. Si falla cualquiera de las dos, el valor es null. Valor: "
    "PK-<sha256 de las raices ordenadas>[:12]."
)

#: Limitación declarada, no descubierta: la regla **no reconoce paráfrasis**.
#: Dos ítems que digan lo mismo con otras palabras reciben claves distintas y no
#: se agrupan. Es fallo cerrado deliberado: la duda no fusiona.
LIMITACION_PROPERTY_KEY: Final = (
    "No reconoce parafrasis: dos items equivalentes con vocabulario distinto "
    "reciben claves distintas y NO se agrupan. Limitacion deliberada y "
    "fallo-cerrado."
)

# ---------------------------------------------------------------------------
# subject_key_experimental · proyección definitiva
# ---------------------------------------------------------------------------

RX_SUBJECT_KEY: Final = re.compile(r"^[a-z0-9]+$")

VERSION_VOCABULARIO_SUBJECT_KEY: Final = "P2-SUBJECT-KEY-0.1"
FUENTE_DE_ASIGNACION_SUBJECT_KEY: Final = (
    "Entidades que el propio item declara en entity_ids, resueltas contra el "
    "bloque entidades del corpus de conformidad v0.5."
)
REGLA_DE_VALIDACION_SUBJECT_KEY: Final = (
    "0 entidades declaradas -> null (ausencia real). 1 entidad -> slug del "
    "nombre canonico. 2 o mas -> null (fallo cerrado: dos sujetos no son un "
    "sujeto). El slug NO lleva separador: A calcula su familia de E3 como "
    "plegar(subject_key).split('-')[0], de modo que sin guion la familia es la "
    "clave entera y coincide exactamente con la entidad."
)

#: Proyección expresamente descartada: fue la de las sondas, no la definitiva.
#: Con identificadores ``<CLASE>-<n>`` produce los prefijos ``mem`` y ``dec``,
#: ambos por encima de ``PREFIJO_MINIMO``, y por tanto es la **más permisiva**
#: para la expansión por familia de ``E3``, no la más conservadora.
PROYECCION_DE_SONDA_DESCARTADA: Final = "P-SUJETO-01: subject_key := id del item"


def slug_de_sujeto(nombre: str) -> str:
    """Slug estable y sin separador del nombre canónico de una entidad."""
    descompuesto = unicodedata.normalize("NFKD", nombre.lower())
    return "".join(c for c in descompuesto if c.isalnum() and not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Criticidad aplicada segura · tres planos
# ---------------------------------------------------------------------------

#: Vocabulario de procedencias de ``B04-Q21``, adoptado por la resolución §4.2.
FUENTES_DE_POLITICA: Final[tuple[str, ...]] = (
    "ACTO_EXPLICITO",
    "REQUISITO_O_DECISION_APROBADA",
    "ETIQUETA_DE_ESCENARIO",
    "REGLA_OPERATIVA_APROBADA",
)

#: Tabla cerrada de ``criticidad.fuente`` bruta —campo privado del arnés, que no
#: cruza— a ``fuente_de_politica`` segura. **Solo el resultado cruza la
#: frontera, nunca el dominio.** Una fuente bruta ausente de la tabla aborta la
#: construcción: no hay valor por defecto.
TABLA_FUENTE_DE_POLITICA: Final[Mapping[str, str]] = {
    "B04-CA-01": "ACTO_EXPLICITO",
    "B04-CA-02": "ACTO_EXPLICITO",
    "B04-CA-20": "ACTO_EXPLICITO",
    "B04-CA-21": "ACTO_EXPLICITO",
    "B04-CA-42": "REQUISITO_O_DECISION_APROBADA",
    "B04-CA-45": "REQUISITO_O_DECISION_APROBADA",
    S4.FUENTE_CRITICIDAD_COMPARTIDA: "ETIQUETA_DE_ESCENARIO",
    "REGLA-CRIT-07": "REGLA_OPERATIVA_APROBADA",
}

CAMPOS_CRITICIDAD_APLICADA: Final[tuple[str, ...]] = (
    "nivel",
    "razon_segura",
    "fuente_de_politica",
    "regla_de_politica",
)

#: Patrón de identificador de **caso del banco**. El control es preventivo: hoy
#: ningún valor de ``razon_segura`` ni de ``regla_de_politica`` coincide, y el
#: validador falla cerrado si alguna vez coincidiera. ``CRIT-0x`` es
#: deliberadamente un identificador de **política**, no de caso, y no encaja.
RX_IDENTIFICADOR_DE_CASO: Final = re.compile(
    r"\bB\d{2}-CA-\d+\b|\bPDP-CA-\d+\b|\bN[123]-\d+\b|\bB\d{2}-CA-\d+/R\d+\b"
)

USOS_PERMITIDOS_CRITICIDAD: Final[tuple[str, ...]] = (
    "G12",
    "tratamiento previo al limite",
    "desempate estable y registrado",
    "explicacion autorizada",
    "estado PARCIAL por desbordamiento critico",
    "handoff integro a B05",
)
USOS_PROHIBIDOS_CRITICIDAD: Final[tuple[str, ...]] = (
    "generar candidatas",
    "alterar similitud",
    "saltar etapas",
    "rescatar un elemento que no paso las puertas",
    "favorecer a un candidato",
)

# ---------------------------------------------------------------------------
# Clasificación por (campo, consumidor, uso) · cinco capacidades
# ---------------------------------------------------------------------------

CAPACIDADES: Final[tuple[str, ...]] = (
    "ENTRADA_DE_CANDIDATO",
    "SOLO_CAPA_COMUN",
    "COMUN_Y_SENAL_DECLARADA_DE_A",
    "HANDOFF_A_B05",
    "ORACULO_PROHIBIDO",
)

_ENTRADA: Final = "ENTRADA_DE_CANDIDATO"
_COMUN: Final = "SOLO_CAPA_COMUN"
_COMUN_Y_A: Final = "COMUN_Y_SENAL_DECLARADA_DE_A"
_B05: Final = "HANDOFF_A_B05"
_ORACULO: Final = "ORACULO_PROHIBIDO"

#: Una categoría global por campo no puede expresar que un mismo valor sea
#: legible por ``common`` para una cosa y por ``A`` para otra. La clasificación
#: es por **terna**: campo, quién y para qué.
CLASIFICACION: Final[Mapping[str, Mapping[str, object]]] = {
    # --- entrada de recuperación -----------------------------------------
    **{
        campo: {
            "capacidad": _ENTRADA,
            "consumidores": ("common", "ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D"),
            "uso_autorizado": "recuperacion",
            "uso_prohibido": "ninguno adicional",
        }
        for campo in (
            "id",
            "kind",
            "project_id",
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
            "procedencia",
            "entity_ids",
        )
    },
    # --- canales laterales ------------------------------------------------
    "property_key": {
        "capacidad": _COMUN,
        "consumidores": ("common",),
        "uso_autorizado": "decidir equivalencia entre identidades distintas",
        "uso_prohibido": (
            "cualquier lectura por un candidato; generar candidatas; ranking; "
            "calculo durante la consulta"
        ),
    },
    "subject_key_experimental": {
        "capacidad": _COMUN_Y_A,
        "consumidores": ("common", "ADR002-A"),
        "uso_autorizado": (
            "common: agrupacion y desempate de orden. ADR002-A: exclusivamente "
            "los tres usos que su ficha declara (E1 clave exacta, E3 familia por "
            "prefijo concreto y validacion semantica por item)"
        ),
        "uso_prohibido": "cualquier uso de un candidato no declarado en su ficha",
    },
    # --- criticidad aplicada segura ---------------------------------------
    **{
        campo: {
            "capacidad": _B05,
            "consumidores": ("common", "B05"),
            "uso_autorizado": "G12, limite, explicacion autorizada y traspaso integro a B05",
            "uso_prohibido": "lectura por un candidato; generar candidatas; alterar similitud",
        }
        for campo in CAMPOS_CRITICIDAD_APLICADA
    },
    # --- oráculo y metadatos privados del arnés ---------------------------
    **{
        campo: {
            "capacidad": _ORACULO,
            "consumidores": (),
            "uso_autorizado": "ninguno en el canal de recuperacion",
            "uso_prohibido": "todos",
        }
        for campo in (
            "criticidad.fuente",
            "criticidad.razon",
            "criticidad.regla",
            "items.traza",
            "relaciones.nota",
            "entidades.nota",
            "entidades.grupo_homonimo",
            "documentos.traza",
            "mensajes.traza",
            "cases",
            "references",
            "adjudicacion",
            "resultado_esperado",
            "elegibles",
            "prohibidos",
            "grupos_esperados",
            "etapa_esperada",
            "parada_esperada",
            "etiqueta_de_candidato",
            "proyeccion_t0",
        )
    },
}

#: Atributos que un candidato puede leer de las estructuras que recibe. El
#: control es **lista blanca por contención** —``atributos_leidos <=
#: ATRIBUTOS_PERMITIDOS``—, el mecanismo del precedente real de ``ADR002-B``. Una
#: búsqueda de ausencia de una cadena literal sería fallo-abierta y queda
#: excluida como control principal.
ATRIBUTOS_PERMITIDOS_AL_CANDIDATO: Final[frozenset[str]] = frozenset(
    {
        "id",
        "clase",
        "project_id",
        "texto",
        "subject_key",
        "vigente",
        "disponible",
        "created_at",
        "entity_ids",
        "clase_de_evidencia",
        "criticidad",
    }
)

#: Campos que NINGUNA estructura entregada a un candidato puede llevar.
ATRIBUTOS_VETADOS_AL_CANDIDATO: Final[frozenset[str]] = frozenset(
    {"property_key", "razon_segura", "fuente_de_politica", "regla_de_politica"}
)


class ContratoFamiliaV05Error(AssertionError):
    """Violación del contrato de la familia sucesora de conformidad v0.5."""


def capacidad_de(campo: str) -> str:
    """Capacidad declarada de un campo. **Falla cerrada** si no lo conoce.

    Un campo sin terna asignada no recibe una categoría por defecto: aborta la
    construcción de la proyección. Un valor por defecto convertiría el olvido de
    clasificar en una autorización silenciosa.
    """
    entrada = CLASIFICACION.get(campo)
    if entrada is None:
        msg = (
            f"campo sin terna asignada: {campo!r}; la clasificacion falla cerrada "
            f"y no admite valor por defecto"
        )
        raise ContratoFamiliaV05Error(msg)
    return str(entrada["capacidad"])


def legible_por(campo: str, consumidor: str) -> bool:
    """Si un consumidor concreto puede leer un campo concreto."""
    entrada = CLASIFICACION.get(campo)
    if entrada is None:
        raise ContratoFamiliaV05Error(f"campo sin terna asignada: {campo!r}")
    consumidores = entrada["consumidores"]
    assert isinstance(consumidores, tuple)
    return consumidor in consumidores


def contiene_identificador_de_caso(texto: str) -> bool:
    """True si el texto porta un identificador de caso del banco."""
    return bool(RX_IDENTIFICADOR_DE_CASO.search(texto or ""))


__all__ = [
    "AHORA_DECLARADO",
    "ATRIBUTOS_PERMITIDOS_AL_CANDIDATO",
    "ATRIBUTOS_VETADOS_AL_CANDIDATO",
    "BLOBS_V0_4",
    "CAMPOS_CRITICIDAD_APLICADA",
    "CAPACIDADES",
    "CLASIFICACION",
    "CONGELABLES_V0_5",
    "CONSULTA_DELTA",
    "CONSULTA_PROPIA_DEL_DESTINO",
    "DOMINIOS_RECALCULADOS",
    "ENTIDAD_DESTINO_DELTA",
    "ENTIDAD_ORIGEN_DELTA",
    "FUENTES_DE_POLITICA",
    "HEREDADOS_V0_5",
    "INSTANTE_DELTA",
    "ITEM_DESTINO_DELTA",
    "ITEM_ORIGEN_DELTA",
    "LONGITUD_PROPERTY_KEY",
    "ORDEN_DE_MATERIALIZACION",
    "PREFIJO_PROPERTY_KEY",
    "PROYECCION_T0_BLOB_OBSERVADO",
    "PROYECCION_T0_NO_REGENERADA",
    "PROYECTO_DELTA",
    "RELACION_DELTA",
    "RX_PROPERTY_KEY",
    "RX_SUBJECT_KEY",
    "SEMILLA",
    "TABLA_FUENTE_DE_POLITICA",
    "TEXTO_DESTINO_DELTA",
    "TEXTO_ORIGEN_DELTA",
    "TIPOS_EXCLUIDOS_DEL_DELTA",
    "TIPO_RELACION_DELTA",
    "VERSION_CONTRATO",
    "ContratoFamiliaV05Error",
    "capacidad_de",
    "contiene_identificador_de_caso",
    "legible_por",
    "slug_de_sujeto",
]
