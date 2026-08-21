"""Adapter real de la sonda estructural: lee la vía GitHub con la CLI ``gh`` (C1, S3).

Mismo patrón que :mod:`sirius_engine.adapters.github_cli_mirror` (A3,
incidencia #193): una llamada por lectura, sin reintentos propios, con
``ejecutar`` inyectable para que ninguna prueba de este repositorio necesite
la red (requisito 7). Dos lecturas -run y jobs-, porque ``total_jobs`` (la
señal estructural que S3 midió) solo lo expone el segundo endpoint; el primer
endpoint no lo trae (ver ``ports/run_actions_probe.py`` para por qué esto no
vive en ``github_mirror.py``).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from sirius_engine.ports.github_mirror import LecturaEstado
from sirius_engine.ports.run_actions_probe import LecturaRunActionsSnapshot, RunActionsSnapshot

Ejecutor = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def _ejecutar_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *argv], capture_output=True, text=True, check=False, timeout=60)


@dataclass
class GitHubActionsRunProbe:
    """Implementación real de :class:`~sirius_engine.ports.run_actions_probe.RunActionsProbe`."""

    ejecutar: Ejecutor = _ejecutar_gh

    def _invocar(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self.ejecutar(argv)
        except (OSError, subprocess.SubprocessError) as exc:
            return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr=str(exc))

    def leer(self, *, repo: str, run_id: str) -> LecturaRunActionsSnapshot:
        proceso_run = self._invocar(
            ["api", f"repos/{repo}/actions/runs/{run_id}", "--jq", "{status,conclusion}"]
        )
        if proceso_run.returncode != 0:
            if "404" in proceso_run.stderr:
                # Leído: la API respondió, y de forma explícita "no existe".
                # Es ausencia real, no una lectura caída (mismo criterio que
                # `github_cli_mirror.leer_run_actions`).
                return LecturaRunActionsSnapshot(estado=LecturaEstado.OK, snapshot=None)
            return LecturaRunActionsSnapshot(
                estado=LecturaEstado.NO_DISPONIBLE,
                error=proceso_run.stderr.strip() or "gh api devolvió un error al leer el run",
            )
        try:
            crudo_run = json.loads(proceso_run.stdout)
            estado_run = str(crudo_run.get("status") or "")
            conclusion = crudo_run.get("conclusion")
        except (json.JSONDecodeError, TypeError) as exc:
            return LecturaRunActionsSnapshot(estado=LecturaEstado.NO_DISPONIBLE, error=str(exc))

        proceso_jobs = self._invocar(
            ["api", f"repos/{repo}/actions/runs/{run_id}/jobs", "--jq", ".total_count"]
        )
        total_jobs: int | None
        if proceso_jobs.returncode != 0:
            # La lectura del run sí se pudo leer; la de jobs no. `total_jobs`
            # queda `None` -"no pude leer esto", no "cero"- para que quien
            # clasifique no confunda una lectura caída con la señal
            # estructural de "no arrancó" (S3-P1: `total_jobs==0` es un hecho
            # medido, no lo que se afirma cuando falta el dato).
            total_jobs = None
        else:
            try:
                total_jobs = int(proceso_jobs.stdout.strip())
            except ValueError:
                total_jobs = None

        snapshot = RunActionsSnapshot(
            run_id=run_id, estado_run=estado_run, conclusion=conclusion, total_jobs=total_jobs
        )
        return LecturaRunActionsSnapshot(estado=LecturaEstado.OK, snapshot=snapshot)
