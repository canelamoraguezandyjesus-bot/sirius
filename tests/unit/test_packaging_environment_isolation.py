"""Regresiones estructurales del entorno dedicado de empaquetado.

``build_windows.ps1`` es la entrada canónica y ejecuta la guarda de ruta. La
implementación pesada vive en ``build_windows_impl.ps1`` y solo se alcanza
cuando la guarda ha aceptado una ruta externa al checkout.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from _powershell_text import executable_text

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
    """Entre la guarda y la delegacion no puede EJECUTARSE nada del entorno.

    Se mira solo el texto ejecutable. Buscar la subcadena "uv sync" a secas
    tambien encontraba el comentario que explica que el bloqueo cubre uv sync y
    el mensaje de error que lo menciona, de modo que la prueba fallaba por lo
    que el script *dice* en vez de por lo que *hace*. El wrapper no invoca uv
    sync: la unica invocacion real es Invoke-Native "uv" @("sync", ...) y vive
    en build_windows_impl.ps1, ya dentro del snapshot.
    """
    guard_call = build_wrapper.index("$packagingGuard = Invoke-JsonController")
    implementation_call = build_wrapper.index("& $SnapshotImplementation")

    assert guard_call < implementation_call
    assert "packaging_path_guard.py" in build_wrapper

    region = build_wrapper[guard_call:implementation_call]
    executable = executable_text(region)

    # La forma concreta con la que este repositorio invoca uv. Se busca en el
    # texto CRUDO a proposito: "uv" y "sync" son literales de cadena, y
    # executable_text los vacia, asi que buscarlos ahi no encontraria nunca una
    # invocacion real. Los falsos positivos que rompian esta prueba -un
    # comentario y un mensaje de error- no contienen esta forma.
    assert not re.search(r'Invoke-Native\s+"uv"', region)
    # Y la forma suelta, como comando, que si tiene sentido buscar en lo
    # ejecutable porque ahi no habria comillas que vaciar.
    assert not re.search(r"^\s*(&\s*)?uv\s+sync\b", executable, re.MULTILINE)
    assert "UV_PROJECT_ENVIRONMENT" not in executable


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


def test_the_sync_copies_instead_of_hardlinking(build_implementation: str) -> None:
    """El enlazado por omision de uv no sobrevive a OneDrive.

    En la primera construccion real desde un arbol limpio en 60a7e9d, uv sync
    fallo en el paso 4/13 instalando pyside6 6.11.1: los archivos de su cache ya
    tenian enlaces permanentes hacia la .venv del proyecto, que vive bajo
    OneDrive, y crear otro enlace hacia ellos es una operacion que el filtro de
    nube rechaza con el error 396 de Windows. Pausar la sincronizacion no basta,
    porque el filtro sigue montado. Copiar es el remedio que documenta el propio
    uv y no cambia que se instala.
    """
    assignment = re.search(r'\$env:UV_LINK_MODE\s*=\s*"copy"', build_implementation)
    assert assignment is not None, "el build no fuerza el modo de enlace de uv"

    sync_call = build_implementation.index('Invoke-Native "uv" @("sync"')
    assert assignment.start() < sync_call, "UV_LINK_MODE se define despues del sync: llega tarde"


def test_pyside6_deploy_is_told_which_environment_it_runs_in(
    build_implementation: str,
) -> None:
    """Ejecutarlo DESDE el entorno no basta: hay que decirselo.

    La deteccion de pyside6-deploy es solo ``bool(os.environ.get("VIRTUAL_ENV"))``;
    no mira ``sys.prefix``. Sin la variable se cree fuera de todo entorno y
    pregunta por teclado si puede instalar paquetes. Como la salida esta
    redirigida al log, la pregunta no se ve y la construccion se queda esperando:
    50 minutos parada en el paso 8/13 con 173 bytes de log y cero CPU. Antes
    funcionaba por accidente, con la variable heredada de la .venv activada.
    """
    for invocation in ("--dry-run", '-c "$WorkingSpec" -v'):
        position = build_implementation.index(invocation)
        preceding = build_implementation[:position]
        block_start = preceding.rindex("@echo off")
        assert 'set "VIRTUAL_ENV=$PackagingVenv"' in build_implementation[block_start:position], (
            f"la invocacion con {invocation} no declara VIRTUAL_ENV"
        )


def test_pyside6_deploy_runs_without_a_console_to_ask_on(
    build_implementation: str,
) -> None:
    """Ninguna pregunta puede volver a colgar el build.

    Sin entrada, ``input()`` lanza ``EOFError``, el proceso termina con codigo
    distinto de cero y el fallo sale con su log. Un build desatendido no puede
    depender de que alguien este mirando la pantalla.
    """
    for invocation in ("--dry-run", "-v"):
        line = next(
            candidate
            for candidate in build_implementation.splitlines()
            if "$VenvDeploy" in candidate and invocation in candidate
        )
        assert "< NUL" in line, f"la invocacion con {invocation} deja la entrada abierta: {line}"


def test_the_generated_batch_files_carry_no_powershell_comments(
    build_implementation: str,
) -> None:
    """Dentro de un here-string, ``#`` no comenta: es una linea del .cmd.

    Un comentario que explicaba VSLANG se escribio dentro del cuerpo de
    ``run-deploy.cmd``, y las dos construcciones de 3432253 escupieron diez veces
    ``'"#" no se reconoce como un comando interno o externo'``. No afecto al
    artefacto -los inventarios de las dos salieron identicos-, pero un archivo
    generado no puede llevar comentarios del lenguaje que lo genera.
    """
    here_strings = re.findall(r'@"\r?\n(.*?)\r?\n"@', build_implementation, re.DOTALL)
    batch_bodies = [body for body in here_strings if body.lstrip().startswith("@echo off")]

    assert batch_bodies, "no se encontro ningun cuerpo de .cmd generado que revisar"
    for body in batch_bodies:
        offending = [line for line in body.splitlines() if line.lstrip().startswith("#")]
        assert offending == [], "un .cmd generado lleva comentarios de PowerShell: " + "; ".join(
            offending
        )


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


def test_nuitka_compiles_without_the_inline_compiler_cache() -> None:
    """Nada se interpone entre scons y cl.exe.

    Nuitka trae su propia copia de clcache y la enciende sola en MSVC::

        if env.msvc_mode and not env.disable_ccache:
            enableClcache(...)

    En la construccion de e9d51c7 fallo en las 15 unidades que intento, desde la
    primera, con "clcache: preprocessor failed", y dejo la compilacion muerta a
    los cinco minutos. Es una cache: quitarla no cambia el contenido del
    artefacto, solo el tiempo de compilacion.
    """
    spec = (_SCRIPTS.parent / "pysidedeploy.spec").read_text(encoding="utf-8")

    extra_args = next(line for line in spec.splitlines() if line.startswith("extra_args ="))

    assert "--disable-cache=ccache" in extra_args, (
        "Nuitka volveria a interponer su copia interna de clcache"
    )


def test_msvc_speaks_english_to_nuitka(build_implementation: str) -> None:
    """La capa de scons de Nuitka lee la salida de cl.exe, y solo en ingles.

    Lo pide en el log de la propia construccion: "Support language of Nuitka is
    English. Please install the English language pack for Visual Studio." VSLANG
    es el mecanismo de Microsoft para fijar el idioma por LCID, asi que no hace
    falta instalar nada en el equipo. No cambia el artefacto: solo el idioma de
    los mensajes del compilador.
    """
    for invocation in ("--dry-run", '-c "$WorkingSpec" -v'):
        position = build_implementation.index(invocation)
        block_start = build_implementation[:position].rindex("@echo off")
        assert 'set "VSLANG=1033"' in build_implementation[block_start:position], (
            f"la invocacion con {invocation} deja a MSVC hablando en el idioma del sistema"
        )
