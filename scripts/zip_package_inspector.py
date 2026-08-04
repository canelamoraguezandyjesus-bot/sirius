"""Inspección y extracción acotada del ZIP de B13.

La misma implementación que usa ``verify_windows_package.ps1`` queda cubierta
por ``tests/unit/test_zip_package_inspector.py``. Las rutas se juzgan con
semántica Windows mediante ``ntpath`` aunque las pruebas se ejecuten en Ubuntu.
Además de impedir zip-slip, el módulo limita tamaños declarados, expansión total
y ratio de compresión antes de extraer, y vuelve a imponer los límites mientras
copia cada archivo.

Uso desde PowerShell::

    python scripts/zip_package_inspector.py <zip> <raiz-de-extraccion>
    python scripts/zip_package_inspector.py extract <zip> <raiz-de-extraccion>
"""

from __future__ import annotations

import json
import ntpath
import shutil
import sys
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

__all__ = [
    "DEFAULT_LIMITS",
    "ExtractionResult",
    "ZipInspection",
    "ZipLimits",
    "ZipSafetyError",
    "copy_bounded",
    "inspect_entry_names",
    "inspect_zip",
    "main",
    "safe_extract_zip",
]

_MIB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ZipLimits:
    """Límites conservadores para un paquete standalone de Sirius."""

    max_entry_uncompressed_bytes: int = 512 * _MIB
    max_total_uncompressed_bytes: int = 2 * 1024 * _MIB
    max_compression_ratio: float = 200.0
    copy_chunk_bytes: int = _MIB


DEFAULT_LIMITS = ZipLimits()


class ZipSafetyError(ValueError):
    """El ZIP no puede inspeccionarse o extraerse de forma segura."""


