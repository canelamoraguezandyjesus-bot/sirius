"""Selección y procedencia del artefacto de B13.

Existe porque el verificador acreditó un artefacto que no correspondía al commit
del repositorio. Las dos construcciones de ``f9b68d5`` fallaron, no dejaron
artefacto, y el verificador —que tomaba «el ZIP más reciente» de
``dist/windows``— encontró el ``Sirius-0.1.0.dev0-a82972f-windows-x64.zip`` de
una ronda anterior, lo validó y terminó como SUPERADA CON RESERVAS. Es decir:
produjo evidencia de un commit distinto del que estaba en HEAD, justo después de
un fallo de compilación. Una verificación de B13 no puede acreditar el artefacto
de otro commit.

Aquí se decide qué ZIP es el legítimo y si su procedencia cuadra. La lógica vive
en Python, y no dentro del ``.ps1``, para que la cubran pruebas: el verificador
invoca este módulo y consume su JSON, de modo que lo que se prueba es lo que se
ejecuta.

Uso desde PowerShell::

    python scripts/package_provenance.py select <dist-dir> <version> <sha-corto>
    python scripts/package_provenance.py verify <manifiesto> <commit> <sha-corto>
"""

from __future__ import annotations

import json
import ntpath
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

__all__ = [
    "ProvenanceResult",
    "SelectionResult",
    "artifact_name",
    "check_provenance",
    "main",
    "select_artifact",
]


def artifact_name(version: str, commit_short: str) -> str:
    """El único nombre de artefacto admisible para esta versión y este commit.

    Debe coincidir exactamente con el que compone ``build_windows.ps1``.
    """
    return f"Sirius-{version}-{commit_short}-windows-x64"


@dataclass(frozen=True)
class SelectionResult:
    """Qué ZIP hay que verificar, o por qué no hay ninguno."""

    expected_name: str
    zip_path: str | None
    error: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "expected_name": self.expected_name,
            "zip_path": self.zip_path,
            "error": self.error,
        }


@dataclass(frozen=True)
class ProvenanceResult:
    """Si el manifiesto del artefacto corresponde al commit actual."""

    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "errors": list(self.errors)}


def select_artifact(
    distribution_directory: str,
    version: str,
    commit_short: str,
    *,
    existing_names: list[str] | None = None,
) -> SelectionResult:
    """Elige el ZIP por nombre exacto, nunca «el más reciente».

    ``existing_names`` permite probar la decisión sin tocar el disco; cuando no
    se pasa, se lee el directorio.
    """
    expected = artifact_name(version, commit_short)
    expected_zip = expected + ".zip"

    if existing_names is None:
        import os

        try:
            names = os.listdir(distribution_directory)
        except OSError:
            return SelectionResult(
                expected_name=expected,
                zip_path=None,
                error=(
                    f"No existe {distribution_directory}. No hay ningun artefacto construido "
                    f"desde el HEAD actual ({commit_short}). Ejecuta antes build_windows.ps1."
                ),
            )
    else:
        names = list(existing_names)

    if expected_zip in names:
        return SelectionResult(
            expected_name=expected,
            zip_path=ntpath.join(distribution_directory, expected_zip),
            error=None,
        )

    # No está. Se nombran los que sí hay, porque el caso real es tener el ZIP de
    # otro commit al lado y conviene decir por qué no sirve.
    others = sorted(
        name for name in names if name.startswith("Sirius-") and name.endswith("-windows-x64.zip")
    )
    detail = ""
    if others:
        detail = (
            " Hay artefactos de otros commits, que NO acreditan este: " + ", ".join(others) + "."
        )
    return SelectionResult(
        expected_name=expected,
        zip_path=None,
        error=(
            f"No existe {expected_zip}: no hay ningun artefacto construido desde el HEAD "
            f"actual ({commit_short})." + detail + " Ejecuta build_windows.ps1 con el arbol limpio."
        ),
    )


def check_provenance(
    manifest: Mapping[str, Any], commit: str, commit_short: str
) -> ProvenanceResult:
    """Compara el manifiesto del artefacto con el commit del repositorio.

    Se comprueban las dos formas, completa y corta, porque son campos distintos
    del manifiesto y cualquiera de las dos puede quedar obsoleta por separado.
    """
    errors: list[str] = []

    recorded_commit = manifest.get("source_commit")
    if not isinstance(recorded_commit, str) or recorded_commit == "":
        errors.append("El manifiesto no declara source_commit.")
    elif recorded_commit != commit:
        errors.append(
            f"source_commit del manifiesto ({recorded_commit}) no es el HEAD actual ({commit})."
        )

    recorded_short = manifest.get("source_commit_short")
    if not isinstance(recorded_short, str) or recorded_short == "":
        errors.append("El manifiesto no declara source_commit_short.")
    elif recorded_short != commit_short:
        errors.append(
            f"source_commit_short del manifiesto ({recorded_short}) no es el sha corto "
            f"actual ({commit_short})."
        )

    return ProvenanceResult(errors=tuple(errors))


def _load_manifest(path: str) -> Mapping[str, Any]:
    with open(path, encoding="utf-8") as handle:
        loaded: Any = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("El manifiesto no es un objeto JSON.")
    return loaded


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "select" and len(argv) == 5:
        result = select_artifact(argv[2], argv[3], argv[4])
        print(json.dumps(result.as_dict()))
        return 0
    if len(argv) >= 2 and argv[1] == "verify" and len(argv) == 5:
        provenance = check_provenance(_load_manifest(argv[2]), argv[3], argv[4])
        print(json.dumps(provenance.as_dict()))
        return 0
    print(
        "uso: package_provenance.py select <dist-dir> <version> <sha-corto>\n"
        "     package_provenance.py verify <manifiesto> <commit> <sha-corto>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
