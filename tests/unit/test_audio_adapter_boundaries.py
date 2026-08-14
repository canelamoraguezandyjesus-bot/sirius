"""Salvaguarda de arquitectura: QtMultimedia nunca se importa al cargar un módulo.

Hallazgo MS-A02 de la auditoría: ``from PySide6.QtMultimedia import ...`` falla
en Linux con ``ImportError: libpulse.so.0``, y ``quality.yml`` corre en
``ubuntu-latest`` instalando solo ``libegl1``, ``libgl1`` y ``libxkbcommon0``.
Un import a nivel de módulo rompería la recolección de ``pytest`` antes de
ejecutar una sola prueba, aunque todas usen adaptadores simulados, y dejaría el
ciclo atascado en el mismo sitio que el intento anterior de #126.

Esta prueba convierte esa salvaguarda en algo que el CI vigila, en vez de una
convención que se olvida al escribir el siguiente adaptador.
"""

from __future__ import annotations

import ast
from pathlib import Path

_AUDIO_DIR = Path(__file__).resolve().parents[2] / "src" / "sirius" / "adapters" / "audio"
_PRESENTATION_DIR = Path(__file__).resolve().parents[2] / "src" / "sirius" / "presentation"

_LAZY_ONLY_MODULE = "PySide6.QtMultimedia"


def _module_level_imports(source_path: Path) -> set[str]:
    """Módulos importados al cargar el archivo, sin contar los perezosos.

    Se ignora lo que está dentro de una función y lo que vive bajo
    ``if TYPE_CHECKING:``, porque nada de eso se ejecuta al importar.
    """
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    names: set[str] = set()

    def is_type_checking_guard(node: ast.stmt) -> bool:
        if not isinstance(node, ast.If):
            return False
        test = node.test
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"

    def walk(body: list[ast.stmt]) -> None:
        for node in body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue  # perezoso: no se ejecuta al importar
            if is_type_checking_guard(node):
                continue  # solo lo ve el comprobador de tipos
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names.add(node.module)
            elif isinstance(node, ast.ClassDef | ast.If | ast.Try | ast.With):
                walk(node.body)
                walk(getattr(node, "orelse", []))
                walk(getattr(node, "finalbody", []))

    walk(tree.body)
    return names


def _offenders(directory: Path) -> dict[str, set[str]]:
    offenders: dict[str, set[str]] = {}
    for source_path in sorted(directory.rglob("*.py")):
        imported = _module_level_imports(source_path)
        forbidden = {name for name in imported if name.startswith(_LAZY_ONLY_MODULE)}
        if forbidden:
            offenders[source_path.name] = forbidden
    return offenders


def test_audio_adapters_never_import_qtmultimedia_at_module_level() -> None:
    assert _AUDIO_DIR.exists(), "se esperaba encontrar los adaptadores de audio"

    offenders = _offenders(_AUDIO_DIR)

    assert not offenders, (
        "QtMultimedia importado al cargar el módulo: Quality fallaría en Linux "
        f"por falta de libpulse. Muévelo dentro de la función. {offenders}"
    )


def test_presentation_never_imports_qtmultimedia_at_module_level() -> None:
    """La interfaz tampoco: importar la superficie no puede tocar el audio."""
    offenders = _offenders(_PRESENTATION_DIR)

    assert not offenders, f"QtMultimedia importado al cargar la interfaz: {offenders}"


def _all_imports(source_path: Path) -> set[str]:
    """Todo lo que importa el archivo, también dentro de funciones."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


def test_the_fakes_never_touch_qtmultimedia_at_all() -> None:
    """Ni siquiera perezosamente: son los que hacen que la suite corra sin audio."""
    imported = _all_imports(_AUDIO_DIR / "fake.py")

    assert not any(name.startswith(_LAZY_ONLY_MODULE) for name in imported)
