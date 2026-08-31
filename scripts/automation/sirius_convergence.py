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

Los analizadores puros del historial (``parse_round_records``,
``history_after_last_resume``, ``ci_failure_streak`` y lo que necesitan) ya no
se definen aquí: viven en ``src/sirius_engine/round_history.py``, dentro del
paquete y sin ninguna copia ni enlace hermano -el árbol versionado no tiene
enlaces simbólicos y una prueba lo prohíbe-, porque
:mod:`sirius_engine.mirror_projection` (incidencia #193)
también los necesita y, a diferencia de este script, se importa desde una
instalación real del paquete (H-13, incidencia #275). Este módulo los importa
por ruta de fichero, no con ``import sirius_engine...``: ese import obligaría
a este script -que ``repair-sirius-work.yml`` ejecuta con el ``python3`` del
sistema, sin el proyecto instalado- a depender del paquete y sus dependencias.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

#: El módulo compartido vive UNA sola vez, dentro del paquete. Este script lo
#: alcanza por ruta relativa al árbol, no por importación: `sirius_convergence`
#: se ejecuta con el `python3` del sistema -`repair-sirius-work.yml:285`-, sin
#: el entorno del proyecto instalado, así que `import sirius_engine` no es una
#: opción (criterio de parada (a) de la incidencia #275).
#:
#: Se resuelve la ruta directamente en vez de dejar un enlace simbólico
#: hermano: el árbol versionado no tiene ninguno, y una prueba lo prohíbe
#: -`test_el_arbol_versionado_no_contiene_enlaces_simbolicos`- porque
#: `_contenida_en_raiz` colapsa los `..` sin resolverlos y una cita que
#: atravesara un enlace validaría un fichero distinto del citado.
_RUTA_COMPARTIDA = (
    Path(__file__).resolve().parents[2] / "src" / "sirius_engine" / "round_history.py"
)


def _cargar_round_history() -> ModuleType:
    ruta = _RUTA_COMPARTIDA
    spec = importlib.util.spec_from_file_location("sirius_round_history", ruta)
    if spec is None or spec.loader is None:  # pragma: no cover - defensivo
        raise ImportError(f"No se pudo cargar el módulo compartido en {ruta}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


_round_history = _cargar_round_history()
parse_round_records = _round_history.parse_round_records
history_after_last_resume = _round_history.history_after_last_resume
ci_failure_streak = _round_history.ci_failure_streak
severity_weight = _round_history.severity_weight
_normalize_text = _round_history._normalize_text
_normalize_location = _round_history._normalize_location

#: Detector de familia repetida (ADR-078, incidencia #277): construido y
#: medido, pero sin llamante hasta esta incidencia (#495, informe de la mina
#: `docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md` §7). Se carga
#: por ruta, igual que ``round_history.py`` arriba y por el mismo motivo: este
#: script corre con el ``python3`` del sistema, sin el proyecto instalado.
#:
#: A diferencia de ``round_history.py``, ``round_family_detector.py`` SÍ hace
#: ``from sirius_engine.round_history import _normalize_location`` -es un
#: módulo normal del paquete, pensado para instalarse-, y esa importación
#: fallaría con ``ModuleNotFoundError`` bajo un intérprete sin el paquete
#: instalado. En vez de tocar su interfaz (el objetivo de la incidencia #495
#: pide no hacerlo salvo que sea imprescindible), se registra en
#: ``sys.modules`` un paquete ``sirius_engine`` mínimo con su submódulo
#: ``round_history`` ya apuntando al módulo cargado por ruta arriba, ANTES de
#: ejecutar el archivo: el import de ``round_family_detector.py`` encuentra el
#: nombre completo ya resuelto en ``sys.modules`` y nunca toca el sistema de
#: importación real. Verificado bajo el ``python3`` desnudo del runner en
#: ``test_cli_family_check_runs_under_the_bare_system_python_without_the_project_installed``.
#:
#: Ese registro se **deshace siempre al terminar**, tanto si ``sirius_engine``
#: no existía en el proceso como si ya era el paquete real -por ejemplo, bajo
#: pytest, que lo importa de verdad al recolectar otras pruebas del árbol-:
#: sin esto, el simulacro sustituía en ``sys.modules`` el submódulo real
#: ``sirius_engine.round_history`` por el duplicado cargado por ruta durante
#: el resto del proceso, rompiendo el aislamiento que ``_cargar_round_history``
#: ya garantiza dos funciones más arriba con su nombre privado
#: ``sirius_round_history`` (hallazgo CLAUDE-FAM-DETECT-001, incidencia #495).
_RUTA_FAMILY_DETECTOR = (
    Path(__file__).resolve().parents[2] / "src" / "sirius_engine" / "round_family_detector.py"
)


def _cargar_round_family_detector() -> ModuleType:
    paquete_previo = sys.modules.get("sirius_engine")
    round_history_previo = sys.modules.get("sirius_engine.round_history")
    tenia_atributo = paquete_previo is not None and hasattr(paquete_previo, "round_history")
    atributo_previo = getattr(paquete_previo, "round_history", None)

    paquete_simulado = paquete_previo
    if paquete_simulado is None:
        paquete_simulado = ModuleType("sirius_engine")
        paquete_simulado.__path__ = []  # type: ignore[attr-defined]
    sys.modules["sirius_engine"] = paquete_simulado
    sys.modules["sirius_engine.round_history"] = _round_history
    paquete_simulado.round_history = _round_history  # type: ignore[attr-defined]

    ruta = _RUTA_FAMILY_DETECTOR
    spec = importlib.util.spec_from_file_location("sirius_round_family_detector", ruta)
    if spec is None or spec.loader is None:  # pragma: no cover - defensivo
        raise ImportError(f"No se pudo cargar el módulo compartido en {ruta}")
    modulo = importlib.util.module_from_spec(spec)
    # Registrado ANTES de ejecutar, con su propio nombre: el módulo declara
    # ``@dataclass(frozen=True, slots=True)``, y ``dataclasses`` resuelve sus
    # anotaciones buscando ``sys.modules[cls.__module__]`` mientras la clase se
    # procesa. Sin este registro previo, la búsqueda encuentra ``None`` y la
    # carga falla con ``AttributeError`` antes de llegar a la primera línea
    # útil del módulo -``round_history.py``, cargado igual arriba, no lo
    # necesita porque no define ninguna dataclass-.
    sys.modules[spec.name] = modulo
    try:
        spec.loader.exec_module(modulo)
    finally:
        if paquete_previo is None:
            sys.modules.pop("sirius_engine", None)
        else:
            sys.modules["sirius_engine"] = paquete_previo
            if tenia_atributo:
                paquete_previo.round_history = atributo_previo  # type: ignore[attr-defined]
            elif hasattr(paquete_previo, "round_history"):
                del paquete_previo.round_history  # type: ignore[attr-defined]
        if round_history_previo is None:
            sys.modules.pop("sirius_engine.round_history", None)
        else:
            sys.modules["sirius_engine.round_history"] = round_history_previo
    return modulo


#: Caché de la carga perezosa: ``None`` hasta que ``family-check`` se ejecuta
#: de verdad por primera vez en el proceso.
_round_family_detector_cache: ModuleType | None = None


def _obtener_round_family_detector() -> ModuleType:
    """Carga perezosa de ``round_family_detector.py``.

    Cargarlo al importar este módulo -como antes- hacía que un fallo del
    detector (archivo ausente, error de importación, regresión al evaluarlo)
    también hiciera fallar los subcomandos críticos ``record`` y ``decide``,
    que ni siquiera lo usan: `record` y `decide` se ejecutan en cada ronda,
    mientras que el detector es solo un aviso informativo (ADR-121). Se carga
    aquí, solo cuando ``cmd_family_check`` lo necesita de verdad (hallazgo
    CODEX-001, incidencia #495).
    """
    global _round_family_detector_cache
    if _round_family_detector_cache is None:
        _round_family_detector_cache = _cargar_round_family_detector()
    return _round_family_detector_cache


# Intentos consecutivos de corrección motivados por un fallo de Quality, sin un
# Quality en verde de por medio, antes de pasar a decisión humana. Tres da
# margen a un arreglo de construcción real —el primero puede ser un diagnóstico
# equivocado— sin permitir un bucle indefinido.
MAX_CI_FAILURE_STREAK = 3


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


def decide(records: list[dict[str, Any]], ci_failures: int = 0) -> dict[str, Any]:
    """Decisión determinista sobre si la siguiente corrección puede continuar.

    ``ci_failures`` son los intentos consecutivos motivados por un fallo de
    Quality desde el último Quality en verde. Se comprueban ANTES que nada: son
    el otro motor del ciclo y el único que la medida de progreso no puede ver,
    porque ese camino no publica registros de ronda.
    """
    if ci_failures >= MAX_CI_FAILURE_STREAK:
        return {
            "decision": "BLOCK",
            "reason": "ci-sin-arreglo",
            "detail": (
                f"Quality ha fallado {ci_failures} veces seguidas sin un verde de por medio. "
                "La corrección automática no está consiguiendo arreglar la construcción, y "
                "seguir reintentando no es progreso: se requiere una decisión humana."
            ),
            "rounds": len(records),
            "ci_failures": ci_failures,
        }

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
        # El corte se aplica UNA vez y alimenta las dos medidas, para que no
        # puedan discrepar sobre dónde empieza el historial vigente.
        vigente = history_after_last_resume(text)
        result = decide(parse_round_records(vigente), ci_failures=ci_failure_streak(vigente))
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"{result['decision']} ({result['reason']}): {result['detail']}", file=sys.stderr)
    return 0


def cmd_family_check(args: argparse.Namespace) -> int:
    """Aviso informativo de familia repetida (ADR-078) sobre un historial ya leído.

    ``comments_file`` es responsabilidad de quien invoca (incidencia #495,
    mismo contrato que ``sirius-familia-repetida``): el historial de
    comentarios de confianza, del más antiguo al más reciente, incluyendo YA
    la ronda que se está publicando -este comando no llama a ``gh`` ni
    conoce la ronda actual por sí mismo-.

    Nunca falla de forma que bloquee al llamador (requisito (b) de la
    incidencia #495 y ADR-121: este aviso informa, no decide): un historial
    ilegible, o un fallo al cargar el propio detector (hallazgo CODEX-001),
    se publican como ``hay_familia_repetida: false`` con el motivo en
    ``error``, en vez de como código de salida distinto de 0.
    """
    try:
        with open(args.comments_file, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        result: dict[str, Any] = {
            "hay_familia_repetida": False,
            "evidencias": [],
            "error": f"No se pudo leer el historial ({exc}).",
        }
    else:
        try:
            detector = _obtener_round_family_detector()
        except Exception as exc:
            result = {
                "hay_familia_repetida": False,
                "evidencias": [],
                "error": f"No se pudo cargar el detector de familia repetida ({exc}).",
            }
        else:
            vigente = history_after_last_resume(text)
            deteccion = detector.detectar_familia_repetida(parse_round_records(vigente))
            result = {
                "hay_familia_repetida": deteccion.hay_familia_repetida,
                "evidencias": [
                    {"archivo": e.archivo, "rondas": list(e.rondas), "detalle": e.detalle}
                    for e in deteccion.evidencias
                ],
            }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
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

    family_check = subparsers.add_parser(
        "family-check", help="aviso informativo de familia repetida (ADR-078)"
    )
    family_check.add_argument(
        "--comments-file",
        required=True,
        help=(
            "archivo con los comentarios de confianza de la incidencia, del más antiguo "
            "al más reciente, incluyendo ya la ronda que se está publicando"
        ),
    )
    family_check.add_argument("--output", required=True, help="archivo JSON con el aviso")
    family_check.set_defaults(func=cmd_family_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handler = args.func
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
