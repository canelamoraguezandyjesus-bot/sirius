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
"""

from __future__ import annotations

from collections.abc import Mapping
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


def autoridad_de_clase(clase: WorkItemClass) -> Autoridad:
    """Función total: toda clase de ``WorkItemClass`` tiene autoridad asignada.

    No hay valor por defecto ni degradación: si ``WorkItemClass`` ganara un
    miembro nuevo sin actualizar ``_TABLA_AUTORIDAD``, esto falla explícito
    (``KeyError``) en vez de asumir en silencio una autoridad para una clase
    que el contrato nunca fijó.
    """
    return _TABLA_AUTORIDAD[clase]
