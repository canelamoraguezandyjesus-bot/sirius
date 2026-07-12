"""Architectural guardrail: application must never import openai or SQLAlchemy.

Mirrors ``test_presentation_boundaries.py``: application orchestrates use
cases through ports only. Only the concrete adapters (``sirius.adapters.*``)
may know about ``openai``, SQLAlchemy, or the SQLite persistence details.
"""

from __future__ import annotations

import ast
from pathlib import Path

_APPLICATION_DIR = Path(__file__).resolve().parents[2] / "src" / "sirius" / "application"

_FORBIDDEN_MODULE_PREFIXES = (
    "sqlalchemy",
    "openai",
    "sirius.adapters",
)


def _imported_module_names(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


def test_application_never_imports_openai_sqlalchemy_or_adapters_directly() -> None:
    application_files = sorted(_APPLICATION_DIR.glob("*.py"))
    assert application_files, "expected to find application source files"

    offenders: dict[str, set[str]] = {}
    for source_path in application_files:
        imported = _imported_module_names(source_path)
        forbidden = {
            name
            for name in imported
            if any(name.startswith(prefix) for prefix in _FORBIDDEN_MODULE_PREFIXES)
        }
        if forbidden:
            offenders[source_path.name] = forbidden

    assert offenders == {}
