"""Implementación en memoria del puerto de persistencia (incidencia #177, requisito 9).

Único almacén de A1: sin ficheros, sin red, sin reloj real. Cada operación
aplica la transición pura del dominio (:mod:`sirius_engine.domain.work_item`,
:mod:`sirius_engine.domain.run`) y, si tiene éxito, registra la instantánea
resultante en el diario append-only
(:mod:`sirius_engine.domain.events`) antes de devolverla — así el diario
siempre está al día con el estado en vivo, incluso si una llamada posterior
falla.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from sirius_engine.domain import run as run_ops
from sirius_engine.domain import work_item as work_item_ops
from sirius_engine.domain.errors import (
    DuplicateIdError,
    MutableResourceConflictError,
    UnknownRunError,
    UnknownWorkItemError,
)
from sirius_engine.domain.events import AggregateType, Event, EventKind
from sirius_engine.domain.run import Run
from sirius_engine.domain.work_item import WorkItem, WorkItemClass


class InMemoryWorkEngineStore:
    """Satisface :class:`sirius_engine.ports.store.WorkEngineStore`."""

    def __init__(self) -> None:
        self._work_items: dict[str, WorkItem] = {}
        self._runs: dict[str, Run] = {}
        self._events: list[Event] = []
        self._next_sequence = 1

    # -- diario -----------------------------------------------------------------

    def list_events(self) -> Sequence[Event]:
        return tuple(self._events)

    def _record_work_item(self, work_item: WorkItem, kind: EventKind, *, now: datetime) -> WorkItem:
        self._work_items[work_item.work_id] = work_item
        self._events.append(
            Event(
                sequence=self._next_sequence,
                occurred_at=now,
                aggregate_type=AggregateType.WORK_ITEM,
                aggregate_id=work_item.work_id,
                kind=kind,
                entity=work_item,
            )
        )
        self._next_sequence += 1
        return work_item

    def _record_run(self, run: Run, kind: EventKind, *, now: datetime) -> Run:
        self._runs[run.run_id] = run
        self._events.append(
            Event(
                sequence=self._next_sequence,
                occurred_at=now,
                aggregate_type=AggregateType.RUN,
                aggregate_id=run.run_id,
                kind=kind,
                entity=run,
            )
        )
        self._next_sequence += 1
        return run

    def _require_work_item(self, work_id: str) -> WorkItem:
        work_item = self._work_items.get(work_id)
        if work_item is None:
            raise UnknownWorkItemError(work_id)
        return work_item

    def _require_run(self, run_id: str) -> Run:
        run = self._runs.get(run_id)
        if run is None:
            raise UnknownRunError(run_id)
        return run

    # -- WorkItem -----------------------------------------------------------------

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
    ) -> WorkItem:
        if work_id in self._work_items:
            raise DuplicateIdError("WorkItem", work_id)
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
        return self._record_work_item(work_item, "work_item_created", now=now)

    def get_work_item(self, work_id: str) -> WorkItem | None:
        return self._work_items.get(work_id)

    def list_work_item_versions(self, work_id: str) -> Sequence[WorkItem]:
        return tuple(
            event.entity
            for event in self._events
            if isinstance(event.entity, WorkItem) and event.aggregate_id == work_id
        )

    def activate_work_item(self, work_id: str, *, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(current.activate(now=now), "work_item_activated", now=now)

    def cancel_work_item(self, work_id: str, *, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(current.cancel(now=now), "work_item_cancelled", now=now)

    def escalate_work_item(self, work_id: str, *, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(current.escalate(now=now), "work_item_escalated", now=now)

    def resolve_work_item_decision(
        self, work_id: str, *, continuar: bool, now: datetime
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(
            current.resolve_decision(continuar=continuar, now=now),
            "work_item_decision_resolved",
            now=now,
        )

    def dispatch_work_item_async(self, work_id: str, *, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(
            current.dispatch_async(now=now), "work_item_dispatched_async", now=now
        )

    def observe_work_item_external_fact(self, work_id: str, *, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(
            current.observe_external_fact(now=now),
            "work_item_observed_external_fact",
            now=now,
        )

    def fail_work_item_safely(self, work_id: str, *, diagnostico: str, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(
            current.fail_safely(diagnostico=diagnostico, now=now),
            "work_item_failed_safely",
            now=now,
        )

    def reactivate_work_item(self, work_id: str, *, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(current.reactivate(now=now), "work_item_reactivated", now=now)

    def deliver_work_item(
        self, work_id: str, *, resultado: Mapping[str, object], now: datetime
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(
            current.deliver(resultado=resultado, now=now), "work_item_delivered", now=now
        )

    def pause_work_item(self, work_id: str, *, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(current.pause(now=now), "work_item_paused", now=now)

    def resume_work_item(self, work_id: str, *, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(current.resume(now=now), "work_item_resumed", now=now)

    def change_work_item_scope(
        self,
        work_id: str,
        *,
        now: datetime,
        objetivo: str | None = None,
        entregable: str | None = None,
        criterio_terminado: str | None = None,
        limites: Mapping[str, object] | None = None,
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(
            current.change_scope(
                now=now,
                objetivo=objetivo,
                entregable=entregable,
                criterio_terminado=criterio_terminado,
                limites=limites,
            ),
            "work_item_scope_changed",
            now=now,
        )

    def reprioritize_work_item(self, work_id: str, *, prioridad: int, now: datetime) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._record_work_item(
            current.reprioritize(prioridad=prioridad, now=now),
            "work_item_reprioritized",
            now=now,
        )

    # -- Run --------------------------------------------------------------------

    def prepare_run(
        self,
        *,
        run_id: str,
        work_id: str,
        paso: str,
        worker: str,
        work_package: Mapping[str, object],
        deadline: datetime,
        now: datetime,
        recurso_mutable: str | None = None,
    ) -> Run:
        if run_id in self._runs:
            raise DuplicateIdError("Run", run_id)
        run = run_ops.prepare(
            run_id=run_id,
            work_id=work_id,
            paso=paso,
            worker=worker,
            work_package=work_package,
            intento=1,
            deadline=deadline,
            now=now,
            recurso_mutable=recurso_mutable,
        )
        return self._record_run(run, "run_prepared", now=now)

    def get_run(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    def list_runs_for_work_item(self, work_id: str) -> Sequence[Run]:
        return tuple(run for run in self._runs.values() if run.work_id == work_id)

    def _conflicting_unconfirmed_cancellation(self, run: Run) -> Run | None:
        if run.recurso_mutable is None:
            return None
        for other in self._runs.values():
            if other.run_id == run.run_id:
                continue
            if other.recurso_mutable != run.recurso_mutable:
                continue
            if other.has_unconfirmed_cancellation:
                return other
        return None

    def dispatch_run(self, run_id: str, *, now: datetime) -> Run:
        current = self._require_run(run_id)
        conflict = self._conflicting_unconfirmed_cancellation(current)
        if conflict is not None:
            assert current.recurso_mutable is not None
            raise MutableResourceConflictError(current.recurso_mutable, conflict.run_id)
        return self._record_run(current.dispatch(now=now), "run_dispatched", now=now)

    def confirm_run_running(self, run_id: str, *, now: datetime) -> Run:
        current = self._require_run(run_id)
        return self._record_run(current.confirm_running(now=now), "run_confirmed_running", now=now)

    def observe_run(self, run_id: str, *, observacion: str, now: datetime) -> Run:
        current = self._require_run(run_id)
        return self._record_run(
            current.observe(observacion=observacion, now=now), "run_observed", now=now
        )

    def succeed_run(self, run_id: str, *, resultado: Mapping[str, object], now: datetime) -> Run:
        current = self._require_run(run_id)
        return self._record_run(
            current.succeed(resultado=resultado, now=now), "run_succeeded", now=now
        )

    def fail_run(self, run_id: str, *, diagnostico: str, now: datetime) -> Run:
        current = self._require_run(run_id)
        return self._record_run(
            current.fail(diagnostico=diagnostico, now=now), "run_failed", now=now
        )

    def mark_run_lost(self, run_id: str, *, now: datetime) -> Run:
        current = self._require_run(run_id)
        return self._record_run(current.mark_lost(now=now), "run_marked_lost", now=now)

    def request_run_cancellation(self, run_id: str, *, now: datetime) -> Run:
        current = self._require_run(run_id)
        return self._record_run(
            current.request_cancel(now=now), "run_cancellation_requested", now=now
        )

    def confirm_run_cancelled(self, run_id: str, *, now: datetime) -> Run:
        current = self._require_run(run_id)
        return self._record_run(
            current.confirm_cancelled(now=now), "run_cancellation_confirmed", now=now
        )

    def retry_run(
        self,
        run_id: str,
        *,
        new_run_id: str,
        deadline: datetime,
        now: datetime,
        worker: str | None = None,
        work_package: Mapping[str, object] | None = None,
    ) -> Run:
        if new_run_id in self._runs:
            raise DuplicateIdError("Run", new_run_id)
        previous = self._require_run(run_id)
        new_run = run_ops.retry(
            previous,
            run_id=new_run_id,
            deadline=deadline,
            now=now,
            worker=worker,
            work_package=work_package,
        )
        return self._record_run(new_run, "run_retried", now=now)

    def substitute_run_worker(
        self,
        run_id: str,
        *,
        new_run_id: str,
        worker: str,
        motivo: str,
        deadline: datetime,
        now: datetime,
        work_package: Mapping[str, object] | None = None,
    ) -> Run:
        if new_run_id in self._runs:
            raise DuplicateIdError("Run", new_run_id)
        previous = self._require_run(run_id)
        new_run = run_ops.substitute_worker(
            previous,
            run_id=new_run_id,
            worker=worker,
            motivo=motivo,
            deadline=deadline,
            now=now,
            work_package=work_package,
        )
        return self._record_run(new_run, "run_worker_substituted", now=now)
