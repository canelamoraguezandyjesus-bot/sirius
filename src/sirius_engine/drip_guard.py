"""Guardián de goteo en vivo (incidencia #496, ADR-121).

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

**Limitación conocida, declarada en vez de implementada** (ver ADR-121): la
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

import functools
import json
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

#: Mensaje exacto que pide el objetivo de la incidencia #496.
MENSAJE_POSIBLE_GOTEO = (
    "posible goteo: este contenido ya estaba idéntico en la ronda 1, ¿por qué no se vio entonces?"
)

# Sufijo de línea (o rango) que el recolector añade al `archivo` de un
# hallazgo: `scripts/x.py:120`, `scripts/x.py:120-134`. Solo se usa el
# primer número: es el que ancla la comparación mecánica de §3.1 del informe
# de la mina (el rango, cuando aparece, describe un tramo citado a mano, no
# un hunk).
_LOCATION_LINE_RE = re.compile(r"^(.*?):(\d+)(?:-\d+)?$")


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

    Sin sufijo de línea reconocible, la línea es ``None`` y la ruta es el
    texto completo tal cual -el nivel mecánico de §3.1 del informe de la mina
    no es aplicable sin una línea concreta, así que el llamador decide qué
    hacer con esa ausencia.
    """
    texto = str(archivo or "").strip()
    match = _LOCATION_LINE_RE.match(texto)
    if not match:
        return texto, None
    return match.group(1), int(match.group(2))


_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _line_kind_in_patch(patch: str, line: int) -> str:
    """``"added"``, ``"context"``, ``"removed"`` u ``"outside"`` para ``line``.

    Recorre el ``patch`` unificado que devuelve la API de comparación de
    GitHub para un fichero, siguiendo DOS numeraciones en paralelo: la del
    lado viejo (para detectar ``"removed"``) y la del lado nuevo (para
    ``"added"``/``"context"``, numeración con la que ``line`` se interpreta
    por defecto). Un comentario inline de Codex puede citar, en cambio, la
    numeración del lado viejo (`original_line`) cuando apunta a contenido
    eliminado (`sirius_codex_review.py`); como el ``archivo:línea`` de un
    hallazgo no conserva de qué lado vino el número, una línea que coincide
    con la posición vieja de un ``-`` se declara ``"removed"`` -contenido que
    SÍ cambió entre la ronda 1 y ahora, así que nunca es goteo, sea cual sea
    el lado que el número realmente representaba-. Una línea con guion final
    (``\\ No newline at end of file``) no es una línea de diff y no consume
    numeración.
    """
    numero_viejo: int | None = None
    numero_nuevo: int | None = None
    for cruda in patch.splitlines():
        cabecera = _HUNK_HEADER_RE.match(cruda)
        if cabecera:
            numero_viejo = int(cabecera.group(1))
            numero_nuevo = int(cabecera.group(2))
            continue
        if numero_nuevo is None or numero_viejo is None:
            continue
        if cruda.startswith("\\"):
            continue
        marca = cruda[0] if cruda else " "
        if marca == "-":
            if numero_viejo == line:
                return "removed"
            numero_viejo += 1
            continue
        if numero_nuevo == line:
            return "added" if marca == "+" else "context"
        numero_nuevo += 1
        numero_viejo += 1
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
    if kind in ("added", "removed"):
        # "added": la línea es contenido nuevo, no puede ser goteo. "removed":
        # la línea citada coincide con la posición vieja de contenido
        # eliminado entre la ronda 1 y ahora -cambió, así que declararla
        # goteo sería justo el error que corrige CODEX-003-.
        return DripVerdict.SIN_MARCA
    # "context" (línea sin tocar dentro de un hunk modificado) y "outside"
    # (fuera de todo hunk) se tratan igual, siguiendo la regla mecánica pura
    # de §3.1 del informe de la mina -con la limitación conocida y declarada
    # en el docstring del módulo sobre líneas de contexto con una hermana
    # modificada en el mismo hunk (`§459` rondas 3 y 4)-.
    return DripVerdict.POSIBLE_GOTEO


