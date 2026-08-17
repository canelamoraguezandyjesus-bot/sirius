"""Matriz punto-de-muerte x resultado del spike I3 (incidencia #182, ADR-026).

Reproduce bajo `pytest` -y por tanto en CI (requisito 3: `experiments/` no lo
recorre `pytest`, pero `tests/engine/` sí)- la evidencia de que el patrón
elegido (diario append-only con `fsync`, checksum por registro y clave de
idempotencia) deja el almacén, tras matar el proceso escritor en CADA punto
nombrado del ciclo de una transición, en exactamente uno de dos estados: la
transición no ocurrió, o ocurrió una sola vez. Nunca a medias, nunca dos
veces (requisito 1).

Los puntos de corte los inyecta el propio proceso que muere
(`os.kill(os.getpid(), SIGKILL)` dentro de
`durable_journal.append_durably`), no un temporizador externo: el arnés se
detiene siempre en el punto nombrado, nunca "aproximadamente ahí" (requisito
2, riesgo declarado en la incidencia).

La matriz completa (columna "resultado esperado") se publica también en
``experiments/work_engine_spike_i3/RESULTADOS.md`` y en la descripción de la
PR, junto con la comparativa de patrones y los límites conocidos.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from experiments.work_engine_spike_i3.durable_journal import (
    KillPoint,
    append_durably,
    recover_invalid_tail,
    replay,
)
from experiments.work_engine_spike_i3.durable_store import DurableJsonlWorkItemStore
from experiments.work_engine_spike_i3.entity_codec import run_to_dict, work_item_to_dict

from sirius_engine.domain.events import AggregateType
from sirius_engine.domain.run import prepare as prepare_run
from sirius_engine.domain.work_item import WorkItemClass, create_work_item

_REPO_ROOT = Path(__file__).resolve().parents[2]
_NOW = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)


def _sample_record(*, sequence: int = 1, idempotency_key: str | None = None) -> dict[str, Any]:
    work_item = create_work_item(
        work_id="WI-SPIKE-0001",
        peticion_original="texto literal de la petición",
        objetivo="objetivo normalizado y confirmado",
        contexto_origen=("incidencia:182",),
        entregable="un entregable de prueba",
        criterio_terminado="el entregable existe y pasa sus pruebas",
        limites={"presupuesto_turnos": 5},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
    )
    return {
        "sequence": sequence,
        "occurred_at": _NOW.isoformat(),
        "aggregate_type": AggregateType.WORK_ITEM.value,
        "aggregate_id": work_item.work_id,
        "kind": "work_item_created",
        "entity": work_item_to_dict(work_item),
        "idempotency_key": idempotency_key,
    }


def _sample_run_record(*, sequence: int = 1, idempotency_key: str | None = None) -> dict[str, Any]:
    """Registro de una transición representativa de ``Run`` (incidencia #182, CODEX-002).

    I3 exige un esqueleto desechable con ``WorkItem`` **y** ``Run``: la
    matriz punto-de-muerte ya cubre `WorkItem` (`_sample_record`); esto
    aporta la transición de `Run` correspondiente -`prepare`, la primera del
    ciclo `PREPARED -> DISPATCHED -> RUNNING -> FINISHED` (§3.3)- para
    demostrar que el mismo patrón de escritura (diario append-only, `fsync`,
    checksum, idempotencia) también cubre a `Run`, sin implementar el resto
    del puerto (ver límites conocidos en `RESULTADOS.md`).
    """
    run = prepare_run(
        run_id="RUN-SPIKE-0001",
        work_id="WI-SPIKE-0001",
        paso="paso-1",
        worker="worker-de-prueba",
        work_package={"instrucciones": "ejecutar paso 1"},
        intento=1,
        deadline=datetime(2026, 8, 17, 13, 0, tzinfo=UTC),
        now=_NOW,
    )
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
            "experiments.work_engine_spike_i3.writer_process",
            str(journal_path),
            str(record_path),
            kill_at_arg,
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        timeout=30,
    )


#: La matriz que el requisito 1 exige publicada: para cada punto nombrado del
#: ciclo de escritura, el resultado que el patrón elegido garantiza tras
#: reiniciar. "ocurrio_una_vez" en los tres últimos puntos es esperado y
#: documentado como límite conocido (ADR-026 §2): `kill -9` no vacía la
#: caché de páginas del kernel, así que los bytes que `os.write` ya entregó
#: siguen visibles al releer el fichero en la misma máquina, se haya
#: llamado a `fsync` o no. El arnés no puede demostrar lo contrario sin
#: inyección de fallos a nivel de sistema de ficheros (fuera de alcance).
EXPECTED_OUTCOME = {
    KillPoint.BEFORE_OPEN: "no_ocurrio",
    KillPoint.AFTER_OPEN_BEFORE_WRITE: "no_ocurrio",
    KillPoint.MID_WRITE_TORN: "no_ocurrio",
    KillPoint.AFTER_WRITE_BEFORE_FSYNC: "ocurrio_una_vez",
    KillPoint.AFTER_FSYNC_BEFORE_CLOSE: "ocurrio_una_vez",
    KillPoint.AFTER_CLOSE: "ocurrio_una_vez",
}


@pytest.mark.parametrize("kill_at", tuple(KillPoint), ids=lambda kp: kp.value)
def test_matriz_punto_de_muerte_por_resultado(kill_at: KillPoint, tmp_path: Path) -> None:
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


@pytest.mark.parametrize("kill_at", tuple(KillPoint), ids=lambda kp: kp.value)
def test_matriz_punto_de_muerte_por_resultado_run(kill_at: KillPoint, tmp_path: Path) -> None:
    """Réplica de la matriz anterior para una transición de ``Run`` (CODEX-002).

    Mismo patrón de escritura, mismo arnés (`writer_process` no distingue
    tipo de agregado: solo anexa el registro que se le pase), la MISMA
    garantía -nunca a medias, nunca dos veces- también vale para `Run`.
    """
    journal_path = tmp_path / "diario.jsonl"
    record = _sample_run_record()

    completed = _run_writer_subprocess(journal_path, record, kill_at, tmp_path)

    assert completed.returncode == -9, (
        f"el subproceso debía morir por SIGKILL exactamente en {kill_at.value}; "
        f"returncode={completed.returncode!r} stderr={completed.stderr!r}"
    )

    result = replay(journal_path)
    assert len(result.valid_records) in (0, 1), (
        f"nunca a medias ni dos veces; matar en {kill_at.value} produjo "
        f"{len(result.valid_records)} registros válidos para Run"
    )
    outcome = "no_ocurrio" if len(result.valid_records) == 0 else "ocurrio_una_vez"
    assert outcome == EXPECTED_OUTCOME[kill_at], (
        f"punto {kill_at.value} (Run): se esperaba {EXPECTED_OUTCOME[kill_at]}, salió {outcome}"
    )
    if outcome == "ocurrio_una_vez":
        assert result.valid_records[0]["aggregate_id"] == record["aggregate_id"]
        assert result.valid_records[0]["aggregate_type"] == AggregateType.RUN.value


def test_reintento_tras_reinicio_no_duplica_por_idempotencia(tmp_path: Path) -> None:
    """Mitad "sin duplicación" del requisito: reintento tras reinicio, sin doble evento.

    Escenario real: la escritura durable terminó (equivalente a matar justo
    después de `AFTER_CLOSE`), pero quien la pidió murió o perdió la
    conexión antes de recibir confirmación, así que al "reiniciar" reintenta
    la MISMA petición lógica. Una `idempotency_key` repetida no debe producir
    un segundo evento.
    """
    journal_path = tmp_path / "diario.jsonl"

    store_antes_de_reiniciar = DurableJsonlWorkItemStore(journal_path)
    creado = store_antes_de_reiniciar.create_work_item(
        work_id="WI-IDEMP-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=("incidencia:182",),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_NOW,
        idempotency_key="req-crear-WI-IDEMP-0001",
    )

    # "Reinicio": una instancia nueva del almacén sobre el MISMO diario.
    store_tras_reiniciar = DurableJsonlWorkItemStore(journal_path)
    reintentado = store_tras_reiniciar.create_work_item(
        work_id="WI-IDEMP-0001",
        peticion_original="texto literal",
        objetivo="objetivo",
        contexto_origen=("incidencia:182",),
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


def test_kill_mid_write_torn_reapertura_reintento_preserva_prefijo_y_produce_un_evento(
    tmp_path: Path,
) -> None:
    """CODEX-001: un reintento tras `mid_write_torn` no debe quedarse en 0 registros para siempre.

    Antes de esta corrección, `replay()` descartaba la cola inválida sin
    truncarla, y como `append_durably` abre con `O_APPEND`, el reintento se
    escribía DETRÁS de la cola torn -así que la línea fundida (cola torn +
    registro nuevo) seguía sin analizar como JSON válido y `replay` seguía
    descartándolo todo, reintento incluido. `recover_invalid_tail` (llamado
    automáticamente al principio de cada `append_durably`) recorta esa cola
    antes de escribir, así que el reintento aterriza limpio detrás del
    último registro válido.

    Escenario: (1) un registro válido ya asentado -el prefijo que debe
    sobrevivir-, (2) un segundo registro que muere en `MID_WRITE_TORN`
    -deja una cola inválida-, (3) "reapertura" (nuevo proceso) reintenta la
    MISMA petición lógica sin matar esta vez.
    """
    journal_path = tmp_path / "diario.jsonl"
    primero = _sample_record(sequence=1)
    segundo = _sample_record(sequence=2)
    segundo["aggregate_id"] = "WI-SPIKE-0002"

    # (1) Prefijo válido ya asentado antes del incidente.
    append_durably(journal_path, primero, kill_at=None)
    assert len(replay(journal_path).valid_records) == 1

    # (2) El escritor muere a mitad de escribir el segundo registro.
    completed = _run_writer_subprocess(journal_path, segundo, KillPoint.MID_WRITE_TORN, tmp_path)
    assert completed.returncode == -9

    tras_el_kill = replay(journal_path)
    assert len(tras_el_kill.valid_records) == 1, "el prefijo válido debe sobrevivir al kill"
    assert tras_el_kill.valid_records[0]["aggregate_id"] == primero["aggregate_id"]
    assert tras_el_kill.discarded_tail_bytes > 0, "la cola torn debe quedar marcada como inválida"

    # (3) "Reapertura": un proceso nuevo reintenta la MISMA petición, sin kill esta vez.
    recortados = recover_invalid_tail(journal_path)
    assert recortados == tras_el_kill.discarded_tail_bytes
    append_durably(journal_path, segundo, kill_at=None)

    tras_el_reintento = replay(journal_path)
    assert tras_el_reintento.discarded_tail_bytes == 0
    assert len(tras_el_reintento.valid_records) == 2, (
        "el reintento debe producir exactamente un evento nuevo, preservando el prefijo válido"
    )
    assert tras_el_reintento.valid_records[0]["aggregate_id"] == primero["aggregate_id"]
    assert tras_el_reintento.valid_records[1]["aggregate_id"] == segundo["aggregate_id"]


def test_recover_invalid_tail_es_no_operativo_sin_cola_invalida(tmp_path: Path) -> None:
    """`recover_invalid_tail` no debe tocar un diario ya limpio (ni uno inexistente)."""
    journal_path = tmp_path / "diario.jsonl"

    assert recover_invalid_tail(journal_path) == 0

    append_durably(journal_path, _sample_record(sequence=1), kill_at=None)
    raw_antes = journal_path.read_bytes()

    assert recover_invalid_tail(journal_path) == 0
    assert journal_path.read_bytes() == raw_antes


def test_almacen_durable_reproduce_un_ciclo_de_vida_real(tmp_path: Path) -> None:
    """El subconjunto del puerto encadena varias transiciones reales, reutilizando rebuild_state."""
    journal_path = tmp_path / "diario.jsonl"
    store = DurableJsonlWorkItemStore(journal_path)

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

    # Reabrir desde cero, como si fuera un proceso nuevo tras un reinicio limpio.
    store_reabierto = DurableJsonlWorkItemStore(journal_path)
    assert store_reabierto.get_work_item("WI-CICLO-0001") == fallado
    assert [event.kind for event in store_reabierto.list_events()] == [
        "work_item_created",
        "work_item_activated",
        "work_item_failed_safely",
    ]


# -- Prueba por mutación (ADR-001 §3, requisito 4) -------------------------------------


def _replay_sin_checksum(journal_path: Path) -> list[dict[str, Any]]:
    """Reproducción MUTADA: igual que ``durable_journal.replay``, sin comparar el checksum.

    Existe solo para demostrar por contraste que la comprobación de checksum
    en la implementación real es la que sostiene la propiedad: sin ella, un
    registro con bytes alterados se acepta como si fuera válido.
    """
    if not journal_path.exists():
        return []
    valid: list[dict[str, Any]] = []
    for line_bytes in journal_path.read_bytes().splitlines(keepends=True):
        try:
            record = json.loads(line_bytes)
        except json.JSONDecodeError:
            break
        if not isinstance(record, dict) or "checksum_sha256" not in record:
            break
        record.pop("checksum_sha256")
        valid.append(record)  # MUTACIÓN: sin comparar con el hash recalculado.
    return valid


def test_mutacion_quitar_el_checksum_acepta_un_registro_corrupto(tmp_path: Path) -> None:
    journal_path = tmp_path / "diario.jsonl"
    append_durably(journal_path, _sample_record(sequence=1), kill_at=None)

    raw = journal_path.read_bytes()
    corrupted = raw.replace(b"objetivo normalizado", b"OBJETIVO_ALTERADO_", 1)
    assert corrupted != raw, "la mutación debe tocar de verdad los bytes del fichero"
    journal_path.write_bytes(corrupted)

    # Implementación real: el checksum no coincide -> se descarta como cola corrupta.
    assert replay(journal_path).valid_records == ()

    # Variante mutada (sin comprobar el checksum): acepta el registro corrupto.
    assert len(_replay_sin_checksum(journal_path)) == 1


def test_mutacion_quitar_la_comprobacion_de_idempotencia_duplica(tmp_path: Path) -> None:
    """Contraste con ``test_reintento_tras_reinicio_no_duplica_por_idempotencia``.

    Anexar directamente con ``append_durably`` -saltándose
    ``DurableJsonlWorkItemStore._append``, que es quien comprueba
    ``idempotency_key`` antes de escribir- para el mismo reintento produce
    DOS registros: la mutación (quitar la comprobación) rompe "sin
    duplicación al reproducir".
    """
    journal_path = tmp_path / "diario.jsonl"
    key = "req-mutado-0001"

    append_durably(journal_path, _sample_record(sequence=1, idempotency_key=key), kill_at=None)
    append_durably(journal_path, _sample_record(sequence=2, idempotency_key=key), kill_at=None)

    assert len(replay(journal_path).valid_records) == 2
