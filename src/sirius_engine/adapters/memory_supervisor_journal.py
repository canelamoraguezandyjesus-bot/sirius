"""Diario del supervisor en memoria (C1, incidencia #232).

Mismo nivel de madurez que :mod:`sirius_engine.adapters.memory_store` en A1:
suficiente para probar el comportamiento y para un proceso de una sola
ejecución. La representación durable, si hiciera falta, es una decisión
posterior -no la exige esta incidencia, que solo pide que el episodio "quede
en el diario", no que sobreviva a un reinicio del proceso-.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sirius_engine.domain.supervision import SupervisionEpisode


@dataclass
class InMemorySupervisorJournal:
    """Implementación en memoria del puerto :mod:`sirius_engine.ports.supervisor_journal`."""

    _episodios: list[SupervisionEpisode] = field(default_factory=list)
    _run_ids_atendidos: set[str] = field(default_factory=set)
    #: work_id -> run_id que dejó la escalada pendiente de notificar (CODEX-001).
    _escaladas_pendientes: dict[str, str] = field(default_factory=dict)

    def has_episode(self, run_id: str) -> bool:
        return run_id in self._run_ids_atendidos

    def record(self, episode: SupervisionEpisode) -> None:
        self._episodios.append(episode)
        self._run_ids_atendidos.add(episode.run_id)

    def episodes(self) -> tuple[SupervisionEpisode, ...]:
        return tuple(self._episodios)

    def pending_escalation_run_id(self, work_id: str) -> str | None:
        return self._escaladas_pendientes.get(work_id)

    def record_pending_escalation(self, run_id: str, work_id: str) -> None:
        self._escaladas_pendientes[work_id] = run_id

    def clear_pending_escalation(self, work_id: str) -> None:
        self._escaladas_pendientes.pop(work_id, None)
