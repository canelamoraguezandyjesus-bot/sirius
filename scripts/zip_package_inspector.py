"""Inspección, congelación y extracción acotada del ZIP de B13.

La misma implementación que usa ``verify_windows_package.ps1`` queda cubierta
por ``tests/unit/test_zip_package_inspector.py``. Las rutas se juzgan con
semántica Windows aunque las pruebas se ejecuten en Ubuntu. Además de impedir
zip-slip y alias Win32, el módulo limita el tamaño del ZIP de origen, el número
de entradas, los tamaños declarados, la expansión total y el ratio de
compresión. Los límites se vuelven a imponer mientras se congelan y extraen los
bytes.

Uso desde PowerShell::

    python scripts/zip_package_inspector.py freeze <zip-origen> <zip-congelado>
    python scripts/zip_package_inspector.py <zip> <raiz-de-extraccion>
    python scripts/zip_package_inspector.py extract <zip> <raiz-de-extraccion>
"""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from windows_path_safety import WindowsPathError, split_safe_windows_relative_path

__all__ = [
    "DEFAULT_LIMITS",
    "ExtractionResult",
    "FrozenCopyResult",
    "ZipInspection",
    "ZipLimits",
    "ZipSafetyError",
    "copy_bounded",
    "freeze_zip",
    "inspect_entry_names",
    "inspect_zip",
    "main",
    "safe_extract_zip",
]

_MIB = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ZipLimits:
    """Límites conservadores para un paquete standalone de Sirius."""

    max_source_bytes: int = 1024 * _MIB
    max_entries: int = 4096
    max_entry_uncompressed_bytes: int = 512 * _MIB
    max_total_uncompressed_bytes: int = 2 * 1024 * _MIB
    max_compression_ratio: float = 200.0
    copy_chunk_bytes: int = _MIB


DEFAULT_LIMITS = ZipLimits()


class ZipSafetyError(ValueError):
    """El ZIP no puede congelarse, inspeccionarse o extraerse de forma segura."""


@dataclass(frozen=True, slots=True)
class FrozenCopyResult:
    """Resultado verificable de la copia privada y acotada del ZIP."""

    bytes_written: int
    ok: bool = True

    def as_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "bytes_written": self.bytes_written}


@dataclass(frozen=True, slots=True)
class ZipInspection:
    """Información necesaria para decidir si el ZIP puede extraerse."""

    roots: tuple[str, ...]
    unsafe: tuple[str, ...]
    file_count: int
    entry_count: int = 0
    total_uncompressed_bytes: int = 0
    max_entry_uncompressed_bytes: int = 0
    max_compression_ratio: float = 0.0
    size_violations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "roots": list(self.roots),
            "unsafe": list(self.unsafe),
            "file_count": self.file_count,
            "entry_count": self.entry_count,
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


def _segments(original_name: str, *, directory_entry: bool) -> tuple[str, ...]:
    return split_safe_windows_relative_path(
        original_name,
        directory_entry=directory_entry,
    )


def _normalized_entry_key(original_name: str, *, directory_entry: bool) -> str:
    return "/".join(
        _segments(original_name, directory_entry=directory_entry)
    ).casefold()


def _compression_ratio(info: zipfile.ZipInfo, limits: ZipLimits) -> float:
    if info.file_size == 0:
        return 0.0
    if info.compress_size <= 0:
        return limits.max_compression_ratio + 1.0
    return info.file_size / info.compress_size


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    unix_mode = (info.external_attr >> 16) & 0o170000
    return unix_mode == 0o120000


def freeze_zip(
    source_path: str,
    *,
    frozen_path: str,
    limits: ZipLimits = DEFAULT_LIMITS,
) -> FrozenCopyResult:
    """Copia el ZIP a una ruta privada sin superar el límite de origen.

    El tamaño se comprueba antes de crear el destino y se vuelve a imponer sobre
    los bytes realmente leídos. Si el origen cambia de longitud durante la
    copia, o cualquier operación falla, la copia parcial se elimina.
    """

    source = Path(source_path)
    target = Path(frozen_path)
    if source.resolve() == target.resolve():
        raise ZipSafetyError("el ZIP de origen y la copia congelada son la misma ruta")
    if target.exists():
        raise ZipSafetyError("la ruta de la copia congelada ya existe")

    expected_bytes = source.stat().st_size
    if expected_bytes > limits.max_source_bytes:
        raise ZipSafetyError(
            "ZIP de origen demasiado grande "
            f"({expected_bytes} bytes; limite {limits.max_source_bytes})"
        )

    bytes_written = 0
    try:
        with source.open("rb") as reader, target.open("xb") as writer:
            while True:
                chunk = reader.read(limits.copy_chunk_bytes)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > limits.max_source_bytes:
                    raise ZipSafetyError(
                        "el ZIP de origen supero el limite durante la copia congelada"
                    )
                writer.write(chunk)

        if bytes_written != expected_bytes:
            raise ZipSafetyError(
                "el ZIP de origen cambio de longitud durante la copia "
                f"(inicial {expected_bytes}, copiado {bytes_written})"
            )
    except Exception:
        target.unlink(missing_ok=True)
        raise

    return FrozenCopyResult(bytes_written=bytes_written)


