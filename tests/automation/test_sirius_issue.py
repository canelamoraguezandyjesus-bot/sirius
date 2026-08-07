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

import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
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

# Llamada que se queda esperando la respuesta de GitHub. Es el caso que ningun
# plazo comprobado ENTRE llamadas puede acotar, y el unico que distingue un
# limite real por proceso de uno decorativo.
[ -n "${GH_MOCK_HANG_SECONDS:-}" ] && sleep "$GH_MOCK_HANG_SECONDS"

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
      if [ "${GH_MOCK_COMMENTS_ALWAYS_FAIL:-0}" = "1" ]; then echo "503 comments" >&2; exit 1; fi
      if should_fail comments_fail; then echo "503 comments" >&2; exit 1; fi
      # Falla SOLO a partir de la lectura n+1. Un contador decreciente no sirve
      # para esto: hace fallar las primeras, y aqui hace falta lo contrario —que
      # la deduplicacion inicial funcione y sea la RELECTURA posterior al POST la
      # que caiga—. Sin esta forma, la prueba del caso "no puedo confirmar si el
      # POST llego" pasaria en vacio por la rama de historial ilegible.
      if [ -n "${GH_MOCK_COMMENTS_FAIL_AFTER:-}" ]; then
        cnt=0; [ -f "$D/comments_calls" ] && cnt="$(cat "$D/comments_calls")"
        cnt=$((cnt+1)); echo "$cnt" > "$D/comments_calls"
        if [ "$cnt" -gt "$GH_MOCK_COMMENTS_FAIL_AFTER" ]; then echo "503 comments" >&2; exit 1; fi
      fi
      # La carga se construye con la MISMA forma que devuelve la API REST
      # (`body`, `author_association`, `user.login`) y el filtro `--jq` que trae
      # la llamada se aplica con jq de verdad. Así el filtro de autoría de
      # confianza queda realmente ejercitado: un simulador que devolviera solo
      # los cuerpos haría indistinguible un historial firmado por el
      # propietario de uno sembrado por un tercero, que es exactamente la
      # diferencia que ese filtro existe para detectar.
      filter=""; prev=""
      for a in "$@"; do [ "$prev" = "--jq" ] && filter="$a"; prev="$a"; done
      [ -n "$filter" ] || filter='.[].body'
      python3 "$D/build_comments.py" rest "$comments_file" 2>/dev/null | jq -r "$filter" 2>/dev/null
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/labels'; then
      if [ "${GH_MOCK_FAIL_LABELS_READ:-0}" = "1" ]; then echo "503 labels" >&2; exit 1; fi
      cat "$labels_file" 2>/dev/null
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/pulls/'; then
      # Estado de una PR concreta: se devuelve un JSON con el estado por-PR
      # (archivo pr_state_<N>.txt, "open" por defecto) para poder simular PRs
      # cerradas/superadas. El llamador extrae `.state` con jq.
      pr_num="$(printf '%s' "$args" | grep -oE '/pulls/[0-9]+' | grep -oE '[0-9]+' | head -1)"
      pr_state="open"
      [ -f "$D/pr_state_${pr_num}.txt" ] && pr_state="$(cat "$D/pr_state_${pr_num}.txt")"
      printf '{"state":"%s"}' "$pr_state"
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
          if [ "${GH_MOCK_GRAPHQL_ALWAYS_FAIL:-0}" = "1" ]; then echo "503 graphql" >&2; exit 1; fi
          # Vía de respaldo GraphQL: nombres de campo distintos
          # (`authorAssociation`, `author.login` con prefijo `app/`) y el mismo
          # tratamiento honesto del filtro, para que el respaldo no pueda
          # degradar la garantía sin que una prueba lo note.
          filter=""; prev=""
          for a in "$@"; do [ "$prev" = "--jq" ] && filter="$a"; prev="$a"; done
          [ -n "$filter" ] || filter='.comments[].body'
          python3 "$D/build_comments.py" graphql "$comments_file" 2>/dev/null \
            | jq -r "$filter" 2>/dev/null
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
        # Fallo LIMPIO: la peticion no llega a GitHub, no se escribe nada.
        if should_fail comment_clean; then echo "503 sin aceptar" >&2; exit 1; fi
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
        # Fallo AMBIGUO: GitHub ya ha aceptado la peticion (el comentario queda
        # escrito, arriba) pero la respuesta se pierde y `gh` devuelve error. Es
        # el caso que un reintento ciego convierte en duplicado, y el unico que
        # distingue una recuperacion por relectura de un `sirius_retry`.
        if should_fail comment_ambiguous; then echo "502 tras aceptar" >&2; exit 1; fi
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

