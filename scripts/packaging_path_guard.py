"""Guarda canónica de la ruta del entorno de empaquetado de B13.

El módulo usa semántica de rutas Windows incluso cuando las pruebas se ejecutan
en Linux. Es el mismo código que invoca ``build_windows.ps1`` antes de cualquier
sincronización o creación del entorno.
"""

from __future__ import annotations

import json
import ntpath
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass

_DEVICE_NAMESPACE_PREFIXES = ("\\\\?\\", "\\\\.\\", "\\??\\")
PathResolver = Callable[[str], str]


class PackagingPathError(ValueError):
    """La ruta propuesta no puede usarse como entorno de empaquetado."""


@dataclass(frozen=True, slots=True)
class PackagingPathValidation:
    """Rutas canónicas aceptadas por la guarda."""

    repo_root: str
    packaging_path: str
    ok: bool = True


def canonical_windows_path(value: str) -> str:
    """Normaliza una ruta absoluta con reglas de Windows."""

    raw = value.strip()
    if not raw:
        raise PackagingPathError("la ruta no puede estar vacia")

    windows_raw = raw.replace("/", "\\")
    if windows_raw.startswith(_DEVICE_NAMESPACE_PREFIXES):
        raise PackagingPathError(
            "no se permiten rutas de espacio de nombres extendido o de dispositivo"
        )

    normalized = ntpath.normcase(ntpath.normpath(windows_raw))
    if not ntpath.isabs(normalized):
        raise PackagingPathError(f"la ruta debe ser absoluta: {value!r}")

    drive, tail = ntpath.splitdrive(normalized)
    if not drive or not tail.startswith("\\"):
        raise PackagingPathError(f"la ruta no tiene una raiz Windows valida: {value!r}")

    if tail != "\\":
        normalized = normalized.rstrip("\\")
    return normalized


def _strip_runtime_extended_prefix(value: str) -> str:
    """Convierte el prefijo interno que puede devolver Windows a una ruta normal."""

    upper = value.upper()
    if upper.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if upper.startswith("\\\\?\\"):
        return value[4:]
    return value


def _resolve_existing_windows_components(path: str) -> str:
    """Resuelve junctions, enlaces y nombres 8.3 sin crear ninguna ruta.

    El destino completo puede no existir todavía. Se localiza el ancestro más
    profundo que sí existe, se resuelve mediante la implementación nativa de
    ``realpath`` de Windows y se vuelven a añadir los componentes pendientes.
    """

    if sys.platform != "win32":
        return path

    current = path
    missing_tail: list[str] = []
    while True:
        try:
            _ = os.lstat(current)
            break
        except FileNotFoundError:
            parent, leaf = ntpath.split(current)
            if not leaf or parent == current:
                raise PackagingPathError(
                    f"no existe ningun ancestro resoluble para la ruta: {path}"
                )
            missing_tail.append(leaf)
            current = parent
        except OSError as exc:
            raise PackagingPathError(
                f"no se pudo inspeccionar de forma segura la identidad de: {path}"
            ) from exc

    try:
        resolved = os.path.realpath(current, strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PackagingPathError(
            f"no se pudo resolver de forma segura la identidad de: {path}"
        ) from exc

    if not resolved:
        raise PackagingPathError(
            f"no se pudo resolver de forma segura la identidad de: {path}"
        )

    resolved = _strip_runtime_extended_prefix(resolved)
    for component in reversed(missing_tail):
        resolved = ntpath.join(resolved, component)
    return resolved


def resolved_windows_path(value: str, *, resolver: PathResolver | None = None) -> str:
    """Normaliza y resuelve la identidad física de los componentes existentes."""

    canonical = canonical_windows_path(value)
    selected_resolver = (
        _resolve_existing_windows_components if resolver is None else resolver
    )
    try:
        resolved = selected_resolver(canonical)
    except PackagingPathError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise PackagingPathError(
            f"no se pudo resolver de forma segura la identidad de: {canonical}"
        ) from exc

    if not resolved:
        raise PackagingPathError(
            f"no se pudo resolver de forma segura la identidad de: {canonical}"
        )
    return canonical_windows_path(_strip_runtime_extended_prefix(resolved))


def validate_packaging_path(
    repo_root: str,
    packaging_path: str,
    *,
    resolver: PathResolver | None = None,
) -> PackagingPathValidation:
    """Rechaza el checkout y cualquiera de sus descendientes físicos.

    Una ruta hermana con prefijo textual común es válida. Una ruta ordinaria de
    otra unidad también es válida porque no puede ser descendiente del checkout.
    Cualquier ambigüedad al resolver o comparar se rechaza.
    """

    resolved_repo = resolved_windows_path(repo_root, resolver=resolver)
    resolved_packaging = resolved_windows_path(packaging_path, resolver=resolver)

    repo_drive, _ = ntpath.splitdrive(resolved_repo)
    packaging_drive, _ = ntpath.splitdrive(resolved_packaging)
    if repo_drive != packaging_drive:
        return PackagingPathValidation(
            repo_root=resolved_repo,
            packaging_path=resolved_packaging,
        )

    try:
        common = ntpath.commonpath((resolved_repo, resolved_packaging))
    except ValueError as exc:
        raise PackagingPathError(
            "las rutas no se pueden comparar de forma segura; se rechaza el entorno"
        ) from exc

    if common == resolved_repo:
        if resolved_packaging == resolved_repo:
            detail = "coincide con el checkout"
        else:
            detail = "esta dentro del checkout"
        raise PackagingPathError(
            f"{resolved_packaging} {detail}; el entorno debe vivir fuera del repositorio"
        )

    return PackagingPathValidation(
        repo_root=resolved_repo,
        packaging_path=resolved_packaging,
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
