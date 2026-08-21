"""Adapter real de la sonda estructural sobre ``gh api`` (C1, incidencia #232).

Mismo principio que ``test_github_cli_mirror.py`` (A3): ``ejecutar`` siempre
sustituido por un doble -ninguna prueba de este repositorio toca la red
(requisito 7)-.
"""

from __future__ import annotations

import subprocess

from sirius_engine.adapters.github_actions_run_probe import GitHubActionsRunProbe
from sirius_engine.ports.run_actions_probe import LecturaEstado

_REPO = "owner/repo"


def _proceso(
    argv: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


def test_leer_ok_combina_run_y_jobs() -> None:
    argv_vistos: list[list[str]] = []

    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        argv_vistos.append(argv)
        if argv[1].endswith("/jobs"):
            return _proceso(argv, stdout="0\n")
        return _proceso(argv, stdout='{"status": "queued", "conclusion": null}')

    lectura = GitHubActionsRunProbe(ejecutar=ejecutar).leer(repo=_REPO, run_id="123")

    assert lectura.estado is LecturaEstado.OK
    assert lectura.snapshot is not None
    assert lectura.snapshot.estado_run == "queued"
    assert lectura.snapshot.conclusion is None
    assert lectura.snapshot.total_jobs == 0
    assert len(argv_vistos) == 2
    assert argv_vistos[0][1] == f"repos/{_REPO}/actions/runs/123"
    assert argv_vistos[1][1] == f"repos/{_REPO}/actions/runs/123/jobs"


def test_leer_run_404_es_ausencia_real_no_lectura_caida() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="gh: Not Found (HTTP 404)")

    lectura = GitHubActionsRunProbe(ejecutar=ejecutar).leer(repo=_REPO, run_id="999")

    assert lectura.estado is LecturaEstado.OK
    assert lectura.snapshot is None


def test_leer_run_fallo_de_proceso_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="HTTP 503")

    lectura = GitHubActionsRunProbe(ejecutar=ejecutar).leer(repo=_REPO, run_id="123")

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
    assert lectura.snapshot is None
    assert "503" in (lectura.error or "")


def test_leer_jobs_fallido_deja_total_jobs_en_none_no_en_cero() -> None:
    """`total_jobs=None` -"no pude leer"- nunca se confunde con `0` -"leí: no hay job"-."""

    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        if argv[1].endswith("/jobs"):
            return _proceso(argv, returncode=1, stderr="HTTP 503")
        return _proceso(argv, stdout='{"status": "in_progress", "conclusion": null}')

    lectura = GitHubActionsRunProbe(ejecutar=ejecutar).leer(repo=_REPO, run_id="123")

    assert lectura.estado is LecturaEstado.OK
    assert lectura.snapshot is not None
    assert lectura.snapshot.total_jobs is None


def test_leer_run_json_invalido_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, stdout="no-es-json")

    lectura = GitHubActionsRunProbe(ejecutar=ejecutar).leer(repo=_REPO, run_id="123")

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
