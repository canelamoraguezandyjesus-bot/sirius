"""Matriz punto-de-muerte x resultado, reproducida contra el camino de producción (A2, #186).

Requisito 2 de la incidencia #186: la matriz punto-de-muerte x resultado que
S1 (incidencia #182, ADR-026) validó contra `experiments/work_engine_spike_i3/`
se convierte aquí en prueba estable contra el código de producción
(`src/sirius_engine/adapters/durable/`), con el MISMO resultado exacto. No
sustituye a `tests/engine/test_spike_i3_durability.py` -esa sigue siendo la
evidencia fechada de S1 (no se borra `experiments/`, arquitectura de la
incidencia)-; esta es su promoción.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sirius_engine.adapters.durable.entity_codec import run_from_dict, run_to_dict
from sirius_engine.adapters.durable.journal import (
    DirectorySyncError,
    InternalCorruptionError,
    KillPoint,
    append_durably,
    build_line,
    canonical_bytes,
    recover_invalid_tail,
    replay,
)
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.domain.budget import Budget
from sirius_engine.domain.events import AggregateType
from sirius_engine.domain.run import CancellationStatus, Run
from sirius_engine.domain.run import prepare as prepare_run
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, WorkItemState
from sirius_engine.domain.worker_ref import WorkerRef
from sirius_engine.governance import registrar_gasto
from sirius_engine.ports.store import WorkEngineStore

_REPO_ROOT = Path(__file__).resolve().parents[2]
_NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
#: Adapter + perfil versionado, sin modelo ni runtime: lo que se conoce
#: antes de que ningún Worker acepte el encargo (§3.3, ADR-054).
_WORKER = WorkerRef(adapter="worker-de-prueba", perfil_ref="perfiles/prueba", perfil_version=1)
_WORKER_EXTERNO = WorkerRef(
    adapter="worker-externo", perfil_ref="perfiles/prueba", perfil_version=1
)


def _sample_run() -> Run:
    return prepare_run(
        run_id="RUN-A2-0001",
        work_id="WI-A2-0001",
        paso="paso-1",
        worker=_WORKER,
        work_package={"instrucciones": "ejecutar paso 1"},
        intento=1,
        deadline=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
        now=_NOW,
    )


def _sample_record(*, sequence: int = 1, idempotency_key: str | None = None) -> dict[str, Any]:
    run = _sample_run()
    return {
        "sequence": sequence,
        "occurred_at": _NOW.isoformat(),
        "aggregate_type": AggregateType.RUN.value,
        "aggregate_id": run.run_id,
        "kind": "run_prepared",
        "entity": run_to_dict(run),
        "idempotency_key": idempotency_key,
    }


def _run_writer_subprocess(
    journal_path: Path,
    record: Mapping[str, Any],
    kill_at: KillPoint | None,
    tmp_path: Path,
) -> subprocess.CompletedProcess[bytes]:
    record_path = tmp_path / "registro-entrada.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    kill_at_arg = "-" if kill_at is None else kill_at.value
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.engine._durable_writer_process",
            str(journal_path),
            str(record_path),
            kill_at_arg,
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        timeout=30,
    )


#: Igual que en S1 (ADR-026, `RESULTADOS.md`): "ocurrio_una_vez" en los tres
#: últimos puntos es el límite conocido heredado -`kill -9` no vacía la
#: caché de páginas del kernel- documentado también en ADR-029 §2.
EXPECTED_OUTCOME = {
    KillPoint.BEFORE_OPEN: "no_ocurrio",
    KillPoint.AFTER_OPEN_BEFORE_WRITE: "no_ocurrio",
    KillPoint.MID_WRITE_TORN: "no_ocurrio",
    KillPoint.AFTER_WRITE_BEFORE_FSYNC: "ocurrio_una_vez",
    KillPoint.AFTER_FSYNC_BEFORE_CLOSE: "ocurrio_una_vez",
    KillPoint.AFTER_CLOSE: "ocurrio_una_vez",
}


@pytest.mark.parametrize("kill_at", tuple(KillPoint), ids=lambda kp: kp.value)
def test_matriz_punto_de_muerte_por_resultado_produccion(
    kill_at: KillPoint, tmp_path: Path
) -> None:
    journal_path = tmp_path / "diario.jsonl"
    record = _sample_record()

    completed = _run_writer_subprocess(journal_path, record, kill_at, tmp_path)

    assert completed.returncode == -9, (
        f"el subproceso debía morir por SIGKILL exactamente en {kill_at.value}; "
        f"returncode={completed.returncode!r} stderr={completed.stderr!r}"
    )

    result = replay(journal_path)
    assert len(result.valid_records) in (0, 1), (
        f"nunca a medias ni dos veces; matar en {kill_at.value} produjo "
        f"{len(result.valid_records)} registros válidos"
    )
    outcome = "no_ocurrio" if len(result.valid_records) == 0 else "ocurrio_una_vez"
    assert outcome == EXPECTED_OUTCOME[kill_at], (
        f"punto {kill_at.value}: se esperaba {EXPECTED_OUTCOME[kill_at]}, salió {outcome}"
    )
    if outcome == "ocurrio_una_vez":
        assert result.valid_records[0]["aggregate_id"] == record["aggregate_id"]
        run_reconstruido = run_from_dict(result.valid_records[0]["entity"])
        assert run_reconstruido == _sample_run()


def test_reintento_tras_reinicio_no_duplica_por_idempotencia(tmp_path: Path) -> None:
    journal_path = tmp_path / "diario.jsonl"

    store_antes_de_reiniciar = DurableWorkEngineStore(journal_path)
    creado = store_antes_de_reiniciar.create_work_item(
        work_id="WI-IDEMP-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=("incidencia:186",),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
        idempotency_key="req-crear-WI-IDEMP-0001",
    )

    # "Reinicio": una instancia nueva del almacén sobre el MISMO diario.
    store_tras_reiniciar = DurableWorkEngineStore(journal_path)
    reintentado = store_tras_reiniciar.create_work_item(
        work_id="WI-IDEMP-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=("incidencia:186",),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
        idempotency_key="req-crear-WI-IDEMP-0001",
    )

    assert reintentado == creado
    assert len(store_tras_reiniciar.list_events()) == 1
    assert len(replay(journal_path).valid_records) == 1


def test_fallo_de_fsync_de_directorio_tras_persistir_no_duplica_al_reintentar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CODEX-001: reproduce el hallazgo exacto -fallar únicamente la SEGUNDA llamada a
    ``os.fsync`` (la del directorio, tras la del propio fichero) deja el registro
    completo en disco pero el evento sin absorber en memoria. Con la corrección, el
    reintento con la MISMA instancia y la MISMA clave no debe duplicar el registro.
    """
    journal_path = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(journal_path)

    real_fsync = os.fsync
    llamadas = 0

    def fsync_que_falla_la_segunda_vez(fd: int) -> None:
        nonlocal llamadas
        llamadas += 1
        if llamadas == 2:
            raise OSError("fallo simulado de fsync de directorio")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync_que_falla_la_segunda_vez)

    with pytest.raises(DirectorySyncError):
        store.create_work_item(
            work_id="WI-CODEX001-0001",
            peticion_original="texto literal",
            objetivo="objetivo",
            contexto_origen=(),
            entregable="entregable",
            criterio_terminado="criterio",
            limites={},
            prioridad=1,
            clase=WorkItemClass.PROGRAMACION,
            now=_NOW,
            idempotency_key="req-crear-WI-CODEX001-0001",
        )

    # El registro ya está completo en el diario -su fsync de fichero tuvo
    # éxito-, aunque falló sincronizar el directorio. Antes de la corrección,
    # el índice en memoria no reflejaba este evento pese a estar ya durable.
    assert len(replay(journal_path).valid_records) == 1
    creado = store.get_work_item("WI-CODEX001-0001")
    assert creado is not None

    monkeypatch.setattr(os, "fsync", real_fsync)

    reintentado = store.create_work_item(
        work_id="WI-CODEX001-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
        idempotency_key="req-crear-WI-CODEX001-0001",
    )

    assert reintentado == creado
    assert len(store.list_events()) == 1
    assert len(replay(journal_path).valid_records) == 1