@dataclass(frozen=True, slots=True)
class AnnotationSummary:
    """Resultado de :func:`annotate_observations`: las observaciones y su diagnóstico.

    ``sin_informacion`` cuenta cuántas observaciones evaluaron a
    :data:`DripVerdict.SIN_INFORMACION` -típicamente porque
    :data:`CompareFetcher` falló al leer la comparación-, para que el CLI
    pueda declarar ese fallo por stderr de forma distinguible de "0 marcadas
    porque no hubo goteo" (regla (c) de la incidencia #496, hallazgo
    CLAUDE-REVIEW-499-001/CODEX-004 de la revisión de la PR #499). No añade
    marcas, no bloquea la ronda ni modifica las observaciones estructuradas:
    solo hace observable un dato que antes se descartaba en silencio.
    """

    observations: list[dict[str, Any]]
    sin_informacion: int


def annotate_observations(
    observations: Sequence[Mapping[str, Any]],
    *,
    round_number: int,
    round_records: Sequence[Mapping[str, Any]],
    current_head: str,
    repo: str,
    fetch: CompareFetcher,
) -> AnnotationSummary:
    """Copia ``observations`` añadiendo ``posible_goteo`` donde corresponda.

    No muta la entrada. Cada observación que evalúa a
    :data:`DripVerdict.POSIBLE_GOTEO` recibe el campo nuevo
    ``posible_goteo`` con :data:`MENSAJE_POSIBLE_GOTEO`; las demás se
    devuelven sin ese campo, sin ningún otro cambio.
    """
    anotadas: list[dict[str, Any]] = []
    sin_informacion = 0
    for observation in observations:
        copia = dict(observation)
        veredicto = evaluate_finding(
            round_number=round_number,
            round_records=round_records,
            current_head=current_head,
            repo=repo,
            archivo=observation.get("archivo"),
            fetch=fetch,
        )
        if veredicto is DripVerdict.POSIBLE_GOTEO:
            copia["posible_goteo"] = MENSAJE_POSIBLE_GOTEO
        elif veredicto is DripVerdict.SIN_INFORMACION:
            sin_informacion += 1
        anotadas.append(copia)
    return AnnotationSummary(observations=anotadas, sin_informacion=sin_informacion)


#: Tope documentado de la API de comparación de GitHub: la lista ``files``
#: solo cubre la primera página e incluye como máximo 300 entradas para toda
#: la comparación (https://docs.github.com/en/rest/commits/commits#compare-two-commits).
#: Si el fichero buscado no aparece y la lista llega a este tope, su ausencia
#: no demuestra que no cambió -pudo quedar fuera por el límite- (CODEX-002).
_MAX_FILES_PER_PAGE = 300


@functools.lru_cache(maxsize=32)
def _gh_compare_raw(repo: str, head1: str, head2: str, timeout: float) -> dict[str, Any] | None:
    """Ejecuta ``gh api compare`` UNA vez por ``(repo, head1, head2, timeout)``.

    Memoizado a propósito (CODEX-001): dentro de una misma ejecución del CLI,
    todas las observaciones de la ronda comparan el mismo par de heads -solo
    cambia el fichero, que se filtra en memoria a partir de esta respuesta,
    no en la URL-, así que repetir la llamada por cada observación multiplica
    el coste (hasta el timeout de 30s) sin motivo: con el endpoint bloqueado
    y 20 observaciones se agotarían los 10 minutos del paso "Aplicar el
    veredicto" (`review-sirius-work.yml`) antes de poder aplicar el
    fallback. Memoizar aquí, y no imponer un presupuesto global, evita ese
    consumo sin tocar el timeout del workflow.

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
    return datos


def gh_compare_file(
    repo: str, head1: str, head2: str, file_path: str, *, timeout: float = 30.0
) -> FileCompareResult | None:
    """Implementación real de :data:`CompareFetcher`, vía ``gh api compare``.

    La llamada a `gh` en sí la hace :func:`_gh_compare_raw`, memoizada por
    ``(repo, head1, head2, timeout)``; esta función solo filtra la respuesta
    ya obtenida para ``file_path``.
    """
    datos = _gh_compare_raw(repo, head1, head2, timeout)
    if datos is None:
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
    if len(ficheros) >= _MAX_FILES_PER_PAGE:
        return None
    return FileCompareResult(changed=False, patch=None)
