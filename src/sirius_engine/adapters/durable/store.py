"""Almacén durable de referencia del puerto ``WorkEngineStore`` (A2, incidencia #186).

Implementa el puerto **completo** (``WorkItem`` y ``Run``, todas las
transiciones) sobre el mismo patrón de escritura que S1 demostró seguro
(ADR-026): diario append-only con `fsync`, checksum SHA-256 por registro y
clave de idempotencia opcional
(:mod:`sirius_engine.adapters.durable.journal`), reutilizando el dominio de
A1 sin reimplementar ninguna transición y ``Event``/``rebuild_state``
(:mod:`sirius_engine.domain.events`) para reconstruir el estado.

**De referencia, no definitiva** (ADR-019, ADR-029): la representación
física del almacén la fija D2, no este módulo. La suite de comportamiento en
``tests/engine/`` está escrita contra el puerto y corre, sin modificarse,
tanto sobre :class:`~sirius_engine.adapters.memory_store.InMemoryWorkEngineStore`
como sobre este almacén.

A diferencia del spike de S1 (que releía el diario entero en cada llamada,
límite conocido documentado en ``RESULTADOS.md``), este almacén reproduce el
diario **una sola vez**, al construirse, y mantiene un índice en memoria
(``_work_items``, ``_runs``, ``_events``, ``_idempotency_seen``) que
actualiza de forma incremental en cada anexo — sin volver a leer el fichero
por escritura.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from sirius_engine.adapters.durable.entity_codec import (
    entity_from_dict,
    run_to_dict,
    work_item_to_dict,
)
from sirius_engine.adapters.durable.journal import append_durably, replay
from sirius_engine.domain import run as run_ops
from sirius_engine.domain import work_item as work_item_ops
from sirius_engine.domain.errors import (
    DuplicateIdError,
    MutableResourceConflictError,
    UnknownRunError,
    UnknownWorkItemError,
)
from sirius_engine.domain.events import AggregateType, Event, EventKind, rebuild_state
from sirius_engine.domain.run import Run
from sirius_engine.domain.work_item import WorkItem, WorkItemClass


class DurableWorkEngineStore:
    """Satisface :class:`sirius_engine.ports.store.WorkEngineStore` de forma durable."""

    def __init__(self, journal_path: Path) -> None:
        self._journal_path = journal_path
        self._events: list[Event] = []
        self._work_items: dict[str, WorkItem] = {}
        self._runs: dict[str, Run] = {}
        self._idempotency_seen: dict[str, WorkItem | Run] = {}
        self._next_sequence = 1
        self._load()

    # -- carga inicial: una sola pasada por el diario -----------------------------

    def _load(self) -> None:
        for record in replay(self._journal_path).valid_records:
            aggregate_type = AggregateType(record["aggregate_type"])
            entity = entity_from_dict(aggregate_type, record["entity"])
            event = Event(
                sequence=record["sequence"],
                occurred_at=datetime.fromisoformat(record["occurred_at"]),
                aggregate_type=aggregate_type,
                aggregate_id=record["aggregate_id"],
                kind=record["kind"],
                entity=entity,
            )
            self._absorb(event, idempotency_key=record.get("idempotency_key"))

    def _absorb(self, event: Event, *, idempotency_key: str | None) -> None:
        """Registrar ``event`` en el índice en memoria, sin volver a tocar el diario."""
        self._events.append(event)
        self._next_sequence = max(self._next_sequence, event.sequence + 1)
        if event.aggregate_type is AggregateType.WORK_ITEM:
            assert isinstance(event.entity, WorkItem)
            self._work_items[event.aggregate_id] = event.entity
        else:
            assert isinstance(event.entity, Run)
            self._runs[event.aggregate_id] = event.entity
        if idempotency_key is not None and idempotency_key not in self._idempotency_seen:
            self._idempotency_seen[idempotency_key] = event.entity

    # -- diario -----------------------------------------------------------------

    def list_events(self) -> Sequence[Event]:
        return tuple(self._events)

    def _append_work_item(
        self,
        work_item: WorkItem,
        kind: EventKind,
        *,
        now: datetime,
        idempotency_key: str | None,
    ) -> WorkItem:
        """Anexar de forma durable, o devolver lo ya anexado si ``idempotency_key`` se repite.

        Requisito «sin duplicación al reproducir» (ADR-026): si el llamador
        reintenta la MISMA petición lógica -porque el intento anterior murió
        después de escribir pero antes de confirmar-, no se anexa un segundo
        evento: se devuelve lo que el intento anterior ya produjo.
        """
        if idempotency_key is not None:
            cached = self._idempotency_seen.get(idempotency_key)
            if cached is not None:
                assert isinstance(cached, WorkItem)
                return cached
        sequence = self._next_sequence
        record = {
            "sequence": sequence,
            "occurred_at": now.isoformat(),
            "aggregate_type": AggregateType.WORK_ITEM.value,
            "aggregate_id": work_item.work_id,
            "kind": kind,
            "entity": work_item_to_dict(work_item),
            "idempotency_key": idempotency_key,
        }
        append_durably(self._journal_path, record)
        self._absorb(
            Event(
                sequence=sequence,
                occurred_at=now,
                aggregate_type=AggregateType.WORK_ITEM,
                aggregate_id=work_item.work_id,
                kind=kind,
                entity=work_item,
            ),
            idempotency_key=idempotency_key,
        )
        return work_item

    def _append_run(
        self,
        run: Run,
        kind: EventKind,
        *,
        now: datetime,
        idempotency_key: str | None,
    ) -> Run:
        if idempotency_key is not None:
            cached = self._idempotency_seen.get(idempotency_key)
            if cached is not None:
                assert isinstance(cached, Run)
                return cached
        sequence = self._next_sequence
        record = {
            "sequence": sequence,
            "occurred_at": now.isoformat(),
            "aggregate_type": AggregateType.RUN.value,
            "aggregate_id": run.run_id,
            "kind": kind,
            "entity": run_to_dict(run),
            "idempotency_key": idempotency_key,
        }
        append_durably(self._journal_path, record)
        self._absorb(
            Event(
                sequence=sequence,
                occurred_at=now,
                aggregate_type=AggregateType.RUN,
                aggregate_id=run.run_id,
                kind=kind,
                entity=run,
            ),
            idempotency_key=idempotency_key,
        )
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
        idempotency_key: str | None = None,
    ) -> WorkItem:
        if idempotency_key is not None:
            cached = self._idempotency_seen.get(idempotency_key)
            if cached is not None:
                assert isinstance(cached, WorkItem)
                return cached
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
        return self._append_work_item(
            work_item, "work_item_created", now=now, idempotency_key=idempotency_key
        )

    def get_work_item(self, work_id: str) -> WorkItem | None:
        return self._work_items.get(work_id)

    def list_work_item_versions(self, work_id: str) -> Sequence[WorkItem]:
        """Una instantánea por revisión de alcance (§3.2), no una por evento.

        Delega en :func:`~sirius_engine.domain.events.rebuild_state` sobre el
        mismo índice de eventos en memoria que respalda este almacén, igual
        que hace :class:`~sirius_engine.adapters.memory_store.InMemoryWorkEngineStore`.
        """
        return rebuild_state(self._events).work_item_versions.get(work_id, ())

    def activate_work_item(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.activate(now=now),
            "work_item_activated",
            now=now,
            idempotency_key=idempotency_key,
        )

    def cancel_work_item(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.cancel(now=now),
            "work_item_cancelled",
            now=now,
            idempotency_key=idempotency_key,
        )

    def escalate_work_item(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.escalate(now=now),
            "work_item_escalated",
            now=now,
            idempotency_key=idempotency_key,
        )

    def resolve_work_item_decision(
        self,
        work_id: str,
        *,
        continuar: bool,
        now: datetime,
        idempotency_key: str | None = None,
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.resolve_decision(continuar=continuar, now=now),
            "work_item_decision_resolved",
            now=now,
            idempotency_key=idempotency_key,
        )

    def dispatch_work_item_async(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.dispatch_async(now=now),
            "work_item_dispatched_async",
            now=now,
            idempotency_key=idempotency_key,
        )

    def observe_work_item_external_fact(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.observe_external_fact(now=now),
            "work_item_observed_external_fact",
            now=now,
            idempotency_key=idempotency_key,
        )

    def fail_work_item_safely(
        self,
        work_id: str,
        *,
        diagnostico: str,
        now: datetime,
        idempotency_key: str | None = None,
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.fail_safely(diagnostico=diagnostico, now=now),
            "work_item_failed_safely",
            now=now,
            idempotency_key=idempotency_key,
        )

    def reactivate_work_item(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.reactivate(now=now),
            "work_item_reactivated",
            now=now,
            idempotency_key=idempotency_key,
        )

    def deliver_work_item(
        self,
        work_id: str,
        *,
        resultado: Mapping[str, object],
        now: datetime,
        idempotency_key: str | None = None,
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.deliver(resultado=resultado, now=now),
            "work_item_delivered",
            now=now,
            idempotency_key=idempotency_key,
        )

    def begin_work_item_execution(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.begin_execution(now=now),
            "work_item_execution_started",
            now=now,
            idempotency_key=idempotency_key,
        )

    def begin_work_item_check(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.begin_check(now=now),
            "work_item_check_started",
            now=now,
            idempotency_key=idempotency_key,
        )

    def begin_work_item_review(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.begin_review(now=now),
            "work_item_review_started",
            now=now,
            idempotency_key=idempotency_key,
        )

    def approve_work_item_review(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.approve_review(now=now),
            "work_item_review_approved",
            now=now,
            idempotency_key=idempotency_key,
        )

    def request_work_item_repair(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.request_repair(now=now),
            "work_item_repair_requested",
            now=now,
            idempotency_key=idempotency_key,
        )

    def resume_work_item_after_repair(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.resume_after_repair(now=now),
            "work_item_repair_resumed",
            now=now,
            idempotency_key=idempotency_key,
        )

    def pause_work_item(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.pause(now=now), "work_item_paused", now=now, idempotency_key=idempotency_key
        )

    def resume_work_item(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.resume(now=now), "work_item_resumed", now=now, idempotency_key=idempotency_key
        )

    def change_work_item_scope(
        self,
        work_id: str,
        *,
        now: datetime,
        objetivo: str | None = None,
        entregable: str | None = None,
        criterio_terminado: str | None = None,
        limites: Mapping[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        changed = current.change_scope(
            now=now,
            objetivo=objetivo,
            entregable=entregable,
            criterio_terminado=criterio_terminado,
            limites=limites,
        )
        # Arquitectura §3.2, réplica exacta de InMemoryWorkEngineStore (ver su
        # docstring): (a) marcar TODO Run no terminado como obsoleto, sin
        # condición sobre su estado de cancelación; (b) parar al Worker solo
        # donde procede -cerrar de una vez un PREPARED, pedir cancelación a
        # uno vivo sin cancelación ya pedida, o solo marcar si ya la tenía.
        for run in self.list_runs_for_work_item(work_id):
            if run.estado is run_ops.RunState.FINISHED:
                continue
            invalidado = run.mark_scope_invalidated(now=now)
            if invalidado.estado is run_ops.RunState.PREPARED:
                self._append_run(
                    invalidado.invalidate_prepared(now=now),
                    "run_prepared_invalidated",
                    now=now,
                    idempotency_key=None,
                )
            elif invalidado.cancellation_status is run_ops.CancellationStatus.NONE:
                self._append_run(
                    invalidado.request_cancel(now=now),
                    "run_cancellation_requested",
                    now=now,
                    idempotency_key=None,
                )
            else:
                self._append_run(invalidado, "run_scope_invalidated", now=now, idempotency_key=None)
        return self._append_work_item(
            changed, "work_item_scope_changed", now=now, idempotency_key=idempotency_key
        )

    def reprioritize_work_item(
        self,
        work_id: str,
        *,
        prioridad: int,
        now: datetime,
        idempotency_key: str | None = None,
    ) -> WorkItem:
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.reprioritize(prioridad=prioridad, now=now),
            "work_item_reprioritized",
            now=now,
            idempotency_key=idempotency_key,
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
        idempotency_key: str | None = None,
    ) -> Run:
        if idempotency_key is not None:
            cached = self._idempotency_seen.get(idempotency_key)
            if cached is not None:
                assert isinstance(cached, Run)
                return cached
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
        return self._append_run(run, "run_prepared", now=now, idempotency_key=idempotency_key)

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

    def dispatch_run(
        self, run_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> Run:
        current = self._require_run(run_id)
        conflict = self._conflicting_unconfirmed_cancellation(current)
        if conflict is not None:
            assert current.recurso_mutable is not None
            raise MutableResourceConflictError(current.recurso_mutable, conflict.run_id)
        return self._append_run(
            current.dispatch(now=now), "run_dispatched", now=now, idempotency_key=idempotency_key
        )

    def confirm_run_running(
        self, run_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> Run:
        current = self._require_run(run_id)
        return self._append_run(
            current.confirm_running(now=now),
            "run_confirmed_running",
            now=now,
            idempotency_key=idempotency_key,
        )

    def observe_run(
        self,
        run_id: str,
        *,
        observacion: str,
        now: datetime,
        idempotency_key: str | None = None,
    ) -> Run:
        current = self._require_run(run_id)
        return self._append_run(
            current.observe(observacion=observacion, now=now),
            "run_observed",
            now=now,
            idempotency_key=idempotency_key,
        )

    def succeed_run(
        self,
        run_id: str,
        *,
        resultado: Mapping[str, object],
        now: datetime,
        idempotency_key: str | None = None,
    ) -> Run:
        current = self._require_run(run_id)
        return self._append_run(
            current.succeed(resultado=resultado, now=now),
            "run_succeeded",
            now=now,
            idempotency_key=idempotency_key,
        )

    def fail_run(
        self,
        run_id: str,
        *,
        diagnostico: str,
        now: datetime,
        idempotency_key: str | None = None,
    ) -> Run:
        current = self._require_run(run_id)
        return self._append_run(
            current.fail(diagnostico=diagnostico, now=now),
            "run_failed",
            now=now,
            idempotency_key=idempotency_key,
        )

    def mark_run_lost(
        self, run_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> Run:
        current = self._require_run(run_id)
        return self._append_run(
            current.mark_lost(now=now),
            "run_marked_lost",
            now=now,
            idempotency_key=idempotency_key,
        )

    def request_run_cancellation(
        self, run_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> Run:
        current = self._require_run(run_id)
        return self._append_run(
            current.request_cancel(now=now),
            "run_cancellation_requested",
            now=now,
            idempotency_key=idempotency_key,
        )

    def confirm_run_cancelled(
        self, run_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> Run:
        current = self._require_run(run_id)
        return self._append_run(
            current.confirm_cancelled(now=now),
            "run_cancellation_confirmed",
            now=now,
            idempotency_key=idempotency_key,
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
        idempotency_key: str | None = None,
    ) -> Run:
        if idempotency_key is not None:
            cached = self._idempotency_seen.get(idempotency_key)
            if cached is not None:
                assert isinstance(cached, Run)
                return cached
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
        return self._append_run(new_run, "run_retried", now=now, idempotency_key=idempotency_key)

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
        idempotency_key: str | None = None,
    ) -> Run:
        if idempotency_key is not None:
            cached = self._idempotency_seen.get(idempotency_key)
            if cached is not None:
                assert isinstance(cached, Run)
                return cached
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
        return self._append_run(
            new_run, "run_worker_substituted", now=now, idempotency_key=idempotency_key
        )
