"""Puerto del diario del despachador (C2, incidencia #240).

Hermano de :mod:`sirius_engine.ports.supervisor_journal` (C1): un episodio
de despacho por ``work_id`` -a diferencia de C1, que indexa por ``run_id``,
porque un ``WorkItem`` de clase ``programacion`` se despacha una única vez,
nunca por Run- y la misma disciplina de idempotencia: el diario es también
la fuente de la que el despachador lee si YA activó un ``work_id``, para que
dos pasadas sobre el mismo WorkItem produzcan una sola activación (C2-P3).

``episode_for``/``record`` por sí solos no bastan para eso cuando dos
llamadas concurrentes existen: ambas pueden ver ``episode_for`` devolver
``None`` antes de que ninguna llame a ``record`` (revisión de la incidencia
#240, ronda 2). ``reservar``/``liberar`` cierran ese hueco -como máximo una
llamada obtiene el derecho de escribir; las demás reutilizan su episodio o
esperan a que termine-, sin coordinar nada fuera de este mismo diario.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from sirius_engine.domain.dispatch import DispatchEpisode


@dataclass(frozen=True, slots=True)
class Reserva:
    """El resultado de intentar reservar un ``work_id`` para despacharlo.

    Exactamente una de estas tres formas es cierta:

    - ``obtenida`` es ``True``: esta llamada ganó la reserva y debe seguir
      -proyectar, escribir en GitHub y, al terminar (con éxito o no),
      liberarla con :meth:`DispatchJournal.record` o
      :meth:`DispatchJournal.liberar`-.
    - ``episodio`` no es ``None``: ya había un episodio registrado; no hay
      nada que reservar ni que escribir, se reutiliza éste.
    - ``evento`` no es ``None``: otra llamada concurrente tiene la reserva
      en curso; ``evento.wait()`` se dispara en cuanto esa llamada termine
      (haya grabado episodio o lo haya liberado sin grabar).
    """

    obtenida: bool
    episodio: DispatchEpisode | None
    evento: threading.Event | None


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
        """Anexar un episodio. Append-only: nunca sobrescribe uno anterior.

        Libera, atómicamente con el anexado, la reserva obtenida con
        :meth:`reservar` para ``episode.work_id`` y despierta a cualquier
        llamada esperando en su ``evento``.
        """
        ...

    def episodes(self) -> Sequence[DispatchEpisode]:
        """Todos los episodios registrados, en orden de escritura.

        Suficiente para reconstruir el episodio completo -qué orden, qué
        WorkItem, qué incidencia, qué etiqueta y cuándo- sin volver a
        consultar GitHub (C2-P6).
        """
        ...

    def reservar(self, work_id: str) -> Reserva:
        """Reservar atómicamente el derecho de despachar ``work_id``.

        Como máximo una llamada concurrente recibe ``obtenida=True`` por
        cada ``work_id`` sin episodio registrado; el resto recibe el
        episodio ya existente o un ``evento`` que esperar (nunca ambas
        cosas a la vez que ``obtenida=True``).
        """
        ...

    def liberar(self, work_id: str) -> None:
        """Liberar una reserva obtenida con :meth:`reservar` sin grabar episodio.

        Para cuando una guarda posterior a la reserva (clase, estado, orden
        enlazada) rechaza el ``WorkItem`` o la escritura falla: la reserva
        no puede quedar en pie para siempre, o una llamada futura para el
        mismo ``work_id`` esperaría un ``evento`` que nunca se dispara.
        """
        ...
