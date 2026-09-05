#!/usr/bin/env python3
"""Sirius — agregación determinista de la revisión dual (Claude + Codex).

Combina el veredicto del revisor Claude y el resultado normalizado de Codex en
un único JSON compatible con ``sirius_apply_verdict.sh`` (rol ``reviewer``).
No hay votos, promedios ni arbitraje por otro modelo: solo reglas fijas, en
este orden de precedencia (contrato operativo §4.1):

1. JSON ausente o inválido de cualquier revisor obligatorio → ``FAILED_SAFELY``.
2. SHA revisado distinto del esperado o no demostrable → ``FAILED_SAFELY``.
3. ``FAILED_SAFELY`` de cualquiera → ``FAILED_SAFELY``.
4. ``BLOCKED_BY_DECISION`` de Claude → ``BLOCKED_BY_DECISION``.
5. ``CHANGES_REQUESTED`` de cualquiera → ``CHANGES_REQUESTED``.
6. Solo si ambos aprueban el mismo SHA → ``REVIEW_APPROVED``.

Las observaciones conservan su procedencia con prefijos ``CLAUDE-``/``CODEX-``
y solo se eliminan duplicados exactos (misma fuente, mismo archivo y mismo
cuerpo normalizado): es preferible conservar dos hallazgos parecidos con su
procedencia que borrar uno incorrectamente. Los textos de ambos revisores se
tratan como datos; este script nunca los interpreta como instrucciones.

En modo ``solo`` (bandera de revisión dual apagada) el resultado reproduce el
flujo vigente de revisión únicamente con Claude; el archivo de Codex se ignora.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

CLAUDE_STATUSES = {
    "REVIEW_APPROVED",
    "CHANGES_REQUESTED",
    "BLOCKED_BY_DECISION",
    "FAILED_SAFELY",
}
CODEX_STATUSES = {"APPROVED", "CHANGES_REQUESTED", "FAILED_SAFELY"}

# Cualquier URL dentro de un campo de contenido. Se neutraliza al construir la
# clave de deduplicación: identifica al comentario que reportó el hallazgo, no
# al hallazgo (ver `_dedupe`).
URL_RE = re.compile(r"https?://\S+")

OBSERVATION_KEYS = (
    "id",
    "severidad",
    "archivo",
    "problema",
    "criterio_esperado",
    "prueba",
    "limites_correccion",
)


def _sha_matches(expected_full: str, candidate: object) -> bool:
    """SHA declarado válido: completo o abreviatura (≥7 hex) que resuelva sin
    ambigüedad al SHA esperado."""
    if not isinstance(candidate, str):
        return False
    cand = candidate.strip().casefold()
    if not re.fullmatch(r"[0-9a-f]{7,40}", cand):
        return False
    return expected_full.casefold().startswith(cand)


def _load_json(path: str) -> dict[str, Any] | None:
    # `as exc` mantiene los paréntesis del except múltiple: este script lo
    # ejecuta el python3 del runner de Actions, que aún no entiende la forma
    # sin paréntesis de Python 3.14 (PEP 758).
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"sirius_aggregate_reviews: {path} ilegible: {exc}", file=sys.stderr)
        return None
    return data if isinstance(data, dict) else None


def _normalized_observations(raw: object, prefix: str) -> list[dict[str, str]] | None:
    """Observaciones con claves del contrato del corrector e IDs prefijados.

    Devuelve ``None`` si la estructura no es una lista de objetos (JSON
    inválido según el contrato).
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    observations: list[dict[str, str]] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            return None
        original_id = str(item.get("id") or f"{index:03d}").strip()
        if original_id.upper().startswith(f"{prefix}-"):
            identifier = original_id.upper()
        else:
            identifier = f"{prefix}-{original_id}"
        observation = {"id": identifier}
        for key in OBSERVATION_KEYS[1:]:
            observation[key] = str(item.get(key) or "").strip() or "(no indicado)"
        observations.append(observation)
    return observations


