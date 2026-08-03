"""Esquema v0.6 del benchmark de ADR-002 · corrección mínima de `B04-CA-19`.

Existe por **un solo defecto** de la familia v0.5, y no corrige nada más.

`B04-CA-19` exige que `DEC-006`, `DEC-007` y `DEC-008` formen un grupo con
representante justificado y **tres procedencias**. En la v0.5 los tres comparten
texto literal —«La plataforma de despliegue aprobada es Nimbo.»— y aportan
`DOC-001`, `DOC-002` y `MSG-030`, pero **ninguno declara entidad**, de modo que
la regla aprobada les asigna ``subject_key_experimental = null`` y
``property_key = null``. Y la regla de agrupación prohíbe agrupar cuando esos
ejes son desconocidos: la duda no fusiona. La v0.5 queda por tanto **congelada
como identidad histórica pero no apta para continuar**.

La corrección es la mínima posible: **una entidad sintética** para el concepto
que los tres enuncian, asignada **exclusivamente** a esos tres ítems, y la
**regeneración de los dos canales laterales con la regla ya aprobada**, sin
tocar una sola línea de esa regla.

Custodia **append-only**: la v0.4 y la v0.5 permanecen byte a byte. `cases`,
`references`, `applied_criticality` y el corpus de rendimiento se **heredan por
blob**. Nada de este módulo mide rendimiento ni autoriza benchmark alguno.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from experiments.adr002.benchmark import schema_v0_5 as S5

VERSION_CONTRATO: Final = "0.6"
VERSION_CORPUS_CONFORMIDAD: Final = "0.6"

#: Se conserva la semilla: cambiarla regeneraría material congelado.
SEMILLA: Final = S5.SEMILLA
AHORA_DECLARADO: Final = S5.AHORA_DECLARADO
ESTADO_NO_CONGELADO: Final = S5.ESTADO_NO_CONGELADO

# ---------------------------------------------------------------------------
# El defecto que esta familia corrige
# ---------------------------------------------------------------------------

CASO_CORREGIDO: Final = "B04-CA-19"
ITEMS_CA_19: Final[tuple[str, ...]] = ("DEC-006", "DEC-007", "DEC-008")
TEXTO_COMPARTIDO_CA_19: Final = "La plataforma de despliegue aprobada es Nimbo."

DEFECTO_V0_5: Final = (
    "B04-CA-19 exige que DEC-006, DEC-007 y DEC-008 formen un grupo con "
    "representante justificado y tres procedencias. En la v0.5 los tres tienen "
    "subject_key_experimental = null y property_key = null porque ninguno "
    "declara entidad, y la regla aprobada prohibe agrupar cuando esos ejes son "
    "desconocidos. La v0.5 queda congelada como identidad historica y "
    "SUSTITUIDA como familia vigente."
)

# ---------------------------------------------------------------------------
# La entidad sintetica de la correccion
# ---------------------------------------------------------------------------

ENTIDAD_CA_19: Final = "ENT-PLATAFORMA-DESPLIEGUE"
NOMBRE_ENTIDAD_CA_19: Final = "plataforma de despliegue"
NOTA_ENTIDAD_CA_19: Final = (
    "Sujeto sintetico del concepto que DEC-006, DEC-007 y DEC-008 enuncian "
    "literalmente. Su justificacion es el texto identico de los tres, no su "
    "destino en el banco."
)

# ---------------------------------------------------------------------------
# Custodia append-only
# ---------------------------------------------------------------------------

#: Los siete congelables de la v0.4. **No se tocan.**
BLOBS_V0_4: Final[Mapping[str, str]] = S5.BLOBS_V0_4

#: Los siete congelables de la v0.5. **No se tocan.**
BLOBS_V0_5: Final[Mapping[str, str]] = {
    "conformance_corpus_v0_5.json": "324f2976f8d4f4aec1d7634a1e16dcc9782c53b0",
    "subject_keys_v0_1.json": "020c10ced48657f57e7fa85076992c6f950dd0fe",
    "property_keys_v0_1.json": "da8953d58a5c17bed7df83e80c5ba3a6b2a27e3f",
    "applied_criticality_v0_1.json": "7dcbba0031e76d4f0763e0d0b853e59584fe3077",
    "cases_v0_5.json": "26919e1016c414697664f93455258cb6492ca48c",
    "references_v0_5.json": "4694ef3bba3a87cae0412895da992ce5e2b54f45",
    "benchmark_manifest_v0_5.json": "d9f97a8153b65f0cedcfc242304fea24570599dd",
}

#: Lo que la v0.6 **hereda por blob**, sin regenerar ni un byte.
HEREDADOS_V0_6: Final[Mapping[str, str]] = {
    "cases_v0_5.json": BLOBS_V0_5["cases_v0_5.json"],
    "references_v0_5.json": BLOBS_V0_5["references_v0_5.json"],
    "applied_criticality_v0_1.json": BLOBS_V0_5["applied_criticality_v0_1.json"],
    "pdp_cases_v0_3.json": BLOBS_V0_4["pdp_cases_v0_3.json"],
    "pdp_harness_rules_v0_2.json": BLOBS_V0_4["pdp_harness_rules_v0_2.json"],
    "performance_corpus_v0_2.json": BLOBS_V0_4["performance_corpus_v0_2.json"],
}

#: Lo unico que esta familia versiona. Nada mas.
CONGELABLES_V0_6: Final[tuple[str, ...]] = (
    "conformance_corpus_v0_6.json",
    "subject_keys_v0_2.json",
    "property_keys_v0_2.json",
    "benchmark_manifest_v0_6.json",
)

ORDEN_DE_MATERIALIZACION: Final[tuple[str, ...]] = CONGELABLES_V0_6

#: La proyeccion T0 sigue sin regenerarse, por el mismo motivo que en la v0.5.
PROYECCION_T0_NO_REGENERADA: Final = S5.PROYECCION_T0_NO_REGENERADA
PROYECCION_T0_BLOB_OBSERVADO: Final = S5.PROYECCION_T0_BLOB_OBSERVADO
PROYECCION_T0_MOTIVO: Final = S5.PROYECCION_T0_MOTIVO

# ---------------------------------------------------------------------------
# Reutilizado sin cambio de la v0.5 · la regla aprobada NO se toca
# ---------------------------------------------------------------------------

RX_SUBJECT_KEY: Final = S5.RX_SUBJECT_KEY
RX_PROPERTY_KEY: Final = S5.RX_PROPERTY_KEY
VERSION_VOCABULARIO_SUBJECT_KEY: Final = S5.VERSION_VOCABULARIO_SUBJECT_KEY
VERSION_VOCABULARIO_PROPERTY_KEY: Final = S5.VERSION_VOCABULARIO_PROPERTY_KEY
FUENTE_DE_ASIGNACION_SUBJECT_KEY: Final = S5.FUENTE_DE_ASIGNACION_SUBJECT_KEY
FUENTE_DE_ASIGNACION_PROPERTY_KEY: Final = S5.FUENTE_DE_ASIGNACION_PROPERTY_KEY
REGLA_DE_VALIDACION_SUBJECT_KEY: Final = S5.REGLA_DE_VALIDACION_SUBJECT_KEY
REGLA_DE_VALIDACION_PROPERTY_KEY: Final = S5.REGLA_DE_VALIDACION_PROPERTY_KEY
LIMITACION_PROPERTY_KEY: Final = S5.LIMITACION_PROPERTY_KEY

ITEM_ORIGEN_DELTA: Final = S5.ITEM_ORIGEN_DELTA
ITEM_DESTINO_DELTA: Final = S5.ITEM_DESTINO_DELTA
RELACION_DELTA: Final = S5.RELACION_DELTA
TIPO_RELACION_DELTA: Final = S5.TIPO_RELACION_DELTA
PROYECTO_DELTA: Final = S5.PROYECTO_DELTA
CONSULTA_DELTA: Final = S5.CONSULTA_DELTA

DOMINIOS_RECALCULADOS: Final = S5.DOMINIOS_RECALCULADOS


class ContratoFamiliaV06Error(AssertionError):
    """Violación del contrato de la familia sucesora de conformidad v0.6."""


__all__ = [
    "BLOBS_V0_4",
    "BLOBS_V0_5",
    "CASO_CORREGIDO",
    "CONGELABLES_V0_6",
    "DEFECTO_V0_5",
    "DOMINIOS_RECALCULADOS",
    "ENTIDAD_CA_19",
    "HEREDADOS_V0_6",
    "ITEMS_CA_19",
    "NOMBRE_ENTIDAD_CA_19",
    "ORDEN_DE_MATERIALIZACION",
    "TEXTO_COMPARTIDO_CA_19",
    "VERSION_CONTRATO",
    "ContratoFamiliaV06Error",
]
