"""Run: one execution attempt of a WorkItem step by a Worker (arquitectura §3.3).

A Run never resurrects: retrying or substituting a Worker always produces a
*new* Run (:func:`retry`, :func:`substitute_worker`), leaving the previous
one untouched. Cancellation is two-phased: :meth:`Run.request_cancel` only
marks the cancellation as unconfirmed; only :meth:`Run.confirm_cancelled`
(after a remote terminal state or demonstrated isolation) closes the Run as
``CANCELLED``. Time is always received as an explicit ``now``/``deadline``
argument — never read from the system clock.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from sirius_engine.domain.errors import DeadlineNotExceededError, IllegalTransitionError

_AGGREGATE = "Run"


class RunState(StrEnum):
    """Ciclo de §3.3: ``PREPARED -> DISPATCHED -> RUNNING -> FINISHED``."""

    PREPARED = "prepared"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    FINISHED = "finished"


#: Only a Run in one of these states can still receive a remote-facing operation.
LIVE_STATES = frozenset({RunState.DISPATCHED, RunState.RUNNING})


class RunOutcome(StrEnum):
    """Desenlaces posibles de un Run ``FINISHED`` (§3.3)."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LOST = "lost"


class CancellationStatus(StrEnum):
    """Estado de la cancelación en dos tiempos (§3.3).

    ``NONE`` mientras no se ha pedido; ``UNCONFIRMED`` desde ``CANCEL``
    hasta que el Adapter observa un estado terminal remoto o un aislamiento
    demostrado. Un Run remoto jamás se considera ``CANCELLED`` mientras siga
    en ``UNCONFIRMED``.
    """

    NONE = "none"
    UNCONFIRMED = "unconfirmed"


@dataclass(frozen=True, slots=True)
class Run:
    """Campos de §3.3."""

    run_id: str
    work_id: str
    paso: str
    worker: str
    work_package: Mapping[str, object]
    intento: int
    estado: RunState
    deadline: datetime
    created_at: datetime
    updated_at: datetime
    desenlace: RunOutcome | None = None
    cancellation_status: CancellationStatus = CancellationStatus.NONE
    ultima_observacion: str | None = None
    observado_en: datetime | None = None
    resultado: Mapping[str, object] | None = None
    diagnostico: str | None = None
    recurso_mutable: str | None = None
    sustituye_a: str | None = None
    motivo_sustitucion: str | None = None

    def _require(self, allowed: frozenset[RunState], operation: str) -> None:
        if self.estado not in allowed:
            raise IllegalTransitionError(_AGGREGATE, operation, self.estado)

    def dispatch(self, *, now: datetime) -> Run:
        """``PREPARED -> DISPATCHED``."""
        self._require(frozenset({RunState.PREPARED}), "dispatch")
        return replace(self, estado=RunState.DISPATCHED, updated_at=now)

    def confirm_running(self, *, now: datetime) -> Run:
        """``DISPATCHED -> RUNNING`` (``STATUS`` confirma que el Worker aceptó)."""
        self._require(frozenset({RunState.DISPATCHED}), "confirm_running")
        return replace(self, estado=RunState.RUNNING, updated_at=now)

    def observe(self, *, observacion: str, now: datetime) -> Run:
        """Registra el último ``STATUS`` conocido, sin cambiar de estado."""
        self._require(LIVE_STATES, "observe")
        return replace(self, ultima_observacion=observacion, observado_en=now, updated_at=now)

    def succeed(self, *, resultado: Mapping[str, object], now: datetime) -> Run:
        """``RUNNING -> FINISHED(SUCCEEDED)``."""
        self._require(frozenset({RunState.RUNNING}), "succeed")
        return replace(
            self,
            estado=RunState.FINISHED,
            desenlace=RunOutcome.SUCCEEDED,
            resultado=MappingProxyType(dict(resultado)),
            updated_at=now,
        )

    def fail(self, *, diagnostico: str, now: datetime) -> Run:
        """``{DISPATCHED,RUNNING} -> FINISHED(FAILED)``."""
        self._require(LIVE_STATES, "fail")
        return replace(
            self,
            estado=RunState.FINISHED,
            desenlace=RunOutcome.FAILED,
            diagnostico=diagnostico,
            updated_at=now,
        )

    def mark_lost(self, *, now: datetime) -> Run:
        """``{DISPATCHED,RUNNING} -> FINISHED(LOST)`` cuando vence la cota absoluta.

        Requiere, de forma independiente: (a) un estado sin ``STATUS``
        concluyente (comprobado como transición ilegal si no se cumple) y
        (b) ``now >= deadline`` (comprobado con
        :class:`~sirius_engine.domain.errors.DeadlineNotExceededError` si no
        se cumple).
        """
        self._require(LIVE_STATES, "mark_lost")
        if now < self.deadline:
            raise DeadlineNotExceededError(self.run_id)
        return replace(self, estado=RunState.FINISHED, desenlace=RunOutcome.LOST, updated_at=now)

    def invalidate_prepared(self, *, now: datetime) -> Run:
        """``PREPARED -> FINISHED(CANCELLED)`` directamente, sin cancelación en dos tiempos.

        Un Run en ``PREPARED`` nunca llegó a ningún Worker remoto, así que no
        hay nada que confirmar (§3.3): el alcance obsoleto se invalida de una
        vez, a diferencia de :meth:`request_cancel`, reservado a Runs ya
        despachados.
        """
        self._require(frozenset({RunState.PREPARED}), "invalidate_prepared")
        return replace(
            self, estado=RunState.FINISHED, desenlace=RunOutcome.CANCELLED, updated_at=now
        )

    def request_cancel(self, *, now: datetime) -> Run:
        """``CANCEL`` produce ``CANCELLATION_UNCONFIRMED`` (el estado del ciclo no cambia)."""
        self._require(LIVE_STATES, "request_cancel")
        if self.cancellation_status is CancellationStatus.UNCONFIRMED:
            raise IllegalTransitionError(_AGGREGATE, "request_cancel", self.estado)
        return replace(self, cancellation_status=CancellationStatus.UNCONFIRMED, updated_at=now)

    def confirm_cancelled(self, *, now: datetime) -> Run:
        """``CANCELLATION_UNCONFIRMED -> FINISHED(CANCELLED)``.

        Solo con terminal remoto o aislamiento demostrado (arquitectura
        §3.3); nunca automáticamente por el mero paso del tiempo.
        """
        self._require(LIVE_STATES, "confirm_cancelled")
        if self.cancellation_status is not CancellationStatus.UNCONFIRMED:
            raise IllegalTransitionError(_AGGREGATE, "confirm_cancelled", self.estado)
        return replace(
            self,
            estado=RunState.FINISHED,
            desenlace=RunOutcome.CANCELLED,
            cancellation_status=CancellationStatus.NONE,
            updated_at=now,
        )

    @property
    def has_unconfirmed_cancellation(self) -> bool:
        """True mientras el Run está vivo con una cancelación pendiente de confirmar."""
        return self.estado in LIVE_STATES and self.cancellation_status is (
            CancellationStatus.UNCONFIRMED
        )


