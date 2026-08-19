"""Una intención ya clasificada: la forma que consume la puerta determinista.

Arquitectura §11 separa dos cosas: **interpretar** intención y estructurar un
borrador necesita modelo [M]; la **puerta** que decide qué hacer con esa
intención ya clasificada es determinista [D] (arquitectura §8.5). Este módulo
define la frontera exacta entre ambas: :class:`IntentSignal` es lo que
cualquier intérprete -la heurística v0 de :mod:`sirius_engine.intent_interpreter`
hoy, un intérprete con modelo real mañana- debe producir para que
:mod:`sirius_engine.gate` pueda decidir sin volver a interpretar nada.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from sirius_engine.domain.escalation import CausaEscalado
from sirius_engine.domain.work_item import WorkItemClass


class TipoIntencion(StrEnum):
    """Las categorías de arquitectura §8.5, más la distinción de la Capa 1 (#172 §6.1-6.3)."""

    #: Conversar: no crea WorkItem, no consulta el pasado.
    CONVERSAR = "conversar"
    #: «¿Qué pasó con X?»: no crea WorkItem, responde vía ``contexto.recuperar``.
    CONSULTAR_PASADO = "consultar_pasado"
    #: Explorar/debatir («quizá habría que…»): no crea WorkItem.
    EXPLORAR = "explorar"
    #: Ambigüedad: objetivo sin entregable discernible. No crea WorkItem.
    AMBIGUA = "ambigua"
    #: Orden explícita e inequívoca: crea Y activa, sin segunda confirmación.
    ORDEN_INEQUIVOCA = "orden_inequivoca"
    #: Acción sensible o material (§10): confirma o escala antes de activar.
    SENSIBLE_O_MATERIAL = "sensible_o_material"


#: Tipos que, si llegan sin datos de trabajo, son un error de construcción:
#: la puerta necesita objetivo/entregable/clase para poder crear algo.
_REQUIEREN_DATOS_TRABAJO = frozenset(
    {TipoIntencion.ORDEN_INEQUIVOCA, TipoIntencion.SENSIBLE_O_MATERIAL}
)


@dataclass(frozen=True, slots=True)
class DatosNuevoTrabajo:
    """Lo mínimo de arquitectura §3.1 para crear un WorkItem, ya normalizado."""

    objetivo: str
    entregable: str
    criterio_terminado: str
    clase: WorkItemClass
    limites: Mapping[str, object]
    contexto_origen: tuple[str, ...] = ()
    prioridad: int = 3
    plan: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "limites", MappingProxyType(dict(self.limites)))


@dataclass(frozen=True, slots=True)
class IntentSignal:
    """Una intención ya clasificada, lista para la puerta determinista."""

    tipo: TipoIntencion
    mensaje_original: str
    datos_trabajo: DatosNuevoTrabajo | None = None
    causa_sensibilidad: CausaEscalado | None = None
    motivo_sensibilidad: str | None = None
    pregunta_aclaratoria: str | None = None
    consulta: str | None = None

    def __post_init__(self) -> None:
        if self.tipo in _REQUIEREN_DATOS_TRABAJO and self.datos_trabajo is None:
            raise ValueError(f"IntentSignal de tipo {self.tipo!r} exige datos_trabajo")
        if self.tipo is TipoIntencion.SENSIBLE_O_MATERIAL and self.causa_sensibilidad is None:
            raise ValueError(
                "IntentSignal de tipo SENSIBLE_O_MATERIAL exige causa_sensibilidad "
                "(una de las siete causas cerradas de arquitectura §10)"
            )
        if self.tipo is TipoIntencion.CONSULTAR_PASADO and self.consulta is None:
            raise ValueError("IntentSignal de tipo CONSULTAR_PASADO exige consulta")
