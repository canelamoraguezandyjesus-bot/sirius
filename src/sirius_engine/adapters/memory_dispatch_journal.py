"""Diario del despachador en memoria (C2, incidencia #240).

Mismo nivel de madurez que :mod:`sirius_engine.adapters.memory_supervisor_journal`
en C1: suficiente para probar el comportamiento y para un proceso de una
sola ejecución. La representación durable, si hiciera falta, es una
decisión posterior -no la exige esta incidencia-.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sirius_engine.domain.dispatch import DispatchEpisode


@dataclass
class InMemoryDispatchJournal:
    """Implementación en memoria del puerto :mod:`sirius_engine.ports.dispatch_journal`."""

    _episodios: list[DispatchEpisode] = field(default_factory=list)
    _por_work_id: dict[str, DispatchEpisode] = field(default_factory=dict)

    def episode_for(self, work_id: str) -> DispatchEpisode | None:
        return self._por_work_id.get(work_id)

    def record(self, episode: DispatchEpisode) -> None:
        self._episodios.append(episode)
        self._por_work_id[episode.work_id] = episode

    def episodes(self) -> tuple[DispatchEpisode, ...]:
        return tuple(self._episodios)
