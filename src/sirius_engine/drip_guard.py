"""Guardián de goteo en vivo (incidencia #496, ADR-123).

Implementa la propuesta 1 de `§7` del informe de la mina
(`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md`): cuando la
revisión de una ronda N>1 publica un hallazgo que cita un fichero y una línea
concretos del repositorio, este módulo compara el head de la ronda 1 de la
misma incidencia con el head actual -exactamente el mecanismo que la mina usó
a mano en `§3.1`, `gh api repos/.../compare/{head1}...{headN}` restringido al
fichero citado- y decide si ese hallazgo huele a goteo: contenido que ya
estaba idéntico en la ronda 1 y que la revisión de entonces pudo haber visto.

**Esto SOLO informa.** No bloquea la ronda, no cambia ninguna transición de
estado del ciclo revisión-corrección y no descarta ningún hallazgo: el
hallazgo marcado se corrige exactamente igual que uno sin marcar (regla (a)
de la incidencia #496). La marca sirve para medir la tasa real en producción
antes de darle cualquier autoridad (criterio de la incidencia #267).

**Limitación conocida, declarada en vez de implementada** (ver ADR-123): la
mina documenta dos falsos positivos sobre su muestra completa (`§459` rondas
3 y 4, ver `§5`) en los que la línea citada es una línea de contexto sin
tocar, pero el hallazgo es legítimo porque una línea HERMANA del mismo hunk sí
cambió y reveló, solo en esa ronda, una inconsistencia con la línea citada.
Este guardián no distingue ese caso: una línea de contexto sin tocar dentro de
un hunk modificado se marca igual que una línea completamente fuera de todo
hunk. Detectar la excepción exigiría razonar sobre el contenido semántico del
cambio, no solo su posición en el diff -el tipo de heurística que el criterio
de entrada de la incidencia #267 pide medir antes de construir, no adivinar-.

El módulo es puro salvo por :func:`gh_compare_file`, la única función que
llama a `gh`. Todo lo demás recibe la comparación ya resuelta (o su fallo)
inyectada, para poder fijar el comportamiento con pruebas deterministas y sin
red.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

#: Mensaje exacto que pide el objetivo de la incidencia #496.
MENSAJE_POSIBLE_GOTEO = (
    "posible goteo: este contenido ya estaba idéntico en la ronda 1, ¿por qué no se vio entonces?"
)

#: Presupuesto de tiempo por defecto para TODAS las comparaciones de una
#: ronda (incidencia #501, CLAUDE-REVISOR-001). El paso que invoca este
#: guardián (`sirius_apply_verdict.sh`, vía `sirius_drip_guard_cli.py`) tiene
#: un `timeout-minutes: 10` en el workflow; 120s deja margen de sobra para el
#: resto del paso (leer el historial, aplicar el veredicto, publicar el
#: fallback informativo) incluso si cada comparación agota su propio
#: `timeout` de 30s. Una vez agotado, ninguna comparación nueva se intenta:
#: las observaciones restantes se resuelven a SIN_INFORMACION, nunca a "no
#: cambió" (regla (c) de la incidencia #496).
DEFAULT_TIME_BUDGET_SECONDS = 120.0

# Prefijo de `archivo` que parece una ruta de fichero del repositorio: letras,
# dígitos, `/`, `.`, `_`, `-`. No es suficiente por sí solo -"el" también
# encaja-, así que solo se acepta como ruta reconocible cuando además
# contiene un separador de directorio o una extensión (incidencia #523, G3):
# el adorno que los revisores añaden alrededor de la ruta real (nombre de
# función entre paréntesis, "en <sha>", "líneas NNN-MMM") nunca usa esos
# caracteres, así que el prefijo se detiene exactamente donde termina la ruta.
_RUTA_PREFIX_RE = re.compile(r"^[A-Za-z0-9/._-]+")

# Sufijo de línea (o rango) pegado directamente a una ruta reconocible:
# `scripts/x.py:120`, `scripts/x.py:120-134`, y con texto arbitrario detrás
# ("en <sha>", un nombre de función entre paréntesis). Solo se usa el primer
# número: es el que ancla la comparación mecánica de §3.1 del informe de la
# mina (el rango o el sha, cuando aparecen, describen un tramo o un commit
# citados a mano, no un hunk).
_LOCATION_SUFFIX_RE = re.compile(r"^:(\d+)(?:-\d+)?")

# Cita en prosa de una línea cuando no va pegada a la ruta con `:NNN`, tal
# como los revisores la escriben dentro de un paréntesis junto al nombre de
# la función: "línea 723", "líneas ~766-805". El signo `~` (aproximación) se
# tolera antes del número; el que preceda a la palabra "línea(s)" no importa,
# porque la búsqueda no ancla el inicio del texto.
_LOCATION_PROSE_RE = re.compile(r"l[ií]neas?\s*~?\s*(\d+)", re.IGNORECASE)


class DripVerdict(Enum):
    """Resultado de evaluar un único hallazgo contra el historial de rondas.

    Tres valores, no un booleano: una lectura fallida de la API de
    comparación (`SIN_INFORMACION`) tiene que ser un valor estructuralmente
    distinto de "el fichero no cambió" (`POSIBLE_GOTEO`), para que ningún
    fallo de lectura pueda convertirse en una marca por accidente de tipos
    (regla (c) de la incidencia #496).
    """

    POSIBLE_GOTEO = "posible_goteo"
    SIN_MARCA = "sin_marca"
    SIN_INFORMACION = "sin_informacion"


@dataclass(frozen=True, slots=True)
class FileCompareResult:
    """Resultado, YA LEÍDO con éxito, de comparar un fichero entre dos heads.

    ``changed=False`` es información positiva («el fichero no aparece en el
    diff»), y por eso este tipo solo existe cuando la lectura tuvo éxito: un
    fallo de lectura se representa con ``None``, nunca con este tipo, para
    que las dos situaciones no puedan confundirse.
    """

    changed: bool
    patch: str | None


#: Compara un fichero entre dos heads: (repo, head1, head2, ruta) -> resultado,
#: o ``None`` si la lectura falló (regla (c) de la incidencia #496: un fallo de
#: lectura NUNCA es "no hubo cambios").
CompareFetcher = Callable[[str, str, str, str], "FileCompareResult | None"]


def parse_archivo_location(archivo: object) -> tuple[str, int | None]:
    """Separa el ``archivo`` de un hallazgo en (ruta, línea).

    Los revisores adornan el campo ``archivo`` de formas que la lectura
    mecánica de §3.1 del informe de la mina no anticipaba: un sufijo entre
    paréntesis con el nombre de la función, "en <sha>" detrás del número, o
    la línea citada en prosa ("líneas ~766-805") en vez de pegada a la ruta.
    Regla conservadora, en este orden (incidencia #523, G3):

    1. Si tras una ruta reconocible hay ``:NNN`` (con o sin ``-MMM`` y con o
       sin texto detrás), la línea es ``NNN``.
    2. Si no, si en el resto del texto aparece ``línea(s) ~?NNN``, la línea
       es ``NNN``.
    3. Si no hay número reconocible, la línea es ``None`` -el nivel mecánico
       de §3.1 no es aplicable sin una línea concreta, así que el llamador
       decide qué hacer con esa ausencia- y la ruta es la ruta reconocible
       si la hay, o el texto completo si no la hay.

    Esta función no valida la ruta contra el disco: el ``fetch`` inyectado ya
    resuelve a ``SIN_INFORMACION`` si la ruta no existe en la comparación.
    """
    texto = str(archivo or "").strip()
    if not texto:
        return "", None

    ruta_reconocible: str | None = None
    resto = texto
    prefijo = _RUTA_PREFIX_RE.match(texto)
    if prefijo and ("/" in prefijo.group(0) or "." in prefijo.group(0)):
        ruta_reconocible = prefijo.group(0)
        resto = texto[len(ruta_reconocible) :]

    if ruta_reconocible is not None:
        sufijo = _LOCATION_SUFFIX_RE.match(resto)
        if sufijo:
            return ruta_reconocible, int(sufijo.group(1))

    prosa = _LOCATION_PROSE_RE.search(resto if ruta_reconocible is not None else texto)
    ruta = ruta_reconocible if ruta_reconocible is not None else texto
    if prosa:
        return ruta, int(prosa.group(1))
    return ruta, None


_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _line_kind_in_patch(patch: str, line: int) -> str:
    """``"added"``, ``"context"`` o ``"outside"`` para ``line`` (numeración del lado nuevo).

    Recorre el ``patch`` unificado que devuelve la API de comparación de
    GitHub para un fichero. Las líneas eliminadas (``-``) no consumen
    numeración del lado nuevo; las de contexto (``" "``) y las añadidas
    (``+``) sí. Una línea con guion final (``\\ No newline at end of file``)
    no es una línea de diff y no consume numeración.
    """
    numero_nuevo: int | None = None
    for cruda in patch.splitlines():
        cabecera = _HUNK_HEADER_RE.match(cruda)
        if cabecera:
            numero_nuevo = int(cabecera.group(1))
            continue
        if numero_nuevo is None:
            continue
        if cruda.startswith("\\"):
            continue
        marca = cruda[0] if cruda else " "
        if marca == "-":
            continue
        if numero_nuevo == line:
            return "added" if marca == "+" else "context"
        numero_nuevo += 1
    return "outside"


def evaluate_finding(
    *,
    round_number: int,
    round_records: Sequence[Mapping[str, Any]],
    current_head: str,
    repo: str,
    archivo: object,
    fetch: CompareFetcher,
) -> DripVerdict:
    """Evalúa un único hallazgo de la ronda ``round_number`` contra la ronda 1.

    ``round_records`` es la salida de
    :func:`sirius_engine.round_history.parse_round_records` sobre el
    historial YA LEÍDO de la incidencia -este módulo no llama a `gh` para
    leer comentarios, solo para comparar diffs (regla (b) de la incidencia
    #496: reutiliza ese analizador, no lo repite).

    La ronda 1 nunca se marca: no hay ronda anterior con la que comparar
    (regla (e) de la incidencia #496).
    """
    if round_number <= 1:
        return DripVerdict.SIN_MARCA

    ruta, linea = parse_archivo_location(archivo)
    if not ruta or linea is None:
        # Sin línea concreta, el nivel mecánico de §3.1 no es aplicable: el
        # informe de la mina lo reclasifica al nivel manual, fuera del
        # alcance de este guardián. Callarse es la respuesta correcta, no una
        # ausencia de respuesta.
        return DripVerdict.SIN_MARCA

    round_uno = next((r for r in round_records if int(r.get("round", 0)) == 1), None)
    if round_uno is None:
        # Historial sin ronda 1 registrada: no se puede afirmar nada sobre
        # ella, así que el guardián se calla en vez de arriesgar una marca.
        return DripVerdict.SIN_INFORMACION
    round1_head = str(round_uno.get("head") or "")
    if not round1_head:
        return DripVerdict.SIN_INFORMACION

    resultado = fetch(repo, round1_head, current_head, ruta)
    if resultado is None:
        return DripVerdict.SIN_INFORMACION
    if not resultado.changed:
        return DripVerdict.POSIBLE_GOTEO
    if not resultado.patch:
        # Cambió (p. ej. renombrado o binario) pero sin patch textual que
        # examinar a nivel de línea: no hay evidencia suficiente para marcar.
        return DripVerdict.SIN_MARCA

    kind = _line_kind_in_patch(resultado.patch, linea)
    if kind == "added":
        return DripVerdict.SIN_MARCA
    # "context" (línea sin tocar dentro de un hunk modificado) y "outside"
    # (fuera de todo hunk) se tratan igual, siguiendo la regla mecánica pura
    # de §3.1 del informe de la mina -con la limitación conocida y declarada
    # en el docstring del módulo sobre líneas de contexto con una hermana
    # modificada en el mismo hunk (`§459` rondas 3 y 4)-.
    return DripVerdict.POSIBLE_GOTEO


def annotate_observations(
    observations: Sequence[Mapping[str, Any]],
    *,
    round_number: int,
    round_records: Sequence[Mapping[str, Any]],
    current_head: str,
    repo: str,
    fetch: CompareFetcher,
    time_budget_seconds: float = DEFAULT_TIME_BUDGET_SECONDS,
) -> list[dict[str, Any]]:
    """Copia ``observations`` añadiendo ``posible_goteo`` donde corresponda.

    No muta la entrada. Cada observación que evalúa a
    :data:`DripVerdict.POSIBLE_GOTEO` recibe el campo nuevo
    ``posible_goteo`` con :data:`MENSAJE_POSIBLE_GOTEO`; las demás se
    devuelven sin ese campo, sin ningún otro cambio. Si la observación de
    entrada ya traía una clave ``posible_goteo`` propia -en modo solo-Claude,
    directamente del veredicto del revisor, no de este guardián-, se
    descarta: esa clave está reservada a este módulo y un valor ajeno
    conservado por copia se publicaría como si el guardián la hubiera
    marcado.
    """
    anotadas, _ = _annotate_with_verdicts(
        observations,
        round_number=round_number,
        round_records=round_records,
        current_head=current_head,
        repo=repo,
        fetch=fetch,
        time_budget_seconds=time_budget_seconds,
    )
    return anotadas


def annotate_observations_with_verdicts(
    observations: Sequence[Mapping[str, Any]],
    *,
    round_number: int,
    round_records: Sequence[Mapping[str, Any]],
    current_head: str,
    repo: str,
    fetch: CompareFetcher,
    time_budget_seconds: float = DEFAULT_TIME_BUDGET_SECONDS,
) -> tuple[list[dict[str, Any]], list[DripVerdict]]:
    """Igual que :func:`annotate_observations`, y además devuelve el
    :class:`DripVerdict` de cada observación, en el mismo orden.

    Existe para que un llamador (el CLI) pueda distinguir cuántas
    observaciones quedaron en :data:`DripVerdict.SIN_INFORMACION` -lectura de
    `gh api compare` caída, historial sin ronda 1- de cuántas se evaluaron de
    verdad, sin invocar ``fetch`` una segunda vez y sin que esa distinción
    toque el JSON anotado (``anotadas``) ni la transición del ciclo (regla
    (a) de la incidencia #496): los veredictos se devuelven aparte, nunca
    como un campo adicional de la observación.
    """
    return _annotate_with_verdicts(
        observations,
        round_number=round_number,
        round_records=round_records,
        current_head=current_head,
        repo=repo,
        fetch=fetch,
        time_budget_seconds=time_budget_seconds,
    )


def _memoize_fetch_with_budget(
    fetch: CompareFetcher, *, time_budget_seconds: float
) -> CompareFetcher:
    """Envuelve ``fetch`` con caché por fichero y un presupuesto de tiempo global.

    Dos observaciones de la misma ronda que citan el mismo fichero (mismo
    ``repo``/``head1``/``head2``/``ruta``) reutilizan una única llamada real
    (incidencia #501, CLAUDE-REVISOR-001): sin esto, cada observación
    disparaba su propia llamada secuencial a ``gh api compare``, aunque
    varias citaran el mismo fichero.

    El presupuesto es un reloj de pared compartido por TODAS las llamadas que
    pasen por este envoltorio: en cuanto se agota, ninguna llamada real nueva
    se intenta -se resuelve como lectura fallida (``None``), nunca como "no
    cambió" (regla (c) de la incidencia #496)-, así que un endpoint lento o
    bloqueado no puede agotar por sí solo el timeout del paso que llama a
    este guardián.
    """
    cache: dict[tuple[str, str, str, str], FileCompareResult | None] = {}
    deadline = time.monotonic() + time_budget_seconds

    def _fetch_memoizado(repo: str, head1: str, head2: str, ruta: str) -> FileCompareResult | None:
        clave = (repo, head1, head2, ruta)
        if clave in cache:
            return cache[clave]
        resultado = None if time.monotonic() >= deadline else fetch(repo, head1, head2, ruta)
        cache[clave] = resultado
        return resultado

    return _fetch_memoizado


def _annotate_with_verdicts(
    observations: Sequence[Mapping[str, Any]],
    *,
    round_number: int,
    round_records: Sequence[Mapping[str, Any]],
    current_head: str,
    repo: str,
    fetch: CompareFetcher,
    time_budget_seconds: float = DEFAULT_TIME_BUDGET_SECONDS,
) -> tuple[list[dict[str, Any]], list[DripVerdict]]:
    fetch_acotado = _memoize_fetch_with_budget(fetch, time_budget_seconds=time_budget_seconds)
    anotadas: list[dict[str, Any]] = []
    veredictos: list[DripVerdict] = []
    for observation in observations:
        copia = dict(observation)
        copia.pop("posible_goteo", None)
        veredicto = evaluate_finding(
            round_number=round_number,
            round_records=round_records,
            current_head=current_head,
            repo=repo,
            archivo=observation.get("archivo"),
            fetch=fetch_acotado,
        )
        if veredicto is DripVerdict.POSIBLE_GOTEO:
            copia["posible_goteo"] = MENSAJE_POSIBLE_GOTEO
        anotadas.append(copia)
        veredictos.append(veredicto)
    return anotadas, veredictos


#: Límite documentado de ficheros que devuelve la API de comparación de
#: GitHub (`gh api repos/.../compare/...`) en la clave ``files`` de una sola
#: respuesta. Por encima de este número la lista viene truncada sin que la
#: respuesta lo señale con un campo propio (incidencia #501,
#: CLAUDE-REVISOR-002): la única señal observable es que ``files`` alcanza
#: exactamente este tamaño.
_MAX_COMPARE_FILES = 300


def gh_compare_file(
    repo: str, head1: str, head2: str, file_path: str, *, timeout: float = 30.0
) -> FileCompareResult | None:
    """Implementación real de :data:`CompareFetcher`, vía ``gh api compare``.

    Traduce CUALQUIER fallo -proceso, tiempo de espera, JSON ilegible,
    forma inesperada de la respuesta- a ``None``. Es la única función impura
    del módulo; el resto del código nunca llama a `gh` directamente.
    """
    try:
        proceso = subprocess.run(
            ["gh", "api", f"repos/{repo}/compare/{head1}...{head2}"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    # Dos cláusulas y no `except (A, B):` a propósito: `ruff format` con
    # `target-version = "py314"` quita los paréntesis y deja sintaxis de PEP 758,
    # que el `python3` del runner (3.12) no entiende -exactamente como ya
    # ocurrió en `sirius_convergence.py`, ver `sirius_check_docs.py`-. Este
    # módulo lo carga `sirius_drip_guard_cli.py` con el `python3` del sistema.
    except OSError:
        return None
    except subprocess.TimeoutExpired:
        return None
    if proceso.returncode != 0:
        return None
    try:
        datos = json.loads(proceso.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(datos, dict):
        return None
    ficheros = datos.get("files")
    if not isinstance(ficheros, list):
        return None
    for entrada in ficheros:
        if not isinstance(entrada, dict):
            continue
        if entrada.get("filename") != file_path:
            continue
        patch = entrada.get("patch")
        return FileCompareResult(changed=True, patch=patch if isinstance(patch, str) else None)
    if len(ficheros) >= _MAX_COMPARE_FILES:
        # La lista alcanzó el límite documentado de la API: puede estar
        # truncada, así que la ausencia de `file_path` en ella no es
        # evidencia de que no cambiara -sería asumir "no cambió" sobre una
        # lectura potencialmente incompleta (regla (c) de la incidencia
        # #496). Se declara lectura fallida, nunca "sin cambios".
        return None
    return FileCompareResult(changed=False, patch=None)
