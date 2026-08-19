"""registrar_gasto / resolver_fallo_tecnico: gobierno previo al primer Worker externo.

A5-P4 (incidencia #206): agotar el presupuesto simulado corta el Run y
produce ``NEEDS_DECISION`` con notificación.
A5-P5 (dirección "ninguna otra causa escala"): un fallo técnico corregible
nunca produce ``NEEDS_DECISION`` -termina en ``FAILED_SAFELY``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sirius_engine.domain.budget import Budget
from sirius_engine.domain.escalation import CausaEscalado, Escalada
from sirius_engine.domain.run import RunOutcome, RunState
from sirius_engine.domain.work_item import WorkItemState
from sirius_engine.governance import registrar_gasto, resolver_fallo_tecnico
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeRun, MakeWorkItem

_NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
_DEADLINE = _NOW + timedelta(hours=1)


class _Notificador:
    def __init__(self) -> None:
        self.entregadas: list[Escalada] = []

    def notificar(self, escalada: Escalada) -> None:
        self.entregadas.append(escalada)


def _activar_con_run(
    store: WorkEngineStore,
    *,
    work_id: str,
    run_id: str,
    make_work_item: MakeWorkItem,
    make_run: MakeRun,
) -> None:
    make_work_item(now=_NOW, work_id=work_id, limites={"presupuesto": {"limite": 10.0}})
    store.activate_work_item(work_id, now=_NOW)
    make_run(now=_NOW, deadline=_DEADLINE, run_id=run_id, work_id=work_id)
    store.dispatch_run(run_id, now=_NOW)
    store.confirm_run_running(run_id, now=_NOW)


def test_gasto_que_no_agota_no_corta_nada(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun
) -> None:
    _activar_con_run(
        store,
        work_id="WI-GOV-0001",
        run_id="RUN-GOV-0001",
        make_work_item=make_work_item,
        make_run=make_run,
    )
    resultado = registrar_gasto(
        store, work_id="WI-GOV-0001", presupuesto=Budget(limite=10.0), coste=3.0, now=_NOW
    )
    assert resultado.cortado is False
    assert resultado.presupuesto.consumido == 3.0
    assert resultado.escalada is None

    work_item = store.get_work_item("WI-GOV-0001")
    assert work_item is not None
    assert work_item.estado is WorkItemState.ACTIVE

    run = store.get_run("RUN-GOV-0001")
    assert run is not None
    assert run.estado is RunState.RUNNING


def test_agotar_el_presupuesto_corta_el_run_y_escala_con_notificacion(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun
) -> None:
    """A5-P4: corte determinista al agotarse, con NEEDS_DECISION y notificación."""
    _activar_con_run(
        store,
        work_id="WI-GOV-0002",
        run_id="RUN-GOV-0002",
        make_work_item=make_work_item,
        make_run=make_run,
    )
    notificador = _Notificador()

    resultado = registrar_gasto(
        store,
        work_id="WI-GOV-0002",
        presupuesto=Budget(limite=10.0),
        coste=10.0,
        run_id="RUN-GOV-0002",
        now=_NOW,
        notificar=notificador,
    )
    assert resultado.cortado is True
    assert resultado.presupuesto.agotado is True

    run_cortado = store.get_run("RUN-GOV-0002")
    assert run_cortado is not None
    assert run_cortado.estado is RunState.FINISHED
    assert run_cortado.desenlace is RunOutcome.FAILED

    work_item_escalado = store.get_work_item("WI-GOV-0002")
    assert work_item_escalado is not None
    assert work_item_escalado.estado is WorkItemState.NEEDS_DECISION

    assert resultado.escalada is not None
    assert resultado.escalada.causa is CausaEscalado.GASTO_O_PRESUPUESTO
    assert len(notificador.entregadas) == 1
    assert notificador.entregadas[0] is resultado.escalada


def test_agotar_por_encima_del_limite_tambien_corta(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun
) -> None:
    _activar_con_run(
        store,
        work_id="WI-GOV-0003",
        run_id="RUN-GOV-0003",
        make_work_item=make_work_item,
        make_run=make_run,
    )
    resultado = registrar_gasto(
        store,
        work_id="WI-GOV-0003",
        presupuesto=Budget(limite=10.0),
        coste=15.0,
        run_id="RUN-GOV-0003",
        now=_NOW,
    )
    assert resultado.cortado is True
    work_item = store.get_work_item("WI-GOV-0003")
    assert work_item is not None
    assert work_item.estado is WorkItemState.NEEDS_DECISION


def test_fallo_tecnico_corregible_nunca_escala(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun
) -> None:
    """A5-P5 (dirección negativa): un fallo técnico va a FAILED_SAFELY, nunca a NEEDS_DECISION."""
    _activar_con_run(
        store,
        work_id="WI-GOV-0004",
        run_id="RUN-GOV-0004",
        make_work_item=make_work_item,
        make_run=make_run,
    )
    work_item = resolver_fallo_tecnico(
        store,
        work_id="WI-GOV-0004",
        run_id="RUN-GOV-0004",
        diagnostico="ModuleNotFoundError: dependencia rota en el runner",
        now=_NOW,
    )
    assert work_item.estado is WorkItemState.FAILED_SAFELY

    run = store.get_run("RUN-GOV-0004")
    assert run is not None
    assert run.estado is RunState.FINISHED
    assert run.desenlace is RunOutcome.FAILED
