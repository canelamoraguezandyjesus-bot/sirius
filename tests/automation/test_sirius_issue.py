"""Pruebas funcionales de la biblioteca de E/S robusta ``sirius_issue.sh``.

Se ejercita la biblioteca real con un ``gh`` simulado y con estado (etiquetas,
estado de la incidencia y comentarios) en el ``PATH``. No requiere red ni el
``gh`` real.

La biblioteca es Bash y solo se ejecuta en los runners Linux de los workflows y
en las Routines. Estas pruebas se aíslan a un Bash POSIX funcional: el runner
Windows de Quality expone ``bash.exe`` de WSL sin distribución instalada, por lo
que aquí se omiten (la cobertura se mantiene en Linux, donde la biblioteca corre).
El validador estructural (Python puro) se prueba aparte y sí corre en todas las
plataformas.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "scripts" / "automation" / "sirius_issue.sh"


def _bash_works() -> bool:
    """True solo si hay un Bash POSIX funcional (no el stub de WSL en Windows)."""
    exe = shutil.which("bash")
    if not exe:
        return False
    try:
        proc = subprocess.run(
            [exe, "-c", "echo sirius-bash-ok"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "sirius-bash-ok"


# La biblioteca es Bash y solo se ejecuta en los runners Linux de los workflows y
# en las Routines. En Windows (runner de Quality) se omite el módulo completo:
# `bash` resuelve al stub de WSL sin distribución y estas pruebas no aplican.
pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or not _bash_works(),
    reason="Requiere un Bash POSIX funcional (no aplica en el runner Windows de Quality).",
)

# gh simulado con estado: emula las llamadas de la biblioteca y mantiene
# labels.txt, state.txt y comments.txt para poder verificar atomicidad e
# idempotencia de las transiciones.
_GH_MOCK = r"""#!/usr/bin/env bash
D="$GH_MOCK_DIR"
echo "$*" >> "$D/calls.log"
sub="$1"; shift || true

labels_file="$D/labels.txt"
state_file="$D/state.txt"
comments_file="$D/comments.txt"
[ -f "$state_file" ] || echo "open" > "$state_file"

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
        tac "$comments_file" 2>/dev/null
      else
        cat "$comments_file" 2>/dev/null
      fi
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/labels'; then
      if [ "${GH_MOCK_FAIL_LABELS_READ:-0}" = "1" ]; then echo "503 labels" >&2; exit 1; fi
      cat "$labels_file" 2>/dev/null
      exit 0
    fi
    if printf '%s' "$args" | grep -q '[.]state'; then
      cat "$state_file"
      exit 0
    fi
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
            tac "$comments_file" 2>/dev/null
          else
            cat "$comments_file" 2>/dev/null
          fi
        else
          if should_fail graphql_fail; then echo "503 graphql" >&2; exit 1; fi
          cat "$D/body_graphql.txt" 2>/dev/null
        fi
        exit 0
        ;;
      edit)
        add=""; rem=""; prev=""
        for a in "$@"; do
          [ "$prev" = "--add-label" ] && add="$a"
          [ "$prev" = "--remove-label" ] && rem="$a"
          prev="$a"
        done
        if [ -n "$add" ]; then
          if [ "${GH_MOCK_FAIL_ADD:-0}" = "1" ]; then echo "add fail" >&2; exit 1; fi
          grep -Fxq "$add" "$labels_file" 2>/dev/null || echo "$add" >> "$labels_file"
        fi
        if [ -n "$rem" ]; then
          if [ "${GH_MOCK_FAIL_REMOVE:-0}" = "1" ]; then echo "remove fail" >&2; exit 1; fi
          if [ -f "$labels_file" ]; then
            grep -Fxv "$rem" "$labels_file" > "$labels_file.tmp" 2>/dev/null
            mv "$labels_file.tmp" "$labels_file" 2>/dev/null || true
          fi
        fi
        exit 0
        ;;
      close)
        if [ "${GH_MOCK_FAIL_CLOSE:-0}" = "1" ]; then echo "close fail" >&2; exit 1; fi
        echo "closed" > "$state_file"
        echo "CLOSE" >> "$D/actions.log"
        exit 0
        ;;
      comment)
        bf=""; btext=""; prev=""
        for a in "$@"; do
          [ "$prev" = "--body-file" ] && bf="$a"
          [ "$prev" = "--body" ] && btext="$a"
          prev="$a"
        done
        if [ -n "$bf" ]; then
          cat "$bf" >> "$comments_file"; printf '\n' >> "$comments_file"
        elif [ -n "$btext" ]; then
          printf '%s\n' "$btext" >> "$comments_file"
        fi
        echo "COMMENT" >> "$D/actions.log"
        exit 0
        ;;
      *)
        echo "$action $*" >> "$D/actions.log"; exit 0
        ;;
    esac
    ;;
  label)
    action="$1"; shift || true
    case "$action" in
      create)
        # Modela `gh label create [--force]`: upsert cuando lleva --force.
        if [ "${GH_MOCK_FAIL_ENSURE:-0}" = "1" ]; then echo "ensure fail" >&2; exit 1; fi
        echo "label create $*" >> "$D/actions.log"; exit 0
        ;;
      *)
        # gh no tiene `gh label view`; cualquier otro subcomando es desconocido.
        echo "unknown gh label subcommand: $action" >&2; exit 2
        ;;
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

