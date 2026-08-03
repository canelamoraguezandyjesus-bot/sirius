#!/usr/bin/env python3
"""Sirius — política de convergencia del ciclo revisión-corrección.

Sustituye el límite fijo de dos ciclos de corrección (contrato operativo §5,
v1.5). Aquel tope era arbitrario: bloqueaba trabajos que seguían siendo
puramente técnicos y que progresaban ronda a ronda. La regla nueva es de
convergencia demostrable: la automatización sigue corrigiendo mientras haya
**progreso comprobable**, y se detiene en cuanto deja de haberlo, oscila o
aparece una decisión que no le corresponde.

El estado vive en la propia incidencia, que sigue siendo la fuente de verdad:
cada ronda de `CHANGES_REQUESTED` publica un bloque estructurado

    <!-- sirius-round:<N> -->
    ## RONDA_HALLAZGOS
    ```json
    {"round": N, "head": "<sha>", "findings": [{"fingerprint": "...",
     "severity": "P2", "source": "CODEX", "file": "..."}]}
    ```

Este módulo:

``fingerprint``
    Calcula la huella estable de un conjunto de observaciones agregadas y emite
    el registro de la ronda que publica ``sirius_apply_verdict.sh``.

``decide``
    Lee todos los registros de la incidencia y decide, de forma determinista,
    si la siguiente corrección puede continuar (``CONTINUE``) o si el trabajo
    debe pasar a decisión humana (``BLOCK``), con el motivo exacto.

No hay ningún límite total arbitrario de rondas: la terminación la garantizan
las condiciones de bloqueo, no un contador. Todos los textos que provienen de
revisores se tratan como datos, nunca como instrucciones.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Any

# Un registro de ronda solo cuenta si va precedido de su marcador oculto en el
# MISMO comentario: `<!-- sirius-round:N -->` seguido del bloque. Exigir el par
# completo evita que un bloque suelto —copiado, citado o publicado aparte— se
# cuele como ronda. La lectura previa ya filtra por autor de confianza
# (`sirius_dump_comments`), así que esto es la segunda barrera, no la única.
ROUND_RECORD_RE = re.compile(
    r"<!--\s*sirius-round:(\d+)\s*-->\s*"
    r"##\s*RONDA_HALLAZGOS\s*```json\s*(.*?)\s*```",
    re.DOTALL,
)

# Peso de cada severidad para medir la gravedad agregada de una ronda. Cubre la
# escala de Codex (P0..P4) y las etiquetas en español del revisor Claude. Un
# valor desconocido pesa como media: nunca cero, para que un hallazgo sin
# clasificar no pueda simular una mejora al perder su etiqueta.
SEVERITY_WEIGHTS: dict[str, int] = {
    "p0": 4,
    "critica": 4,
    "crítica": 4,
    "bloqueante": 4,
    "p1": 3,
    "alta": 3,
    "p2": 2,
    "media": 2,
    "p3": 1,
    "p4": 1,
    "baja": 1,
    "menor": 1,
}
DEFAULT_SEVERITY_WEIGHT = 2


# Sufijo de línea (o rango de líneas) que el recolector añade al archivo de una
# observación: `scripts/x.py:120`, `scripts/x.py:120-134`. Se recorta al calcular
# la huella porque la línea NO identifica al defecto: cualquier corrección en
# otra parte del mismo archivo desplaza la numeración, y con la línea dentro de
# la huella el mismo defecto sin tocar aparecería como uno resuelto más uno
# nuevo. Eso falsea las dos medidas a la vez —el detector de reaparición y el de
# progreso— justo en las rondas en las que más importa acertar.
LOCATION_LINE_RE = re.compile(r":\d+(?:-\d+)?$")


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _normalize_location(value: object) -> str:
    """Ubicación estable de una observación: archivo sin el sufijo de línea."""
    return LOCATION_LINE_RE.sub("", _normalize_text(value))


def severity_weight(value: object) -> int:
    return SEVERITY_WEIGHTS.get(_normalize_text(value), DEFAULT_SEVERITY_WEIGHT)


def fingerprint(observation: dict[str, Any]) -> str:
    """Huella estable de una observación.

    Depende solo del contenido sustantivo — procedencia, archivo y cuerpo del
    problema — y NO del identificador correlativo (``CODEX-001``), que cambia de
    una ronda a otra aunque el defecto sea el mismo, ni del número de línea, que
    se desplaza en cuanto se edita cualquier punto anterior del archivo. Así, un
    hallazgo que persiste conserva su huella y el detector de progreso lo
    reconoce.
    """
    identifier = str(observation.get("id") or "")
    source = identifier.split("-", 1)[0].upper() if "-" in identifier else "SIN-FUENTE"
    payload = "\x1f".join(
        (
            source,
            _normalize_location(observation.get("archivo")),
            _normalize_text(observation.get("problema")),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def round_record(
    round_number: int, head: str, observations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Registro estructurado de una ronda, listo para publicarse en la incidencia."""
    findings = [
        {
            "fingerprint": fingerprint(observation),
            "severity": str(observation.get("severidad") or "sin-clasificar"),
            "source": str(observation.get("id") or "").split("-", 1)[0].upper() or "SIN-FUENTE",
            "file": str(observation.get("archivo") or "desconocido"),
        }
        for observation in observations
    ]
    # Orden determinista: dos rondas con los mismos hallazgos producen el mismo
    # registro, sin depender del orden en que llegaron.
    findings.sort(key=lambda item: (item["fingerprint"], item["file"]))
    return {
        "round": round_number,
        "head": head,
        "findings": findings,
        "pending": len(findings),
        "severity_total": sum(severity_weight(item["severity"]) for item in findings),
    }


