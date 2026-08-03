"""Guarda canónica de la ruta del entorno de empaquetado de B13.

El módulo usa semántica de rutas Windows incluso cuando las pruebas se ejecutan
en Linux. Es el mismo código que invoca ``build_windows.ps1`` antes de cualquier
sincronización o creación del entorno.
"""

from __future__ import annotations

import json
import ntpath
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass


class PackagingPathError(ValueError):
    """La ruta propuesta no puede usarse como entorno de empaquetado."""


@dataclass(frozen=True, slots=True)
class PackagingPathValidation:
    """Rutas canónicas aceptadas por la guarda."""

    repo_root: str
    packaging_path: str
    ok: bool = True


def canonical_windows_path(value: str) -> str:
    """Normaliza una ruta absoluta con reglas de Windows y sin tocar el disco."""

    raw = value.strip()
    if not raw:
        raise PackagingPathError("la ruta no puede estar vacia")

    normalized = ntpath.normcase(ntpath.normpath(raw.replace("/", "\\")))
    if not ntpath.isabs(normalized):
        raise PackagingPathError(f"la ruta debe ser absoluta: {value!r}")

    drive, tail = ntpath.splitdrive(normalized)
    if not drive or not tail.startswith("\\"):
        raise PackagingPathError(f"la ruta no tiene una raiz Windows valida: {value!r}")

    if tail != "\\":
        normalized = normalized.rstrip("\\")
    return normalized


def validate_packaging_path(repo_root: str, packaging_path: str) -> PackagingPathValidation:
    """Rechaza el checkout y cualquiera de sus descendientes.

    Una ruta hermana con prefijo textual común es válida. Una ruta de otra unidad
    también es válida porque no puede ser descendiente del checkout.
    """

    canonical_repo = canonical_windows_path(repo_root)
    canonical_packaging = canonical_windows_path(packaging_path)

    try:
        common = ntpath.commonpath((canonical_repo, canonical_packaging))
    except ValueError:
        common = ""

    if common == canonical_repo:
        if canonical_packaging == canonical_repo:
            detail = "coincide con el checkout"
        else:
            detail = "esta dentro del checkout"
        raise PackagingPathError(
            f"{canonical_packaging} {detail}; el entorno debe vivir fuera del repositorio"
        )

    return PackagingPathValidation(
        repo_root=canonical_repo,
        packaging_path=canonical_packaging,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Emite JSON estable para que PowerShell pueda aplicar la precondición."""

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print(json.dumps({"ok": False, "error": "uso: <repo_root> <packaging_path>"}))
        return 2

    try:
        result = validate_packaging_path(args[0], args[1])
    except PackagingPathError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2

    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
