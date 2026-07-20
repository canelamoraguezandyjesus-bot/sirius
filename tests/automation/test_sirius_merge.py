"""Pruebas de ``scripts/automation/sirius_merge_on_command.sh``.

Ejercitan el ejecutor de merge por comentario explícito del propietario con un
``gh`` simulado y con estado (etiquetas, comentarios, PR y check-runs por
número). Sin red ni ``gh`` real. Se omiten en Windows por las mismas razones
documentadas en ``test_sirius_issue.py``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MERGE_SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_merge_on_command.sh"


def _bash_works() -> bool:
    exe = shutil.which("bash")
    if not exe:
        return False
    try:
        proc = subprocess.run(
            [exe, "-c", "echo ok"], capture_output=True, text=True, timeout=30, check=False
        )
    except OSError:
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "ok"


pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or not _bash_works(),
    reason="Requiere un Bash POSIX funcional (no aplica en el runner Windows de Quality).",
)

REPO = "owner/repo"
ISSUE = 60
COMMENT_ID = "111"

# gh simulado con estado por incidencia (labels_N.txt / comments_N.txt /
# body_N.txt) más PR (pr_N.json, ya con forma post-jq: head como SHA plano) y
# check-runs (checks_SHA.txt con la conclusion en texto plano).
_GH_MOCK = r"""#!/usr/bin/env bash
D="$GH_MOCK_DIR"
echo "gh $*" >> "$D/calls.log"
sub="$1"; shift || true

issue_from() { printf '%s' "$1" | grep -oE 'issues/[0-9]+' | head -1 | cut -d/ -f2; }

case "$sub" in
  api)
    args="$*"
    if printf '%s' "$args" | grep -q '/check-runs'; then
      sha="$(printf '%s' "$args" | grep -oE 'commits/[^/]+' | cut -d/ -f2)"
      cat "$D/checks_${sha}.txt" 2>/dev/null || echo "none"
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/pulls/'; then
      pr="$(printf '%s' "$args" | grep -oE 'pulls/[0-9]+' | cut -d/ -f2)"
      if printf '%s' "$args" | grep -q 'draft'; then
        cat "$D/pr_${pr}.json" 2>/dev/null || exit 1
      else
        jq -r '.merged // "false"' "$D/pr_${pr}.json" 2>/dev/null || echo "false"
      fi
      exit 0
    fi
    n="$(issue_from "$args")"
    if printf '%s' "$args" | grep -q '/labels'; then
      cat "$D/labels_${n}.txt" 2>/dev/null; exit 0
    fi
    if printf '%s' "$args" | grep -q '/comments'; then
      if printf '%s' "$args" | grep -q 'reverse'; then
        tac "$D/comments_${n}.txt" 2>/dev/null
      else
        cat "$D/comments_${n}.txt" 2>/dev/null
      fi
      exit 0
    fi
    cat "$D/body_${n}.txt" 2>/dev/null
    exit 0
    ;;
  issue)
    action="$1"; shift || true
    num=""
    for a in "$@"; do case "$a" in [0-9]*) num="$a"; break;; esac; done
    case "$action" in
      view)
        if printf '%s' "$*" | grep -q comments; then cat "$D/comments_${num}.txt" 2>/dev/null
        else cat "$D/body_${num}.txt" 2>/dev/null; fi
        exit 0;;
      comment)
        bf=""; prev=""
        for a in "$@"; do [ "$prev" = "--body-file" ] && bf="$a"; prev="$a"; done
        if [ -n "$bf" ]; then
          cat "$bf" >> "$D/comments_${num}.txt"
          printf '\n' >> "$D/comments_${num}.txt"
        fi
        echo "COMMENT ${num}" >> "$D/actions.log"; exit 0;;
    esac;;
  pr)
    action="$1"; shift || true
    case "$action" in
      merge)
        prnum=""
        for a in "$@"; do case "$a" in [0-9]*) prnum="$a"; break;; esac; done
        echo "MERGE ${prnum}" >> "$D/actions.log"
        if [ "${GH_MOCK_FAIL_MERGE:-0}" = "1" ]; then
          echo "merge failed: required review missing" >&2
          exit 1
        fi
        python3 - "$D/pr_${prnum}.json" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
