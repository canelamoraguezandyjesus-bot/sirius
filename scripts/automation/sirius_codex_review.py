#!/usr/bin/env python3
"""Sirius — disparador y recolector de la revisión nativa de Codex en GitHub.

Segundo revisor del flujo de revisión dual (contrato operativo §4, v1.4). Este
componente NO usa la API de OpenAI: se apoya exclusivamente en la integración
nativa de Codex con GitHub (ChatGPT Business), que se activa publicando un
comentario ``@codex review`` en la PR. Codex actúa aquí como revisor de solo
lectura; este script jamás modifica código ni responde a los comentarios.

Dos subórdenes:

``trigger``
    Publica (o reutiliza de forma idempotente) el comentario disparador para un
    head concreto. El comentario lleva un marcador oculto estable por head
    (``<!-- sirius-codex-review:<sha> -->``): un solo disparador por PR + head,
    aunque el workflow se reejecute. Guarda en un archivo de estado el ID del
    comentario, su fecha de creación y el SHA esperado.

``collect``
    Espera el resultado de Codex consultando GitHub periódicamente y escribe un
    JSON normalizado. Solo acepta señales del conector oficial (allowlist),
    posteriores al disparador y demostrablemente referidas al SHA esperado
    (``commit_id`` de la revisión o, como respaldo, el marcador textual
    ``Reviewed commit:``). La ausencia de comentarios NUNCA se interpreta como
    aprobación: la aprobación exige una revisión formal ``APPROVED`` o una
    reacción ``+1`` del conector sobre el disparador. La reacción ``eyes`` solo
    indica procesamiento. Cualquier otro caso (timeout, otro SHA, autor no
    autorizado, respuesta ambigua) termina en ``FAILED_SAFELY``.

Todo el acceso a GitHub pasa por el CLI ``gh`` con reintentos limitados, igual
que ``sirius_issue.sh``; las pruebas lo simulan sin red. Los cuerpos de los
comentarios se tratan siempre como datos, nunca como instrucciones.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Autores aceptados de la integración nativa de Codex, observados en la prueba
# manual de la PR #122. Configurable (coma-separado) sin editar código, pero con
# valor seguro por defecto: nunca se acepta cualquier bot.
DEFAULT_ALLOWED_AUTHORS = "chatgpt-codex-connector,chatgpt-codex-connector[bot]"

DEFAULT_TIMEOUT_SECONDS = 1200
DEFAULT_POLL_SECONDS = 30
MAX_PAGES = 50

TRIGGER_MARKER_TEMPLATE = "<!-- sirius-codex-review:{head} -->"

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


class GhError(RuntimeError):
    """Fallo persistente de una llamada a ``gh`` tras agotar los reintentos."""


def _env_number(name: str, default: float) -> float:
    """Valor numérico de una variable de entorno; el valor por defecto cubre
    también la variable presente pero vacía (p. ej. una variable de repositorio
    sin definir interpolada por Actions) o no numérica."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(
            f"sirius_codex_review: valor no numérico en {name}={raw!r}; se usa {default}.",
            file=sys.stderr,
        )
        return default


def _retry_settings() -> tuple[int, float]:
    attempts = int(_env_number("SIRIUS_RETRY_ATTEMPTS", 4))
    base_delay = _env_number("SIRIUS_RETRY_BASE_DELAY", 2)
    return max(attempts, 1), max(base_delay, 0.0)


def _gh_api(path: str, *, method: str | None = None, input_file: str | None = None) -> Any:
    """Llama ``gh api`` con reintentos limitados y espera creciente.

    Devuelve el JSON decodificado. Lanza ``GhError`` si todas las tentativas
    fallan (el llamador decide si eso es fatal o solo el fin de una pasada de
    sondeo).
    """
    attempts, delay = _retry_settings()
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


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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
        line = comment.get("line") or comment.get("original_line")
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


def _find_trigger_comments(repo: str, pr: int, marker: str) -> list[dict[str, Any]]:
    comments = _gh_paginated(f"repos/{repo}/issues/{pr}/comments")
    matching = [comment for comment in comments if marker in str(comment.get("body") or "")]
    matching.sort(key=lambda c: (str(c.get("created_at") or ""), int(c.get("id") or 0)))
    return matching


