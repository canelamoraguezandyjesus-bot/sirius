#!/usr/bin/env python3
"""Sirius — disparador y recolector de la revisión nativa de Codex en GitHub.

Segundo revisor del flujo de revisión dual (contrato operativo §4.1). Este
componente NO usa la API de OpenAI: se apoya exclusivamente en la integración
nativa de Codex con GitHub (ChatGPT Business), que se activa publicando un
comentario ``@codex review`` en la PR. Codex actúa aquí como revisor de solo
lectura; este script jamás modifica código ni responde a los comentarios.

Dos subórdenes:

``trigger``
    Publica (o reutiliza de forma idempotente) el comentario disparador de una
    ronda concreta. El comentario lleva un marcador oculto estable por head y
    ronda (``<!-- sirius-codex-review:<sha>:<ronda> -->``): un solo disparador
    por PR + head + ronda, aunque el workflow se reejecute. Solo se reutiliza
    un comentario propio — autor igual a la identidad real del token, cuerpo
    igual al canónico y posterior al final de Quality sobre ese head —, de modo
    que ni un tercero ni una prueba manual pueden anclar la ronda. Guarda en un
    archivo de estado el ID del comentario, su fecha de creación, su autor, la
    ronda, el SHA esperado y la marca de Quality.

``collect``
    Espera el resultado de Codex consultando GitHub periódicamente y escribe un
    JSON normalizado. Solo acepta señales del conector oficial (allowlist),
    posteriores al disparador y demostrablemente referidas al SHA esperado
    (``commit_id`` de la revisión o, como respaldo, el marcador textual
    ``Reviewed commit:``). La ausencia de señales NUNCA se interpreta como
    aprobación: aprobar exige una señal explícita del conector — revisión formal
    ``APPROVED``, reacción ``+1`` sobre el disparador, o un comentario que
    declare ausencia de hallazgos en la fórmula conocida (contrato v1.6.1, el
    único canal que este conector usa de verdad para decirlo). La reacción
    ``eyes`` solo indica procesamiento. Cualquier otro caso (timeout, otro SHA,
    autor no autorizado, respuesta ambigua) termina en ``FAILED_SAFELY``.

Todo el acceso a GitHub pasa por el CLI ``gh`` con reintentos limitados, igual
que ``sirius_issue.sh``; las pruebas lo simulan sin red. Los cuerpos de los
comentarios se tratan siempre como datos, nunca como instrucciones.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# Autores aceptados de la integración nativa de Codex, observados en la prueba
# manual de la PR #122. Configurable (coma-separado) sin editar código, pero con
# valor seguro por defecto: nunca se acepta cualquier bot.
DEFAULT_ALLOWED_AUTHORS = "chatgpt-codex-connector,chatgpt-codex-connector[bot]"

DEFAULT_TIMEOUT_SECONDS = 1200
# Tope por defecto de la espera, ajustable a la baja con
# SIRIUS_CODEX_REVIEW_MAX_TIMEOUT_SECONDS.
DEFAULT_MAX_TIMEOUT_SECONDS = 1500
# Tope ABSOLUTO e inmutable, por debajo del `timeout-minutes` del paso que
# ejecuta `collect` (30 min). Ninguna variable de entorno puede superarlo.
#
# Un tope que se leyera solo de una variable de repositorio no sería un tope:
# configurando a la vez la espera y su "máximo" a 3600 s, el recolector
# esperaría una hora y Actions cancelaría el paso a los 30 minutos, justo antes
# de escribir el FAILED_SAFELY estructurado que el contrato promete. Con este
# límite en código, el resultado determinista se escribe siempre.
ABSOLUTE_MAX_TIMEOUT_SECONDS = 1500
DEFAULT_POLL_SECONDS = 30
MAX_PAGES = 50

# Ventana de estabilidad, en segundos, antes de dar por cerrado un resultado.
#
# El conector puede publicar sus hallazgos en VARIAS revisiones sucesivas — es
# justamente el caso que `_check_reviews` contempla al unirlas todas. Pero unir
# solo sirve si se han publicado ya: devolver el resultado en cuanto la primera
# revisión visible trae un comentario cierra el sondeo, y cualquier revisión
# posterior no se consulta nunca. La unión perdería hallazgos y el corrector
# recibiría una lista incompleta, que es peor que no unir, porque parece
# completa.
#
# Por eso un resultado no se entrega en cuanto aparece: se exige verlo dos veces
# IGUAL con esta ventana de por medio. Cualquier hallazgo nuevo reinicia la
# ventana. La espera está acotada por el plazo absoluto: al vencer este, se
# entrega lo que haya —nunca un timeout falso teniendo hallazgos a la vista—.
DEFAULT_SETTLE_SECONDS = 60

# El marcador identifica la ronda, no solo el head: `<head>:<ronda>`. La ronda
# es estable ante reejecuciones del MISMO run de Actions (GITHUB_RUN_ID no
# cambia al reintentar), así que la idempotencia se conserva; pero una ronda
# nueva sobre el mismo head (por ejemplo, tras una parada segura y una nueva
# aplicación de la etiqueta) obtiene su propio disparador y NUNCA puede quedar
# satisfecha por una revisión pedida en la ronda anterior.
#: Prefijos con los que el conector declara que ha fallado ÉL, no que haya
#: revisado. Enumerados recorriendo las 21 PR en las que ha comentado; ver
#: `_declara_fallo_del_conector` para el detalle y las latencias observadas.
#: Se anclan al inicio del cuerpo y se mantienen estrechos: reconocer de más
#: aquí no aprueba nada, pero pararía una ronda sana antes de tiempo.
_FALLOS_DECLARADOS_DEL_CONECTOR: tuple[str, ...] = (
    "Codex Review: Something went wrong.",
    "You have reached your Codex usage",
    "To use Codex here,",
    "Codex couldn't complete this request.",
)

TRIGGER_MARKER_TEMPLATE = "<!-- sirius-codex-review:{head}:{round_id} -->"

# Solicitud de revisión: únicamente orientación de revisión, jamás instrucciones
# de corrección (el conector también entiende órdenes que modifican la PR y
# están prohibidas en este flujo).
TRIGGER_BODY_TEMPLATE = """{marker}

@codex review

