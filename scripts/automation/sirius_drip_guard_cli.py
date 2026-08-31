#!/usr/bin/env python3
"""Sirius — línea de órdenes del guardián de goteo en vivo (incidencia #496, ADR-121).

Lee el historial de rondas YA VOLCADO de una incidencia (mismo formato que
espera :func:`sirius_engine.round_history.parse_round_records`: los
comentarios de confianza concatenados del más antiguo al más reciente) y las
observaciones estructuradas que ``sirius_apply_verdict.sh`` está a punto de
publicar como la ronda actual, y escribe esas mismas observaciones con el
campo ``posible_goteo`` añadido donde corresponda
(:mod:`sirius_engine.drip_guard`).

Se ejecuta con el ``python3`` del sistema, igual que
``sirius_convergence.py`` -sin el proyecto instalado
(`repair-sirius-work.yml`)-, así que carga los módulos compartidos por ruta
de fichero en vez de con ``import sirius_engine...``.

Nunca hace fallar el proceso completo por un problema propio: el guardián es
estrictamente informativo (regla (a) de la incidencia #496). Ante cualquier
error -historial ilegible, `gh` no disponible, JSON corrupto- escribe las
observaciones de entrada SIN anotar y declara el motivo por stderr.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

_RAIZ = Path(__file__).resolve().parents[2] / "src" / "sirius_engine"


def _cargar(nombre: str, archivo: str) -> ModuleType:
    ruta = _RAIZ / archivo
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    if spec is None or spec.loader is None:  # pragma: no cover - defensivo
        raise ImportError(f"No se pudo cargar el módulo compartido en {ruta}")
    modulo = importlib.util.module_from_spec(spec)
    # Registrado en sys.modules ANTES de ejecutar el cuerpo: `drip_guard.py`
    # usa `@dataclass(slots=True)` con anotaciones de cadena
    # (`from __future__ import annotations`), y la propia biblioteca estándar
    # de dataclasses resuelve esas anotaciones buscando
    # `sys.modules[cls.__module__]` en tiempo de definición de la clase. Sin
    # este registro, esa búsqueda encuentra `None` y la carga del módulo
    # revienta con un `AttributeError` que no tiene nada que ver con este
    # guardián -un módulo cargado por ruta sin dataclasses (como
    # `round_history.py`) nunca lo dispara, así que pasa desapercibido hasta
    # que un módulo con dataclasses lo hereda-.
    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)
    return modulo


_round_history = _cargar("sirius_round_history", "round_history.py")
_drip_guard = _cargar("sirius_drip_guard", "drip_guard.py")
parse_round_records = _round_history.parse_round_records
annotate_observations = _drip_guard.annotate_observations
gh_compare_file = _drip_guard.gh_compare_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument(
        "--comments-file",
        required=True,
        help="historial de la incidencia, comentarios de confianza del más antiguo al más reciente",
    )
    parser.add_argument("--round", required=True, type=int, help="número de la ronda actual")
    parser.add_argument("--head", required=True, help="head SHA de la ronda actual")
    parser.add_argument(
        "--observations",
        required=True,
        help="JSON (archivo) con el array de observaciones de la ronda actual",
    )
    parser.add_argument("--output", required=True, help="ruta donde escribir el JSON anotado")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        observations = json.loads(Path(args.observations).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(
            f"sirius_drip_guard_cli: observaciones ilegibles ({error}); nada que anotar.",
            file=sys.stderr,
        )
        return _escribir_sin_anotar([], args.output)
    if not isinstance(observations, list):
        print(
            "sirius_drip_guard_cli: las observaciones no son una lista; nada que anotar.",
            file=sys.stderr,
        )
        return _escribir_sin_anotar([], args.output)

    try:
        texto_historial = Path(args.comments_file).read_text(encoding="utf-8")
        round_records = parse_round_records(texto_historial)
        anotadas = annotate_observations(
            observations,
            round_number=args.round,
            round_records=round_records,
            current_head=args.head,
            repo=args.repo,
            fetch=gh_compare_file,
        )
    except Exception as error:  # guardián informativo (regla (a), incidencia #496): nunca bloquea
        print(
            f"sirius_drip_guard_cli: fallo evaluando el goteo ({error}); "
            "se publican las observaciones sin anotar.",
            file=sys.stderr,
        )
        return _escribir_sin_anotar(observations, args.output)

    marcadas = sum(1 for item in anotadas if isinstance(item, dict) and item.get("posible_goteo"))
    print(
        f"sirius_drip_guard_cli: {marcadas} de {len(anotadas)} observación(es) marcadas.",
        file=sys.stderr,
    )
    Path(args.output).write_text(json.dumps(anotadas, ensure_ascii=False), encoding="utf-8")
    return 0


def _escribir_sin_anotar(observations: list[object], output: str) -> int:
    Path(output).write_text(json.dumps(observations, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
