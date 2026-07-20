"""Pruebas del reconciliador de estados y de la transición auto-reparadora.

Ejercitan ``scripts/automation/sirius_reconcile.sh`` y la reanudación de
``sirius_transition`` (marcador presente con estado incompleto) con un ``gh``
simulado y con estado. Sin red ni ``gh`` real. Se omiten en Windows por las
mismas razones documentadas en ``test_sirius_issue.py``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RECONCILE = REPO_ROOT / "scripts" / "automation" / "sirius_reconcile.sh"
LIB = REPO_ROOT / "scripts" / "automation" / "sirius_issue.sh"


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

# gh simulado con estado por incidencia (labels_N.txt / state_N.txt /
# comments_N.txt) más PRs (pr_N.json) y check-runs (checks_SHA.txt).
_GH_MOCK = r"""#!/usr/bin/env bash
D="$GH_MOCK_DIR"
echo "gh $*" >> "$D/calls.log"
sub="$1"; shift || true

issue_from() { printf '%s' "$1" | grep -oE 'issues/[0-9]+' | head -1 | cut -d/ -f2; }

case "$sub" in
  api)
    args="$*"
    if printf '%s' "$args" | grep -qE 'issues\?|issues -f|repos/[^ ]+/issues($| -f)'; then
      cat "$D/open_issues.txt" 2>/dev/null; exit 0
    fi
    if printf '%s' "$args" | grep -q '/check-runs'; then
      sha="$(printf '%s' "$args" | grep -oE 'commits/[0-9a-f]+' | cut -d/ -f2)"
      cat "$D/checks_${sha}.txt" 2>/dev/null || echo "none"; exit 0
    fi
    if printf '%s' "$args" | grep -q '/pulls/'; then
      pr="$(printf '%s' "$args" | grep -oE 'pulls/[0-9]+' | cut -d/ -f2)"
      cat "$D/pr_${pr}.json" 2>/dev/null || exit 1; exit 0
    fi
    n="$(issue_from "$args")"
    if printf '%s' "$args" | grep -q '/labels'; then
      cat "$D/labels_${n}.txt" 2>/dev/null; exit 0
    fi
    if printf '%s' "$args" | grep -q '/comments'; then
      cat "$D/comments_${n}.txt" 2>/dev/null; exit 0
    fi
    if printf '%s' "$args" | grep -q '[.]state'; then
      cat "$D/state_${n}.txt" 2>/dev/null || echo open; exit 0
    fi
    cat "$D/body_${n}.txt" 2>/dev/null; exit 0
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
      edit)
        add=""; rem=""; prev=""
        for a in "$@"; do
          [ "$prev" = "--add-label" ] && add="$a"
          [ "$prev" = "--remove-label" ] && rem="$a"
          prev="$a"
        done
        lf="$D/labels_${num}.txt"
        if [ -n "$add" ]; then
          grep -Fxq "$add" "$lf" 2>/dev/null || echo "$add" >> "$lf"
        fi
        if [ -n "$rem" ] && [ -f "$lf" ]; then
          grep -Fxv "$rem" "$lf" > "$lf.tmp" 2>/dev/null; mv "$lf.tmp" "$lf" 2>/dev/null || true
        fi
        exit 0;;
      close)
        if [ "${GH_MOCK_FAIL_CLOSE:-0}" = "1" ]; then echo "close fail" >&2; exit 1; fi
        echo closed > "$D/state_${num}.txt"; echo "CLOSE ${num}" >> "$D/actions.log"; exit 0;;
      comment)
        bf=""; prev=""
        for a in "$@"; do [ "$prev" = "--body-file" ] && bf="$a"; prev="$a"; done
        if [ -n "$bf" ]; then
          cat "$bf" >> "$D/comments_${num}.txt"
          printf '\n' >> "$D/comments_${num}.txt"
        fi
        echo "COMMENT ${num}" >> "$D/actions.log"; exit 0;;
    esac;;
  label)
    action="$1"; shift || true
    case "$action" in
      create) echo "LABEL create $*" >> "$D/actions.log"; exit 0;;
      *) echo "unknown gh label $action" >&2; exit 2;;
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


