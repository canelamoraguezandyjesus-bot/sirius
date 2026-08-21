"""Puerto de notificación: cómo una escalada llega a la interfaz activa (arquitectura §10).

"Cada escalada llega por la interfaz activa con el contexto suficiente para
decidir sin reconstruir nada" (arquitectura §10). Este puerto es
deliberadamente el más pequeño posible: una sola operación, sin acuse de
recibo ni cola -Telegram (D3) y cualquier otra interfaz futura lo
implementan sin tocar el motor.
"""

from __future__ import annotations

from typing import Protocol

from sirius_engine.domain.escalation import Escalada


class NotificationPort(Protocol):
    """Satisfecho por cada adapter de interfaz (CLI v0, Telegram más adelante)."""

    def notificar(self, escalada: Escalada) -> None:
        """Entregar una escalada por la interfaz activa."""
        ...
