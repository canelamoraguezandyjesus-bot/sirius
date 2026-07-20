"""Pruebas del validador estructural del cuerpo de incidencias de Sirius.

Se ejercita el script real como CLI (la misma vía que usa la biblioteca
``scripts/automation/sirius_issue.sh``), sin importar el módulo, para evitar
manipular el ``sys.path`` de mypy.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts" / "automation" / "validate_issue_body.py"

_COMPLETE_BODY = (
    "## Work ID\nSIRIUS-B4F-001\n\n"
    "## Bloque\nB4f\n\n"
    "## Objetivo\n" + ("Integración observable. " * 10) + "\n\n"
    "## Base y dependencias\nB4a-B4e fusionados.\n\n"
    "## Alcance permitido\nIntegrar operaciones aprobadas.\n\n"
    "## Fuera de alcance\nB5, B6, RAG, embeddings.\n\n"
    "## Requisitos y pruebas de aceptación\nPA-010 a PA-016.\n\n"
    "## Validaciones obligatorias\n- `uv run pytest`\n\n"
    "## Rama base\nmain\n\n"
    "## Condiciones de parada\nREADY_FOR_REVIEW\n\n"
    "## Salvaguardas\nNo hacer merge automático.\n"
)


def _run(body: str | None, path: Path) -> subprocess.CompletedProcess[str]:
    if body is not None:
        path.write_text(body, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_complete_body_is_accepted(tmp_path: Path) -> None:
    result = _run(_COMPLETE_BODY, tmp_path / "body.md")
    assert result.returncode == 0, result.stderr


def test_truncated_body_is_rejected(tmp_path: Path) -> None:
    truncated = "## Work ID\nSIRIUS-B4F-001\n\n## Bloque\nB4f\n\n## Objetivo\nInteg"
    result = _run(truncated, tmp_path / "body.md")
    assert result.returncode == 1
    assert "truncado" in result.stderr.lower() or "incompleto" in result.stderr.lower()


def test_missing_single_section_is_rejected(tmp_path: Path) -> None:
    without_safeguards = _COMPLETE_BODY.replace("## Salvaguardas\nNo hacer merge automático.\n", "")
    result = _run(without_safeguards, tmp_path / "body.md")
    assert result.returncode == 1
    assert "salvaguardas" in result.stderr.lower()


def test_empty_body_is_rejected(tmp_path: Path) -> None:
    result = _run("", tmp_path / "body.md")
    assert result.returncode == 1


def test_bold_headings_are_accepted(tmp_path: Path) -> None:
    bold = (
        _COMPLETE_BODY.replace("## Work ID", "**Work ID**")
        .replace("## Objetivo", "**Objetivo**")
        .replace("## Salvaguardas", "**Salvaguardas**")
    )
    result = _run(bold, tmp_path / "body.md")
    assert result.returncode == 0, result.stderr
