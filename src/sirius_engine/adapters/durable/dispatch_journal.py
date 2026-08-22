"""Diario del despachador durable: mismo outbox que ADR-061, hermano de C2 (H-11, ADR-064).

Cierra el defecto **H-11** (`docs/audits/registro_defectos.yml`, incidencia
#242): la única implementación de
:class:`~sirius_engine.ports.dispatch_journal.DispatchJournal` era
:class:`~sirius_engine.adapters.memory_dispatch_journal.InMemoryDispatchJournal`,
así que la garantía «una sola activación por ``work_id``» (C2-P3) solo valía
dentro de un proceso. ADR-064 no reabre la decisión de ADR-061: la aplica.
Un episodio de despacho (:class:`~sirius_engine.domain.dispatch.DispatchEpisode`)
se anexa en su propio fichero JSON Lines, reutilizando **sin modificar**
``append_durably``/``replay`` de :mod:`sirius_engine.adapters.durable.journal`
(`fsync` + checksum SHA-256 + recuperación de cola truncada, ADR-026) — nunca
el diario de sucesos de
:class:`~sirius_engine.adapters.durable.store.DurableWorkEngineStore`.

Al abrir, se reproduce el diario una sola vez y se reconstruye el índice en
memoria (``_episodios``, ``_por_work_id``) aplicando los registros en orden —
igual que :class:`~sirius_engine.adapters.durable.supervisor_journal.DurableSupervisorJournal`.
Es lo que hace que ``episode_for`` -y, por tanto, la rama «ya despachado» de
``reservar``- reconozca tras un reinicio un ``work_id`` cuyo episodio ya se
grabó antes de morir el proceso (H11-P1, H11-P2).

Una diferencia deliberada con ``DurableSupervisorJournal``: la coordinación
de ``reservar``/``liberar`` -que decide, sin intercalado posible, cuál de dos
llamadas concurrentes graba el episodio (revisión de la incidencia #240,
ronda 2)- sigue siendo enteramente en memoria (``_lock`` + ``_en_curso`` con
``threading.Event``), exactamente como en
:class:`~sirius_engine.adapters.memory_dispatch_journal.InMemoryDispatchJournal`:
un ``threading.Event`` no es serializable ni tiene sentido fuera del proceso
que lo crea, y el puerto no promete nada sobre una reserva EN CURSO que no
llegó a grabar episodio -solo sobre un episodio ya grabado (H-11 no exige,
y esta incidencia no decide, qué hace un reinicio con una reserva huérfana
que ningún ``liberar`` cerró; ese caso queda para cuando el despachador
corra desatendido, D2-. Si el proceso muere entre ``reservar`` y ``record``,
un reinicio simplemente no encuentra ``_en_curso`` -no sobrevivió, nunca lo
prometió- y una llamada nueva puede volver a reservar: el mismo
comportamiento que ya tiene hoy ``liberar`` tras una guarda rechazada.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from sirius_engine.adapters.durable.journal import DirectorySyncError, append_durably, replay
from sirius_engine.domain.dispatch import DispatchEpisode
from sirius_engine.ports.dispatch_journal import Reserva

_KIND_EPISODE = "dispatch_episode_recorded"


def _episode_to_record(episode: DispatchEpisode) -> dict[str, Any]:
    return {
        "kind": _KIND_EPISODE,
        "work_id": episode.work_id,
        "orden_enlazada": episode.orden_enlazada,
        "repo": episode.repo,
        "numero_incidencia": episode.numero_incidencia,
        "etiqueta": episode.etiqueta,
        "recorded_at": episode.recorded_at.isoformat(),
    }


def _episode_from_record(record: Mapping[str, Any]) -> DispatchEpisode:
    return DispatchEpisode(
        work_id=record["work_id"],
        orden_enlazada=record["orden_enlazada"],
        repo=record["repo"],
        numero_incidencia=record["numero_incidencia"],
        etiqueta=record["etiqueta"],
        recorded_at=datetime.fromisoformat(record["recorded_at"]),
    )


class DurableDispatchJournal:
    """Implementación durable de :mod:`sirius_engine.ports.dispatch_journal`."""

    def __init__(self, journal_path: Path) -> None:
        self._journal_path = journal_path
        self._episodios: list[DispatchEpisode] = []
        self._por_work_id: dict[str, DispatchEpisode] = {}
        self._en_curso: dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        for record in replay(self._journal_path).valid_records:
            if record["kind"] == _KIND_EPISODE:
                self._absorb_episode(_episode_from_record(record))

    def _absorb_episode(self, episode: DispatchEpisode) -> None:
        self._episodios.append(episode)
        self._por_work_id[episode.work_id] = episode

    def episode_for(self, work_id: str) -> DispatchEpisode | None:
        with self._lock:
            return self._por_work_id.get(work_id)

    def record(self, episode: DispatchEpisode) -> None:
        record = _episode_to_record(episode)
        try:
            append_durably(self._journal_path, record)
        except DirectorySyncError:
            # CODEX-001 (mismo razonamiento que `DurableSupervisorJournal`): el
            # registro ya quedó completo y con `fsync` en el propio fichero
            # -solo falló sincronizar su directorio padre-, así que el
            # episodio ya ocurrió de forma durable. Absorberlo en memoria
            # ahora evita que este índice diverja del diario en disco.
            self._absorb_and_release(episode)
            raise
        self._absorb_and_release(episode)

    def _absorb_and_release(self, episode: DispatchEpisode) -> None:
        with self._lock:
            self._absorb_episode(episode)
            evento = self._en_curso.pop(episode.work_id, None)
        if evento is not None:
            evento.set()

    def episodes(self) -> tuple[DispatchEpisode, ...]:
        with self._lock:
            return tuple(self._episodios)

    def reservar(self, work_id: str) -> Reserva:
        with self._lock:
            episodio = self._por_work_id.get(work_id)
            if episodio is not None:
                return Reserva(obtenida=False, episodio=episodio, evento=None)
            evento_en_curso = self._en_curso.get(work_id)
            if evento_en_curso is not None:
                return Reserva(obtenida=False, episodio=None, evento=evento_en_curso)
            self._en_curso[work_id] = threading.Event()
            return Reserva(obtenida=True, episodio=None, evento=None)

    def liberar(self, work_id: str) -> None:
        with self._lock:
            evento = self._en_curso.pop(work_id, None)
        if evento is not None:
            evento.set()
