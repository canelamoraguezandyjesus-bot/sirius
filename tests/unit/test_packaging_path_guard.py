"""Regresión del P2: validar la ruta antes de sincronizar el entorno."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packaging_path_guard import PackagingPathError, main, validate_packaging_path


def test_rejects_the_checkout_itself() -> None:
    with pytest.raises(PackagingPathError, match="coincide con el checkout"):
        validate_packaging_path(r"C:\work\sirius", r"C:\work\sirius")


def test_rejects_a_descendant_of_the_checkout() -> None:
    with pytest.raises(PackagingPathError, match="dentro del checkout"):
        validate_packaging_path(r"C:\work\sirius", r"C:\work\sirius\packaging-venv")


def test_rejects_dot_dot_that_resolves_inside_the_checkout() -> None:
    with pytest.raises(PackagingPathError, match="dentro del checkout"):
        validate_packaging_path(
            r"C:\work\sirius",
            r"C:\work\outside\..\sirius\packaging-venv",
        )


def test_rejects_mixed_separators_and_case_variants() -> None:
    with pytest.raises(PackagingPathError, match="dentro del checkout"):
        validate_packaging_path(
            r"C:\Work\Sirius",
            r"c:/work/SIRIUS\Packaging-Venv",
        )


def test_accepts_a_sibling_with_a_common_textual_prefix() -> None:
    result = validate_packaging_path(
        r"C:\work\sirius",
        r"C:\work\sirius-packaging\venv",
    )

    assert result.ok is True
    assert result.packaging_path == r"c:\work\sirius-packaging\venv"


def test_accepts_a_path_on_another_drive() -> None:
    result = validate_packaging_path(r"C:\work\sirius", r"D:\sirius-packaging\venv")

    assert result.ok is True
    assert result.packaging_path == r"d:\sirius-packaging\venv"


def test_rejection_has_no_filesystem_side_effects(tmp_path: Path) -> None:
    before = tuple(tmp_path.iterdir())

    with pytest.raises(PackagingPathError):
        validate_packaging_path(r"C:\work\sirius", r"C:\work\sirius\venv")

    assert tuple(tmp_path.iterdir()) == before


def test_cli_reports_a_rejection_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([r"C:\work\sirius", r"C:\work\sirius\venv"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["ok"] is False
    assert "checkout" in payload["error"]


def test_cli_reports_canonical_paths_for_an_accepted_sibling(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([r"C:\work\sirius", r"C:\work\sirius-packaging\venv"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "ok": True,
        "packaging_path": r"c:\work\sirius-packaging\venv",
        "repo_root": r"c:\work\sirius",
    }
