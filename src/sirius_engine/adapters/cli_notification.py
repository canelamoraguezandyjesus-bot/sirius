"""Adapter v0 de notificación: imprime la escalada por la sesión/CLI activa.

Satisface :class:`~sirius_engine.ports.notification.NotificationPort`. No
posee ningún estado durable propio (interfaz v0: "sesión/CLI, sin estado
propio", objetivo 5 de la incidencia #206): cada notificación se entrega
inmediatamente vía ``escritor`` (por defecto, ``print``) y, además, se
conserva en ``entregadas`` únicamente para que la propia sesión pueda
mostrar un resumen del turno -no es un histórico durable ni sobrevive a la
sesión.
"""

from __future__ import annotations

from collections.abc import Callable

from sirius_engine.domain.escalation import Escalada


def _formatear(escalada: Escalada) -> str:
    return (
        f"[NEEDS_DECISION] {escalada.work_id} — causa: {escalada.causa.value} — "
        f"{escalada.motivo}\n"
        f"  objetivo: {escalada.objetivo}\n"
        f"  entregable: {escalada.entregable}\n"
        f"  petición original: {escalada.peticion_original}"
    )


class NotificadorCLI:
    """Notificador v0: escribe cada escalada por la salida de la sesión."""

    def __init__(self, *, escritor: Callable[[str], None] = print) -> None:
        self._escritor = escritor
        self.entregadas: list[Escalada] = []

    def notificar(self, escalada: Escalada) -> None:
        self._escritor(_formatear(escalada))
        self.entregadas.append(escalada)