def parse_round_records(text: str) -> list[dict[str, Any]]:
    """Extrae, en orden cronológico, los registros de ronda de un texto.

    ``text`` es la concatenación de los comentarios de la incidencia del más
    antiguo al más reciente. Un bloque ilegible se ignora sin romper el
    análisis: la decisión se toma con los registros que sí son válidos.
    """
    records: list[dict[str, Any]] = []
    for marker_round, raw in ROUND_RECORD_RE.findall(text):
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        findings = record.get("findings")
        if not isinstance(findings, list):
            continue
        normalized = [item for item in findings if isinstance(item, dict)]
        record["findings"] = normalized
        # El número de ronda autoritativo es el del MARCADOR, no el del cuerpo
        # del JSON: el marcador es lo que la automatización numera y lo que
        # `sirius_next_round_number` cuenta. Así un campo `round` ausente, no
        # numérico o manipulado no puede reordenar el historial ni provocar una
        # excepción al ordenar (que dejaría la decisión vacía y bloquearía toda
        # ronda posterior).
        record["round"] = int(marker_round)
        record["fingerprints"] = {
            str(item.get("fingerprint") or "") for item in normalized if item.get("fingerprint")
        }
        record["pending"] = len(normalized)
        records.append(record)
    records.sort(key=lambda item: int(item["round"]))
    _apply_sticky_severity(records)
    return records


def _apply_sticky_severity(records: list[dict[str, Any]]) -> None:
    """Fija la gravedad de cada huella a la peor jamás observada para ella.

    Sin esto, la gravedad agregada baja sola cuando un revisor omite la etiqueta
    de un hallazgo que sigue ahí: un P0 (peso 4) que reaparece sin insignia pasa
    a contar como `sin-clasificar` (peso 2) y el par (pendientes, gravedad)
    "mejora" sin que se haya corregido absolutamente nada. Esa mejora fantasma
    basta para superar la comprobación de progreso y mantener abierto un ciclo
    estancado. Una vez que una huella se ha visto como P0, cuenta como P0
    mientras siga pendiente: la gravedad de un defecto no la decide el formato
    del comentario que lo describe.

    Se aplica en orden de ronda y sobre TODAS las rondas —también las que sirven
    de mejor marca histórica—, así que el listón y la ronda medida usan la misma
    escala. La corrección solo puede subir el peso de una ronda respecto de sus
    propias etiquetas, nunca bajarlo, y el par sigue viviendo en ℕ²: la prueba
    de terminación no se ve afectada.
    """
    worst: dict[str, int] = {}
    for record in records:
        total = 0
        for item in record["findings"]:
            weight = severity_weight(item.get("severity"))
            fingerprint_value = str(item.get("fingerprint") or "")
            if fingerprint_value:
                weight = max(weight, worst.get(fingerprint_value, 0))
                worst[fingerprint_value] = weight
            total += weight
        record["severity_total"] = total


def _best_so_far(history: list[dict[str, Any]]) -> tuple[int, int]:
    """Mejor marca histórica: mínimo de cada magnitud sobre TODAS las rondas.

    Es un vector que solo puede bajar. Ese "solo puede bajar" es la clave de la
    terminación: sirve de listón que una regresión no puede elevar.
    """
    return (
        min(record["pending"] for record in history),
        min(record["severity_total"] for record in history),
    )