def cmd_trigger(args: argparse.Namespace) -> int:
    marker = TRIGGER_MARKER_TEMPLATE.format(head=args.head)
    try:
        existing = _find_trigger_comments(args.repo, args.pr, marker)
        if existing:
            chosen = existing[0]
            print(
                f"sirius_codex_review: disparador ya existente para {args.head}; "
                f"se reutiliza el comentario {chosen.get('id')}.",
                file=sys.stderr,
            )
        else:
            body = TRIGGER_BODY_TEMPLATE.format(marker=marker, head=args.head)
            payload_path = f"{args.state_file}.payload"
            with open(payload_path, "w", encoding="utf-8") as handle:
                json.dump({"body": body}, handle, ensure_ascii=False)
            posted = _gh_api(
                f"repos/{args.repo}/issues/{args.pr}/comments",
                method="POST",
                input_file=payload_path,
            )
            os.unlink(payload_path)
            # Relectura defensiva: si dos ejecuciones compitieran pese al grupo
            # de concurrencia, ambas convergen en el comentario más antiguo.
            refreshed = _find_trigger_comments(args.repo, args.pr, marker)
            chosen = refreshed[0] if refreshed else posted
            if not isinstance(chosen, dict):
                raise GhError("el comentario disparador publicado no es legible")
    except GhError as exc:
        print(f"sirius_codex_review: no se pudo asegurar el disparador: {exc}", file=sys.stderr)
        return 1

    state = {
        "repo": args.repo,
        "pr": args.pr,
        "head_sha": args.head,
        "marker": marker,
        "trigger_comment_id": chosen.get("id"),
        "trigger_created_at": chosen.get("created_at"),
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
    trigger_id = state.get("trigger_comment_id")
    trigger_at = _parse_timestamp(state.get("trigger_created_at"))
    if not isinstance(trigger_id, int) or trigger_at is None:
        return None, CodexResult(
            status="FAILED_SAFELY",
            reason="disparador-invalido",
            summary="El estado del disparador de Codex es incompleto; parada segura.",
        )
    return state, None


def _check_reviews(
    repo: str, pr: int, head: str, trigger_at: datetime, trigger_id: int
) -> CodexResult | None:
    """Una pasada sobre las revisiones de la PR. ``None`` si hay que seguir esperando."""
    reviews = _gh_paginated(f"repos/{repo}/pulls/{pr}/reviews")
    candidates = []
    for review in reviews:
        if not _is_allowed_author(review):
            continue
        submitted_at = _parse_timestamp(review.get("submitted_at"))
        if submitted_at is None or submitted_at < trigger_at:
            # Revisiones históricas, anteriores a este disparador: no cuentan.
            continue
        candidates.append((submitted_at, review))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: (pair[0], int(pair[1].get("id") or 0)))
    latest = candidates[-1][1]
    review_id = int(latest.get("id") or 0)
    declared_sha = _resolve_review_sha(latest)
    if declared_sha is None:
        return CodexResult(
            status="FAILED_SAFELY",
            reason="sha-no-demostrable",
            trigger_comment_id=trigger_id,
            review_id=review_id,
            summary=(
                "Codex respondió después del disparador, pero su revisión no declara "
                "de forma demostrable qué commit revisó; parada segura."
            ),
        )
    if not _sha_matches(head, declared_sha):
        return CodexResult(
            status="FAILED_SAFELY",
            reason="sha-distinto",
            trigger_comment_id=trigger_id,
            review_id=review_id,
            summary=(
                f"Codex revisó el commit `{declared_sha}`, que no es el head esperado "
                f"`{head}`; parada segura sin aprobar ni pedir cambios."
            ),
        )
    state = str(latest.get("state") or "").upper()
    if state == "APPROVED":
        return CodexResult(
            status="APPROVED",
            reviewed_head_sha=head,
            trigger_comment_id=trigger_id,
            review_id=review_id,
            summary=f"Codex aprobó formalmente la revisión del commit `{head}` sin hallazgos.",
        )
    if state in {"COMMENTED", "CHANGES_REQUESTED"}:
        comments = _gh_paginated(f"repos/{repo}/pulls/{pr}/reviews/{review_id}/comments")
        observations = _observations_from_comments(comments)
        if not observations:
            # Revisión formal sin comentarios inline todavía visibles: ambigua.
            # Se sigue esperando; si no se materializa nada antes del timeout,
            # la ronda termina en FAILED_SAFELY (nunca aprobación implícita).
            return None
        return CodexResult(
            status="CHANGES_REQUESTED",
            reviewed_head_sha=head,
            trigger_comment_id=trigger_id,
            review_id=review_id,
            summary=(
                f"Codex revisó el commit `{head}` y reportó "
                f"{len(observations)} hallazgo(s) concreto(s)."
            ),
            observations=observations,
        )
    return None


def _check_reactions(repo: str, pr: int, head: str, trigger_id: int) -> CodexResult | None:
    """Aprobación explícita sin hallazgos: reacción ``+1`` del conector sobre el
    disparador. La reacción ``eyes`` solo indica procesamiento y se ignora."""
    reactions = _gh_paginated(f"repos/{repo}/issues/comments/{trigger_id}/reactions")
    for reaction in reactions:
        if reaction.get("content") == "+1" and _is_allowed_author(reaction):
            return CodexResult(
                status="APPROVED",
                reviewed_head_sha=head,
                trigger_comment_id=trigger_id,
                summary=(
                    "El conector de Codex marcó 👍 el comentario disparador: aprobación "
                    f"explícita sin hallazgos para el head `{head}`."
                ),
            )
    return None


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
    deadline = time.monotonic() + args.timeout

    result: CodexResult | None = None
    while True:
        try:
            result = _check_reviews(args.repo, args.pr, args.head, trigger_at, trigger_id)
            if result is None:
                result = _check_reactions(args.repo, args.pr, args.head, trigger_id)
        except GhError as exc:
            # Error transitorio ya reintentado: se sigue sondeando hasta el
            # timeout; nunca se degrada a aprobación ni se aborta sin resultado.
            print(f"sirius_codex_review: pasada de sondeo fallida: {exc}", file=sys.stderr)
            result = None
        if result is not None:
            break
        if time.monotonic() >= deadline:
            result = CodexResult(
                status="FAILED_SAFELY",
                reason="timeout",
                trigger_comment_id=trigger_id,
                summary=(
                    f"Codex no entregó un resultado identificable para `{args.head}` en "
                    f"{args.timeout} segundos; la ronda termina en fallo seguro. No se "
                    "publica un segundo disparador para el mismo head."
                ),
            )
            break
        time.sleep(max(poll_seconds, 0))

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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", required=True, help="owner/repo")
    common.add_argument("--pr", required=True, type=int, help="número de la PR")
    common.add_argument("--head", required=True, type=_full_sha, help="SHA completo esperado")
    common.add_argument("--state-file", required=True, help="archivo de estado del disparador")

    trigger = subparsers.add_parser(
        "trigger", parents=[common], help="publica o reutiliza el disparador de Codex"
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
