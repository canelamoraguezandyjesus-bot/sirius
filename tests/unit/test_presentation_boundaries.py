"""Architectural guardrail: presentation must never import SQLite/SQLAlchemy directly.

AGENTS.md: "No accedas a SQLite, OpenAI o secretos desde la interfaz." This is
enforced here by parsing the import statements of every module in
``sirius.presentation`` and asserting none of them reference SQLAlchemy, the
persistence adapters, or an LLM provider adapter.
"""

from __future__ import annotations

import ast
from pathlib import Path

_PRESENTATION_DIR = Path(__file__).resolve().parents[2] / "src" / "sirius" / "presentation"

_FORBIDDEN_MODULE_PREFIXES = (
    "sqlalchemy",
    "sirius.adapters.persistence",
    "sirius.adapters.llm",
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


def test_presentation_never_imports_persistence_or_sqlalchemy_directly() -> None:
    presentation_files = sorted(_PRESENTATION_DIR.glob("*.py"))
    assert presentation_files, "expected to find presentation source files"

    offenders: dict[str, set[str]] = {}
    for source_path in presentation_files:
        imported = _imported_module_names(source_path)
        forbidden = {
            name
            for name in imported
            if any(name.startswith(prefix) for prefix in _FORBIDDEN_MODULE_PREFIXES)
        }
        if forbidden:
            offenders[source_path.name] = forbidden

    assert offenders == {}