def inspect_entry_names(entry_names: Iterable[str], *, extract_root: str) -> ZipInspection:
    """Analiza nombres de entrada con semántica Windows sin tocar el disco."""

    del extract_root  # La API conserva el parámetro; las rutas se confinan por componentes.
    roots: set[str] = set()
    unsafe: list[str] = []
    file_count = 0
    entry_count = 0

    for original_name in entry_names:
        entry_count += 1
        directory_entry = _is_directory_entry(original_name)
        try:
            segments = _segments(original_name, directory_entry=directory_entry)
        except WindowsPathError as exc:
            unsafe.append(f"{exc}: {original_name}")
            continue

        roots.add(segments[0])
        if not directory_entry:
            file_count += 1

    return ZipInspection(
        roots=tuple(sorted(roots)),
        unsafe=tuple(unsafe),
        file_count=file_count,
        entry_count=entry_count,
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

        if names.entry_count > limits.max_entries:
            size_violations.append(
                f"demasiadas entradas ({names.entry_count}; limite {limits.max_entries})"
            )

        for info in infos:
            directory_entry = info.is_dir() or _is_directory_entry(info.filename)
            try:
                key = _normalized_entry_key(
                    info.filename,
                    directory_entry=directory_entry,
                )
            except WindowsPathError:
                # inspect_entry_names ya dejó el diagnóstico exacto.
                continue

            if key in seen_destinations:
                unsafe.append(f"destino duplicado: {info.filename}")
            seen_destinations.add(key)

            if _is_symlink(info):
                unsafe.append(f"enlace simbolico no permitido: {info.filename}")
            if directory_entry:
                continue

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
            entry_count=names.entry_count,
            total_uncompressed_bytes=total_uncompressed,
            max_entry_uncompressed_bytes=max_entry,
            max_compression_ratio=max_ratio,
            size_violations=tuple(size_violations),
        )


def copy_bounded(
    source: IO[bytes],
    target: IO[bytes],
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
    """Extrae el ZIP sin permitir escapes, alias ni expansión excesiva."""

    inspection = inspect_zip(zip_path, extract_root=extract_root, limits=limits)
    problems = (*inspection.unsafe, *inspection.size_violations)
    if problems:
        raise ZipSafetyError("; ".join(problems))

    root = Path(extract_root)
    if root.exists() and any(root.iterdir()):
        raise ZipSafetyError("la raiz de extraccion no esta vacia")

    total_written = 0
    files_written = 0
    try:
        with zipfile.ZipFile(zip_path) as archive:
            infos = archive.infolist()
            if len(infos) > limits.max_entries:
                raise ZipSafetyError(
                    f"demasiadas entradas ({len(infos)}; limite {limits.max_entries})"
                )

            root.mkdir(parents=True, exist_ok=True)
            for info in infos:
                directory_entry = info.is_dir() or _is_directory_entry(info.filename)
                try:
                    segments = _segments(
                        info.filename,
                        directory_entry=directory_entry,
                    )
                except WindowsPathError as exc:
                    raise ZipSafetyError(
                        f"entrada insegura: {info.filename}: {exc}"
                    ) from exc

                destination = root.joinpath(*segments)
                if directory_entry:
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise ZipSafetyError(
                        f"destino duplicado durante extraccion: {info.filename}"
                    )
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
        if len(argv) == 4 and argv[1] == "freeze":
            frozen_result = freeze_zip(argv[2], frozen_path=argv[3])
            print(json.dumps(frozen_result.as_dict()))
            return 0
        if len(argv) == 3:
            inspection = inspect_zip(argv[1], extract_root=argv[2])
            print(json.dumps(inspection.as_dict()))
            return 0
        if len(argv) == 4 and argv[1] == "extract":
            extraction_result = safe_extract_zip(argv[2], extract_root=argv[3])
            print(json.dumps(extraction_result.as_dict()))
            return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2

    print(
        "uso: zip_package_inspector.py freeze <origen> <copia> | "
        "[extract] <ruta-del-zip> <raiz-de-extraccion>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
