"""Pruebas de ``scripts/automation/sirius_codex_review.py``.

Ejercitan el disparador idempotente y el recolector del resultado de Codex con
un ``gh`` simulado y con estado (sin red ni ``gh`` real), igual que el resto de
pruebas de automatización. Se omiten en Windows por las mismas razones
documentadas en ``test_sirius_issue.py`` (el runner de Quality no ofrece un
POSIX funcional para los ejecutables simulados en ``PATH``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_codex_review.py"

REPO = "owner/repo"
PR = 9
HEAD = "1234567890abcdef1234567890abcdef12345678"
OTHER_HEAD = "feedfacefeedfacefeedfacefeedfacefeedface"
MARKER = f"<!-- sirius-codex-review:{HEAD} -->"
CONNECTOR = "chatgpt-codex-connector[bot]"
TRIGGER_AT = "2026-08-03T10:00:00Z"
AFTER_TRIGGER = "2026-08-03T10:05:00Z"
BEFORE_TRIGGER = "2026-08-03T09:00:00Z"


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
    reason="Requiere un entorno POSIX funcional (no aplica en el runner Windows de Quality).",
)

# gh simulado con estado en GH_MOCK_DIR: issue_comments.json, reviews.json,
# review_comments_<id>.json y reactions_<id>.json. Un POST de comentario se
# materializa en issue_comments.json y queda registrado en actions.log. El
# archivo fail_remaining.txt permite inyectar fallos transitorios.
_GH_MOCK = """#!/usr/bin/env python3
import json, os, re, sys

d = os.environ["GH_MOCK_DIR"]
args = sys.argv[1:]
with open(os.path.join(d, "calls.log"), "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")

fail_path = os.path.join(d, "fail_remaining.txt")
if os.path.exists(fail_path):
    with open(fail_path, encoding="utf-8") as fh:
        remaining = int(fh.read().strip() or "0")
    if remaining > 0:
        with open(fail_path, "w", encoding="utf-8") as fh:
            fh.write(str(remaining - 1))
        sys.stderr.write("HTTP 503 simulado\\n")
        sys.exit(1)

if not args or args[0] != "api":
    sys.exit(2)
path = args[1]
method = "GET"
if "-X" in args:
    method = args[args.index("-X") + 1]
input_file = None
if "--input" in args:
    input_file = args[args.index("--input") + 1]

base, _, query = path.partition("?")
params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
page = int(params.get("page", "1"))


def load(name):
    full = os.path.join(d, name)
    if not os.path.exists(full):
        return []
    with open(full, encoding="utf-8") as fh:
        return json.load(fh)


def out(obj):
    json.dump(obj, sys.stdout)
    sys.exit(0)


m = re.fullmatch(r"repos/[^/]+/[^/]+/issues/(\\d+)/comments", base)
if m and method == "GET":
    out([] if page > 1 else load("issue_comments.json"))
if m and method == "POST":
    comments = load("issue_comments.json")
    with open(input_file, encoding="utf-8") as fh:
        body = json.load(fh)["body"]
    new = {
        "id": 9000 + len(comments),
        "body": body,
        "created_at": "2026-08-03T10:00:00Z",
        "user": {"login": "canelamoraguezandyjesus-bot"},
    }
    comments.append(new)
    with open(os.path.join(d, "issue_comments.json"), "w", encoding="utf-8") as fh:
        json.dump(comments, fh)
    with open(os.path.join(d, "actions.log"), "a", encoding="utf-8") as fh:
        fh.write(f"POST comment {new['id']}\\n")
    out(new)

m = re.fullmatch(r"repos/[^/]+/[^/]+/pulls/(\\d+)/reviews", base)
if m:
    out([] if page > 1 else load("reviews.json"))

m = re.fullmatch(r"repos/[^/]+/[^/]+/pulls/(\\d+)/reviews/(\\d+)/comments", base)
if m:
    out([] if page > 1 else load(f"review_comments_{m.group(2)}.json"))

m = re.fullmatch(r"repos/[^/]+/[^/]+/issues/comments/(\\d+)/reactions", base)
if m:
    out([] if page > 1 else load(f"reactions_{m.group(1)}.json"))

sys.exit(2)
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
    env["SIRIUS_CODEX_POLL_SECONDS"] = "0"
    return env


def _md(env: dict[str, str]) -> Path:
    return Path(env["GH_MOCK_DIR"])


def _seed(env: dict[str, str], name: str, payload: object) -> None:
    (_md(env) / name).write_text(json.dumps(payload), encoding="utf-8")