def prepare(
    *,
    run_id: str,
    work_id: str,
    paso: str,
    worker: str,
    work_package: Mapping[str, object],
    intento: int,
    deadline: datetime,
    now: datetime,
    recurso_mutable: str | None = None,
) -> Run:
    """Crear un Run nuevo en ``PREPARED`` (§3.3)."""
    return Run(
        run_id=run_id,
        work_id=work_id,
        paso=paso,
        worker=worker,
        work_package=MappingProxyType(dict(work_package)),
        intento=intento,
        estado=RunState.PREPARED,
        deadline=deadline,
        created_at=now,
        updated_at=now,
        recurso_mutable=recurso_mutable,
    )


def retry(
    previous: Run,
    *,
    run_id: str,
    deadline: datetime,
    now: datetime,
    worker: str | None = None,
    work_package: Mapping[str, object] | None = None,
) -> Run:
    """Reintento: Run nuevo sobre el mismo paso, intento incrementado (§3.2).

    Nunca muta ``previous``. Requiere que el intento anterior haya
    terminado (``FINISHED``): un Run vivo no se reintenta, se cancela o se
    espera primero.
    """
    if previous.estado is not RunState.FINISHED:
        raise IllegalTransitionError(_AGGREGATE, "retry", previous.estado)
    return prepare(
        run_id=run_id,
        work_id=previous.work_id,
        paso=previous.paso,
        worker=worker if worker is not None else previous.worker,
        work_package=work_package if work_package is not None else previous.work_package,
        intento=previous.intento + 1,
        deadline=deadline,
        now=now,
        recurso_mutable=previous.recurso_mutable,
    )


def substitute_worker(
    previous: Run,
    *,
    run_id: str,
    worker: str,
    motivo: str,
    deadline: datetime,
    now: datetime,
    work_package: Mapping[str, object] | None = None,
) -> Run:
    """Sustitución de Worker: reintento con otro Worker, motivo registrado (§3.2).

    Nunca muta ``previous``.
    """
    if worker == previous.worker:
        raise ValueError("worker substitution requires a different worker than the previous run")
    nuevo = retry(
        previous,
        run_id=run_id,
        worker=worker,
        work_package=work_package,
        deadline=deadline,
        now=now,
    )
    return replace(nuevo, sustituye_a=previous.run_id, motivo_sustitucion=motivo)
