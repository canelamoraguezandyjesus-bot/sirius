"""Pruebas funcionales de la biblioteca de E/S robusta ``sirius_issue.sh``.

Se ejercita la biblioteca real con un ``gh`` simulado en el ``PATH`` cuyo
comportamiento (fallos 5xx, cuerpos truncados, respaldo GraphQL, escritura
corrupta, etc.) se controla mediante variables de entorno y archivos de estado.
No requiere acceso de red ni el ``gh`` real.
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "scripts" / "automation" / "sirius_issue.sh"

# gh simulado: emula exactamente las llamadas que hace la biblioteca.
_GH_MOCK = r"""#!/usr/bin/env bash
D="$GH_MOCK_DIR"
echo "$*" >> "$D/calls.log"
sub="$1"; shift || true

should_fail() {
  local f="$D/$1" c=0
  [ -f "$f" ] && c="$(cat "$f")"
  if [ "${c:-0}" -gt 0 ]; then echo $((c-1)) > "$f"; return 0; fi
  return 1
}

case "$sub" in
  api)
    args="$*"
    if printf '%s' "$args" | grep -q -- '-X PATCH'; then
      inp=""; prev=""
      for a in "$@"; do [ "$prev" = "--input" ] && inp="$a"; prev="$a"; done
      body="$(jq -r '.body' "$inp")"
      if [ "${GH_MOCK_CORRUPT_WRITE:-0}" = "1" ]; then
        printf '%s' "${body:0:15}" > "$D/stored_body.txt"
      else
        printf '%s' "$body" > "$D/stored_body.txt"
      fi
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/comments'; then
      if should_fail comments_fail; then echo "503 comments" >&2; exit 1; fi
      if printf '%s' "$args" | grep -q 'reverse'; then
        tac "$D/comments.txt" 2>/dev/null
      else
        cat "$D/comments.txt" 2>/dev/null
      fi
      exit 0
    fi
    # cuerpo de una incidencia por REST
    if [ "${GH_MOCK_REST_ALWAYS_FAIL:-0}" = "1" ]; then echo "503 rest" >&2; exit 1; fi
    if should_fail rest_fail; then echo "503 rest" >&2; exit 1; fi
    if [ -f "$D/stored_body.txt" ]; then
      cat "$D/stored_body.txt"
    else
      cat "$D/body_rest.txt" 2>/dev/null
    fi
    exit 0
    ;;
  issue)
    action="$1"; shift || true
    case "$action" in
      view)
        if printf '%s' "$*" | grep -q 'comments'; then
          if printf '%s' "$*" | grep -q 'reverse'; then
            tac "$D/comments.txt" 2>/dev/null
          else
            cat "$D/comments.txt" 2>/dev/null
          fi
        else
          if should_fail graphql_fail; then echo "503 graphql" >&2; exit 1; fi
          cat "$D/body_graphql.txt" 2>/dev/null
        fi
        exit 0
        ;;
      comment) echo "comment $*" >> "$D/actions.log"; exit 0 ;;
      *) echo "$action $*" >> "$D/actions.log"; exit 0 ;;
    esac
    ;;
  label)
    action="$1"; shift || true
    case "$action" in
      view) [ "${GH_MOCK_LABEL_EXISTS:-1}" = "1" ] && exit 0 || exit 1 ;;
      *) echo "label $action $*" >> "$D/actions.log"; exit 0 ;;
    esac
    ;;
