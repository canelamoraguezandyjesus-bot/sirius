"""Adapter real del espejo sobre ``gh api`` (A3, incidencia #193).

``ejecutar`` se sustituye siempre por un doble: ninguna prueba de este
repositorio accede a la red (requisito 7). Lo que se comprueba es la
traducción entre lo que ``gh`` devolvería y los tipos del puerto -en
particular, que un fallo del proceso se traduce a ``NO_DISPONIBLE`` y NUNCA
a un valor vacío interpretado como ausencia (requisito 2).
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime

from sirius_engine.adapters.github_cli_mirror import GitHubCliMirrorReader
from sirius_engine.ports.github_mirror import LecturaEstado

_REPO = "owner/repo"


def _proceso(
    argv: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode=returncode, stdout=stdout, stderr=stderr)


def test_leer_metadatos_ok() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(
            argv,
            stdout='{"title": "Un título", "state": "OPEN", '
            '"labels": [{"name": "sirius:implementing"}, {"name": "otra"}]}',
        )

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_metadatos(repo=_REPO, numero=1)

    assert lectura.estado is LecturaEstado.OK
    assert lectura.metadatos is not None
    assert lectura.metadatos.titulo == "Un título"
    assert lectura.metadatos.estado_gh == "open"
    assert lectura.metadatos.etiquetas == ("otra", "sirius:implementing")


def test_leer_metadatos_fallo_de_proceso_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="HTTP 503")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_metadatos(repo=_REPO, numero=1)

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
    assert lectura.metadatos is None
    assert "503" in (lectura.error or "")


def test_leer_metadatos_json_invalido_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, stdout="no-es-json")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_metadatos(repo=_REPO, numero=1)
    assert lectura.estado is LecturaEstado.NO_DISPONIBLE


def test_leer_cuerpo_ok_transporta_el_autor_y_conserva_los_saltos_de_linea() -> None:
    """El cuerpo llega CON su autor, y en la misma llamada (ADR-051, defecto H-1).

    Dos cosas a la vez, porque el cambio de ``--jq`` las toca juntas:

    - ``user.login``/``author_association`` viajan en la misma respuesta que
      ``.body``, así que el filtro de confianza del cuerpo no cuesta ninguna
      llamada de red adicional. Se comprueba sobre el ``argv`` real.
    - la salida pasó de ser el cuerpo en crudo a ser un JSON, y un cuerpo
      multilínea tiene que sobrevivir intacto: con el ``rstrip("\\n")`` de
      antes sobre la salida cruda, el salto final del cuerpo se perdía.
    """
    argv_visto: list[list[str]] = []

    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        argv_visto.append(argv)
        return _proceso(
            argv,
            stdout='{"login": "canelamoraguezandyjesus-bot", "association": "OWNER", '
            '"body": "primera linea\\nsegunda linea\\n"}\n',
        )

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_cuerpo(repo=_REPO, numero=1)

    assert lectura.estado is LecturaEstado.OK
    assert lectura.cuerpo is not None
    assert lectura.cuerpo.autor_login == "canelamoraguezandyjesus-bot"
    assert lectura.cuerpo.autor_asociacion == "OWNER"
    assert lectura.cuerpo.texto == "primera linea\nsegunda linea\n"

    # Sobre el `argv`, no sobre la salida: el doble devuelve lo que le
    # digamos pase lo que pase en el `--jq`, así que una mutación que dejara
    # de PEDIR el autor sería invisible mirando solo `lectura`. Comprobado al
    # sembrarla (mutación M4 del ADR-051): la prueba no caía. Lo que el
    # adapter sí controla es la consulta que construye, y eso es lo que se
    # fija aquí.
    #
    # Límite que esto NO cubre, y queda escrito: ninguna prueba de este
    # repositorio ejecuta `gh` ni `jq` (requisito 7), así que nada de aquí
    # demuestra que la salida real de ese `--jq` tenga la forma que
    # `json.loads` espera. Eso solo lo enseña la API real.
    (argv,) = argv_visto
    consulta = " ".join(argv)
    assert ".user.login" in consulta
    assert ".author_association" in consulta
    assert len(argv_visto) == 1, "el autor no puede costar una llamada de red de más"


def test_leer_cuerpo_json_invalido_es_no_disponible() -> None:
    """Una salida que no se puede interpretar es "no pude leer", nunca un cuerpo vacío.

    Mismo criterio que ``leer_metadatos`` (ADR-036): si esto devolviera
    ``OK`` con un ``CuerpoIncidencia`` de campos vacíos, el cuerpo saldría
    además "no de confianza" y desaparecería del historial sin que nadie
    pudiera distinguirlo de una incidencia sin cuerpo.
    """

    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, stdout="no-es-json")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_cuerpo(repo=_REPO, numero=1)

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
    assert lectura.cuerpo is None


def test_leer_comentarios_ok_una_linea_json_por_comentario() -> None:
    salida = (
        '{"login": "owner", "association": "OWNER", '
        '"created_at": "2026-08-18T05:13:24Z", "body": "hola"}\n'
        '{"login": "github-actions[bot]", "association": "NONE", '
        '"created_at": "2026-08-18T05:13:47Z", "body": "notificacion"}\n'
    )

    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, stdout=salida)

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_comentarios(repo=_REPO, numero=1)

    assert lectura.estado is LecturaEstado.OK
    assert lectura.comentarios is not None
    assert len(lectura.comentarios) == 2
    assert lectura.comentarios[0].autor_login == "owner"
    assert lectura.comentarios[1].autor_login == "github-actions[bot]"


def test_leer_comentarios_fallo_de_proceso_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="timeout")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_comentarios(repo=_REPO, numero=1)
    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
    assert lectura.comentarios is None


def test_leer_run_actions_ok() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(
            argv,
            stdout='{"status": "completed", "conclusion": "success", '
            '"head_sha": "deadbeef", "html_url": "https://x"}',
        )

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_run_actions(repo=_REPO, run_id="42")
    assert lectura.estado is LecturaEstado.OK
    assert lectura.run is not None
    assert lectura.run.conclusion == "success"


def test_leer_run_actions_404_es_ausencia_leida_no_fallo() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="gh: Not Found (HTTP 404)")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_run_actions(repo=_REPO, run_id="42")
    assert lectura.estado is LecturaEstado.OK
    assert lectura.run is None


def test_leer_run_actions_fallo_real_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="HTTP 503")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.leer_run_actions(repo=_REPO, run_id="42")
    assert lectura.estado is LecturaEstado.NO_DISPONIBLE


def test_excepcion_del_proceso_se_traduce_a_no_disponible() -> None:
    def ejecutar_que_revienta(argv: list[str]) -> subprocess.CompletedProcess[str]:
        raise TimeoutError("se agotó el tiempo")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar_que_revienta)
    lectura = lector.leer_metadatos(repo=_REPO, numero=1)
    assert lectura.estado is LecturaEstado.NO_DISPONIBLE


# --- El listado de runs por ventana temporal (ADR-151) ----------------------


_DESDE = datetime(2026, 9, 5, 5, 0, tzinfo=UTC)
_HASTA = datetime(2026, 9, 5, 7, 50, tzinfo=UTC)


def _run_json(*, run_id: int, path: str, inicio: str, fin: str, status: str = "completed") -> str:
    return (
        f'{{"id": {run_id}, "path": "{path}", "status": "{status}", '
        f'"run_started_at": "{inicio}", "updated_at": "{fin}"}}'
    )


def test_listar_runs_en_ventana_se_queda_con_los_que_empezaron_o_terminaron_dentro() -> None:
    """El filtro `created` de la API no basta, y por eso el adapter filtra otra vez.

    `created` solo sabe de la fecha de CREACIÓN, así que la consulta retrocede
    para no perder un run que terminó dentro habiendo empezado antes -y
    entonces hay que descartar a mano lo que se trajo de más-.
    """

    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(
            argv,
            stdout="\n".join(
                [
                    # Empezó dentro: cuenta.
                    _run_json(
                        run_id=1,
                        path=".github/workflows/implement-sirius-work.yml",
                        inicio="2026-09-05T06:00:00Z",
                        fin="2026-09-05T06:20:00Z",
                    ),
                    # Empezó ANTES de la ventana y terminó dentro: cuenta.
                    _run_json(
                        run_id=2,
                        path=".github/workflows/motor-sirius.yml",
                        inicio="2026-09-05T04:40:00Z",
                        fin="2026-09-05T05:10:00Z",
                    ),
                    # Empezó y terminó antes de la ventana: NO cuenta.
                    _run_json(
                        run_id=3,
                        path=".github/workflows/motor-sirius.yml",
                        inicio="2026-09-05T03:00:00Z",
                        fin="2026-09-05T03:30:00Z",
                    ),
                ]
            ),
        )

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.listar_runs_en_ventana(repo=_REPO, desde=_DESDE, hasta=_HASTA)

    assert lectura.estado is LecturaEstado.OK
    assert lectura.runs is not None
    assert [run.run_id for run in lectura.runs] == ["1", "2"]
    assert [run.workflow for run in lectura.runs] == [
        "implement-sirius-work.yml",
        "motor-sirius.yml",
    ], "el puerto promete el NOMBRE DEL FICHERO, que es como se excluye un workflow (ADR-144)"


def test_listar_runs_en_ventana_consulta_con_el_filtro_created_de_la_api() -> None:
    """La consulta retrocede una ventana entera, derivada de la propia ventana."""
    visto: list[list[str]] = []

    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        visto.append(argv)
        return _proceso(argv, stdout="")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lector.listar_runs_en_ventana(repo=_REPO, desde=_DESDE, hasta=_HASTA)

    (argv,) = visto
    assert f"repos/{_REPO}/actions/runs" in argv
    # 05:00 menos la ventana entera (2 h 50 min) = 02:10 del mismo día.
    assert "created=>=2026-09-05T02:10:00Z" in argv


def test_un_run_sin_terminar_solo_cuenta_si_empezo_dentro() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(
            argv,
            stdout="\n".join(
                [
                    _run_json(
                        run_id=4,
                        path=".github/workflows/motor-sirius.yml",
                        inicio="2026-09-05T04:00:00Z",
                        fin="2026-09-05T07:00:00Z",
                        status="in_progress",
                    ),
                    _run_json(
                        run_id=5,
                        path=".github/workflows/motor-sirius.yml",
                        inicio="2026-09-05T06:00:00Z",
                        fin="2026-09-05T07:00:00Z",
                        status="in_progress",
                    ),
                ]
            ),
        )

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.listar_runs_en_ventana(repo=_REPO, desde=_DESDE, hasta=_HASTA)

    assert lectura.runs is not None
    assert [run.run_id for run in lectura.runs] == ["5"], (
        "un run vivo que arrancó antes cruza la ventana, no cae en ella: `updated_at` "
        "de un run sin terminar no es la hora a la que terminó"
    )
    assert lectura.runs[0].fin is None


def test_listar_runs_en_ventana_vacio_es_ventana_tranquila_leida() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, stdout="")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.listar_runs_en_ventana(repo=_REPO, desde=_DESDE, hasta=_HASTA)

    assert lectura.estado is LecturaEstado.OK
    assert lectura.runs == ()


def test_listar_runs_en_ventana_fallo_de_proceso_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, returncode=1, stderr="HTTP 503")

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.listar_runs_en_ventana(repo=_REPO, desde=_DESDE, hasta=_HASTA)

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
    assert lectura.runs is None, "una lectura caída no puede parecerse a una ventana tranquila"
    assert "503" in (lectura.error or "")


def test_listar_runs_en_ventana_con_una_respuesta_ilegible_es_no_disponible() -> None:
    def ejecutar(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return _proceso(argv, stdout='{"id": 1, "path": ".github/workflows/x.yml"}')

    lector = GitHubCliMirrorReader(ejecutar=ejecutar)
    lectura = lector.listar_runs_en_ventana(repo=_REPO, desde=_DESDE, hasta=_HASTA)

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
    assert lectura.runs is None
