"""Adapter real del espejo: lee la vía GitHub con la CLI ``gh`` (A3, incidencia #193).

Una llamada por lectura, sin reintentos propios: el requisito de este bloque
es que un fallo se distinga de una ausencia (``sirius_engine.ports.github_mirror``),
no que se oculte tras una capa de reintentos que podría, ella misma, esconder
el fallo real. La robustez de reintento y de conmutación REST↔GraphQL YA
existe, probada en producción, en ``scripts/automation/sirius_issue.sh``; un
futuro consumidor que necesite esa robustez adicional puede envolver el
parámetro ``ejecutar`` de este adapter -es un punto de extensión explícito,
no una promesa implícita de esta clase.

``ejecutar`` es inyectable a propósito: ninguna prueba de este repositorio
puede acceder a la red (requisito 7), así que las pruebas de este adapter
sustituyen ``ejecutar`` por un doble que nunca invoca ``gh`` de verdad.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sirius_engine.ports.github_mirror import (
    Comentario,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    LecturaRunActions,
    MetadatosIncidencia,
    RunActions,
)

Ejecutor = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def _ejecutar_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *argv], capture_output=True, text=True, check=False, timeout=60)


def _lineas_json(salida: str) -> list[dict[str, object]]:
    """Cada línea no vacía de ``salida`` es un objeto JSON compacto (``@json``).

    Mismo formato que produce ``_sirius_comments_newest_first`` en
    ``sirius_issue.sh``: un objeto por línea, para que invertir orden o leer
    en streaming no dependa de que los cuerpos sean de una sola línea.
    """
    resultado: list[dict[str, object]] = []
    for linea in salida.splitlines():
        linea = linea.strip()
        if not linea:
            continue
        resultado.append(json.loads(linea))
    return resultado


@dataclass
class GitHubCliMirrorReader:
    """Implementación real de :class:`GitHubMirrorPort` sobre ``gh api``."""

    ejecutar: Ejecutor = _ejecutar_gh

    def _invocar(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self.ejecutar(argv)
        except (OSError, subprocess.SubprocessError) as exc:
            return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr=str(exc))

    def leer_metadatos(self, *, repo: str, numero: int) -> LecturaMetadatos:
        proceso = self._invocar(
            ["api", f"repos/{repo}/issues/{numero}", "--jq", "{title,state,labels}"]
        )
        if proceso.returncode != 0:
            return LecturaMetadatos(
                estado=LecturaEstado.NO_DISPONIBLE,
                error=proceso.stderr.strip() or "gh api devolvió un error",
            )
        try:
            crudo = json.loads(proceso.stdout)
            etiquetas = tuple(sorted(etiqueta["name"] for etiqueta in crudo.get("labels", [])))
            metadatos = MetadatosIncidencia(
                numero=numero,
                titulo=str(crudo.get("title") or ""),
                estado_gh=str(crudo.get("state") or "").lower(),
                etiquetas=etiquetas,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return LecturaMetadatos(estado=LecturaEstado.NO_DISPONIBLE, error=str(exc))
        return LecturaMetadatos(estado=LecturaEstado.OK, metadatos=metadatos)

    def leer_cuerpo(self, *, repo: str, numero: int) -> LecturaCuerpo:
        proceso = self._invocar(["api", f"repos/{repo}/issues/{numero}", "--jq", '.body // ""'])
        if proceso.returncode != 0:
            return LecturaCuerpo(
                estado=LecturaEstado.NO_DISPONIBLE,
                error=proceso.stderr.strip() or "gh api devolvió un error",
            )
        return LecturaCuerpo(estado=LecturaEstado.OK, cuerpo=proceso.stdout.rstrip("\n"))

    def leer_comentarios(self, *, repo: str, numero: int) -> LecturaComentarios:
        proceso = self._invocar(
            [
                "api",
                "--paginate",
                f"repos/{repo}/issues/{numero}/comments?per_page=100",
                "--jq",
                ".[] | {login: .user.login, association: .author_association, "
                "created_at: .created_at, body: .body} | @json",
            ]
        )
        if proceso.returncode != 0:
            return LecturaComentarios(
                estado=LecturaEstado.NO_DISPONIBLE,
                error=proceso.stderr.strip() or "gh api devolvió un error",
            )
        try:
            comentarios = tuple(
                Comentario(
                    autor_login=str(entrada["login"]),
                    autor_asociacion=str(entrada["association"]),
                    cuerpo=str(entrada.get("body") or ""),
                    creado_en=datetime.fromisoformat(
                        str(entrada["created_at"]).replace("Z", "+00:00")
                    ),
                )
                for entrada in _lineas_json(proceso.stdout)
            )
        except (KeyError, TypeError, ValueError) as exc:
            return LecturaComentarios(estado=LecturaEstado.NO_DISPONIBLE, error=str(exc))
        return LecturaComentarios(estado=LecturaEstado.OK, comentarios=comentarios)

    def leer_run_actions(self, *, repo: str, run_id: str) -> LecturaRunActions:
        proceso = self._invocar(
            [
                "api",
                f"repos/{repo}/actions/runs/{run_id}",
                "--jq",
                "{status,conclusion,head_sha,html_url}",
            ]
        )
        if proceso.returncode != 0:
            if "404" in proceso.stderr:
                # Leído: la API respondió, y de forma explícita "no existe".
                # Es ausencia real, no una lectura caída.
                return LecturaRunActions(estado=LecturaEstado.OK, run=None)
            return LecturaRunActions(
                estado=LecturaEstado.NO_DISPONIBLE,
                error=proceso.stderr.strip() or "gh api devolvió un error",
            )
        try:
            crudo = json.loads(proceso.stdout)
            run = RunActions(
                run_id=run_id,
                estado_run=str(crudo.get("status") or ""),
                conclusion=crudo.get("conclusion"),
                head_sha=crudo.get("head_sha"),
                url=crudo.get("html_url"),
            )
        except (json.JSONDecodeError, TypeError) as exc:
            return LecturaRunActions(estado=LecturaEstado.NO_DISPONIBLE, error=str(exc))
        return LecturaRunActions(estado=LecturaEstado.OK, run=run)
