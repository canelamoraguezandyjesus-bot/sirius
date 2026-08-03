"""Regresión del lector de entradas del ZIP de B13.

El fallo que estas pruebas fijan es real y estuvo publicado: el verificador
partía los nombres de entrada solo por ``/``, y el ZIP que produce
``ZipFile.CreateFromDirectory`` de .NET Framework los escribe con ``\\``. Cada
ruta completa quedaba como un único segmento y por tanto como una raíz
distinta, así que un ZIP correcto de 109 archivos daba 109 raíces y la
verificación se detenía antes de comprobar nada útil. Convivió con la
comprobación de calidad en verde porque la lógica vivía dentro de un ``.ps1``
que ninguna prueba ejecutaba.

Las rutas se juzgan con semántica de Windows en cualquier plataforma (el módulo
usa ``ntpath`` a propósito), así que estas pruebas valen corriendo en Ubuntu.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from zip_package_inspector import ZipInspection, inspect_entry_names, inspect_zip, main

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


def test_backslash_entries_yield_a_single_root() -> None:
    """El caso exacto que fallaba en Windows.

    Sin normalizar el separador esto devuelve siete raíces, una por archivo.
    """
    inspection = _inspect(BACKSLASH_ENTRIES)

    assert inspection.roots == (ARTIFACT,)
    assert inspection.file_count == 7
    assert inspection.unsafe == ()


def test_forward_slash_entries_still_yield_a_single_root() -> None:
    """Un ZIP conforme a la especificación tiene que seguir valiendo."""
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
    # Un raw-string no puede terminar en barra invertida, de ahi la concatenacion.
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
    """Un ZIP sin carpeta raíz no es el paquete de B13, y debe notarse."""
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
    """Ninguna de estas puede salir de un ZIP hecho por build_windows.ps1.

    Si aparece, el ZIP no es el nuestro: se rechaza en vez de extraerlo.
    """
    inspection = _inspect([entry_name])

    assert len(inspection.unsafe) == 1, f"{label} no fue rechazada"
    assert entry_name in inspection.unsafe[0]
    # Una entrada rechazada no aporta raíz ni cuenta como archivo.
    assert inspection.roots == ()
    assert inspection.file_count == 0


def test_a_safe_entry_survives_alongside_an_unsafe_one() -> None:
    """Rechazar una entrada no puede descartar el resto del análisis."""
    inspection = _inspect([rf"{ARTIFACT}\Sirius.exe", "/etc/passwd"])

    assert inspection.roots == (ARTIFACT,)
    assert inspection.file_count == 1
    assert len(inspection.unsafe) == 1


def test_a_sibling_directory_that_shares_the_prefix_is_rejected() -> None:
    """El límite se compara con separador final, no como simple prefijo.

    Sin él, ``...Zip-malicioso\\x`` pasaría por estar dentro de ``...Zip``.
    """
    inspection = inspect_entry_names(
        [r"..\Paquete Extraido Del Zip-malicioso\evil.exe"], extract_root=EXTRACT_ROOT
    )

    assert len(inspection.unsafe) == 1


def test_inspect_zip_reads_a_real_archive(tmp_path: Path) -> None:
    """El mismo análisis, contra un ZIP de verdad en disco."""
    archive_path = tmp_path / "paquete.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for name in BACKSLASH_ENTRIES:
            archive.writestr(name, b"contenido")

    inspection = inspect_zip(str(archive_path), extract_root=EXTRACT_ROOT)

    assert inspection.roots == (ARTIFACT,)
    assert inspection.file_count == 7
    assert inspection.unsafe == ()


def test_the_command_line_emits_json_for_powershell(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """PowerShell consume esta salida con ConvertFrom-Json."""
    archive_path = tmp_path / "paquete.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(BACKSLASH_ENTRIES[0], b"contenido")

    exit_code = main(["zip_package_inspector.py", str(archive_path), EXTRACT_ROOT])

    assert exit_code == 0
    payload = capsys.readouterr().out.strip()
    assert '"roots": ["' + ARTIFACT + '"]' in payload
    assert '"file_count": 1' in payload
    assert '"unsafe": []' in payload


def test_the_command_line_rejects_a_wrong_argument_count(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["zip_package_inspector.py"]) == 2
    assert "uso:" in capsys.readouterr().err
