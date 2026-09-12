"""Autoridad por clase de trabajo (contrato operativo v1.7 §11, ADR-041).

Regla única del contrato: **la autoridad es una función total por clase de
trabajo**; ningún WorkItem puede nacer sin autoridad asignada. Este módulo
implementa esa función total sobre :class:`WorkItemClass`, para que "un
WorkItem nace siempre con autoridad asignada" (requisito de la incidencia
#206) sea una propiedad comprobable en vez de una promesa.

La regla de la tabla §11.1 es una sola pregunta: **¿existe la clase en la vía
GitHub?** Si sí, la incidencia es la fuente de verdad hasta que conmute; si
no, el almacén del motor lo es desde el nacimiento. **Desde ADR-177 la tabla
se deriva de esa pregunta** (:data:`CLASES_CON_VIA_GITHUB`) en vez de
escribirse aparte. Hasta entonces era una copia a mano de agosto (ADR-041)
que decía ``MOTOR`` para documentación e investigación -«A5 nunca publica
nada en GitHub»- mientras ADR-088 y ADR-099 metían esas dos clases en la
vía GitHub del despachador sin tocarla: quince encargos reales corrieron
enteros en GitHub con autoridad «motor», y el contador de los siete días no
midió nunca ninguno. Dos listas para el mismo hecho acaban divergiendo; la
única forma de que no diverjan es que sea una, y que ``TABLA_ACTIVACION``
esté atada a ella por una prueba.

Interpretación de las dos clases sin fila explícita en la tabla del contrato
(``consulta-larga``, ``mixta``): ambas se resuelven a ``MOTOR`` porque ninguna
tiene vía GitHub definida en ningún documento aprobado. Es la lectura
conservadora que completa un patrón ya aprobado, no una fila nueva inventada
(ADR-043). Y «documental no publicada», que el contrato lista con autoridad
``motor``, no tiene clase en el motor: toda la documentación que el motor
despacha va por la vía GitHub (ADR-088), así que ``DOCUMENTACION`` es la fila
«documental publicada (PR en el repo)».

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


#: Las clases que existen en la vía GitHub: la columna «¿Existe en la vía
#: GitHub?» de la tabla §11.1 del contrato, y la ÚNICA definición de ese
#: hecho en el código (ADR-177). ``TABLA_ACTIVACION`` -el despachador- tiene
#: que tener exactamente estas claves, y ``tests/engine/test_authority.py``
#: falla si las dos divergen; la autoridad de abajo se deriva de aquí.
CLASES_CON_VIA_GITHUB: frozenset[WorkItemClass] = frozenset(
    {
        WorkItemClass.PROGRAMACION,
        WorkItemClass.AUDITORIA,
        WorkItemClass.DOCUMENTACION,
        WorkItemClass.INVESTIGACION,
    }
)

#: Y las nativas del motor, declaradas también a propósito: la tabla se
#: construye SOLO con lo declarado en una de las dos, así que una clase nueva
#: que no se declare en ninguna sigue reventando con ``KeyError`` (ADR-041) en
#: vez de recibir una autoridad por defecto en silencio.
CLASES_SIN_VIA_GITHUB: frozenset[WorkItemClass] = frozenset(
    {
        WorkItemClass.CONVERSACION_NO_APLICA,
        WorkItemClass.CONSULTA_LARGA,
        WorkItemClass.MIXTA,
    }
)

#: La función total de §11.1, DERIVADA de las dos declaraciones de arriba.
_TABLA_AUTORIDAD: Mapping[WorkItemClass, Autoridad] = {
    **dict.fromkeys(CLASES_CON_VIA_GITHUB, Autoridad.INCIDENCIA),
    **dict.fromkeys(CLASES_SIN_VIA_GITHUB, Autoridad.MOTOR),
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