data["merged"] = True
data["state"] = "closed"
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh)
PY
        if [ "${GH_MOCK_MERGE_REPORTS_FAIL_BUT_WORKS:-0}" = "1" ]; then
          echo "merge failed: transient error after success" >&2
          exit 1
        fi
        exit 0;;
      *) echo "unknown gh pr $action" >&2; exit 2;;
    esac;;
esac
exit 0
"""


def _setup(tmp_path: Path) -> dict[str, str]:
    mock_dir = tmp_path / "mock"
    bin_dir = tmp_path / "bin"
    mock_dir.mkdir()
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(_GH_MOCK, encoding="utf-8")
    gh.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["GH_MOCK_DIR"] = str(mock_dir)
    env["SIRIUS_RETRY_BASE_DELAY"] = "0"
    env["SIRIUS_RETRY_ATTEMPTS"] = "2"
    return env


def _md(env: dict[str, str]) -> Path:
    return Path(env["GH_MOCK_DIR"])


def _run_merge(
    env: dict[str, str], comment_body: str = "fusiona", issue: int = ISSUE
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MERGE_SCRIPT), REPO, str(issue), COMMENT_ID, comment_body],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _seed_issue(
    env: dict[str, str],
    issue: int,
    labels: list[str],
    comments: str = "",
    body: str = "cuerpo",
) -> None:
    md = _md(env)
    (md / f"labels_{issue}.txt").write_text("".join(f"{x}\n" for x in labels), encoding="utf-8")
    (md / f"comments_{issue}.txt").write_text(comments, encoding="utf-8")
    (md / f"body_{issue}.txt").write_text(body, encoding="utf-8")


def _seed_pr(
    env: dict[str, str],
    pr: int,
    *,
    state: str = "open",
    draft: bool = False,
    merged: bool = False,
    mergeable_state: str = "clean",
    head: str = "c4d482267d9a",
) -> None:
    md = _md(env)
    (md / f"pr_{pr}.json").write_text(
        json.dumps(
            {
                "state": state,
                "draft": draft,
                "merged": merged,
                "mergeable_state": mergeable_state,
                "head": head,
            }
        ),
        encoding="utf-8",
    )


def _seed_checks(env: dict[str, str], sha: str, conclusion: str) -> None:
    (_md(env) / f"checks_{sha}.txt").write_text(conclusion, encoding="utf-8")


def _ready_issue(env: dict[str, str], pr: int = 57, head: str = "c4d482267d9a") -> None:
    _seed_issue(
        env,
        ISSUE,
        ["sirius:ready-for-merge"],
        comments=f"APROBADO\n- Head SHA: `{head}`\nhttps://github.com/owner/repo/pull/{pr}\n",
    )
    _seed_pr(env, pr, head=head)
    _seed_checks(env, head, "success")


def _actions(env: dict[str, str]) -> str:
    f = _md(env) / "actions.log"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def _comments(env: dict[str, str], issue: int = ISSUE) -> str:
    f = _md(env) / f"comments_{issue}.txt"
    return f.read_text(encoding="utf-8") if f.exists() else ""


# --------------------------------------------------------------------------- #
# La orden debe ser exacta y la etiqueta debe seguir vigente
# --------------------------------------------------------------------------- #


def test_wrong_keyword_no_action(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _ready_issue(env)
    r = _run_merge(env, comment_body="no fusiones todavia")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MERGE" not in _actions(env)
    assert "COMMENT" not in _actions(env)


def test_keyword_with_surrounding_whitespace_and_case_matches(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _ready_issue(env)
    r = _run_merge(env, comment_body="  FUSIONA  \n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MERGE 57" in _actions(env)


def test_not_ready_for_merge_label_no_action(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(env, ISSUE, ["sirius:reviewing"])
    r = _run_merge(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _actions(env) == ""


# --------------------------------------------------------------------------- #
# Localización de la PR
# --------------------------------------------------------------------------- #


def test_no_pr_found_blocks(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(env, ISSUE, ["sirius:ready-for-merge"], comments="sin PR aqui")
    r = _run_merge(env)
    assert r.returncode != 0
    assert "MERGE" not in _actions(env)
    assert "sirius-merge-blocked:111" in _comments(env)


def test_multiple_prs_blocks(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(
        env,
        ISSUE,
        ["sirius:ready-for-merge"],
        comments="https://github.com/owner/repo/pull/57\nhttps://github.com/owner/repo/pull/58\n",
    )
    r = _run_merge(env)
    assert r.returncode != 0
    assert "MERGE" not in _actions(env)
    assert "varias PR distintas" in _comments(env)


# --------------------------------------------------------------------------- #
# Estado de la PR
# --------------------------------------------------------------------------- #


def test_already_merged_no_action(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _ready_issue(env)
    _seed_pr(env, 57, merged=True, head="c4d482267d9a")
    r = _run_merge(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MERGE" not in _actions(env)
    assert "sirius-merge-blocked" not in _comments(env)


def test_draft_pr_blocks(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _ready_issue(env)
    _seed_pr(env, 57, draft=True, head="c4d482267d9a")
    r = _run_merge(env)
    assert r.returncode != 0
    assert "MERGE" not in _actions(env)
    assert "borrador" in _comments(env)


def test_dirty_mergeable_state_blocks(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _ready_issue(env)
    _seed_pr(env, 57, mergeable_state="dirty", head="c4d482267d9a")
    r = _run_merge(env)
    assert r.returncode != 0
    assert "MERGE" not in _actions(env)
    assert "conflictos" in _comments(env)


# --------------------------------------------------------------------------- #
# Cabeza aprobada y Quality
# --------------------------------------------------------------------------- #


def test_no_approved_head_blocks(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(
        env,
        ISSUE,
        ["sirius:ready-for-merge"],
        comments="https://github.com/owner/repo/pull/57\n",
    )
    _seed_pr(env, 57, head="c4d482267d9a")
    _seed_checks(env, "c4d482267d9a", "success")
    r = _run_merge(env)
    assert r.returncode != 0
    assert "Head SHA" in _comments(env)


def test_stale_head_blocks(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _ready_issue(env, head="aaaaaaaaaaaa")
    _seed_pr(env, 57, head="bbbbbbbbbbbb")  # commits nuevos tras la aprobacion
    r = _run_merge(env)
    assert r.returncode != 0
    assert "MERGE" not in _actions(env)
    assert "commits posteriores" in _comments(env)


def test_quality_not_green_blocks(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _ready_issue(env)
    _seed_checks(env, "c4d482267d9a", "failure")
    r = _run_merge(env)
    assert r.returncode != 0
    assert "MERGE" not in _actions(env)
    assert "Quality no esta en verde" in _comments(env)


# --------------------------------------------------------------------------- #
# Camino feliz y verificación autoritativa del merge
# --------------------------------------------------------------------------- #


def test_happy_path_merges_without_extra_comment(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _ready_issue(env)
    r = _run_merge(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MERGE 57" in _actions(env)
    assert "COMMENT" not in _actions(env)
    pr = json.loads((_md(env) / "pr_57.json").read_text())
    assert pr["merged"] is True


def test_merge_command_fails_but_pr_was_merged_reports_success(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_MERGE_REPORTS_FAIL_BUT_WORKS"] = "1"
    _ready_issue(env)
    r = _run_merge(env)
    assert r.returncode == 0, r.stdout + r.stderr
    pr = json.loads((_md(env) / "pr_57.json").read_text())
    assert pr["merged"] is True
    assert "sirius-merge-blocked" not in _comments(env)


def test_merge_command_genuinely_fails_blocks(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_MERGE"] = "1"
    _ready_issue(env)
    r = _run_merge(env)
    assert r.returncode != 0
    pr = json.loads((_md(env) / "pr_57.json").read_text())
    assert pr["merged"] is False
    assert "required review missing" in _comments(env)


def test_block_comment_is_idempotent_per_comment_id(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(env, ISSUE, ["sirius:ready-for-merge"], comments="sin PR aqui")
    r1 = _run_merge(env)
    assert r1.returncode != 0
    r2 = _run_merge(env)
    assert r2.returncode != 0
    assert _comments(env).count("sirius-merge-blocked:111") == 1