@dataclass(frozen=True, slots=True)
class ZipInspection:
    """Información necesaria para decidir si el ZIP puede extraerse."""

    roots: tuple[str, ...]
    unsafe: tuple[str, ...]
    file_count: int
    total_uncompressed_bytes: int = 0
    max_entry_uncompressed_bytes: int = 0
    max_compression_ratio: float = 0.0
    size_violations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "roots": list(self.roots),
            "unsafe": list(self.unsafe),
            "file_count": self.file_count,
            "total_uncompressed_bytes": self.total_uncompressed_bytes,
            "max_entry_uncompressed_bytes": self.max_entry_uncompressed_bytes,
            "max_compression_ratio": self.max_compression_ratio,
            "size_violations": list(self.size_violations),
        }


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Resultado verificable de la extracción controlada."""

    file_count: int
    total_uncompressed_bytes: int
    ok: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "file_count": self.file_count,
            "total_uncompressed_bytes": self.total_uncompressed_bytes,
        }


def _is_directory_entry(name: str) -> bool:
    return name.endswith("/") or name.endswith("\\")


def _segments(original_name: str) -> list[str]:
    normalized = original_name.replace("\\", "/")
    return [segment for segment in normalized.split("/") if segment != ""]


def _normalized_entry_key(original_name: str) -> str:
    return "/".join(_segments(original_name)).casefold()


def _compression_ratio(info: zipfile.ZipInfo, limits: ZipLimits) -> float:
    if info.file_size == 0:
        return 0.0
    if info.compress_size <= 0:
        return limits.max_compression_ratio + 1.0
    return info.file_size / info.compress_size


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    unix_mode = (info.external_attr >> 16) & 0o170000
    return unix_mode == 0o120000


def inspect_entry_names(entry_names: Iterable[str], *, extract_root: str) -> ZipInspection:
    """Analiza nombres de entrada sin tocar el disco."""

    boundary = ntpath.normpath(extract_root).rstrip("\\") + "\\"
    roots: set[str] = set()
    unsafe: list[str] = []
    file_count = 0

    for original_name in entry_names:
        normalized = original_name.replace("\\", "/")
        if (
            normalized.startswith("/")
            or ntpath.isabs(original_name)
            or ntpath.splitdrive(original_name)[0] != ""
        ):
            unsafe.append(f"ruta absoluta o con unidad: {original_name}")
            continue

        segments = _segments(original_name)
        if not segments:
            continue
        if ".." in segments:
            unsafe.append(f"segmento '..': {original_name}")
            continue

        destination = ntpath.normpath(ntpath.join(extract_root, "\\".join(segments)))
        if not destination.casefold().startswith(boundary.casefold()):
            unsafe.append(f"escaparia de la carpeta de extraccion: {original_name}")
            continue

        roots.add(segments[0])
        if not _is_directory_entry(original_name):
            file_count += 1

    return ZipInspection(
        roots=tuple(sorted(roots)),
        unsafe=tuple(unsafe),
        file_count=file_count,
    )


def inspect_zip(
    zip_path: str,
    *,
    extract_root: str,
    limits: ZipLimits = DEFAULT_LIMITS,
) -> ZipInspection:
    """Inspecciona nombres y expansión declarada antes de extraer."""

    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        names = inspect_entry_names((info.filename for info in infos), extract_root=extract_root)
        unsafe = list(names.unsafe)
        size_violations: list[str] = []
        seen_destinations: set[str] = set()
        total_uncompressed = 0
        max_entry = 0
        max_ratio = 0.0

        for info in infos:
            if info.is_dir() or _is_directory_entry(info.filename):
                continue

            key = _normalized_entry_key(info.filename)
            if key in seen_destinations:
                unsafe.append(f"destino duplicado: {info.filename}")
            seen_destinations.add(key)

            if _is_symlink(info):
                unsafe.append(f"enlace simbolico no permitido: {info.filename}")

            total_uncompressed += info.file_size
            max_entry = max(max_entry, info.file_size)
            ratio = _compression_ratio(info, limits)
            max_ratio = max(max_ratio, ratio)

            if info.file_size > limits.max_entry_uncompressed_bytes:
                size_violations.append(
                    f"entrada demasiado grande ({info.file_size} bytes): {info.filename}"
                )
            if ratio > limits.max_compression_ratio:
                size_violations.append(
                    f"ratio de compresion excesivo ({ratio:.1f}): {info.filename}"
                )

        if total_uncompressed > limits.max_total_uncompressed_bytes:
            size_violations.append(
                "tamano total expandido excesivo "
                f"({total_uncompressed} bytes; limite {limits.max_total_uncompressed_bytes})"
            )

        return ZipInspection(
            roots=names.roots,
            unsafe=tuple(unsafe),
            file_count=names.file_count,
            total_uncompressed_bytes=total_uncompressed,
            max_entry_uncompressed_bytes=max_entry,
            max_compression_ratio=max_ratio,
            size_violations=tuple(size_violations),
        )


def copy_bounded(
    source: BinaryIO,
    target: BinaryIO,
    *,
    expected_bytes: int,
    total_before: int,
    limits: ZipLimits = DEFAULT_LIMITS,
) -> int:
    """Copia una entrada imponiendo límites sobre los bytes realmente escritos."""

    entry_bytes = 0
    while True:
        chunk = source.read(limits.copy_chunk_bytes)
        if not chunk:
            break
        entry_bytes += len(chunk)
        if entry_bytes > expected_bytes:
            raise ZipSafetyError("la entrada expandio mas bytes de los declarados")
        if entry_bytes > limits.max_entry_uncompressed_bytes:
            raise ZipSafetyError("la entrada supero el limite individual durante la extraccion")
        if total_before + entry_bytes > limits.max_total_uncompressed_bytes:
            raise ZipSafetyError("el ZIP supero el limite acumulado durante la extraccion")
        target.write(chunk)

    if entry_bytes != expected_bytes:
        raise ZipSafetyError(
            f"tamano extraido inesperado: declarado {expected_bytes}, real {entry_bytes}"
        )
    return entry_bytes


def safe_extract_zip(
    zip_path: str,
    *,
    extract_root: str,
    limits: ZipLimits = DEFAULT_LIMITS,
) -> ExtractionResult:
    """Extrae el ZIP sin permitir escapes, sobreescrituras ni expansión excesiva."""

    inspection = inspect_zip(zip_path, extract_root=extract_root, limits=limits)
    problems = (*inspection.unsafe, *inspection.size_violations)
    if problems:
        raise ZipSafetyError("; ".join(problems))

    root = Path(extract_root)
    if root.exists() and any(root.iterdir()):
        raise ZipSafetyError("la raiz de extraccion no esta vacia")
    root.mkdir(parents=True, exist_ok=True)

    total_written = 0
    files_written = 0
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                segments = _segments(info.filename)
                if not segments:
                    continue
                destination = root.joinpath(*segments)
                if info.is_dir() or _is_directory_entry(info.filename):
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise ZipSafetyError(f"destino duplicado durante extraccion: {info.filename}")
                with archive.open(info, "r") as source, destination.open("xb") as target:
                    written = copy_bounded(
                        source,
                        target,
                        expected_bytes=info.file_size,
                        total_before=total_written,
                        limits=limits,
                    )
                total_written += written
                files_written += 1
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise

    return ExtractionResult(
        file_count=files_written,
        total_uncompressed_bytes=total_written,
    )


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 3:
            inspection = inspect_zip(argv[1], extract_root=argv[2])
            print(json.dumps(inspection.as_dict()))
            return 0
        if len(argv) == 4 and argv[1] == "extract":
            result = safe_extract_zip(argv[2], extract_root=argv[3])
            print(json.dumps(result.as_dict()))
            return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2

    print(
        "uso: zip_package_inspector.py [extract] <ruta-del-zip> <raiz-de-extraccion>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
