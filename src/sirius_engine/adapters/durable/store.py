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
from sirius_engine.adapters.durable.journal import DirectorySyncError, append_durably, replay
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

# Clave interna de la cascada de invalidación de `change_work_item_scope`
# (CODEX-001, ronda 5): una tupla, nunca una `str`. La clave pública que
# aporta el llamador siempre es `str`; al derivar la clave de cada Run de la
# cascada con una tupla en vez de concatenar texto (p.ej. `f"{key}::scope-
# cascade::{run_id}"`), ninguna clave pública -sea cual sea su contenido-
# puede colisionar por igualdad con una derivada: son de tipos distintos y
# `"x" == ("a", "b", "c")` es siempre `False` en Python. Antes, una clave
# pública que por casualidad (o a propósito) tuviera la forma exacta del
# texto compuesto colisionaba en `_idempotency_seen` con la derivada
# correspondiente y `_append_run` devolvía el Run cacheado sin anexar la
# invalidación.
_ScopeCascadeKey = tuple[str, str, str]
_IdempotencyKey = str | _ScopeCascadeKey

# CODEX-001 (ronda 6): forma de texto que usaba la clave interna de la
# cascada ANTES de la ronda 5 (``f"{idempotency_key}::scope-cascade::
# {run.run_id}"``). Un diario escrito por esa versión persiste esa clave
# como `str`, no como la tupla que esta versión deriva; `_decode_idempotency_key`
# reconstruye la tupla equivalente al reproducir un registro con esa forma,
# para que un reintento tras una cascada incompleta la reconozca igual que
# reconocería una escrita ya en formato nuevo. Solo se aplica a los tres
# tipos de evento que la cascada puede producir (ninguna otra vía de la API
# pública los emite con clave derivada) y exige que el sufijo coincida con
# el `aggregate_id` del propio registro, para no confundir por casualidad
# una clave pública que un llamador hubiera elegido con esa forma exacta
# (el mismo riesgo, ya aceptado, que motivó la ronda 5 para el formato
# nuevo: aquí es inevitable porque el formato viejo era literalmente texto
# concatenado y no lleva ninguna marca que lo distinga de una clave
# pública coincidente).
_LEGACY_SCOPE_CASCADE_MARKER = "::scope-cascade::"
_LEGACY_SCOPE_CASCADE_KINDS = frozenset(
    {"run_prepared_invalidated", "run_cancellation_requested", "run_scope_invalidated"}
)


