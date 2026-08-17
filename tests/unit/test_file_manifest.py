"""Regresiones del validador confinado de FILE-MANIFEST.sha256."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from file_manifest import (
    MAX_MANIFEST_BYTES,
    MAX_MANIFEST_ENTRIES,
    MAX_MANIFEST_LINE_CHARS,
    ManifestValidationError,
    main,
    validate_manifest,
    validate_manifest_lines,
)

PACKAGE_ROOT = r"C:\Temp\Sirius Packaging Smoke Test\Paquete Extraido\Sirius"
HASH_A = "a" * 64
HASH_B = "b" * 64


def _validate(*lines: str):  # type: ignore[no-untyped-def]
    return validate_manifest_lines(list(lines), package_root=PACKAGE_ROOT)


def test_valid_paths_are_normalized_without_changing_their_hashes() -> None:
    entries = _validate(
        f"{HASH_A}  Sirius.exe",
        rf"{HASH_B}  migrations\versions\revision.py",
    )

    assert [entry.sha256 for entry in entries] == [HASH_A, HASH_B]
    assert [entry.path for entry in entries] == [
        "Sirius.exe",
        "migrations/versions/revision.py",
    ]


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "/Windows/System32/evil.dll",
        r"C:\Windows\System32\evil.dll",
        r"\\server\share\evil.dll",
        r"..\outside.txt",
        r"migrations\..\outside.txt",
        "migrations//outside.txt",
        "migrations/./outside.txt",
    ],
)
def test_unsafe_or_ambiguous_paths_are_rejected(unsafe_path: str) -> None:
    with pytest.raises(ManifestValidationError):
        _validate(f"{HASH_A}  {unsafe_path}")


def test_empty_path_is_rejected() -> None:
    with pytest.raises(ManifestValidationError, match="ruta vacia"):
        _validate(f"{HASH_A}  ")


def test_blank_manifest_line_is_rejected() -> None:
    with pytest.raises(ManifestValidationError, match="entrada vacia"):
        _validate(f"{HASH_A}  Sirius.exe", "")


def test_invalid_hash_is_rejected() -> None:
    with pytest.raises(ManifestValidationError, match="SHA-256 no valido"):
        _validate("not-a-hash  Sirius.exe")


def test_duplicates_are_rejected_after_case_and_separator_normalization() -> None:
    with pytest.raises(ManifestValidationError, match="duplicado"):
        _validate(
            rf"{HASH_A}  PySide6\plugins\platforms\qwindows.dll",
            f"{HASH_B}  pyside6/plugins/platforms/QWINDOWS.DLL",
        )


def test_empty_manifest_is_rejected() -> None:
    with pytest.raises(ManifestValidationError, match="no contiene archivos"):
        _validate()


def test_manifest_entry_count_is_bounded_before_parsing() -> None:
    lines = [f"{HASH_A}  file-{index}.txt" for index in range(MAX_MANIFEST_ENTRIES + 1)]

    with pytest.raises(ManifestValidationError, match="demasiadas entradas"):
        validate_manifest_lines(lines, package_root=PACKAGE_ROOT)


def test_manifest_line_length_is_bounded_before_path_processing() -> None:
    path = "x" * MAX_MANIFEST_LINE_CHARS

    with pytest.raises(ManifestValidationError, match="longitud excesiva"):
        _validate(f"{HASH_A}  {path}")


def test_manifest_file_size_is_bounded_before_decoding(tmp_path: Path) -> None:
    manifest = tmp_path / "FILE-MANIFEST.sha256"
    manifest.write_bytes(b"x" * (MAX_MANIFEST_BYTES + 1))

    with pytest.raises(ManifestValidationError, match="demasiado grande"):
        validate_manifest(str(manifest), package_root=PACKAGE_ROOT)


def test_command_emits_only_validated_entries_for_powershell(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "FILE-MANIFEST.sha256"
    manifest.write_text(f"{HASH_A}  Sirius.exe\n", encoding="utf-8")

    exit_code = main(["file_manifest.py", str(manifest), PACKAGE_ROOT])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "ok": True,
        "entries": [{"sha256": HASH_A, "path": "Sirius.exe"}],
    }


def test_command_returns_json_error_without_exposing_external_file_contents(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "FILE-MANIFEST.sha256"
    manifest.write_text(f"{HASH_A}  ..\\outside.txt\n", encoding="utf-8")

    exit_code = main(["file_manifest.py", str(manifest), PACKAGE_ROOT])

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert ".." in payload["error"]
