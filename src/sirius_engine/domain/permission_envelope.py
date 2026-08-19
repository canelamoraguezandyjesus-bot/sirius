"""PermissionEnvelope: perfil de permisos EFECTIVO de un Run (arquitectura §5.1, §6.1).

Lo calcula el motor a partir del :class:`~sirius_engine.domain.profile.AgentProfile`
mediante :func:`compute_permission_envelope` -la única función pública de
este módulo que produce un ``PermissionEnvelope`` no vacío. Ningún camino de
este módulo acepta un envelope "declarado" desde fuera del motor: no hay
ningún parámetro que permita a un Worker construirse el suyo (incidencia
#202, requisito "el PermissionEnvelope lo calcula el motor... nunca
declarado por el Worker").
"""

from __future__ import annotations

from dataclasses import dataclass

from sirius_engine.domain.errors import EgressIncompatibleError
from sirius_engine.domain.profile import AgentProfile


@dataclass(frozen=True, slots=True)
class PermissionEnvelope:
    """Deny-by-default: solo lo que estos campos conceden existe para el Run."""

    capacidades_concedidas: frozenset[str]
    escritura: str | None
    red: bool


#: El punto de partida deny-by-default (§5.1): no concede nada.
ENVELOPE_VACIO = PermissionEnvelope(capacidades_concedidas=frozenset(), escritura=None, red=False)


def compute_permission_envelope(profile: AgentProfile) -> PermissionEnvelope:
    """Calcular el envelope efectivo de un perfil.

    Deny-by-default: concede exactamente las capacidades que el perfil
    declara, ni una más -no hay concesión implícita alguna. Fail-closed ante
    la incompatibilidad estructural de §6.1 regla 1 -red externa y escritura
    irrestricta a la vez-: se lanza antes de conceder nada, nunca se degrada
    a "solo lectura" o "solo red".
    """
    if profile.permisos.red and profile.permisos.escritura is not None:
        raise EgressIncompatibleError(profile.ref)
    return PermissionEnvelope(
        capacidades_concedidas=frozenset(profile.capacidades),
        escritura=profile.permisos.escritura,
        red=profile.permisos.red,
    )
