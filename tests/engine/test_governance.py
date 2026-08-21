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
from sirius_engine.domain.run import CancellationStatus, RunOutcome, RunState
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
    """A5-P4: corte determinista al agotarse, con NEEDS_DECISION y notificación.

    "Corta" significa pedir la cancelación del Run vivo por el protocolo en
    dos tiempos del dominio (CODEX-002): el Run queda con la cancelación
    pedida y sin confirmar, nunca ``FAILED`` de un plumazo -confirmarlo es
    responsabilidad del Adapter que observa el terminal remoto.
    """
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
        now=_NOW,
        notificar=notificador,
    )
    assert resultado.cortado is True
    assert resultado.presupuesto.agotado is True

    run_cortado = store.get_run("RUN-GOV-0002")
    assert run_cortado is not None
    assert run_cortado.estado is RunState.RUNNING
    assert run_cortado.cancellation_status is CancellationStatus.UNCONFIRMED

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
        now=_NOW,
    )
    assert resultado.cortado is True
    work_item = store.get_work_item("WI-GOV-0003")
    assert work_item is not None
    assert work_item.estado is WorkItemState.NEEDS_DECISION


def test_agotar_el_presupuesto_cancela_todos_los_runs_vivos_del_work_item(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun
) -> None:
    """CODEX-002: no solo el Run que llegó como argumento -TODOS los vivos."""
    make_work_item(now=_NOW, work_id="WI-GOV-0006", limites={"presupuesto": {"limite": 10.0}})
    store.activate_work_item("WI-GOV-0006", now=_NOW)
    make_run(
        now=_NOW,
        deadline=_DEADLINE,
        run_id="RUN-GOV-0006-A",
        work_id="WI-GOV-0006",
        paso="paso-1",
    )
    store.dispatch_run("RUN-GOV-0006-A", now=_NOW)
    store.confirm_run_running("RUN-GOV-0006-A", now=_NOW)
    make_run(
        now=_NOW,
        deadline=_DEADLINE,
        run_id="RUN-GOV-0006-B",
        work_id="WI-GOV-0006",
        paso="paso-2",
    )
    store.dispatch_run("RUN-GOV-0006-B", now=_NOW)

    resultado = registrar_gasto(
        store, work_id="WI-GOV-0006", presupuesto=Budget(limite=10.0), coste=10.0, now=_NOW
    )
    assert resultado.cortado is True

    run_a = store.get_run("RUN-GOV-0006-A")
    run_b = store.get_run("RUN-GOV-0006-B")
    assert run_a is not None and run_a.cancellation_status is CancellationStatus.UNCONFIRMED
    assert run_b is not None and run_b.cancellation_status is CancellationStatus.UNCONFIRMED


def test_agotar_el_presupuesto_no_toca_runs_de_otro_work_item(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun
) -> None:
    """CODEX-002: el corte de un WorkItem nunca cancela Runs ajenos."""
    _activar_con_run(
        store,
        work_id="WI-GOV-0007",
        run_id="RUN-GOV-0007",
        make_work_item=make_work_item,
        make_run=make_run,
    )
    _activar_con_run(
        store,
        work_id="WI-GOV-OTRO-0007",
        run_id="RUN-GOV-OTRO-0007",
        make_work_item=make_work_item,
        make_run=make_run,
    )

    registrar_gasto(
        store, work_id="WI-GOV-0007", presupuesto=Budget(limite=10.0), coste=10.0, now=_NOW
    )

    run_ajeno = store.get_run("RUN-GOV-OTRO-0007")
    assert run_ajeno is not None
    assert run_ajeno.estado is RunState.RUNNING
    assert run_ajeno.cancellation_status is CancellationStatus.NONE


