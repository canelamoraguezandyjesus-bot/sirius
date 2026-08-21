"""Escalado al propietario: la lista cerrada de siete causas (arquitectura §10).

``NEEDS_DECISION`` se dispara ÚNICAMENTE por una de las siete causas de
:class:`CausaEscalado`, y por ninguna otra (#172 §2.7, arquitectura §10). Los
fallos técnicos corregibles (reintento, sustitución de Worker, o
``FAILED_SAFELY`` con diagnóstico) NUNCA construyen una :class:`Escalada`:
no hay ninguna función en este módulo que produzca una sin una causa
explícita de la lista cerrada.

Cada :class:`Escalada` lleva la instantánea completa del WorkItem que la
origina, para que "toda escalada llega con contexto suficiente para decidir
sin reconstruir nada" (requisito de la incidencia #206) sea una propiedad
verificable en vez de una promesa de prosa.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sirius_engine.domain.work_item import WorkItem


class CausaEscalado(StrEnum):
    """Las siete causas de arquitectura §10, y ninguna más.

    El orden y el texto siguen la enumeración de la arquitectura al pie de
    la letra, para que una lectura de esa sección y una lectura de este
    enum encuentren la misma lista.
    """

    #: 1. decisión de producto o arquitectura no resuelta (incluye
    #: DECISION_REQUIRED del revisor y BLOCKED_BY_DECISION del Worker).
    DECISION_PRODUCTO_O_ARQUITECTURA = "decision_producto_o_arquitectura"
    #: 2. gasto nuevo o cambio de presupuesto (incluye agotar el
    #: presupuesto del WorkItem).
    GASTO_O_PRESUPUESTO = "gasto_o_presupuesto"
    #: 3. permisos o credenciales sensibles.
    PERMISOS_O_CREDENCIALES_SENSIBLES = "permisos_o_credenciales_sensibles"
    #: 4. operación destructiva o difícilmente reversible.
    OPERACION_DESTRUCTIVA_O_IRREVERSIBLE = "operacion_destructiva_o_irreversible"
    #: 5. privacidad o salida de información sensible (incluye cualquier
    #: excepción al ExportSafeBrief).
    PRIVACIDAD_O_INFORMACION_SENSIBLE = "privacidad_o_informacion_sensible"
    #: 6. alternativas razonables con consecuencias materialmente distintas.
    ALTERNATIVAS_MATERIALMENTE_DISTINTAS = "alternativas_materialmente_distintas"
    #: 7. ausencia real de convergencia tras intentos razonables.
    AUSENCIA_DE_CONVERGENCIA = "ausencia_de_convergencia"


@dataclass(frozen=True, slots=True)
class Escalada:
    """Contexto completo de una escalada: nada que reconstruir aparte de esto."""

    work_id: str
    causa: CausaEscalado
    motivo: str
    peticion_original: str
    objetivo: str
    entregable: str
    criterio_terminado: str
    limites: Mapping[str, object]
    contexto_origen: tuple[str, ...]
    referencias: tuple[str, ...]
    ocurrida_en: datetime


def construir_escalada(
    work_item: WorkItem,
    *,
    causa: CausaEscalado,
    motivo: str,
    ocurrida_en: datetime,
    referencias: tuple[str, ...] = (),
) -> Escalada:
    """Construir la ``Escalada`` de un WorkItem, copiando su instantánea completa.

    Deliberadamente NO acepta ningún campo de contexto "resumido a mano":
    cada campo se copia del propio ``WorkItem``, así que no hay ninguna vía
    por la que la escalada pueda decir menos de lo que el WorkItem sabe.
    """
    return Escalada(
        work_id=work_item.work_id,
        causa=causa,
        motivo=motivo,
        peticion_original=work_item.peticion_original,
        objetivo=work_item.objetivo,
        entregable=work_item.entregable,
        criterio_terminado=work_item.criterio_terminado,
        limites=work_item.limites,
        contexto_origen=work_item.contexto_origen,
        referencias=referencias,
        ocurrida_en=ocurrida_en,
    )
