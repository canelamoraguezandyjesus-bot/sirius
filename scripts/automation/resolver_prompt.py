"""Resolver el prompt EXACTO que corresponde a ``Perfil: rol@N`` (H-28, #396).

El defecto que corrige: los workflows extraían el rol tirando la versión y
leían el prompt vigente de main, así que ``implementer@1`` podía significar
dos textos distintos en dos Runs. Aquí la versión gobierna: el manifiesto
(``scripts/automation/prompts/manifiesto.json``) dice qué fichero es cada
``rol@N`` y con qué sha256, y este módulo NO entrega nada que no pueda
afirmar — clave desconocida, campo ausente o texto que ya no coincide con la
versión declarada paran en rojo (fail-closed), porque ejecutar el prompt
equivocado produce trabajo que parece hecho y no lo está.

Corre con el ``python3`` a secas del runner (solo stdlib, ver
``test_sirius_runner_python_compat.py``). El campo ``Perfil:`` lo parsea
``sirius_engine.profile_field`` cargado por ruta de fichero —una sola verdad,
mismo mecanismo que ``sirius_convergence.py`` usa desde H-13—, no una copia
del regex que pudiera divergir.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

_RAIZ_POR_DEFECTO = Path(__file__).resolve().parents[2]
_MANIFIESTO_RELATIVO = Path("scripts/automation/prompts/manifiesto.json")
_PROFILE_FIELD = _RAIZ_POR_DEFECTO / "src" / "sirius_engine" / "profile_field.py"


def _cargar_profile_field() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sirius_profile_field", _PROFILE_FIELD)
    if spec is None or spec.loader is None:  # pragma: no cover - defensivo
        raise ImportError(f"No se pudo cargar el módulo compartido en {_PROFILE_FIELD}")
    modulo = importlib.util.module_from_spec(spec)
    # Registrado ANTES de ejecutar: `@dataclass(slots=True)` reconstruye la
    # clase y busca su módulo en `sys.modules`; sin esto revienta al cargar.
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


parse_perfil_field = _cargar_profile_field().parse_perfil_field


class ResolucionImposible(Exception):
    """No se puede afirmar qué texto corresponde: se para, no se adivina."""


def resolver_prompt(cuerpo: str, *, carril: str, raiz: Path) -> Path:
    """La ruta (relativa a ``raiz``) del prompt que el manifiesto fija para
    el ``Perfil: rol@N`` declarado en ``cuerpo``, verificada byte a byte."""
    perfil = parse_perfil_field(cuerpo)
    if perfil is None:
        raise ResolucionImposible(
            "el cuerpo no declara 'Perfil: rol@N' y sin él no se puede elegir prompt"
        )
    clave = f"{perfil.ref}@{perfil.version}"
    manifiesto = json.loads((raiz / _MANIFIESTO_RELATIVO).read_text(encoding="utf-8"))
    filas = manifiesto["carriles"].get(carril)
    if filas is None:
        raise ResolucionImposible(f"carril desconocido: '{carril}'")
    fila = filas.get(clave)
    if fila is None:
        conocidas = ", ".join(sorted(filas))
        raise ResolucionImposible(
            f"'{clave}' no está en el manifiesto (carril {carril}; conocidas: {conocidas}). "
            "Si es una versión nueva, regístrala en manifiesto.json con su sha256."
        )
    fichero = raiz / fila["fichero"]
    if not fichero.is_file():
        raise ResolucionImposible(f"{clave}: el fichero {fila['fichero']} no existe")
    real = hashlib.sha256(fichero.read_bytes()).hexdigest()
    if real != fila["sha256"]:
        raise ResolucionImposible(
            f"{clave}: el texto de {fila['fichero']} ya no es el de la versión "
            f"registrada (sha256 {real[:12]}… ≠ {fila['sha256'][:12]}…). Registra "
            "una versión nueva en el manifiesto y sube la versión del perfil, o "
            "restaura el texto; una versión publicada no se edita."
        )
    return Path(fila["fichero"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carril", required=True, choices=("ejecucion", "revision"))
    args = parser.parse_args(argv)
    cuerpo = os.environ.get("ISSUE_BODY")
    if cuerpo is None:
        print("::error::falta la variable de entorno ISSUE_BODY", file=sys.stderr)
        return 1
    try:
        ruta = resolver_prompt(cuerpo, carril=args.carril, raiz=_RAIZ_POR_DEFECTO)
    except ResolucionImposible as exc:
        print(f"::error::prompt sin resolver ({args.carril}): {exc}", file=sys.stderr)
        return 1
    print(ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
