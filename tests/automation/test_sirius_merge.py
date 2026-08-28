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
    if printf '%s' "$args" | grep -q '/compare/'; then
      # Cuantos commits de la base le faltan a la rama. Por defecto 0: al dia.
      cat "$D/behind_by.txt" 2>/dev/null || echo "0"
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/check-runs'; then
      sha="$(printf '%s' "$args" | grep -oE 'commits/[^/]+' | cut -d/ -f2)"
      cat "$D/checks_${sha}.txt" 2>/dev/null || echo "none"
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/pulls/'; then
      pr="$(printf '%s' "$args" | grep -oE 'pulls/[0-9]+' | cut -d/ -f2)"
      if printf '%s' "$args" | grep -q 'draft' || ! printf '%s' "$args" | grep -q -- '--jq'; then
        # Lectura de estado de la PR (jq con 'draft') y resolución por
        # `sirius_find_pr_for_issue` (llamada sin --jq, que ahora comprueba que
        # la PR siga abierta): ambas esperan el JSON completo con `state`.
        cat "$D/pr_${pr}.json" 2>/dev/null || exit 1
      else
        # Relectura de confirmación del merge: `--jq '.merged'`.
        jq -r '.merged // "false"' "$D/pr_${pr}.json" 2>/dev/null || echo "false"
      fi
      exit 0
    fi
    n="$(issue_from "$args")"
    # Las etiquetas vienen del OBJETO de la incidencia (`--jq '.labels[].name'`),
    # no de `/issues/<n>/labels` (ADR-027): se despacha por el FILTRO, porque la
    # ruta ya no distingue esta lectura, y se aplica el `--jq` real del llamador
    # para que un filtro equivocado no pueda pasar en verde.
    filtro_lbl=""; prev=""
    for a in "$@"; do [ "$prev" = "--jq" ] && filtro_lbl="$a"; prev="$a"; done
    if printf '%s' "$filtro_lbl" | grep -q '[.]labels'; then
      cat "$D/labels_${n}.txt" 2>/dev/null \
        | jq -R . | jq -sc '{labels: map(select(length>0) | {name: .})}' | jq -r "$filtro_lbl"
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/comments'; then
      # Una lectura CAIDA no es un historial vacio. Sin esta palanca no habria
      # como probar que el guion ya no publica "no hay PR" ante un 503.
      if [ "${GH_MOCK_FAIL_COMMENTS:-0}" = "1" ]; then echo "503 comments" >&2; exit 1; fi
      if printf '%s' "$args" | grep -q '@json'; then
        python3 -c '
import json, sys
raw = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else ""
for line in raw.splitlines():
    sys.stdout.write(json.dumps({"body": line}) + "\n")
' "$D/comments_${n}.txt" 2>/dev/null
      elif printf '%s' "$args" | grep -q 'reverse'; then
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
        if [ "${GH_MOCK_FAIL_COMMENTS:-0}" = "1" ]; then echo "503 graphql" >&2; exit 1; fi
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
    base: str = "main",
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
                "base": base,
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


def _sembrar_atraso(env: dict[str, str], commits: int) -> None:
    """Cuantos commits de la base le faltan a la rama de la PR."""
    (_md(env) / "behind_by.txt").write_text(f"{commits}\n", encoding="utf-8")


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