_MARKER = "<!-- sirius-completed:abc1234 -->"


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
    env["SIRIUS_RETRY_ATTEMPTS"] = "3"
    return env


def _mock_dir(env: dict[str, str]) -> Path:
    return Path(env["GH_MOCK_DIR"])


def _run(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    full = f"source '{LIB}'\n" + textwrap.dedent(script)
    return subprocess.run(
        ["bash", "-c", full], capture_output=True, text=True, env=env, check=False
    )


def _transition_call(
    marker: str, body_file: Path, close: str = "noclose", removes: str = ""
) -> str:
    return (
        f'sirius_transition owner/repo 55 "{marker}" "{body_file}" '
        f'"sirius:completed" "006B75" "desc" "{close}" "{removes}"'
    )


def _write_body(env: dict[str, str], marker: str) -> Path:
    body = _mock_dir(env).parent / "tbody.md"
    body.write_text(f"{marker}\n\n## SIRIUS_COMPLETED\n- ok\n", encoding="utf-8")
    return body


def _comments(env: dict[str, str]) -> str:
    f = _mock_dir(env) / "comments.txt"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def _actions(env: dict[str, str]) -> str:
    f = _mock_dir(env) / "actions.log"
    return f.read_text(encoding="utf-8") if f.exists() else ""


# --------------------------------------------------------------------------- #
# Lectura robusta
# --------------------------------------------------------------------------- #


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
    (_mock_dir(env) / "graphql_fail").write_text("99", encoding="utf-8")
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
    assert out.read_text(encoding="utf-8").rstrip("\n") == _COMPLETE_BODY.rstrip("\n")


def test_workitem_all_truncated_fails(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    md = _mock_dir(env)
    (md / "body_rest.txt").write_text(_TRUNCATED_BODY, encoding="utf-8")
    (md / "body_graphql.txt").write_text(_TRUNCATED_BODY, encoding="utf-8")
    out = tmp_path / "out.md"
    r = _run(f"sirius_read_workitem_body owner/repo 55 '{out}'", env)
    assert r.returncode != 0


# --------------------------------------------------------------------------- #
# Escritura verificada
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# Etiquetas y SHA
# --------------------------------------------------------------------------- #


def test_ensure_label_upserts_via_force(tmp_path: Path) -> None:
    # Regresión (#55): ensure_label debe usar `gh label create --force` (upsert) y
    # NO `gh label view` (subcomando inexistente que hacía fallar la transición
    # cuando la etiqueta ya existía).
    env = _setup(tmp_path)
    r = _run("sirius_ensure_label owner/repo sirius:review-requested 8250DF desc", env)
    assert r.returncode == 0, r.stderr
    actions = _actions(env)
    assert "label create" in actions
    assert "--force" in actions
    calls = (_mock_dir(env) / "calls.log").read_text()
    assert "label view" not in calls  # nunca debe invocarse `gh label view`


def test_ensure_label_fails_returns_error(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_ENSURE"] = "1"
    r = _run("sirius_ensure_label owner/repo sirius:completed 006B75 desc", env)
    assert r.returncode != 0


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


# --------------------------------------------------------------------------- #
# set_labels / close: idempotencia y verificación
# --------------------------------------------------------------------------- #


def test_set_labels_success_and_verified(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "labels.txt").write_text("sirius:ci-pending\n", encoding="utf-8")
    r = _run("sirius_set_issue_labels owner/repo 55 sirius:review-requested sirius:ci-pending", env)
    assert r.returncode == 0, r.stderr
    labels = (_mock_dir(env) / "labels.txt").read_text()
    assert "sirius:review-requested" in labels
    assert "sirius:ci-pending" not in labels


def test_set_labels_fails_when_add_fails(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_ADD"] = "1"
    (_mock_dir(env) / "labels.txt").write_text("sirius:ci-pending\n", encoding="utf-8")
    r = _run("sirius_set_issue_labels owner/repo 55 sirius:review-requested sirius:ci-pending", env)
    assert r.returncode != 0  # la etiqueta no quedó aplicada


def test_set_labels_fails_when_remove_fails(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_REMOVE"] = "1"
    (_mock_dir(env) / "labels.txt").write_text("sirius:ci-pending\n", encoding="utf-8")
    r = _run("sirius_set_issue_labels owner/repo 55 sirius:review-requested sirius:ci-pending", env)
    assert r.returncode != 0  # la etiqueta anterior no se retiró


def test_close_idempotent_when_already_closed(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_CLOSE"] = "1"  # el comando close falla...
    (_mock_dir(env) / "state.txt").write_text("closed", encoding="utf-8")  # ...pero ya está cerrada
    r = _run("sirius_close_issue owner/repo 55", env)
    assert r.returncode == 0, r.stderr


def test_close_fails_when_still_open(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_CLOSE"] = "1"
    (_mock_dir(env) / "state.txt").write_text("open", encoding="utf-8")
    r = _run("sirius_close_issue owner/repo 55", env)
    assert r.returncode != 0


# --------------------------------------------------------------------------- #
# Atomicidad de la transición: sin marcador tras un fallo; reintento correcto
# --------------------------------------------------------------------------- #


def test_transition_stops_and_no_marker_when_ensure_label_fails(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_ENSURE"] = "1"
    body = _write_body(env, _MARKER)
    r = _run(_transition_call(_MARKER, body, close="close", removes="sirius:ci-pending"), env)
    assert r.returncode != 0
    assert _MARKER not in _comments(env)
    assert "COMMENT" not in _actions(env)


def test_transition_stops_and_no_marker_when_add_label_fails(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_ADD"] = "1"
    body = _write_body(env, _MARKER)
    r = _run(_transition_call(_MARKER, body, removes="sirius:ci-pending"), env)
    assert r.returncode != 0
    assert _MARKER not in _comments(env)
    assert "COMMENT" not in _actions(env)


def test_transition_stops_and_no_marker_when_remove_label_fails(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_REMOVE"] = "1"
    (_mock_dir(env) / "labels.txt").write_text("sirius:ci-pending\n", encoding="utf-8")
    body = _write_body(env, _MARKER)
    r = _run(_transition_call(_MARKER, body, removes="sirius:ci-pending"), env)
    assert r.returncode != 0
    assert _MARKER not in _comments(env)
    assert "COMMENT" not in _actions(env)


def test_transition_stops_and_no_marker_when_close_fails(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["GH_MOCK_FAIL_CLOSE"] = "1"
    body = _write_body(env, _MARKER)
    r = _run(_transition_call(_MARKER, body, close="close", removes="sirius:ci-pending"), env)
    assert r.returncode != 0
    assert _MARKER not in _comments(env)
    assert "COMMENT" not in _actions(env)


def test_transition_success_then_marker_present(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    body = _write_body(env, _MARKER)
    r = _run(_transition_call(_MARKER, body, close="close", removes="sirius:ci-pending"), env)
    assert r.returncode == 0, r.stderr
    assert _MARKER in _comments(env)
    assert (_mock_dir(env) / "state.txt").read_text().strip() == "closed"


def test_transition_retry_completes_after_earlier_failure(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    body = _write_body(env, _MARKER)
    # 1er intento: el cierre falla -> transición detenida, sin marcador.
    env_fail = dict(env)
    env_fail["GH_MOCK_FAIL_CLOSE"] = "1"
    r1 = _run(_transition_call(_MARKER, body, close="close", removes="sirius:ci-pending"), env_fail)
    assert r1.returncode != 0
    assert _MARKER not in _comments(env)
    # 2º intento (mismo estado, sin el fallo): completa y publica el marcador.
    r2 = _run(_transition_call(_MARKER, body, close="close", removes="sirius:ci-pending"), env)
    assert r2.returncode == 0, r2.stderr
    assert _MARKER in _comments(env)


def test_transition_idempotent_no_duplicate_after_success(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    body = _write_body(env, _MARKER)
    r1 = _run(_transition_call(_MARKER, body, close="close", removes="sirius:ci-pending"), env)
    assert r1.returncode == 0, r1.stderr
    r2 = _run(_transition_call(_MARKER, body, close="close", removes="sirius:ci-pending"), env)
    assert r2.returncode == 0, r2.stderr
    # El marcador aparece una sola vez y solo se publicó un comentario.
    assert _comments(env).count(_MARKER) == 1
    assert _actions(env).count("COMMENT") == 1