# Constructor de la carga de comentarios del `gh` simulado. Cada bloque de
# comments.txt (separados por una línea en blanco) es un comentario. Una primera
# línea `@@untrusted`, `@@collaborator`, `@@member` o `@@bot` fija su autoría;
# sin directiva, el comentario lo firma el propietario de la incidencia.
_BUILD_COMMENTS = """#!/usr/bin/env python3
import json
import os
import sys

shape = sys.argv[1]
try:
    with open(sys.argv[2], encoding="utf-8") as handle:
        raw = handle.read()
except OSError:
    raw = ""

# (author_association, login REST, login GraphQL)
AUTHORS = {
    "@@untrusted": ("NONE", "tercero-cualquiera", "tercero-cualquiera"),
    "@@collaborator": ("COLLABORATOR", "colaborador", "colaborador"),
    "@@member": ("MEMBER", "miembro", "miembro"),
    "@@bot": ("NONE", "github-actions[bot]", "app/github-actions"),
}

chunks = [c for c in raw.split("\\n\\n") if c.strip()]
# Consistencia eventual: la escritura ya ocurrio pero la lectura todavia no la
# refleja. Es el caso que distingue "no llego" de "aun no lo veo", y sin el no se
# puede probar que la recuperacion no republique apoyandose en una ausencia.
if os.environ.get("GH_MOCK_COMMENTS_HIDE_LAST") == "1" and chunks:
    chunks = chunks[:-1]

rest = []
graphql = []
for chunk in chunks:
    association, login, graphql_login = "OWNER", "propietario", "propietario"
    lines = chunk.split("\\n")
    if lines and lines[0].strip() in AUTHORS:
        association, login, graphql_login = AUTHORS[lines[0].strip()]
        chunk = "\\n".join(lines[1:])
    # Los cuerpos reales terminan en salto de línea; conservarlo mantiene la
    # separación por línea en blanco que usa el fichero simulado.
    body = chunk + "\\n"
    rest.append({"body": body, "author_association": association, "user": {"login": login}})
    graphql.append(
        {"body": body, "authorAssociation": association, "author": {"login": graphql_login}}
    )

json.dump(rest if shape == "rest" else {"comments": graphql}, sys.stdout)
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
    (mock_dir / "build_comments.py").write_text(_BUILD_COMMENTS, encoding="utf-8")

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


# --------------------------------------------------------------------------- #
# Localización de PR referenciada (usada por el merge por comentario)
# --------------------------------------------------------------------------- #


def test_find_pr_for_issue_none(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "body_rest.txt").write_text("sin PR aqui", encoding="utf-8")
    r = _run("sirius_find_pr_for_issue owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""


def test_find_pr_for_issue_single_from_comments(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "body_rest.txt").write_text("cuerpo sin PR", encoding="utf-8")
    (_mock_dir(env) / "comments.txt").write_text(
        "READY https://github.com/owner/repo/pull/57\n", encoding="utf-8"
    )
    r = _run("sirius_find_pr_for_issue owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["57"]


def test_find_pr_for_issue_dedups_body_and_comments(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "body_rest.txt").write_text(
        "PR: https://github.com/owner/repo/pull/57\n", encoding="utf-8"
    )
    (_mock_dir(env) / "comments.txt").write_text(
        "READY https://github.com/owner/repo/pull/57\n", encoding="utf-8"
    )
    r = _run("sirius_find_pr_for_issue owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["57"]


def test_find_pr_for_issue_multiple_distinct(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "body_rest.txt").write_text(
        "PR: https://github.com/owner/repo/pull/57\n", encoding="utf-8"
    )
    (_mock_dir(env) / "comments.txt").write_text(
        "https://github.com/owner/repo/pull/58\n", encoding="utf-8"
    )
    r = _run("sirius_find_pr_for_issue owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert sorted(r.stdout.split()) == ["57", "58"]


def test_find_pr_for_issue_excludes_closed(tmp_path: Path) -> None:
    # Una PR cerrada mencionada en comentarios antiguos NO cuenta como vigente.
    env = _setup(tmp_path)
    (_mock_dir(env) / "body_rest.txt").write_text("cuerpo sin PR", encoding="utf-8")
    (_mock_dir(env) / "comments.txt").write_text(
        "PR abierta: https://github.com/owner/repo/pull/57\n", encoding="utf-8"
    )
    (_mock_dir(env) / "pr_state_57.txt").write_text("closed", encoding="utf-8")
    r = _run("sirius_find_pr_for_issue owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""


def test_find_pr_for_issue_keeps_only_open_when_superseded(tmp_path: Path) -> None:
    # Escenario del relanzamiento (incidencia #66): una PR previa cerrada (#71)
    # y una nueva abierta (#73) referenciadas en el historial. Solo debe contar
    # la abierta, sin falso "varias PR".
    env = _setup(tmp_path)
    (_mock_dir(env) / "body_rest.txt").write_text("cuerpo sin PR", encoding="utf-8")
    (_mock_dir(env) / "comments.txt").write_text(
        "PR abierta: https://github.com/owner/repo/pull/71\n"
        "PR abierta: https://github.com/owner/repo/pull/73\n",
        encoding="utf-8",
    )
    (_mock_dir(env) / "pr_state_71.txt").write_text("closed", encoding="utf-8")
    (_mock_dir(env) / "pr_state_73.txt").write_text("open", encoding="utf-8")
    r = _run("sirius_find_pr_for_issue owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["73"]


def test_find_pr_for_issue_ignores_other_repo(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "body_rest.txt").write_text(
        "https://github.com/other/repo/pull/9\n", encoding="utf-8"
    )
    r = _run("sirius_find_pr_for_issue owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""


# --------------------------------------------------------------------------- #
# Extracción de observaciones estructuradas (usada por el corrector)
# --------------------------------------------------------------------------- #


def test_extract_observations_none_when_absent(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "comments.txt").write_text("comentario sin observaciones\n", encoding="utf-8")
    r = _run("sirius_extract_observations owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""


def test_extract_observations_extracts_json_block(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "comments.txt").write_text(
        '## OBSERVACIONES_ESTRUCTURADAS\n```json\n[{"id": "R1"}]\n```\n\n',
        encoding="utf-8",
    )
    r = _run("sirius_extract_observations owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [{"id": "R1"}]


def test_extract_observations_uses_most_recent_round(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    # comments.txt esta en orden cronologico, separado por la linea en blanco
    # que deja `gh issue comment` tras cada publicacion; el mock invierte por
    # bloques (no por linea) para simular la consulta "reverse" real.
    (_mock_dir(env) / "comments.txt").write_text(
        '## OBSERVACIONES_ESTRUCTURADAS\n```json\n[{"id": "R1-old"}]\n```\n\n'
        '## OBSERVACIONES_ESTRUCTURADAS\n```json\n[{"id": "R2-new"}]\n```\n\n',
        encoding="utf-8",
    )
    r = _run("sirius_extract_observations owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [{"id": "R2-new"}]


# --------------------------------------------------------------------------- #
# Filtro de autoría de confianza
# --------------------------------------------------------------------------- #
#
# Toda lectura del historial que gobierna una decisión (observaciones a
# corregir, head que superó Quality, registros de convergencia) pasa por
# `SIRIUS_TRUSTED_AUTHOR_JQ`. Sin estas pruebas el filtro era invisible: el `gh`
# simulado devolvía cuerpos sin autoría, así que un comentario del propietario y
# uno sembrado por un tercero eran indistinguibles y el filtro podía romperse
# —o desaparecer— sin que ninguna prueba se enterara. El simulador aplica ahora
# el filtro real con jq sobre cargas con la forma de la API, de modo que lo que
# se comprueba aquí es el filtro de producción, no una imitación.


def test_untrusted_comment_is_ignored_when_extracting_observations(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "comments.txt").write_text(
        '## OBSERVACIONES_ESTRUCTURADAS\n```json\n[{"id": "LEGITIMA"}]\n```\n\n'
        "@@untrusted\n"
        '## OBSERVACIONES_ESTRUCTURADAS\n```json\n[{"id": "INYECTADA"}]\n```\n\n',
        encoding="utf-8",
    )
    r = _run("sirius_extract_observations owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    # El bloque más reciente es el del tercero: si el filtro no actuara, sería
    # el que ganaría y el corrector trabajaría sobre observaciones inyectadas.
    assert json.loads(r.stdout) == [{"id": "LEGITIMA"}]


def test_bot_comment_is_trusted_when_extracting_observations(tmp_path: Path) -> None:
    # La automatización publica como `github-actions[bot]`, cuyo
    # author_association NO es OWNER: el filtro debe aceptarlo explícitamente o
    # el flujo no podría leer sus propias publicaciones.
    env = _setup(tmp_path)
    (_mock_dir(env) / "comments.txt").write_text(
        '@@bot\n## OBSERVACIONES_ESTRUCTURADAS\n```json\n[{"id": "DE-LA-AUTOMATIZACION"}]\n```\n\n',
        encoding="utf-8",
    )
    r = _run("sirius_extract_observations owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [{"id": "DE-LA-AUTOMATIZACION"}]


@pytest.mark.parametrize("directive", ["@@collaborator", "@@member"])
def test_collaborator_and_member_comments_are_not_trusted(tmp_path: Path, directive: str) -> None:
    # COLLABORATOR y MEMBER pueden comentar sin poder autorizar un merge: el
    # alcance de confianza se limita a quien ya podía autorizarlo.
    env = _setup(tmp_path)
    (_mock_dir(env) / "comments.txt").write_text(
        f'{directive}\n## OBSERVACIONES_ESTRUCTURADAS\n```json\n[{{"id": "AJENA"}}]\n```\n\n',
        encoding="utf-8",
    )
    r = _run("sirius_extract_observations owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""


def test_untrusted_comment_cannot_forge_the_quality_head(tmp_path: Path) -> None:
    # `sirius_scan_text` alimenta `sirius_extract_sha`, que decide qué head se
    # considera revisado. Un tercero no puede fijarlo.
    env = _setup(tmp_path)
    (_mock_dir(env) / "body_rest.txt").write_text("cuerpo sin head", encoding="utf-8")
    (_mock_dir(env) / "comments.txt").write_text(
        "Head SHA: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n\n"
        "@@untrusted\n"
        "Head SHA: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n\n",
        encoding="utf-8",
    )
    out = tmp_path / "scan.txt"
    r = _run(
        f'sirius_scan_text owner/repo 55 "{out}"; sirius_extract_sha "{out}"',
        env,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "a" * 40


def test_untrusted_round_record_is_ignored_when_numbering_rounds(tmp_path: Path) -> None:
    # Un tercero no puede empujar la numeración de rondas hacia adelante (ni
    # hacia atrás): el historial de convergencia solo lo escriben el propietario
    # y la propia automatización.
    env = _setup(tmp_path)
    (_mock_dir(env) / "comments.txt").write_text(
        "<!-- sirius-round:1 -->\n\n@@untrusted\n<!-- sirius-round:99 -->\n\n",
        encoding="utf-8",
    )
    r = _run("sirius_next_round_number owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "2"


def test_graphql_fallback_keeps_the_trusted_author_filter(tmp_path: Path) -> None:
    # Si REST falla y se cae al respaldo GraphQL, la garantía debe seguir en
    # pie: un fallo transitorio no puede abrir la puerta a un historial ajeno.
    env = _setup(tmp_path)
    # Falla la vía REST de COMENTARIOS (no la del cuerpo): es la que obliga a
    # caer al respaldo. Sin esta bandera la prueba pasaría por el camino REST y
    # no comprobaría nada del respaldo.
    env["GH_MOCK_COMMENTS_ALWAYS_FAIL"] = "1"
    (_mock_dir(env) / "comments.txt").write_text(
        "@@bot\n"
        '## OBSERVACIONES_ESTRUCTURADAS\n```json\n[{"id": "DE-LA-AUTOMATIZACION"}]\n```\n\n'
        "@@untrusted\n"
        '## OBSERVACIONES_ESTRUCTURADAS\n```json\n[{"id": "INYECTADA"}]\n```\n\n',
        encoding="utf-8",
    )
    r = _run("sirius_extract_observations owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [{"id": "DE-LA-AUTOMATIZACION"}]


def test_untrusted_marker_does_not_suppress_the_official_comment(tmp_path: Path) -> None:
    # Los marcadores de idempotencia son PREDECIBLES: `sirius-quality:<head>:failure`
    # se deriva del SHA público de la PR. Si la deduplicación mirase comentarios
    # de cualquier autor, un tercero que publicara el marcador antes que el flujo
    # conseguiría que la transición se diera por hecha y omitiese su propio
    # comentario. Solo un marcador de identidad confiable puede suprimirlo.
    env = _setup(tmp_path)
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    (_mock_dir(env) / "comments.txt").write_text(
        f"@@untrusted\n{marker}\ncomentario ajeno que se adelanta\n\n", encoding="utf-8"
    )
    body = _write_body(env, marker)
    r = _run(f'sirius_comment_once owner/repo 55 "{marker}" "{body}"', env)
    assert r.returncode == 0, r.stderr
    assert "COMMENT" in _actions(env)
    assert "## SIRIUS_COMPLETED" in _comments(env)


def test_trusted_marker_still_suppresses_a_duplicate_comment(tmp_path: Path) -> None:
    # La otra mitad de la garantía: filtrar por autor no debe romper la
    # idempotencia real. Un marcador propio sigue impidiendo el duplicado.
    env = _setup(tmp_path)
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    (_mock_dir(env) / "comments.txt").write_text(
        f"{marker}\nregistro oficial ya publicado\n\n", encoding="utf-8"
    )
    body = _write_body(env, marker)
    r = _run(f'sirius_comment_once owner/repo 55 "{marker}" "{body}"', env)
    assert r.returncode == 0, r.stderr
    assert "COMMENT" not in _actions(env)


def test_untrusted_marker_does_not_blind_the_ci_failure_count(tmp_path: Path) -> None:
    # Escenario completo del defecto. `ci_failure_streak` cuenta sobre el volcado
    # de comentarios, que filtra por autor: si un marcador ajeno hubiera bastado
    # para saltarse la publicación del registro oficial, el fallo de Quality no
    # habría existido para la cota y `MAX_CI_FAILURE_STREAK` sería eludible
    # indefinidamente, manteniendo vivo al corrector (que escribe) sin límite.
    env = _setup(tmp_path)
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    (_mock_dir(env) / "comments.txt").write_text(
        f"@@untrusted\n{marker}\nadelantado por un tercero\n\n", encoding="utf-8"
    )
    body = _mock_dir(env).parent / "ci.md"
    body.write_text(f"{marker}\n\n## CI_FAILURE\n- Quality en rojo\n", encoding="utf-8")
    dump = tmp_path / "dump.txt"
    r = _run(
        f'sirius_comment_once owner/repo 55 "{marker}" "{body}" '
        f'&& sirius_dump_comments owner/repo 55 "{dump}"',
        env,
    )
    assert r.returncode == 0, r.stderr
    # El volcado de confianza contiene el fallo exactamente una vez: el ajeno se
    # descarta y el oficial sí llega a publicarse.
    assert dump.read_text(encoding="utf-8").count(marker) == 1
    assert "## CI_FAILURE" in dump.read_text(encoding="utf-8")


def test_untrusted_marker_does_not_skip_a_transition_record(tmp_path: Path) -> None:
    # `sirius_transition` comparte la búsqueda del marcador. Con un marcador
    # ajeno debe comportarse como si no existiera: aplicar la etiqueta Y dejar
    # su propio registro.
    env = _setup(tmp_path)
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    (_mock_dir(env) / "comments.txt").write_text(f"@@untrusted\n{marker}\n\n", encoding="utf-8")
    body = _write_body(env, marker)
    r = _run(_transition_call(marker, body), env)
    assert r.returncode == 0, r.stderr
    assert "COMMENT" in _actions(env)
    assert "## SIRIUS_COMPLETED" in _comments(env)


# --------------------------------------------------------------------------- #
# El POST no es idempotente: recuperación por relectura, no reintento ciego
# --------------------------------------------------------------------------- #


def test_ambiguous_post_failure_does_not_duplicate_the_comment(tmp_path: Path) -> None:
    # El caso que un `sirius_retry` alrededor del POST convertía en duplicado:
    # GitHub acepta la petición —el comentario queda publicado— y la respuesta se
    # pierde, así que `gh` devuelve error. Reintentar publica una segunda copia,
    # y encima autoritativa: la firma la automatización, pasa el filtro de autor
    # y los escáneres deterministas la cuentan. La relectura distingue "no llegó"
    # de "llegó y no me enteré".
    env = _setup(tmp_path)
    (_mock_dir(env) / "comment_ambiguous").write_text("1", encoding="utf-8")
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    body = _write_body(env, marker)
    r = _run(f'sirius_comment_once owner/repo 55 "{marker}" "{body}"', env)
    assert r.returncode == 0, r.stderr
    assert _comments(env).count(marker) == 1, "el comentario se ha publicado dos veces"


def test_ambiguous_post_failure_is_confirmed_by_reread(tmp_path: Path) -> None:
    # El POST llegó y la relectura lo ve: se termina sin republicar. La relectura
    # sirve para confirmar el éxito, que es lo único que puede demostrar.
    env = _setup(tmp_path)
    (_mock_dir(env) / "comment_ambiguous").write_text("1", encoding="utf-8")
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    body = _write_body(env, marker)
    r = _run(f'sirius_comment_once owner/repo 55 "{marker}" "{body}"', env)
    assert r.returncode == 0, r.stderr
    assert _actions(env).count("COMMENT") == 1


def test_a_transient_post_failure_does_not_lose_the_record(tmp_path: Path) -> None:
    # `complete-sirius-after-merge` cierra la incidencia ANTES de publicar y
    # después solo busca incidencias abiertas: un único 5xx sin reintento dejaba
    # la incidencia cerrada y sin registro de forma irrecuperable, porque
    # reejecutar ya no la encuentra. Siendo el duplicado inocuo para los lectores,
    # perder el registro es el daño real y reintentar es lo correcto.
    env = _setup(tmp_path)
    (_mock_dir(env) / "comment_clean").write_text("2", encoding="utf-8")
    marker = "<!-- sirius-completed:abc1234 -->"
    body = _write_body(env, marker)
    r = _run(f'sirius_comment_once owner/repo 55 "{marker}" "{body}"', env)
    assert r.returncode == 0, r.stderr
    assert _comments(env).count(marker) == 1


def test_the_publication_budget_is_a_total_deadline(tmp_path: Path) -> None:
    # La cota es un plazo TOTAL, no un número de intentos por nivel: reutilizar
    # el mismo número en el POST y en las lecturas multiplicaba el presupuesto
    # (~154 s) contra jobs de `timeout-minutes: 5`. Con plazo agotado se para de
    # inmediato, sin depender de cuántos reintentos gasten las lecturas.
    env = _setup(tmp_path)
    (_mock_dir(env) / "comment_clean").write_text("99", encoding="utf-8")
    env["SIRIUS_COMMENT_BUDGET_SECONDS"] = "0"
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    body = _write_body(env, marker)
    r = _run(f'sirius_comment_once owner/repo 55 "{marker}" "{body}"', env)
    assert r.returncode != 0
    # Con el plazo ya vencido para en la primera llamada, que ahora es la lectura
    # de deduplicación: el presupuesto la cubre también, y ese es el arreglo.
    assert "plazo agotado" in r.stderr
    assert _actions(env).count("COMMENT") == 0


def test_the_wait_never_overshoots_the_remaining_budget(tmp_path: Path) -> None:
    # El plazo se comprobaba solo entre esperas, así que una espera exponencial
    # ya iniciada se consumía entera: con 90 s el reloj se miraba a los 62 s,
    # dormía 64 más hasta 126 y aún lanzaba otro POST. El plazo no acotaba nada.
    # Aquí el presupuesto da para una espera corta y la siguiente se recorta, así
    # que el tiempo real no puede rebasarlo de forma apreciable.
    env = _setup(tmp_path)
    (_mock_dir(env) / "comment_clean").write_text("99", encoding="utf-8")
    env["SIRIUS_COMMENT_BUDGET_SECONDS"] = "3"
    env["SIRIUS_RETRY_BASE_DELAY"] = "2"
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    body = _write_body(env, marker)
    inicio = time.monotonic()
    r = _run(f'sirius_comment_once owner/repo 55 "{marker}" "{body}"', env)
    transcurrido = time.monotonic() - inicio
    assert r.returncode != 0
    assert "agotado el plazo" in r.stderr
    # Margen generoso para el arranque de bash y las llamadas al simulador; lo
    # que se comprueba es que no se duerman los 2+4+8… completos por encima del
    # plazo, no una precisión de reloj.
    assert transcurrido < 15, f"la funcion ha rebasado el plazo con creces: {transcurrido:.1f}s"


def test_a_hung_call_cannot_outlive_the_budget(tmp_path: Path) -> None:
    # Ni `gh issue comment` ni las lecturas paginadas tienen límite propio, y `gh`
    # no expone ninguno configurable, así que una llamada bloqueada consumía el
    # resto del job —los workflows que llaman aquí corren con `timeout-minutes: 5`—
    # y la transición se cancelaba antes de la parada controlada. El corte tiene
    # que venir de fuera del proceso.
    env = _setup(tmp_path)
    env["GH_MOCK_HANG_SECONDS"] = "60"
    env["SIRIUS_COMMENT_BUDGET_SECONDS"] = "3"
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    body = _write_body(env, marker)
    inicio = time.monotonic()
    r = _run(f'sirius_comment_once owner/repo 55 "{marker}" "{body}"', env)
    transcurrido = time.monotonic() - inicio
    assert r.returncode != 0
    # Umbral ajustado al presupuesto, no holgado: con `< 30` esta prueba pasaba
    # tardando 18,3 s —seis llamadas de 3 s— porque el límite se calculaba una
    # vez y lo heredaba cada reintento. El aserto flojo ocultaba el defecto que
    # decía cubrir.
    assert transcurrido < 12, (
        f"una llamada colgada ha sobrevivido al plazo: {transcurrido:.1f}s con 3s de "
        "presupuesto; el limite no acota el CONJUNTO de llamadas"
    )


def test_retries_stop_sleeping_once_the_deadline_passed(tmp_path: Path) -> None:
    # Con el plazo vencido, `_sirius_gh` ya no lanza la llamada — pero sin una
    # guarda en `sirius_retry` el bucle seguiría durmiendo sus esperas
    # exponenciales entre intentos inútiles: 2+4+8 por REST y otro tanto por
    # GraphQL, ~28 s gastados DESPUÉS de agotado el presupuesto. Las demás
    # pruebas no lo ven porque fijan la espera base en 0.
    env = _setup(tmp_path)
    env["SIRIUS_RETRY_BASE_DELAY"] = "2"
    inicio = time.monotonic()
    r = _run(
        "export SIRIUS_GH_DEADLINE=1; sirius_read_issue_comments owner/repo 55",
        env,
    )
    transcurrido = time.monotonic() - inicio
    assert r.returncode != 0
    assert transcurrido < 5, f"se han dormido esperas tras vencer el plazo: {transcurrido:.1f}s"


def test_the_deadline_does_not_leak_to_later_calls(tmp_path: Path) -> None:
    # El plazo se exporta; si sobreviviera a la función, acotaría llamadas
    # posteriores con un instante ya vencido y las haría fallar sin motivo.
    env = _setup(tmp_path)
    env["SIRIUS_COMMENT_BUDGET_SECONDS"] = "1"
    (_mock_dir(env) / "comment_clean").write_text("99", encoding="utf-8")
    marker = "<!-- sirius-quality:5b7a0f2:failure -->"
    body = _write_body(env, marker)
    r = _run(
        f'sirius_comment_once owner/repo 55 "{marker}" "{body}" >/dev/null 2>&1; '
        f'echo "plazo=[${{SIRIUS_GH_DEADLINE:-}}]"; '
        f'sirius_read_issue_comments owner/repo 55 >/dev/null && echo "lectura-posterior-ok"',
        env,
    )
    assert "plazo=[]" in r.stdout, f"el plazo se ha escapado: {r.stdout}"
    assert "lectura-posterior-ok" in r.stdout, "una lectura posterior ha quedado acotada de más"


# --------------------------------------------------------------------------- #
# Numeración de rondas
# --------------------------------------------------------------------------- #


def test_next_round_number_starts_at_one_without_history(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    (_mock_dir(env) / "comments.txt").write_text("sin rondas todavia\n", encoding="utf-8")
    r = _run("sirius_next_round_number owner/repo 55", env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "1"


def test_next_round_number_fails_when_history_is_unreadable(tmp_path: Path) -> None:
    # Antes devolvía 1 en este caso: con rondas 1..3 ya publicadas, la ronda
    # siguiente se numeraba otra vez como 1, se colaba al principio del
    # historial ordenado y falseaba la medida de convergencia. Numerar a ciegas
    # es peor que detenerse.
    env = _setup(tmp_path)
    env["GH_MOCK_COMMENTS_ALWAYS_FAIL"] = "1"
    env["GH_MOCK_GRAPHQL_ALWAYS_FAIL"] = "1"
    r = _run("sirius_next_round_number owner/repo 55", env)
    assert r.returncode != 0
    assert r.stdout.strip() == ""


def test_next_round_number_reuses_a_provided_dump(tmp_path: Path) -> None:
    # El llamador que ya leyó el historial no debe releerlo: una segunda lectura
    # abre una ventana en la que falla y la ronda se numeraría a ciegas.
    env = _setup(tmp_path)
    dump = tmp_path / "dump.txt"
    dump.write_text("<!-- sirius-round:4 -->\n", encoding="utf-8")
    env["GH_MOCK_COMMENTS_ALWAYS_FAIL"] = "1"
    env["GH_MOCK_GRAPHQL_ALWAYS_FAIL"] = "1"
    r = _run(f'sirius_next_round_number owner/repo 55 "{dump}"', env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "5"


def test_comment_read_failure_is_reported_without_pipefail(tmp_path: Path) -> None:
    # `_sirius_comments_newest_first` lee y transforma en dos pasos, no en una
    # tubería: encadenados, el estado de salida sería el de `python3` (que
    # siempre acierta) y un 503 de `gh` se convertiría en "no hay comentarios"
    # salvo que el llamador tuviera `pipefail`. Aquí se ejecuta a propósito SIN
    # `pipefail` y con ambas vías caídas: debe fallar, no fingir un historial
    # vacío.
    env = _setup(tmp_path)
    env["GH_MOCK_COMMENTS_ALWAYS_FAIL"] = "1"
    env["GH_MOCK_GRAPHQL_ALWAYS_FAIL"] = "1"
    dump = tmp_path / "dump.txt"
    r = _run(f'sirius_dump_comments owner/repo 55 "{dump}"', env)
    assert r.returncode != 0
    assert "no se pudieron leer los comentarios" in r.stderr