def _run_reconcile(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(RECONCILE), "owner/repo"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _seed_issue(
    env: dict[str, str],
    num: int,
    labels: list[str],
    comments: str = "",
    body: str = "cuerpo",
) -> None:
    md = _md(env)
    with open(md / "open_issues.txt", "a", encoding="utf-8") as fh:
        fh.write(f"{num}\n")
    (md / f"labels_{num}.txt").write_text("".join(f"{x}\n" for x in labels), encoding="utf-8")
    (md / f"comments_{num}.txt").write_text(comments, encoding="utf-8")
    (md / f"body_{num}.txt").write_text(body, encoding="utf-8")
    (md / f"state_{num}.txt").write_text("open", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Caso A: marcador de completado con cierre a medias (incidencia #50)
# --------------------------------------------------------------------------- #


def test_reconcile_closes_issue_with_completed_marker(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(env, 50, [], comments="<!-- sirius-completed:b649c92faf98 -->\nSIRIUS_COMPLETED\n")
    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CORREGIDO" in r.stdout
    md = _md(env)
    assert "sirius:completed" in (md / "labels_50.txt").read_text()
    assert (md / "state_50.txt").read_text().strip() == "closed"
    # Sin comentarios nuevos: reparación silenciosa.
    actions = (md / "actions.log").read_text() if (md / "actions.log").exists() else ""
    assert "COMMENT" not in actions


def test_reconcile_completed_marker_is_idempotent(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(env, 50, [], comments="<!-- sirius-completed:b649c92faf98 -->\n")
    assert _run_reconcile(env).returncode == 0
    # La incidencia queda cerrada; una segunda pasada no la ve (cerrada) y aunque
    # la viera, las operaciones son idempotentes. Se simula que sigue listada.
    r2 = _run_reconcile(env)
    assert r2.returncode == 0
    md = _md(env)
    actions = (md / "actions.log").read_text() if (md / "actions.log").exists() else ""
    assert "COMMENT" not in actions


def test_reconcile_ambiguous_completed_marker_not_fixed(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(
        env,
        61,
        ["sirius:failed-safely"],
        comments="<!-- sirius-completed:abc1234:ambiguous -->\n",
    )
    r = _run_reconcile(env)
    assert r.returncode == 0
    md = _md(env)
    assert (md / "state_61.txt").read_text().strip() == "open"
    assert "CORREGIDO" not in r.stdout


# --------------------------------------------------------------------------- #
# Caso B: ci-pending con Quality verde perdido
# --------------------------------------------------------------------------- #


def _seed_ci_pending(env: dict[str, str], conclusion: str) -> None:
    md = _md(env)
    _seed_issue(
        env,
        55,
        ["sirius:ci-pending"],
        comments="READY https://github.com/owner/repo/pull/57\n",
    )
    (md / "pr_57.json").write_text('{"state":"open","head":"c4d482267d9a"}', encoding="utf-8")
    (md / "checks_c4d482267d9a.txt").write_text(conclusion, encoding="utf-8")


def test_reconcile_ci_pending_with_green_quality_transitions(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_ci_pending(env, "success")
    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CORREGIDO" in r.stdout
    md = _md(env)
    labels = (md / "labels_55.txt").read_text()
    assert "sirius:review-requested" in labels
    assert "sirius:ci-pending" not in labels
    assert "sirius-quality:c4d482267d9a:success" in (md / "comments_55.txt").read_text()


def test_reconcile_ci_pending_without_result_reports_only(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_ci_pending(env, "none")
    r = _run_reconcile(env)
    assert r.returncode == 0
    md = _md(env)
    labels = (md / "labels_55.txt").read_text()
    assert "sirius:ci-pending" in labels
    assert "sirius:review-requested" not in labels
    assert "CORREGIDO" not in r.stdout


def test_reconcile_ci_pending_with_failed_quality_reports_only(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_ci_pending(env, "failure")
    r = _run_reconcile(env)
    assert r.returncode == 0
    labels = (_md(env) / "labels_55.txt").read_text()
    assert "sirius:ci-pending" in labels
    assert "CORREGIDO" not in r.stdout


# --------------------------------------------------------------------------- #
# Contradicciones y estados que esperan humanos: solo informe
# --------------------------------------------------------------------------- #


def test_reconcile_multiple_state_labels_reports_contradiction(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(env, 62, ["sirius:ci-pending", "sirius:reviewing"])
    r = _run_reconcile(env)
    assert r.returncode == 0
    assert "CONTRADICCION" in r.stdout
    labels = (_md(env) / "labels_62.txt").read_text()
    assert "sirius:ci-pending" in labels and "sirius:reviewing" in labels


def test_reconcile_blocked_decision_reports_human(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_issue(env, 55, ["sirius:blocked-decision"])
    r = _run_reconcile(env)
    assert r.returncode == 0
    assert "HUMANO" in r.stdout
    assert "CORREGIDO" not in r.stdout


# --------------------------------------------------------------------------- #
# Transición auto-reparadora: marcador presente con estado incompleto
# --------------------------------------------------------------------------- #


def _run_lib(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f"source '{LIB}'\n{script}"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_transition_resumes_when_marker_present_but_state_incomplete(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    md = _md(env)
    marker = "<!-- sirius-completed:abc1234 -->"
    _seed_issue(env, 50, ["sirius:ci-pending"], comments=f"{marker}\n")
    body = tmp_path / "b.md"
    body.write_text(f"{marker}\n\ncuerpo\n", encoding="utf-8")
    r = _run_lib(
        f'sirius_transition owner/repo 50 "{marker}" "{body}" '
        f'"sirius:completed" "006B75" "d" "close" "sirius:ci-pending"',
        env,
    )
    assert r.returncode == 0, r.stderr
    labels = (md / "labels_50.txt").read_text()
    assert "sirius:completed" in labels
    assert "sirius:ci-pending" not in labels
    assert (md / "state_50.txt").read_text().strip() == "closed"
    # El marcador ya existía: no se duplica el comentario.
    assert (md / "comments_50.txt").read_text().count(marker) == 1


def test_transition_verified_marker_short_circuits(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    md = _md(env)
    marker = "<!-- sirius-completed:abc1234 -->"
    _seed_issue(env, 50, ["sirius:completed"], comments=f"{marker}\n")
    (md / "state_50.txt").write_text("closed", encoding="utf-8")
    body = tmp_path / "b.md"
    body.write_text(f"{marker}\n", encoding="utf-8")
    r = _run_lib(
        f'sirius_transition owner/repo 50 "{marker}" "{body}" '
        f'"sirius:completed" "006B75" "d" "close" ""',
        env,
    )
    assert r.returncode == 0, r.stderr
    actions = (md / "actions.log").read_text() if (md / "actions.log").exists() else ""
    assert "COMMENT" not in actions and "CLOSE" not in actions
