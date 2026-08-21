"""Sonda de solo lectura sobre runs de GitHub Actions (S3, spike I1, incidencia #211).

Mismo patrón que ``sirius_engine.adapters.github_cli_mirror`` (A3): una
llamada de ``gh api`` por lectura, ``ejecutar`` inyectable para que ninguna
prueba de este repositorio acceda a la red. La diferencia deliberada de este
módulo es ``SoloLecturaEjecutor``: un guarda que se ejecuta en cada llamada,
real o de prueba, y que hace la propiedad "esta sonda nunca escribe"
estructural en vez de una promesa leída en el código (S3-P3, incidencia
#211, nota de arranque §4 del ADR-046).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

Ejecutor = Callable[[list[str]], "subprocess.CompletedProcess[str]"]

# Sufijos de endpoint que la API de GitHub reserva a verbos que cambian
# estado (cancelar, relanzar, aprobar, despachar, etiquetar, comentar,
# fusionar, revisar) aunque se invoquen con GET implícito de `gh api`.
_ENDPOINTS_ESCRITURA = (
    "/cancel",
    "/rerun",
    "/rerun-failed-jobs",
    "/approve",
    "/dispatches",
    "/labels",
    "/comments",
    "/merge",
    "/reviews",
    "/force-cancel",
)


class EscrituraProhibida(RuntimeError):
    """La sonda intentó una llamada que no es de solo lectura."""


# LISTA BLANCA, no lista negra. Tres rondas de revisión (incidencia #211,
# PR #212) encontraron tres formas distintas de burlar la lista negra anterior
# -"--method=DELETE", luego "-XDELETE" pegado, luego "-iXDELETE" agrupado- y la
# tercera engañaba además a la detección del endpoint con `-H "Accept: ..."`.
# Tres defectos de la misma familia son la señal de ADR-001 para dejar de
# parchear y atacar la raíz: **intentar entender la gramática de banderas de
# `gh` es una carrera que se pierde**, porque basta una sintaxis no prevista.
#
# Aquí se invierte: no se enumera lo prohibido, se enumera lo permitido. La
# sonda solo necesita estas dos banderas, y no se acepta ninguna otra.
_BANDERAS_PERMITIDAS = frozenset({"--silent", "--paginate"})
# La propiedad que hace sólida la detección del endpoint, y que la versión
# anterior no tenía: **las dos banderas permitidas son booleanas y no consumen
# valor**. Por construcción, entonces, cualquier argumento que no empiece por
# "-" sólo puede ser el endpoint; ya no hay que adivinar cuál lo es. Si algún
# día hiciera falta una bandera CON valor, esta propiedad se rompe y hay que
# revisar esta función entera, no sólo añadirla al conjunto.


def _asegurar_solo_lectura(argv: list[str]) -> None:
    if not argv or argv[0] != "api":
        raise EscrituraProhibida(f"esta sonda solo invoca 'gh api ...': {argv!r}")
    posicionales: list[str] = []
    for arg in argv[1:]:
        if arg.startswith("-"):
            if arg not in _BANDERAS_PERMITIDAS:
                raise EscrituraProhibida(f"bandera no permitida {arg!r}: {argv!r}")
        else:
            posicionales.append(arg)
    if len(posicionales) != 1:
        raise EscrituraProhibida(f"se esperaba exactamente un endpoint: {argv!r}")
    endpoint_sin_query = posicionales[0].split("?", 1)[0]
    if any(sufijo in endpoint_sin_query for sufijo in _ENDPOINTS_ESCRITURA):
        raise EscrituraProhibida(f"endpoint de escritura prohibido: {argv!r}")


@dataclass
class SoloLecturaEjecutor:
    """Envuelve un :data:`Ejecutor` y bloquea cualquier llamada que no sea lectura.

    El guarda corre ANTES de invocar ``interno``: una llamada rechazada nunca
    llega a ``gh``, ni siquiera con el doble de pruebas.
    """

    interno: Ejecutor

    def __call__(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        _asegurar_solo_lectura(argv)
        return self.interno(argv)


def _ejecutar_gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *argv], capture_output=True, text=True, check=False, timeout=60)


class LecturaEstado(StrEnum):
    """Resultado de un intento de lectura, igual que ``github_mirror.LecturaEstado``.

    ``NO_ENCONTRADO`` es un tercer valor que ese puerto no necesita: para los
    registros de un run, un 404 es un HECHO observable (el run nunca produjo
    registros), no la ausencia de intento de leer ni un fallo de la sonda.
    Confundir los dos es exactamente lo que ADR-036 prohíbe.
    """

    OK = "ok"
    NO_ENCONTRADO = "no_encontrado"
    NO_DISPONIBLE = "no_disponible"


@dataclass(frozen=True, slots=True)
class LecturaJson:
    estado: LecturaEstado
    datos: dict[str, object] | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class LecturaLogs:
    """Solo el resultado HTTP: la sonda nunca descarga ni decodifica el cuerpo.

    El cuerpo de ``.../logs`` es un zip binario; decodificarlo como texto
    puede fallar con contenido real (a diferencia de un zip vacío de
    marcador de posición, que sí decodifica por casualidad). `--silent`
    evita el problema entero: no hace falta el cuerpo para saber si hay
    registros, solo el código HTTP.
    """

    estado: LecturaEstado
    error: str | None = None


@dataclass
class GitHubActionsProbe:
    """Adapter real de la sonda. ``ejecutar`` es inyectable (requisito de pruebas sin red)."""

    ejecutar: Ejecutor = field(default=_ejecutar_gh)

    def __post_init__(self) -> None:
        self.ejecutar = SoloLecturaEjecutor(self.ejecutar)

    def _invocar(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self.ejecutar(argv)
        except (OSError, subprocess.SubprocessError) as exc:
            return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr=str(exc))

    def _leer_json(self, endpoint: str) -> LecturaJson:
        proceso = self._invocar(["api", endpoint])
        if proceso.returncode != 0:
            if "404" in proceso.stderr:
                return LecturaJson(estado=LecturaEstado.NO_ENCONTRADO)
            return LecturaJson(
                estado=LecturaEstado.NO_DISPONIBLE,
                error=proceso.stderr.strip() or "gh api devolvió un error",
            )
        try:
            datos = json.loads(proceso.stdout)
        except json.JSONDecodeError as exc:
            return LecturaJson(estado=LecturaEstado.NO_DISPONIBLE, error=str(exc))
        return LecturaJson(estado=LecturaEstado.OK, datos=datos)

    def leer_run(self, *, repo: str, run_id: str) -> LecturaJson:
        return self._leer_json(f"repos/{repo}/actions/runs/{run_id}")

    def leer_jobs(self, *, repo: str, run_id: str) -> LecturaJson:
        return self._leer_json(f"repos/{repo}/actions/runs/{run_id}/jobs")

    def leer_rate_limit(self) -> LecturaJson:
        return self._leer_json("rate_limit")

    def leer_logs(self, *, repo: str, run_id: str) -> LecturaLogs:
        proceso = self._invocar(["api", "--silent", f"repos/{repo}/actions/runs/{run_id}/logs"])
        if proceso.returncode == 0:
            return LecturaLogs(estado=LecturaEstado.OK)
        if "404" in proceso.stderr or "Not Found" in proceso.stderr:
            return LecturaLogs(estado=LecturaEstado.NO_ENCONTRADO)
        return LecturaLogs(
            estado=LecturaEstado.NO_DISPONIBLE,
            error=proceso.stderr.strip() or "gh api devolvió un error",
        )