def test_reintento_de_una_transicion_tras_reinicio_no_duplica_ni_lanza(
    tmp_path: Path,
) -> None:
    """CLAUDE-A2-IDEMP-01 / CODEX-002: reintentar una TRANSICIÓN, no solo una creación.

    ``test_reintento_tras_reinicio_no_duplica_por_idempotencia`` solo ejercita
    ``create_work_item``. Este caso reproduce exactamente el defecto
    reportado: activar un WorkItem con una ``idempotency_key``, "reiniciar" el
    almacén, y reintentar la MISMA activación con la MISMA clave. Antes de la
    corrección, el chequeo de idempotencia ocurría DESPUÉS de evaluar
    ``current.activate(...)`` -sobre un estado ya avanzado a ACTIVE- y el
    dominio lanzaba ``IllegalTransitionError`` en vez de devolver el resultado
    ya anexado.
    """
    journal_path = tmp_path / "diario.jsonl"

    store_antes_de_reiniciar = DurableWorkEngineStore(journal_path)
    store_antes_de_reiniciar.create_work_item(
        work_id="WI-IDEMP-TRANS-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=("incidencia:186",),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    activado = store_antes_de_reiniciar.activate_work_item(
        "WI-IDEMP-TRANS-0001", now=_NOW, idempotency_key="req-activar-WI-IDEMP-TRANS-0001"
    )

    # "Reinicio": una instancia nueva del almacén sobre el MISMO diario.
    store_tras_reiniciar = DurableWorkEngineStore(journal_path)
    reintentado = store_tras_reiniciar.activate_work_item(
        "WI-IDEMP-TRANS-0001", now=_NOW, idempotency_key="req-activar-WI-IDEMP-TRANS-0001"
    )

    assert reintentado == activado
    assert len(store_tras_reiniciar.list_events()) == 2  # crear + activar, no tres.
    assert len(replay(journal_path).valid_records) == 2