Revisa únicamente el commit `{head}`, head actual de esta PR. No modifiques
código ni la PR. Reporta solo defectos concretos y accionables. Para cada
hallazgo incluye severidad, archivo y línea, problema observado, comportamiento
esperado, evidencia o prueba que lo demuestra y límites de la corrección.
"""

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REVIEWED_COMMIT_RE = re.compile(r"Reviewed commit[^0-9a-fA-F]{0,20}([0-9a-fA-F]{7,40})")
SEVERITY_BADGE_RE = re.compile(r"!\[(P[0-9])[^\]]*Badge[^\]]*\]")

# Fórmula con la que el conector declara que no encontró nada, observada en las
# incidencias #148 y #177: «Codex Review: Didn't find any major issues».
#
# Se aceptan solo variantes de ESA afirmación (apóstrofo recto o tipográfico,
# forma contraída o no, con «major» o sin él). No se exige el prefijo «Codex
# Review:» —la procedencia ya la garantiza la allowlist de autores—, pero
# tampoco se admite ninguna otra redacción: lo que no encaja no aprueba, se
# detiene. Ver `_declares_no_findings` para por qué la estrechez es el punto.
# La comilla tipográfica se escribe escapada en el patrón, no literal: el
# carácter crudo es indistinguible del apóstrofo recto a simple vista, y en algo
# que decide una aprobación no puede quedar duda de qué se está aceptando.
NO_FINDINGS_RE = re.compile(
    "(?:did\\s?n['\u2019]t|did\\s+not)\\s+find\\s+any\\s+(?:major\\s+)?issues",
    re.IGNORECASE,
)


class GhError(RuntimeError):
    """Fallo persistente de una llamada a ``gh`` tras agotar los reintentos."""


def _env_number(name: str, default: float) -> float:
    """Valor numérico de una variable de entorno, saneado.

    El valor por defecto cubre la variable ausente, presente pero vacía (p. ej.
    una variable de repositorio sin definir interpolada por Actions) o no
    numérica. Se rechazan además los valores no finitos (``inf``, ``nan``) y los
    negativos: `float()` los aceptaría, y un ``inf`` convertiría cualquier tope
    en ausencia de tope.
    """
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        print(
            f"sirius_codex_review: valor no numérico en {name}={raw!r}; se usa {default}.",
            file=sys.stderr,
        )
        return default
    if not math.isfinite(value) or value < 0:
        print(
            f"sirius_codex_review: valor no utilizable en {name}={raw!r} "
            f"(debe ser finito y no negativo); se usa {default}.",
            file=sys.stderr,
        )
        return default
    return value


def _retry_settings() -> tuple[int, float]:
    attempts = int(_env_number("SIRIUS_RETRY_ATTEMPTS", 4))
    base_delay = _env_number("SIRIUS_RETRY_BASE_DELAY", 2)
    return max(attempts, 1), max(base_delay, 0.0)


def _gh_api(
    path: str,
    *,
    method: str | None = None,
    input_file: str | None = None,
    attempts_override: int | None = None,
) -> Any:
    """Llama ``gh api`` con reintentos limitados y espera creciente.

    Devuelve el JSON decodificado. Lanza ``GhError`` si todas las tentativas
    fallan (el llamador decide si eso es fatal o solo el fin de una pasada de
    sondeo). ``attempts_override`` permite desactivar los reintentos en
    operaciones NO idempotentes (el POST del disparador: reintentar a ciegas
    podría publicar el comentario dos veces si la primera respuesta se perdió
    después de haberse aplicado en el servidor).
    """
    attempts, delay = _retry_settings()
    if attempts_override is not None:
        attempts = attempts_override
    cmd = ["gh", "api", path]
    if method:
        cmd += ["-X", method]
    if input_file:
        cmd += ["--input", input_file]
    last_error = ""
    for attempt in range(1, attempts + 1):
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout or "null")
            except json.JSONDecodeError as exc:
                last_error = f"respuesta no JSON: {exc}"
        else:
            last_error = proc.stderr.strip() or f"gh api salió con {proc.returncode}"
        if attempt < attempts:
            print(
                f"sirius_codex_review: intento {attempt}/{attempts} falló"
                f" ({path}): {last_error}; reintento en {delay}s",
                file=sys.stderr,
            )
            time.sleep(delay)
            delay = delay * 2 if delay else 0
    raise GhError(f"gh api {path}: {last_error}")


def _gh_paginated(path_template: str) -> list[dict[str, Any]]:
    """Recorre una colección REST página a página (determinista y simulable)."""
    items: list[dict[str, Any]] = []
    separator = "&" if "?" in path_template else "?"
    for page in range(1, MAX_PAGES + 1):
        chunk = _gh_api(f"{path_template}{separator}per_page=100&page={page}")
        if not isinstance(chunk, list):
            raise GhError(f"respuesta inesperada (no lista) en {path_template}")
        items.extend(item for item in chunk if isinstance(item, dict))
        if len(chunk) < 100:
            break
    return items


def _allowed_authors() -> set[str]:
    raw = os.environ.get("SIRIUS_CODEX_ALLOWED_AUTHORS", DEFAULT_ALLOWED_AUTHORS)
    return {item.strip().casefold() for item in raw.split(",") if item.strip()}


def _author_login(item: dict[str, Any]) -> str:
    user = item.get("user")
    if isinstance(user, dict) and isinstance(user.get("login"), str):
        return str(user["login"])
    return ""


def _is_allowed_author(item: dict[str, Any]) -> bool:
    return _author_login(item).casefold() in _allowed_authors()


def _utcnow() -> datetime:
    """Instante actual con zona horaria explícita (UTC).

    Las marcas de GitHub llegan con zona (``...Z``); comparar contra un
    ``datetime`` ingenuo lanzaría ``TypeError``, así que aquí nunca se produce
    uno sin zona.
    """
    return datetime.now(UTC)


def _parse_timestamp(value: object) -> datetime | None:
    """Marca temporal de GitHub como ``datetime`` con zona horaria.

    Se asume UTC cuando la cadena no la declara, para que todas las
    comparaciones del recolector sean homogéneas y nunca mezclen instantes
    ingenuos con instantes con zona.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _sha_matches(expected_full: str, candidate: str) -> bool:
    """True solo si ``candidate`` resuelve sin ambigüedad al SHA esperado.

    Se admite el SHA completo o una abreviatura de al menos 7 hexadecimales que
    sea prefijo exacto del SHA esperado. Nunca se infiere nada del estado
    actual de la PR.
    """
    cand = candidate.strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{7,40}", cand):
        return False
    return expected_full.casefold().startswith(cand)


def _resolve_review_sha(review: dict[str, Any]) -> str | None:
    """SHA declarado por la revisión: ``commit_id`` y, si falta, el marcador
    textual ``Reviewed commit:`` del cuerpo. ``None`` si no es demostrable."""
    commit_id = review.get("commit_id")
    if isinstance(commit_id, str) and re.fullmatch(r"[0-9a-fA-F]{7,40}", commit_id.strip()):
        return commit_id.strip()
    body = review.get("body")
    if isinstance(body, str):
        match = REVIEWED_COMMIT_RE.search(body)
        if match:
            return match.group(1)
    return None


