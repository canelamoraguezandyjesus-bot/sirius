"""Capability Resolver v0 (arquitectura §6).

Resuelve capacidades abstractas contra el registro versionado y el
``PermissionEnvelope`` efectivo, con dos guardas independientes y sin
degradación en ninguna de las dos:

1. Capacidad no registrada -> :class:`~sirius_engine.domain.errors.UnknownCapabilityError`
   (nunca un proveedor por defecto ni la capacidad más parecida).
2. Capacidad registrada pero no concedida por el envelope ->
   :class:`~sirius_engine.domain.errors.CapabilityNotGrantedError` (nunca
   una versión recortada de la capacidad, nunca sustituida por otra).
"""

from __future__ import annotations

from dataclasses import dataclass

from sirius_engine.capability_registry import CapabilityRegistry
from sirius_engine.domain.errors import CapabilityNotGrantedError, UnknownCapabilityError
from sirius_engine.domain.permission_envelope import PermissionEnvelope


@dataclass(frozen=True, slots=True)
class ResolvedCapability:
    """Una capacidad ya resuelta: qué se pidió y con qué categoría de proveedor se satisfizo."""

    nombre: str
    proveedor: str


def resolve_capabilities(
    *,
    solicitadas: tuple[str, ...],
    envelope: PermissionEnvelope,
    registro: CapabilityRegistry,
) -> tuple[ResolvedCapability, ...]:
    """Resolver, en el orden solicitado, cada capacidad contra registro y envelope.

    Determinista: misma tupla de entrada + mismo envelope + mismo registro ->
    misma tupla de salida, en el mismo orden (no se reordena por ningún
    criterio interno).
    """
    resueltas: list[ResolvedCapability] = []
    for nombre in solicitadas:
        definicion = registro.obtener(nombre)
        if definicion is None:
            raise UnknownCapabilityError(nombre)
        if nombre not in envelope.capacidades_concedidas:
            raise CapabilityNotGrantedError(nombre)
        resueltas.append(ResolvedCapability(nombre=nombre, proveedor=definicion.proveedor))
    return tuple(resueltas)