def test_reintento_de_change_work_item_scope_no_repite_la_cascada_de_runs(
    tmp_path: Path,
) -> None:
    """CODEX-002: la cascada de ``change_work_item_scope`` también debe saltarse en el reintento.

    ``change_work_item_scope`` invalida cada ``Run`` no terminado del
    WorkItem ANTES de anexar el propio cambio de alcance. Si el chequeo de
    idempotencia no se adelanta también delante de esa cascada, un reintento
    volvería a invalidar los Run (o fallaría al intentarlo dos veces), en vez
    de devolver el resultado ya confirmado sin ningún efecto adicional.
    """
    journal_path = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(journal_path)
    store.create_work_item(
        work_id="WI-IDEMP-SCOPE-0001",
        peticion_original="texto literal",
        objetivo="objetivo original",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    store.prepare_run(
        run_id="RUN-IDEMP-SCOPE-0001",
        work_id="WI-IDEMP-SCOPE-0001",
        paso="paso-1",
        worker=_WORKER,
        work_package={"instrucciones": "ejecutar paso 1"},
        deadline=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
        now=_NOW,
    )
    key = "req-cambiar-alcance-WI-IDEMP-SCOPE-0001"

    cambiado = store.change_work_item_scope(
        "WI-IDEMP-SCOPE-0001", now=_NOW, objetivo="objetivo nuevo", idempotency_key=key
    )
    eventos_tras_primer_cambio = len(store.list_events())

    reintentado = store.change_work_item_scope(
        "WI-IDEMP-SCOPE-0001", now=_NOW, objetivo="objetivo nuevo", idempotency_key=key
    )

    assert reintentado == cambiado
    assert len(store.list_events()) == eventos_tras_primer_cambio
    assert len(replay(journal_path).valid_records) == eventos_tras_primer_cambio


def test_una_clave_publica_con_forma_de_clave_de_cascada_no_bloquea_la_invalidacion(
    tmp_path: Path,
) -> None:
    """CODEX-001 (ronda 5): la clave interna de la cascada no debe colisionar con una pública.

    Reproduce el hallazgo exacto: un Run se despacha con la clave pública
    ``"K::scope-cascade::R"`` -la misma forma de texto que, ANTES de esta
    corrección, se usaba para derivar la clave interna de la cascada de
    ``change_work_item_scope`` concatenando la clave del llamador con
    ``"::scope-cascade::"`` y el id del Run-. Al cambiar después el alcance
    del WorkItem con la clave pública ``"K"``, la clave derivada para ese
    mismo Run coincidía por igualdad de texto con la entrada ya presente en
    `_idempotency_seen`, y `_append_run` devolvía el Run cacheado sin anexar
    la invalidación: el alcance cambiaba pero el Run seguía `DISPATCHED`, sin
    cancelación pedida y sin `invalidado_por_alcance`. Con la clave interna
    aislada por tipo (una tupla, nunca igual a una `str`), el Run debe quedar
    invalidado y con la cancelación pedida.
    """
    journal_path = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(journal_path)
    work_id = "WI-CODEX001R5-0001"
    run_id = "RUN-CODEX001R5-0001"
    store.create_work_item(
        work_id=work_id,
        peticion_original="texto literal",
        objetivo="objetivo original",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    store.prepare_run(
        run_id=run_id,
        work_id=work_id,
        paso="paso-1",
        worker=_WORKER,
        work_package={"instrucciones": "ejecutar paso 1"},
        deadline=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
        now=_NOW,
    )
    scope_key = "K"
    colliding_public_key = f"{scope_key}::scope-cascade::{run_id}"
    store.dispatch_run(run_id, now=_NOW, idempotency_key=colliding_public_key)

    store.change_work_item_scope(
        work_id, now=_NOW, objetivo="objetivo nuevo", idempotency_key=scope_key
    )

    run = store.get_run(run_id)
    assert run is not None
    assert run.invalidado_por_alcance is True
    assert run.cancellation_status is CancellationStatus.UNCONFIRMED
    assert "run_cancellation_requested" in [event.kind for event in store.list_events()]


def test_reintento_tras_cascada_incompleta_reconoce_clave_interna_de_diario_heredado(
    tmp_path: Path,
) -> None:
    """CODEX-001 (ronda 6): un diario heredado de antes de la ronda 5 debe migrarse.

    Reproduce el hallazgo exacto: un diario escrito por la versión ANTERIOR a
    la ronda 5 -que derivaba la clave interna de la cascada concatenando
    texto, ``f"{clave}::scope-cascade::{run_id}"``, en vez de una tupla- con
    4 registros, el último ``run_cancellation_requested`` con esa clave
    heredada, tras una cascada de ``change_work_item_scope`` interrumpida a
    mitad (p. ej. por un ``DirectorySyncError``, CODEX-001 ronda 4). Al abrir
    ese diario con esta versión y reintentar la MISMA clave pública ``"K"``,
    `_decode_idempotency_key` debe reconstruir la tupla equivalente a partir
    del texto heredado para que la cascada reconozca ese paso como ya hecho;
    sin la migración, la clave heredada (``str``) nunca coincide con la
    tupla que esta versión deriva al reintentar, y la cascada repite el paso
    ya confirmado -anexando ``run_scope_invalidated`` de más, 6 registros en
    vez de los 5 esperados (los 4 + ``work_item_scope_changed``).
    """
    journal_path = tmp_path / "diario.jsonl"
    work_id = "WI-CODEX001R6-0001"
    run_id = "RUN-CODEX001R6-0001"

    store = DurableWorkEngineStore(journal_path)
    store.create_work_item(
        work_id=work_id,
        peticion_original="texto literal",
        objetivo="objetivo original",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    store.prepare_run(
        run_id=run_id,
        work_id=work_id,
        paso="paso-1",
        worker=_WORKER,
        work_package={"instrucciones": "ejecutar paso 1"},
        deadline=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
        now=_NOW,
    )
    store.dispatch_run(run_id, now=_NOW)

    # Escribir a mano el 4.º registro exactamente como lo escribía la
    # cascada ANTES de la ronda 5: clave interna como texto concatenado.
    dispatched = store.get_run(run_id)
    assert dispatched is not None
    cancelado = dispatched.mark_scope_invalidated(now=_NOW).request_cancel(now=_NOW)
    legacy_key = f"K::scope-cascade::{run_id}"
    append_durably(
        journal_path,
        {
            "sequence": 4,
            "occurred_at": _NOW.isoformat(),
            "aggregate_type": AggregateType.RUN.value,
            "aggregate_id": run_id,
            "kind": "run_cancellation_requested",
            "entity": run_to_dict(cancelado),
            "idempotency_key": legacy_key,
        },
    )

    reabierto = DurableWorkEngineStore(journal_path)
    reabierto.change_work_item_scope(
        work_id, now=_NOW, objetivo="objetivo nuevo", idempotency_key="K"
    )

    registros = replay(journal_path).valid_records
    assert [r["kind"] for r in registros] == [
        "work_item_created",
        "run_prepared",
        "run_dispatched",
        "run_cancellation_requested",
        "work_item_scope_changed",
    ]
    run = reabierto.get_run(run_id)
    assert run is not None
    assert run.invalidado_por_alcance is True
    assert run.cancellation_status == CancellationStatus.UNCONFIRMED


def test_cancelacion_publica_con_forma_de_clave_de_cascada_es_idempotente_al_reabrir(
    tmp_path: Path,
) -> None:
    """CODEX-001 (ronda 7): una cancelación PÚBLICA no debe confundirse con la cascada.

    Reproduce el hallazgo exacto: se pide la cancelación de un Run
    ``DISPATCHED`` vía la API pública ``request_run_cancellation`` -no la
    cascada de ``change_work_item_scope``- con la clave pública
    ``"K::scope-cascade::R"``, que por casualidad tiene la misma forma de
    texto que la clave interna heredada de la cascada
    (:data:`_LEGACY_SCOPE_CASCADE_MARKER`). Al reabrir el almacén,
    `_decode_idempotency_key` NO debe reinterpretar esa clave pública como la
    tupla interna de la cascada -el Run anexado no lleva
    `invalidado_por_alcance`, la evidencia que sí deja la cascada-, así que
    debe seguir siendo reconocible como la misma clave `str` que el llamador
    volverá a usar. Reintentar la MISMA petición tras reabrir debe devolver
    el Run ya cancelado de forma idempotente, sin lanzar
    `IllegalTransitionError` por pedir la cancelación dos veces.
    """
    journal_path = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(journal_path)
    work_id = "WI-CODEX001R7-0001"
    run_id = "RUN-CODEX001R7-0001"
    store.create_work_item(
        work_id=work_id,
        peticion_original="texto literal",
        objetivo="objetivo original",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    store.prepare_run(
        run_id=run_id,
        work_id=work_id,
        paso="paso-1",
        worker=_WORKER,
        work_package={"instrucciones": "ejecutar paso 1"},
        deadline=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
        now=_NOW,
    )
    store.dispatch_run(run_id, now=_NOW)

    colliding_public_key = f"K::scope-cascade::{run_id}"
    primero = store.request_run_cancellation(run_id, now=_NOW, idempotency_key=colliding_public_key)
    assert primero.invalidado_por_alcance is False
    assert primero.cancellation_status is CancellationStatus.UNCONFIRMED

    reabierto = DurableWorkEngineStore(journal_path)
    reintento = reabierto.request_run_cancellation(
        run_id, now=_NOW, idempotency_key=colliding_public_key
    )
    assert reintento == primero
    assert [event.kind for event in reabierto.list_events()] == [
        "work_item_created",
        "run_prepared",
        "run_dispatched",
        "run_cancellation_requested",
    ]


def test_fallo_de_fsync_a_mitad_de_la_cascada_de_change_scope_no_duplica_al_reintentar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CODEX-001 (ronda 4): la cascada de ``change_work_item_scope`` debe ser
    reanudable, no solo la llamada de nivel superior.

    Reproduce el hallazgo exacto: un Run ``DISPATCHED`` vivo, y falla
    únicamente el `fsync` del DIRECTORIO (la segunda llamada a `os.fsync`
    dentro de CADA anexo) al anexar `run_cancellation_requested` -el anexo
    interno de la cascada, no el anexo final del cambio de alcance-. El
    registro queda completo y durable en el diario pese al fallo (CODEX-001
    previo), pero `change_work_item_scope` nunca llega a anexar
    `work_item_scope_changed`. Antes de esta corrección, el reintento con la
    MISMA clave de idempotencia recomputaba la cascada entera para el mismo
    Run -que ya no tiene `cancellation_status is NONE`- y anexaba un
    `run_scope_invalidated` adicional además de `work_item_scope_changed`:
    seis registros en vez de cinco.
    """
    journal_path = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(journal_path)
    store.create_work_item(
        work_id="WI-CODEX001R4-0001",
        peticion_original="texto literal",
        objetivo="objetivo original",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    store.prepare_run(
        run_id="RUN-CODEX001R4-0001",
        work_id="WI-CODEX001R4-0001",
        paso="paso-1",
        worker=_WORKER,
        work_package={"instrucciones": "ejecutar paso 1"},
        deadline=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
        now=_NOW,
    )
    store.dispatch_run("RUN-CODEX001R4-0001", now=_NOW)

    real_fsync = os.fsync
    llamadas = 0

    def fsync_que_falla_la_segunda_llamada(fd: int) -> None:
        nonlocal llamadas
        llamadas += 1
        # A partir de aquí (los tres anexos previos ya están confirmados y no
        # pasan por este contador): llamada 1 es el fsync de FICHERO del
        # anexo `run_cancellation_requested` -tiene éxito, el registro queda
        # completo-; llamada 2 es el fsync de SU directorio, la que falla.
        if llamadas == 2:
            raise OSError("fallo simulado de fsync de directorio")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync_que_falla_la_segunda_llamada)

    key = "req-cambiar-alcance-WI-CODEX001R4-0001"
    with pytest.raises(DirectorySyncError):
        store.change_work_item_scope(
            "WI-CODEX001R4-0001", now=_NOW, objetivo="objetivo nuevo", idempotency_key=key
        )

    registros_tras_el_fallo = replay(journal_path).valid_records
    assert [r["kind"] for r in registros_tras_el_fallo] == [
        "work_item_created",
        "run_prepared",
        "run_dispatched",
        "run_cancellation_requested",
    ]

    monkeypatch.setattr(os, "fsync", real_fsync)

    reintentado = store.change_work_item_scope(
        "WI-CODEX001R4-0001", now=_NOW, objetivo="objetivo nuevo", idempotency_key=key
    )

    assert reintentado.objetivo == "objetivo nuevo"
    eventos_finales = [event.kind for event in store.list_events()]
    assert eventos_finales == [
        "work_item_created",
        "run_prepared",
        "run_dispatched",
        "run_cancellation_requested",
        "work_item_scope_changed",
    ]
    registros_finales = replay(journal_path).valid_records
    assert [r["kind"] for r in registros_finales] == eventos_finales

    run_final = store.get_run("RUN-CODEX001R4-0001")
    assert run_final is not None
    assert run_final.cancellation_status is not None
    assert run_final.invalidado_por_alcance is True

    # "Reinicio": reproducir el diario desde cero debe llegar al mismo estado.
    store_reabierto = DurableWorkEngineStore(journal_path)
    assert [event.kind for event in store_reabierto.list_events()] == eventos_finales
    assert store_reabierto.get_work_item("WI-CODEX001R4-0001") == reintentado


def test_fallo_de_fsync_entre_dos_runs_del_corte_por_presupuesto_no_impide_completarlo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CODEX-001 (ronda 3, incidencia #206/#207): el corte por presupuesto agotado
    debe ser una operación reanudable, no solo la llamada de nivel superior.

    Reproduce el hallazgo exacto: dos Runs vivos del mismo WorkItem, y falla
    únicamente el `fsync` del DIRECTORIO al anexar el `run_cancellation_requested`
    del SEGUNDO Run -el primero ya quedó cancelado de forma durable-. El
    registro del segundo Run queda igualmente completo y durable en el
    diario pese al fallo (CODEX-001 previo), pero
    `cancel_all_live_runs_and_escalate_work_item` nunca llega a anexar
    `work_item_escalated`: la excepción se propaga fuera de la cascada antes
    de escalar. Antes de esta corrección, esa cascada vivía inline en
    `governance.registrar_gasto` como un `for` sin ningún punto de reintento
    propio; un reintento del mismo `registrar_gasto` con el mismo
    `work_id` volvía a listar los Runs y a intentar cancelar el segundo -ya
    cancelado de forma durable- sin problema, PERO nada garantizaba que el
    llamador fuera a reintentarlo: la responsabilidad de resumir el corte
    vivía fuera del almacén. Moverla a una única operación de almacén hace
    que un reintento de ESA llamada, y solo esa, complete el corte.
    """
    journal_path = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(journal_path)
    store.create_work_item(
        work_id="WI-CODEX001R3B-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    store.activate_work_item("WI-CODEX001R3B-0001", now=_NOW)
    for run_id, paso in (("RUN-CODEX001R3B-A", "paso-1"), ("RUN-CODEX001R3B-B", "paso-2")):
        store.prepare_run(
            run_id=run_id,
            work_id="WI-CODEX001R3B-0001",
            paso=paso,
            worker=_WORKER,
            work_package={"instrucciones": f"ejecutar {paso}"},
            deadline=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
            now=_NOW,
        )
        store.dispatch_run(run_id, now=_NOW)

    real_fsync = os.fsync
    llamadas = 0

    def fsync_que_falla_la_sexta_llamada(fd: int) -> None:
        nonlocal llamadas
        llamadas += 1
        # Llamada 1: fsync de fichero al anexar la intención del corte
        # (`work_item_budget_cutoff_started`, CODEX-001 ronda 8, éxito).
        # Llamada 2: fsync de SU directorio (éxito). Llamada 3: fsync de
        # fichero al cancelar RUN-A (éxito). Llamada 4: fsync de SU
        # directorio (éxito, RUN-A queda cancelado). Llamada 5: fsync de
        # fichero al cancelar RUN-B (éxito, el registro ya es completo).
        # Llamada 6: fsync de SU directorio -la que falla-.
        if llamadas == 6:
            raise OSError("fallo simulado de fsync de directorio")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync_que_falla_la_sexta_llamada)

    with pytest.raises(DirectorySyncError):
        store.cancel_all_live_runs_and_escalate_work_item("WI-CODEX001R3B-0001", now=_NOW)

    registros_tras_el_fallo = replay(journal_path).valid_records
    assert [r["kind"] for r in registros_tras_el_fallo] == [
        "work_item_created",
        "work_item_activated",
        "run_prepared",
        "run_dispatched",
        "run_prepared",
        "run_dispatched",
        "work_item_budget_cutoff_started",
        "run_cancellation_requested",
        "run_cancellation_requested",
    ]
    work_item_a_medias = store.get_work_item("WI-CODEX001R3B-0001")
    assert work_item_a_medias is not None
    assert work_item_a_medias.estado is WorkItemState.ACTIVE

    monkeypatch.setattr(os, "fsync", real_fsync)

    reintentado = store.cancel_all_live_runs_and_escalate_work_item("WI-CODEX001R3B-0001", now=_NOW)

    assert reintentado.estado is WorkItemState.NEEDS_DECISION
    eventos_finales = [event.kind for event in store.list_events()]
    assert eventos_finales == [
        "work_item_created",
        "work_item_activated",
        "run_prepared",
        "run_dispatched",
        "run_prepared",
        "run_dispatched",
        "work_item_budget_cutoff_started",
        "run_cancellation_requested",
        "run_cancellation_requested",
        "work_item_escalated",
    ]
    registros_finales = replay(journal_path).valid_records
    assert [r["kind"] for r in registros_finales] == eventos_finales

    run_a = store.get_run("RUN-CODEX001R3B-A")
    run_b = store.get_run("RUN-CODEX001R3B-B")
    assert run_a is not None and run_a.cancellation_status is CancellationStatus.UNCONFIRMED
    assert run_b is not None and run_b.cancellation_status is CancellationStatus.UNCONFIRMED

    # "Reinicio": reproducir el diario desde cero debe llegar al mismo estado.
    store_reabierto = DurableWorkEngineStore(journal_path)
    assert [event.kind for event in store_reabierto.list_events()] == eventos_finales
    assert store_reabierto.get_work_item("WI-CODEX001R3B-0001") == reintentado


def test_reabrir_el_almacen_tras_el_fallo_reconcilia_el_corte_pendiente_sin_reintento_manual(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CODEX-001 (ronda 8, incidencia #206/#207): el corte se autorrepara al reabrir.

    Reproduce el hallazgo exacto: tras la MISMA caída a mitad de la cascada
    que el test anterior, en vez de que el llamador repita la llamada, se
    reabre el almacén sin más -exactamente como ocurriría tras un reinicio
    real del proceso, donde nada garantiza que alguien vaya a repetir
    ``cancel_all_live_runs_and_escalate_work_item``-. La intención del corte
    (``work_item_budget_cutoff_started``) ya quedó anexada de forma durable
    ANTES del fallo, así que reabrir el almacén basta para que
    ``_reconcile_pending_budget_cutoffs`` termine el corte por su cuenta, con
    el ``now`` que ya persistía el propio marcador -nunca un reloj real-.
    """
    journal_path = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(journal_path)
    store.create_work_item(
        work_id="WI-CODEX001R8-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    store.activate_work_item("WI-CODEX001R8-0001", now=_NOW)
    for run_id, paso in (("RUN-CODEX001R8-A", "paso-1"), ("RUN-CODEX001R8-B", "paso-2")):
        store.prepare_run(
            run_id=run_id,
            work_id="WI-CODEX001R8-0001",
            paso=paso,
            worker=_WORKER,
            work_package={"instrucciones": f"ejecutar {paso}"},
            deadline=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
            now=_NOW,
        )
        store.dispatch_run(run_id, now=_NOW)

    real_fsync = os.fsync
    llamadas = 0

    def fsync_que_falla_la_sexta_llamada(fd: int) -> None:
        nonlocal llamadas
        llamadas += 1
        if llamadas == 6:
            raise OSError("fallo simulado de fsync de directorio")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync_que_falla_la_sexta_llamada)

    with pytest.raises(DirectorySyncError):
        store.cancel_all_live_runs_and_escalate_work_item("WI-CODEX001R8-0001", now=_NOW)

    registros_tras_el_fallo = replay(journal_path).valid_records
    assert [r["kind"] for r in registros_tras_el_fallo] == [
        "work_item_created",
        "work_item_activated",
        "run_prepared",
        "run_dispatched",
        "run_prepared",
        "run_dispatched",
        "work_item_budget_cutoff_started",
        "run_cancellation_requested",
        "run_cancellation_requested",
    ]
    work_item_a_medias = store.get_work_item("WI-CODEX001R8-0001")
    assert work_item_a_medias is not None
    assert work_item_a_medias.estado is WorkItemState.ACTIVE

    monkeypatch.setattr(os, "fsync", real_fsync)

    # Reabrir el almacén SIN volver a llamar a `cancel_all_live_runs_and_
    # escalate_work_item`: la reconciliación debe ocurrir sola, dentro del
    # propio `__init__`.
    store_reabierto = DurableWorkEngineStore(journal_path)

    reconciliado = store_reabierto.get_work_item("WI-CODEX001R8-0001")
    assert reconciliado is not None
    assert reconciliado.estado is WorkItemState.NEEDS_DECISION

    eventos_finales = [event.kind for event in store_reabierto.list_events()]
    assert eventos_finales == [
        "work_item_created",
        "work_item_activated",
        "run_prepared",
        "run_dispatched",
        "run_prepared",
        "run_dispatched",
        "work_item_budget_cutoff_started",
        "run_cancellation_requested",
        "run_cancellation_requested",
        "work_item_escalated",
    ]
    registros_finales = replay(journal_path).valid_records
    assert [r["kind"] for r in registros_finales] == eventos_finales

    run_a = store_reabierto.get_run("RUN-CODEX001R8-A")
    run_b = store_reabierto.get_run("RUN-CODEX001R8-B")
    assert run_a is not None and run_a.cancellation_status is CancellationStatus.UNCONFIRMED
    assert run_b is not None and run_b.cancellation_status is CancellationStatus.UNCONFIRMED

    # Una segunda reapertura no debe repetir la reconciliación: ya no hay
    # ningún corte pendiente, así que el diario y el estado quedan estables.
    store_reabierto_otra_vez = DurableWorkEngineStore(journal_path)
    assert [event.kind for event in store_reabierto_otra_vez.list_events()] == eventos_finales
    assert store_reabierto_otra_vez.get_work_item("WI-CODEX001R8-0001") == reconciliado


def test_almacen_durable_reproduce_un_ciclo_de_vida_real(tmp_path: Path) -> None:
    journal_path = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(journal_path)

    store.create_work_item(
        work_id="WI-CICLO-0001",
        peticion_original="texto",
        objetivo="objetivo",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    store.activate_work_item("WI-CICLO-0001", now=_NOW)
    fallado = store.fail_work_item_safely(
        "WI-CICLO-0001", diagnostico="sin progreso posible", now=_NOW
    )

    store_reabierto = DurableWorkEngineStore(journal_path)
    assert store_reabierto.get_work_item("WI-CICLO-0001") == fallado
    assert [event.kind for event in store_reabierto.list_events()] == [
        "work_item_created",
        "work_item_activated",
        "work_item_failed_safely",
    ]


# -- Prueba por mutación (ADR-001 §3, requisito 5 de la incidencia #186) -------------


def test_mutacion_quitar_el_checksum_acepta_un_registro_corrupto(tmp_path: Path) -> None:
    """Mutación: dejar de comparar el checksum al reproducir acepta un registro alterado."""
    journal_path = tmp_path / "diario.jsonl"
    append_durably(journal_path, _sample_record(sequence=1), kill_at=None)

    raw = journal_path.read_bytes()
    corrupted = raw.replace(b"paso-1", b"PASO_ALTERADO", 1)
    assert corrupted != raw, "la mutación debe tocar de verdad los bytes del fichero"
    journal_path.write_bytes(corrupted)

    # Implementación real: el checksum no coincide y la línea sigue terminada
    # en su propio salto de línea -corrupción interna, no cola truncada- así
    # que replay se niega a descartarla en silencio.
    with pytest.raises(InternalCorruptionError):
        replay(journal_path)

    # Variante MUTADA (sin comparar el checksum): acepta el registro corrupto.
    def _replay_sin_checksum(path: Path) -> list[dict[str, Any]]:
        valid: list[dict[str, Any]] = []
        for line_bytes in path.read_bytes().splitlines(keepends=True):
            try:
                record = json.loads(line_bytes)
            except json.JSONDecodeError:
                break
            if not isinstance(record, dict) or "checksum_sha256" not in record:
                break
            record.pop("checksum_sha256")
            valid.append(record)
        return valid

    assert len(_replay_sin_checksum(journal_path)) == 1


def test_byte_0x0d_corrupto_no_hace_desaparecer_un_registro_valido(tmp_path: Path) -> None:
    """Reproduce la incidencia #316: un byte corrompido a 0x0D no debe borrar un registro.

    ``bytes.splitlines`` corta también en ``\\r`` (0x0D), mientras que el
    escritor solo delimita registros con ``\\n`` (0x0A, :func:`build_line`).
    Un byte de contenido corrompido a 0x0D partía esa línea en dos fragmentos
    para ``replay``: el primero -sin su propio ``\\n``- se confundía con la
    cola sin terminar de una escritura interrumpida, y el registro completo y
    válido desaparecía sin lanzar :class:`InternalCorruptionError`.
    """
    journal_path = tmp_path / "diario.jsonl"
    for sequence in range(4):
        append_durably(journal_path, _sample_record(sequence=sequence), kill_at=None)

    raw = journal_path.read_bytes()
    newline_positions = [index for index, byte in enumerate(raw) if byte == 0x0A]
    assert len(newline_positions) == 4, "se esperan exactamente 4 líneas completas"
    # Corromper la ÚLTIMA línea (el cuarto registro): así, tras la línea
    # corrompida, no queda ningún registro válido -la única forma de
    # reproducir la rama "cola truncada", que es la que el bug confunde con
    # una escritura interrumpida real y descarta en silencio.
    last_line_start = newline_positions[2] + 1
    last_line_end = newline_positions[3]
    corrupt_offset = (last_line_start + last_line_end) // 2
    assert raw[corrupt_offset] != 0x0A

    corrupted = bytearray(raw)
    corrupted[corrupt_offset] = 0x0D
    journal_path.write_bytes(bytes(corrupted))

    # El escritor solo delimita registros con `\n`: esta línea corrompida
    # sigue siendo, de principio a fin, la línea completa que se escribió -no
    # el sufijo sin terminar de una escritura interrumpida-, así que perderla
    # sin avisar sería corrupción interna, nunca una cola truncada que se
    # pueda descartar en silencio.
    with pytest.raises(InternalCorruptionError):
        replay(journal_path)


def test_mutacion_quitar_la_comprobacion_de_idempotencia_duplica(tmp_path: Path) -> None:
    """Contraste con ``test_reintento_tras_reinicio_no_duplica_por_idempotencia``.

    Anexar directamente con ``append_durably`` -saltándose
    ``DurableWorkEngineStore._append_run``, que es quien comprueba
    ``idempotency_key`` antes de escribir- para el mismo reintento produce
    DOS registros: la mutación (quitar esa comprobación) rompe "sin
    duplicación al reproducir".
    """
    journal_path = tmp_path / "diario.jsonl"
    key = "req-mutado-0001"

    append_durably(journal_path, _sample_record(sequence=1, idempotency_key=key), kill_at=None)
    append_durably(journal_path, _sample_record(sequence=2, idempotency_key=key), kill_at=None)

    assert len(replay(journal_path).valid_records) == 2


def test_mutacion_quitar_recover_invalid_tail_funde_el_reintento_con_la_cola_rota(
    tmp_path: Path,
) -> None:
    """Mutación: anexar sin recortar antes la cola inválida funde el reintento con la basura.

    ``append_durably`` real llama a :func:`recover_invalid_tail` antes de
    escribir. La variante MUTADA de abajo escribe directamente con
    ``O_APPEND`` sin recortar primero -el comportamiento que tenía el spike
    antes de CODEX-001 (incidencia #182)-, así que el registro nuevo aterriza
    detrás de la cola rota de ``MID_WRITE_TORN`` y la línea fundida deja de
    analizar como registro válido: el reintento nunca "aterriza".
    """
    journal_path = tmp_path / "diario.jsonl"
    primero = _sample_record(sequence=1)
    segundo = _sample_record(sequence=2, idempotency_key="req-mutado-cola")
    segundo["aggregate_id"] = "RUN-A2-0002"

    append_durably(journal_path, primero, kill_at=None)
    assert len(replay(journal_path).valid_records) == 1

    completed = _run_writer_subprocess(journal_path, segundo, KillPoint.MID_WRITE_TORN, tmp_path)
    assert completed.returncode == -9
    tras_el_kill = replay(journal_path)
    assert len(tras_el_kill.valid_records) == 1
    assert tras_el_kill.discarded_tail_bytes > 0

    # Implementación real: recortar antes de reintentar, aterriza limpio.
    recover_invalid_tail(journal_path)
    append_durably(journal_path, segundo, kill_at=None)
    assert len(replay(journal_path).valid_records) == 2

    # Variante MUTADA sobre un diario nuevo con la MISMA cola rota: anexar
    # con O_APPEND sin recortar primero -sin llamar a recover_invalid_tail-
    # deja la línea fundida sin analizar, así que el reintento se pierde.
    journal_mutado = tmp_path / "diario-mutado.jsonl"
    append_durably(journal_mutado, primero, kill_at=None)
    completed_mutado = _run_writer_subprocess(
        journal_mutado, segundo, KillPoint.MID_WRITE_TORN, tmp_path
    )
    assert completed_mutado.returncode == -9

    linea_reintento = build_line(segundo)
    fd = os.open(journal_mutado, os.O_WRONLY | os.O_APPEND)
    try:
        os.write(fd, linea_reintento)
        os.fsync(fd)
    finally:
        os.close(fd)

    with pytest.raises(InternalCorruptionError):
        # La línea fundida (cola torn + reintento) no termina en su propio
        # `\n` de forma coherente con un registro completo, pero SÍ hay
        # bytes tras la primera línea inválida que no vuelven a analizar
        # como JSON: el fichero queda irrecuperable para `replay`, la
        # consecuencia exacta que `recover_invalid_tail` existe para evitar.
        replay(journal_mutado)


def test_mutacion_quitar_el_fsync_deja_de_invocarlo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutación: quitar la llamada a ``os.fsync`` dentro de ``append_durably``.

    El arnés de kill-injection no puede distinguir un anexo con `fsync` de
    uno sin él (ADR-026 límite conocido: `kill -9` no vacía la caché de
    páginas del kernel, documentado también en ADR-029 §2) — por eso esta
    mutación no se demuestra con la matriz, sino con un espía: la
    implementación real invoca `os.fsync` exactamente dos veces por anexo
    normal sobre un diario ya existente -una para el propio fichero, otra
    para su directorio padre (CODEX-002: se sincroniza en CADA anexo, no
    solo en el que crea el fichero, cubierto aparte por
    ``test_cada_anexo_sincroniza_tambien_su_directorio``)-; un mutante que
    borre la línea del `fsync` del fichero deja esta lista con una sola
    llamada, y este espía lo detecta donde el kill-matrix no podría.
    """
    journal_path = tmp_path / "diario.jsonl"
    append_durably(journal_path, _sample_record(sequence=1), kill_at=None)

    llamadas: list[int] = []
    real_fsync = os.fsync

    def fsync_espia(fd: int) -> None:
        llamadas.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync_espia)

    append_durably(journal_path, _sample_record(sequence=2), kill_at=None)

    assert len(llamadas) == 2, (
        "append_durably debe llamar a os.fsync dos veces por anexo sobre un diario ya "
        "existente (fichero + directorio); un mutante que quite la línea del fichero "
        "dejaría esta lista con una sola llamada"
    )


def test_cada_anexo_sincroniza_tambien_su_directorio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CODEX-001/CODEX-002: TODO anexo confirmado sincroniza su directorio padre.

    Sin esto, en sistemas de archivos donde sincronizar el fichero no basta
    para hacer durable su entrada de directorio, una caída justo después de
    un anexo confirmado podría, al reiniciar, dejar el diario entero sin
    existir. Comprobarlo solo en el anexo que CREA el fichero no basta
    (CODEX-002): una ejecución anterior puede morir después de crear el
    fichero pero antes de sincronizar su directorio, dejándolo visible sin
    que la entrada sea durable; el siguiente anexo vería el fichero ya
    existente y, si solo sincronizara en la creación, nunca repararía esa
    entrada pendiente. Por eso la corrección sincroniza el directorio en
    CADA anexo, se comprueba aquí con un espía sobre ``os.open``/``os.fsync``
    tanto en el primer anexo (que crea el fichero) como en el segundo (sobre
    el diario ya existente).
    """
    journal_path = tmp_path / "subdir" / "diario.jsonl"
    journal_path.parent.mkdir()

    fsync_calls: list[int] = []
    real_fsync = os.fsync
    dir_fd_abierto: list[int] = []
    real_open = os.open

    def open_espia(path: Any, flags: int, *args: Any) -> int:
        fd = real_open(path, flags, *args)
        if Path(os.fspath(path)) == journal_path.parent and flags == os.O_RDONLY:
            dir_fd_abierto.append(fd)
        return fd

    def fsync_espia(fd: int) -> None:
        fsync_calls.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "open", open_espia)
    monkeypatch.setattr(os, "fsync", fsync_espia)

    append_durably(journal_path, _sample_record(sequence=1), kill_at=None)

    assert len(dir_fd_abierto) == 1, (
        "el anexo que crea el diario debe abrir su directorio padre en solo lectura "
        "para poder sincronizarlo"
    )
    assert dir_fd_abierto[0] in fsync_calls, (
        "el descriptor del directorio padre abierto al crear el diario debe sincronizarse "
        "con os.fsync, o su entrada nueva podría no sobrevivir a una caída"
    )

    # Un segundo anexo, sobre el diario YA existente, también debe abrir y
    # sincronizar el directorio padre (CODEX-002): no puede depender de si
    # ESTE anexo creó el fichero, porque una ejecución anterior pudo haberlo
    # creado sin llegar a sincronizar su directorio.
    dir_fd_abierto.clear()
    fsync_calls.clear()
    append_durably(journal_path, _sample_record(sequence=2), kill_at=None)
    assert len(dir_fd_abierto) == 1, (
        "un anexo sobre un diario ya existente también debe abrir su directorio padre, "
        "por si una creación anterior murió antes de sincronizarlo (CODEX-002)"
    )
    assert dir_fd_abierto[0] in fsync_calls, (
        "el directorio padre debe sincronizarse en cada anexo, no solo en el que crea "
        "el fichero (CODEX-002)"
    )


def test_creacion_interrumpida_antes_de_sincronizar_directorio_se_repara_en_el_reintento(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CODEX-002: reproduce el defecto exacto -``AFTER_OPEN_BEFORE_WRITE`` deja el fichero
    creado (visible) pero sin su directorio sincronizado; antes de la corrección, el
    reintento sobre ese fichero ya existente nunca abría el directorio padre.
    """
    journal_path = tmp_path / "diario.jsonl"

    # Simula la creación interrumpida: el fichero queda creado (vacío) pero
    # su directorio padre nunca llegó a sincronizarse, tal como dejaría un
    # kill en AFTER_OPEN_BEFORE_WRITE.
    fd = os.open(journal_path, os.O_WRONLY | os.O_CREAT, 0o644)
    os.close(fd)
    assert journal_path.exists()

    dir_fd_abierto: list[int] = []
    real_open = os.open

    def open_espia(path: Any, flags: int, *args: Any) -> int:
        fd = real_open(path, flags, *args)
        if Path(os.fspath(path)) == journal_path.parent and flags == os.O_RDONLY:
            dir_fd_abierto.append(fd)
        return fd

    monkeypatch.setattr(os, "open", open_espia)

    append_durably(journal_path, _sample_record(sequence=1), kill_at=None)

    assert len(dir_fd_abierto) == 1, (
        "el reintento sobre un fichero ya existente -pero creado por una ejecución "
        "interrumpida que nunca sincronizó su directorio- debe sincronizarlo ahora "
        "(CODEX-002); antes de la corrección, `created` ya era falso y nunca lo abría"
    )


def test_canonical_bytes_es_estable_ante_el_orden_de_las_claves() -> None:
    """El checksum se calcula sobre una codificación canónica: el orden de entrada no importa."""
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonical_bytes(a) == canonical_bytes(b)


def test_reabrir_el_almacen_termina_un_corte_que_quedo_a_medias_en_waiting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H-3, segunda aparicion de la misma familia: la recuperacion tambien miraba solo ACTIVE.

    `_reconcile_pending_budget_cutoffs` se saltaba todo WorkItem que no
    estuviera en `ACTIVE`. Como un Worker asincrono deja el WorkItem en
    `WAITING` -y `WAITING` es el estado en que se gasta el dinero-, una
    caida a mitad del corte por presupuesto dejaba el trabajo esperando para
    siempre a un Run ya cancelado, sin escalada y sin que nadie se enterara,
    aunque el marcador durable del corte estuviera ahi.
    """
    journal_path = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(journal_path)
    store.create_work_item(
        work_id="WI-H3-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={"presupuesto": {"limite": 10.0}},
        prioridad=1,
        clase=WorkItemClass.INVESTIGACION,
        now=_NOW,
    )
    store.activate_work_item("WI-H3-0001", now=_NOW)
    store.prepare_run(
        run_id="RUN-H3-0001",
        work_id="WI-H3-0001",
        paso="investigar",
        worker=_WORKER_EXTERNO,
        work_package={"instrucciones": "investigar"},
        deadline=datetime(2026, 8, 18, 13, 0, tzinfo=UTC),
        now=_NOW,
    )
    store.dispatch_run("RUN-H3-0001", now=_NOW)
    store.confirm_run_running("RUN-H3-0001", now=_NOW)
    store.dispatch_work_item_async("WI-H3-0001", now=_NOW)
    assert store.get_work_item("WI-H3-0001").estado is WorkItemState.WAITING  # type: ignore[union-attr]

    # Caida justo DESPUES de que el marcador del corte quede durable: el
    # `fsync` real ya se ejecuto, asi que el marcador sobrevive; lo que no
    # llega a ocurrir es la cascada.
    real_fsync = os.fsync
    ya_fallo = False

    def fsync_que_falla_tras_el_marcador(fd: int) -> None:
        nonlocal ya_fallo
        real_fsync(fd)
        if ya_fallo or not stat.S_ISDIR(os.fstat(fd).st_mode):
            return
        if "work_item_budget_cutoff_started" in journal_path.read_text():
            ya_fallo = True
            raise OSError("fallo simulado de fsync de directorio")

    monkeypatch.setattr(os, "fsync", fsync_que_falla_tras_el_marcador)
    with pytest.raises(DirectorySyncError):
        store.cancel_all_live_runs_and_escalate_work_item("WI-H3-0001", now=_NOW)
    monkeypatch.setattr(os, "fsync", real_fsync)

    kinds = [r["kind"] for r in replay(journal_path).valid_records]
    assert "work_item_budget_cutoff_started" in kinds
    assert "work_item_escalated" not in kinds
    a_medias = store.get_work_item("WI-H3-0001")
    assert a_medias is not None and a_medias.estado is WorkItemState.WAITING

    # Reabrir el almacen, sin que nadie repita la llamada, tiene que terminarlo.
    reabierto = DurableWorkEngineStore(journal_path)
    recuperado = reabierto.get_work_item("WI-H3-0001")
    assert recuperado is not None
    assert recuperado.estado is WorkItemState.NEEDS_DECISION

    run = reabierto.get_run("RUN-H3-0001")
    assert run is not None
    assert run.cancellation_status is CancellationStatus.UNCONFIRMED


def test_cada_anexo_salvo_el_primero_relee_el_diario_entero_h21(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H-21 (docs/audits/evidencia-H-20-H-22.md, incidencia #326): el docstring de
    ``DurableWorkEngineStore`` presumía, frente al spike de S1, de reproducir el diario
    una sola vez al construirse y mantenerse con un índice en memoria "sin volver a leer
    el fichero por escritura". Es falso: ``append_durably`` llama incondicionalmente a
    ``recover_invalid_tail``, que llama a ``replay``, que hace ``read_bytes`` del fichero
    entero y recalcula los checksums en CADA anexo -salvo el primero sobre un diario que
    todavía no existe, donde ``recover_invalid_tail``/``replay`` cortan antes de leer
    nada por el `exists()` inicial-. Medición registrada en la auditoría: 200 anexos
    producen 199 lecturas completas del fichero (6.470.505 bytes leídos para un fichero
    final de 65.090 bytes). Esta prueba fija ese hecho con un espía sobre
    ``Path.read_bytes``: si alguien introduce el índice incremental que el docstring
    (antes de esta incidencia) presumía tener, el conteo baja de 199 y esta prueba lo
    delata en vez de dejar que la frase falsa vuelva por la puerta de atrás.
    """
    journal_path = tmp_path / "diario.jsonl"

    lecturas_completas: list[int] = []
    read_bytes_real = Path.read_bytes

    def read_bytes_espia(self: Path) -> bytes:
        if self == journal_path:
            lecturas_completas.append(len(lecturas_completas))
        return read_bytes_real(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes_espia)

    store = DurableWorkEngineStore(journal_path)
    store.create_work_item(
        work_id="WI-H21-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )

    anexos_totales = 200
    for prioridad in range(2, anexos_totales + 1):
        store.reprioritize_work_item("WI-H21-0001", prioridad=prioridad, now=_NOW)

    assert len(lecturas_completas) == anexos_totales - 1, (
        f"se esperaban {anexos_totales - 1} lecturas completas del diario tras "
        f"{anexos_totales} anexos (H-21); si este numero baja, alguien dejo de releer "
        "el diario entero en cada anexo y el docstring de DurableWorkEngineStore "
        "necesitaria dejar de decir que si se relee"
    )


def _ejecutar_guion_de_corte_que_no_escala(store: WorkEngineStore, *, work_id: str) -> WorkItem:
    """El guion de H-20: un corte por presupuesto que golpea un WorkItem en PAUSED.

    ``PAUSED`` no está en ``ESTADOS_EN_CURSO``, así que
    ``cancel_all_live_runs_and_escalate_work_item`` (invocada por
    ``registrar_gasto`` al agotarse el presupuesto) cancela los Runs vivos
    -ninguno aquí- pero no escala: devuelve ``cortado=True, escalada=None``
    y el WorkItem sigue ``PAUSED``. El guion lo reactiva después, con un
    ``now`` posterior, quedando ``ACTIVE`` dentro del mismo proceso tanto en
    memoria como en el durable.
    """
    momento_del_corte = datetime(2026, 1, 1, tzinfo=UTC)
    momento_de_reanudar = datetime(2026, 1, 2, tzinfo=UTC)
    store.create_work_item(
        work_id=work_id,
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={"presupuesto": {"limite": 10.0}},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=momento_del_corte,
    )
    store.activate_work_item(work_id, now=momento_del_corte)
    store.pause_work_item(work_id, now=momento_del_corte)
    resultado = registrar_gasto(
        store,
        work_id=work_id,
        presupuesto=Budget(limite=10.0),
        coste=10.0,
        now=momento_del_corte,
    )
    assert resultado.cortado is True
    assert resultado.escalada is None
    assert resultado.work_item.estado is WorkItemState.PAUSED
    store.resume_work_item(work_id, now=momento_de_reanudar)
    work_item = store.get_work_item(work_id)
    assert work_item is not None
    return work_item


def test_reabrir_el_diario_no_diverge_del_almacen_en_memoria_tras_un_corte_que_no_escalo(
    tmp_path: Path,
) -> None:
    """H-20 (incidencia #321/#345): el mismo guion debe acabar igual en los dos almacenes.

    ``cancel_all_live_runs_and_escalate_work_item`` anexa
    ``work_item_budget_cutoff_started`` ANTES de comprobar si el WorkItem
    está en curso; si no lo está -aquí, ``PAUSED``-, sale sin escalar y sin
    anexar ningún ``work_item_escalated`` que limpie el marcador, que queda
    pendiente para siempre. El almacén en memoria no tiene ese marcador ni
    reconciliación al reabrir, así que el mismo guion lo deja en ``ACTIVE``
    con la fecha de la reanudación. El durable, reabierto, encuentra el
    marcador todavía pendiente y a un WorkItem que YA está ``ACTIVE`` (en
    curso), así que ``_reconcile_pending_budget_cutoffs`` repite la cascada
    con el ``now`` viejo del marcador y lo escala a ``NEEDS_DECISION`` con
    la fecha del corte original, no la de la reanudación: mismo guion,
    almacenes que dicen algo distinto.
    """
    work_id = "WI-H20-0001"
    en_memoria = _ejecutar_guion_de_corte_que_no_escala(InMemoryWorkEngineStore(), work_id=work_id)

    journal_path = tmp_path / "diario.jsonl"
    durable = DurableWorkEngineStore(journal_path)
    en_el_mismo_proceso = _ejecutar_guion_de_corte_que_no_escala(durable, work_id=work_id)
    assert (en_el_mismo_proceso.estado, en_el_mismo_proceso.updated_at) == (
        en_memoria.estado,
        en_memoria.updated_at,
    )

    reabierto = DurableWorkEngineStore(journal_path)
    tras_reabrir = reabierto.get_work_item(work_id)
    assert tras_reabrir is not None
    assert (tras_reabrir.estado, tras_reabrir.updated_at) == (
        en_memoria.estado,
        en_memoria.updated_at,
    ), (
        "el almacen durable diverge del almacen en memoria al reabrir el diario: "
        f"memoria={en_memoria.estado.value}/{en_memoria.updated_at} "
        f"durable tras reabrir={tras_reabrir.estado.value}/{tras_reabrir.updated_at}"
    )
