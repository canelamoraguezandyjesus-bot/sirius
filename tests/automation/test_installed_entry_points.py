"""H-13 (incidencia #275): los puntos de entrada funcionan desde una instalación real.

Antes de este bloque, ``sirius_engine.mirror_projection`` insertaba
``scripts/`` en ``sys.path`` e importaba ``automation.sirius_convergence`` en
cuanto se LLAMABA -no solo se importaba- a la proyección. ``scripts/`` no
viaja en el wheel (``[tool.uv.build-backend] module-name`` solo empaqueta
``sirius``/``sirius_engine``), así que cualquier punto de entrada que
alcanzara ``mirror_projection`` -``sirius-despachar`` vía
``sirius_engine.cli`` -> ``context_recall``, y ``sirius-racha`` directamente-
reventaba con ``ModuleNotFoundError`` en cuanto se ejecutaba desde una
instalación real, no editable (comprobado manualmente reproduciendo este
fallo con el código previo a H-13: construyendo el wheel real, instalándolo
en un venv limpio y ejecutando el binario instalado).

Este módulo repite exactamente esa reproducción como prueba automática:
construye el wheel de verdad con ``uv build``, lo instala con ``uv pip
install --no-deps`` en un venv limpio -sin el checkout, sin ``scripts/``- y
ejecuta los binarios instalados. Las dependencias de terceros (SQLAlchemy,
pydantic...) se resuelven vía ``PYTHONPATH`` contra el ``site-packages`` del
entorno de desarrollo -instalarlas de nuevo exigiría red, que este runner no
tiene garantizada-, pero eso es exactamente lo que este bloque NO toca:
``sirius``/``sirius_engine`` solo existen, en el venv de la prueba, en la
copia instalada desde el wheel.

Límite honesto: si ``uv`` no está disponible en el entorno de pruebas, estas
pruebas se saltan explícitamente en vez de darse por buenas.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_TERCEROS_SITE_PACKAGES = sysconfig.get_path("purelib")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("uv") is None, reason="uv no está disponible en este entorno."),
]


@pytest.fixture(scope="module")
def instalacion_real(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Wheel real construido e instalado en un venv limpio, sin el checkout."""
    base = tmp_path_factory.mktemp("h13-instalacion")
    wheel_dir = base / "dist"
    build = subprocess.run(
        ["uv", "build", "--wheel", "-o", str(wheel_dir), "--offline"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheels = sorted(wheel_dir.glob("*.whl"))
    assert wheels, f"uv build no produjo ningún wheel: {build.stdout}{build.stderr}"

    venv_dir = base / "venv"
    venv_create = subprocess.run(
        ["uv", "venv", str(venv_dir), "--python", sys.executable, "--offline"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert venv_create.returncode == 0, venv_create.stdout + venv_create.stderr

    install = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(venv_dir / "bin" / "python"),
            "--offline",
            "--no-deps",
            str(wheels[0]),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    return venv_dir


@pytest.mark.parametrize("entry_point", ["sirius-despachar", "sirius-racha"])
def test_entry_point_arranca_desde_la_instalacion_sin_el_arbol_de_codigo(
    instalacion_real: Path, entry_point: str
) -> None:
    """Requisito 6: arrancan de verdad, no solo se importan sin fallar."""
    binario = instalacion_real / "bin" / entry_point
    assert binario.is_file(), f"El wheel no instaló el punto de entrada {entry_point}"

    entorno = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": _TERCEROS_SITE_PACKAGES}
    result = subprocess.run(
        [str(binario), "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(instalacion_real),
        env=entorno,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ModuleNotFoundError" not in result.stderr
