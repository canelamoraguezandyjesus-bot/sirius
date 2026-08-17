"""Almacén durable mínimo del puerto ``WorkEngineStore`` (ADR-026).

Implementa deliberadamente un SUBCONJUNTO del puerto -crear, activar,
cancelar y fallar a salvo un ``WorkItem``, más lectura- suficiente
para ejercitar el patrón de escritura seguro elegido: diario append-only con
``fsync``, checksum por registro y clave de idempotencia. No sustituye a
``InMemoryWorkEngineStore`` ni fija la representación definitiva del almacén
(eso depende de I3+I4, arquitectura §15, ADR-019; se fija en D2). Reutiliza
el dominio de A1 y ``rebuild_state`` sin reimplementarlos.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from experiments.work_engine_spike_i3.durable_journal import KillPoint, append_durably, replay
from experiments.work_engine_spike_i3.entity_codec import work_item_from_dict, work_item_to_dict
from sirius_engine.domain import work_item as work_item_ops
from sirius_engine.domain.errors import UnknownWorkItemError
from sirius_engine.domain.events import AggregateType, Event, rebuild_state
from sirius_engine.domain.work_item import WorkItem, WorkItemClass


class DurableJsonlWorkItemStore:
    """Satisface el subconjunto de ``WorkItem`` del puerto (ver docstring del módulo)."""

    def __init__(self, journal_path: Path) -> None:
        self._journal_path = journal_path

    # -- reproducción del diario --------------------------------------------------

    def _events(self) -> tuple[Event, ...]:
        events = []
        for record in replay(self._journal_path).valid_records:
            events.append(
                Event(
                    sequence=record["sequence"],
                    occurred_at=datetime.fromisoformat(record["occurred_at"]),
                    aggregate_type=AggregateType(record["aggregate_type"]),
                    aggregate_id=record["aggregate_id"],
                    kind=record["kind"],
                    entity=work_item_from_dict(record["entity"]),
                )
            )
        return tuple(events)

    def _idempotency_keys_seen(self) -> dict[str, WorkItem]:
        seen: dict[str, WorkItem] = {}
        for record in replay(self._journal_path).valid_records:
            key = record.get("idempotency_key")
            if key is not None and key not in seen:
                seen[key] = work_item_from_dict(record["entity"])
        return seen

    def _next_sequence(self) -> int:
        return max((event.sequence for event in self._events()), default=0) + 1

    def _require_work_item(self, work_id: str) -> WorkItem:
        current = self.get_work_item(work_id)
        if current is None:
            raise UnknownWorkItemError(work_id)
        return current

    def get_work_item(self, work_id: str) -> WorkItem | None:
        return rebuild_state(self._events()).latest_work_item(work_id)

    def list_work_item_versions(self, work_id: str) -> tuple[WorkItem, ...]:
        return rebuild_state(self._events()).work_item_versions.get(work_id, ())

    def list_events(self) -> tuple[Event, ...]:
        return self._events()

    # -- escritura durable ----------------------------------------------------------

    def _append(
        self,
        work_item: WorkItem,
        kind: str,
        *,
        now: datetime,
        idempotency_key: str | None,
        kill_at: KillPoint | None,
    ) -> WorkItem:
        """Anexar de forma durable, o devolver lo ya anexado si ``idempotency_key`` se repite.

        Requisito «sin duplicación al reproducir»: si el llamador reintenta la
        MISMA petición lógica (porque el intento anterior murió después de
        escribir pero antes de confirmar), este método no anexa un segundo
        evento -- devuelve el ``WorkItem`` que el intento anterior ya produjo.
        """
        if idempotency_key is not None:
            existing = self._idempotency_keys_seen().get(idempotency_key)
            if existing is not None:
                return existing
        record = {
            "sequence": self._next_sequence(),
            "occurred_at": now.isoformat(),
            "aggregate_type": AggregateType.WORK_ITEM.value,
            "aggregate_id": work_item.work_id,
            "kind": kind,
            "entity": work_item_to_dict(work_item),
            "idempotency_key": idempotency_key,
        }
        append_durably(self._journal_path, record, kill_at=kill_at)
        return work_item

    def create_work_item(
        self,
        *,
        work_id: str,
        peticion_original: str,
        objetivo: str,
        contexto_origen: tuple[str, ...],
        entregable: str,
        criterio_terminado: str,
        limites: Mapping[str, object],
        prioridad: int,
        clase: WorkItemClass,
        now: datetime,
        plan: tuple[str, ...] = (),
        idempotency_key: str | None = None,
        kill_at: KillPoint | None = None,
    ) -> WorkItem:
        work_item = work_item_ops.create_work_item(
            work_id=work_id,
            peticion_original=peticion_original,
            objetivo=objetivo,
            contexto_origen=contexto_origen,
            entregable=entregable,
            criterio_terminado=criterio_terminado,
            limites=limites,
            prioridad=prioridad,
            clase=clase,
            now=now,
            plan=plan,
        )
        return self._append(
            work_item,
            "work_item_created",
            now=now,
            idempotency_key=idempotency_key,
            kill_at=kill_at,
        )

    def activate_work_item(
        self,
        work_id: str,
        *,
        now: datetime,
        idempotency_key: str | None = None,
        kill_at: KillPoint | None = None,
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append(
            current.activate(now=now),
            "work_item_activated",
            now=now,
            idempotency_key=idempotency_key,
            kill_at=kill_at,
        )

    def cancel_work_item(
        self,
        work_id: str,
        *,
        now: datetime,
        idempotency_key: str | None = None,
        kill_at: KillPoint | None = None,
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append(
            current.cancel(now=now),
            "work_item_cancelled",
            now=now,
            idempotency_key=idempotency_key,
            kill_at=kill_at,
        )

    def fail_work_item_safely(
        self,
        work_id: str,
        *,
        diagnostico: str,
        now: datetime,
        idempotency_key: str | None = None,
        kill_at: KillPoint | None = None,
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append(
            current.fail_safely(diagnostico=diagnostico, now=now),
            "work_item_failed_safely",
            now=now,
            idempotency_key=idempotency_key,
            kill_at=kill_at,
        )
