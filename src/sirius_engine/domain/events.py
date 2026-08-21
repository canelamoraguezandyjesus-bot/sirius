"""Diario de eventos append-only (arquitectura §3.5, §12).

Cada transición del motor queda registrada como un :class:`Event` inmutable
que lleva la instantánea resultante del agregado (``WorkItem`` o ``Run``).
:func:`rebuild_state` reproduce el diario desde cero y reconstruye
exactamente el mismo estado que produjo el puerto de persistencia en vivo —
sin volver a ejecutar ninguna transición, solo plegando eventos en orden.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal

from sirius_engine.domain.run import Run
from sirius_engine.domain.work_item import WorkItem


class AggregateType(StrEnum):
    """Qué tipo de agregado describe un :class:`Event`."""

    WORK_ITEM = "work_item"
    RUN = "run"


@dataclass(frozen=True, slots=True)
class Event:
    """Un asiento del diario: una transición y la instantánea que produjo.

    ``sequence`` es la posición de escritura, asignada por el puerto de
    persistencia al hacer ``append`` — nunca reordenada ni reescrita.
    """

    sequence: int
    occurred_at: datetime
    aggregate_type: AggregateType
    aggregate_id: str
    kind: str
    entity: WorkItem | Run


@dataclass(frozen=True, slots=True)
class RebuiltState:
    """Resultado de reproducir el diario: versiones de WorkItem y Runs por id."""

    work_item_versions: Mapping[str, tuple[WorkItem, ...]]
    runs: Mapping[str, Run]

    def latest_work_item(self, work_id: str) -> WorkItem | None:
        """Última versión conocida del WorkItem, o ``None`` si nunca apareció en el diario."""
        versions = self.work_item_versions.get(work_id)
        return versions[-1] if versions else None


def rebuild_state(events: Sequence[Event]) -> RebuiltState:
    """Reconstruir el estado plegando el diario en orden de ``sequence``.

    Determinista: la misma secuencia de eventos produce siempre el mismo
    resultado, sin importar el orden en que ``events`` se haya recibido.

    ``work_item_versions`` conserva **una entrada por revisión de alcance**
    (``WorkItem.version``, arquitectura §3.2): eventos que comparten versión
    —cambios de estado, repriorizaciones— actualizan la instantánea de esa
    versión en vez de añadir una copia nueva, así un consumidor puede
    indexar revisiones de alcance de forma fiable. Ningún evento del diario
    se descarta por esto: todos siguen presentes en ``events``.
    """
    work_item_versions: dict[str, dict[int, WorkItem]] = {}
    runs: dict[str, Run] = {}
    for event in sorted(events, key=lambda e: e.sequence):
        if event.aggregate_type is AggregateType.WORK_ITEM:
            assert isinstance(event.entity, WorkItem)
            by_version = work_item_versions.setdefault(event.aggregate_id, {})
            by_version[event.entity.version] = event.entity
        else:
            assert isinstance(event.entity, Run)
            runs[event.aggregate_id] = event.entity
    return RebuiltState(
        work_item_versions={
            work_id: tuple(by_version.values())
            for work_id, by_version in work_item_versions.items()
        },
        runs=dict(runs),
    )


EventKind = Literal[
    "work_item_created",
    "work_item_created_needing_decision",
    "work_item_activated",
    "work_item_cancelled",
    "work_item_escalated",
    "work_item_decision_resolved",
    "work_item_dispatched_async",
    "work_item_observed_external_fact",
    "work_item_failed_safely",
    "work_item_reactivated",
    "work_item_delivered",
    "work_item_paused",
    "work_item_resumed",
    "work_item_scope_changed",
    "work_item_reprioritized",
    "work_item_execution_started",
    "work_item_check_started",
    "work_item_review_started",
    "work_item_review_approved",
    "work_item_repair_requested",
    "work_item_repair_resumed",
    "work_item_budget_cutoff_started",
    "work_item_budget_cutoff_stopped_waiting",
    "run_prepared",
    "run_dispatched",
    "run_confirmed_running",
    "run_observed",
    "run_succeeded",
    "run_failed",
    "run_marked_lost",
    "run_prepared_invalidated",
    "run_scope_invalidated",
    "run_cancellation_requested",
    "run_cancellation_confirmed",
    "run_retried",
    "run_worker_substituted",
]
