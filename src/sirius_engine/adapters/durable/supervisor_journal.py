"""Diario del supervisor durable: outbox propio, no acoplado al almacén (H-10, ADR-061).

Cierra el defecto **H-10** (`docs/audits/registro_defectos.yml`, incidencia
#236): la marca de «escalada pendiente de notificar» de
:class:`~sirius_engine.ports.supervisor_journal.SupervisorJournal` sobrevive
hoy solo en :class:`~sirius_engine.adapters.memory_supervisor_journal.InMemorySupervisorJournal`.
ADR-057 dejó diferida la elección de diseño; ADR-061 la resuelve: un diario
propio, en su propio fichero JSON Lines, reutilizando **sin modificar** las
primitivas genéricas de :mod:`sirius_engine.adapters.durable.journal`
(``append_durably``/``replay``: `fsync` + checksum SHA-256 + recuperación de
cola truncada, ADR-026) — nunca el diario de sucesos de
:class:`~sirius_engine.adapters.durable.store.DurableWorkEngineStore`. Los dos
puertos (:mod:`sirius_engine.ports.supervisor_journal` y
:mod:`sirius_engine.ports.store`) siguen tan separados como C1 los dejó a
propósito: este módulo no importa nada de ``ports/store.py`` ni de
``domain/events.py``.

Tres tipos de registro, todos con el mismo formato de línea que ya usa
``journal.py``:

- ``supervision_episode_recorded``: el episodio completo, append-only.
- ``pending_escalation_recorded``: ``work_id`` + ``run_id`` que dejó la
  escalada pendiente de notificar (CODEX-001, C1).
- ``pending_escalation_cleared``: ``work_id`` cuya marca se limpió tras
  entregar la notificación.

Al abrir, se reproduce el diario una sola vez (igual que
``DurableWorkEngineStore._load``) y se reconstruye el índice en memoria
aplicando los registros en orden: el último ``pending_escalation_recorded``
o ``pending_escalation_cleared`` para un ``work_id`` dado gana. Es lo que
hace que la marca sea correlacionable con su ``run_id`` y sobreviva a un
reinicio del proceso (H10-P1, H10-P4).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from sirius_engine.adapters.durable.journal import DirectorySyncError, append_durably, replay
from sirius_engine.domain.supervision import SupervisionDecision, SupervisionEpisode

_KIND_EPISODE = "supervision_episode_recorded"
_KIND_PENDING_RECORDED = "pending_escalation_recorded"
_KIND_PENDING_CLEARED = "pending_escalation_cleared"


def _episode_to_record(episode: SupervisionEpisode) -> dict[str, Any]:
    return {
        "kind": _KIND_EPISODE,
        "run_id": episode.run_id,
        "work_id": episode.work_id,
        "paso": episode.paso,
        "intento": episode.intento,
        "observado": episode.observado,
        "decision": episode.decision.value,
        "motivo": episode.motivo,
        "resulting_run_id": episode.resulting_run_id,
        "recorded_at": episode.recorded_at.isoformat(),
    }


def _episode_from_record(record: Mapping[str, Any]) -> SupervisionEpisode:
    return SupervisionEpisode(
        run_id=record["run_id"],
        work_id=record["work_id"],
        paso=record["paso"],
        intento=record["intento"],
        observado=record["observado"],
        decision=SupervisionDecision(record["decision"]),
        motivo=record["motivo"],
        resulting_run_id=record["resulting_run_id"],
        recorded_at=datetime.fromisoformat(record["recorded_at"]),
    )


class DurableSupervisorJournal:
    """Implementación durable de :mod:`sirius_engine.ports.supervisor_journal`."""

    def __init__(self, journal_path: Path) -> None:
        self._journal_path = journal_path
        self._episodios: list[SupervisionEpisode] = []
        self._run_ids_atendidos: set[str] = set()
        #: work_id -> run_id que dejó la escalada pendiente de notificar.
        self._escaladas_pendientes: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        for record in replay(self._journal_path).valid_records:
            kind = record["kind"]
            if kind == _KIND_EPISODE:
                self._absorb_episode(_episode_from_record(record))
            elif kind == _KIND_PENDING_RECORDED:
                self._escaladas_pendientes[record["work_id"]] = record["run_id"]
            elif kind == _KIND_PENDING_CLEARED:
                self._escaladas_pendientes.pop(record["work_id"], None)

    def _absorb_episode(self, episode: SupervisionEpisode) -> None:
        self._episodios.append(episode)
        self._run_ids_atendidos.add(episode.run_id)

    def has_episode(self, run_id: str) -> bool:
        return run_id in self._run_ids_atendidos

    def record(self, episode: SupervisionEpisode) -> None:
        record = _episode_to_record(episode)
        try:
            append_durably(self._journal_path, record)
        except DirectorySyncError:
            # CODEX-001 (mismo razonamiento que `DurableWorkEngineStore`): el
            # registro ya quedó completo y con `fsync` en el propio fichero
            # -solo falló sincronizar su directorio padre-, así que el
            # episodio ya ocurrió de forma durable. Absorberlo en memoria
            # ahora evita que este índice diverja del diario en disco.
            self._absorb_episode(episode)
            raise
        self._absorb_episode(episode)

    def episodes(self) -> tuple[SupervisionEpisode, ...]:
        return tuple(self._episodios)

    def pending_escalation_run_id(self, work_id: str) -> str | None:
        return self._escaladas_pendientes.get(work_id)

    def record_pending_escalation(self, run_id: str, work_id: str) -> None:
        record = {"kind": _KIND_PENDING_RECORDED, "work_id": work_id, "run_id": run_id}
        try:
            append_durably(self._journal_path, record)
        except DirectorySyncError:
            self._escaladas_pendientes[work_id] = run_id
            raise
        self._escaladas_pendientes[work_id] = run_id

    def clear_pending_escalation(self, work_id: str) -> None:
        record = {"kind": _KIND_PENDING_CLEARED, "work_id": work_id}
        try:
            append_durably(self._journal_path, record)
        except DirectorySyncError:
            self._escaladas_pendientes.pop(work_id, None)
            raise
        self._escaladas_pendientes.pop(work_id, None)
