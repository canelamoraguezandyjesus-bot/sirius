"""Observador real del mundo para el barrido de recuperación (C1, incidencia #232).

Implementación real de :class:`~sirius_engine.ports.world.RunWorldObserver`
(A2, incidencia #186): hasta esta incidencia solo existía un doble de
pruebas. Traduce lo que :class:`~sirius_engine.ports.run_actions_probe.RunActionsProbe`
lee de la API de Actions a un :class:`~sirius_engine.ports.world.RunWorldObservation`,
con la clasificación que el spike S3 midió (``experiments/work_engine_spike_i1/RESULTADOS.md``,
tabla "borde x observación").

**La cota de `LOST` no se inventa aquí.** S3 declaró NO CONCLUYENTE cualquier
umbral de duración derivado de `total_jobs==0`: una lectura puntual no
distingue un run recién encolado de uno atascado 48 h (mismo estado
observable). Este observador no intenta esa distinción con un número nuevo;
usa la única cota absoluta que el dominio ya tenía antes de esta incidencia,
``Run.deadline`` (arquitectura §3.3) -así que la decisión de LOST sigue
perteneciendo enteramente a :meth:`~sirius_engine.domain.run.Run.mark_lost`
vía :func:`sirius_engine.recovery.run_recovery_sweep`, este observador solo
reporta ``LOST`` cuando la ambigüedad estructural coincide con el deadline ya
vencido-.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius_engine.domain.run import CancellationStatus, Run
from sirius_engine.ports.github_mirror import LecturaEstado
from sirius_engine.ports.run_actions_probe import RunActionsProbe, RunActionsSnapshot
from sirius_engine.ports.world import RemoteRunStatus, RunWorldObservation

#: Conclusiones de `completed` medidas o razonablemente esperables que se
#: traducen a un desenlace concluyente. Cualquier otra (`action_required`,
#: `neutral`, `stale`...) no se adivina: cae al `UNKNOWN` explícito de abajo.
_CONCLUSIONES_DE_FALLO = frozenset({"failure", "timed_out"})


def _clasificar(run: Run, snapshot: RunActionsSnapshot, *, now: datetime) -> RunWorldObservation:
    if snapshot.estado_run != "completed":
        # `queued` o `in_progress`: todavía no hay desenlace remoto.
        if snapshot.total_jobs is None:
            return RunWorldObservation(
                status=RemoteRunStatus.UNKNOWN,
                diagnostico=f"no se pudo leer total_jobs del run {run.run_id}",
            )
        if snapshot.total_jobs == 0 and now >= run.deadline:
            # S3-P1, fila 2 ("no arrancado, perpetuo"): sin ningún job creado
            # y con la cota absoluta del Run ya vencida. No es una duración
            # inventada -es la misma `Run.deadline` que ya regía antes de
            # esta incidencia-, solo la lectura estructural que confirma que
            # no hay nada más que esperar.
            return RunWorldObservation(
                status=RemoteRunStatus.LOST,
                diagnostico=(
                    f"run {run.run_id} sigue sin crear ningún job (total_jobs=0) y su "
                    "deadline ya venció"
                ),
            )
        return RunWorldObservation(status=RemoteRunStatus.PENDING)

    conclusion = snapshot.conclusion
    if conclusion == "success":
        # La API de Actions no expone el resultado estructurado del Worker
        # (eso vive en el veredicto/PR, fuera de este puerto): se reporta
        # SUCCEEDED sin `resultado` legible, y el barrido de recuperación ya
        # trata eso como observación inutilizable (H-2, ADR-053) en vez de
        # inventar un resultado vacío.
        return RunWorldObservation(status=RemoteRunStatus.SUCCEEDED, resultado=None)
    if conclusion == "skipped":
        # S3-P1, fila 4: se creó un job pero su `if:` no se cumplió. Ningún
        # trabajo real se ejecutó -desenlace corregible, no una pérdida
        # ambigua-, así que se trata como fallo con diagnóstico explícito.
        return RunWorldObservation(
            status=RemoteRunStatus.FAILED,
            diagnostico=f"run {run.run_id}: conclusion=skipped (la condición `if:` no se cumplió)",
        )
    if conclusion == "cancelled":
        if snapshot.total_jobs == 0:
            # S3-P1, fila 3: cancelado antes de crear ningún job -"no
            # arrancó", no "se perdió"-.
            return RunWorldObservation(
                status=RemoteRunStatus.FAILED,
                diagnostico=f"run {run.run_id}: cancelado sin llegar a crear ningún job",
            )
        if run.cancellation_status is CancellationStatus.UNCONFIRMED:
            # S3-P1, fila 1: cancelado con trabajo real (total_jobs>0), y el
            # motor SÍ había pedido esta cancelación (protocolo en dos
            # tiempos, §3.3).
            return RunWorldObservation(status=RemoteRunStatus.CANCELLED)
        # Cancelado con trabajo real, pero el motor nunca pidió `CANCEL`:
        # aislamiento externo, no una cancelación propia. `_reconcile_run`
        # rechaza cerrar como CANCELLED sin la petición previa (H-2 aplicado
        # a la cancelación), así que se reporta como pérdida.
        return RunWorldObservation(
            status=RemoteRunStatus.LOST,
            diagnostico=(
                f"run {run.run_id}: cancelado externamente, sin `CANCEL` pedido por el motor"
            ),
        )
    if conclusion in _CONCLUSIONES_DE_FALLO:
        # S3-P1, fila 6 (`failure`); `timed_out` no está en la tabla medida
        # pero es la misma familia de desenlace concluyente que `failure`.
        return RunWorldObservation(
            status=RemoteRunStatus.FAILED, diagnostico=f"run {run.run_id}: conclusion={conclusion}"
        )
    return RunWorldObservation(
        status=RemoteRunStatus.UNKNOWN,
        diagnostico=f"run {run.run_id}: conclusion={conclusion!r} no reconocida por S3",
    )


@dataclass
class GitHubActionsRunObserver:
    """Implementación real de :class:`~sirius_engine.ports.world.RunWorldObserver`."""

    probe: RunActionsProbe
    repo: str

    def check_run(self, run: Run, *, now: datetime) -> RunWorldObservation:
        lectura = self.probe.leer(repo=self.repo, run_id=run.run_id)
        if lectura.estado is LecturaEstado.NO_DISPONIBLE:
            return RunWorldObservation(
                status=RemoteRunStatus.UNKNOWN,
                diagnostico=lectura.error or "lectura no disponible",
            )
        if lectura.snapshot is None:
            return RunWorldObservation(
                status=RemoteRunStatus.UNKNOWN,
                diagnostico=f"el run {run.run_id} no aparece en la API de Actions",
            )
        return _clasificar(run, lectura.snapshot, now=now)