def _trigger_comment(
    comment_id: int = 500, head: str = HEAD, created_at: str = TRIGGER_AT
) -> dict[str, Any]:
    return {
        "id": comment_id,
        "body": f"<!-- sirius-codex-review:{head} -->\n\n@codex review\n",
        "created_at": created_at,
        "user": {"login": "canelamoraguezandyjesus-bot"},
    }


def _review(
    review_id: int = 700,
    *,
    author: str = CONNECTOR,
    state: str = "COMMENTED",
    commit_id: str | None = HEAD,
    body: str = "### Codex Review",
    submitted_at: str = AFTER_TRIGGER,
) -> dict[str, Any]:
    review: dict[str, Any] = {
        "id": review_id,
        "state": state,
        "body": body,
        "submitted_at": submitted_at,
        "user": {"login": author},
    }
    if commit_id is not None:
        review["commit_id"] = commit_id
    return review


def _review_comment(
    comment_id: int = 801, path: str = "src/x.py", line: int = 12
) -> dict[str, Any]:
    return {
        "id": comment_id,
        "path": path,
        "line": line,
        "body": "**![P2 Badge](https://img.shields.io/badge/P2-yellow)** No valida la entrada.",
        "html_url": f"https://github.com/{REPO}/pull/{PR}#discussion_r{comment_id}",
    }


