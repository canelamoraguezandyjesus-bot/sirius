"""Política de supervisión de Runs perdidos (C1, incidencia #232, contrato §12.2).

El contrato autoriza al motor a «sondear el estado de sus Runs y actuar sobre
ellos: reintentar, sustituir el Worker o escalar» (§12.2). Este módulo es la
función de decisión, pura y determinista (C1-P5): dado un ``Run`` ya cerrado
como ``LOST`` y cuántos intentos lleva su paso, decide UNA de las tres
acciones -nunca inventa una cuarta, nunca decide sin poder justificarlo con
los campos del propio ``Run``-.

Los umbrales de la política (:class:`SupervisorPolicy`) son valores por
defecto **provisionales**, no cotas medidas: el informe de S3
(``experiments/work_engine_spike_i1/RESULTADOS.md``) declaró NO CONCLUYENTE
tanto la cadencia de sondeo como el umbral de "puede seguir vivo" de un Run en
`queued`. Ninguno de los dos entra aquí como constante -la cota de `LOST`
sigue viniendo de ``Run.deadline`` (arquitectura §3.3), un dato que ya existía
antes de esta incidencia-. Lo único que este módulo decide es QUÉ HACER una
vez que un Run YA está ``LOST``, y ese conteo (cuántas veces se ha
reintentado ya un mismo paso) es un número entero de la propia historia del
Run (``Run.intento``), no una medición de S3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sirius_engine.domain.run import Run
from sirius_engine.domain.worker_ref import WorkerRef


class SupervisionDecision(StrEnum):
    """Las tres acciones que el §12.2 autoriza, y ninguna otra."""

    #: Reintentar el mismo paso, con el mismo Worker: repone el intento que el
    #: consumo (el Run perdido) retiró -misma idea que ``reactivation_labels``
    #: de ``sirius_reconcile.sh``, trasladada al dominio del motor.
    REACTIVATE = "reactivate"
    #: Reintentar con un Worker distinto: el mismo Worker ya perdió el paso
    #: ``policy.max_reactivaciones`` veces seguidas.
    SUBSTITUTE_WORKER = "substitute_worker"
    #: Ausencia real de convergencia (arquitectura §10, causa 7): ni
    #: reintentar ni sustituir progresó. Se para y se pide una decisión.
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class SupervisorPolicy:
    """Umbrales de la política. Valores por defecto marcados como provisionales.

    Ninguno de los dos límites numéricos viene de una medición de S3 -esa
    medición se declaró NO CONCLUYENTE a propósito (ver el docstring del
    módulo)-, así que ambos son configurables y su valor por defecto es un
    criterio de ingeniería conservador (fallar rápido hacia el propietario en
    vez de reintentar indefinidamente), no una cota comprobada.
    """

    #: Cuántos reintentos con el MISMO Worker se conceden antes de sustituirlo.
    #: Provisional: 1.
    max_reactivaciones: int = 1
    #: Cuántas sustituciones de Worker se conceden antes de escalar.
    #: Provisional: 1.
    max_sustituciones: int = 1
    #: El Worker al que sustituir, si la política decide ``SUBSTITUTE_WORKER``.
    #: ``None`` significa "no hay alternativa configurada": la decisión salta
    #: directamente a ``ESCALATE`` en vez de inventar un Worker con el que
    #: sustituir (arquitectura §10: una escalada nunca se evita fabricando
    #: una alternativa que nadie configuró).
    worker_alternativo: WorkerRef | None = None

    def __post_init__(self) -> None:
        if self.max_reactivaciones < 0:
            raise ValueError("SupervisorPolicy.max_reactivaciones no puede ser negativo")
        if self.max_sustituciones < 0:
            raise ValueError("SupervisorPolicy.max_sustituciones no puede ser negativo")


def decidir_politica(run: Run, *, policy: SupervisorPolicy) -> SupervisionDecision:
    """Decidir qué hacer con un ``Run`` ya ``LOST``, a partir de su propio ``intento``.

    Determinista: función pura de ``run.intento`` y ``policy``, sin reloj ni
    E/S (C1-P5). ``run.intento`` ya cuenta, por construcción de
    :func:`~sirius_engine.domain.run.retry`, cuántos intentos lleva este paso
    -reintentar y sustituir Worker son la misma cuenta, porque
    ``substitute_worker`` llama a ``retry`` por dentro-, así que no hace
    falta reconstruir el historial del paso para decidir.
    """
    if run.intento <= policy.max_reactivaciones:
        return SupervisionDecision.REACTIVATE
    sustituciones_ya_hechas = run.intento - policy.max_reactivaciones - 1
    puede_sustituir = (
        policy.worker_alternativo is not None
        and not policy.worker_alternativo.same_profile(run.worker)
        and sustituciones_ya_hechas < policy.max_sustituciones
    )
    if puede_sustituir:
        return SupervisionDecision.SUBSTITUTE_WORKER
    return SupervisionDecision.ESCALATE


@dataclass(frozen=True, slots=True)
class SupervisionEpisode:
    """El episodio completo de una acción del supervisor: qué observó, qué decidió y por qué.

    Es lo que satisface el requisito de la incidencia #232 «toda acción del
    supervisor queda en el diario con el episodio completo». Vive en su
    propio diario append-only (:mod:`sirius_engine.ports.supervisor_journal`)
    en vez de mezclarse con el diario de eventos del ``WorkEngineStore``
    (:mod:`sirius_engine.domain.events`): ese diario modela transiciones de
    ``WorkItem``/``Run`` con su propia instantánea tipada, y no tiene sitio
    para el texto libre de "por qué" que una decisión de política necesita
    explicar. Las transiciones que SÍ mutan ``WorkItem``/``Run``
    (``run_retried``, ``run_worker_substituted``, ``work_item_escalated``...)
    siguen quedando en el diario de siempre, con su propia instantánea.
    """

    run_id: str
    work_id: str
    paso: str
    intento: int
    observado: str
    decision: SupervisionDecision
    motivo: str
    resulting_run_id: str | None
    recorded_at: datetime
