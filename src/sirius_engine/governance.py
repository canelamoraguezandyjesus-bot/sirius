"""Gobierno previo al primer Worker externo: presupuesto y fallos técnicos.

Dos funciones, cada una con una regla de una sola dirección (arquitectura
§10, requisitos de la incidencia #206):

- :func:`registrar_gasto` es la ÚNICA función de este bloque que actualiza
  el consumo de un :class:`~sirius_engine.domain.budget.Budget`. Si el
  gasto agota el presupuesto, corta de forma determinista: para cualquier
  Run vivo del WorkItem y escala con la causa cerrada
  ``GASTO_O_PRESUPUESTO``, con notificación. No existe ninguna otra vía
  para gastar sin pasar por aquí.
- :func:`resolver_fallo_tecnico` nunca produce una escalada: "los fallos
  técnicos corregibles NO escalan" (arquitectura §10) se resuelve con
  ``FAILED_SAFELY`` y diagnóstico, nunca con ``NEEDS_DECISION``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius_engine.domain.budget import Budget
from sirius_engine.domain.errors import UnknownWorkItemError
from sirius_engine.domain.escalation import CausaEscalado, Escalada, construir_escalada
from sirius_engine.domain.run import LIVE_STATES
from sirius_engine.domain.work_item import WorkItem
from sirius_engine.ports.notification import NotificationPort
from sirius_engine.ports.store import WorkEngineStore


@dataclass(frozen=True, slots=True)
class ResultadoGasto:
    """Lo que produjo registrar un gasto: el presupuesto siempre se actualiza."""

    presupuesto: Budget
    work_item: WorkItem
    cortado: bool
    escalada: Escalada | None


def registrar_gasto(
    store: WorkEngineStore,
    *,
    work_id: str,
    presupuesto: Budget,
    coste: float,
    now: datetime,
    run_id: str | None = None,
    notificar: NotificationPort | None = None,
) -> ResultadoGasto:
    """Registrar un gasto contra ``presupuesto``. Corte determinista al agotarse.

    ``presupuesto`` es el valor que trae el llamador (nunca leído de un
    estado oculto, misma disciplina que ``now``); el nuevo valor, ya con el
    gasto aplicado, se devuelve siempre en ``ResultadoGasto.presupuesto``,
    tanto si corta como si no.
    """
    nuevo_presupuesto = presupuesto.consumir(coste)
    if not nuevo_presupuesto.agotado:
        work_item = store.get_work_item(work_id)
        if work_item is None:
            raise UnknownWorkItemError(work_id)
        return ResultadoGasto(
            presupuesto=nuevo_presupuesto, work_item=work_item, cortado=False, escalada=None
        )

    if run_id is not None:
        run = store.get_run(run_id)
        if run is not None and run.estado in LIVE_STATES:
            store.fail_run(run_id, diagnostico="presupuesto agotado: corte determinista", now=now)

    work_item = store.escalate_work_item(work_id, now=now)
    escalada = construir_escalada(
        work_item,
        causa=CausaEscalado.GASTO_O_PRESUPUESTO,
        motivo=(
            f"presupuesto agotado: consumido {nuevo_presupuesto.consumido} "
            f"de un límite de {nuevo_presupuesto.limite}"
        ),
        ocurrida_en=now,
    )
    if notificar is not None:
        notificar.notificar(escalada)
    return ResultadoGasto(
        presupuesto=nuevo_presupuesto, work_item=work_item, cortado=True, escalada=escalada
    )


def resolver_fallo_tecnico(
    store: WorkEngineStore,
    *,
    work_id: str,
    run_id: str,
    diagnostico: str,
    now: datetime,
) -> WorkItem:
    """Un fallo técnico corregible nunca escala: siempre termina en ``FAILED_SAFELY``.

    No implementa aquí la política completa de reintento/sustitución de
    Worker (arquitectura §10: "reintento, sustitución de Worker o
    FAILED_SAFELY, en ese orden de preferencia") -esos dos primeros pasos
    son primitivas ya existentes del dominio (``Run.retry``,
    ``Run.substitute_worker``, A1) que un futuro supervisor (C1) orquesta
    con conocimiento de perfiles y Workers alternativos, fuera del alcance
    de gobierno de A5. Lo que A5 garantiza es la propiedad negativa: ningún
    fallo técnico, tratado por esta función, produce jamás ``NEEDS_DECISION``.
    """
    run = store.get_run(run_id)
    if run is not None and run.estado in LIVE_STATES:
        store.fail_run(run_id, diagnostico=diagnostico, now=now)
    return store.fail_work_item_safely(work_id, diagnostico=diagnostico, now=now)
