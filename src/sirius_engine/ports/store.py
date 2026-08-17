"""Puerto de persistencia del Work Engine (arquitectura §3.1-§3.3, incidencia #177).

Contrato explícito que cualquier almacén del motor debe satisfacer: crear y
transicionar ``WorkItem``/``Run``, exponer el historial de versiones de un
WorkItem, y llevar el diario de eventos append-only. La representación
física NO se decide aquí (queda para I3/I4, arquitectura §15); en A1 solo
existe la implementación en memoria de
:mod:`sirius_engine.adapters.memory_store`, pero el mismo conjunto de
pruebas de comportamiento se escribe contra este puerto para que una futura
implementación durable las pase sin modificarlas (incidencia #177, requisito 9).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol

from sirius_engine.domain.events import Event
from sirius_engine.domain.run import Run
from sirius_engine.domain.work_item import WorkItem, WorkItemClass


class WorkEngineStore(Protocol):
    """Contrato implementado por el almacén en memoria y por futuros almacenes durables."""

    # -- WorkItem -------------------------------------------------------------

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
        """Crear un WorkItem confirmado en ``PLANNED`` y registrarlo en el diario."""
        ...

    def get_work_item(self, work_id: str) -> WorkItem | None:
        """Devolver la última versión conocida del WorkItem, o ``None`` si no existe."""
        ...

    def list_work_item_versions(self, work_id: str) -> Sequence[WorkItem]:
        """Devolver todas las versiones del WorkItem, en orden de creación."""
        ...

    def activate_work_item(self, work_id: str, *, now: datetime) -> WorkItem: ...

    def cancel_work_item(self, work_id: str, *, now: datetime) -> WorkItem: ...

    def escalate_work_item(self, work_id: str, *, now: datetime) -> WorkItem: ...

    def resolve_work_item_decision(
        self, work_id: str, *, continuar: bool, now: datetime
    ) -> WorkItem: ...

    def dispatch_work_item_async(self, work_id: str, *, now: datetime) -> WorkItem: ...

    def observe_work_item_external_fact(self, work_id: str, *, now: datetime) -> WorkItem: ...

    def fail_work_item_safely(
        self, work_id: str, *, diagnostico: str, now: datetime
    ) -> WorkItem: ...

    def reactivate_work_item(self, work_id: str, *, now: datetime) -> WorkItem: ...

    def deliver_work_item(
        self, work_id: str, *, resultado: Mapping[str, object], now: datetime
    ) -> WorkItem:
        """``ACTIVE -> DELIVERED``. Requiere haber llegado a fase ``ENTREGAR`` (§3.4)."""
        ...

    def begin_work_item_execution(self, work_id: str, *, now: datetime) -> WorkItem:
        """Fase ``PREPARAR -> EJECUTAR`` (§3.4)."""
        ...

    def begin_work_item_check(self, work_id: str, *, now: datetime) -> WorkItem:
        """Fase ``EJECUTAR -> COMPROBAR`` (§3.4)."""
        ...

    def begin_work_item_review(self, work_id: str, *, now: datetime) -> WorkItem:
        """Fase ``COMPROBAR -> REVISAR`` (§3.4)."""
        ...

    def approve_work_item_review(self, work_id: str, *, now: datetime) -> WorkItem:
        """Fase ``REVISAR -> ENTREGAR`` (revisión ``APPROVED``, §3.4)."""
        ...

    def request_work_item_repair(self, work_id: str, *, now: datetime) -> WorkItem:
        """Fase ``REVISAR -> REPARAR`` (revisión ``CHANGES_REQUIRED``, §3.4)."""
        ...

    def resume_work_item_after_repair(self, work_id: str, *, now: datetime) -> WorkItem:
        """Fase ``REPARAR -> COMPROBAR``: reingresa al bucle revisar-reparar (§3.4)."""
        ...

    def pause_work_item(self, work_id: str, *, now: datetime) -> WorkItem: ...

    def resume_work_item(self, work_id: str, *, now: datetime) -> WorkItem: ...

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
        """Edición versionada del alcance. Si invalida Runs vivos, los cancela primero (§3.2)."""
        ...

    def reprioritize_work_item(
        self, work_id: str, *, prioridad: int, now: datetime
    ) -> WorkItem: ...

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
        """Crear el primer Run (intento 1) de un paso, en ``PREPARED``."""
        ...

    def get_run(self, run_id: str) -> Run | None: ...

    def list_runs_for_work_item(self, work_id: str) -> Sequence[Run]: ...

    def dispatch_run(self, run_id: str, *, now: datetime) -> Run:
        """``PREPARED -> DISPATCHED``.

        Rechaza el despacho con
        :class:`~sirius_engine.domain.errors.MutableResourceConflictError`
        si el Run comparte ``recurso_mutable`` con otro Run vivo cuya
        cancelación sigue sin confirmar.
        """
        ...

    def confirm_run_running(self, run_id: str, *, now: datetime) -> Run: ...

    def observe_run(self, run_id: str, *, observacion: str, now: datetime) -> Run: ...

    def succeed_run(
        self, run_id: str, *, resultado: Mapping[str, object], now: datetime
    ) -> Run: ...

    def fail_run(self, run_id: str, *, diagnostico: str, now: datetime) -> Run: ...

    def mark_run_lost(self, run_id: str, *, now: datetime) -> Run: ...

    def request_run_cancellation(self, run_id: str, *, now: datetime) -> Run: ...

    def confirm_run_cancelled(self, run_id: str, *, now: datetime) -> Run: ...

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
        """Crear un Run nuevo (intento+1) sobre el mismo paso que ``run_id``, sin mutarlo."""
        ...

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
        """Crear un Run nuevo con otro Worker, registrando el motivo, sin mutar ``run_id``."""
        ...

    # -- Diario de eventos --------------------------------------------------------

    def list_events(self) -> Sequence[Event]:
        """Devolver todos los eventos registrados, en orden de escritura."""
        ...
