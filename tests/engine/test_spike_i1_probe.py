"""S3-P3 -- la sonda del spike I1 es de solo lectura, y se demuestra (incidencia #211).

Ninguna prueba de este módulo invoca `gh` de verdad (requisito 7 del
repositorio): todas sustituyen `ejecutar` por un doble. Lo que se comprueba
es que `SoloLecturaEjecutor` -el guarda que envuelve cualquier ejecutor real
o falso- rechaza cada forma de escritura ANTES de que el ejecutor interno
llegue a invocarse, y que los métodos reales de `GitHubActionsProbe` nunca
construyen un argv que el guarda rechace.
"""

from __future__ import annotations

import subprocess

import pytest
from experiments.work_engine_spike_i1.probe import (
    EscrituraProhibida,
    GitHubActionsProbe,
    LecturaEstado,
    SoloLecturaEjecutor,
)

_REPO = "owner/repo"


def _proceso(
    argv: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


class _EjecutorContador:
    """Doble que cuenta cuántas veces se le invocó de verdad, para demostrar que
    una llamada rechazada nunca llega hasta aquí."""

    def __init__(self, stdout: str = "{}") -> None:
        self.llamadas: list[list[str]] = []
        self.stdout = stdout

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        self.llamadas.append(argv)
        return _proceso(argv, stdout=self.stdout)


@pytest.mark.parametrize(
    "argv",
    [
        ["api", "--method", "POST", "repos/owner/repo/actions/runs/1/cancel"],
        ["api", "-X", "DELETE", "repos/owner/repo/actions/runs/1"],
        ["api", "repos/owner/repo/actions/runs/1/cancel"],
        ["api", "repos/owner/repo/actions/runs/1/rerun"],
        ["api", "repos/owner/repo/issues/1/labels"],
        ["api", "repos/owner/repo/issues/1/comments"],
        ["api", "-f", "body=hola", "repos/owner/repo/issues/1/comments"],
        ["issue", "comment", "1", "--body", "hola"],
        # Formas unidas de `--method`/`-X`: `gh` las acepta igual que las
        # separadas por espacio (CODEX-001, incidencia #211, PR #212).
        ["api", "--method=DELETE", "repos/owner/repo/actions/runs/1"],
        ["api", "-XDELETE", "repos/owner/repo/actions/runs/1"],
        ["api", "-fbody=hola", "repos/owner/repo/issues/1/comments"],
        ["api", "-Fbody=hola", "repos/owner/repo/issues/1/comments"],
        ["api", "--input=body.json", "repos/owner/repo/actions/runs/1/cancel"],
        # Banderas cortas agrupadas: pflag deja anteponer "-i" (booleana) a una
        # bandera que toma valor, así que "-iXDELETE" equivale a "-i -X DELETE"
        # aunque el argumento no empiece por "-X" (CODEX-001, incidencia #211,
        # PR #212).
        ["api", "-iXDELETE", "repos/owner/repo/actions/runs/1"],
        ["api", "-ifbody=hola", "repos/owner/repo/issues/1/comments"],
        ["api", "-iFbody=hola", "repos/owner/repo/issues/1/comments"],
        [],
    ],
)
def test_solo_lectura_ejecutor_rechaza_toda_forma_de_escritura(argv: list[str]) -> None:
    contador = _EjecutorContador()
    guardado = SoloLecturaEjecutor(interno=contador)

    with pytest.raises(EscrituraProhibida):
        guardado(argv)

    assert contador.llamadas == [], "la llamada rechazada no debe llegar nunca al ejecutor interno"


@pytest.mark.parametrize(
    "argv",
    [
        ["api", "repos/owner/repo/actions/runs/1"],
        ["api", "repos/owner/repo/actions/runs/1/jobs"],
        ["api", "--silent", "repos/owner/repo/actions/runs/1/logs"],
        ["api", "rate_limit"],
        ["api", "--paginate", "repos/owner/repo/actions/runs?per_page=100"],
        # "-i" (--include) es la única bandera corta booleana de `gh api`: sola,
        # sin nada agrupado detrás, sigue siendo una lectura legítima.
        ["api", "-i", "repos/owner/repo/actions/runs/1"],
    ],
)
def test_solo_lectura_ejecutor_permite_lecturas_normales(argv: list[str]) -> None:
    contador = _EjecutorContador()
    guardado = SoloLecturaEjecutor(interno=contador)

    guardado(argv)

    assert contador.llamadas == [argv]


def test_probe_envuelve_el_ejecutor_inyectado_con_el_guarda() -> None:
    contador = _EjecutorContador()
    sonda = GitHubActionsProbe(ejecutar=contador)

    with pytest.raises(EscrituraProhibida):
        sonda.ejecutar(["api", "--method", "POST", "repos/owner/repo/actions/runs/1/cancel"])

    assert contador.llamadas == []


def test_leer_run_ok() -> None:
    contador = _EjecutorContador(stdout='{"status": "completed", "conclusion": "success"}')
    sonda = GitHubActionsProbe(ejecutar=contador)

    lectura = sonda.leer_run(repo=_REPO, run_id="1")

    assert lectura.estado is LecturaEstado.OK
    assert lectura.datos == {"status": "completed", "conclusion": "success"}
    assert contador.llamadas == [["api", "repos/owner/repo/actions/runs/1"]]


def test_leer_run_404_es_no_encontrado_no_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="gh: Not Found (HTTP 404)")

    sonda = GitHubActionsProbe(ejecutar=ejecutar)

    lectura = sonda.leer_run(repo=_REPO, run_id="999")

    assert lectura.estado is LecturaEstado.NO_ENCONTRADO


