#!/usr/bin/env python3
"""¿Está retirado este carril? Lector del registro para los workflows (ADR-162).

Misma fuente de verdad que el despachador —
``docs/implementation/work_engine/carriles_retirados.json``— y misma redacción de
la explicación, para que el mensaje que ve quien aplica una etiqueta y el que ve
quien teclea `sirius-despachar` no puedan divergir.

Corre con el ``python3`` a secas del runner: **solo biblioteca estándar**. Por eso
el registro es JSON y no YAML, y por eso este guion no importa ``sirius_engine``
—el runner no tiene el proyecto instalado— sino que carga el módulo del motor por
ruta de fichero, igual que ``resolver_prompt.py`` y ``sirius_convergence.py``. Así
la explicación vive en UN solo sitio.

Uso:

    python3 scripts/automation/sirius_carril_retirado.py investigacion

Salida: código 0 si el carril está retirado —y escribe la explicación en la
salida estándar—, código 1 si sigue activo. Es la convención de un `if` de shell.
Ante cualquier problema de lectura sale con código 2 y **no** afirma nada: un
registro ilegible no es «el carril está activo», y confundirlos dejaría pasar
trabajo por un carril retirado (fail-closed en la afirmación, no en el flujo).
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_RAIZ = Path(__file__).resolve().parents[2]
_MODULO = _RAIZ / "src" / "sirius_engine" / "carriles_retirados.py"


def _cargar_modulo() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sirius_carriles_retirados", _MODULO)
    if spec is None or spec.loader is None:  # pragma: no cover - defensivo
        raise ImportError(f"No se pudo cargar {_MODULO}")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clase", help="La clase del carril: «investigacion» o «auditoria».")
    parser.add_argument(
        "--registro",
        default=None,
        help="Ruta alternativa del registro (solo para pruebas).",
    )
    args = parser.parse_args(argv)

    try:
        modulo = _cargar_modulo()
        registro = Path(args.registro) if args.registro else None
        carriles = modulo.carriles_retirados(registro=registro)
    except Exception as error:  # cualquier fallo de lectura para aquí, no se afirma nada
        print(f"No se pudo leer el registro de carriles retirados: {error}", file=sys.stderr)
        return 2

    entrada = carriles.get(args.clase)
    if entrada is None:
        return 1
    print(entrada.explicacion())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
