"""Adapter real de escritura: credencial temprana y los dos verbos enumerados (C2-P4, C2-P5, #240).

``ejecutar`` se sustituye siempre por un doble que nunca invoca ``gh`` de
verdad (misma disciplina que ``test_github_cli_mirror.py``, requisito 7: sin
red, sin credenciales reales).
"""

from __future__ import annotations

import dataclasses
import inspect
import subprocess

import pytest

from sirius_engine.adapters.github_cli_writer import (
    CREDENCIAL_ENV_VAR,
    GitHubCliWriter,
    GitHubWriteError,
    MissingCredentialError,
)
from sirius_engine.ports.github_writer import IncidenciaCreada


def test_sin_credencial_en_el_entorno_falla_pronto_y_claro(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CREDENCIAL_ENV_VAR, raising=False)
    with pytest.raises(MissingCredentialError) as excinfo:
        GitHubCliWriter(ejecutar=lambda argv, token: pytest.fail("no debía ejecutar gh"))
    assert CREDENCIAL_ENV_VAR in str(excinfo.value)


def test_credencial_vacia_en_el_entorno_tambien_falla_pronto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CREDENCIAL_ENV_VAR, "")
    with pytest.raises(MissingCredentialError):
        GitHubCliWriter(ejecutar=lambda argv, token: pytest.fail("no debía ejecutar gh"))


def test_con_credencial_explicita_no_lee_el_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CREDENCIAL_ENV_VAR, raising=False)
    escritor = GitHubCliWriter(
        ejecutar=lambda argv, token: pytest.fail("no ejecuta"), token="t0k3n"
    )
    assert escritor.token == "t0k3n"


def test_crear_incidencia_invoca_gh_issue_create_con_el_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CREDENCIAL_ENV_VAR, "s3cr3t0")
    llamadas: list[tuple[list[str], str]] = []

    def _doble(argv: list[str], token: str) -> subprocess.CompletedProcess[str]:
        llamadas.append((argv, token))
        return subprocess.CompletedProcess(
            argv, returncode=0, stdout="https://github.com/acme/repo/issues/241\n", stderr=""
        )

    escritor = GitHubCliWriter(ejecutar=_doble)
    resultado = escritor.crear_incidencia(
        repo="acme/repo", titulo="[SIRIUS] título", cuerpo="cuerpo", etiquetas=("sirius:planned",)
    )
    assert resultado == IncidenciaCreada(numero=241, url="https://github.com/acme/repo/issues/241")
    assert len(llamadas) == 1
    argv, token = llamadas[0]
    assert argv[:2] == ["issue", "create"]
    assert "--repo" in argv and "acme/repo" in argv
    assert "--label" in argv and "sirius:planned" in argv
    assert token == "s3cr3t0"


def test_crear_incidencia_falla_claro_si_gh_devuelve_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CREDENCIAL_ENV_VAR, "s3cr3t0")

    def _doble(argv: list[str], token: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="HTTP 403")

    escritor = GitHubCliWriter(ejecutar=_doble)
    with pytest.raises(GitHubWriteError):
        escritor.crear_incidencia(repo="acme/repo", titulo="t", cuerpo="c", etiquetas=())


def test_aplicar_etiqueta_invoca_gh_issue_edit_add_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CREDENCIAL_ENV_VAR, "s3cr3t0")
    llamadas: list[list[str]] = []

    def _doble(argv: list[str], token: str) -> subprocess.CompletedProcess[str]:
        llamadas.append(argv)
        return subprocess.CompletedProcess(argv, returncode=0, stdout="", stderr="")

    escritor = GitHubCliWriter(ejecutar=_doble)
    escritor.aplicar_etiqueta(repo="acme/repo", numero=241, etiqueta="sirius:implement-requested")
    assert len(llamadas) == 1
    argv = llamadas[0]
    assert argv[:2] == ["issue", "edit"]
    assert "241" in argv
    assert "--add-label" in argv and "sirius:implement-requested" in argv


def test_aplicar_etiqueta_falla_claro_si_gh_devuelve_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CREDENCIAL_ENV_VAR, "s3cr3t0")

    def _doble(argv: list[str], token: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="404")

    escritor = GitHubCliWriter(ejecutar=_doble)
    with pytest.raises(GitHubWriteError):
        escritor.aplicar_etiqueta(repo="acme/repo", numero=1, etiqueta="x")


def test_el_adapter_real_solo_expone_los_dos_verbos_enumerados() -> None:
    # ``ejecutar`` y ``token`` son campos del dataclass -su valor por
    # defecto es una función, así que ``inspect.isfunction`` los confundiría
    # con un método-, no verbos de escritura: se excluyen explícitamente.
    campos = {campo.name for campo in dataclasses.fields(GitHubCliWriter)}
    metodos_publicos = {
        nombre
        for nombre, miembro in inspect.getmembers(GitHubCliWriter, predicate=inspect.isfunction)
        if not nombre.startswith("_") and nombre not in campos
    }
    assert metodos_publicos == {"crear_incidencia", "aplicar_etiqueta"}
