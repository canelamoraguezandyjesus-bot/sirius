"""Regresiones comunes de rutas Win32 para ZIP y FILE-MANIFEST."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from file_manifest import ManifestValidationError, validate_manifest_lines
from windows_path_safety import WindowsPathError, split_safe_windows_relative_path
from zip_package_inspector import (
    ZipSafetyError,
    inspect_entry_names,
    inspect_zip,
    safe_extract_zip,
)

PACKAGE_ROOT = r"C:\Temp\Sirius Packaging Smoke Test\Paquete\Sirius"
EXTRACT_ROOT = r"C:\Temp\Sirius Packaging Smoke Test\Extraido"
HASH = "a" * 64


@pytest.mark.parametrize(
    ("raw_path", "expected"),
    [
        (r"Sirius\migrations\env.py", ("Sirius", "migrations", "env.py")),
        (
            "Sirius/PySide6/plugins/qwindows.dll",
            ("Sirius", "PySide6", "plugins", "qwindows.dll"),
        ),
        ("Sirius/migrations/", ("Sirius", "migrations")),
    ],
)
def test_safe_windows_paths_have_one_unambiguous_component_sequence(
    raw_path: str, expected: tuple[str, ...]
) -> None:
    assert split_safe_windows_relative_path(
        raw_path, directory_entry=raw_path.endswith(("/", "\\"))
    ) == expected


def test_directory_separator_is_only_accepted_for_a_directory_entry() -> None:
    with pytest.raises(WindowsPathError):
        split_safe_windows_relative_path("Sirius/migrations/")


@pytest.mark.parametrize(
    "unsafe_path",
    [
        r"Sirius\Sirius.exe:oculto",
        r"Sirius\NUL.txt",
        r"Sirius\COM1",
        r"Sirius\archivo. ",
        r"Sirius\archivo.",
        r"Sirius\archivo?.txt",
        "Sirius/control\x01.txt",
        r"Sirius\\doble.txt",
        r"Sirius\.\archivo.txt",
        r"Sirius\..\archivo.txt",
        r"C:\Sirius\archivo.txt",
        r"\\servidor\recurso\archivo.txt",
    ],
)
def test_ambiguous_or_dangerous_windows_paths_are_rejected(unsafe_path: str) -> None:
    with pytest.raises(WindowsPathError):
        split_safe_windows_relative_path(unsafe_path)


def test_zip_inspection_rejects_ads_reserved_names_and_trimmed_aliases() -> None:
    inspection = inspect_entry_names(
        [
            r"Sirius\Sirius.exe",
            r"Sirius\Sirius.exe:oculto",
            r"Sirius\NUL.txt",
            r"Sirius\archivo. ",
        ],
        extract_root=EXTRACT_ROOT,
    )

    assert inspection.roots == ("Sirius",)
    assert inspection.file_count == 1
    assert len(inspection.unsafe) == 3
    assert any("Sirius.exe:oculto" in issue for issue in inspection.unsafe)
    assert any("NUL.txt" in issue for issue in inspection.unsafe)
    assert any("archivo. " in issue for issue in inspection.unsafe)


def test_unsafe_zip_path_is_rejected_before_any_output_is_created(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    extract_root = tmp_path / "extraido"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(r"Sirius\Sirius.exe", b"normal")
        archive.writestr(r"Sirius\Sirius.exe:oculto", b"ads")

    with pytest.raises(ZipSafetyError):
        safe_extract_zip(str(archive_path), extract_root=str(extract_root))

    assert not extract_root.exists()


def test_directory_and_file_collision_is_rejected_before_extraction(tmp_path: Path) -> None:
    archive_path = tmp_path / "collision.zip"
    extract_root = tmp_path / "extraido"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("Sirius/collision/", b"")
        archive.writestr("Sirius/collision", b"file")

    inspection = inspect_zip(str(archive_path), extract_root=EXTRACT_ROOT)

    assert any("destino duplicado" in issue for issue in inspection.unsafe)
    with pytest.raises(ZipSafetyError, match="destino duplicado"):
        safe_extract_zip(str(archive_path), extract_root=str(extract_root))
    assert not extract_root.exists()


@pytest.mark.parametrize(
    "entry_names",
    [
        ("Sirius/node", "Sirius/node/child.txt"),
        ("Sirius/node/child.txt", "Sirius/node"),
        ("Sirius/node/", "Sirius/node/child.txt", "Sirius/node"),
    ],
)
def test_file_ancestor_collisions_are_rejected_before_extraction(
    tmp_path: Path, entry_names: tuple[str, ...]
) -> None:
    archive_path = tmp_path / "ancestor-collision.zip"
    extract_root = tmp_path / "extraido"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for index, name in enumerate(entry_names):
            archive.writestr(name, b"" if name.endswith("/") else str(index).encode())

    inspection = inspect_zip(str(archive_path), extract_root=EXTRACT_ROOT)

    assert any(
        "colisiona" in issue or "directorio" in issue or "duplicado" in issue
        for issue in inspection.unsafe
    )
    with pytest.raises(ZipSafetyError):
        safe_extract_zip(str(archive_path), extract_root=str(extract_root))
    assert not extract_root.exists()


def test_directory_symlink_is_rejected_before_extraction(tmp_path: Path) -> None:
    archive_path = tmp_path / "symlink.zip"
    extract_root = tmp_path / "extraido"
    link = zipfile.ZipInfo("Sirius/link/")
    link.create_system = 3
    link.external_attr = 0o120777 << 16
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(link, b"")

    inspection = inspect_zip(str(archive_path), extract_root=EXTRACT_ROOT)

    assert any("enlace simbolico" in issue for issue in inspection.unsafe)
    with pytest.raises(ZipSafetyError, match="enlace simbolico"):
        safe_extract_zip(str(archive_path), extract_root=str(extract_root))
    assert not extract_root.exists()


@pytest.mark.parametrize(
    "unsafe_path",
    [
        r"Sirius.exe:oculto",
        r"NUL.txt",
        r"migrations\archivo. ",
        r"migrations\archivo?.py",
    ],
)
def test_file_manifest_rejects_the_same_windows_aliases(unsafe_path: str) -> None:
    with pytest.raises(ManifestValidationError):
        validate_manifest_lines(
            [f"{HASH}  {unsafe_path}"],
            package_root=PACKAGE_ROOT,
        )
