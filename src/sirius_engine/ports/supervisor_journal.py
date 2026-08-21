"""Puerto del diario del supervisor (C1, incidencia #232).

Dos operaciones, deliberadamente separadas de
:class:`~sirius_engine.ports.store.WorkEngineStore`: ese puerto es el diario
de eventos del propio motor (transiciones tipadas de ``WorkItem``/``Run``);
este es el registro de **episodios de supervisión** (qué observó el
supervisor, qué decidió y por qué), y también la fuente de la que el
supervisor lee si YA actuó sobre un ``run_id`` -el marcador de idempotencia
que evita la doble acción (C1-P2), con la misma disciplina de marcadores que
``sirius_reconcile.sh`` usa para no repetir un aviso ya publicado-.

Un tercer grupo de operaciones (CODEX-001, ronda 3 de la incidencia #232)
correlaciona explícitamente una escalada pendiente de notificar con el
``run_id`` que la causó. Sin esa correlación, encontrar un ``WorkItem`` en
``NEEDS_DECISION`` no basta para saber si el causante es ESTE ``run_id`` u
otro motivo -un corte de presupuesto anterior, o un segundo ``Run`` perdido
en la misma pasada del supervisor-.
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

    def pending_escalation_run_id(self, work_id: str) -> str | None:
        """El ``run_id`` que dejó pendiente de notificar la escalada de ``work_id``, si lo hay.

        ``None`` si no hay ninguna escalada pendiente conocida -bien porque
        nunca hubo una, bien porque ya se entregó y se limpió con
        :meth:`clear_pending_escalation`-. Un ``WorkItem`` en
        ``NEEDS_DECISION`` para el que esto devuelve ``None`` (o un
        ``run_id`` distinto) no está demostrablemente correlacionado con el
        ``run_id`` que lo consulta: la transición pudo venir de otra causa
        (CODEX-001).
        """
        ...

    def record_pending_escalation(self, run_id: str, work_id: str) -> None:
        """Registrar que ``run_id`` acaba de transicionar ``work_id`` a ``NEEDS_DECISION``.

        Se llama justo después de que la mutación del almacén se confirme y
        ANTES de intentar la notificación, para que la correlación sobreviva
        aunque la notificación falle a continuación (misma disciplina que
        CODEX-004 ya exige para no perder la escalada).
        """
        ...

    def clear_pending_escalation(self, work_id: str) -> None:
        """Limpiar la marca de escalada pendiente tras entregar la notificación."""
        ...