def test_reintentar_registrar_gasto_tras_un_corte_ya_completado_no_falla(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun
) -> None:
    """CODEX-001 (ronda 3): un reintento de ``registrar_gasto`` no debe fallar
    si el corte del intento anterior ya completó -por ejemplo, porque el
    llamador no llegó a enterarse del éxito antes de caer justo después.
    ``cancel_all_live_runs_and_escalate_work_item`` debe devolver el
    WorkItem ya escalado tal cual, sin reintentar una transición
    ``escalate`` que ahora sería ilegal.
    """
    _activar_con_run(
        store,
        work_id="WI-GOV-0008",
        run_id="RUN-GOV-0008",
        make_work_item=make_work_item,
        make_run=make_run,
    )
    primero = registrar_gasto(
        store, work_id="WI-GOV-0008", presupuesto=Budget(limite=10.0), coste=10.0, now=_NOW
    )
    assert primero.cortado is True

    reintento = registrar_gasto(
        store, work_id="WI-GOV-0008", presupuesto=Budget(limite=10.0), coste=10.0, now=_NOW
    )
    assert reintento.cortado is True

    work_item = store.get_work_item("WI-GOV-0008")
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


def test_agotar_el_presupuesto_desde_waiting_corta_y_escala(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun
) -> None:
    """H-3: el corte tiene que funcionar con un Worker asincrono, no solo en ACTIVE.

    ``WAITING`` es el estado en que el motor espera a un Worker externo
    (arquitectura §3.2), y por tanto **el estado en el que se gasta el
    dinero**. Las demas pruebas de este fichero parten todas de ``ACTIVE``,
    que es justo por donde se colo el defecto.
    """
    _activar_con_run(
        store,
        work_id="WI-GOV-0100",
        run_id="RUN-GOV-0100",
        make_work_item=make_work_item,
        make_run=make_run,
    )
    store.dispatch_work_item_async("WI-GOV-0100", now=_NOW)
    en_espera = store.get_work_item("WI-GOV-0100")
    assert en_espera is not None
    assert en_espera.estado is WorkItemState.WAITING

    notificador = _Notificador()
    resultado = registrar_gasto(
        store,
        work_id="WI-GOV-0100",
        presupuesto=Budget(limite=10.0),
        coste=11.0,
        now=_NOW,
        notificar=notificador,
    )

    assert resultado.cortado is True
    assert resultado.presupuesto.consumido == 11.0
    assert resultado.escalada is not None
    assert resultado.escalada.causa is CausaEscalado.GASTO_O_PRESUPUESTO
    assert len(notificador.entregadas) == 1

    work_item = store.get_work_item("WI-GOV-0100")
    assert work_item is not None
    assert work_item.estado is WorkItemState.NEEDS_DECISION

    run = store.get_run("RUN-GOV-0100")
    assert run is not None
    assert run.cancellation_status is CancellationStatus.UNCONFIRMED


def test_un_coste_tardio_sobre_un_trabajo_ya_detenido_no_escala_ni_revienta(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun
) -> None:
    """H-3, cuarta propiedad: decidir explicitamente el estado no escalable.

    Un coste que llega tarde -el Worker ya habia parado- no puede escalar un
    trabajo que ya no esta en curso, pero tampoco puede romper: el
    presupuesto actualizado se devuelve siempre, que es lo que promete el
    docstring de ``registrar_gasto``.
    """
    _activar_con_run(
        store,
        work_id="WI-GOV-0101",
        run_id="RUN-GOV-0101",
        make_work_item=make_work_item,
        make_run=make_run,
    )
    store.fail_work_item_safely("WI-GOV-0101", diagnostico="el Worker no progresa", now=_NOW)

    notificador = _Notificador()
    resultado = registrar_gasto(
        store,
        work_id="WI-GOV-0101",
        presupuesto=Budget(limite=10.0),
        coste=11.0,
        now=_NOW,
        notificar=notificador,
    )

    assert resultado.presupuesto.consumido == 11.0
    assert resultado.escalada is None
    assert notificador.entregadas == []

    work_item = store.get_work_item("WI-GOV-0101")
    assert work_item is not None
    assert work_item.estado is WorkItemState.FAILED_SAFELY

    run = store.get_run("RUN-GOV-0101")
    assert run is not None
    assert run.cancellation_status is CancellationStatus.UNCONFIRMED
