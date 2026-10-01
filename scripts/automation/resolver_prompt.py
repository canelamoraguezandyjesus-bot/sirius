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
import re
import sys
from pathlib import Path
from types import ModuleType

_RAIZ_POR_DEFECTO = Path(__file__).resolve().parents[2]
_MANIFIESTO_RELATIVO = Path("scripts/automation/prompts/manifiesto.json")
_PROFILE_FIELD = _RAIZ_POR_DEFECTO / "src" / "sirius_engine" / "profile_field.py"
_PERFILES_RELATIVO = Path("docs/implementation/work_engine/perfiles")
# La linea `version: N` del perfil, leida con la biblioteca estandar: este
# modulo corre con el python3 a secas del runner, sin PyYAML (ADR-221).
_VERSION_DEL_PERFIL = re.compile(r"^version:\s*(\d+)\s*$", re.MULTILINE)


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


def version_vigente(rol: str, *, raiz: Path) -> int | None:
    """La `version:` que declara `docs/implementation/work_engine/perfiles/<rol>.yml`,
    o ``None`` si el perfil no existe o no la declara. No decide nada: informa."""
    fichero = raiz / _PERFILES_RELATIVO / f"{rol}.yml"
    if not fichero.is_file():
        return None
    encontrada = _VERSION_DEL_PERFIL.search(fichero.read_text(encoding="utf-8"))
    return int(encontrada.group(1)) if encontrada else None


def aviso_de_vigencia(cuerpo: str, *, raiz: Path) -> str | None:
    """Una frase si el `Perfil: rol@N` del cuerpo resuelve pero N no es la version
    vigente del rol; ``None`` si es la vigente o no se puede saber.

    No es un rechazo: `rol@N` significa UN texto (H-28) y una version antigua
    sigue siendo ejecutable a proposito. Es el aviso que a #653 le falto: llevaba
    `implementer@2` con la 4 vigente y nadie se lo dijo (ADR-221).
    """
    perfil = parse_perfil_field(cuerpo)
    if perfil is None:
        return None
    vigente = version_vigente(perfil.ref, raiz=raiz)
    if vigente is None or int(perfil.version) == vigente:
        return None
    return (
        f"el cuerpo declara `Perfil: {perfil.ref}@{perfil.version}` y la version vigente de "
        f"`{perfil.ref}` es la {vigente} "
        f"(docs/implementation/work_engine/perfiles/{perfil.ref}.yml). Se ejecuta con la "
        "declarada, porque `rol@N` significa un texto (H-28) y el implementador ejecuta la "
        "instantanea del evento, no el cuerpo actual. Si querias la vigente, cuenta con que al "
        "leer esto el run ya habra consumido la activacion (la incidencia estara en "
        "`sirius:implementing`): deja que termine o cancelalo desde Actions, espera a que la "
        "incidencia quede sin estado activo (si lo cancelas quedara en `sirius:failed-safely`), "
        "edita el cuerpo y activala de nuevo en este orden: retira el estado que haya quedado, "
        "aplica `sirius:planned` y, en ultimo lugar, `sirius:implement-requested`. Retirar y "
        "volver a aplicar la etiqueta mientras el run sigue en marcha no sirve: esta puerta "
        "rechaza una activacion sobre una incidencia con estado activo, y editar el cuerpo sin "
        "reactivar no detiene este run."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carril", required=True, choices=("ejecucion", "revision"))
    parser.add_argument(
        "--vigencia",
        action="store_true",
        help=(
            "ademas de resolver, imprimir en la salida estandar el aviso de version no "
            "vigente (o nada) en vez de la ruta del prompt; el codigo de salida no cambia"
        ),
    )
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
    if args.vigencia:
        aviso = aviso_de_vigencia(cuerpo, raiz=_RAIZ_POR_DEFECTO)
        if aviso:
            print(aviso)
        return 0
    print(ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