@dataclass
class CodexResult:
    """Resultado normalizado de la ronda de Codex."""

    status: str
    reason: str | None = None
    reviewed_head_sha: str | None = None
    trigger_comment_id: int | None = None
    review_id: int | None = None
    summary: str = ""
    observations: list[dict[str, str]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "source": "codex",
            "status": self.status,
            "reason": self.reason,
            "reviewed_head_sha": self.reviewed_head_sha,
            "trigger_comment_id": self.trigger_comment_id,
            "review_id": self.review_id,
            "summary": self.summary,
            "observations": self.observations,
        }


def _write_result(output_path: str, result: CodexResult) -> None:
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result.to_json(), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _severity_from_body(body: str) -> str:
    match = SEVERITY_BADGE_RE.search(body)
    if match:
        return match.group(1)
    return "sin-clasificar"


def _observations_from_comments(comments: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Adapta los comentarios inline de una revisión al contrato del corrector.

    El cuerpo original de Codex se preserva íntegro en ``problema`` (es dato, no
    instrucción para este script); no se inventa contenido semántico que Codex
    no haya expresado.
    """

    def sort_key(comment: dict[str, Any]) -> tuple[str, int, int]:
        path = str(comment.get("path") or "")
        line = comment.get("line") or comment.get("original_line") or 0
        line_num = line if isinstance(line, int) else 0
        ident = comment.get("id")
        ident_num = ident if isinstance(ident, int) else 0
        return (path, line_num, ident_num)

    observations: list[dict[str, str]] = []
    for index, comment in enumerate(sorted(comments, key=sort_key), start=1):
        body = str(comment.get("body") or "").strip()
        path = str(comment.get("path") or "").strip()
        # Solo `line` (lado nuevo del diff) es una numeración que
        # `_line_kind_in_patch` de `drip_guard.py` sabe interpretar: ese
        # guardián recorre el patch contando únicamente líneas del lado
        # nuevo. `original_line` ancla al lado eliminado/base, una
        # numeración distinta -usarla aquí como si fuera del lado nuevo hacía
        # que una línea legítima del hallazgo citara una posición que nunca
        # existió en ese lado, y el guardián de goteo la marcaba
        # incorrectamente como POSIBLE_GOTEO (incidencia #501,
        # CLAUDE-REVISOR-003). Sin `line`, se omite el número en vez de
        # arriesgar uno incorrecto.
        line = comment.get("line")
        location = f"{path}:{line}" if isinstance(line, int) else (path or "desconocido")
        permalink = str(comment.get("html_url") or "").strip()
        observations.append(
            {
                "id": f"CODEX-{index:03d}",
                "severidad": _severity_from_body(body),
                "archivo": location,
                "problema": body or "(comentario de Codex sin cuerpo)",
                "criterio_esperado": (
                    "Resolver el defecto exactamente como lo describe el hallazgo de Codex "
                    "citado en 'problema' y demostrar la corrección con una prueba."
                ),
                "prueba": permalink or f"Comentario inline de Codex sobre {location}.",
                "limites_correccion": (
                    "Corregir únicamente el componente señalado, sin ampliar el alcance "
                    "aprobado de la incidencia."
                ),
            }
        )
    return observations


# --------------------------------------------------------------------------- #
# trigger
# --------------------------------------------------------------------------- #


def _automation_identity() -> str:
    """Login real del token con el que se publica el disparador.

    Necesario para no reutilizar como disparador un comentario ajeno: el
    marcador es predecible (deriva del head), así que cualquiera con acceso a
    comentar podría sembrarlo. Si además la revisión automática del panel de
    Codex estuviera encendida, una revisión NO solicitada por el workflow
    quedaría "posterior" a ese comentario y satisfaría la ronda sin que la
    automatización hubiera pedido nada después de Quality.
    """
    identity = _gh_api("user")
    login = identity.get("login") if isinstance(identity, dict) else None
    if not isinstance(login, str) or not login.strip():
        raise GhError("no se pudo determinar la identidad del token que publica el disparador")
    return login.strip()


def _normalized_body(text: str) -> str:
    """Cuerpo comparable: finales de línea unificados y espacio exterior fuera.

    La comparación NO es byte a byte a propósito. El cuerpo lo genera esta
    misma automatización, así que el objetivo del cotejo es distinguir un
    disparador propio de cualquier otro comentario con el mismo marcador, no
    detectar diferencias de espaciado. Una comparación byte a byte fallaría
    contra nuestro propio comentario si GitHub o un cliente intermedio
    normalizasen los finales de línea (CRLF) o recortasen el salto final, y esa
    falsa diferencia publicaría un SEGUNDO `@codex review` para el mismo head
    en cada reejecución — justo el consumo duplicado que el contrato prohíbe
    (§6). El contenido interno sí debe coincidir exactamente.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _find_trigger_comments(
    repo: str,
    pr: int,
    marker: str,
    *,
    author: str,
    expected_body: str,
    not_before: datetime,
) -> list[dict[str, Any]]:
    """Comentarios disparadores propios: marcador presente, autor igual a la
    identidad de la automatización y cuerpo igual al generado por la plantilla
    determinista (ver ``_normalized_body`` para el criterio exacto). Un
    comentario ajeno (o del mismo autor pero con otro texto) NO se reutiliza:
    en su lugar se publica el propio.

    ``not_before`` es el instante en que Quality terminó sobre este head: un
    comentario anterior a esa marca no pertenece a la ronda posterior a Quality
    y se descarta aunque cumpla todo lo demás. Sin esa condición, un comentario
    sembrado antes de que CI terminara podría anclar la ronda a una revisión de
    Codex previa a la validación.
    """
    comments = _gh_paginated(f"repos/{repo}/issues/{pr}/comments")
    wanted_author = author.casefold()
    wanted_body = _normalized_body(expected_body)
    matching = []
    for comment in comments:
        if marker not in str(comment.get("body") or ""):
            continue
        if _author_login(comment).casefold() != wanted_author:
            continue
        if _normalized_body(str(comment.get("body") or "")) != wanted_body:
            continue
        created_at = _parse_timestamp(comment.get("created_at"))
        if created_at is None or created_at < not_before:
            print(
                f"sirius_codex_review: se descarta el comentario {comment.get('id')}: "
                "no es posterior al final de Quality sobre este head.",
                file=sys.stderr,
            )
            continue
        matching.append(comment)
    matching.sort(key=lambda c: (str(c.get("created_at") or ""), int(c.get("id") or 0)))
    return matching


def cmd_trigger(args: argparse.Namespace) -> int:
    marker = TRIGGER_MARKER_TEMPLATE.format(head=args.head, round_id=args.round_id)
    body = TRIGGER_BODY_TEMPLATE.format(marker=marker, head=args.head)
    quality_at = _parse_timestamp(args.quality_completed_at)
    if quality_at is None:
        print(
            "sirius_codex_review: no se pudo interpretar el instante en que Quality "
            f"terminó ({args.quality_completed_at!r}); sin esa marca no puedo demostrar "
            "que el disparador pertenece a la ronda posterior a Quality. Parada segura.",
            file=sys.stderr,
        )
        return 1
    try:
        author = _automation_identity()
        existing = _find_trigger_comments(
            args.repo,
            args.pr,
            marker,
            author=author,
            expected_body=body,
            not_before=quality_at,
        )
        if existing:
            chosen = existing[0]
            print(
                f"sirius_codex_review: disparador propio ya existente para {args.head}; "
                f"se reutiliza el comentario {chosen.get('id')} de {author}.",
                file=sys.stderr,
            )
        else:
            payload_path = f"{args.state_file}.payload"
            with open(payload_path, "w", encoding="utf-8") as handle:
                json.dump({"body": body}, handle, ensure_ascii=False)
            # El POST NO se reintenta a ciegas: si la respuesta se pierde
            # después de que el servidor aplicara el comentario, un reintento
            # publicaría un segundo @codex review para el mismo head. Ante un
            # fallo se relee la PR: si el marcador ya está, se reutiliza.
            posted: Any = None
            post_error: GhError | None = None
            try:
                posted = _gh_api(
                    f"repos/{args.repo}/issues/{args.pr}/comments",
                    method="POST",
                    input_file=payload_path,
                    attempts_override=1,
                )
            except GhError as exc:
                post_error = exc
            os.unlink(payload_path)
            # Relectura defensiva: converge en el comentario propio más antiguo
            # tanto tras una carrera improbable como tras un POST de resultado
            # ambiguo (aplicado en el servidor pero con la respuesta perdida).
            refreshed = _find_trigger_comments(
                args.repo,
                args.pr,
                marker,
                author=author,
                expected_body=body,
                not_before=quality_at,
            )
            chosen = refreshed[0] if refreshed else posted
            if not isinstance(chosen, dict):
                if post_error is not None:
                    raise post_error
                raise GhError("el comentario disparador publicado no es legible")
    except GhError as exc:
        print(f"sirius_codex_review: no se pudo asegurar el disparador: {exc}", file=sys.stderr)
        return 1

    state = {
        "repo": args.repo,
        "pr": args.pr,
        "head_sha": args.head,
        "round_id": args.round_id,
        "marker": marker,
        "trigger_comment_id": chosen.get("id"),
        "trigger_created_at": chosen.get("created_at"),
        "trigger_author": _author_login(chosen) or author,
        "quality_completed_at": args.quality_completed_at,
    }
    with open(args.state_file, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        f"sirius_codex_review: disparador registrado (comentario "
        f"{state['trigger_comment_id']}, head {args.head}).",
        file=sys.stderr,
    )
    return 0


# --------------------------------------------------------------------------- #
# collect
# --------------------------------------------------------------------------- #


def _load_state(args: argparse.Namespace) -> tuple[dict[str, Any] | None, CodexResult | None]:
    try:
        with open(args.state_file, encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return None, CodexResult(
            status="FAILED_SAFELY",
            reason="sin-disparador",
            summary=(
                "No existe un estado de disparador de Codex legible para esta ronda "
                f"({exc}); no se puede identificar con seguridad ningún resultado."
            ),
        )
    if not isinstance(state, dict) or state.get("head_sha") != args.head:
        return None, CodexResult(
            status="FAILED_SAFELY",
            reason="disparador-de-otro-head",
            summary=(
                "El disparador registrado no corresponde al head esperado "
                f"({args.head}); no se reutilizan resultados de otro head."
            ),
        )
    if str(state.get("round_id") or "") != str(args.round_id):
        # La ronda es parte de la identidad del disparador: un estado de otra
        # ronda podría anclar la espera a una revisión ya consumida.
        return None, CodexResult(
            status="FAILED_SAFELY",
            reason="disparador-de-otra-ronda",
            summary=(
                "El disparador registrado pertenece a otra ronda de revisión "
                f"({state.get('round_id')!r} en vez de {args.round_id!r}); no se "
                "reutilizan resultados de una ronda anterior."
            ),
        )
    trigger_id = state.get("trigger_comment_id")
    trigger_at = _parse_timestamp(state.get("trigger_created_at"))
    if not isinstance(trigger_id, int) or trigger_at is None:
        return None, CodexResult(
            status="FAILED_SAFELY",
            reason="disparador-invalido",
            summary="El estado del disparador de Codex es incompleto; parada segura.",
        )
    quality_at = _parse_timestamp(state.get("quality_completed_at"))
    if quality_at is None or trigger_at < quality_at:
        return None, CodexResult(
            status="FAILED_SAFELY",
            reason="disparador-anterior-a-quality",
            trigger_comment_id=trigger_id,
            summary=(
                "No puedo demostrar que el disparador sea posterior al final de "
                "Quality sobre este head; la ronda no es identificable con "
                "seguridad. Parada segura."
            ),
        )
    return state, None


def _check_reviews(
    repo: str, pr: int, head: str, trigger_at: datetime, trigger_id: int
) -> tuple[CodexResult | None, bool]:
    """Una pasada sobre las revisiones de la PR.

    Devuelve ``(resultado, hay_revisiones)``. ``resultado`` es ``None`` si hay
    que seguir esperando; ``hay_revisiones`` indica si el conector ya publicó
    alguna revisión formal posterior al disparador, aunque todavía no sea
    interpretable — el llamador lo necesita para NO caer al camino de la
    reacción 👍 cuando existe una revisión formal en curso.

    Se consideran TODAS las revisiones posteriores al disparador, no solo la
    última. Codex puede publicar más de una (por ejemplo, una tanda de
    comentarios y después un resumen), y quedarse con la última descartaría en
    silencio los hallazgos de las anteriores; en el peor caso, una revisión
    aprobatoria posterior enterraría los cambios pedidos por la primera y la
    ronda aprobaría un head con defectos ya reportados. Los hallazgos se unen y
    cualquier ambigüedad de SHA en cualquiera de ellas detiene la ronda.
    """
    reviews = _gh_paginated(f"repos/{repo}/pulls/{pr}/reviews")
    candidates = []
    for review in reviews:
        if not _is_allowed_author(review):
            continue
        submitted_at = _parse_timestamp(review.get("submitted_at"))
        if submitted_at is None or submitted_at <= trigger_at:
            # Revisiones históricas: no cuentan. La comparación es ESTRICTA a
            # propósito. `submitted_at` tiene resolución de segundo, así que una
            # revisión enviada en el mismo segundo que el disparador no puede
            # demostrarse posterior a él; aceptarla dejaría que una revisión
            # automática del panel, o una manual previa, satisficiera la ronda
            # sin que Codex haya respondido al comentario posterior a Quality.
            # Descartar un empate solo cuesta esperar a la revisión real —Codex
            # tarda minutos, no milisegundos—; aceptarlo cuesta la garantía.
            continue
        candidates.append((submitted_at, review))
    if not candidates:
        return None, False
    candidates.sort(key=lambda pair: (pair[0], int(pair[1].get("id") or 0)))

    # Toda revisión candidata debe demostrar que auditó el head esperado. Basta
    # una que no lo demuestre para detener la ronda: no se puede saber si sus
    # hallazgos (o su ausencia) se refieren a esta versión.
    for _, review in candidates:
        review_id = int(review.get("id") or 0)
        declared_sha = _resolve_review_sha(review)
        if declared_sha is None:
            return (
                CodexResult(
                    status="FAILED_SAFELY",
                    reason="sha-no-demostrable",
                    trigger_comment_id=trigger_id,
                    review_id=review_id,
                    summary=(
                        "Codex respondió después del disparador, pero su revisión no declara "
                        "de forma demostrable qué commit revisó; parada segura."
                    ),
                ),
                True,
            )
        if not _sha_matches(head, declared_sha):
            return (
                CodexResult(
                    status="FAILED_SAFELY",
                    reason="sha-distinto",
                    trigger_comment_id=trigger_id,
                    review_id=review_id,
                    summary=(
                        f"Codex revisó el commit `{declared_sha}`, que no es el head esperado "
                        f"`{head}`; parada segura sin aprobar ni pedir cambios."
                    ),
                ),
                True,
            )

    # Hallazgos de TODAS las revisiones con comentarios, numerados de forma
    # global y determinista (el orden lo fija `_observations_from_comments`).
    inline_comments: list[dict[str, Any]] = []
    unclear_review_id = 0
    approved_review_id = 0
    for _, review in candidates:
        review_id = int(review.get("id") or 0)
        state = str(review.get("state") or "").upper()
        if state == "APPROVED":
            approved_review_id = approved_review_id or review_id
            continue
        if state in {"COMMENTED", "CHANGES_REQUESTED"}:
            comments = _gh_paginated(f"repos/{repo}/pulls/{pr}/reviews/{review_id}/comments")
            # "Sin comentarios inline" NO significa "todavía no materializada".
            # El conector publica también revisiones cuyo contenido vive
            # entero en el `body` — el resumen «Codex Review» —, y esas están
            # completas: su endpoint de comentarios está vacío para siempre.
            # Tratarlas como ambiguas convertiría CADA ronda legítima con
            # resumen en un timeout, que es peor que el defecto que esta
            # comprobación vino a corregir: rompería el camino normal en vez de
            # un caso límite.
            #
            # El discriminante es tener algo que leer: una revisión sin cuerpo
            # Y sin comentarios no ha entregado nada todavía. Si una revisión
            # con cuerpo publica sus comentarios más tarde, de eso se encarga la
            # ventana de estabilidad — el resultado cambia y la espera se
            # reinicia —, que es exactamente para lo que existe.
            if not comments and not str(review.get("body") or "").strip():
                unclear_review_id = unclear_review_id or review_id
            inline_comments.extend(comments)

    if unclear_review_id:
        # CADA revisión formal no aprobatoria debe haber entregado algo antes de
        # aceptar la unión, no solo el conjunto. Basta una que no haya entregado
        # nada para que la ronda entera siga sin interpretar: si se devolvieran
        # los hallazgos de las demás, la ventana de estabilidad cerraría sobre
        # una lista incompleta —el resultado se repite igual pasada tras pasada—
        # y los hallazgos de esa revisión no llegarían nunca al corrector. Peor
        # aún, la lista llegaría con apariencia de completa.
        #
        # Comprobarlo por conjunto (¿hay ALGUNA observación?) no basta:
        # enmascara justamente el caso en que una revisión trae hallazgos y otra
        # todavía no se puede leer.
        print(
            f"sirius_codex_review: la revisión {unclear_review_id} no ha entregado todavía "
            "ni cuerpo ni comentarios inline; la ronda sigue sin interpretar aunque otras "
            "revisiones ya hayan aportado hallazgos.",
            file=sys.stderr,
        )
        return None, True

    observations = _observations_from_comments(inline_comments)
    reported_review_id = int(candidates[-1][1].get("id") or 0)

    if observations:
        return (
            CodexResult(
                status="CHANGES_REQUESTED",
                reviewed_head_sha=head,
                trigger_comment_id=trigger_id,
                review_id=reported_review_id,
                summary=(
                    f"Codex revisó el commit `{head}` y reportó "
                    f"{len(observations)} hallazgo(s) concreto(s)."
                ),
                observations=observations,
            ),
            True,
        )
    if approved_review_id:
        return (
            CodexResult(
                status="APPROVED",
                reviewed_head_sha=head,
                trigger_comment_id=trigger_id,
                review_id=approved_review_id,
                summary=f"Codex aprobó formalmente la revisión del commit `{head}` sin hallazgos.",
            ),
            True,
        )
    return None, True


def _declara_fallo_del_conector(body: str) -> str | None:
    """¿El conector está diciendo que ÉL ha fallado, en vez de revisar?

    Devuelve la primera línea del mensaje si lo es, o ``None``.

    Por qué existe. El 21-08-2026, en la PR #233, Codex contestó a los **4
    minutos** con «Codex Review: Something went wrong. Try again later by
    commenting "@codex review".» El recolector no lo vio, esperó los 1200 s
    completos y después afirmó que Codex «no entregó un resultado
    identificable». Contestó: contestó un fallo. Se perdieron 16 minutos y una
    ronda, y el mensaje decía exactamente qué había que hacer.

    La causa mecánica: estos cuerpos no traen ``Reviewed commit:``, así que
    ``_resolve_review_sha`` devuelve ``None`` y el filtro de SHA los descartaba
    **antes** de mirarles el texto. No eran ambiguos: eran invisibles.

    Reconocimiento por prefijo anclado al inicio, y estrecho a propósito, igual
    que :func:`_declares_no_findings`. Las cuatro formas salen de recorrer las
    **21 PR** en las que este conector ha comentado, no de suponerlas:

    ==========================================  ====  =================
    Prefijo                                     Casos Latencia observada
    ==========================================  ====  =================
    ``Codex Review: Something went wrong.``     2     4 m 08 s / 5 m 44 s
    ``You have reached your Codex usage``       1     7 s
    ``To use Codex here,``                      1     12 s
    ``Codex couldn't complete this request.``   2     canal de tarea
    ==========================================  ====  =================

    Los dos cuerpos de la primera son **idénticos byte a byte** (578 caracteres).
    Con n=2 no está probado que el bloque de error interior sea siempre «Unknown
    error», así que lo que se reconoce es el prefijo, que sí es estable.

    **Esto nunca aprueba nada.** Solo convierte una espera de 20 minutos en una
    parada inmediata y diagnosticable. La asimetría es la de
    ``_declares_no_findings`` pero al revés y más benigna: si el conector cambia
    su texto de error, volvemos al comportamiento de hoy —esperar el plazo—, que
    es exactamente lo que ya hacíamos.
    """
    texto = body.strip()
    for prefijo in _FALLOS_DECLARADOS_DEL_CONECTOR:
        if texto.startswith(prefijo):
            return texto.splitlines()[0].strip()
    return None


def _declares_no_findings(body: str) -> bool:
    """¿El comentario dice, en la fórmula conocida del conector, que no halló nada?

    Reconocimiento DELIBERADAMENTE ESTRECHO. Es lo único que separa una
    aprobación de una parada segura, así que el criterio es «esta frase concreta,
    observada», no «suena a que aprueba». Una redacción distinta —o una que
    además traiga hallazgos— no aprueba: cae en la parada segura de siempre.

    La asimetría manda: si el conector cambia su texto, el coste es una ronda
    bloqueada que mira una persona. Si el patrón fuera ancho, el coste sería
    aprobar una PR con defectos reportados. Solo uno de esos dos errores es
    recuperable.
    """
    if SEVERITY_BADGE_RE.search(body):
        # Trae insignias de severidad: hay hallazgos, diga lo que diga el
        # encabezado. No es una aprobación.
        return False
    return NO_FINDINGS_RE.search(body) is not None


def _check_conversation_comments(
    repo: str, pr: int, head: str, trigger_at: datetime, trigger_id: int
) -> CodexResult | None:
    """Respuesta del conector publicada como comentario de la conversación.

    El conector no siempre contesta con una revisión formal. La incidencia #148
    lo vio por primera vez: respondió «Codex Review: Didn't find any major
    issues» en un comentario ordinario, 101 s después del disparador y con su
    marcador ``Reviewed commit:``. El recolector no miraba ese canal, gastó los
    1200 s completos y después afirmó que Codex no había entregado un resultado
    identificable. Se añadió entonces esta comprobación, pero devolviendo
    siempre ``FAILED_SAFELY`` porque §4.1 solo admitía aprobar con revisión
    formal ``APPROVED`` o reacción ``+1``.

    La incidencia #177 demostró que ese canal no es un caso límite: es el ÚNICO
    por el que este conector dice «no encontré nada». En las 7 rondas de la PR
    #178 emitió seis revisiones formales —todas ``COMMENTED``, ninguna
    ``APPROVED``— cuando tenía hallazgos, y un comentario de conversación cuando
    no los tenía, sin marcar 👍 el disparador pese a prometerlo en su propio
    texto. Con la regla anterior, los dos canales de aprobación del contrato no
    ocurrían nunca: ninguna PR limpia podía alcanzar ``ready-for-merge``.

    Por eso el contrato v1.6.1 admite un tercer canal, con las mismas
    comprobaciones de siempre (autor permitido, estrictamente posterior al
    disparador, SHA demostrable e igual al esperado) más una condición nueva: el
    cuerpo debe declarar ausencia de hallazgos en la fórmula conocida
    (``_declares_no_findings``). Cualquier otro comentario del conector sigue
    siendo la parada segura ``respuesta-por-comentario``.

    La precedencia NO cambia: el llamador solo consulta este canal cuando no hay
    ninguna revisión formal posterior al disparador ni reacción. Una señal débil
    no resuelve una ambigüedad.
    """
    comments = _gh_paginated(f"repos/{repo}/issues/{pr}/comments")
    candidates: list[dict[str, Any]] = []
    for comment in comments:
        if int(comment.get("id") or 0) == trigger_id:
            continue  # el propio disparador
        if not _is_allowed_author(comment):
            continue
        created_at = _parse_timestamp(comment.get("created_at"))
        # Estrictamente posterior, igual que las revisiones: un empate de
        # segundos no demuestra el orden causal.
        if created_at is None or created_at <= trigger_at:
            continue
        # ANTES del filtro de SHA, y no después, porque estos mensajes no
        # traen `Reviewed commit:` y morían justo en esa línea sin que nadie
        # les leyera el texto (PR #233, 21-08-2026: 16 minutos esperando a
        # quien ya había contestado).
        fallo = _declara_fallo_del_conector(str(comment.get("body") or ""))
        if fallo is not None:
            return CodexResult(
                status="FAILED_SAFELY",
                reason="codex-fallo-declarado",
                reviewed_head_sha=head,
                trigger_comment_id=trigger_id,
                summary=(
                    f"Codex no revisó `{head}`: declaró un fallo suyo "
                    f"({comment.get('html_url') or comment.get('id')}) — «{fallo}». "
                    "La ronda termina en fallo seguro sin agotar el plazo, porque "
                    "esperar más no lo va a cambiar: el conector ya contestó. "
                    "Volver a aplicar la etiqueta de revisión abre una ronda nueva "
                    "con su propio disparador, que es lo que este mensaje pide."
                ),
            )
        declared_sha = _resolve_review_sha(comment)
        if declared_sha is None or not _sha_matches(head, declared_sha):
            continue
        candidates.append(comment)

    if not candidates:
        return None

    # Se miran TODOS los comentarios de la ronda, no solo el primero, y basta uno
    # que no declare ausencia de hallazgos para detenerla — el mismo principio
    # que `_check_reviews` aplica a las revisiones.
    #
    # Quedarse con el primero haría depender el desenlace del orden de llegada:
    # un comentario intermedio del conector precedería a la declaración de «no
    # encontré nada» y bloquearía una ronda limpia; y al revés, si el que
    # decidiera fuera el último, una declaración posterior enterraría un
    # comentario anterior con hallazgos y aprobaría un head con defectos ya
    # reportados. Exigirlo de todos elimina la dependencia del orden por los dos
    # lados a la vez.
    unclear = next(
        (c for c in candidates if not _declares_no_findings(str(c.get("body") or ""))),
        None,
    )
    if unclear is not None:
        return CodexResult(
            status="FAILED_SAFELY",
            reason="respuesta-por-comentario",
            reviewed_head_sha=head,
            trigger_comment_id=trigger_id,
            summary=(
                f"Codex respondió sobre `{head}` en un comentario de la conversación "
                f"({unclear.get('html_url') or unclear.get('id')}) que no es una revisión "
                "formal ni declara ausencia de hallazgos en la fórmula reconocida. No "
                "puedo interpretarlo como aprobación ni como lista de cambios; la ronda "
                "se detiene con el motivo real, no con un timeout."
            ),
        )
    return CodexResult(
        status="APPROVED",
        reviewed_head_sha=head,
        trigger_comment_id=trigger_id,
        summary=(
            f"Codex declaró no haber encontrado hallazgos en el commit `{head}`, en un "
            f"comentario de la conversación "
            f"({candidates[-1].get('html_url') or candidates[-1].get('id')}). Es el canal "
            "por el que este conector comunica la ausencia de hallazgos: no publica una "
            "revisión formal cuando no tiene nada que reportar."
        ),
    )


def _check_reactions(repo: str, pr: int, head: str, trigger_id: int) -> CodexResult | None:
    """Aprobación explícita sin hallazgos: reacción ``+1`` del conector sobre el
    disparador. La reacción ``eyes`` solo indica procesamiento y se ignora.

    Solo se consulta cuando NO existe ninguna revisión formal posterior al
    disparador. Una reacción es una señal mucho más débil que una revisión: si
    Codex ya publicó una revisión que todavía no es interpretable, dejar que el
    👍 decidiera convertiría esa ambigüedad en una aprobación, que es
    exactamente lo que la ronda no debe hacer nunca.

    A diferencia de una revisión formal, la reacción no lleva ``commit_id``:
    para no fabricar un ``reviewed_head_sha`` indemostrable, la aprobación solo
    se acepta si el head actual de la PR sigue siendo exactamente el esperado
    (Codex revisa el head vigente al recibir el disparador). Si el head cambió
    durante la ronda, el resultado es un fallo seguro, nunca una aprobación.
    """
    reactions = _gh_paginated(f"repos/{repo}/issues/comments/{trigger_id}/reactions")
    for reaction in reactions:
        if reaction.get("content") == "+1" and _is_allowed_author(reaction):
            pr_data = _gh_api(f"repos/{repo}/pulls/{pr}")
            current_head = ""
            if isinstance(pr_data, dict) and isinstance(pr_data.get("head"), dict):
                current_head = str(pr_data["head"].get("sha") or "")
            if current_head.casefold() != head.casefold():
                return CodexResult(
                    status="FAILED_SAFELY",
                    reason="head-cambiado",
                    trigger_comment_id=trigger_id,
                    summary=(
                        "El conector de Codex marcó 👍 el disparador, pero el head actual "
                        f"de la PR (`{current_head or 'ilegible'}`) ya no es el esperado "
                        f"(`{head}`); no puedo demostrar qué versión aprobó. Parada segura."
                    ),
                )
            return CodexResult(
                status="APPROVED",
                reviewed_head_sha=head,
                trigger_comment_id=trigger_id,
                summary=(
                    "El conector de Codex marcó 👍 el comentario disparador: aprobación "
                    f"explícita sin hallazgos para el head `{head}` (verificado que sigue "
                    "siendo el head actual de la PR)."
                ),
            )
    return None


def _result_signature(result: CodexResult) -> tuple[Any, ...]:
    """Huella de lo observado en una pasada, para detectar que ya no cambia.

    Depende del contenido sustantivo de los hallazgos —no de identificadores
    correlativos ni de qué revisión los trajo—, para que dos pasadas que ven
    exactamente lo mismo produzcan la misma huella y una pasada que ve un
    hallazgo nuevo produzca otra.
    """
    return (
        result.status,
        result.reviewed_head_sha,
        tuple(
            sorted(
                (
                    str(observation.get("archivo") or ""),
                    str(observation.get("severidad") or ""),
                    str(observation.get("problema") or ""),
                )
                for observation in result.observations
            )
        ),
    )


def cmd_collect(args: argparse.Namespace) -> int:
    state, failure = _load_state(args)
    if failure is not None or state is None:
        _write_result(
            args.output,
            failure
            or CodexResult(status="FAILED_SAFELY", reason="sin-disparador", summary="Sin estado."),
        )
        return 0

    trigger_id = int(state["trigger_comment_id"])
    trigger_at = _parse_timestamp(state.get("trigger_created_at"))
    assert trigger_at is not None  # garantizado por _load_state
    poll_seconds = _env_number("SIRIUS_CODEX_POLL_SECONDS", DEFAULT_POLL_SECONDS)
    # El tope efectivo nunca puede superar el absoluto en código: una variable
    # de repositorio solo puede bajarlo, jamás subirlo.
    configured_max = _env_number(
        "SIRIUS_CODEX_REVIEW_MAX_TIMEOUT_SECONDS", DEFAULT_MAX_TIMEOUT_SECONDS
    )
    max_timeout = min(configured_max, ABSOLUTE_MAX_TIMEOUT_SECONDS)
    if configured_max > ABSOLUTE_MAX_TIMEOUT_SECONDS:
        print(
            f"sirius_codex_review: el tope configurado ({configured_max:.0f} s) supera el "
            f"absoluto en código ({ABSOLUTE_MAX_TIMEOUT_SECONDS:.0f} s), que garantiza escribir "
            "un resultado antes de que expire el paso; se aplica el absoluto.",
            file=sys.stderr,
        )
    timeout = max(args.timeout, 0.0)
    if timeout > max_timeout:
        print(
            f"sirius_codex_review: la espera configurada ({timeout:.0f} s) supera el tope "
            f"({max_timeout:.0f} s); se limita al tope.",
            file=sys.stderr,
        )
        timeout = max_timeout

    # El plazo de Codex es ABSOLUTO y empieza en el instante real del
    # disparador, no cuando arranca este paso. Codex trabaja en paralelo a
    # Claude desde que se publica la solicitud, así que el tiempo que tarde
    # Claude ya consume ese plazo: si el revisor Claude agotó la ventana, aquí
    # NO se concede un plazo nuevo completo. Lo que queda es la diferencia, y
    # nunca menos de cero.
    elapsed_since_trigger = (_utcnow() - trigger_at).total_seconds()
    remaining = timeout - elapsed_since_trigger
    if remaining < timeout:
        print(
            f"sirius_codex_review: han transcurrido {elapsed_since_trigger:.0f} s desde el "
            f"disparador; del plazo absoluto de {timeout:.0f} s quedan "
            f"{max(remaining, 0):.0f} s.",
            file=sys.stderr,
        )
    deadline = time.monotonic() + max(remaining, 0.0)

    settle_seconds = max(_env_number("SIRIUS_CODEX_SETTLE_SECONDS", DEFAULT_SETTLE_SECONDS), 0.0)

    result: CodexResult | None = None
    # Último resultado observado y su huella, a la espera de estabilizarse.
    settling: CodexResult | None = None
    settling_signature: tuple[Any, ...] | None = None
    settle_until = 0.0
    while True:
        # Siempre se hace al menos una pasada de sondeo, incluso con el plazo
        # absoluto ya agotado: si Codex respondió mientras Claude trabajaba, su
        # resultado debe recogerse en vez de declararse un timeout falso.
        observed: CodexResult | None = None
        poll_failed = False
        try:
            observed, has_reviews = _check_reviews(
                args.repo, args.pr, args.head, trigger_at, trigger_id
            )
            if observed is None and not has_reviews:
                observed = _check_reactions(args.repo, args.pr, args.head, trigger_id)
            if observed is None and not has_reviews:
                # Último canal, y el más débil: solo se mira cuando no hay
                # ninguna revisión formal en curso ni reacción. Mirarlo antes
                # debilitaría la precedencia que exige §4.1 —una revisión formal
                # manda sobre señales más flojas—.
                observed = _check_conversation_comments(
                    args.repo, args.pr, args.head, trigger_at, trigger_id
                )
        except GhError as exc:
            # Error transitorio ya reintentado: se sigue sondeando hasta el
            # timeout; nunca se degrada a aprobación ni se aborta sin resultado.
            print(f"sirius_codex_review: pasada de sondeo fallida: {exc}", file=sys.stderr)
            poll_failed = True

        if observed is not None:
            if observed.status == "FAILED_SAFELY":
                # Una parada segura no mejora esperando: el motivo (SHA
                # distinto o no demostrable) ya es definitivo para esta ronda.
                result = observed
                break
            signature = _result_signature(observed)
            now = time.monotonic()
            if signature != settling_signature:
                # Estado nuevo: Codex sigue publicando. Se reinicia la ventana.
                if settling_signature is not None:
                    print(
                        "sirius_codex_review: el resultado de Codex cambió durante la ventana "
                        "de estabilidad; se reinicia la espera para no perder hallazgos.",
                        file=sys.stderr,
                    )
                settling, settling_signature = observed, signature
                settle_until = now + settle_seconds
            elif now >= settle_until and settling is not None:
                # La ventana se cerró sin que nada cambiara: el resultado ya es
                # el definitivo de la ronda.
                result = settling
                break
        elif not poll_failed and settling is not None:
            # La pasada SÍ se completó y ya no hay nada interpretable. Eso NO es
            # "sigue valiendo lo anterior": significa que apareció una revisión
            # formal que todavía no se puede leer y que vuelve ambigua la ronda
            # entera. Conservar el resultado que se estaba estabilizando dejaría
            # que, al vencer el plazo, se entregara un valor obsoleto — y en el
            # peor caso se aprobara el head pese a una revisión pendiente que el
            # propio código declara ambigua. Se descarta: si la ambigüedad no se
            # aclara antes del plazo, la ronda termina en fallo seguro.
            #
            # Una pasada fallida por error de transporte (`poll_failed`) no
            # invalida nada: no es evidencia de ambigüedad, solo de que no se
            # pudo mirar.
            print(
                "sirius_codex_review: el resultado que se estaba estabilizando ha dejado de "
                "ser interpretable (probablemente una revisión formal sin comentarios "
                "visibles); se descarta y la ronda vuelve a esperar.",
                file=sys.stderr,
            )
            settling, settling_signature = None, None

        if time.monotonic() >= deadline:
            if settling is not None:
                # Hay un resultado a la vista pero la ventana no llegó a
                # cerrarse: se entrega lo observado. Perder hallazgos ya
                # recogidos por declarar un timeout sería estrictamente peor.
                print(
                    "sirius_codex_review: el plazo absoluto venció antes de cerrar la ventana "
                    "de estabilidad; se entrega el último resultado observado.",
                    file=sys.stderr,
                )
                result = settling
                break
            result = CodexResult(
                status="FAILED_SAFELY",
                reason="timeout",
                trigger_comment_id=trigger_id,
                summary=(
                    f"Codex no entregó un resultado identificable para `{args.head}` dentro "
                    f"del plazo absoluto de {timeout:.0f} segundos contados desde el "
                    "disparador; la ronda termina en fallo seguro. No se publica un segundo "
                    "disparador para el mismo head y ronda."
                ),
            )
            break

        # La pausa se acota al primer instante en que hay algo que decidir: el
        # plazo absoluto o, si hay un resultado estabilizándose, el cierre de su
        # ventana. Dormir el intervalo completo hacía que un remanente menor que
        # `SIRIUS_CODEX_POLL_SECONDS` (30 s por defecto) se pasara de largo: el
        # recolector terminaba hasta medio minuto después del plazo que promete,
        # y el resultado se entregaba más tarde de lo necesario al cerrarse la
        # ventana. El plazo absoluto deja de ser aproximado.
        now = time.monotonic()
        wake_at = deadline
        if settling is not None and settle_until < wake_at:
            wake_at = settle_until
        time.sleep(max(min(poll_seconds, wake_at - now), 0.0))

    _write_result(args.output, result)
    print(
        f"sirius_codex_review: resultado {result.status}"
        f"{f' ({result.reason})' if result.reason else ''} escrito en {args.output}.",
        file=sys.stderr,
    )
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _full_sha(value: str) -> str:
    if not SHA_RE.fullmatch(value.strip().casefold()):
        raise argparse.ArgumentTypeError(f"se esperaba un SHA completo de 40 hex: {value!r}")
    return value.strip().casefold()


def _round_id(value: str) -> str:
    """Identificador de ronda: no vacío y sin caracteres que rompan el marcador."""
    cleaned = value.strip()
    if not cleaned or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", cleaned):
        raise argparse.ArgumentTypeError(
            f"identificador de ronda inválido: {value!r} (se esperaba [A-Za-z0-9._-]{{1,64}})"
        )
    return cleaned


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", required=True, help="owner/repo")
    common.add_argument("--pr", required=True, type=int, help="número de la PR")
    common.add_argument("--head", required=True, type=_full_sha, help="SHA completo esperado")
    common.add_argument("--state-file", required=True, help="archivo de estado del disparador")
    common.add_argument(
        "--round-id",
        required=True,
        type=_round_id,
        help=(
            "identificador estable de la ronda de revisión (el run de Actions): "
            "igual en las reejecuciones del mismo run, distinto en una ronda nueva"
        ),
    )

    trigger = subparsers.add_parser(
        "trigger", parents=[common], help="publica o reutiliza el disparador de Codex"
    )
    trigger.add_argument(
        "--quality-completed-at",
        required=True,
        help="instante RFC3339 en que Quality terminó sobre este head",
    )
    trigger.set_defaults(func=cmd_trigger)

    collect = subparsers.add_parser(
        "collect", parents=[common], help="espera y normaliza el resultado de Codex"
    )
    collect.add_argument("--output", required=True, help="archivo JSON de salida")
    collect.add_argument(
        "--timeout",
        type=float,
        default=_env_number("SIRIUS_CODEX_REVIEW_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        help="segundos máximos de espera antes del fallo seguro",
    )
    collect.set_defaults(func=cmd_collect)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handler = args.func
    result = handler(args)
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
