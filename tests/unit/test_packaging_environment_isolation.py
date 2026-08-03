"""Regresión: el build de empaquetado no puede usar la .venv de desarrollo.

Caso real en Windows, dos veces seguidas antes de llegar a compilar:

    Acceso denegado al eliminar
      .venv\\Lib\\site-packages\\ast_serialize-0.6.0.dist-info\\sboms
    Acceso denegado al eliminar
      .venv\\Lib\\site-packages\\coverage-7.15.0.dist-info\\licenses

La causa no era el permiso, sino el diseño. ``check.ps1`` deja en ``.venv`` los
grupos normales y ``dev``; después el build ejecutaba
``uv sync --frozen --no-default-groups --group packaging`` **sobre esa misma
.venv**, así que uv hacía lo que se le pedía: desinstalar las herramientas de
desarrollo. Bajo OneDrive, borrar esos árboles falla. Reintentar habría sido
insistir en destruir el entorno de desarrollo con más paciencia.

Estas comprobaciones son estructurales, sobre el texto del script, porque el
objeto de la prueba es una decisión de configuración de PowerShell y aquí no hay
PowerShell. Son deliberadamente concretas: cada una falla con el código anterior
a la corrección.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_BUILD_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_windows.ps1"


@pytest.fixture(scope="module")
def build_script() -> str:
    return _BUILD_SCRIPT.read_text(encoding="utf-8")


def test_the_build_script_exists() -> None:
    assert _BUILD_SCRIPT.is_file()


def test_the_packaging_interpreter_does_not_come_from_the_development_venv(
    build_script: str,
) -> None:
    """``$VenvPython`` y ``$VenvDeploy`` no pueden apuntar a ``<repo>\\.venv``.

    Con el código anterior estas dos asignaciones eran
    ``Join-Path $RepoRoot ".venv\\Scripts\\python.exe"``, y es lo que hacía que
    el sync caza al entorno de desarrollo.
    """
    offending = [
        line.strip()
        for line in build_script.splitlines()
        if re.search(r"^\s*\$Venv(Python|Deploy)\s*=", line) and ".venv" in line
    ]

    assert offending == [], (
        "el build sigue tomando su interprete de la .venv de desarrollo: " + "; ".join(offending)
    )


def test_the_build_script_never_builds_a_path_into_the_development_venv(build_script: str) -> None:
    """No puede componerse ninguna ruta hacia ``<repo>\\.venv``.

    Se busca la construcción concreta, no la cadena ``.venv`` a secas: el script
    menciona ``.venv`` legítimamente en la lista de patrones prohibidos que
    impide que una ruta de entorno acabe dentro de ``pysidedeploy.spec``. Esa
    mención es justo lo contrario del defecto, así que una prueba que la contara
    como infracción obligaría a debilitar una comprobación buena.
    """
    offending = [
        line.strip()
        for line in build_script.splitlines()
        if re.search(r"Join-Path\s+\$RepoRoot\s+[\"']\.venv", line)
        or re.search(r"\$RepoRoot[^\n]*[\"']\\?\.venv\\", line)
    ]

    assert offending == [], (
        "el build todavia compone una ruta a la .venv de desarrollo: " + "; ".join(offending)
    )


def test_the_build_declares_a_dedicated_packaging_environment(build_script: str) -> None:
    """Debe existir una ruta propia, fuera del checkout."""
    assert "$PackagingVenv" in build_script
    assert "LOCALAPPDATA" in build_script, (
        "el entorno dedicado debe vivir bajo LOCALAPPDATA, fuera del checkout y de OneDrive"
    )


def test_the_dedicated_environment_is_selected_through_the_supported_mechanism(
    build_script: str,
) -> None:
    """``UV_PROJECT_ENVIRONMENT``, comprobado contra uv 0.8.17.

    No es una suposición: se verificó que uv crea el entorno en la ruta
    indicada, instala solo las dependencias normales más el grupo pedido, y deja
    intacta la ``.venv`` del proyecto.
    """
    assert "UV_PROJECT_ENVIRONMENT" in build_script


def test_the_sync_still_excludes_default_groups(build_script: str) -> None:
    """El aislamiento del grupo dev no se pierde al cambiar de entorno."""
    assert "--no-default-groups" in build_script
    assert "--frozen" in build_script


def test_the_environment_inventory_is_still_enforced(build_script: str) -> None:
    """Estar en otro entorno no exime de comprobar qué contiene."""
    for required in ("PySide6", "nuitka", "alembic", "SQLAlchemy", "keyring"):
        assert required in build_script, f"falta la comprobacion de {required}"
    for forbidden in ("mypy", "pytest", "ruff", "pytest-qt", "pytest-cov"):
        assert forbidden in build_script, f"falta la comprobacion de ausencia de {forbidden}"


def test_the_versioned_deploy_spec_never_names_an_environment_path() -> None:
    """``pysidedeploy.spec`` versionado no puede llevar rutas de entorno.

    Ni la del entorno dedicado ni la de la ``.venv``: el artefacto debe poder
    construirse desde otro checkout y en otra maquina.
    """
    spec = (_BUILD_SCRIPT.parent.parent / "pysidedeploy.spec").read_text(encoding="utf-8")

    lowered = spec.lower()
    assert ".venv" not in lowered
    assert "localappdata" not in lowered
    assert "packaging-venv" not in lowered
    assert "c:\\users" not in lowered
