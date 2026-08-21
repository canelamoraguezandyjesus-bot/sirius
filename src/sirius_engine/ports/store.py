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
from sirius_engine.domain.worker_ref import WorkerRef


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
    ) -> WorkItem:
        """Crear un WorkItem directamente en ``NEEDS_DECISION``, en una sola operación.

        Para el caso ``CREAR_Y_ESCALAR`` de la puerta (arquitectura §8.5):
        a diferencia de encadenar ``create_work_item`` + ``activate_work_item``
        + ``escalate_work_item``, ningún observador puede ver ``ACTIVE`` de
        forma intermedia -ni una caída a mitad de camino puede dejar un
        trabajo sensible en ese estado- porque solo hay un punto de
        persistencia para las tres transiciones.
        """
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

    def cancel_all_live_runs_and_escalate_work_item(
        self, work_id: str, *, now: datetime
    ) -> WorkItem:
        """Pedir la cancelación de TODOS los Runs vivos del WorkItem y escalarlo.

        Una sola operación reanudable, para el corte por presupuesto agotado
        (``governance.registrar_gasto``, CODEX-001 ronda 3, incidencia
        #206/#207): a diferencia de listar los Runs y pedir su cancelación
        uno a uno desde fuera, terminando con un ``escalate_work_item``
        aparte, esto es un único punto de reintento. Pedir la cancelación de
        un Run que ya la tenía pedida es un no-op (se salta, igual que
        ``change_work_item_scope``); si el WorkItem ya está en
        ``NEEDS_DECISION`` -porque un intento anterior completó el corte
        pero el llamador no llegó a saberlo antes de caer- se devuelve tal
        cual, sin volver a intentar la transición ``escalate`` y sin lanzar.
        Así, si una caída deja el corte a medias -algunos Runs cancelados,
        otros no, con o sin escalar todavía-, llamarlo de nuevo con el mismo
        ``work_id`` retoma exactamente donde se quedó hasta completarlo.
        """
        ...

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
        worker: WorkerRef,
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

    def confirm_run_running(
        self,
        run_id: str,
        *,
        now: datetime,
        modelo: str | None = None,
        runtime: str | None = None,
    ) -> Run:
        """``DISPATCHED -> RUNNING``, anotando el modelo/runtime que el Worker aceptó.

        ``modelo`` y ``runtime`` son opcionales porque no todo Worker los
        dice; omitirlos deja intacto lo que ya constara. Contradecir lo ya
        registrado levanta
        :class:`~sirius_engine.domain.errors.WorkerRuntimeConflictError`.
        """
        ...

    def observe_run(self, run_id: str, *, observacion: str, now: datetime) -> Run: ...

    def succeed_run(
        self, run_id: str, *, resultado: Mapping[str, object], now: datetime
    ) -> Run: ...

    def fail_run(self, run_id: str, *, diagnostico: str, now: datetime) -> Run: ...

    def mark_run_lost(self, run_id: str, *, now: datetime, diagnostico: str | None = None) -> Run:
        """``{DISPATCHED,RUNNING} -> FINISHED(LOST)``.

        ``diagnostico`` conserva lo que el observador del mundo haya dicho
        sobre por qué se declaró perdido (CODEX-002); opcional porque no
        todo observador lo da.
        """
        ...

    def request_run_cancellation(self, run_id: str, *, now: datetime) -> Run: ...

    def confirm_run_cancelled(self, run_id: str, *, now: datetime) -> Run: ...

    def retry_run(
        self,
        run_id: str,
        *,
        new_run_id: str,
        deadline: datetime,
        now: datetime,
        worker: WorkerRef | None = None,
        work_package: Mapping[str, object] | None = None,
    ) -> Run:
        """Crear un Run nuevo (intento+1) sobre el mismo paso que ``run_id``, sin mutarlo."""
        ...

    def substitute_run_worker(
        self,
        run_id: str,
        *,
        new_run_id: str,
        worker: WorkerRef,
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