def test_la_orden_vale_aunque_lleve_la_firma_que_anade_la_herramienta(tmp_path: Path) -> None:
    """Una firma anexada por el servidor no puede invalidar la orden.

    Quien comenta por API no controla lo que la herramienta le anexa detrás.
    Sin esto, la orden es inescribible por esa via — paso de verdad con
    `continua`, y `fusiona` tenia el mismo hueco. La autorizacion sigue siendo
    del propietario: el workflow exige `author_association == OWNER` y este
    guion lo reverifica por REST.
    """
    env = _setup(tmp_path)
    _ready_issue(env)
    r = _run_merge(
        env,
        comment_body="fusiona\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MERGE" in _actions(env), r.stdout + r.stderr


def test_el_texto_antes_de_la_firma_sigue_invalidando_la_orden(tmp_path: Path) -> None:
    """Control negativo: solo se perdona la firma, no cualquier texto."""
    env = _setup(tmp_path)
    _ready_issue(env)
    r = _run_merge(
        env,
        comment_body="no fusiones todavia\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_",
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MERGE" not in _actions(env)


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
    # Ambas PRs siguen ABIERTAS: solo entonces la referencia doble es una
    # ambigüedad real (una PR cerrada quedaría descartada por el resolutor).
    _seed_pr(env, 57)
    _seed_pr(env, 58)
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


def test_una_lectura_caida_no_se_publica_como_ausencia_de_pr(tmp_path: Path) -> None:
    """El defecto que la #193 destapó, en el guion de fusión.

    `sirius_find_pr_for_issue` se tragaba los fallos y devolvía vacío, así que
    con GitHub degradado el propietario recibía «No he encontrado ninguna PR
    asociada a esta incidencia» estando la PR abierta. Es una afirmación falsa
    publicada como diagnóstico: manda a una persona a buscar un problema que no
    existe, justo cuando lo único que hacía falta era reintentar.

    Ahora la función devuelve 2 y el guion lo distingue (ADR-036).
    """
    env = _setup(tmp_path)
    _ready_issue(env)
    env["GH_MOCK_FAIL_COMMENTS"] = "1"
    r = _run_merge(env)

    assert r.returncode != 0
    assert "MERGE" not in _actions(env), "no puede fusionar nada sin haber leído"
    salida = r.stdout + r.stderr
    assert "No he encontrado ninguna PR" not in salida, (
        "una lectura caída se está reportando como ausencia de PR"
    )
    assert "Reintentable" in salida
    assert "No he podido fusionar" not in _comentarios_publicados(env), (
        "no debe publicar el diagnóstico de la ausencia cuando lo que falló fue la lectura"
    )


def _comentarios_publicados(env: dict[str, str]) -> str:
    return _comments(env)


# --- La rama tiene que estar al dia con la base -------------------------------
#
# `mergeable_state` solo dice `dirty` cuando hay CONFLICTO de git. Una rama
# atrasada sin conflicto sale `clean`, y entonces se fusionaria algo cuyo Quality
# se calculo contra un `main` que ya no existe.


def test_una_rama_atrasada_no_se_fusiona(tmp_path: Path) -> None:
    """Verde contra su propia base no es verde contra la base de verdad.

    Ya pasó: `main` se puso roja tras una tanda de fusiones porque dos ramas,
    verdes por separado, usaban campos incompatibles. Y estuvo a punto de
    repetirse tres veces el 22-08-2026 con números de ADR — ficheros de nombre
    distinto, sin conflicto para git, y `main` con dos ADR del mismo número.
    """
    env = _setup(tmp_path)
    _ready_issue(env)
    _sembrar_atraso(env, 3)
    r = _run_merge(env)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "MERGE" not in _actions(env)
    publicado = _comentarios_publicados(env)
    assert "3 commit(s) por detras" in publicado, publicado
    assert "Update branch" in publicado


def test_una_rama_al_dia_si_se_fusiona(tmp_path: Path) -> None:
    """Control positivo: sin el, la prueba de arriba pasaria con el merge roto."""
    env = _setup(tmp_path)
    _ready_issue(env)
    _sembrar_atraso(env, 0)
    r = _run_merge(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "MERGE" in _actions(env)


def test_si_no_se_puede_leer_el_atraso_se_bloquea_y_se_pide_reintento(tmp_path: Path) -> None:
    """INVERTIDA el 28-08-2026 por H-31 (auditoría externa, autorizada la corrección).

    La versión anterior dejaba SEGUIR con `behind_by` ilegible, con este motivo
    escrito: «el error cae del lado de seguir, porque las otras cinco
    comprobaciones siguen puestas». La auditoría lo impugnó y el argumento
    gana: esta lectura es MATERIAL -decide si el verde de Quality corresponde a
    la base que se va a fusionar- y las demás lecturas materiales del mismo
    guion fallan cerradas. El coste del fail-open ya se pagó una vez: main roja
    tras fusionar dos ramas verdes contra bases viejas.

    Lo que la versión anterior protegía no se pierde: el bloqueo DICE que es
    reintentable, así que un 503 no deja la orden tirada en silencio, la deja
    con la instrucción de repetir `fusiona`.
    """
    env = _setup(tmp_path)
    _ready_issue(env)
    (_md(env) / "behind_by.txt").write_text("null\n", encoding="utf-8")
    r = _run_merge(env)
    assert r.returncode != 0, "con behind_by ilegible la fusión siguió adelante"
    assert "MERGE" not in _actions(env), "se fusionó sin saber si la base estaba al día"
    salida = r.stdout + r.stderr
    assert "reintent" in salida.lower() or "otra vez" in salida.lower(), (
        f"el bloqueo no dice que se puede reintentar: cambiaría un merge colado "
        f"por una orden tirada en silencio. Salida:\n{salida[-600:]}"
    )


def test_un_atraso_ilegible_por_vacio_tambien_bloquea(tmp_path: Path) -> None:
    """La otra forma del mismo fallo: la API ni contesta y la variable queda vacía."""
    env = _setup(tmp_path)
    _ready_issue(env)
    (_md(env) / "behind_by.txt").write_text("\n", encoding="utf-8")
    r = _run_merge(env)
    assert r.returncode != 0
    assert "MERGE" not in _actions(env)