def _dedupe(observations: list[dict[str, str]]) -> list[dict[str, str]]:
    """Elimina solo duplicados inequívocos: misma procedencia (prefijo del ID) y
    TODO el contenido normalizado idéntico (archivo, problema, criterio, prueba,
    severidad y límites). Sin deduplicación semántica: dos hallazgos que
    difieren en cualquier campo se conservan ambos.

    Al construir la clave se neutralizan las URL de ``prueba``, y SOLO de ese
    campo. En los hallazgos de Codex ``prueba`` es el permalink del comentario
    que lo reportó, distinto para cada comentario aunque el defecto sea
    literalmente el mismo: si el conector publica el mismo hallazgo en dos
    revisiones —caso que el recolector contempla al unir todas las revisiones de
    la ronda—, la clave diferiría solo en ese enlace y el duplicado no se
    eliminaría nunca. El corrector recibiría el defecto repetido y, peor,
    ``pending`` y ``severity_total`` contarían comentarios en vez de defectos,
    falseando la medida de convergencia.

    Neutralizar las URL de TODOS los campos corregiría eso pero abriría un daño
    mayor y en la dirección contraria: dos hallazgos cuyo ``problema`` se
    distingue precisamente por una URL —dos advisories, dos endpoints, dos
    referencias distintas descritas con la misma frase— se fusionarían y uno se
    perdería. Borrar un hallazgo real es peor que conservar dos parecidos, así
    que la neutralización se limita al único campo que se sabe portador de
    metadato del canal, y **solo para la procedencia ``CODEX``**, que es donde
    se sabe qué contiene ese campo porque lo genera el propio recolector.

    Restringirlo por campo pero no por procedencia seguía siendo demasiado
    amplio: daba por supuesto que el ``prueba`` del revisor Claude nunca es un
    enlace, y eso es una suposición sobre la salida de un modelo, no una
    garantía. Dos observaciones de Claude por lo demás iguales cuya evidencia
    apunte a URL distintas —dos ejecuciones, dos casos, dos informes— son
    hallazgos distintos y deben conservarse ambos. El permalink de la primera
    aparición se conserva en la observación que sobrevive.
    """

    def key_value(source: str, field: str, value: str) -> str:
        if source == "CODEX" and field == "prueba":
            value = URL_RE.sub("<url>", value)
        return re.sub(r"\s+", " ", value).strip().casefold()

    seen: set[tuple[str, ...]] = set()
    unique: list[dict[str, str]] = []
    for observation in observations:
        source = observation["id"].split("-", 1)[0]
        key = (
            source,
            *(key_value(source, field, observation[field]) for field in OBSERVATION_KEYS[1:]),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(observation)
    return unique


def _failed(
    summary: str, sources: dict[str, dict[str, str]], *, infra_retryable: bool = False
) -> dict[str, Any]:
    resultado: dict[str, Any] = {
        "verdict": "FAILED_SAFELY",
        "summary": summary,
        "sources": sources,
        "observations": [],
    }
    if infra_retryable:
        # ADR-141: la parada es del ARNÉS de la revisión (head no demostrado,
        # timeout del recolector), no del contenido revisado. El aplicador de
        # veredictos puede re-armar UNA ronda nueva en vez de detener la
        # incidencia; cualquier otra parada se queda sin la bandera y detiene
        # como siempre.
        resultado["infra_retryable"] = True
    return resultado


def aggregate(
    claude: dict[str, Any] | None,
    codex: dict[str, Any] | None,
    expected_head: str,
    mode: str,
) -> dict[str, Any]:
    """Aplica las reglas de precedencia y devuelve el veredicto agregado."""
    sources: dict[str, dict[str, str]] = {}

    # --- Regla 1: validez estructural de cada revisor obligatorio -------------
    claude_status = str(claude.get("verdict") or "") if claude else ""
    if claude is None or claude_status not in CLAUDE_STATUSES:
        sources["claude"] = {"status": "INVALID"}
        return _failed(
            "El veredicto del revisor Claude está ausente o fuera del contrato; "
            "parada segura de la ronda de revisión.",
            sources,
        )
    sources["claude"] = {"status": claude_status}

    claude_observations = _normalized_observations(claude.get("observations"), "CLAUDE")
    if claude_observations is None or (
        claude_status == "CHANGES_REQUESTED" and not claude_observations
    ):
        sources["claude"] = {"status": "INVALID"}
        return _failed(
            "El revisor Claude pidió cambios sin observaciones estructuradas válidas; "
            "parada segura de la ronda de revisión.",
            sources,
        )

    codex_status = ""
    codex_observations: list[dict[str, str]] = []
    dual = mode == "dual"
    if dual:
        codex_status = str(codex.get("status") or "") if codex else ""
        if codex is None or codex_status not in CODEX_STATUSES:
            sources["codex"] = {"status": "INVALID"}
            return _failed(
                "El resultado de Codex está ausente o fuera del contrato; con la "
                "revisión dual activada Codex es obligatorio y la ronda se detiene "
                "de forma segura (sin degradar a revisión solo Claude).",
                sources,
            )
        sources["codex"] = {"status": codex_status}
        normalized = _normalized_observations(codex.get("observations"), "CODEX")
        if normalized is None or (codex_status == "CHANGES_REQUESTED" and not normalized):
            sources["codex"] = {"status": "INVALID"}
            return _failed(
                "Codex pidió cambios sin observaciones estructuradas válidas; "
                "parada segura de la ronda de revisión.",
                sources,
            )
        codex_observations = normalized

    # --- Regla 2: el SHA revisado debe ser demostrable e igual al esperado ----
    if claude_status in {"REVIEW_APPROVED", "CHANGES_REQUESTED"} and not _sha_matches(
        expected_head, claude.get("reviewed_head_sha")
    ):
        return _failed(
            "El revisor Claude no demostró haber revisado el head esperado "
            f"`{expected_head}` (reviewed_head_sha ausente o distinto); parada segura.",
            sources,
            infra_retryable=True,
        )
    if (
        dual
        and codex_status in {"APPROVED", "CHANGES_REQUESTED"}
        and not _sha_matches(expected_head, codex.get("reviewed_head_sha") if codex else None)
    ):
        return _failed(
            "Codex no demostró haber revisado el head esperado "
            f"`{expected_head}` (reviewed_head_sha ausente o distinto); parada segura.",
            sources,
            infra_retryable=True,
        )

    # --- Regla 3: fallo seguro de cualquiera -----------------------------------
    if claude_status == "FAILED_SAFELY" or (dual and codex_status == "FAILED_SAFELY"):
        details = []
        if claude_status == "FAILED_SAFELY":
            details.append(f"Claude: {str(claude.get('summary') or '').strip() or 'sin detalle'}")
        if dual and codex_status == "FAILED_SAFELY" and codex is not None:
            reason = str(codex.get("reason") or "").strip()
            summary = str(codex.get("summary") or "").strip() or "sin detalle"
            details.append(f"Codex{f' ({reason})' if reason else ''}: {summary}")
        # ADR-141: reintentable solo si la ÚNICA parada es el timeout del
        # recolector de Codex — una parada de contenido de Claude no se
        # reintenta sola, taparía su diagnóstico.
        solo_timeout_de_codex = (
            claude_status != "FAILED_SAFELY"
            and dual
            and codex_status == "FAILED_SAFELY"
            and codex is not None
            and str(codex.get("reason") or "").strip() == "timeout"
        )
        return _failed(
            "La ronda de revisión dual termina en fallo seguro. " + " | ".join(details),
            sources,
            infra_retryable=solo_timeout_de_codex,
        )

    # --- Regla 4: bloqueo por decisión de Claude --------------------------------
    if claude_status == "BLOCKED_BY_DECISION":
        return {
            "verdict": "BLOCKED_BY_DECISION",
            "summary": str(claude.get("summary") or "").strip()
            or "El revisor Claude requiere una decisión humana.",
            "sources": sources,
            "observations": [],
        }

    # --- Regla 5: cambios solicitados por cualquiera ----------------------------
    if claude_status == "CHANGES_REQUESTED" or (dual and codex_status == "CHANGES_REQUESTED"):
        observations = _dedupe(
            (claude_observations if claude_status == "CHANGES_REQUESTED" else [])
            + codex_observations
        )
        parts = [f"Claude: {claude_status}"]
        if dual:
            parts.append(f"Codex: {codex_status}")
        return {
            "verdict": "CHANGES_REQUESTED",
            "summary": (
                "Resultado conjunto de la revisión ("
                + "; ".join(parts)
                + f"): {len(observations)} observación(es) estructurada(s) para el corrector."
            ),
            "reviewed_head_sha": expected_head,
            "sources": sources,
            "observations": observations,
        }

    # --- Regla 6: aprobación solo si todos los obligatorios aprueban ------------
    summary = (
        "Revisión dual aprobada: Claude y Codex revisaron y aprobaron el mismo head."
        if dual
        else "Revisión aprobada por Claude (modo de revisión dual desactivado)."
    )
    return {
        "verdict": "REVIEW_APPROVED",
        "summary": summary,
        "reviewed_head_sha": expected_head,
        "sources": sources,
        "observations": [],
    }


def _full_sha(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value.strip().casefold()):
        raise argparse.ArgumentTypeError(f"se esperaba un SHA completo de 40 hex: {value!r}")
    return value.strip().casefold()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude-file", required=True, help="JSON del revisor Claude")
    parser.add_argument("--codex-file", required=True, help="JSON normalizado de Codex")
    parser.add_argument("--expected-head", required=True, type=_full_sha)
    parser.add_argument("--mode", required=True, choices=["dual", "solo"])
    parser.add_argument("--output", required=True, help="archivo JSON agregado de salida")
    args = parser.parse_args(argv)

    claude = _load_json(args.claude_file)
    codex = _load_json(args.codex_file) if args.mode == "dual" else None
    aggregated = aggregate(claude, codex, args.expected_head, args.mode)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(aggregated, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        f"sirius_aggregate_reviews: veredicto agregado {aggregated['verdict']} "
        f"escrito en {args.output}.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
