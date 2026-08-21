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

    def has_episode(self, run_id: str) -> bool:
        return run_id in self._run_ids_atendidos

    def record(self, episode: SupervisionEpisode) -> None:
        self._episodios.append(episode)
        self._run_ids_atendidos.add(episode.run_id)

    def episodes(self) -> tuple[SupervisionEpisode, ...]:
        return tuple(self._episodios)
