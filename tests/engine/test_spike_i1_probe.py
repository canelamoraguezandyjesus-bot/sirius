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
from experiments.work_engine_spike_i1 import probe
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
        # Ronda 3 (CLAUDE-REVISOR-001): una bandera legítima que consume un
        # valor separado por espacio hacía que ese VALOR se tomara por el
        # endpoint, y el endpoint real -de escritura- no se llegaba a mirar.
        [
            "api",
            "-H",
            "Accept: application/vnd.github+json",
            "repos/owner/repo/actions/runs/1/cancel",
        ],
        ["api", "-q", ".id", "repos/owner/repo/actions/runs/1/rerun"],
        ["api", "--hostname", "github.com", "repos/owner/repo/issues/1/comments"],
        # Y la propiedad que sostiene la lista blanca: cualquier bandera que no
        # esté en ella se rechaza SIN mirar qué significa. Estas no son de
        # escritura; se rechazan igual, y ese es justo el punto -no se intenta
        # entender la gramática de `gh`, se acepta solo lo necesario.
        ["api", "-i", "repos/owner/repo/actions/runs/1"],
        ["api", "--jq", ".id", "repos/owner/repo/actions/runs/1"],
        ["api", "--verbose", "repos/owner/repo/actions/runs/1"],
        # Dos posicionales tampoco: con las banderas permitidas -todas
        # booleanas- un segundo argumento suelto no puede ser un valor, así que
        # o sobra o el argv no es el que la sonda cree estar mandando.
        ["api", "repos/owner/repo/actions/runs/1", "repos/owner/repo/issues/1/comments"],
        ["api", "--silent"],
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
        # "-i" ya NO figura aquí: se movió a la lista de rechazadas. Con lista
        # blanca, lo que la sonda no necesita no se permite, aunque sea
        # inofensivo. Es el precio -barato- de no tener que razonar nunca más
        # sobre la gramática de banderas de `gh`.
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


def test_el_guarda_aguanta_aunque_alguien_amplie_la_lista_blanca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La propiedad que hace sólida la detección del endpoint, fijada.

    Hoy las dos banderas permitidas son booleanas, así que "contar
    posicionales" y "coger el primer argumento sin guion" dan el mismo
    resultado: son indistinguibles y una mutación entre ambas no rompe nada.

    La diferencia aparece el día en que alguien añada a la lista blanca una
    bandera que SÍ consume valor -exactamente lo que el comentario de
    `_BANDERAS_PERMITIDAS` advierte-. Contando posicionales, ese valor cuenta
    como un segundo posicional y la llamada se rechaza; adivinando, el valor se
    confundiría con el endpoint y el endpoint real -de escritura- no se
    miraría nunca. Que es, literalmente, el defecto de la ronda 3.

    Esta prueba fija el comportamiento seguro sin esperar a que ocurra.
    """
    monkeypatch.setattr(probe, "_BANDERAS_PERMITIDAS", frozenset({"--silent", "--paginate", "-H"}))
    contador = _EjecutorContador()
    guardado = SoloLecturaEjecutor(interno=contador)

    with pytest.raises(EscrituraProhibida):
        guardado(
            [
                "api",
                "-H",
                "Accept: application/vnd.github+json",
                "repos/owner/repo/actions/runs/1/cancel",
            ]
        )

    assert contador.llamadas == []
