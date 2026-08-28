"""Diario del despachador en memoria (C2, incidencia #240).

Mismo nivel de madurez que :mod:`sirius_engine.adapters.memory_supervisor_journal`
en C1: suficiente para probar el comportamiento y para un proceso de una
sola ejecución. La representación durable, si hiciera falta, es una
decisión posterior -no la exige esta incidencia-.

``_lock`` protege las tres operaciones que tienen que ser atómicas entre
sí -``reservar``, ``record``, ``liberar``- frente a dos hilos del mismo
proceso; es la misma unidad de concurrencia que ya asume el resto del
motor (un proceso, sin coordinación entre procesos) y basta para cerrar la
carrera de la revisión de la incidencia #240, ronda 2: dos hilos que
llaman a ``reservar`` para el mismo ``work_id`` nunca ven ambos
``obtenida=True``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from sirius_engine.domain.dispatch import DispatchEpisode
from sirius_engine.ports.dispatch_journal import Reserva


@dataclass
class InMemoryDispatchJournal:
    """Implementación en memoria del puerto :mod:`sirius_engine.ports.dispatch_journal`."""

    _episodios: list[DispatchEpisode] = field(default_factory=list)
    _por_work_id: dict[str, DispatchEpisode] = field(default_factory=dict)
    _en_curso: dict[str, threading.Event] = field(default_factory=dict)
    _intenciones: set[str] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def episode_for(self, work_id: str) -> DispatchEpisode | None:
        with self._lock:
            return self._por_work_id.get(work_id)

    def record_intencion(self, work_id: str) -> None:
        with self._lock:
            self._intenciones.add(work_id)

    def intencion_pendiente(self, work_id: str) -> bool:
        with self._lock:
            return work_id in self._intenciones and work_id not in self._por_work_id

    def record(self, episode: DispatchEpisode) -> None:
        with self._lock:
            self._episodios.append(episode)
            self._por_work_id[episode.work_id] = episode
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
