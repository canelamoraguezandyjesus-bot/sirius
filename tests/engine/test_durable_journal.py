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
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sirius_engine.adapters.durable.entity_codec import run_from_dict, run_to_dict
from sirius_engine.adapters.durable.journal import (
    InternalCorruptionError,
    KillPoint,
    append_durably,
    build_line,
    canonical_bytes,
    recover_invalid_tail,
    replay,
)
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.domain.events import AggregateType
from sirius_engine.domain.run import Run
from sirius_engine.domain.run import prepare as prepare_run
from sirius_engine.domain.work_item import WorkItemClass

_REPO_ROOT = Path(__file__).resolve().parents[2]
_NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _sample_run() -> Run:
    return prepare_run(
        run_id="RUN-A2-0001",
        work_id="WI-A2-0001",
        paso="paso-1",
        worker="worker-de-prueba",
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
    implementación real invoca `os.fsync` exactamente una vez por anexo
    normal; un mutante que borre esa línea deja de invocarlo, y este espía
    lo detecta donde el kill-matrix no podría.
    """
    journal_path = tmp_path / "diario.jsonl"
    llamadas: list[int] = []
    real_fsync = os.fsync

    def fsync_espia(fd: int) -> None:
        llamadas.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync_espia)

    append_durably(journal_path, _sample_record(sequence=1), kill_at=None)

    assert len(llamadas) == 1, (
        "append_durably debe llamar a os.fsync exactamente una vez por anexo; "
        "un mutante que quite esa línea dejaría esta lista vacía"
    )


def test_canonical_bytes_es_estable_ante_el_orden_de_las_claves() -> None:
    """El checksum se calcula sobre una codificación canónica: el orden de entrada no importa."""
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonical_bytes(a) == canonical_bytes(b)
