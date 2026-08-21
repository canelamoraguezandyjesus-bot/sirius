"""Diario del supervisor durable (H-10, incidencia #238, ADR-061).

Cubre las cinco pruebas de terminado de la incidencia (H10-P1 a H10-P5) y las
tres mutaciones exigidas por el ADR-001 §3. Reutiliza los dobles y ayudantes
ya definidos en ``test_supervisor.py`` -no se duplican- para que las pruebas
de aquí ejerzan exactamente el mismo camino de producción
(:func:`sirius_engine.supervisor.supervise_runs`), con la única diferencia de
que el diario se "reabre" (una instancia nueva de
:class:`~sirius_engine.adapters.durable.supervisor_journal.DurableSupervisorJournal`
sobre el MISMO fichero) para simular un reinicio del proceso.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sirius_engine.adapters.durable.journal import append_durably, replay
from sirius_engine.adapters.durable.supervisor_journal import (
    _KIND_EPISODE,
    _KIND_PENDING_RECORDED,
    DurableSupervisorJournal,
    _episode_from_record,
)
from sirius_engine.adapters.memory_supervisor_journal import InMemorySupervisorJournal
from sirius_engine.domain.supervision import (
    SupervisionDecision,
    SupervisionEpisode,
    SupervisorPolicy,
)
from sirius_engine.domain.work_item import WorkItemState
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.ports.world import RemoteRunStatus, RunWorldObservation
from sirius_engine.recovery import run_recovery_sweep
from sirius_engine.supervisor import _actuar, supervise_runs

from .conftest import MakeRun
from .test_supervisor import (
    FakeRunWorldObserver,
    NotificadorQueFallaLaPrimeraVez,
    _dispatch_lost_run,
    _make_motor_work_item,
)

# --- H10-P1, H10-P2, H10-P3: sobrevive, no se pierde, no se duplica ----------------------


def test_h10_p1_p2_p3_la_marca_sobrevive_no_se_pierde_y_no_se_duplica(
    store: WorkEngineStore, make_run: MakeRun, now: datetime, tmp_path: Path
) -> None:
    """Encadena H10-P1 (sobrevive), H10-P3 (se puede leer) y H10-P2 (no se duplica).

    Primera pasada: la notificación falla SIEMPRE -aproxima "el proceso muere
    antes de notificar", porque la marca ya quedó durable ANTES de intentar
    la entrega (CODEX-004, `supervisor._escalar`), pase lo que pase después.
    """
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    politica = SupervisorPolicy(max_reactivaciones=0, max_sustituciones=0)  # fuerza ESCALATE
    journal_path = tmp_path / "diario-supervisor.jsonl"
    journal = DurableSupervisorJournal(journal_path)
    notificador_que_siempre_falla = NotificadorQueFallaLaPrimeraVez(fallar_hasta=999)

    primera = supervise_runs(
        store, world, journal, now=momento, policy=politica, notificar=notificador_que_siempre_falla
    )
    assert primera.acted == ()
    assert len(primera.errors) == 1
    assert journal.episodes() == ()

    # H10-P1: "reiniciar" -una instancia nueva sobre el MISMO fichero- y la
    # marca sigue ahí, correlacionada con el `run_id` que la causó.
    reabierto_1 = DurableSupervisorJournal(journal_path)
    assert reabierto_1.pending_escalation_run_id("WI-0001") == "RUN-0001"
    assert reabierto_1.has_episode("RUN-0001") is False

    # Segunda pasada tras reabrir: la notificación esta vez SÍ llega.
    notificador_que_entrega = NotificadorQueFallaLaPrimeraVez(fallar_hasta=0)
    segunda = supervise_runs(
        store, world, reabierto_1, now=momento, policy=politica, notificar=notificador_que_entrega
    )
    assert len(segunda.acted) == 1
    assert segunda.acted[0].decision is SupervisionDecision.ESCALATE
    assert len(notificador_que_entrega.entregas) == 1
    assert len(reabierto_1.episodes()) == 1

    # H10-P3: reabrir de nuevo, el episodio registrado antes del reinicio se
    # puede leer después.
    reabierto_2 = DurableSupervisorJournal(journal_path)
    assert len(reabierto_2.episodes()) == 1
    assert reabierto_2.episodes()[0].run_id == "RUN-0001"
    assert reabierto_2.has_episode("RUN-0001") is True
    assert reabierto_2.pending_escalation_run_id("WI-0001") is None  # ya se limpió

    # H10-P2: una TERCERA pasada tras el segundo reinicio no reenvía el aviso.
    tercera = supervise_runs(
        store, world, reabierto_2, now=momento, policy=politica, notificar=notificador_que_entrega
    )
    assert tercera.acted == ()
    assert len(notificador_que_entrega.entregas) == 1  # sigue siendo UNA sola entrega
    assert len(reabierto_2.episodes()) == 1


# --- H10-P4: la correlación es real, incluso tras un reinicio ----------------------------


def test_h10_p4_dos_runs_perdidos_cada_marca_apunta_al_suyo_tras_reabrir(
    store: WorkEngineStore, make_run: MakeRun, now: datetime, tmp_path: Path
) -> None:
    _make_motor_work_item(store, now=now)
    store.activate_work_item("WI-0001", now=now)
    store.dispatch_work_item_async("WI-0001", now=now)
    deadline = now + timedelta(hours=2)
    for run_id, paso in (("RUN-A", "paso-1"), ("RUN-B", "paso-2")):
        make_run(now=now, deadline=deadline, run_id=run_id, work_id="WI-0001", paso=paso)
        store.dispatch_run(run_id, now=now)
        store.confirm_run_running(run_id, now=now)
    momento = deadline + timedelta(minutes=1)
    world = FakeRunWorldObserver(
        observations={
            "RUN-A": RunWorldObservation(status=RemoteRunStatus.LOST),
            "RUN-B": RunWorldObservation(status=RemoteRunStatus.LOST),
        }
    )
    politica = SupervisorPolicy(max_reactivaciones=0, max_sustituciones=0)  # fuerza ESCALATE
    journal_path = tmp_path / "diario-supervisor.jsonl"
    journal = DurableSupervisorJournal(journal_path)
    notificador = NotificadorQueFallaLaPrimeraVez(fallar_hasta=0)  # nunca falla

    primera = supervise_runs(
        store, world, journal, now=momento, policy=politica, notificar=notificador
    )
    assert len(primera.acted) == 1
    assert primera.acted[0].run_id == "RUN-A"
    assert primera.deferred == ("RUN-B",)
    assert len(notificador.entregas) == 1

    # "Reinicio": la marca de RUN-A ya se limpió (se entregó); RUN-B nunca
    # tuvo ninguna -sigue sin episodio propio.
    reabierto = DurableSupervisorJournal(journal_path)
    assert reabierto.pending_escalation_run_id("WI-0001") is None
    assert reabierto.has_episode("RUN-A") is True
    assert reabierto.has_episode("RUN-B") is False

    # Una pasada más tras reabrir: RUN-B se difiere -no "resuelto por
    # contagio" de la escalada de RUN-A que ya se atendió.
    tercera = supervise_runs(
        store, world, reabierto, now=momento, policy=politica, notificar=notificador
    )
    assert tercera.acted == ()
    assert tercera.deferred == ("RUN-B",)
    assert reabierto.has_episode("RUN-B") is False
    assert len(notificador.entregas) == 1  # ninguna entrega nueva


# --- H10-P5: el adapter en memoria sigue en verde, mismo contrato ------------------------


def test_h10_p5_el_diario_en_memoria_y_el_durable_comparten_el_mismo_comportamiento_basico(
    tmp_path: Path,
) -> None:
    """No demuestra C1-P1..P5 de nuevo -eso lo sigue haciendo `test_supervisor.py` sin
    modificar-, solo que ambas implementaciones satisfacen el mismo contrato básico del
    puerto de forma idéntica, con y sin persistencia.
    """
    episodio = SupervisionEpisode(
        run_id="RUN-CONTRATO",
        work_id="WI-CONTRATO",
        paso="paso-1",
        intento=1,
        observado="lost",
        decision=SupervisionDecision.REACTIVATE,
        motivo="motivo de prueba",
        resulting_run_id="RUN-CONTRATO-S2",
        recorded_at=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
    )

    en_memoria = InMemorySupervisorJournal()
    durable = DurableSupervisorJournal(tmp_path / "diario-contrato.jsonl")

    for diario in (en_memoria, durable):
        assert diario.has_episode("RUN-CONTRATO") is False
        diario.record(episodio)
        assert diario.has_episode("RUN-CONTRATO") is True
        assert diario.episodes() == (episodio,)
        assert diario.pending_escalation_run_id("WI-CONTRATO") is None
        diario.record_pending_escalation("RUN-CONTRATO", "WI-CONTRATO")
        assert diario.pending_escalation_run_id("WI-CONTRATO") == "RUN-CONTRATO"
        diario.clear_pending_escalation("WI-CONTRATO")
        assert diario.pending_escalation_run_id("WI-CONTRATO") is None


# --- Mutación 1 (ADR-001 §3): la marca no se persiste -> cae H10-P1 ----------------------


class _DiarioMutadoSinPersistirLaMarca(DurableSupervisorJournal):
    """Mutación: `record_pending_escalation` deja de anexar al diario -solo memoria."""

    def record_pending_escalation(self, run_id: str, work_id: str) -> None:
        self._escaladas_pendientes[work_id] = run_id  # sin `append_durably`: no sobrevive


def test_mutacion_no_persistir_la_marca_hace_caer_h10_p1(tmp_path: Path) -> None:
    journal_path = tmp_path / "diario-mutado.jsonl"
    mutado = _DiarioMutadoSinPersistirLaMarca(journal_path)
    mutado.record_pending_escalation("RUN-X", "WI-X")
    assert mutado.pending_escalation_run_id("WI-X") == "RUN-X"  # en memoria sí está

    # H10-P1 exige que sobreviva a un reinicio: aquí NO sobrevive -la mutación
    # hace caer justo la propiedad que la prueba real comprueba.
    reabierto_tras_mutacion = DurableSupervisorJournal(journal_path)
    assert reabierto_tras_mutacion.pending_escalation_run_id("WI-X") is None

    # Implementación real, sin mutar: sí sobrevive (contraste explícito).
    journal_path_real = tmp_path / "diario-real.jsonl"
    real = DurableSupervisorJournal(journal_path_real)
    real.record_pending_escalation("RUN-X", "WI-X")
    reabierto_real = DurableSupervisorJournal(journal_path_real)
    assert reabierto_real.pending_escalation_run_id("WI-X") == "RUN-X"


# --- Mutación 2 (ADR-001 §3): se pierde la correlación con run_id -> cae H10-P4 ----------


class _DiarioMutadoSinCorrelacionDeRunId(DurableSupervisorJournal):
    """Mutación: la marca se persiste sin el `run_id` que la causó -degradada a `None`."""

    def record_pending_escalation(self, run_id: str, work_id: str) -> None:
        record: Mapping[str, Any] = {
            "kind": _KIND_PENDING_RECORDED,
            "work_id": work_id,
            "run_id": None,  # CORRECTO sería `run_id`: aquí se descarta a propósito.
        }
        append_durably(self._journal_path, record)
        self._escaladas_pendientes[work_id] = run_id


def test_mutacion_perder_la_correlacion_de_run_id_hace_caer_h10_p4(tmp_path: Path) -> None:
    journal_path = tmp_path / "diario-mutado.jsonl"
    mutado = _DiarioMutadoSinCorrelacionDeRunId(journal_path)
    mutado.record_pending_escalation("RUN-A", "WI-X")
    assert mutado.pending_escalation_run_id("WI-X") == "RUN-A"  # en memoria, antes de reabrir

    # H10-P4 exige que la marca siga apuntando a SU run_id tras un reinicio.
    # Con la mutación, la correlación se pierde -no hay forma de distinguir a
    # RUN-A del `None` que quedó persistido, así que ni siquiera el propio
    # RUN-A vuelve a reconocerse tras reabrir.
    reabierto_tras_mutacion = DurableSupervisorJournal(journal_path)
    assert reabierto_tras_mutacion.pending_escalation_run_id("WI-X") != "RUN-A"

    # Implementación real: la correlación sí sobrevive intacta.
    journal_path_real = tmp_path / "diario-real.jsonl"
    real = DurableSupervisorJournal(journal_path_real)
    real.record_pending_escalation("RUN-A", "WI-X")
    reabierto_real = DurableSupervisorJournal(journal_path_real)
    assert reabierto_real.pending_escalation_run_id("WI-X") == "RUN-A"


# --- Mutación 3 (ADR-001 §3): se reenvía el aviso al reabrir -> cae H10-P2 ---------------


class _DiarioMutadoQueIgnoraLaLimpiezaAlReabrir(DurableSupervisorJournal):
    """Mutación: `_load` ignora `pending_escalation_cleared` -una escalada YA entregada
    antes del reinicio vuelve a parecer pendiente al reabrir."""

    def _load(self) -> None:
        for record in replay(self._journal_path).valid_records:
            kind = record["kind"]
            if kind == _KIND_EPISODE:
                self._absorb_episode(_episode_from_record(record))
            elif kind == _KIND_PENDING_RECORDED:
                self._escaladas_pendientes[record["work_id"]] = record["run_id"]
            # deliberadamente NO procesa _KIND_PENDING_CLEARED.


def test_mutacion_ignorar_la_limpieza_al_reabrir_hace_caer_h10_p2(
    store: WorkEngineStore, make_run: MakeRun, now: datetime, tmp_path: Path
) -> None:
    """Reproduce el hueco exacto: el proceso muere DESPUÉS de que `_escalar` limpie la
    marca (entrega confirmada) pero ANTES de que `supervise_runs` registre el episodio
    -la única ventana en la que "ya se entregó" y "ya consta en el diario" no coinciden.
    """
    _make_motor_work_item(store, now=now)
    _deadline, momento = _dispatch_lost_run(store, make_run, now=now)
    world = FakeRunWorldObserver(
        observations={"RUN-0001": RunWorldObservation(status=RemoteRunStatus.LOST)}
    )
    politica = SupervisorPolicy(max_reactivaciones=0, max_sustituciones=0)  # fuerza ESCALATE
    journal_path = tmp_path / "diario-supervisor.jsonl"
    journal = DurableSupervisorJournal(journal_path)
    notificador = NotificadorQueFallaLaPrimeraVez(fallar_hasta=0)  # nunca falla

    # Recuperar el Run a LOST (lo que `supervise_runs` hace normalmente) y
    # actuar directamente con `_actuar` -sin la llamada a `journal.record`
    # que `supervise_runs` haría justo DESPUÉS-: simula la caída exacta.
    run_recovery_sweep(store, world, now=momento)
    run = store.get_run("RUN-0001")
    work_item = store.get_work_item("WI-0001")
    assert run is not None and work_item is not None

    outcome = _actuar(
        store, run, work_item, policy=politica, now=momento, notificar=notificador, journal=journal
    )
    assert outcome is not None
    assert len(notificador.entregas) == 1  # la entrega SÍ ocurrió...
    assert journal.episodes() == ()  # ...pero el episodio nunca llegó a registrarse
    assert store.get_work_item("WI-0001").estado is WorkItemState.NEEDS_DECISION  # type: ignore[union-attr]

    # Implementación real: reabrir procesa la limpieza -> no reenvía.
    reabierto_real = DurableSupervisorJournal(journal_path)
    assert reabierto_real.pending_escalation_run_id("WI-0001") is None
    segunda_real = supervise_runs(
        store, world, reabierto_real, now=momento, policy=politica, notificar=notificador
    )
    assert segunda_real.acted == ()
    assert segunda_real.deferred == ("RUN-0001",)
    assert len(notificador.entregas) == 1  # sigue siendo UNA sola entrega

    # Variante MUTADA: reabrir con la clase que ignora la limpieza -> la marca
    # parece seguir pendiente -> H10-P2 cae, se reenvía el aviso.
    reabierto_mutado = _DiarioMutadoQueIgnoraLaLimpiezaAlReabrir(journal_path)
    assert reabierto_mutado.pending_escalation_run_id("WI-0001") == "RUN-0001"
    segunda_mutada = supervise_runs(
        store, world, reabierto_mutado, now=momento, policy=politica, notificar=notificador
    )
    assert len(segunda_mutada.acted) == 1  # la mutación SÍ vuelve a actuar...
    assert len(notificador.entregas) == 2  # ...y reenvía el aviso: exactamente lo prohibido.
