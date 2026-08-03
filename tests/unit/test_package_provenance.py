"""Regresión: una verificación de B13 no puede acreditar otro commit.

El caso real: las dos construcciones de ``f9b68d5`` fallaron y no dejaron
artefacto, pero el verificador tomaba «el ZIP más reciente» de ``dist/windows``,
encontró el de ``a82972f`` de una ronda anterior, lo validó y terminó como
SUPERADA CON RESERVAS. Evidencia de un commit distinto del que estaba en HEAD,
producida justo después de un fallo de compilación.

Las tres situaciones que fijan estas pruebas son las del informe:

1. HEAD ``f9b68d5`` con un único ZIP de ``a82972f`` -> rechazo.
2. HEAD ``f9b68d5`` con ZIP y manifiesto de ``f9b68d5`` -> aceptación.
3. Nombre de ``f9b68d5`` pero manifiesto de otro commit -> rechazo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from package_provenance import (
    artifact_name,
    check_provenance,
    main,
    select_artifact,
)

VERSION = "0.1.0.dev0"
HEAD = "f9b68d53e8208c4ccd3185e9032baefbbf7760ce"
HEAD_SHORT = "f9b68d5"
OLD = "a82972faee35e518f86d22075e6d2ba3edcf4f72"
OLD_SHORT = "a82972f"

DIST = r"C:\repo\dist\windows"


def _manifest(commit: str, commit_short: str) -> dict[str, object]:
    return {
        "product": "Sirius",
        "app_version": VERSION,
        "source_commit": commit,
        "source_commit_short": commit_short,
        "packaging_mode": "standalone",
    }


def test_the_artifact_name_matches_what_the_build_composes() -> None:
    """Mismo formato que ``build_windows.ps1``; si divergen, nada encaja."""
    assert artifact_name(VERSION, HEAD_SHORT) == f"Sirius-{VERSION}-{HEAD_SHORT}-windows-x64"


# --- 1. Solo hay el ZIP de otro commit --------------------------------------


def test_a_leftover_zip_from_another_commit_is_refused() -> None:
    """El caso exacto que produjo evidencia falsa."""
    selection = select_artifact(
        DIST,
        VERSION,
        HEAD_SHORT,
        existing_names=[
            f"Sirius-{VERSION}-{OLD_SHORT}-windows-x64.zip",
            f"Sirius-{VERSION}-{OLD_SHORT}-windows-x64.zip.sha256",
        ],
    )

    assert selection.zip_path is None
    assert selection.error is not None
    assert HEAD_SHORT in selection.error
    # El mensaje nombra el artefacto ajeno, para que se entienda por qué no vale.
    assert OLD_SHORT in selection.error


def test_an_empty_distribution_directory_is_refused() -> None:
    selection = select_artifact(DIST, VERSION, HEAD_SHORT, existing_names=[])

    assert selection.zip_path is None
    assert selection.error is not None
    assert HEAD_SHORT in selection.error


def test_the_newest_zip_is_never_chosen_just_for_being_newest() -> None:
    """Aunque haya varios, solo vale el del commit actual.

    ``existing_names`` conserva el orden de aparición, así que un algoritmo que
    tomara «el último» devolvería el de otro commit.
    """
    selection = select_artifact(
        DIST,
        VERSION,
        HEAD_SHORT,
        existing_names=[
            f"Sirius-{VERSION}-{HEAD_SHORT}-windows-x64.zip",
            f"Sirius-{VERSION}-cafe123-windows-x64.zip",
        ],
    )

    assert selection.zip_path is not None
    assert HEAD_SHORT in selection.zip_path
    assert "cafe123" not in selection.zip_path


# --- 2. El ZIP y el manifiesto son del commit actual -------------------------


def test_the_matching_zip_is_selected_and_its_provenance_accepted() -> None:
    selection = select_artifact(
        DIST,
        VERSION,
        HEAD_SHORT,
        existing_names=[f"Sirius-{VERSION}-{HEAD_SHORT}-windows-x64.zip"],
    )
    assert selection.error is None
    assert selection.zip_path is not None
    assert selection.zip_path.endswith(f"Sirius-{VERSION}-{HEAD_SHORT}-windows-x64.zip")

    provenance = check_provenance(_manifest(HEAD, HEAD_SHORT), HEAD, HEAD_SHORT)

    assert provenance.ok
    assert provenance.errors == ()


# --- 3. El nombre cuadra pero el manifiesto es de otro commit ---------------


def test_a_matching_name_with_a_foreign_manifest_is_refused() -> None:
    """El nombre se puede renombrar a mano; el manifiesto es la procedencia.

    Sin esta comprobación, bastaría copiar un ZIP viejo con el nombre nuevo
    para que la verificación lo acreditara.
    """
    provenance = check_provenance(_manifest(OLD, OLD_SHORT), HEAD, HEAD_SHORT)

    assert not provenance.ok
    assert len(provenance.errors) == 2
    assert any(OLD in error and HEAD in error for error in provenance.errors)


def test_only_the_long_commit_diverging_is_still_refused() -> None:
    """Los dos campos se comprueban por separado, no solo uno."""
    provenance = check_provenance(_manifest(OLD, HEAD_SHORT), HEAD, HEAD_SHORT)

    assert not provenance.ok
    assert len(provenance.errors) == 1
    assert "source_commit" in provenance.errors[0]


def test_only_the_short_commit_diverging_is_still_refused() -> None:
    provenance = check_provenance(_manifest(HEAD, OLD_SHORT), HEAD, HEAD_SHORT)

    assert not provenance.ok
    assert len(provenance.errors) == 1
    assert "source_commit_short" in provenance.errors[0]


@pytest.mark.parametrize("missing", ["source_commit", "source_commit_short"])
def test_a_manifest_missing_a_provenance_field_is_refused(missing: str) -> None:
    """Ausencia no es coincidencia: un manifiesto incompleto no acredita nada."""
    manifest = _manifest(HEAD, HEAD_SHORT)
    del manifest[missing]

    provenance = check_provenance(manifest, HEAD, HEAD_SHORT)

    assert not provenance.ok
    assert any(missing in error for error in provenance.errors)


def test_a_manifest_with_a_non_string_field_is_refused() -> None:
    manifest = _manifest(HEAD, HEAD_SHORT)
    manifest["source_commit"] = 12345

    provenance = check_provenance(manifest, HEAD, HEAD_SHORT)

    assert not provenance.ok


# --- Interfaz de linea de comandos que consume PowerShell -------------------


def test_select_on_disk_finds_the_matching_zip(tmp_path: Path) -> None:
    (tmp_path / f"Sirius-{VERSION}-{HEAD_SHORT}-windows-x64.zip").write_bytes(b"z")
    (tmp_path / f"Sirius-{VERSION}-{OLD_SHORT}-windows-x64.zip").write_bytes(b"z")

    selection = select_artifact(str(tmp_path), VERSION, HEAD_SHORT)

    assert selection.error is None
    assert selection.zip_path is not None
    assert HEAD_SHORT in selection.zip_path


def test_select_on_a_missing_directory_is_refused_without_raising() -> None:
    selection = select_artifact(r"C:\no\existe\en\absoluto", VERSION, HEAD_SHORT)

    assert selection.zip_path is None
    assert selection.error is not None


def test_the_select_command_emits_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / f"Sirius-{VERSION}-{HEAD_SHORT}-windows-x64.zip").write_bytes(b"z")

    exit_code = main(["package_provenance.py", "select", str(tmp_path), VERSION, HEAD_SHORT])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] is None
    assert HEAD_SHORT in payload["zip_path"]
    assert payload["expected_name"] == artifact_name(VERSION, HEAD_SHORT)


def test_the_verify_command_reports_a_foreign_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path = tmp_path / "BUILD-MANIFEST.json"
    manifest_path.write_text(json.dumps(_manifest(OLD, OLD_SHORT)), encoding="utf-8")

    exit_code = main(["package_provenance.py", "verify", str(manifest_path), HEAD, HEAD_SHORT])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert len(payload["errors"]) == 2


def test_the_verify_command_accepts_the_current_commit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path = tmp_path / "BUILD-MANIFEST.json"
    manifest_path.write_text(json.dumps(_manifest(HEAD, HEAD_SHORT)), encoding="utf-8")

    assert main(["package_provenance.py", "verify", str(manifest_path), HEAD, HEAD_SHORT]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["errors"] == []


def test_a_wrong_argument_count_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["package_provenance.py"]) == 2
    assert "uso:" in capsys.readouterr().err
