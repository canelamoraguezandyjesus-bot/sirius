"""WorkerRequest: proyección determinista del encargo (arquitectura §5.1).

::

    WorkPackage + AgentProfileRef(version/hash) + CapabilityBindings
                + PermissionEnvelope + OutputSchema
                ──[proyección determinista]──> WorkerRequest

:func:`project_worker_request` es esa proyección: mismo ``WorkItem`` + mismo
perfil + mismo registro de capacidades + mismo contexto -> mismo
``WorkerRequest``, siempre (A4-P1). No depende del reloj, del orden de
ningún diccionario ni del entorno: todos sus insumos son inmutables
(dataclasses ``frozen``, tuplas, ``Mapping``) y la única lógica es
determinista de principio a fin.

El orden de las dos comprobaciones internas es fijo -egress antes que
resolución de capacidades- porque un Run que no puede exportar su contexto
no debe ni intentar resolver nada (fail-closed antes de ``START``, §6.1
regla 4): ninguna capacidad se resuelve, ni siquiera para descartarla, si el
contexto ya bloqueó el arranque.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sirius_engine.capability_registry import CapabilityRegistry
from sirius_engine.capability_resolver import ResolvedCapability, resolve_capabilities
from sirius_engine.domain.context_fragment import ContextFragment
from sirius_engine.domain.permission_envelope import (
    PermissionEnvelope,
    compute_permission_envelope,
)
from sirius_engine.domain.profile import AgentProfile
from sirius_engine.domain.work_item import WorkItem
from sirius_engine.egress import validar_egress_fail_closed


@dataclass(frozen=True, slots=True)
class WorkerRequest:
    """El encargo exacto que recibe un Worker para un paso de un WorkItem."""

    work_id: str
    perfil_ref: str
    perfil_version: int
    objetivo: str
    contexto: tuple[ContextFragment, ...]
    entregable: str
    criterio_terminado: str
    capacidades_resueltas: tuple[ResolvedCapability, ...]
    permisos: PermissionEnvelope
    limites: Mapping[str, object]


def project_worker_request(
    *,
    work_item: WorkItem,
    profile: AgentProfile,
    registro: CapabilityRegistry,
    contexto: tuple[ContextFragment, ...] = (),
) -> WorkerRequest:
    """Proyectar el ``WorkerRequest`` de un ``WorkItem`` bajo un perfil dado."""
    envelope = compute_permission_envelope(profile)
    validar_egress_fail_closed(fragmentos=contexto, red=envelope.red)
    capacidades_resueltas = resolve_capabilities(
        solicitadas=profile.capacidades, envelope=envelope, registro=registro
    )
    return WorkerRequest(
        work_id=work_item.work_id,
        perfil_ref=profile.ref,
        perfil_version=profile.version,
        objetivo=work_item.objetivo,
        contexto=contexto,
        entregable=work_item.entregable,
        criterio_terminado=work_item.criterio_terminado,
        capacidades_resueltas=capacidades_resueltas,
        permisos=envelope,
        limites=MappingProxyType(dict(work_item.limites)),
    )
