"""``sirius-memoria``: escribe las dos vistas de la memoria común (ADR-171).

Cáscara y nada más, como ``sirius-reflejar``: resuelve rutas y llama a las
funciones puras de :mod:`sirius_engine.memoria`. Dos subcomandos:

- ``conocimiento`` escribe ``MEMORIA.md`` en la raíz del repositorio a partir
  del árbol; con ``--comprobar`` no escribe nada y sale con 1 si el fichero
  confirmado no coincide con lo que se generaría, diciendo qué hacer.
- ``desenlaces`` escribe ``DESENLACES.md`` junto al diario del motor, a partir
  de ``diario.jsonl`` y de su hermano ``diario-despacho.jsonl`` si existe. Lo
  ejecuta ``reflejar-desenlace.yml`` en la rama del motor.

Códigos de salida: 0 hecho; 1 la comprobación encontró la vista desactualizada;
2 argumentos o ficheros que no valen.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from sirius_engine.memoria import (
    COMANDO,
    FICHERO_DESENLACES,
    FICHERO_MEMORIA,
    comprobar_memoria,
    escribir_desenlaces,
    escribir_memoria,
)


def _raiz_por_defecto() -> Path:
    """La raíz del repositorio: el directorio actual, que es desde donde se llama `uv run`."""
    return Path.cwd()


def _diario_de_despacho(diario: Path) -> Path:
    """Misma regla que los demás puntos de entrada (ADR-064): hermano `-despacho.jsonl`."""
    return diario.with_name(f"{diario.stem}-despacho.jsonl")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=COMANDO, description=__doc__.split("\n\n")[0])
    subcomandos = parser.add_subparsers(dest="vista", required=True)

    conocimiento = subcomandos.add_parser(
        "conocimiento", help=f"escribir {FICHERO_MEMORIA} en la raíz a partir del árbol"
    )
    conocimiento.add_argument(
        "--raiz",
        type=Path,
        default=None,
        help="raíz del repositorio (por defecto, el directorio actual)",
    )
    conocimiento.add_argument(
        "--comprobar",
        action="store_true",
        help="no escribir: salir con 1 si el fichero confirmado está desactualizado",
    )

    desenlaces = subcomandos.add_parser(
        "desenlaces", help=f"escribir {FICHERO_DESENLACES} a partir del diario del motor"
    )
    desenlaces.add_argument("--diario", type=Path, required=True, help="ruta de diario.jsonl")
    desenlaces.add_argument(
        "--salida",
        type=Path,
        default=None,
        help=f"dónde escribir (por defecto, {FICHERO_DESENLACES} junto al diario)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    if argumentos.vista == "conocimiento":
        raiz: Path = argumentos.raiz or _raiz_por_defecto()
        if not (raiz / "docs" / "decisions").is_dir():
            print(f"{COMANDO}: {raiz} no parece la raíz del repositorio.", file=sys.stderr)
            return 2
        if argumentos.comprobar:
            problema = comprobar_memoria(raiz)
            if problema is None:
                print(f"{FICHERO_MEMORIA} está al día.")
                return 0
            print(f"{COMANDO}: {problema}", file=sys.stderr)
            return 1
        fichero = escribir_memoria(raiz)
        print(f"Escrito {fichero}.")
        return 0

    diario: Path = argumentos.diario
    if not diario.is_file():
        print(f"{COMANDO}: no existe el diario {diario}.", file=sys.stderr)
        return 2
    despacho = _diario_de_despacho(diario)
    salida: Path = argumentos.salida or diario.with_name(FICHERO_DESENLACES)
    try:
        escribir_desenlaces(diario, salida, despacho if despacho.is_file() else None)
    except ValueError as error:
        print(f"{COMANDO}: {error}", file=sys.stderr)
        return 2
    print(f"Escrito {salida}.")
    return 0


if __name__ == "__main__":  # pragma: no cover - entrada manual
    sys.exit(main())
