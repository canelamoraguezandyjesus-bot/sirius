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
from datetime import UTC, datetime

from sirius_engine.ports.github_mirror import (
    Comentario,
    CuerpoIncidencia,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    LecturaRunActions,
    LecturaRunsEnVentana,
    MetadatosIncidencia,
    RunActions,
    RunEnVentana,
)

Ejecutor = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def _ejecutar_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *argv], capture_output=True, text=True, check=False, timeout=60)


def _instante(texto: str) -> datetime:
    """Un instante de la API de GitHub (``2026-09-05T07:44:12Z``) como ``datetime`` con zona."""
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


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
        # El autor del cuerpo viaja en la MISMA respuesta que el cuerpo
        # (`user.login` y `author_association` de `repos/{repo}/issues/{n}`),
        # así que transportarlo no cuesta ninguna llamada de red adicional:
        # solo dos campos más en el `--jq`. Sin él, la proyección no puede
        # filtrar el cuerpo por confianza -defecto H-1, incidencia #215-.
        #
        # El `--jq` pasa a emitir un objeto en vez de una cadena, y por eso
        # aquí ya no vale `rstrip("\n")` sobre la salida cruda: el salto de
        # línea que se recorta es el del final del JSON, no el del cuerpo.
        proceso = self._invocar(
            [
                "api",
                f"repos/{repo}/issues/{numero}",
                "--jq",
                '{login: (.user.login // ""), association: (.author_association // ""), '
                'body: (.body // "")} | @json',
            ]
        )
        if proceso.returncode != 0:
            return LecturaCuerpo(
                estado=LecturaEstado.NO_DISPONIBLE,
                error=proceso.stderr.strip() or "gh api devolvió un error",
            )
        try:
            crudo = json.loads(proceso.stdout)
            cuerpo = CuerpoIncidencia(
                autor_login=str(crudo["login"]),
                autor_asociacion=str(crudo["association"]),
                texto=str(crudo.get("body") or ""),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return LecturaCuerpo(estado=LecturaEstado.NO_DISPONIBLE, error=str(exc))
        return LecturaCuerpo(estado=LecturaEstado.OK, cuerpo=cuerpo)

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

    def listar_runs_en_ventana(
        self, *, repo: str, desde: datetime, hasta: datetime
    ) -> LecturaRunsEnVentana:
        """Los runs que empezaron o terminaron dentro de ``[desde, hasta]``, vía ``gh api``.

        DOS PASOS, y el segundo no es redundante. El filtro ``created`` de la
        API solo sabe de la fecha de CREACIÓN del run, así que por sí solo
        dejaría fuera lo que el puerto promete: un run creado antes de
        ``desde`` que TERMINÓ dentro de la ventana. Por eso la consulta
        retrocede una ventana entera -``desde - (hasta - desde)``- y el filtro
        exacto se aplica aquí, sobre lo devuelto.

        Retroceder una ventana entera no es un número inventado: quien llama
        con la ventana de tolerancia de etiqueta de máquina la trae ya derivada
        del DOBLE del job más largo declarado
        (``ventana_tolerancia_etiqueta_maquina``), así que ningún run puede
        haber empezado más de media ventana antes de terminar. Una ventana
        entera lo cubre con holgura, y se deriva de lo que ya se recibe en vez
        de añadir una constante nueva.
        """
        margen = hasta - desde
        desde_consulta = (desde - margen).astimezone(UTC)
        proceso = self._invocar(
            [
                "api",
                "--paginate",
                f"repos/{repo}/actions/runs",
                "-f",
                f"created=>={desde_consulta.strftime('%Y-%m-%dT%H:%M:%SZ')}",
                "-f",
                "per_page=100",
                "--jq",
                ".workflow_runs[] | {id, path, status, "
                "run_started_at: (.run_started_at // .created_at), updated_at} | @json",
            ]
        )
        if proceso.returncode != 0:
            return LecturaRunsEnVentana(
                estado=LecturaEstado.NO_DISPONIBLE,
                error=proceso.stderr.strip() or "gh api devolvió un error",
            )
        try:
            todos = [
                RunEnVentana(
                    run_id=str(entrada["id"]),
                    # `path` viene como `.github/workflows/motor-sirius.yml`;
                    # el puerto promete el nombre del fichero, que es la forma
                    # con la que este repositorio excluye un workflow por su
                    # nombre (ADR-144).
                    workflow=str(entrada["path"]).rsplit("/", maxsplit=1)[-1],
                    inicio=_instante(str(entrada["run_started_at"])),
                    # La API no publica un `completed_at` en el listado:
                    # `updated_at` es su última modificación, y solo equivale a
                    # "cuándo terminó" cuando el run YA terminó. Un run vivo se
                    # declara sin fin en vez de estrenar una fecha que no es la
                    # que dice ser.
                    fin=(
                        _instante(str(entrada["updated_at"]))
                        if str(entrada.get("status")) == "completed"
                        else None
                    ),
                )
                for entrada in _lineas_json(proceso.stdout)
            ]
        except (KeyError, TypeError, ValueError) as exc:
            return LecturaRunsEnVentana(estado=LecturaEstado.NO_DISPONIBLE, error=str(exc))
        runs = tuple(
            run
            for run in todos
            if desde <= run.inicio <= hasta or (run.fin is not None and desde <= run.fin <= hasta)
        )
        return LecturaRunsEnVentana(estado=LecturaEstado.OK, runs=runs)
