"""WorkItem: durable record and state machine (arquitectura §3.1-3.2).

A ``WorkItem`` is an immutable snapshot; every operation returns a *new*
instance instead of mutating the one it was called on, so the history kept
by a persistence port (and by the event journal) never has its past
rewritten. Illegal operations raise
:class:`~sirius_engine.domain.errors.IllegalTransitionError` instead of
coercing into a valid state.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from sirius_engine.domain.errors import IllegalPhaseTransitionError, IllegalTransitionError

_AGGREGATE = "WorkItem"


class WorkItemState(StrEnum):
    """States of §3.2. Order matches the diagram, not any priority."""

    PLANNED = "planned"
    ACTIVE = "active"
    WAITING = "waiting"
    NEEDS_DECISION = "needs_decision"
    PAUSED = "paused"
    FAILED_SAFELY = "failed_safely"
    CANCELLED = "cancelled"
    DELIVERED = "delivered"


#: Terminal states: no operation in §3.2 leaves an outgoing edge from these.
TERMINAL_STATES = frozenset({WorkItemState.CANCELLED, WorkItemState.DELIVERED})

#: States ``pausar`` may be called from (§3.2: "desde PLANNED/ACTIVE/WAITING").
PAUSABLE_STATES = frozenset({WorkItemState.PLANNED, WorkItemState.ACTIVE, WorkItemState.WAITING})


class WorkItemPhase(StrEnum):
    """Fases del ciclo revisar-reparar (arquitectura §3.4)."""

    PREPARAR = "preparar"
    EJECUTAR = "ejecutar"
    COMPROBAR = "comprobar"
    REVISAR = "revisar"
    REPARAR = "reparar"
    ENTREGAR = "entregar"


class WorkItemClass(StrEnum):
    """Clases de trabajo enumeradas en §3.1."""

    CONVERSACION_NO_APLICA = "conversacion-no-aplica"
    INVESTIGACION = "investigacion"
    DOCUMENTACION = "documentacion"
    PROGRAMACION = "programacion"
    AUDITORIA = "auditoria"
    CONSULTA_LARGA = "consulta-larga"
    MIXTA = "mixta"


@dataclass(frozen=True, slots=True)
class WorkItem:
    """Campos mínimos de §3.1."""

    work_id: str
    peticion_original: str
    objetivo: str
    contexto_origen: tuple[str, ...]
    entregable: str
    criterio_terminado: str
    limites: Mapping[str, object]
    prioridad: int
    clase: WorkItemClass
    estado: WorkItemState
    fase: WorkItemPhase
    plan: tuple[str, ...]
    version: int
    created_at: datetime
    updated_at: datetime
    evidencia: tuple[str, ...] = ()
    resultado: Mapping[str, object] | None = None
    diagnostico: str | None = None
    paused_from: WorkItemState | None = None

    def _require(self, allowed: frozenset[WorkItemState], operation: str) -> None:
        if self.estado not in allowed:
            raise IllegalTransitionError(_AGGREGATE, operation, self.estado)

    def _require_phase(self, allowed: frozenset[WorkItemPhase], operation: str) -> None:
        if self.fase not in allowed:
            raise IllegalPhaseTransitionError(_AGGREGATE, operation, self.fase)

    def activate(self, *, now: datetime) -> WorkItem:
        """``PLANNED -> ACTIVE`` (orden del propietario o cola aprobada)."""
        self._require(frozenset({WorkItemState.PLANNED}), "activate")
        return replace(self, estado=WorkItemState.ACTIVE, updated_at=now)

    def cancel(self, *, now: datetime) -> WorkItem:
        """``PLANNED -> CANCELLED`` or ``FAILED_SAFELY -> CANCELLED``.

        Cancelling from ``NEEDS_DECISION`` goes through
        :meth:`resolve_decision` instead, since §3.2 models it as part of
        the registered decision, not a bare ``cancelar``.
        """
        self._require(frozenset({WorkItemState.PLANNED, WorkItemState.FAILED_SAFELY}), "cancel")
        return replace(self, estado=WorkItemState.CANCELLED, updated_at=now)

    def escalate(self, *, now: datetime) -> WorkItem:
        """``ACTIVE -> NEEDS_DECISION``."""
        self._require(frozenset({WorkItemState.ACTIVE}), "escalate")
        return replace(self, estado=WorkItemState.NEEDS_DECISION, updated_at=now)

    def resolve_decision(self, *, continuar: bool, now: datetime) -> WorkItem:
        """``NEEDS_DECISION -> ACTIVE`` (reanudar) or ``-> CANCELLED`` (cancelar por decisión)."""
        self._require(frozenset({WorkItemState.NEEDS_DECISION}), "resolve_decision")
        target = WorkItemState.ACTIVE if continuar else WorkItemState.CANCELLED
        return replace(self, estado=target, updated_at=now)

    def dispatch_async(self, *, now: datetime) -> WorkItem:
        """``ACTIVE -> WAITING`` (despacho asíncrono)."""
        self._require(frozenset({WorkItemState.ACTIVE}), "dispatch_async")
        return replace(self, estado=WorkItemState.WAITING, updated_at=now)

    def observe_external_fact(self, *, now: datetime) -> WorkItem:
        """``WAITING -> ACTIVE`` (hecho externo observado por el supervisor)."""
        self._require(frozenset({WorkItemState.WAITING}), "observe_external_fact")
        return replace(self, estado=WorkItemState.ACTIVE, updated_at=now)

    def fail_safely(self, *, diagnostico: str, now: datetime) -> WorkItem:
        """``ACTIVE -> FAILED_SAFELY`` (sin progreso posible, con diagnóstico)."""
        self._require(frozenset({WorkItemState.ACTIVE}), "fail_safely")
        return replace(
            self, estado=WorkItemState.FAILED_SAFELY, diagnostico=diagnostico, updated_at=now
        )

    def reactivate(self, *, now: datetime) -> WorkItem:
        """``FAILED_SAFELY -> ACTIVE`` (reactivación consciente)."""
        self._require(frozenset({WorkItemState.FAILED_SAFELY}), "reactivate")
        return replace(self, estado=WorkItemState.ACTIVE, updated_at=now)

    def begin_execution(self, *, now: datetime) -> WorkItem:
        """``PREPARAR -> EJECUTAR`` (arquitectura §3.4)."""
        self._require(frozenset({WorkItemState.ACTIVE}), "begin_execution")
        self._require_phase(frozenset({WorkItemPhase.PREPARAR}), "begin_execution")
        return replace(self, fase=WorkItemPhase.EJECUTAR, updated_at=now)

    def begin_check(self, *, now: datetime) -> WorkItem:
        """``EJECUTAR -> COMPROBAR`` (arquitectura §3.4)."""
        self._require(frozenset({WorkItemState.ACTIVE}), "begin_check")
        self._require_phase(frozenset({WorkItemPhase.EJECUTAR}), "begin_check")
        return replace(self, fase=WorkItemPhase.COMPROBAR, updated_at=now)

    def begin_review(self, *, now: datetime) -> WorkItem:
        """``COMPROBAR -> REVISAR`` (arquitectura §3.4)."""
        self._require(frozenset({WorkItemState.ACTIVE}), "begin_review")
        self._require_phase(frozenset({WorkItemPhase.COMPROBAR}), "begin_review")
        return replace(self, fase=WorkItemPhase.REVISAR, updated_at=now)

    def approve_review(self, *, now: datetime) -> WorkItem:
        """``REVISAR -> ENTREGAR`` (revisión ``APPROVED``, arquitectura §3.4)."""
        self._require(frozenset({WorkItemState.ACTIVE}), "approve_review")
        self._require_phase(frozenset({WorkItemPhase.REVISAR}), "approve_review")
        return replace(self, fase=WorkItemPhase.ENTREGAR, updated_at=now)

    def request_repair(self, *, now: datetime) -> WorkItem:
        """``REVISAR -> REPARAR`` (revisión ``CHANGES_REQUIRED``, arquitectura §3.4)."""
        self._require(frozenset({WorkItemState.ACTIVE}), "request_repair")
        self._require_phase(frozenset({WorkItemPhase.REVISAR}), "request_repair")
        return replace(self, fase=WorkItemPhase.REPARAR, updated_at=now)

    def resume_after_repair(self, *, now: datetime) -> WorkItem:
        """``REPARAR -> COMPROBAR``: reingresa al bucle revisar-reparar (arquitectura §3.4)."""
        self._require(frozenset({WorkItemState.ACTIVE}), "resume_after_repair")
        self._require_phase(frozenset({WorkItemPhase.REPARAR}), "resume_after_repair")
        return replace(self, fase=WorkItemPhase.COMPROBAR, updated_at=now)

    def deliver(self, *, resultado: Mapping[str, object], now: datetime) -> WorkItem:
        """``ACTIVE -> DELIVERED`` (fase ENTREGAR completada).

        Requiere haber recorrido el ciclo de fases hasta ``ENTREGAR`` (§3.4)
        —vía :meth:`approve_review`— antes de aceptar la entrega.
        """
        self._require(frozenset({WorkItemState.ACTIVE}), "deliver")
        self._require_phase(frozenset({WorkItemPhase.ENTREGAR}), "deliver")
        return replace(
            self,
            estado=WorkItemState.DELIVERED,
            resultado=MappingProxyType(dict(resultado)),
            updated_at=now,
        )

    def pause(self, *, now: datetime) -> WorkItem:
        """``{PLANNED,ACTIVE,WAITING} -> PAUSED``, remembering the state to resume into."""
        self._require(PAUSABLE_STATES, "pause")
        return replace(self, estado=WorkItemState.PAUSED, paused_from=self.estado, updated_at=now)

    def resume(self, *, now: datetime) -> WorkItem:
        """``PAUSED -> estado previo``."""
        self._require(frozenset({WorkItemState.PAUSED}), "resume")
        assert self.paused_from is not None, "PAUSED WorkItem must record paused_from"
        return replace(self, estado=self.paused_from, paused_from=None, updated_at=now)

    def change_scope(
        self,
        *,
        now: datetime,
        objetivo: str | None = None,
        entregable: str | None = None,
        criterio_terminado: str | None = None,
        limites: Mapping[str, object] | None = None,
    ) -> WorkItem:
        """Edición versionada del alcance desde cualquier estado no terminal (§3.2).

        Conserva la versión anterior: el llamador (puerto de persistencia)
        es responsable de guardar la instancia devuelta como una versión
        *nueva*, sin sobreescribir la anterior. Fuerza rehacer PREPARAR.
        """
        if self.estado in TERMINAL_STATES:
            raise IllegalTransitionError(_AGGREGATE, "change_scope", self.estado)
        return replace(
            self,
            objetivo=self.objetivo if objetivo is None else objetivo,
            entregable=self.entregable if entregable is None else entregable,
            criterio_terminado=(
                self.criterio_terminado if criterio_terminado is None else criterio_terminado
            ),
            limites=self.limites if limites is None else MappingProxyType(dict(limites)),
            fase=WorkItemPhase.PREPARAR,
            version=self.version + 1,
            updated_at=now,
        )

    def reprioritize(self, *, prioridad: int, now: datetime) -> WorkItem:
        """Cambio de ``prioridad``: no es un estado, no versiona (§3.2)."""
        if self.estado in TERMINAL_STATES:
            raise IllegalTransitionError(_AGGREGATE, "reprioritize", self.estado)
        return replace(self, prioridad=prioridad, updated_at=now)


def create_work_item(
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
    """Crear un WorkItem confirmado, en ``PLANNED`` (§3.2: "crear (confirmado)")."""
    return WorkItem(
        work_id=work_id,
        peticion_original=peticion_original,
        objetivo=objetivo,
        contexto_origen=contexto_origen,
        entregable=entregable,
        criterio_terminado=criterio_terminado,
        limites=MappingProxyType(dict(limites)),
        prioridad=prioridad,
        clase=clase,
        estado=WorkItemState.PLANNED,
        fase=WorkItemPhase.PREPARAR,
        plan=plan,
        version=1,
        created_at=now,
        updated_at=now,
    )
