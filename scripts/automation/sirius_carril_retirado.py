#!/usr/bin/env python3
"""¿Está retirado este carril? Lector del registro para los workflows (ADR-163).

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

**Solo esos tres códigos significan algo, y quien llama debe tratarlos así**
(ADR-167): `0` retirado, `1` activo, y **cualquier otro valor** —126 o 127 si el
intérprete o este guion no están donde se espera, una señal, un fallo del propio
`python3`— es un «no lo sé» que obliga a detenerse sin ejecutar el carril. Las
dos puertas que lo llaman lo hacen con un `case`, no con un `if ... -ne 0`, justo
por esto.

Además de `--registro`, admite la variable de entorno
``SIRIUS_CARRILES_RETIRADOS`` con la misma función: es la única forma de que una
prueba ejecute el guion real de un paso de workflow —que no pasa `--registro`—
contra un registro controlado, sin tocar el registro de verdad.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
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

    # `SIRIUS_CARRILES_RETIRADOS` es la MISMA vía por variable de entorno, y
    # existe para que las pruebas puedan ejecutar el guion REAL de los pasos de
    # los workflows -que no llevan `--registro`- contra registros controlados,
    # sin tocar el registro de verdad. No concede autoridad nueva: ponerla exige
    # editar el workflow, que es exactamente el permiso que ya haría falta para
    # editar el registro. Y no debilita el fail-closed: si apunta a algo
    # ilegible, esto sale con 2 como cualquier otro fallo de lectura.
    ruta = args.registro or os.environ.get("SIRIUS_CARRILES_RETIRADOS") or None

    try:
        modulo = _cargar_modulo()
        registro = Path(ruta) if ruta else None
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
