"""Regresiones estructurales del entorno dedicado de empaquetado.

``build_windows.ps1`` es la entrada canónica y ejecuta la guarda de ruta. La
implementación pesada vive en ``build_windows_impl.ps1`` y solo se alcanza
cuando la guarda ha aceptado una ruta externa al checkout.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
_BUILD_WRAPPER = _SCRIPTS / "build_windows.ps1"
_BUILD_IMPLEMENTATION = _SCRIPTS / "build_windows_impl.ps1"


@pytest.fixture(scope="module")
def build_wrapper() -> str:
    return _BUILD_WRAPPER.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def build_implementation() -> str:
    return _BUILD_IMPLEMENTATION.read_text(encoding="utf-8")


def test_the_canonical_wrapper_and_internal_implementation_exist() -> None:
    assert _BUILD_WRAPPER.is_file()
    assert _BUILD_IMPLEMENTATION.is_file()


def test_the_path_guard_runs_before_the_internal_build(build_wrapper: str) -> None:
    guard_call = build_wrapper.index("$packagingGuard = Invoke-JsonController")
    implementation_call = build_wrapper.index("& $SnapshotImplementation")

    assert guard_call < implementation_call
    assert "packaging_path_guard.py" in build_wrapper
    assert "UV_PROJECT_ENVIRONMENT" not in build_wrapper[guard_call:implementation_call]
    assert "uv sync" not in build_wrapper[guard_call:implementation_call]


def test_no_packaging_executable_is_derived_before_the_guard(build_wrapper: str) -> None:
    guard_call = build_wrapper.index("$packagingGuard = Invoke-JsonController")
    pre_guard = build_wrapper[:guard_call]

    assert "$VenvPython" not in pre_guard
    assert "$VenvDeploy" not in pre_guard
    assert "Scripts\\python.exe" not in pre_guard
    assert "Scripts\\pyside6-deploy.exe" not in pre_guard


def test_the_packaging_interpreter_does_not_come_from_the_development_venv(
    build_implementation: str,
) -> None:
    offending = [
        line.strip()
        for line in build_implementation.splitlines()
        if re.search(r"^\s*\$Venv(Python|Deploy)\s*=", line) and ".venv" in line
    ]

    assert offending == [], (
        "el build sigue tomando su interprete de la .venv de desarrollo: " + "; ".join(offending)
    )


def test_the_build_never_builds_a_path_into_the_development_venv(
    build_implementation: str,
) -> None:
    offending = [
        line.strip()
        for line in build_implementation.splitlines()
        if re.search(r"Join-Path\s+\$RepoRoot\s+[\"']\.venv", line)
        or re.search(r"\$RepoRoot[^\n]*[\"']\\?\.venv\\", line)
    ]

    assert offending == [], (
        "el build todavia compone una ruta a la .venv de desarrollo: " + "; ".join(offending)
    )


def test_the_build_declares_a_dedicated_packaging_environment(
    build_wrapper: str,
    build_implementation: str,
) -> None:
    combined = build_wrapper + build_implementation
    assert "$PackagingVenv" in combined
    assert "LOCALAPPDATA" in combined


def test_the_dedicated_environment_is_selected_through_uv(
    build_implementation: str,
) -> None:
    assert "UV_PROJECT_ENVIRONMENT" in build_implementation


def test_the_sync_still_excludes_default_groups(build_implementation: str) -> None:
    assert "--no-default-groups" in build_implementation
    assert "--frozen" in build_implementation


def test_the_environment_inventory_is_still_enforced(build_implementation: str) -> None:
    for required in ("PySide6", "nuitka", "alembic", "SQLAlchemy", "keyring"):
        assert required in build_implementation, f"falta la comprobacion de {required}"
    for forbidden in ("mypy", "pytest", "ruff", "pytest-qt", "pytest-cov"):
        assert forbidden in build_implementation, (
            f"falta la comprobacion de ausencia de {forbidden}"
        )


def test_the_versioned_deploy_spec_never_names_an_environment_path() -> None:
    spec = (_SCRIPTS.parent / "pysidedeploy.spec").read_text(encoding="utf-8")

    lowered = spec.lower()
    assert ".venv" not in lowered
    assert "localappdata" not in lowered
    assert "packaging-venv" not in lowered
    assert "c:\\users" not in lowered