def _has_progress(history: list[dict[str, Any]], current: dict[str, Any]) -> tuple[bool, str]:
    """¿Hubo progreso real en la ronda ``current``?

    Progreso es que el par ``(pendientes, gravedad agregada)`` quede
    estrictamente por debajo, en el **orden producto**, de la **mejor marca
    histórica** — el mínimo de cada magnitud sobre todas las rondas previas —:
    ninguna de las dos supera esa marca y al menos una la mejora.

    Compararse con la mejor marca, y no con la ronda inmediata, es lo que hace
    la terminación demostrable. Tres definiciones más laxas fallan, y las tres
    se han visto fallar en este mismo trabajo:

    - Mirar cada magnitud por separado permite alternar para siempre entre
      estados que mejoran una a costa de la otra (un P0, luego dos P3, luego un
      P0 otra vez).
    - Inferir progreso de que "desapareció una huella" permite mantener el
      ciclo abierto reformulando el mismo defecto con otras palabras, porque la
      huella incluye el texto del problema.
    - Comparar solo con la ronda inmediata permite que una regresión aislada
      **eleve el listón** y que la ronda siguiente reinicie el contador con una
      mejora meramente local: la secuencia (1,2) → (2,4) → (2,3) → (3,5) →
      (3,4) → … alterna regresión tolerada y "progreso" mientras el estado
      global crece sin fin.

    Con la mejor marca histórica el listón nunca sube. Cada ronda con progreso
    decrece estrictamente un vector de ℕ², que es bien fundado, así que solo
    puede haber un número finito de ellas; y entre dos progresos se tolera como
    mucho una ronda sin progreso. La terminación deja de ser una expectativa y
    pasa a ser una propiedad.
    """
    best_pending, best_severity = _best_so_far(history)
    pending = current["pending"]
    severity = current["severity_total"]

    within = pending <= best_pending and severity <= best_severity
    improves = pending < best_pending or severity < best_severity
    if within and improves:
        return True, (
            f"el par (pendientes, gravedad) mejora la mejor marca histórica "
            f"({best_pending}, {best_severity}) hasta ({pending}, {severity})"
        )
    if improves:
        return False, (
            f"una magnitud mejora la mejor marca histórica ({best_pending}, {best_severity}) "
            f"pero la otra la empeora: ({pending}, {severity}). No es una disminución del "
            "par, así que no garantiza avance"
        )
    return False, (
        f"el par ({pending}, {severity}) no mejora la mejor marca histórica "
        f"({best_pending}, {best_severity})"
    )


