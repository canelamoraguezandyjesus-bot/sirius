"""Barrido de recuperación al arrancar (A2, incidencia #186, arquitectura §3.5).

Requisitos 3 y 4 de la incidencia: tras un reinicio simulado, cada ``Run``
no terminado se reconcilia contra el mundo (incluido el caso de un
desenlace remoto ocurrido mientras el motor estaba "caído"), cada
``WorkItem`` en ``WAITING`` se libera cuando corresponde, y ejecutar el
barrido dos veces seguidas deja el mismo estado que ejecutarlo una vez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pytest

from sirius_engine.domain.errors import IllegalTransitionError
from sirius_engine.domain.events import rebuild_state
from sirius_engine.domain.run import CancellationStatus, Run, RunOutcome, RunState
from sirius_engine.domain.work_item import WorkItemState
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.ports.world import RemoteRunStatus, RunWorldObservation
from sirius_engine.recovery import (
    RecoverySweepResult,
    UnobservedRun,
    _reconcile_run,
    run_recovery_sweep,
)

from .conftest import MakeRun, MakeWorkItem


@dataclass
class FakeRunWorldObserver:
    """Doble de pruebas de ``RunWorldObserver``: devuelve lo que el escenario configure.

    En A2 no existe ninguna implementación real de este puerto -leer el
    mundo real es A3 y bloques posteriores-, así que este doble es la única
    forma de ejercitar el barrido (arquitectura §3.5, alcance permitido de
    la incidencia #186: «en este bloque no hay acceso real a GitHub ni a
    procesos: se sustituye por un doble en las pruebas»).

    Desde H-2 (ADR-053), un escenario de éxito tiene que decir **qué se leyó**:
    ``resultado={}`` es «leí, y el Worker no devolvió campos», mientras que
    ``resultado=None`` es «no pude leer el resultado» y ya no cierra el Run.
    Antes daban lo mismo, y esa era exactamente la confusión del defecto.
    """

    observations: dict[str, RunWorldObservation] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    def check_run(self, run: Run, *, now: datetime) -> RunWorldObservation:
        self.calls.append(run.run_id)
        default = RunWorldObservation(status=RemoteRunStatus.PENDING)
        return self.observations.get(run.run_id, default)


def _waiting_work_item_with_live_run(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    make_run: MakeRun,
    *,
    now: datetime,
    deadline: datetime,
    run_state: RunState,
) -> None:
    """Levantar un ``WorkItem`` en ``WAITING`` con un ``Run`` en el estado pedido.

    Reproduce el escenario real: el motor despachó (y quizá confirmó) un
    paso, entró en espera asíncrona, y "murió" antes de observar el
    desenlace -exactamente el punto donde el barrido de recuperación entra.
    """
    make_work_item(now=now)
    store.activate_work_item("WI-0001", now=now)
    store.dispatch_work_item_async("WI-0001", now=now)
    make_run(now=now, deadline=deadline)
    if run_state in (RunState.DISPATCHED, RunState.RUNNING):
        store.dispatch_run("RUN-0001", now=now)
    if run_state is RunState.RUNNING:
        store.confirm_run_running("RUN-0001", now=now)


def test_barrido_reconcilia_un_run_running_que_tuvo_exito_mientras_el_motor_estaba_caido(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )

    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(
                status=RemoteRunStatus.SUCCEEDED, resultado={"salida": "ok"}
            )
        }
    )

    result = run_recovery_sweep(store, world, now=now)

    assert result == RecoverySweepResult(
        reconciled_run_ids=("RUN-0001",), released_work_item_ids=("WI-0001",)
    )
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.FINISHED
    assert dict(run.resultado or {}) == {"salida": "ok"}
    work_item = store.get_work_item("WI-0001")
    assert work_item is not None
    assert work_item.estado is WorkItemState.ACTIVE


def test_barrido_promueve_un_run_dispatched_hasta_running_antes_de_darlo_por_exitoso(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """El motor murió tras despachar pero antes de confirmar `RUNNING`.

    La recuperación lo cierra igual.
    """
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.DISPATCHED
    )

    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(status=RemoteRunStatus.SUCCEEDED, resultado={})
        }
    )

    result = run_recovery_sweep(store, world, now=now)

    assert result.reconciled_run_ids == ("RUN-0001",)
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.FINISHED
    kinds = [event.kind for event in store.list_events() if event.aggregate_id == "RUN-0001"]
    assert kinds == ["run_prepared", "run_dispatched", "run_confirmed_running", "run_succeeded"]


def test_barrido_promueve_un_run_prepared_hasta_dispatched_antes_de_darlo_por_fallido(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """El motor murió antes de registrar el despacho.

    La recuperación lo cierra igual, como fallido.
    """
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.PREPARED
    )

    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(status=RemoteRunStatus.FAILED, diagnostico="rechazado")
        }
    )

    result = run_recovery_sweep(store, world, now=now)

    assert result.reconciled_run_ids == ("RUN-0001",)
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.FINISHED
    assert run.diagnostico == "rechazado"
    kinds = [event.kind for event in store.list_events() if event.aggregate_id == "RUN-0001"]
    assert kinds == ["run_prepared", "run_dispatched", "run_failed"]
    # Un WorkItem WAITING con su único Run fallado también se libera: el
    # hecho externo (el paso terminó, aunque mal) ya se observó.
    work_item = store.get_work_item("WI-0001")
    assert work_item is not None
    assert work_item.estado is WorkItemState.ACTIVE


def test_barrido_no_actua_sobre_runs_aun_pendientes(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    world = FakeRunWorldObserver()  # sin observaciones configuradas: PENDING por defecto

    result = run_recovery_sweep(store, world, now=now)

    assert result == RecoverySweepResult(reconciled_run_ids=(), released_work_item_ids=())
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.RUNNING
    work_item = store.get_work_item("WI-0001")
    assert work_item is not None
    assert work_item.estado is WorkItemState.WAITING


def test_barrido_no_marca_lost_antes_de_que_venza_el_deadline(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )

    result_temprano = run_recovery_sweep(store, world, now=now)
    assert result_temprano == RecoverySweepResult(reconciled_run_ids=(), released_work_item_ids=())
    assert store.get_run("RUN-0001").estado is RunState.RUNNING  # type: ignore[union-attr]

    result_tras_deadline = run_recovery_sweep(store, world, now=deadline + timedelta(minutes=1))
    assert result_tras_deadline.reconciled_run_ids == ("RUN-0001",)
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.FINISHED


def test_barrido_ejecutado_dos_veces_seguidas_deja_el_mismo_estado(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """Requisito 4: idempotencia del barrido -segunda pasada, ningún evento nuevo."""
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(status=RemoteRunStatus.SUCCEEDED, resultado={})
        }
    )

    primera = run_recovery_sweep(store, world, now=now)
    eventos_tras_primera = tuple(store.list_events())

    segunda = run_recovery_sweep(store, world, now=now)
    eventos_tras_segunda = tuple(store.list_events())

    assert primera.reconciled_run_ids == ("RUN-0001",)
    assert segunda == RecoverySweepResult(reconciled_run_ids=(), released_work_item_ids=())
    assert eventos_tras_segunda == eventos_tras_primera


def test_barrido_ignora_un_workitem_waiting_con_runs_todavia_vivos(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """Dos Runs para el mismo paso asíncrono: solo se libera cuando AMBOS terminaron."""
    deadline = now + timedelta(hours=2)
    make_work_item(now=now)
    store.activate_work_item("WI-0001", now=now)
    store.dispatch_work_item_async("WI-0001", now=now)
    make_run(now=now, deadline=deadline, run_id="RUN-0001")
    make_run(now=now, deadline=deadline, run_id="RUN-0002")
    store.dispatch_run("RUN-0001", now=now)
    store.confirm_run_running("RUN-0001", now=now)
    store.dispatch_run("RUN-0002", now=now)
    store.confirm_run_running("RUN-0002", now=now)

    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(status=RemoteRunStatus.SUCCEEDED, resultado={})
        }
    )

    result = run_recovery_sweep(store, world, now=now)

    assert result.reconciled_run_ids == ("RUN-0001",)
    assert result.released_work_item_ids == ()  # RUN-0002 sigue vivo: no se libera todavía
    work_item = store.get_work_item("WI-0001")
    assert work_item is not None
    assert work_item.estado is WorkItemState.WAITING


# -- Prueba por mutación (ADR-001 §3, requisito 5 de la incidencia #186) -------------


def _sweep_sin_filtro_de_runs_terminados(
    store: WorkEngineStore, world: FakeRunWorldObserver, *, now: datetime
) -> None:
    """Variante MUTADA de :func:`run_recovery_sweep`: sin el filtro de ``Run`` ya ``FINISHED``.

    Reutiliza el mismo ``_reconcile_run`` de la implementación real -la
    mutación es exclusivamente quitar ``if run.estado is RunState.FINISHED:
    continue``-, para aislar qué garantiza la idempotencia: sin ese filtro,
    una segunda pasada vuelve a intentar reconciliar un ``Run`` que ya
    terminó, y el dominio lo rechaza (``IllegalTransitionError``) en vez de
    quedarse callado. Real, `run_recovery_sweep`, es no-operativo en la
    segunda pasada; esta variante revienta.
    """
    state = rebuild_state(store.list_events())
    for run_id in sorted(state.runs):
        run = state.runs[run_id]
        observation = world.check_run(run, now=now)
        _reconcile_run(store, run, observation, now=now)


def test_mutacion_quitar_el_filtro_de_runs_terminados_rompe_la_idempotencia(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(status=RemoteRunStatus.SUCCEEDED, resultado={})
        }
    )

    _sweep_sin_filtro_de_runs_terminados(store, world, now=now)
    assert store.get_run("RUN-0001").estado is RunState.FINISHED  # type: ignore[union-attr]

    with pytest.raises(IllegalTransitionError):
        _sweep_sin_filtro_de_runs_terminados(store, world, now=now)


# --- Rama CANCELLED de `_reconcile_run` --------------------------------------
#
# La cancelación es en dos tiempos (§3.3): `CANCEL` deja el Run vivo con
# `cancellation_status = UNCONFIRMED`, y solo un terminal remoto observado -o
# un aislamiento demostrado- lo cierra. El barrido es justo quien observa ese
# terminal cuando el motor estuvo caído entre los dos tiempos, así que esta
# rama cubre el hueco exacto que la cancelación en dos tiempos abre.
#
# Se prueban las DOS direcciones de su guarda. Solo con el caso positivo,
# borrar `if run.cancellation_status is not CancellationStatus.UNCONFIRMED`
# dejaría la prueba en verde mientras el barrido cerraría como CANCELLED
# cualquier Run que el mundo reportase así, sin que nadie lo hubiera pedido.


def _waiting_work_item_with_cancellation_requested(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    make_run: MakeRun,
    *,
    now: datetime,
    deadline: datetime,
) -> None:
    """Escenario real: se pidió `CANCEL` y el motor murió antes de confirmarlo."""
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    store.request_run_cancellation("RUN-0001", now=now)


def test_barrido_confirma_una_cancelacion_que_el_mundo_ya_dio_por_terminada(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """El desenlace remoto ocurrió mientras el motor estaba caído; el barrido lo cierra."""
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_cancellation_requested(
        store, make_work_item, make_run, now=now, deadline=deadline
    )
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.CANCELLED)}
    )

    result = run_recovery_sweep(store, world, now=now)

    assert result == RecoverySweepResult(
        reconciled_run_ids=("RUN-0001",), released_work_item_ids=("WI-0001",)
    )
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.FINISHED
    assert run.desenlace is RunOutcome.CANCELLED
    assert run.cancellation_status is CancellationStatus.NONE
    kinds = [event.kind for event in store.list_events() if event.aggregate_id == "RUN-0001"]
    assert kinds == [
        "run_prepared",
        "run_dispatched",
        "run_confirmed_running",
        "run_cancellation_requested",
        "run_cancellation_confirmed",
    ]
    # El WorkItem esperaba a ese Run: al terminar, la espera asíncrona se libera.
    work_item = store.get_work_item("WI-0001")
    assert work_item is not None
    assert work_item.estado is WorkItemState.ACTIVE


def test_barrido_no_cierra_como_cancelado_un_run_cuya_cancelacion_nadie_pidio(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """La otra dirección de la guarda: sin `CANCEL` previo, el barrido no actúa.

    Un Run remoto puede reportarse CANCELLED por causas ajenas al motor. Sin
    la cancelación en dos tiempos registrada en el diario, cerrarlo aquí
    inventaría una decisión que nadie tomó -y `confirm_cancelled` la
    rechazaría con `IllegalTransitionError`, perdiendo la pasada entera-.
    """
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.CANCELLED)}
    )
    eventos_antes = tuple(store.list_events())

    result = run_recovery_sweep(store, world, now=now)

    assert result == RecoverySweepResult(reconciled_run_ids=(), released_work_item_ids=())
    assert tuple(store.list_events()) == eventos_antes
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.RUNNING
    assert run.cancellation_status is CancellationStatus.NONE


def test_barrido_de_una_cancelacion_ejecutado_dos_veces_deja_el_mismo_estado(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """Requisito 4, para esta rama: la segunda pasada no anexa ningún evento nuevo."""
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_cancellation_requested(
        store, make_work_item, make_run, now=now, deadline=deadline
    )
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.CANCELLED)}
    )

    primera = run_recovery_sweep(store, world, now=now)
    eventos_tras_primera = tuple(store.list_events())

    segunda = run_recovery_sweep(store, world, now=now)
    eventos_tras_segunda = tuple(store.list_events())

    assert primera.reconciled_run_ids == ("RUN-0001",)
    assert segunda == RecoverySweepResult(reconciled_run_ids=(), released_work_item_ids=())
    assert eventos_tras_segunda == eventos_tras_primera


# --- H-2 (incidencia #214, ADR-053): «no pude observar» no es un desenlace ----
#
# ADR-036 cerró esta familia para el espejo -«una lectura caída no es una
# ausencia»- y reapareció aquí, en el único camino por el que el resultado real
# de un Worker llega al diario: `resultado=observation.resultado or {}` convertía
# «el mundo dijo SUCCEEDED pero no pude leer el resultado» en «éxito con
# resultado vacío», y de paso liberaba el `WorkItem` como si el paso hubiera
# entregado algo.
#
# Se miden las TRES direcciones, no solo la que arregla el defecto:
#
#   1. `SUCCEEDED` sin resultado legible (`resultado=None`) NO cierra el Run.
#   2. `SUCCEEDED` con resultado legible y VACÍO (`{}`) SÍ lo cierra. Sin esta,
#      «no cerrar nunca» pasaría por arreglo -es la lección del «devolver 2
#      siempre» de ADR-036, que habría matado el único caso concluyente-.
#   3. `UNKNOWN` no se confunde con `PENDING`: el barrido no inventa desenlace,
#      pero tampoco se queda callado -lo reporta en `unobserved_runs`-.


def test_barrido_no_cierra_como_exito_un_desenlace_sin_resultado_legible(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """H-2: el mundo dijo `SUCCEEDED`, pero el resultado no se pudo leer.

    Un `Run` cerrado así diría en el diario «este trabajo salió bien y no
    entregó nada», que es una afirmación que nadie hizo.
    """
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(status=RemoteRunStatus.SUCCEEDED, resultado=None)
        }
    )
    eventos_antes = tuple(store.list_events())

    result = run_recovery_sweep(store, world, now=now)

    assert result.reconciled_run_ids == ()
    assert result.released_work_item_ids == ()
    assert tuple(store.list_events()) == eventos_antes
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.RUNNING
    assert run.desenlace is None
    assert run.resultado is None
    # No inventa desenlace, pero tampoco se calla: quien invoca el barrido
    # recibe el Run y el porqué, y puede registrarlo o avisar.
    assert [inobservable.run_id for inobservable in result.unobserved_runs] == ["RUN-0001"]
    assert "resultado" in result.unobserved_runs[0].diagnostico
    # El WorkItem sigue esperando: liberarlo afirmaría que el paso terminó.
    work_item = store.get_work_item("WI-0001")
    assert work_item is not None
    assert work_item.estado is WorkItemState.WAITING


def test_un_resultado_legible_y_vacio_si_cierra_el_run_como_exito(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """Anti-vacua: `{}` es una lectura, no una ausencia de lectura.

    Sin esta prueba, «no cerrar nunca como éxito» pasaría por arreglo. La
    diferencia entera está en `None` (no pude leer) frente a `{}` (leí, y el
    Worker no devolvió campos).
    """
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(status=RemoteRunStatus.SUCCEEDED, resultado={})
        }
    )

    result = run_recovery_sweep(store, world, now=now)

    assert result.reconciled_run_ids == ("RUN-0001",)
    assert result.released_work_item_ids == ("WI-0001",)
    assert result.unobserved_runs == ()
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.FINISHED
    assert run.desenlace is RunOutcome.SUCCEEDED
    assert dict(run.resultado or {}) == {}


def test_barrido_no_inventa_un_desenlace_cuando_el_mundo_no_pudo_observar(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """`UNKNOWN`: la lectura del mundo cayó. No es un hecho sobre el `Run`."""
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(
                status=RemoteRunStatus.UNKNOWN, diagnostico="502 al leer el estado del Run"
            )
        }
    )
    eventos_antes = tuple(store.list_events())

    result = run_recovery_sweep(store, world, now=now)

    assert result.reconciled_run_ids == ()
    assert result.released_work_item_ids == ()
    assert result.unobserved_runs == (
        UnobservedRun(run_id="RUN-0001", diagnostico="502 al leer el estado del Run"),
    )
    assert tuple(store.list_events()) == eventos_antes
    run = store.get_run("RUN-0001")
    assert run is not None
    assert run.estado is RunState.RUNNING
    assert run.desenlace is None
    work_item = store.get_work_item("WI-0001")
    assert work_item is not None
    assert work_item.estado is WorkItemState.WAITING


def test_no_pude_observar_no_es_sigue_vivo_el_barrido_los_distingue(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """Las dos direcciones de la distinción, en la misma pasada.

    `PENDING` es una afirmación -«sigue vivo»- y el barrido calla porque no
    hay nada que hacer todavía. `UNKNOWN` no afirma nada, y callar sería
    tratar un fallo de lectura como un hecho sobre el mundo. Tratar `UNKNOWN`
    como `PENDING` deja este barrido sin nada que reportar.
    """
    deadline = now + timedelta(hours=2)
    make_work_item(now=now)
    store.activate_work_item("WI-0001", now=now)
    store.dispatch_work_item_async("WI-0001", now=now)
    make_run(now=now, deadline=deadline, run_id="RUN-0001")
    make_run(now=now, deadline=deadline, run_id="RUN-0002")
    for run_id in ("RUN-0001", "RUN-0002"):
        store.dispatch_run(run_id, now=now)
        store.confirm_run_running(run_id, now=now)

    world = FakeRunWorldObserver(
        observations={
            "RUN-0001": RunWorldObservation(status=RemoteRunStatus.UNKNOWN),
            "RUN-0002": RunWorldObservation(status=RemoteRunStatus.PENDING),
        }
    )

    result = run_recovery_sweep(store, world, now=now)

    assert result.reconciled_run_ids == ()
    assert [inobservable.run_id for inobservable in result.unobserved_runs] == ["RUN-0001"]
    # Sin `diagnostico` del observador, el barrido pone uno propio: no puede
    # decir POR QUÉ falló la lectura, pero sí que no la hubo.
    assert result.unobserved_runs[0].diagnostico != ""
    assert store.get_run("RUN-0002").estado is RunState.RUNNING  # type: ignore[union-attr]


def test_barrido_repetido_sobre_un_run_inobservable_no_anexa_ningun_evento(
    store: WorkEngineStore, make_work_item: MakeWorkItem, make_run: MakeRun, now: datetime
) -> None:
    """Requisito 4 para esta rama: «como mucho repite una consulta».

    Un `Run` inobservable sigue vivo, así que la siguiente pasada vuelve a
    preguntar por él -y vuelve a reportarlo- sin escribir nada en el diario.
    """
    deadline = now + timedelta(hours=2)
    _waiting_work_item_with_live_run(
        store, make_work_item, make_run, now=now, deadline=deadline, run_state=RunState.RUNNING
    )
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.UNKNOWN)}
    )
    eventos_antes = tuple(store.list_events())

    primera = run_recovery_sweep(store, world, now=now)
    segunda = run_recovery_sweep(store, world, now=now)

    assert primera == segunda
    assert [inobservable.run_id for inobservable in segunda.unobserved_runs] == ["RUN-0001"]
    assert tuple(store.list_events()) == eventos_antes
    assert world.calls == ["RUN-0001", "RUN-0001"]
