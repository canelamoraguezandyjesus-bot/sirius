"""Supervisor de la vía GitHub: detectar, actuar, coordinarse (incidencia #232).

Cubre las cinco pruebas de terminado de la incidencia (C1-P1 a C1-P5) y las
tres mutaciones exigidas por el ADR-001 §3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pytest

from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.adapters.memory_supervisor_journal import InMemorySupervisorJournal
from sirius_engine.domain.errors import DuplicateIdError
from sirius_engine.domain.escalation import CausaEscalado
from sirius_engine.domain.events import rebuild_state
from sirius_engine.domain.run import Run, RunOutcome, RunState
from sirius_engine.domain.supervision import SupervisionDecision, SupervisorPolicy
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, WorkItemState
from sirius_engine.domain.worker_ref import WorkerRef
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.ports.world import RemoteRunStatus, RunWorldObservation
from sirius_engine.recovery import run_recovery_sweep
from sirius_engine.supervisor import (
    SupervisionSweepResult,
    _actuar,
    _bajo_jurisdiccion_del_motor,
    _episodio,
    _run_gobernado_por_el_motor,
    supervise_runs,
)

from .conftest import WORKER_ALTERNATIVO, WORKER_DE_PRUEBA, MakeRun, MakeWorkItem


@dataclass
class FakeRunWorldObserver:
    """Mismo doble que ``test_recovery_sweep.py``: observaciones configuradas por ``run_id``."""

    observations: dict[str, RunWorldObservation] = field(default_factory=dict)

    def check_run(self, run: Run, *, now: datetime) -> RunWorldObservation:
        return self.observations.get(
            run.run_id, RunWorldObservation(status=RemoteRunStatus.PENDING)
        )


def _make_motor_work_item(
    store: WorkEngineStore, *, now: datetime, work_id: str = "WI-0001"
) -> None:
    """Un ``WorkItem`` de autoridad MOTOR (arquitectura §11): la única que el motor supervisa."""
    store.create_work_item(
        work_id=work_id,
        peticion_original="texto literal de la petición",
        objetivo="objetivo normalizado y confirmado",
        contexto_origen=("incidencia:232",),
        entregable="un entregable de prueba",
        criterio_terminado="el entregable existe y pasa sus pruebas",
        limites={"presupuesto_turnos": 10},
        prioridad=1,
        clase=WorkItemClass.INVESTIGACION,
        now=now,
        plan=("paso-1",),
    )


def _dispatch_lost_run(
    store: WorkEngineStore,
    make_run: MakeRun,
    *,
    now: datetime,
    run_id: str = "RUN-0001",
    work_id: str = "WI-0001",
    worker: WorkerRef = WORKER_DE_PRUEBA,
) -> tuple[datetime, datetime]:
    """WorkItem WAITING con un Run RUNNING cuyo deadline ya venció -listo para perderse."""
    store.activate_work_item(work_id, now=now)
    store.dispatch_work_item_async(work_id, now=now)
    deadline = now + timedelta(hours=2)
    make_run(now=now, deadline=deadline, run_id=run_id, work_id=work_id, worker=worker)
    store.dispatch_run(run_id, now=now)
    store.confirm_run_running(run_id, now=now)
    momento_supervision = deadline + timedelta(minutes=1)
    return deadline, momento_supervision


# --- C1-P1: un run matado a mitad se reactiva o se escala, con episodio completo ------


def test_c1_p1_un_run_perdido_se_reactiva_sin_intervencion_humana(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    journal = InMemorySupervisorJournal()

    resultado = supervise_runs(store, world, journal, now=momento)

    assert resultado.recovery.reconciled_run_ids == ("RUN-0001",)
    assert len(resultado.acted) == 1
    outcome = resultado.acted[0]
    assert outcome.decision is SupervisionDecision.REACTIVATE
    assert outcome.resulting_run_id is not None

    nuevo = store.get_run(outcome.resulting_run_id)
    assert nuevo is not None
    assert nuevo.estado is RunState.PREPARED
    assert nuevo.intento == 2
    assert nuevo.paso == "paso-1"

    # El episodio completo: qué observó, qué decidió y por qué.
    episodios = journal.episodes()
    assert len(episodios) == 1
    episodio = episodios[0]
    assert episodio.run_id == "RUN-0001"
    assert episodio.decision is SupervisionDecision.REACTIVATE
    assert "lost" in episodio.observado
    assert episodio.motivo != ""
    assert episodio.resulting_run_id == outcome.resulting_run_id


def test_c1_p1_sin_alternativa_de_worker_un_run_perdido_se_escala(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    journal = InMemorySupervisorJournal()
    # Sin reactivaciones concedidas: el primer atasco ya escala.
    politica = SupervisorPolicy(max_reactivaciones=0, max_sustituciones=0)

    resultado = supervise_runs(store, world, journal, now=momento, policy=politica)

    assert len(resultado.acted) == 1
    outcome = resultado.acted[0]
    assert outcome.decision is SupervisionDecision.ESCALATE
    assert outcome.resulting_run_id is None
    assert outcome.escalada is not None
    assert outcome.escalada.causa is CausaEscalado.AUSENCIA_DE_CONVERGENCIA

    work_item = store.get_work_item("WI-0001")
    assert work_item is not None
    assert work_item.estado is WorkItemState.NEEDS_DECISION

    episodio = journal.episodes()[0]
    assert episodio.decision is SupervisionDecision.ESCALATE
    assert episodio.resulting_run_id is None


def test_c1_p1_agotadas_las_reactivaciones_con_alternativa_configurada_sustituye(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    journal = InMemorySupervisorJournal()
    politica = SupervisorPolicy(
        max_reactivaciones=0, max_sustituciones=1, worker_alternativo=WORKER_ALTERNATIVO
    )

    resultado = supervise_runs(store, world, journal, now=momento, policy=politica)

    outcome = resultado.acted[0]
    assert outcome.decision is SupervisionDecision.SUBSTITUTE_WORKER
    nuevo = store.get_run(outcome.resulting_run_id)  # type: ignore[arg-type]
    assert nuevo is not None
    assert nuevo.worker == WORKER_ALTERNATIVO
    assert nuevo.sustituye_a == "RUN-0001"


# --- C1-P2: no hay carrera con el reconciliador -----------------------------------------


def test_c1_p2_dos_pasadas_sobre_el_mismo_atasco_producen_una_sola_accion(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    journal = InMemorySupervisorJournal()

    primera = supervise_runs(store, world, journal, now=momento)
    segunda = supervise_runs(store, world, journal, now=momento)

    assert len(primera.acted) == 1
    # La segunda pasada NI SIQUIERA intenta actuar sobre RUN-0001: no hay
    # acción nueva y tampoco un intento fallido (`errors`). Sin esta segunda
    # comprobación, un intento fallido -p. ej. `DuplicateIdError` al repetir
    # `retry_run` con el mismo `new_run_id`- también dejaría `acted` vacío, y
    # la prueba no distinguiría "el marcador lo evitó" de "se intentó y
    # falló": justo lo que la mutación de abajo demuestra.
    assert segunda.acted == ()
    assert segunda.errors == ()
    assert len(journal.episodes()) == 1
    # Solo un Run nuevo nació de RUN-0001: intento 1 (perdido) + intento 2 (nuevo).
    assert len(store.list_runs_for_work_item("WI-0001")) == 2


def test_c1_p2_autoridad_incidencia_queda_fuera_de_la_jurisdiccion_del_motor(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    make_run: MakeRun,
    now: datetime,
) -> None:
    """`make_work_item` crea clase PROGRAMACION (autoridad INCIDENCIA, contrato §11).

    El reconciliador (`sirius_reconcile.sh`) es quien vigila esa clase por
    etiquetas de GitHub; el motor no actúa ahí -es la frontera que hace
    imposible la carrera, en vez de leer los marcadores del reconciliador-.
    """
    make_work_item(now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    journal = InMemorySupervisorJournal()

    resultado = supervise_runs(store, world, journal, now=momento)

    assert resultado.acted == ()
    assert resultado.deferred == ("RUN-0001",)
    assert journal.episodes() == ()
    run = store.get_run("RUN-0001")
    assert run is not None and run.estado is RunState.FINISHED  # se reconcilió LOST...
    assert len(store.list_runs_for_work_item("WI-0001")) == 1  # ...pero no se reintentó


def _supervise_runs_sin_marcador_de_idempotencia(
    store: WorkEngineStore,
    observer: FakeRunWorldObserver,
    journal: InMemorySupervisorJournal,
    *,
    now: datetime,
    policy: SupervisorPolicy | None = None,
) -> SupervisionSweepResult:
    """Variante MUTADA de :func:`supervise_runs`: sin ``journal.has_episode``.

    Copia exacta salvo por esa comprobación -misma disciplina que
    ``test_recovery_sweep._sweep_sin_filtro_de_runs_terminados``-: aísla que
    es justo ese marcador el que garantiza la acción única (C1-P2).
    """
    politica = policy if policy is not None else SupervisorPolicy()
    recovery_result = run_recovery_sweep(store, observer, now=now)
    estado = rebuild_state(store.list_events())
    run_ids_perdidos = sorted(
        run_id
        for run_id, run in estado.runs.items()
        if run.estado is RunState.FINISHED and run.desenlace is RunOutcome.LOST
    )
    acted = []
    for run_id in run_ids_perdidos:
        run = store.get_run(run_id)
        if run is None or run.desenlace is not RunOutcome.LOST:
            continue
        work_item = _run_gobernado_por_el_motor(store, run)
        if work_item is None or not _bajo_jurisdiccion_del_motor(work_item):
            continue
        outcome = _actuar(store, run, work_item, policy=politica, now=now, notificar=None)
        if outcome is None:
            continue
        journal.record(_episodio(run, observer, outcome, now=now))
        acted.append(outcome)
    return SupervisionSweepResult(recovery=recovery_result, acted=tuple(acted))


def test_mutacion_quitar_el_marcador_de_idempotencia_permite_doble_accion(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    journal = InMemorySupervisorJournal()

    primera = _supervise_runs_sin_marcador_de_idempotencia(store, world, journal, now=momento)
    assert len(primera.acted) == 1

    # Sin el marcador, la segunda pasada vuelve a intentar la MISMA acción
    # sobre el MISMO Run perdido: el almacén rechaza el `run_id` duplicado
    # que produciría, en vez de dejar pasar una segunda reactivación.
    with pytest.raises(DuplicateIdError):
        _supervise_runs_sin_marcador_de_idempotencia(store, world, journal, now=momento)


# --- C1-P3: un Run ajeno no se toca -------------------------------------------------------


def test_c1_p3_un_run_sin_workitem_propio_no_se_reactiva(
    store: WorkEngineStore, now: datetime
) -> None:
    """Un Run cuyo `work_id` no corresponde a ningún WorkItem del almacén: "ajeno"."""
    deadline = now + timedelta(hours=2)
    store.prepare_run(
        run_id="RUN-AJENO",
        work_id="WI-AJENO",
        paso="paso-1",
        worker=WORKER_DE_PRUEBA,
        work_package={},
        deadline=deadline,
        now=now,
    )
    store.dispatch_run("RUN-AJENO", now=now)
    store.confirm_run_running("RUN-AJENO", now=now)
    momento = deadline + timedelta(minutes=1)
    world = FakeRunWorldObserver(
        observations={"RUN-AJENO": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    journal = InMemorySupervisorJournal()

    resultado = supervise_runs(store, world, journal, now=momento)

    assert resultado.acted == ()
    assert resultado.skipped_foreign == ("RUN-AJENO",)
    assert journal.episodes() == ()
    assert len(store.list_runs_for_work_item("WI-AJENO")) == 1  # nada nuevo nació de él


def test_run_gobernado_por_el_motor_rechaza_un_run_ajeno_directamente(
    store: WorkEngineStore, now: datetime
) -> None:
    deadline = now + timedelta(hours=2)
    run = store.prepare_run(
        run_id="RUN-AJENO",
        work_id="WI-AJENO",
        paso="paso-1",
        worker=WORKER_DE_PRUEBA,
        work_package={},
        deadline=deadline,
        now=now,
    )
    assert _run_gobernado_por_el_motor(store, run) is None


def test_mutacion_quitar_la_comprobacion_de_propiedad_deja_tocar_un_run_ajeno(
    store: WorkEngineStore, now: datetime
) -> None:
    deadline = now + timedelta(hours=2)
    store.prepare_run(
        run_id="RUN-AJENO",
        work_id="WI-AJENO",
        paso="paso-1",
        worker=WORKER_DE_PRUEBA,
        work_package={},
        deadline=deadline,
        now=now,
    )
    store.dispatch_run("RUN-AJENO", now=now)
    store.confirm_run_running("RUN-AJENO", now=now)
    momento = deadline + timedelta(minutes=1)
    world = FakeRunWorldObserver(
        observations={"RUN-AJENO": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )

    recovery_result = run_recovery_sweep(store, world, now=momento)
    perdido = store.get_run("RUN-AJENO")
    assert perdido is not None

    # Mutación: reactivar SIN pasar por `_run_gobernado_por_el_motor`.
    store.retry_run(
        "RUN-AJENO", new_run_id="RUN-AJENO-S2", deadline=momento + timedelta(hours=1), now=momento
    )

    # La mutación SÍ deja tocar el Run ajeno: nace un segundo Run bajo un
    # WorkItem que ni siquiera existe en el almacén del motor.
    assert len(store.list_runs_for_work_item("WI-AJENO")) == 2
    assert store.get_work_item("WI-AJENO") is None
    assert recovery_result.reconciled_run_ids == ("RUN-AJENO",)


# --- C1-P4: el supervisor no crea trabajo -------------------------------------------------


def test_c1_p4_el_supervisor_no_crea_ningun_workitem_nuevo(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    journal = InMemorySupervisorJournal()
    work_ids_antes = set(_todos_los_work_ids(store))

    politica = SupervisorPolicy(max_reactivaciones=0, max_sustituciones=0)  # fuerza ESCALATE
    supervise_runs(store, world, journal, now=momento, policy=politica)

    work_ids_despues = set(_todos_los_work_ids(store))
    assert work_ids_despues == work_ids_antes


def _todos_los_work_ids(store: WorkEngineStore) -> set[str]:
    """Todos los ``work_id`` que aparecen en el diario: la fuente de verdad completa.

    No hay un ``list_work_ids`` en el puerto (``ports/store.py``), así que se
    reconstruye del propio diario en vez de mirar un único ``work_id``
    conocido -mirar solo "WI-0001" no habría detectado un ``WorkItem``
    inventado bajo OTRO id, que es justo lo que C1-P4 prohíbe-.
    """
    return set(rebuild_state(store.list_events()).work_item_versions)


def _escalar_creando_un_workitem_de_seguimiento(
    store: WorkEngineStore, run: Run, work_item: WorkItem, *, now: datetime
) -> None:
    """Variante MUTADA de la rama ESCALATE: además de escalar, crea un WorkItem.

    Copia el único paso que importa (``escalate_work_item``) y añade la
    línea que §12.2 límite 2 prohíbe -"reparar un Run no autoriza a crear
    otro WorkItem"-, con un pretexto plausible ("seguimiento") para que la
    mutación se parezca a una que alguien podría escribir de verdad.
    """
    store.escalate_work_item(work_item.work_id, now=now)
    store.create_work_item(
        work_id=f"{work_item.work_id}-SEGUIMIENTO",
        peticion_original="seguimiento de la escalada",
        objetivo="objetivo",
        contexto_origen=(run.run_id,),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=work_item.clase,
        now=now,
    )


def test_mutacion_permitir_crear_un_workitem_en_la_escalada_rompe_c1_p4(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    # Mismo precondición que deja `run_recovery_sweep` real: el paso terminó
    # (LOST), así que la espera asíncrona ya se liberó a ACTIVE.
    store.observe_work_item_external_fact("WI-0001", now=momento)
    work_ids_antes = set(_todos_los_work_ids(store))
    run = store.get_run("RUN-0001")
    work_item = store.get_work_item("WI-0001")
    assert run is not None and work_item is not None

    _escalar_creando_un_workitem_de_seguimiento(store, run, work_item, now=momento)

    work_ids_despues = set(_todos_los_work_ids(store))
    # La propiedad que C1-P4 exige -el conjunto de WorkItems no crece- SÍ
    # cambia con la mutación: por eso la prueba real de arriba, que la
    # comprueba sobre el código sin mutar, caería si alguien reintrodujera
    # esta línea.
    assert work_ids_despues != work_ids_antes


# --- C1-P5: determinismo -------------------------------------------------------------------


def test_c1_p5_dos_almacenes_identicos_producen_la_misma_decision(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    """Mismas observaciones guardadas -> mismo `now` -> misma decisión, sin reloj real."""
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )

    resultado_1 = supervise_runs(store, world, InMemorySupervisorJournal(), now=momento)

    # Un segundo almacén, construido con la MISMA secuencia de operaciones.
    store_2 = InMemoryWorkEngineStore()
    _make_motor_work_item(store_2, now=now)
    store_2.activate_work_item("WI-0001", now=now)
    store_2.dispatch_work_item_async("WI-0001", now=now)
    store_2.prepare_run(
        run_id="RUN-0001",
        work_id="WI-0001",
        paso="paso-1",
        worker=WORKER_DE_PRUEBA,
        work_package={"instrucciones": "instantánea de prueba"},
        deadline=_deadline,
        now=now,
    )
    store_2.dispatch_run("RUN-0001", now=now)
    store_2.confirm_run_running("RUN-0001", now=now)

    resultado_2 = supervise_runs(store_2, world, InMemorySupervisorJournal(), now=momento)

    assert [outcome.decision for outcome in resultado_1.acted] == [
        outcome.decision for outcome in resultado_2.acted
    ]
    assert [outcome.motivo for outcome in resultado_1.acted] == [
        outcome.motivo for outcome in resultado_2.acted
    ]
