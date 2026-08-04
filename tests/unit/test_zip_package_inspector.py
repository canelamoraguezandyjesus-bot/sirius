"""Regresión del lector y extractor acotado del ZIP de B13."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from zip_package_inspector import (
    ExtractionResult,
    ZipInspection,
    ZipLimits,
    ZipSafetyError,
    copy_bounded,
    inspect_entry_names,
    inspect_zip,
    main,
    safe_extract_zip,
)

ARTIFACT = "Sirius-0.1.0.dev0-a82972f-windows-x64"
EXTRACT_ROOT = r"C:\Temp\Sirius Packaging Smoke Test\Paquete Extraido Del Zip"

# Las rutas reales del artefacto, tal como las escribe .NET Framework.
BACKSLASH_ENTRIES = [
    rf"{ARTIFACT}\Sirius.exe",
    rf"{ARTIFACT}\alembic.ini",
    rf"{ARTIFACT}\BUILD-MANIFEST.json",
    rf"{ARTIFACT}\FILE-MANIFEST.sha256",
    rf"{ARTIFACT}\migrations\env.py",
    rf"{ARTIFACT}\migrations\versions\61be4bb269bf_create_fts5.py",
    rf"{ARTIFACT}\PySide6\plugins\platforms\qwindows.dll",
]


def _inspect(entry_names: list[str]) -> ZipInspection:
    return inspect_entry_names(entry_names, extract_root=EXTRACT_ROOT)


def _limits(
    *,
    entry: int = 1024,
    total: int = 4096,
    ratio: float = 100.0,
    chunk: int = 4,
) -> ZipLimits:
    return ZipLimits(
        max_entry_uncompressed_bytes=entry,
        max_total_uncompressed_bytes=total,
        max_compression_ratio=ratio,
        copy_chunk_bytes=chunk,
    )


def test_backslash_entries_yield_a_single_root() -> None:
    inspection = _inspect(BACKSLASH_ENTRIES)

    assert inspection.roots == (ARTIFACT,)
    assert inspection.file_count == 7
    assert inspection.unsafe == ()


def test_forward_slash_entries_still_yield_a_single_root() -> None:
    inspection = _inspect([name.replace("\\", "/") for name in BACKSLASH_ENTRIES])

    assert inspection.roots == (ARTIFACT,)
    assert inspection.file_count == 7
    assert inspection.unsafe == ()


def test_both_separators_mixed_in_the_same_archive() -> None:
    mixed = [BACKSLASH_ENTRIES[0], BACKSLASH_ENTRIES[1].replace("\\", "/")]

    inspection = _inspect(mixed)

    assert inspection.roots == (ARTIFACT,)
    assert inspection.file_count == 2


def test_directory_entries_are_not_counted_as_files() -> None:
    with_directories = [
        ARTIFACT + "\\",
        ARTIFACT + r"\migrations" + "\\",
        *BACKSLASH_ENTRIES,
    ]

    inspection = _inspect(with_directories)

    assert inspection.file_count == 7
    assert inspection.roots == (ARTIFACT,)


def test_two_roots_are_reported_as_two() -> None:
    inspection = _inspect([rf"{ARTIFACT}\Sirius.exe", r"OtraCarpeta\Sirius.exe"])

    assert inspection.roots == ("OtraCarpeta", ARTIFACT)


def test_a_flat_archive_reports_each_file_as_its_own_root() -> None:
    inspection = _inspect(["Sirius.exe", "alembic.ini"])

    assert inspection.roots == ("Sirius.exe", "alembic.ini")


def test_empty_archive_has_no_roots() -> None:
    inspection = _inspect([])

    assert inspection.roots == ()
    assert inspection.file_count == 0
    assert inspection.unsafe == ()


@pytest.mark.parametrize(
    ("label", "entry_name"),
    [
        ("ruta absoluta posix", "/etc/passwd"),
        ("unidad de Windows", r"C:\Windows\System32\evil.dll"),
        ("recurso UNC", r"\\servidor\recurso\evil.dll"),
        ("traversal desde la raiz del paquete", rf"{ARTIFACT}\..\..\evil.exe"),
        ("traversal posix", "../../evil.exe"),
        ("traversal en medio de la ruta", rf"{ARTIFACT}\migrations\..\..\..\evil.exe"),
    ],
)
def test_unsafe_entries_are_rejected(label: str, entry_name: str) -> None:
    inspection = _inspect([entry_name])

    assert len(inspection.unsafe) == 1, f"{label} no fue rechazada"
    assert entry_name in inspection.unsafe[0]
    assert inspection.roots == ()
    assert inspection.file_count == 0


def test_a_safe_entry_survives_alongside_an_unsafe_one() -> None:
    inspection = _inspect([rf"{ARTIFACT}\Sirius.exe", "/etc/passwd"])

    assert inspection.roots == (ARTIFACT,)
    assert inspection.file_count == 1
    assert len(inspection.unsafe) == 1


def test_a_sibling_directory_that_shares_the_prefix_is_rejected() -> None:
    inspection = inspect_entry_names(
        [r"..\Paquete Extraido Del Zip-malicioso\evil.exe"], extract_root=EXTRACT_ROOT
    )

    assert len(inspection.unsafe) == 1


def test_inspect_zip_reads_a_real_archive(tmp_path: Path) -> None:
    archive_path = tmp_path / "paquete.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name in BACKSLASH_ENTRIES:
            archive.writestr(name, b"contenido")

    inspection = inspect_zip(str(archive_path), extract_root=EXTRACT_ROOT)

    assert inspection.roots == (ARTIFACT,)
    assert inspection.file_count == 7
    assert inspection.total_uncompressed_bytes == 63
    assert inspection.unsafe == ()
    assert inspection.size_violations == ()


def test_inspection_rejects_an_entry_over_the_individual_limit(tmp_path: Path) -> None:
    archive_path = tmp_path / "oversize.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(BACKSLASH_ENTRIES[0], b"x" * 11)

    inspection = inspect_zip(
        str(archive_path), extract_root=EXTRACT_ROOT, limits=_limits(entry=10)
    )

    assert len(inspection.size_violations) == 1
    assert "entrada demasiado grande" in inspection.size_violations[0]


def test_inspection_rejects_excessive_total_expansion(tmp_path: Path) -> None:
    archive_path = tmp_path / "total.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(BACKSLASH_ENTRIES[0], b"a" * 6)
        archive.writestr(BACKSLASH_ENTRIES[1], b"b" * 6)

    inspection = inspect_zip(
        str(archive_path), extract_root=EXTRACT_ROOT, limits=_limits(total=10)
    )

    assert inspection.total_uncompressed_bytes == 12
    assert any("tamano total expandido" in issue for issue in inspection.size_violations)


def test_inspection_rejects_an_excessive_compression_ratio(tmp_path: Path) -> None:
    archive_path = tmp_path / "ratio.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(BACKSLASH_ENTRIES[0], b"0" * 10_000)

    inspection = inspect_zip(
        str(archive_path), extract_root=EXTRACT_ROOT, limits=_limits(entry=20_000, ratio=2.0)
    )

    assert inspection.max_compression_ratio > 2.0
    assert any("ratio de compresion excesivo" in issue for issue in inspection.size_violations)


def test_duplicate_destinations_are_rejected_case_insensitively(tmp_path: Path) -> None:
    archive_path = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(rf"{ARTIFACT}\Sirius.exe", b"uno")
        archive.writestr(rf"{ARTIFACT}\SIRIUS.EXE", b"dos")

    inspection = inspect_zip(str(archive_path), extract_root=EXTRACT_ROOT)

    assert any("destino duplicado" in issue for issue in inspection.unsafe)


def test_copy_bounded_rejects_more_bytes_than_declared() -> None:
    source = io.BytesIO(b"abcde")
    target = io.BytesIO()

    with pytest.raises(ZipSafetyError, match="mas bytes de los declarados"):
        copy_bounded(
            source,
            target,
            expected_bytes=4,
            total_before=0,
            limits=_limits(),
        )


def test_copy_bounded_enforces_the_cumulative_limit_while_writing() -> None:
    source = io.BytesIO(b"abc")
    target = io.BytesIO()

    with pytest.raises(ZipSafetyError, match="limite acumulado"):
        copy_bounded(
            source,
            target,
            expected_bytes=3,
            total_before=8,
            limits=_limits(total=10),
        )


def test_safe_extract_zip_writes_only_the_inspected_files(tmp_path: Path) -> None:
    archive_path = tmp_path / "safe.zip"
    extract_root = tmp_path / "extraido"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(BACKSLASH_ENTRIES[0], b"exe")
        archive.writestr(BACKSLASH_ENTRIES[1], b"ini")

    result = safe_extract_zip(
        str(archive_path),
        extract_root=str(extract_root),
        limits=_limits(),
    )

    assert result == ExtractionResult(file_count=2, total_uncompressed_bytes=6)
    assert (extract_root / ARTIFACT / "Sirius.exe").read_bytes() == b"exe"
    assert (extract_root / ARTIFACT / "alembic.ini").read_bytes() == b"ini"


def test_safe_extract_zip_refuses_size_violations_before_writing(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    extract_root = tmp_path / "extraido"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(BACKSLASH_ENTRIES[0], b"x" * 11)

    with pytest.raises(ZipSafetyError, match="entrada demasiado grande"):
        safe_extract_zip(
            str(archive_path),
            extract_root=str(extract_root),
            limits=_limits(entry=10),
        )

    assert not extract_root.exists()


def test_the_inspection_command_emits_json_for_powershell(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive_path = tmp_path / "paquete.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(BACKSLASH_ENTRIES[0], b"contenido")

    exit_code = main(["zip_package_inspector.py", str(archive_path), EXTRACT_ROOT])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["roots"] == [ARTIFACT]
    assert payload["file_count"] == 1
    assert payload["size_violations"] == []


def test_the_extract_command_emits_json_for_powershell(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive_path = tmp_path / "paquete.zip"
    extract_root = tmp_path / "extraido"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(BACKSLASH_ENTRIES[0], b"contenido")

    exit_code = main(
        ["zip_package_inspector.py", "extract", str(archive_path), str(extract_root)]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"ok": True, "file_count": 1, "total_uncompressed_bytes": 9}


def test_the_command_line_rejects_a_wrong_argument_count(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["zip_package_inspector.py"]) == 2
    assert "uso:" in capsys.readouterr().err