esac
exit 0
"""

_COMPLETE_BODY = (
    "## Work ID\nSIRIUS-B4F-001\n\n## Bloque\nB4f\n\n## Objetivo\n"
    + ("Integración observable y cierre de B4. " * 8)
    + "\n\n## Base y dependencias\nB4a-B4e fusionados.\n\n## Alcance permitido\nIntegrar.\n\n"
    "## Fuera de alcance\nB5, B6, RAG.\n\n"
    "## Requisitos y pruebas de aceptación\nPA-010 a PA-016.\n\n"
    "## Validaciones obligatorias\n- pytest\n\n## Rama base\nmain\n\n"
    "## Condiciones de parada\nREADY_FOR_REVIEW\n\n## Salvaguardas\nNo merge automático.\n"
)

_TRUNCATED_BODY = "## Work ID\nSIRIUS-B4F-001\n\n## Bloque\nB4f\n\n## Objetivo\nInteg"


def _setup(tmp_path: Path) -> dict[str, str]:
    mock_dir = tmp_path / "mock"
    bin_dir = tmp_path / "bin"
    mock_dir.mkdir()
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(_GH_MOCK, encoding="utf-8")
    gh.chmod(0o755)
    import os

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["GH_MOCK_DIR"] = str(mock_dir)
    env["SIRIUS_RETRY_BASE_DELAY"] = "0"
    env["SIRIUS_RETRY_ATTEMPTS"] = "3"
    return env


def _mock_dir(env: dict[str, str]) -> Path:
    return Path(env["GH_MOCK_DIR"])


def _run(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    full = f"source '{LIB}'\n" + textwrap.dedent(script)
    return subprocess.run(
        ["bash", "-c", full], capture_output=True, text=True, env=env, check=False
    )


def test_primary_rest_read_ok(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "body_rest.txt").write_text("HOLA-REST", encoding="utf-8")
    r = _run("sirius_read_issue_body owner/repo 55", env)
    assert r.returncode == 0
    assert r.stdout == "HOLA-REST"


def test_rest_5xx_then_success_via_retry(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    md = _mock_dir(env)
    (md / "body_rest.txt").write_text("BODY-OK", encoding="utf-8")
    (md / "rest_fail").write_text("2", encoding="utf-8")  # falla 2 veces, éxito al 3er intento
    r = _run("sirius_read_issue_body owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "BODY-OK"
    api_calls = [ln for ln in (md / "calls.log").read_text().splitlines() if ln.startswith("api")]
    assert len(api_calls) == 3


def test_rest_fails_falls_back_to_graphql(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_REST_ALWAYS_FAIL"] = "1"
    md = _mock_dir(env)
    (md / "body_graphql.txt").write_text("BODY-GRAPHQL", encoding="utf-8")
    r = _run("sirius_read_issue_body owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "BODY-GRAPHQL"


def test_all_read_paths_fail_returns_error(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_REST_ALWAYS_FAIL"] = "1"
    md = _mock_dir(env)
    (md / "graphql_fail").write_text("99", encoding="utf-8")
    r = _run("sirius_read_issue_body owner/repo 55", env)
    assert r.returncode != 0


def test_workitem_rejects_truncated_and_uses_graphql(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    md = _mock_dir(env)
    (md / "body_rest.txt").write_text(_TRUNCATED_BODY, encoding="utf-8")
    (md / "body_graphql.txt").write_text(_COMPLETE_BODY, encoding="utf-8")
    out = tmp_path / "out.md"
    r = _run(f"sirius_read_workitem_body owner/repo 55 '{out}'", env)
    assert r.returncode == 0, r.stderr
    # La sustitución de comandos elimina el salto final, igual que GitHub al
    # almacenar el cuerpo; se compara sin el salto de línea final.
    assert out.read_text(encoding="utf-8").rstrip("\n") == _COMPLETE_BODY.rstrip("\n")


def test_workitem_all_truncated_fails(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    md = _mock_dir(env)
    (md / "body_rest.txt").write_text(_TRUNCATED_BODY, encoding="utf-8")
    (md / "body_graphql.txt").write_text(_TRUNCATED_BODY, encoding="utf-8")
    out = tmp_path / "out.md"
    r = _run(f"sirius_read_workitem_body owner/repo 55 '{out}'", env)
    assert r.returncode != 0


def test_write_and_verify_ok(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    src = tmp_path / "src.md"
    src.write_text(_COMPLETE_BODY, encoding="utf-8")
    backup = tmp_path / "backup.md"
    (_mock_dir(env) / "body_rest.txt").write_text("cuerpo anterior", encoding="utf-8")
    r = _run(f"sirius_write_issue_body owner/repo 55 '{src}' '{backup}'", env)
    assert r.returncode == 0, r.stderr
    assert backup.read_text(encoding="utf-8") == "cuerpo anterior"


def test_write_detects_corrupted_readback(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_CORRUPT_WRITE"] = "1"
    src = tmp_path / "src.md"
    src.write_text(_COMPLETE_BODY, encoding="utf-8")
    r = _run(f"sirius_write_issue_body owner/repo 55 '{src}'", env)
    assert r.returncode != 0


def test_write_refuses_truncated_source(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    src = tmp_path / "src.md"
    src.write_text(_TRUNCATED_BODY, encoding="utf-8")
    r = _run(f"sirius_write_issue_body owner/repo 55 '{src}'", env)
    assert r.returncode != 0
    calls = _mock_dir(env) / "calls.log"
    patched = calls.exists() and any("PATCH" in ln for ln in calls.read_text().splitlines())
    assert not patched  # nunca se intenta escribir un cuerpo truncado


def test_ensure_label_creates_when_missing(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_LABEL_EXISTS"] = "0"
    r = _run("sirius_ensure_label owner/repo sirius:completed 006B75 desc", env)
    assert r.returncode == 0, r.stderr
    actions = (_mock_dir(env) / "actions.log").read_text()
    assert "label create" in actions


def test_ensure_label_edits_when_present(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_LABEL_EXISTS"] = "1"
    r = _run("sirius_ensure_label owner/repo sirius:completed 006B75 desc", env)
    assert r.returncode == 0, r.stderr
    actions = (_mock_dir(env) / "actions.log").read_text()
    assert "label edit" in actions


def test_extract_sha_found(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    f = tmp_path / "scan.txt"
    f.write_text("- Merge SHA: `e94d1296c63ed2611c0d0ddc981574ea3c50680f`\n", encoding="utf-8")
    r = _run(f"sirius_extract_sha '{f}'", env)
    assert r.stdout == "e94d1296c63ed2611c0d0ddc981574ea3c50680f"


def test_extract_sha_absent_is_no_head(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    f = tmp_path / "scan.txt"
    f.write_text("sin ningun identificador de commit\n", encoding="utf-8")
    r = _run(f"sirius_extract_sha '{f}'", env)
    assert r.stdout == "no-head"


def test_retry_gives_up_after_attempts(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    r = _run(
        'SIRIUS_RETRY_ATTEMPTS=3 SIRIUS_RETRY_BASE_DELAY=0 sirius_retry false; echo "rc=$?"', env
    )
    assert "rc=1" in r.stdout
