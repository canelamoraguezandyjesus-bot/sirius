"""Adapter real de escritura: crea incidencias y aplica etiquetas con la CLI ``gh`` (C2, #240).

Hermano de :mod:`sirius_engine.adapters.github_cli_mirror` (A3, solo
lectura): misma disciplina de ``ejecutar`` inyectable para que ninguna
prueba de este repositorio pueda tocar la red de verdad, mismo patrón de
``subprocess.run`` sin reintentos propios -la robustez de reintento ya vive,
probada, en ``scripts/automation/sirius_issue.sh``-.

La diferencia que importa es la identidad: este adapter ESCRIBE, y el
contrato exige que la credencial con la que escribe (``SIRIUS_BOT_TOKEN``,
la misma que usan los workflows) se lea del entorno del proceso, con un
fallo claro y temprano si falta -nunca a mitad de una escritura-. Cablear
esa variable en un workflow de GitHub Actions está fuera de este bloque
(incidencia #240, límite explícito): esa parte la hace después una sesión
interactiva (ADR-002).

Solo dos verbos, y ninguno más (:class:`~sirius_engine.ports.github_writer.GitHubWriterPort`):
crear una incidencia, aplicar una etiqueta.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from os import environ

from sirius_engine.ports.github_writer import IncidenciaCreada

#: El nombre exacto de la variable de entorno que trae la credencial de
#: escritura (misma identidad que ``secrets.SIRIUS_BOT_TOKEN`` en los
#: workflows, ver ``.github/workflows/*.yml``). Este adapter la lee del
#: entorno del proceso: nunca la deriva, nunca la sustituye por otra.
CREDENCIAL_ENV_VAR = "SIRIUS_BOT_TOKEN"

Ejecutor = Callable[[list[str], str], "subprocess.CompletedProcess[str]"]

_ISSUE_URL_RE = re.compile(r"/issues/(\d+)\s*$")


class MissingCredentialError(Exception):
    """La credencial de escritura no está en el entorno: fallo pronto y claro (C2-P5)."""

    def __init__(self, env_var: str) -> None:
        super().__init__(
            f"falta la variable de entorno {env_var!r}: sin ella el adapter de escritura "
            "no puede autenticarse ante GitHub, y no hay ningún valor por defecto seguro. "
            "Este fallo ocurre AL CONSTRUIR el adapter, antes de cualquier escritura."
        )
        self.env_var = env_var


class GitHubWriteError(Exception):
    """``gh`` devolvió un error al intentar una de las dos escrituras enumeradas."""

    def __init__(self, comando: list[str], mensaje: str) -> None:
        super().__init__(f"'gh {' '.join(comando)}' falló: {mensaje}")
        self.comando = comando
        self.mensaje = mensaje


def _ejecutar_gh(argv: list[str], token: str) -> subprocess.CompletedProcess[str]:
    entorno = dict(environ)
    entorno["GH_TOKEN"] = token
    return subprocess.run(
        ["gh", *argv], capture_output=True, text=True, check=False, timeout=60, env=entorno
    )


def _leer_credencial() -> str:
    token = environ.get(CREDENCIAL_ENV_VAR)
    if not token:
        raise MissingCredentialError(CREDENCIAL_ENV_VAR)
    return token


@dataclass
class GitHubCliWriter:
    """Implementación real de :class:`~sirius_engine.ports.github_writer.GitHubWriterPort`.

    ``token`` es inyectable para pruebas; si se omite, se lee de
    :data:`CREDENCIAL_ENV_VAR` al construir -no en el primer uso-, para que
    la ausencia de credencial falle ANTES de que este objeto exista, nunca a
    mitad de una escritura ya empezada (C2-P5).
    """

    ejecutar: Ejecutor = field(default=_ejecutar_gh)
    token: str = field(default_factory=_leer_credencial)

    def __post_init__(self) -> None:
        if not self.token:
            raise MissingCredentialError(CREDENCIAL_ENV_VAR)

    def _invocar(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        return self.ejecutar(argv, self.token)

    def crear_incidencia(
        self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
    ) -> IncidenciaCreada:
        argv = ["issue", "create", "--repo", repo, "--title", titulo, "--body", cuerpo]
        for etiqueta in etiquetas:
            argv += ["--label", etiqueta]
        proceso = self._invocar(argv)
        if proceso.returncode != 0:
            raise GitHubWriteError(argv, proceso.stderr.strip() or "gh devolvió un error")
        url = proceso.stdout.strip().splitlines()[-1].strip() if proceso.stdout.strip() else ""
        match = _ISSUE_URL_RE.search(url)
        if match is None:
            raise GitHubWriteError(
                argv, f"no se pudo extraer el número de incidencia de la salida: {url!r}"
            )
        return IncidenciaCreada(numero=int(match.group(1)), url=url)

    def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
        argv = ["issue", "edit", str(numero), "--repo", repo, "--add-label", etiqueta]
        proceso = self._invocar(argv)
        if proceso.returncode != 0:
            raise GitHubWriteError(argv, proceso.stderr.strip() or "gh devolvió un error")
