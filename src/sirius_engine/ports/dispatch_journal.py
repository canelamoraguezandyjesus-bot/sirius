"""Puerto del diario del despachador (C2, incidencia #240).

Hermano de :mod:`sirius_engine.ports.supervisor_journal` (C1): un episodio
de despacho por ``work_id`` -a diferencia de C1, que indexa por ``run_id``,
porque un ``WorkItem`` de clase ``programacion`` se despacha una única vez,
nunca por Run- y la misma disciplina de idempotencia: el diario es también
la fuente de la que el despachador lee si YA activó un ``work_id``, para que
dos pasadas sobre el mismo WorkItem produzcan una sola activación (C2-P3).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sirius_engine.domain.dispatch import DispatchEpisode


class DispatchJournal(Protocol):
    """Contrato que cualquier diario de despacho debe satisfacer."""

    def episode_for(self, work_id: str) -> DispatchEpisode | None:
        """El episodio ya registrado para ``work_id``, o ``None`` si nunca se despachó.

        Es el marcador de idempotencia (C2-P3): el despachador lo consulta
        ANTES de escribir nada, y si ya hay un episodio, devuelve ese mismo
        episodio en vez de repetir la activación.
        """
        ...

    def record(self, episode: DispatchEpisode) -> None:
        """Anexar un episodio. Append-only: nunca sobrescribe uno anterior."""
        ...

    def episodes(self) -> Sequence[DispatchEpisode]:
        """Todos los episodios registrados, en orden de escritura.

        Suficiente para reconstruir el episodio completo -qué orden, qué
        WorkItem, qué incidencia, qué etiqueta y cuándo- sin volver a
        consultar GitHub (C2-P6).
        """
        ...
