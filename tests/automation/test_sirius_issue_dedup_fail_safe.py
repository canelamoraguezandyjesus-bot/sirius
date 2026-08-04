"""Regresiones de deduplicación segura cuando el historial no se puede leer."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "scripts" / "automation" / "sirius_issue.sh"


def _bash_works() -> bool:
    executable = shutil.which("bash")
    if not executable:
        return False
    result = subprocess.run(
        [executable, "-c", "true"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or not _bash_works(),
    reason="Requiere un Bash POSIX funcional.",
)

_GH_MOCK = """#!/usr/bin/env bash
set -u
printf '%s\\n' "$*" >> "$GH_CALLS"

if [ "${1:-}" = "api" ]; then
  exit 1
fi
if [ "${1:-}" = "issue" ] && [ "${2:-}" = "view" ]; then
  exit 1
fi

# Nada que muta estado debe alcanzarse en estas pruebas.
exit 0
"""


def _environment(tmp_path: Path) -> tuple[dict[str, str], Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(_GH_MOCK, encoding="utf-8")
    gh.chmod(0o755)

    calls = tmp_path / "calls.log"
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["GH_CALLS"] = str(calls)
    env["SIRIUS_RETRY_ATTEMPTS"] = "1"
    env["SIRIUS_RETRY_BASE_DELAY"] = "0"
    return env, calls


def _run(command: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f"source '{LIB}'\n{command}"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_comment_once_does_not_publish_when_history_is_unreadable(tmp_path: Path) -> None:
    env, calls = _environment(tmp_path)
    body = tmp_path / "body.md"
    body.write_text("<!-- marker -->\n", encoding="utf-8")

    result = _run(
        f"sirius_comment_once owner/repo 55 '<!-- marker -->' '{body}'",
        env,
    )

    assert result.returncode != 0
    assert "no publico" in result.stderr
    assert "issue comment" not in calls.read_text(encoding="utf-8")


def test_transition_stops_before_mutating_when_history_is_unreadable(
    tmp_path: Path,
) -> None:
    env, calls = _environment(tmp_path)
    body = tmp_path / "body.md"
    body.write_text("<!-- marker -->\n", encoding="utf-8")

    result = _run(
        "sirius_transition owner/repo 55 '<!-- marker -->' "
        f"'{body}' 'sirius:repair-requested' 'FBCA04' 'desc' 'noclose' ''",
        env,
    )

    assert result.returncode != 0
    assert "antes de mutar estado" in result.stderr
    recorded = calls.read_text(encoding="utf-8")
    assert "label create" not in recorded
    assert "issue edit" not in recorded
    assert "issue comment" not in recorded
