"""Validacion confinada de ``FILE-MANIFEST.sha256`` para B13.

El verificador de Windows consume este modulo antes de combinar una ruta
declarada por el manifiesto con la raiz del paquete. Las rutas se juzgan con
semantica Windows mediante :mod:`ntpath`, incluso cuando las regresiones se
ejecutan en Ubuntu.
"""

from __future__ import annotations

import json
import ntpath
import re
import sys
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ManifestEntry",
    "ManifestValidationError",
    "main",
    "validate_manifest",
    "validate_manifest_lines",
]

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class ManifestValidationError(ValueError):
    """El manifiesto contiene una entrada que no puede usarse con seguridad."""


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """Entrada normalizada y confinada del inventario de archivos."""

    sha256: str
    path: str

    def as_dict(self) -> dict[str, str]:
        return {"sha256": self.sha256, "path": self.path}


def _normalize_relative_path(raw_path: str, *, package_root: str, line_number: int) -> str:
    path = raw_path.strip()
    if not path:
        raise ManifestValidationError(f"linea {line_number}: ruta vacia")

    normalized = path.replace("\\", "/")
    drive, _ = ntpath.splitdrive(path)
    if normalized.startswith("/") or drive or ntpath.isabs(path):
        raise ManifestValidationError(
            f"linea {line_number}: ruta absoluta, UNC o con unidad: {path}"
        )

    segments = normalized.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ManifestValidationError(
            f"linea {line_number}: segmento vacio, '.' o '..' no permitido: {path}"
        )

    root = ntpath.normpath(package_root)
    boundary = root.rstrip("\\/") + "\\"
    destination = ntpath.normpath(ntpath.join(root, *segments))
    if not destination.casefold().startswith(boundary.casefold()):
        raise ManifestValidationError(
            f"linea {line_number}: la ruta escaparia de la raiz del paquete: {path}"
        )

    return "/".join(segments)


def validate_manifest_lines(lines: list[str], *, package_root: str) -> tuple[ManifestEntry, ...]:
    """Valida y normaliza todas las entradas antes de tocar sus destinos."""

    entries: list[ManifestEntry] = []
    seen: set[str] = set()

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\r\n")
        if not line.strip():
            raise ManifestValidationError(f"linea {line_number}: entrada vacia")

        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ManifestValidationError(
                f"linea {line_number}: se esperaba '<sha256>  <ruta>'"
            )
        digest, raw_path = parts
        if not _SHA256_RE.fullmatch(digest):
            raise ManifestValidationError(f"linea {line_number}: SHA-256 no valido")

        normalized = _normalize_relative_path(
            raw_path,
            package_root=package_root,
            line_number=line_number,
        )
        key = normalized.casefold()
        if key in seen:
            raise ManifestValidationError(
                f"linea {line_number}: destino duplicado normalizado: {normalized}"
            )
        seen.add(key)
        entries.append(ManifestEntry(sha256=digest.lower(), path=normalized))

    if not entries:
        raise ManifestValidationError("el manifiesto no contiene archivos")
    return tuple(entries)


def validate_manifest(manifest_path: str, *, package_root: str) -> tuple[ManifestEntry, ...]:
    """Lee un manifiesto UTF-8 y devuelve solo entradas ya confinadas."""

    text = Path(manifest_path).read_text(encoding="utf-8")
    return validate_manifest_lines(text.splitlines(), package_root=package_root)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("uso: file_manifest.py <FILE-MANIFEST.sha256> <raiz-del-paquete>", file=sys.stderr)
        return 2

    try:
        entries = validate_manifest(argv[1], package_root=argv[2])
    except (OSError, UnicodeError, ManifestValidationError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    print(
        json.dumps(
            {"ok": True, "entries": [entry.as_dict() for entry in entries]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