def _run_trigger(
    env: dict[str, str], tmp_path: Path, head: str = HEAD
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "trigger",
            "--repo",
            REPO,
            "--pr",
            str(PR),
            "--head",
            head,
            "--state-file",
            str(tmp_path / "state.json"),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _run_collect(
    env: dict[str, str], tmp_path: Path, *, timeout: str = "0", head: str = HEAD
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "collect",
            "--repo",
            REPO,
            "--pr",
            str(PR),
            "--head",
            head,
            "--state-file",
            str(tmp_path / "state.json"),
            "--output",
            str(tmp_path / "codex.json"),
            "--timeout",
            timeout,
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _state(tmp_path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    return data


def _write_state(tmp_path: Path, head: str = HEAD, comment_id: int = 500) -> None:
    (tmp_path / "state.json").write_text(
        json.dumps(
            {
                "repo": REPO,
                "pr": PR,
                "head_sha": head,
                "marker": f"<!-- sirius-codex-review:{head} -->",
                "trigger_comment_id": comment_id,
                "trigger_created_at": TRIGGER_AT,
            }
        ),
        encoding="utf-8",
    )


def _result(tmp_path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((tmp_path / "codex.json").read_text(encoding="utf-8"))
    return data


def _post_count(env: dict[str, str]) -> int:
    log = _md(env) / "actions.log"
    if not log.exists():
        return 0
    return log.read_text(encoding="utf-8").count("POST comment")


# --------------------------------------------------------------------------- #
# Disparador
# --------------------------------------------------------------------------- #


def test_trigger_posts_comment_when_absent(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 1
    state = _state(tmp_path)
    assert state["head_sha"] == HEAD
    assert isinstance(state["trigger_comment_id"], int)
    assert state["trigger_created_at"]
    comments = json.loads((_md(env) / "issue_comments.json").read_text(encoding="utf-8"))
    assert MARKER in comments[0]["body"]
    assert "@codex review" in comments[0]["body"]
    # La solicitud jamás incluye órdenes de corrección sobre la PR.
    assert "address that feedback" not in comments[0]["body"]


def test_trigger_reuses_existing_comment_for_same_head(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed(env, "issue_comments.json", [_trigger_comment(comment_id=555)])
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 0
    assert _state(tmp_path)["trigger_comment_id"] == 555


def test_trigger_does_not_reuse_comment_of_other_head(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed(env, "issue_comments.json", [_trigger_comment(comment_id=555, head=OTHER_HEAD)])
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 1
    assert _state(tmp_path)["trigger_comment_id"] != 555


def test_trigger_is_idempotent_across_reruns(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    r1 = _run_trigger(env, tmp_path)
    r2 = _run_trigger(env, tmp_path)
    assert r1.returncode == 0 and r2.returncode == 0
    assert _post_count(env) == 1


def test_trigger_rejects_abbreviated_head(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    r = _run_trigger(env, tmp_path, head=HEAD[:10])
    assert r.returncode != 0
    assert not (tmp_path / "state.json").exists()


# --------------------------------------------------------------------------- #
# Recolector: aprobaciones explícitas
# --------------------------------------------------------------------------- #


def test_collect_formal_approved_review(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "issue_comments.json", [_trigger_comment()])
    _seed(env, "reviews.json", [_review(state="APPROVED")])
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "APPROVED"
    assert result["reviewed_head_sha"] == HEAD
    assert result["review_id"] == 700
    assert result["observations"] == []


def test_collect_thumbs_up_from_connector_is_approval(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reactions_500.json", [{"content": "+1", "user": {"login": CONNECTOR}}])
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "APPROVED"
    assert result["reviewed_head_sha"] == HEAD
    assert result["trigger_comment_id"] == 500


def test_collect_thumbs_up_from_unknown_user_is_ignored(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reactions_500.json", [{"content": "+1", "user": {"login": "otro-usuario"}}])
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"


def test_collect_eyes_reaction_only_keeps_waiting_until_timeout(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reactions_500.json", [{"content": "eyes", "user": {"login": CONNECTOR}}])
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"


# --------------------------------------------------------------------------- #
# Recolector: revisión con hallazgos
# --------------------------------------------------------------------------- #


def test_collect_review_with_comments_yields_changes_requested(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review()])
    _seed(
        env,
        "review_comments_700.json",
        [_review_comment(802, "src/b.py", 30), _review_comment(801, "src/a.py", 10)],
    )
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "CHANGES_REQUESTED"
    assert result["reviewed_head_sha"] == HEAD
    assert [o["id"] for o in result["observations"]] == ["CODEX-001", "CODEX-002"]
    # Orden determinista por archivo y línea, con severidad y permalink.
    first = result["observations"][0]
    assert first["archivo"] == "src/a.py:10"
    assert first["severidad"] == "P2"
    assert "discussion_r801" in first["prueba"]
    assert "No valida la entrada" in first["problema"]
    assert first["limites_correccion"]
    assert first["criterio_esperado"]


def test_collect_normalized_json_has_stable_shape(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(state="APPROVED")])
    _run_collect(env, tmp_path)
    result = _result(tmp_path)
    assert set(result) == {
        "source",
        "status",
        "reason",
        "reviewed_head_sha",
        "trigger_comment_id",
        "review_id",
        "summary",
        "observations",
    }
    assert result["source"] == "codex"


def test_collect_review_without_own_comments_is_not_changes(tmp_path: Path) -> None:
    # Los comentarios pertenecen a OTRO review ID: la revisión candidata queda
    # ambigua (sin hallazgos propios ni aprobación) y termina en fallo seguro.
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(review_id=700)])
    _seed(env, "review_comments_999.json", [_review_comment()])
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"


# --------------------------------------------------------------------------- #
# Recolector: verificación de autor y de SHA
# --------------------------------------------------------------------------- #


def test_collect_accepts_connector_login_without_bot_suffix(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(author="chatgpt-codex-connector", state="APPROVED")])
    _run_collect(env, tmp_path)
    assert _result(tmp_path)["status"] == "APPROVED"


def test_collect_rejects_unknown_bot(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(author="malicious-bot[bot]", state="APPROVED")])
    _run_collect(env, tmp_path)
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"


def test_collect_accepts_unambiguous_abbreviated_sha_marker(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(
        env,
        "reviews.json",
        [
            _review(
                commit_id=None,
                state="APPROVED",
                body=f"### Codex Review\n\n**Reviewed commit:** `{HEAD[:10]}`",
            )
        ],
    )
    _run_collect(env, tmp_path)
    result = _result(tmp_path)
    assert result["status"] == "APPROVED"
    assert result["reviewed_head_sha"] == HEAD


def test_collect_rejects_wrong_sha(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(commit_id=OTHER_HEAD, state="APPROVED")])
    _run_collect(env, tmp_path)
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "sha-distinto"


def test_collect_rejects_review_without_provable_sha(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(commit_id=None, state="APPROVED", body="sin marcador")])
    _run_collect(env, tmp_path)
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "sha-no-demostrable"


def test_collect_ignores_review_prior_to_trigger(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(state="APPROVED", submitted_at=BEFORE_TRIGGER)])
    _run_collect(env, tmp_path)
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"


# --------------------------------------------------------------------------- #
# Recolector: estado del disparador, timeout y errores transitorios
# --------------------------------------------------------------------------- #


def test_collect_without_state_file_fails_safely(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "sin-disparador"


def test_collect_rejects_state_of_other_head(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path, head=OTHER_HEAD)
    _seed(env, "reviews.json", [_review(state="APPROVED")])
    _run_collect(env, tmp_path)
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "disparador-de-otro-head"


def test_collect_timeout_produces_structured_failure(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"
    # El timeout no publica un segundo disparador para el mismo head.
    assert _post_count(env) == 0


def test_collect_survives_transient_github_error(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(state="APPROVED")])
    (_md(env) / "fail_remaining.txt").write_text("1", encoding="utf-8")
    r = _run_collect(env, tmp_path, timeout="5")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _result(tmp_path)["status"] == "APPROVED"
