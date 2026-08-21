"""Puerto del diario del supervisor (C1, incidencia #232).

Dos operaciones, deliberadamente separadas de
:class:`~sirius_engine.ports.store.WorkEngineStore`: ese puerto es el diario
de eventos del propio motor (transiciones tipadas de ``WorkItem``/``Run``);
este es el registro de **episodios de supervisión** (qué observó el
supervisor, qué decidió y por qué), y también la fuente de la que el
supervisor lee si YA actuó sobre un ``run_id`` -el marcador de idempotencia
que evita la doble acción (C1-P2), con la misma disciplina de marcadores que
``sirius_reconcile.sh`` usa para no repetir un aviso ya publicado-.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sirius_engine.domain.supervision import SupervisionEpisode


class SupervisorJournal(Protocol):
    """Contrato que cualquier diario de supervisión debe satisfacer."""

    def has_episode(self, run_id: str) -> bool:
        """True si el supervisor ya registró una acción para este ``run_id``.

        Un ``Run`` solo llega a ``LOST`` una vez -es un estado terminal
        (``FINISHED``) y un ``Run`` nunca resucita, arquitectura §3.3-, así
        que preguntar por ``run_id`` basta: no hace falta ninguna otra clave
        para saber si ESTE atasco concreto ya se atendió.
        """
        ...

    def record(self, episode: SupervisionEpisode) -> None:
        """Anexar un episodio. Append-only: nunca sobrescribe uno anterior."""
        ...

    def episodes(self) -> Sequence[SupervisionEpisode]:
        """Todos los episodios registrados, en orden de escritura."""
        ...