def test_leer_run_fallo_de_proceso_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="HTTP 503")

    sonda = GitHubActionsProbe(ejecutar=ejecutar)

    lectura = sonda.leer_run(repo=_REPO, run_id="1")

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
    assert "503" in (lectura.error or "")


def test_leer_run_json_invalido_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, stdout="no-es-json")

    sonda = GitHubActionsProbe(ejecutar=ejecutar)

    lectura = sonda.leer_run(repo=_REPO, run_id="1")

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE


def test_leer_jobs_usa_el_endpoint_de_jobs() -> None:
    contador = _EjecutorContador(stdout='{"total_count": 0, "jobs": []}')
    sonda = GitHubActionsProbe(ejecutar=contador)

    lectura = sonda.leer_jobs(repo=_REPO, run_id="1")

    assert lectura.estado is LecturaEstado.OK
    assert contador.llamadas == [["api", "repos/owner/repo/actions/runs/1/jobs"]]


def test_leer_rate_limit_usa_el_endpoint_dedicado() -> None:
    contador = _EjecutorContador(stdout='{"resources": {"core": {"remaining": 4999}}}')
    sonda = GitHubActionsProbe(ejecutar=contador)

    lectura = sonda.leer_rate_limit()

    assert lectura.estado is LecturaEstado.OK
    assert contador.llamadas == [["api", "rate_limit"]]


def test_leer_logs_ok_nunca_decodifica_el_cuerpo() -> None:
    """`--silent` es la pieza que evita el problema: el cuerpo real de
    `.../logs` es un zip binario, y decodificarlo como texto puede fallar
    con contenido real (aunque un zip vacío de marcador de posición
    decodifique por casualidad)."""
    contador = _EjecutorContador()
    sonda = GitHubActionsProbe(ejecutar=contador)

    lectura = sonda.leer_logs(repo=_REPO, run_id="1")

    assert lectura.estado is LecturaEstado.OK
    assert contador.llamadas == [["api", "--silent", "repos/owner/repo/actions/runs/1/logs"]]


def test_leer_logs_404_es_un_hecho_no_un_error_de_la_sonda() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="gh: Not Found (HTTP 404)")

    sonda = GitHubActionsProbe(ejecutar=ejecutar)

    lectura = sonda.leer_logs(repo=_REPO, run_id="1")

    assert lectura.estado is LecturaEstado.NO_ENCONTRADO
    assert lectura.error is None


def test_leer_logs_fallo_real_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="HTTP 503")

    sonda = GitHubActionsProbe(ejecutar=ejecutar)

    lectura = sonda.leer_logs(repo=_REPO, run_id="1")

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
    assert "503" in (lectura.error or "")
