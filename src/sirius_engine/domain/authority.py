"""Autoridad por clase de trabajo (contrato operativo v1.7 §11, ADR-041).

Regla única del contrato: **la autoridad es una función total por clase de
trabajo**; ningún WorkItem puede nacer sin autoridad asignada. Este módulo
implementa esa función total sobre :class:`WorkItemClass`, para que "un
WorkItem nace siempre con autoridad asignada" (requisito de la incidencia
#206) sea una propiedad comprobable en vez de una promesa.

Interpretación de las dos clases sin fila explícita en la tabla del
contrato (``consulta-larga``, ``mixta``): ambas se resuelven a ``MOTOR`` por
el mismo criterio que la tabla aplica al resto de clases sin proyección en
GitHub (investigación, documental no publicada) — ninguna tiene una
proyección GitHub definida en ningún documento aprobado. Es la lectura
conservadora que completa un patrón ya aprobado, no una fila nueva
inventada (ADR-043).

``WorkItemClass.DOCUMENTACION`` se resuelve a ``MOTOR`` porque A5 nunca
publica nada en GitHub (fuera de alcance de esta incidencia): la única
variante de "documentación" que A5 puede producir es la no publicada. La
distinción con "documental publicada (PR en el repo)" -autoridad
``incidencia``- es trabajo de C3, que sí escribe en GitHub.

**D1c (incidencia #276, contrato §11.3) añade el segundo término de la
función total**: la autoridad de una clase ya no es solo la tabla estática
de arriba -fija desde la v1.7, ADR-041- sino *esa tabla más lo que diga un
registro fechado de conmutaciones*, tal y como fija el contrato: "registro
fechado como dato versionado en el repositorio". :class:`EntradaConmutacion`
es la línea de ese registro; :func:`autoridad_de_clase` la consulta cuando
se le pasa. La propiedad que ADR-041 fijó a propósito sobrevive intacta: sin
``registro`` (o con uno vacío para la clase pedida), el resultado es
exactamente el de antes -ningún llamador existente, todos en modo solo
lectura y sin registro, cambia de comportamiento-, y una clase ausente de
``_TABLA_AUTORIDAD`` sigue reventando con ``KeyError`` en vez de asumir nada.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sirius_engine.domain.work_item import WorkItemClass


class Autoridad(StrEnum):
    """Quién es la fuente de verdad de un WorkItem (contrato §11)."""

    #: El almacén del motor es la fuente de verdad desde el nacimiento.
    MOTOR = "motor"
    #: La incidencia de GitHub es la fuente de verdad hasta su conmutación
    #: (contrato §11.2-§11.3); el motor mantiene un espejo no autoritativo.
    INCIDENCIA = "incidencia"


#: Tabla de autoridad al entrar en vigor la v1.7 (contrato §11.1, ADR-041).
#: Función total sobre TODO ``WorkItemClass``: sin huecos.
_TABLA_AUTORIDAD: Mapping[WorkItemClass, Autoridad] = {
    WorkItemClass.CONVERSACION_NO_APLICA: Autoridad.MOTOR,
    WorkItemClass.INVESTIGACION: Autoridad.MOTOR,
    WorkItemClass.DOCUMENTACION: Autoridad.MOTOR,
    WorkItemClass.PROGRAMACION: Autoridad.INCIDENCIA,
    WorkItemClass.AUDITORIA: Autoridad.INCIDENCIA,
    WorkItemClass.CONSULTA_LARGA: Autoridad.MOTOR,
    WorkItemClass.MIXTA: Autoridad.MOTOR,
}


#: Las únicas clases que pueden aparecer en un registro de conmutaciones: las
#: que la tabla estática nace con autoridad ``INCIDENCIA`` (§11.1) -las
#: únicas con proyección en la vía GitHub y, por tanto, las únicas que tienen
#: algo que conmutar en cualquier dirección. Derivada de la tabla, no una
#: segunda lista a mantener a mano.
_CLASES_CONMUTABLES: frozenset[WorkItemClass] = frozenset(
    clase for clase, autoridad in _TABLA_AUTORIDAD.items() if autoridad is Autoridad.INCIDENCIA
)


@dataclass(frozen=True, slots=True)
class EntradaConmutacion:
    """Una conmutación fechada de la autoridad de una clase (contrato §11.3).

    ``autoridad`` es la que rige DESDE ``instante`` en adelante -hacia
    ``MOTOR`` al conmutar hacia delante (§11.2/§11.3, otro bloque), hacia
    ``INCIDENCIA`` al revertir (§11.4, D1c). Este tipo admite las dos
    direcciones a propósito: el registro debe poder representar ambas aunque
    D1c solo escriba la segunda.

    Solo una clase nacida con autoridad ``INCIDENCIA`` en la tabla estática
    puede aparecer aquí: una clase ``MOTOR`` -nativa del motor, nunca tuvo
    proyección en GitHub (§11.1)- no tiene nada que conmutar, y admitir una
    entrada suya sería aceptar en silencio un estado que el contrato no
    contempla.
    """

    instante: datetime
    clase: WorkItemClass
    autoridad: Autoridad
    motivo: str

    def __post_init__(self) -> None:
        if self.clase not in _CLASES_CONMUTABLES:
            raise ValueError(
                f"{self.clase.value}: nace con autoridad "
                f"{_TABLA_AUTORIDAD[self.clase].value} y no conmuta (contrato §11.1); no puede "
                "tener una entrada en el registro de conmutaciones"
            )


def autoridad_de_clase(
    clase: WorkItemClass, *, registro: Sequence[EntradaConmutacion] = ()
) -> Autoridad:
    """Función total: toda clase de ``WorkItemClass`` tiene autoridad asignada.

    No hay valor por defecto ni degradación: si ``WorkItemClass`` ganara un
    miembro nuevo sin actualizar ``_TABLA_AUTORIDAD``, esto falla explícito
    (``KeyError``) en vez de asumir en silencio una autoridad para una clase
    que el contrato nunca fijó -esa comprobación ocurre siempre, con o sin
    ``registro``.

    ``registro`` es el segundo término de la función (D1c, contrato §11.3):
    sin entradas para ``clase``, manda la tabla estática, igual que siempre.
    Con entradas, manda la más reciente por ``instante`` -un registro que
    solo crece y nunca reordena lo anterior, así que "la más reciente" es
    siempre la vigente. Si dos entradas comparten ``instante`` -reversión y
    conmutación anterior con el mismo segundo, por ejemplo-, el desempate es
    la posición en ``registro``: gana la añadida después, nunca la primera
    que ``max`` encuentre, porque el registro append-only ya codifica ese
    orden y es la única fuente de verdad sobre "qué pasó después" cuando el
    reloj no distingue (CODEX-001).
    """
    vigente = _TABLA_AUTORIDAD[clase]
    entradas_de_clase = [entrada for entrada in registro if entrada.clase is clase]
    if entradas_de_clase:
        vigente = max(
            enumerate(entradas_de_clase),
            key=lambda indexada: (indexada[1].instante, indexada[0]),
        )[1].autoridad
    return vigente


def formatear_entrada_conmutacion(entrada: EntradaConmutacion) -> str:
    """Serializa una entrada del registro de conmutaciones a JSON determinista.

    Mismo criterio que ``projection_verifier.formatear_linea``: misma
    entrada, mismo texto exacto -condición del registro append-only
    (requisito 8 de la incidencia #276).
    """
    return json.dumps(
        {
            "instante": entrada.instante.isoformat(),
            "clase": entrada.clase.value,
            "autoridad": entrada.autoridad.value,
            "motivo": entrada.motivo,
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def parsear_entrada_conmutacion(texto: str) -> EntradaConmutacion:
    """Inversa de :func:`formatear_entrada_conmutacion`."""
    datos: dict[str, str] = json.loads(texto)
    return EntradaConmutacion(
        instante=datetime.fromisoformat(datos["instante"]),
        clase=WorkItemClass(datos["clase"]),
        autoridad=Autoridad(datos["autoridad"]),
        motivo=datos["motivo"],
    )
