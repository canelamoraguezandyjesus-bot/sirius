"""Puerto de lectura estructural de un run de Actions (C1, incidencia #232, S3).

Distinto de :class:`~sirius_engine.ports.github_mirror.GitHubMirrorPort`
(A3, incidencia #193) a propósito: aquel puerto lee la vía GitHub de una
*incidencia* (metadatos, cuerpo, comentarios) más el estado a nivel de RUN de
un run de Actions asociado a una incidencia (p. ej. el run de Quality de su
PR). Este puerto lee, para un ``run_id`` que el motor despachó él mismo, la
señal ESTRUCTURAL que el spike S3 midió y que el nivel de RUN no expone:
``total_jobs`` -el campo que distingue "no arrancó" de "sigue vivo" (ver
``experiments/work_engine_spike_i1/RESULTADOS.md``, tabla "Cotas propuestas
para C1")-. Mezclar los dos puertos habría acoplado el espejo de solo lectura
de incidencias (A3, congelado) a una necesidad de un bloque posterior.

Reutiliza :class:`~sirius_engine.ports.github_mirror.LecturaEstado`: "leí y no
hay" frente a "no pude leer" es la misma distinción en los dos puertos
(H-2, ADR-053), y da igual qué se esté leyendo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sirius_engine.ports.github_mirror import LecturaEstado as LecturaEstado


@dataclass(frozen=True, slots=True)
class RunActionsSnapshot:
    """Los campos de S3-P1/S3-P2 que clasifican un run de Actions no terminado o terminado."""

    run_id: str
    #: ``"queued"``, ``"in_progress"`` o ``"completed"`` (campo ``status`` de la API).
    estado_run: str
    #: ``conclusion`` de la API; ``None`` mientras el run no ha terminado.
    conclusion: str | None
    #: ``total_jobs`` del endpoint ``/jobs``. ``None`` SOLO si esa lectura
    #: falló -distinto de ``0``, que es la señal estructural medida de "no
    #: arrancó" (S3-P1, filas 2 y 3).
    total_jobs: int | None


@dataclass(frozen=True, slots=True)
class LecturaRunActionsSnapshot:
    estado: LecturaEstado
    snapshot: RunActionsSnapshot | None = None
    error: str | None = None


class RunActionsProbe(Protocol):
    """Contrato que cualquier sonda estructural de runs de Actions debe satisfacer.

    Solo lectura: ningún método de este puerto escribe en GitHub (mismo
    principio que ``SoloLecturaEjecutor`` del spike I1, S3-P3), y ninguna
    prueba de este repositorio lo ejercita contra la red real (requisito 7).
    """

    def leer(self, *, repo: str, run_id: str) -> LecturaRunActionsSnapshot: ...
