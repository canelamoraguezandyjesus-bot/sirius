"""``sirius-familia-repetida``: línea de órdenes del detector de M1 (incidencia #277).

Ejecuta :func:`sirius_engine.round_family_detector.detectar_familia_repetida`
sobre el historial de una incidencia YA LEÍDO: recibe un archivo de texto con
el cuerpo y los comentarios de confianza, concatenados del más antiguo al más
reciente -el mismo formato que espera
:func:`sirius_engine.round_history.parse_round_records`-, y publica el
resultado en JSON. No llama a `gh` ni a ningún modelo (criterio de parada (b)
de la nota de arranque): quien invoque este comando es responsable de haber
leído ya el historial por su cuenta.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from sirius_engine.round_family_detector import detectar_familia_repetida
from sirius_engine.round_history import history_after_last_resume, parse_round_records

COMANDO = "sirius-familia-repetida"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=COMANDO,
        description=(
            "Detecta si las rondas de revisión de una incidencia están dando vueltas "
            "sobre la misma familia de defecto (M1, incidencia #277). Solo señala el "
            "dato y su evidencia: no diagnostica la causa ni decide nada por sí mismo."
        ),
    )
    parser.add_argument(
        "--historial",
        required=True,
        help=(
            "ruta a un archivo de texto con el cuerpo y los comentarios de confianza de "
            "la incidencia, ya leídos y concatenados del más antiguo al más reciente"
        ),
    )
    parser.add_argument(
        "--salida",
        default=None,
        help="ruta del JSON de salida; por defecto, la salida estándar",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        texto = Path(args.historial).read_text(encoding="utf-8")
    except OSError as error:
        print(f"{COMANDO}: no se pudo leer {args.historial} ({error}).", file=sys.stderr)
        return 1

    vigente = history_after_last_resume(texto)
    registros = parse_round_records(vigente)
    deteccion = detectar_familia_repetida(registros)

    payload = {
        "hay_familia_repetida": deteccion.hay_familia_repetida,
        "evidencias": [asdict(evidencia) for evidencia in deteccion.evidencias],
    }
    texto_json = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.salida:
        Path(args.salida).write_text(texto_json + "\n", encoding="utf-8")
    else:
        print(texto_json)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