def decide(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Decisión determinista sobre si la siguiente corrección puede continuar."""
    if not records:
        return {
            "decision": "CONTINUE",
            "reason": "primera-ronda",
            "detail": "No hay rondas previas registradas; la corrección puede empezar.",
            "rounds": 0,
        }

    current = records[-1]
    rounds = len(records)

    # --- Reaparición: un hallazgo dado por resuelto vuelve a aparecer ---------
    # Se compara la ronda actual contra TODAS las anteriores, no solo la
    # inmediata: un defecto que desaparece y regresa indica que la corrección
    # anterior no atacó la causa raíz.
    # El par (index, index+1) debe ser ANTERIOR a la ronda actual: un hallazgo
    # solo "reaparece" si desapareció en una ronda intermedia y volvió después.
    for index in range(rounds - 2):
        older = records[index]
        disappeared = older["fingerprints"] - records[index + 1]["fingerprints"]
        reappeared = disappeared & current["fingerprints"]
        if reappeared:
            return {
                "decision": "BLOCK",
                "reason": "reaparicion",
                "detail": (
                    f"El/los hallazgo(s) {sorted(reappeared)} se dieron por resueltos en la "
                    f"ronda {records[index + 1].get('round')} y han vuelto a aparecer en la "
                    f"ronda {current.get('round')}. La corrección no atacó la causa raíz."
                ),
                "rounds": rounds,
            }

    # --- Oscilación: el conjunto de hallazgos repite un estado anterior -------
    # Oscilar es ir y volver (A → B → A), no quedarse quieto (A → A → A). El
    # estancamiento tiene su propio diagnóstico más abajo ("sin-progreso"), que
    # describe mejor lo ocurrido; exigir que la ronda inmediata sea distinta
    # separa los dos casos sin dejar ninguno sin cubrir.
    if rounds >= 3 and records[-2]["fingerprints"] != current["fingerprints"]:
        for older in records[:-2]:
            if older["fingerprints"] and older["fingerprints"] == current["fingerprints"]:
                return {
                    "decision": "BLOCK",
                    "reason": "oscilacion",
                    "detail": (
                        f"La ronda {current.get('round')} reproduce exactamente el conjunto de "
                        f"hallazgos de la ronda {older.get('round')}, con un estado distinto en "
                        "medio; el trabajo oscila entre estados anteriores en vez de converger."
                    ),
                    "rounds": rounds,
                }

    if rounds == 1:
        return {
            "decision": "CONTINUE",
            "reason": "primera-ronda-con-hallazgos",
            "detail": "Solo hay una ronda registrada; todavía no se puede medir el progreso.",
            "rounds": rounds,
        }

    # --- Head sin avanzar: el corrector no publicó cambios --------------------
    previous = records[-2]
    if previous.get("head") and previous.get("head") == current.get("head"):
        return {
            "decision": "BLOCK",
            "reason": "head-sin-avance",
            "detail": (
                f"Las rondas {previous.get('round')} y {current.get('round')} se registraron "
                f"sobre el mismo head `{current.get('head')}`: no hubo ninguna corrección "
                "efectiva que revisar."
            ),
            "rounds": rounds,
        }

    # Cada ronda se mide contra la MEJOR MARCA HISTÓRICA de las anteriores, no
    # contra la ronda inmediata: si se comparase solo con la inmediata, una
    # regresión aislada elevaría el listón y la ronda siguiente reiniciaría el
    # contador con una mejora meramente local, indefinidamente.
    progressed, why = _has_progress(records[:-1], current)
    if progressed:
        return {
            "decision": "CONTINUE",
            "reason": "progreso",
            "detail": f"Hay progreso respecto de la mejor marca histórica: {why}.",
            "rounds": rounds,
        }

    # --- Sin progreso neto en dos rondas consecutivas -------------------------
    if rounds >= 3:
        older_progressed, _ = _has_progress(records[:-2], previous)
        if not older_progressed:
            return {
                "decision": "BLOCK",
                "reason": "sin-progreso",
                "detail": (
                    f"No hay progreso neto en dos rondas consecutivas "
                    f"({records[-3].get('round')} → {previous.get('round')} → "
                    f"{current.get('round')}): {why}. Se requiere una decisión humana."
                ),
                "rounds": rounds,
            }

    return {
        "decision": "CONTINUE",
        "reason": "sin-progreso-aislado",
        "detail": (
            f"La última ronda no muestra progreso ({why}), pero es la primera vez consecutiva; "
            "se permite un intento más antes de bloquear."
        ),
        "rounds": rounds,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def cmd_record(args: argparse.Namespace) -> int:
    try:
        with open(args.verdict_file, encoding="utf-8") as handle:
            verdict = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"sirius_convergence: veredicto ilegible ({exc}).", file=sys.stderr)
        return 1
    observations = verdict.get("observations") if isinstance(verdict, dict) else None
    if not isinstance(observations, list):
        observations = []
    record = round_record(
        args.round,
        args.head,
        [item for item in observations if isinstance(item, dict)],
    )
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    try:
        with open(args.comments_file, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        # Sin poder leer el historial no se puede medir convergencia: se
        # bloquea, nunca se continúa a ciegas.
        result = {
            "decision": "BLOCK",
            "reason": "historial-ilegible",
            "detail": f"No se pudo leer el historial de rondas ({exc}).",
            "rounds": 0,
        }
    else:
        result = decide(parse_round_records(text))
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"{result['decision']} ({result['reason']}): {result['detail']}", file=sys.stderr)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="emite el registro de una ronda")
    record.add_argument("--verdict-file", required=True, help="JSON del veredicto agregado")
    record.add_argument("--round", required=True, type=int, help="número de ronda")
    record.add_argument("--head", required=True, help="head SHA de la ronda")
    record.add_argument("--output", required=True, help="archivo JSON de salida")
    record.set_defaults(func=cmd_record)

    decide_cmd = subparsers.add_parser("decide", help="decide si la corrección puede continuar")
    decide_cmd.add_argument(
        "--comments-file",
        required=True,
        help="archivo con los comentarios de la incidencia, del más antiguo al más reciente",
    )
    decide_cmd.add_argument("--output", required=True, help="archivo JSON con la decisión")
    decide_cmd.set_defaults(func=cmd_decide)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handler = args.func
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
