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
reporta ``LOST`` cuando el run no tiene un desenlace remoto concluyente
(``completed``) y esa misma cota absoluta ya venció -sin condicionarlo a la
ambigüedad de ``total_jobs==0``: la arquitectura (§3.3, líneas 179-183) exige
la cota como absoluta también para un job que sí llegó a arrancar-.
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
        if now >= run.deadline:
            # Arquitectura §3.3 (líneas 179-183): "LOST: el supervisor no
            # obtiene un STATUS concluyente y la cota absoluta vence" -sin
            # condicionar eso a `total_jobs==0`. Un job que sí llegó a
            # arrancar (`total_jobs>0`) y sigue `in_progress`/`queued` tras
            # el deadline es exactamente esa falta de desenlace concluyente;
            # no es la ambigüedad de S3-P1 fila 2 (esa es solo "no arrancó"),
            # pero la misma cota absoluta ya vencida se aplica igual.
            if snapshot.total_jobs == 0:
                diagnostico = (
                    f"run {run.run_id} sigue sin crear ningún job (total_jobs=0) y su "
                    "deadline ya venció"
                )
            else:
                diagnostico = (
                    f"run {run.run_id} sigue sin desenlace concluyente "
                    f"(total_jobs={snapshot.total_jobs}) y su deadline ya venció"
                )
            return RunWorldObservation(status=RemoteRunStatus.LOST, diagnostico=diagnostico)
        return RunWorldObservation(status=RemoteRunStatus.PENDING)

    conclusion = snapshot.conclusion
    if conclusion == "success":
        # La API de Actions no expone el WorkResult estructurado del Worker
        # (eso vive en el veredicto/PR, fuera de este puerto), y este
        # Adapter no tiene ninguna vía de resultados que lo lea. Un
        # `WorkResult` ausente o ilegible nunca se interpreta como éxito
        # (arquitectura §5.1, líneas 273-286): se cierra como FAILED con
        # diagnóstico, igual que el patrón de `sirius_apply_verdict.sh`.
        # Reportar SUCCEEDED con `resultado=None` dejaba el Run vivo para
        # siempre -`recovery.py` trata esa combinación como observación
        # inutilizable, y ningún observador futuro va a poder leer un
        # resultado que este puerto nunca supo obtener-.
        return RunWorldObservation(
            status=RemoteRunStatus.FAILED,
            diagnostico=(
                f"run {run.run_id}: conclusion=success pero no hay una vía de resultados "
                "que confirme un WorkResult estructurado"
            ),
        )
    if conclusion == "skipped":
        # S3-P1, fila 4: se creó un job pero su `if:` no se cumplió. Ningún
        # trabajo real se ejecutó -desenlace corregible, no una pérdida
        # ambigua-, así que se trata como fallo con diagnóstico explícito.
        return RunWorldObservation(
            status=RemoteRunStatus.FAILED,
            diagnostico=f"run {run.run_id}: conclusion=skipped (la condición `if:` no se cumplió)",
        )
    if conclusion == "cancelled":
        if snapshot.total_jobs is None:
            # La lectura de `/jobs` falló para un run ya `completed`: sin
            # `total_jobs` no se puede distinguir la fila 3 (cancelado antes
            # de arrancar) de la fila 1 (cancelado con trabajo real), y cada
            # una cierra distinto. No se adivina -mismo principio que la
            # rama de arriba para el run no terminado-: se reporta UNKNOWN.
            return RunWorldObservation(
                status=RemoteRunStatus.UNKNOWN,
                diagnostico=f"run {run.run_id}: cancelado pero no se pudo leer total_jobs",
            )
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