class DurableWorkEngineStore:
    """Satisface :class:`sirius_engine.ports.store.WorkEngineStore` de forma durable."""

    def __init__(self, journal_path: Path) -> None:
        self._journal_path = journal_path
        self._events: list[Event] = []
        self._work_items: dict[str, WorkItem] = {}
        self._runs: dict[str, Run] = {}
        self._idempotency_seen: dict[_IdempotencyKey, WorkItem | Run] = {}
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
            self._absorb(event, idempotency_key=self._decode_idempotency_key(record))

    @staticmethod
    def _decode_idempotency_key(record: Mapping[str, object]) -> _IdempotencyKey | None:
        """Reconstruir la clave de idempotencia de un registro del diario.

        Una clave interna de cascada (:data:`_ScopeCascadeKey`) se escribe en
        JSON como lista -``json`` no distingue tupla de lista- y hay que
        devolverla como tupla para que sea hashable y comparable de nuevo
        contra las derivadas en memoria; una clave pública sigue siendo
        ``str`` tal cual.

        CODEX-001 (ronda 6): un registro heredado de antes de la ronda 5
        persiste la clave interna de la cascada como texto concatenado
        (:data:`_LEGACY_SCOPE_CASCADE_MARKER`), no como lista. Si el
        registro es de uno de los tres tipos que solo la cascada emite
        (:data:`_LEGACY_SCOPE_CASCADE_KINDS`) y el texto termina exactamente
        en ``"::scope-cascade::" + aggregate_id`` de ESTE registro, se
        reconstruye la misma tupla que derivaría la cascada actual, para que
        un reintento tras una cascada incompleta la reconozca.

        CODEX-001 (ronda 7): ``run_cancellation_requested`` no es exclusivo
        de la cascada -a diferencia de los otros dos tipos de
        :data:`_LEGACY_SCOPE_CASCADE_KINDS`, la API pública
        ``request_run_cancellation`` también lo emite, con una clave que
        elige el llamador-. Si esa clave pública coincide por casualidad con
        la forma heredada (``"<algo>::scope-cascade::<run_id>"`` para ESTE
        ``run_id``), la detección de arriba la confundiría con la clave
        interna heredada y la convertiría en la tupla derivada, perdiendo la
        idempotencia de la cancelación pública. Por eso, para este tipo en
        concreto, además de la forma del texto se exige la evidencia
        persistida de que el registro salió de la cascada: el propio Run
        anexado lleva ``invalidado_por_alcance=True`` (:mod:`domain.run`)
        únicamente cuando pasó por ``mark_scope_invalidated`` antes de
        ``request_cancel``, algo que solo hace la cascada -la API pública
        llama a ``request_cancel`` directamente y, si el Run ya estuviera
        invalidado por alcance, ya tendría la cancelación en curso y
        ``request_cancel`` rechazaría la llamada por transición ilegal antes
        de que hubiera nada que anexar-. Los otros dos tipos siguen sin
        necesitar esta comprobación porque ningún camino público los emite.
        """
        raw = record.get("idempotency_key")
        if isinstance(raw, list):
            return tuple(raw)
        assert raw is None or isinstance(raw, str)
        if isinstance(raw, str) and record.get("kind") in _LEGACY_SCOPE_CASCADE_KINDS:
            entity = record.get("entity")
            assert isinstance(entity, Mapping)
            is_cascade_evidence = (
                record.get("kind") != "run_cancellation_requested"
                or entity.get("invalidado_por_alcance") is True
            )
            if is_cascade_evidence:
                aggregate_id = record.get("aggregate_id")
                assert isinstance(aggregate_id, str)
                legacy_suffix = f"{_LEGACY_SCOPE_CASCADE_MARKER}{aggregate_id}"
                if raw.endswith(legacy_suffix):
                    public_key = raw[: -len(legacy_suffix)]
                    return ("scope-cascade", public_key, aggregate_id)
        return raw

    def _absorb(self, event: Event, *, idempotency_key: _IdempotencyKey | None) -> None:
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
        idempotency_key: _IdempotencyKey | None,
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
        event = Event(
            sequence=sequence,
            occurred_at=now,
            aggregate_type=AggregateType.WORK_ITEM,
            aggregate_id=work_item.work_id,
            kind=kind,
            entity=work_item,
        )
        try:
            append_durably(self._journal_path, record)
        except DirectorySyncError:
            # CODEX-001: el registro ya quedó completo y con fsync en el
            # propio diario -solo falló sincronizar su directorio padre-, así
            # que el evento ya ocurrió de forma durable. Reconciliar el
            # índice en memoria ahora evita que un reintento con la misma
            # clave, al no encontrarla en `_idempotency_seen`, vuelva a
            # anexar un segundo registro con la misma secuencia.
            self._absorb(event, idempotency_key=idempotency_key)
            raise
        self._absorb(event, idempotency_key=idempotency_key)
        return work_item

    def _append_run(
        self,
        run: Run,
        kind: EventKind,
        *,
        now: datetime,
        idempotency_key: _IdempotencyKey | None,
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
        event = Event(
            sequence=sequence,
            occurred_at=now,
            aggregate_type=AggregateType.RUN,
            aggregate_id=run.run_id,
            kind=kind,
            entity=run,
        )
        try:
            append_durably(self._journal_path, record)
        except DirectorySyncError:
            # CODEX-001: mismo razonamiento que en `_append_work_item`.
            self._absorb(event, idempotency_key=idempotency_key)
            raise
        self._absorb(event, idempotency_key=idempotency_key)
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

    def _idempotent_work_item(self, idempotency_key: str | None) -> WorkItem | None:
        """Resultado ya anexado para ``idempotency_key``, o ``None`` si es una clave nueva.

        Debe consultarse ANTES de evaluar cualquier transición del dominio o
        efecto derivado (CODEX-002): un reintento con la misma clave no debe
        recomputar la transición sobre el estado ya avanzado.
        """
        if idempotency_key is None:
            return None
        cached = self._idempotency_seen.get(idempotency_key)
        if cached is None:
            return None
        assert isinstance(cached, WorkItem)
        return cached

    def _idempotent_run(self, idempotency_key: str | None) -> Run | None:
        """Análogo a :meth:`_idempotent_work_item`, para transiciones de ``Run``."""
        if idempotency_key is None:
            return None
        cached = self._idempotency_seen.get(idempotency_key)
        if cached is None:
            return None
        assert isinstance(cached, Run)
        return cached

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

    def create_and_escalate_work_item(
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
        work_item = (
            work_item_ops.create_work_item(
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
            .activate(now=now)
            .escalate(now=now)
        )
        return self._append_work_item(
            work_item,
            "work_item_created_needing_decision",
            now=now,
            idempotency_key=idempotency_key,
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
        current = self._require_work_item(work_id)
        return self._append_work_item(
            current.pause(now=now), "work_item_paused", now=now, idempotency_key=idempotency_key
        )

    def resume_work_item(
        self, work_id: str, *, now: datetime, idempotency_key: str | None = None
    ) -> WorkItem:
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        #
        # CODEX-001 (ronda 4): si el `fsync` del directorio falla a mitad de
        # esta cascada, el registro ya quedó durable (CODEX-001 previo) pero
        # el anexo del propio cambio de alcance -al final, con
        # `idempotency_key`- nunca llega a ocurrir. Un reintento con la MISMA
        # clave vuelve a evaluar `_idempotent_work_item` en falso y repetiría
        # cada anexo de esta cascada para los Runs ya procesados. Por eso cada
        # anexo interno lleva su propia clave derivada de la clave del
        # llamador: el reintento la encuentra ya en `_idempotency_seen`
        # -incluso si el intento anterior murió justo después de absorberla
        # en memoria- y `_append_run` la salta sin volver a anexar.
        #
        # CODEX-001 (ronda 5): la clave derivada es una tupla
        # (:data:`_ScopeCascadeKey`), no texto concatenado. Una clave pública
        # es siempre `str`; si se derivara concatenando texto (p.ej.
        # ``f"{idempotency_key}::scope-cascade::{run.run_id}"``), una clave
        # pública que un llamador anterior hubiera usado con esa forma exacta
        # colisionaría en `_idempotency_seen` con la derivada de una cascada
        # posterior, y `_append_run` devolvería el Run ya cacheado sin anexar
        # la invalidación. Una tupla nunca es igual a una `str`, así que esta
        # clave interna queda aislada de cualquier clave pública por
        # construcción, no solo por convención de formato.
        for run in self.list_runs_for_work_item(work_id):
            if run.estado is run_ops.RunState.FINISHED:
                continue
            run_idempotency_key: _ScopeCascadeKey | None = (
                ("scope-cascade", idempotency_key, run.run_id)
                if idempotency_key is not None
                else None
            )
            invalidado = run.mark_scope_invalidated(now=now)
            if invalidado.estado is run_ops.RunState.PREPARED:
                self._append_run(
                    invalidado.invalidate_prepared(now=now),
                    "run_prepared_invalidated",
                    now=now,
                    idempotency_key=run_idempotency_key,
                )
            elif invalidado.cancellation_status is run_ops.CancellationStatus.NONE:
                self._append_run(
                    invalidado.request_cancel(now=now),
                    "run_cancellation_requested",
                    now=now,
                    idempotency_key=run_idempotency_key,
                )
            else:
                self._append_run(
                    invalidado,
                    "run_scope_invalidated",
                    now=now,
                    idempotency_key=run_idempotency_key,
                )
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
        cached = self._idempotent_work_item(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_run(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_run(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_run(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_run(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_run(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_run(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_run(idempotency_key)
        if cached is not None:
            return cached
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
        cached = self._idempotent_run(idempotency_key)
        if cached is not None:
            return cached
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
