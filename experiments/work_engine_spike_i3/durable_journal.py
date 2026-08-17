"""Diario append-only durable: escritura con `fsync` y checksum por registro (ADR-026).

Núcleo compartido entre el almacén en proceso
(:mod:`experiments.work_engine_spike_i3.durable_store`) y el subproceso de
kill-injection (:mod:`experiments.work_engine_spike_i3.writer_process`): la
MISMA función de escritura que usa el almacén en marcha normal es la que el
arnés de pruebas ejecuta hasta un punto nombrado y autotermina — el punto de
corte no es una imitación aparte, es el propio camino de producción del
spike, detenido donde se le pide.

Formato de fichero: JSON Lines. Cada línea es un objeto JSON con los campos
del registro más ``checksum_sha256``, calculado sobre la codificación
canónica (claves ordenadas) del resto de campos. Al reproducir
(:func:`replay`), la primera línea que no analiza como JSON válido o cuyo
checksum no coincide se trata como cola truncada por una escritura
interrumpida SOLO si, a la vez, (a) no hay ningún registro completo y válido
después de ella, y (b) esa línea inválida no termina en su propio salto de
línea -es decir, es el sufijo SIN terminar al final del fichero-: en ese caso
se descarta ella y todo lo que la sigue (ADR-026). Si hay al menos un
registro válido después de la línea inválida, o si la línea inválida sí
termina en su propio `\n` (una línea completa que se escribió entera pero
cuyo contenido o checksum no cuadra), no puede ser una cola truncada -una
escritura interrumpida por este escritor solo deja basura SIN terminar al
final, nunca una línea completa ni un registro bueno después de la basura-,
así que es corrupción interna del medio: :func:`replay` lanza
:class:`InternalCorruptionError` en vez de descartar en silencio, porque
recortar ahí perdería registros válidos que sí llegaron a completarse.

Antes de cada anexo, :func:`append_durably` llama a
:func:`recover_invalid_tail`, que recorta y sincroniza esa misma cola
inválida del fichero. Es necesario porque la apertura de escritura usa
``O_APPEND``: sin recortar primero, un reintento escribiría su registro
nuevo (válido) justo detrás de la cola vieja (inválida), y ambos se
fundirían en una sola línea rota para `replay` -que la descartaría entera,
incluido el registro nuevo del reintento.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class InternalCorruptionError(RuntimeError):
    """El diario tiene una línea corrupta que no puede ser cola truncada.

    Dos señales, cualquiera de las dos basta: hay registros completos y
    válidos después de la línea inválida, o la propia línea inválida termina
    en su salto de línea (una línea que se escribió entera, así que no es el
    sufijo sin terminar que deja una escritura interrumpida). En ambos casos
    es corrupción interna del medio, no una cola truncada. Recortar perdería
    registros válidos, así que :func:`replay` se niega a hacerlo y
    :func:`recover_invalid_tail`/:func:`append_durably` propagan este error
    en vez de anexar (ADR-026, límite conocido: reparar el medio o aportar
    redundancia queda fuera de alcance de este spike).
    """


class KillPoint(StrEnum):
    """Puntos nombrados del ciclo de una escritura durable (incidencia #182, requisito 1/2)."""

    BEFORE_OPEN = "before_open"
    AFTER_OPEN_BEFORE_WRITE = "after_open_before_write"
    MID_WRITE_TORN = "mid_write_torn"
    AFTER_WRITE_BEFORE_FSYNC = "after_write_before_fsync"
    AFTER_FSYNC_BEFORE_CLOSE = "after_fsync_before_close"
    AFTER_CLOSE = "after_close"


def _self_kill() -> None:
    """Autoterminar este proceso con SIGKILL, inmediato e incapturable.

    Inyectado dentro del propio código del escritor -en vez de que un
    observador externo mate por temporización- para que el punto de corte
    sea determinista por construcción: siempre el nombrado, nunca "más o
    menos ahí" (el riesgo que la incidencia #182 declara como principal).
    """
    os.kill(os.getpid(), signal.SIGKILL)
    raise AssertionError("SIGKILL no puede bloquearse ni capturarse: inalcanzable")


def _write_all(fd: int, data: bytes) -> None:
    """Escribir todos los bytes de ``data`` en ``fd``, sin confirmar una escritura corta.

    ``os.write`` puede devolver una cuenta de bytes escritos menor que
    ``len(data)`` sin lanzar excepción -POSIX lo permite incluso en ficheros
    regulares-, y el resultado son los mismos bytes en disco que dejaría una
    escritura interrumpida a mitad: el registro queda sin su delimitador
    ``\\n`` final. Sin este bucle, ``append_durably`` confirmaba éxito con
    ese sufijo incompleto en disco; :func:`replay` lo trataba entonces como
    cola truncada -indistinguible de un kill real- y `recover_invalid_tail`
    lo descartaba para siempre, aunque el JSON y el checksum del registro
    estuvieran completos (CODEX-001, incidencia #182). Reintentar hasta
    completar ``data`` -o fallar sin haber llamado a ``fsync``- evita
    confirmar ese estado a medias.
    """
    written = 0
    while written < len(data):
        count = os.write(fd, data[written:])
        if count <= 0:
            raise OSError(
                f"os.write() devolvió {count} bytes escritos de {len(data) - written} "
                "pendientes; no se puede confirmar el anexo"
            )
        written += count


def canonical_bytes(record_without_checksum: Mapping[str, Any]) -> bytes:
    return json.dumps(record_without_checksum, sort_keys=True, ensure_ascii=False).encode("utf-8")


def build_line(record_without_checksum: Mapping[str, Any]) -> bytes:
    checksum = hashlib.sha256(canonical_bytes(record_without_checksum)).hexdigest()
    full = dict(record_without_checksum)
    full["checksum_sha256"] = checksum
    return json.dumps(full, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def recover_invalid_tail(journal_path: Path) -> int:
    """Truncar y sincronizar la cola inválida del diario, si la hay.

    Antes de cada anexo hay que dejar el diario en un estado del que
    ``O_APPEND`` pueda partir de forma segura: si una escritura anterior
    murió a mitad (p. ej. ``MID_WRITE_TORN``), sus bytes finales quedan sin
    ``\\n`` de cierre, y anexar detrás de ellos con ``O_APPEND`` fundiría el
    registro nuevo (válido) con la cola vieja (inválida) en una sola línea
    para :func:`replay`, que la descartaría entera -incluido el registro
    nuevo. Recortar la cola inválida ANTES de escribir evita esa fusión.

    No repara corrupción interna (ADR-026, límite conocido): si `replay`
    determina que la línea inválida tiene registros completos y válidos
    detrás -así que no es una cola truncada-, deja `InternalCorruptionError`
    propagarse sin tocar el fichero, en vez de recortar y perder esos
    registros. Cuando sí es cola truncada, recorta exactamente lo que
    `replay` ya descartaría, ni un byte más. Devuelve cuántos bytes se
    recortaron.
    """
    if not journal_path.exists():
        return 0
    result = replay(journal_path)
    if result.discarded_tail_bytes == 0:
        return 0
    valid_size = journal_path.stat().st_size - result.discarded_tail_bytes
    fd = os.open(journal_path, os.O_WRONLY)
    try:
        os.ftruncate(fd, valid_size)
        os.fsync(fd)
    finally:
        os.close(fd)
    return result.discarded_tail_bytes


def append_durably(
    journal_path: Path,
    record_without_checksum: Mapping[str, Any],
    *,
    kill_at: KillPoint | None = None,
) -> None:
    """Anexar un registro al diario, con puntos de corte inyectables.

    Sin ``kill_at`` es el camino normal: recuperar la cola inválida si la
    hay, abrir, escribir, ``fsync``, cerrar. Con ``kill_at``, se autotermina
    justo después de completar las acciones hasta ese punto — nunca antes.
    """
    if kill_at is KillPoint.BEFORE_OPEN:
        _self_kill()

    recover_invalid_tail(journal_path)

    line = build_line(record_without_checksum)

    fd = os.open(journal_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        if kill_at is KillPoint.AFTER_OPEN_BEFORE_WRITE:
            _self_kill()

        if kill_at is KillPoint.MID_WRITE_TORN:
            # Torn write inyectado, no una interrupción real de la syscall:
            # capturar el kill exactamente a mitad de un write() del kernel
            # no es observable ni reproducible desde el espacio de usuario.
            # Escribir deliberadamente un prefijo incompleto simula su efecto
            # de forma determinista, que es lo que un punto NOMBRADO exige.
            torn_prefix = line[: len(line) // 2]
            os.write(fd, torn_prefix)
            os.fsync(fd)  # incluso el prefijo truncado llega a disco: caso peor.
            _self_kill()

        _write_all(fd, line)

        if kill_at is KillPoint.AFTER_WRITE_BEFORE_FSYNC:
            _self_kill()

        os.fsync(fd)

        if kill_at is KillPoint.AFTER_FSYNC_BEFORE_CLOSE:
            _self_kill()
    finally:
        os.close(fd)

    if kill_at is KillPoint.AFTER_CLOSE:
        _self_kill()


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """Resultado de reproducir el diario: registros válidos y cola descartada."""

    valid_records: tuple[dict[str, Any], ...]
    discarded_tail_bytes: int


def _parse_valid_line(line_bytes: bytes) -> dict[str, Any] | None:
    """Analizar una línea como registro válido, o ``None`` si falla JSON o checksum."""
    try:
        record = json.loads(line_bytes)
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict) or "checksum_sha256" not in record:
        return None
    checksum = record.pop("checksum_sha256")
    expected = hashlib.sha256(canonical_bytes(record)).hexdigest()
    if checksum != expected:
        return None
    return record


def replay(journal_path: Path) -> ReplayResult:
    if not journal_path.exists():
        return ReplayResult(valid_records=(), discarded_tail_bytes=0)

    raw = journal_path.read_bytes()
    lines = raw.splitlines(keepends=True)
    valid: list[dict[str, Any]] = []
    consumed = 0
    first_invalid_index: int | None = None
    for index, line_bytes in enumerate(lines):
        if not line_bytes.endswith(b"\n"):
            # Solo puede ser la última línea del fichero (splitlines únicamente
            # deja sin `\n` el sufijo final si `raw` no termina en salto de
            # línea). Aunque su contenido analice como JSON válido y su
            # checksum cuadre, la ausencia del `\n` de cierre es indistinguible
            # de una escritura interrumpida justo antes de escribirlo -este
            # escritor solo añade el `\n` como parte atómica de la misma
            # `write()` que el resto de la línea (`build_line`)-, así que no
            # puede darse por asentada: cae a la misma comprobación de cola
            # truncada que una línea que ni siquiera parsea.
            first_invalid_index = index
            break
        record = _parse_valid_line(line_bytes)
        if record is None:
            first_invalid_index = index
            break
        valid.append(record)
        consumed += len(line_bytes)

    if first_invalid_index is None:
        return ReplayResult(valid_records=tuple(valid), discarded_tail_bytes=0)

    invalid_line = lines[first_invalid_index]
    remaining_lines = lines[first_invalid_index + 1 :]
    has_valid_record_after = any(
        _parse_valid_line(line_bytes) is not None for line_bytes in remaining_lines
    )
    if has_valid_record_after:
        raise InternalCorruptionError(
            f"{journal_path}: la línea {first_invalid_index + 1} es inválida pero hay "
            "registros completos y válidos después -no es una cola truncada por una "
            "escritura interrumpida, sino corrupción interna del medio"
        )
    if invalid_line.endswith(b"\n"):
        raise InternalCorruptionError(
            f"{journal_path}: la línea {first_invalid_index + 1} es inválida pero "
            "termina en su propio salto de línea -una escritura interrumpida por este "
            "escritor solo deja un sufijo SIN terminar al final del fichero, así que "
            "una línea completa e inválida es corrupción interna del medio, no cola truncada"
        )

    discarded_tail_bytes = len(raw) - consumed
    return ReplayResult(valid_records=tuple(valid), discarded_tail_bytes=discarded_tail_bytes)
