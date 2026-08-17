"""Frontera comprobable entre ``sirius`` y ``sirius_engine`` (ADR-020, incidencia #177 §10).

"El código del motor vive en ``src/sirius_engine/``: fuera de
``src/sirius/`` (frontera aprobada) [...] con prueba de frontera que
prohíbe importaciones entre ``sirius`` y ``sirius_engine`` en ambos
sentidos." Mirrors ``tests/unit/test_application_boundaries.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[2] / "src"
_SIRIUS_DIR = _SRC_DIR / "sirius"
_SIRIUS_ENGINE_DIR = _SRC_DIR / "sirius_engine"


def _imported_module_names(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


def _forbidden_imports(directory: Path, *, forbidden_package: str) -> dict[str, set[str]]:
    offenders: dict[str, set[str]] = {}
    for source_path in sorted(directory.rglob("*.py")):
        imported = _imported_module_names(source_path)
        forbidden = {
            name
            for name in imported
            if name == forbidden_package or name.startswith(f"{forbidden_package}.")
        }
        if forbidden:
            offenders[str(source_path.relative_to(directory))] = forbidden
    return offenders


def test_sirius_never_imports_sirius_engine() -> None:
    assert _SIRIUS_DIR.is_dir(), "expected to find src/sirius"
    offenders = _forbidden_imports(_SIRIUS_DIR, forbidden_package="sirius_engine")
    assert offenders == {}


def test_sirius_engine_never_imports_sirius() -> None:
    assert _SIRIUS_ENGINE_DIR.is_dir(), "expected to find src/sirius_engine"
    offenders = _forbidden_imports(_SIRIUS_ENGINE_DIR, forbidden_package="sirius")
    assert offenders == {}
