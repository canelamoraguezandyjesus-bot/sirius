"""Dar a Sirius la semilla del robot (pieza B de ADR-233)."""

from __future__ import annotations

from sirius.domain.robot_seed import (
    ROBOT_SEED_DESCRIPTION,
    ROBOT_SEED_INSTRUCTIONS,
    ROBOT_SEED_NAME,
)
from sirius.ports.identity_repository import IdentityRepository

__all__ = ["adopt_robot_seed"]


def adopt_robot_seed(identity_repository: IdentityRepository) -> bool:
    """Guarda la semilla del robot como versión nueva de la identidad si todavía no está.

    No borra nada: las versiones anteriores siguen en la historia. Si alguna
    versión ya tiene exactamente este texto, no hace nada aunque la vigente sea
    otra: así un cambio posterior del propietario no se pisa en cada arranque, y
    una semilla nueva, aprobada en otra PR, sí entra. Devuelve si creó versión.
    """
    identity_repository.get_or_create_current_identity()
    if any(
        version.personality_instructions == ROBOT_SEED_INSTRUCTIONS
        for version in identity_repository.get_history()
    ):
        return False
    identity_repository.create_new_version(
        ROBOT_SEED_NAME, ROBOT_SEED_DESCRIPTION, ROBOT_SEED_INSTRUCTIONS
    )
    return True
