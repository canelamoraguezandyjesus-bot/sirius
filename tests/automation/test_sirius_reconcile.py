"""Pruebas del reconciliador de estados y de la transición auto-reparadora.

Ejercitan ``scripts/automation/sirius_reconcile.sh`` y la reanudación de
``sirius_transition`` (marcador presente con estado incompleto) con un ``gh``
simulado y con estado. Sin red ni ``gh`` real. Se omiten en Windows por las
mismas razones documentadas en ``test_sirius_issue.py``.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

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
    # `gh api` usa GET por defecto, pero cambia a POST en cuanto se le pasa un
    # parametro con `-f`. Todas las llamadas de este script son LECTURAS, asi
    # que un POST es un error del llamador y aqui se comporta como el `gh` real:
    # falla. Sin esto, el simulado devolvia datos alegremente a una peticion que
    # en produccion habria dado 404, y la prueba no medía nada (hallazgo P1 de
    # Codex en la PR #143).
    metodo=""; tiene_f=0; prev=""
    for a in "$@"; do
      [ "$prev" = "-X" ] && metodo="$a"
      case "$a" in -f|--raw-field|-F|--field) tiene_f=1;; esac
      prev="$a"
    done
    [ -z "$metodo" ] && [ "$tiene_f" = 1 ] && metodo="POST"
    [ -z "$metodo" ] && metodo="GET"
    if [ "$metodo" != "GET" ]; then
      echo "gh: HTTP 404 (metodo $metodo sobre un endpoint de solo lectura)" >&2
      exit 1
    fi
    if printf '%s' "$args" | grep -qE 'issues\?|issues -f|repos/[^ ]+/issues($| -f)'; then
      # GitHub falla: 503, 403 por limite de tasa... Sin poder simularlo, el
      # camino en que la pasada entera no comprueba nada no se puede medir.
      if [ "${MOCK_FAIL_LIST:-0}" = "1" ]; then
        echo "gh: HTTP 503 (listado de incidencias)" >&2; exit 1
      fi
      cat "$D/open_issues.txt" 2>/dev/null; exit 0
    fi
    if printf '%s' "$args" | grep -q '/check-runs'; then
      sha="$(printf '%s' "$args" | grep -oE 'commits/[0-9a-f]+' | cut -d/ -f2)"
      cat "$D/checks_${sha}.txt" 2>/dev/null || echo "none"; exit 0
    fi
    if printf '%s' "$args" | grep -q '/pulls/'; then
      pr="$(printf '%s' "$args" | grep -oE 'pulls/[0-9]+' | cut -d/ -f2)"
      [ -f "$D/pr_${pr}.json" ] || exit 1
      # Se aplica el `--jq` REAL, igual que con /events. Devolver el fichero
      # entero hacia que un campo que el llamador YA NO PIDE siguiera llegandole:
      # quitar `draft` del filtro no cambiaba nada y la prueba pasaba con el
      # defecto puesto. Un simulado mas permisivo que `gh` deja pasar cualquier
      # suposicion, que es la raiz de varios defectos de esta PR.
      jqpr=""; prev=""
      for a in "$@"; do [ "$prev" = "--jq" ] && jqpr="$a"; prev="$a"; done
      if [ -n "$jqpr" ]; then jq -c "$jqpr" "$D/pr_${pr}.json"; else cat "$D/pr_${pr}.json"; fi
      exit 0
    fi
    n="$(issue_from "$args")"
    if printf '%s' "$args" | grep -q '/events'; then
      raw="$D/events_${n}.txt"
      if [ "${MOCK_FAIL_EVENTS:-0}" = "1" ]; then
        echo "gh: HTTP 403 (rate limit) al leer eventos" >&2; exit 1
      fi
      [ -f "$raw" ] || exit 1
      # El archivo guarda un array de PAGINAS. `gh --paginate` emite un
      # documento JSON por pagina, y `--slurp` emite un unico array con todas.
      # Modelar eso importa: con `--paginate` a secas, `--jq` se aplica a cada
      # pagina por separado y `last` da el ultimo de CADA una (hallazgo P2).
      if printf '%s' "$args" | grep -q -- '--slurp'; then
        entrada="$(cat "$raw")"
      else
        entrada="$(jq -c '.[]' "$raw")"
      fi
      # Se aplica el `--jq` REAL del llamador. Si el simulado devolviera la
      # linea ya filtrada, el filtro —que es donde puede estar el defecto— no
      # quedaria medido por ninguna prueba.
      jqprog=""; prev=""
      for a in "$@"; do [ "$prev" = "--jq" ] && jqprog="$a"; prev="$a"; done
      if [ -n "$jqprog" ]; then printf '%s' "$entrada" | jq -r "$jqprog"
      else printf '%s' "$entrada"; fi
      exit 0
    fi
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
          # Se registra CADA adicion, no solo el estado final: retirar y volver
          # a poner una etiqueta genera un evento nuevo —arranca trabajo— y deja
          # el estado final identico. Mirando solo el resultado, invisible
          # (hallazgo P2 de Codex en la PR #146).
          echo "${num} ${add}" >> "$D/added_labels.log"
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


def _seed_ci_pending(
    env: dict[str, str], conclusion: str, edad_min: int = 1000, borrador: bool = False
) -> None:
    md = _md(env)
    _seed_issue(
        env,
        55,
        ["sirius:ci-pending"],
        comments="READY https://github.com/owner/repo/pull/57\n",
    )
    # El caso B ya no repara sin saber que la transición se PERDIÓ: si
    # `ci-pending` acaba de ponerse, el productor del evento todavía puede
    # actuar. Por eso hay que fechar el estado.
    _seed_events(env, 55, [_evento("labeled", "sirius:ci-pending", _iso(edad_min), 77)])
    (md / "pr_57.json").write_text(
        # Forma REAL de la API: `head` es un objeto con `sha`, no una cadena.
        # Mientras el simulado devolvia el fichero entero sin aplicar el `--jq`,
        # una forma inventada pasaba igual; en produccion `.head.sha` habria
        # fallado. Un simulado fiel obliga a que la siembra tambien lo sea.
        json.dumps({"state": "open", "head": {"sha": "c4d482267d9a"}, "draft": borrador}),
        encoding="utf-8",
    )
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


# --------------------------------------------------------------------------- #
# Estados de máquina que dejan de avanzar (incidencia #138)
# --------------------------------------------------------------------------- #

# Un run que muere no puede informar de su propia muerte. Lo único observable
# desde fuera es que el ESTADO no avanza, y como `issues: labeled` no vuelve a
# dispararse con una etiqueta ya aplicada, nada lo moverá nunca. El
# reconciliador no repara eso —no puede saber si el run murió— pero sí lo hace
# VISIBLE: un resumen de job que nadie abre no es una detección.

REPO_ROOT_WF = REPO_ROOT / ".github" / "workflows"
RECONCILE_WF = REPO_ROOT_WF / "reconcile-sirius-states.yml"


def _iso(minutos_atras: int) -> str:
    momento = datetime.now(UTC) - timedelta(minutes=minutos_atras)
    return momento.strftime("%Y-%m-%dT%H:%M:%SZ")


def _seed_events(
    env: dict[str, str], num: int, eventos: list[dict[str, object]], por_pagina: int = 100
) -> None:
    """Siembra el historial de eventos, repartido en páginas como hace GitHub.

    Se guarda siempre como array de páginas, aunque haya una sola: el simulado
    reproduce a partir de ahí las dos formas en que `gh` entrega los resultados
    (un documento por página, o uno solo con `--slurp`).
    """
    paginas = [eventos[i : i + por_pagina] for i in range(0, len(eventos), por_pagina)] or [[]]
    (_md(env) / f"events_{num}.txt").write_text(json.dumps(paginas), encoding="utf-8")


def _evento(nombre: str, etiqueta: str | None, cuando: str, ident: int) -> dict[str, object]:
    ev: dict[str, object] = {"event": nombre, "created_at": cuando, "id": ident}
    if etiqueta is not None:
        ev["label"] = {"name": etiqueta}
    return ev


def _numero_del_reconciliador(patron: str) -> int:
    m = re.search(patron, RECONCILE.read_text(encoding="utf-8"))
    assert m, f"no encuentro `{patron}` en el reconciliador: la prueba no mediría nada"
    return int(m.group(1))


def test_recon_stuck_001_un_estado_de_maquina_viejo_se_avisa_en_la_incidencia(
    tmp_path: Path,
) -> None:
    """El historial lleva ruido a propósito: el filtro tiene que elegir bien.

    Hay eventos que no son `labeled`, etiquetas distintas, y DOS aplicaciones de
    la misma etiqueta. La fecha buena es la de la última, no la de la primera:
    con la primera, un estado reaplicado hace un minuto se denunciaría como
    atascado desde ayer.
    """
    env = _setup(tmp_path)
    _seed_issue(env, 7, ["sirius:repair-requested"])
    _seed_events(
        env,
        7,
        [
            _evento("labeled", "sirius:repair-requested", _iso(5000), 111),
            _evento("unlabeled", "sirius:repair-requested", _iso(4000), 222),
            _evento("commented", None, _iso(3000), 333),
            _evento("labeled", "sirius:ci-pending", _iso(2000), 444),
            _evento("labeled", "sirius:repair-requested", _iso(1000), 555),
        ],
    )

    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ATASCO" in r.stdout, r.stdout
    assert "sin avanzar" in r.stdout, r.stdout

    publicado = (_md(env) / "comments_7.txt").read_text(encoding="utf-8")
    assert "<!-- sirius-stuck:sirius:repair-requested:555 -->" in publicado, (
        f"el marcador debe llevar el id de la ÚLTIMA aplicación: {publicado!r}"
    )
    assert "111" not in publicado.split("-->")[0], "se fechó por la primera aplicación"
    assert "no ha reparado nada" in publicado


def test_recon_stuck_002_un_estado_reciente_no_se_denuncia(tmp_path: Path) -> None:
    # El revisor puede tardar 85 minutos legítimamente. Avisar antes del umbral
    # convertiría un ciclo vivo en una falsa alarma en la incidencia.
    env = _setup(tmp_path)
    _seed_issue(env, 8, ["sirius:reviewing"])
    _seed_events(env, 8, [_evento("labeled", "sirius:reviewing", _iso(10), 9)])

    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "dentro de lo normal" in r.stdout, r.stdout
    assert "ATASCO" not in r.stdout, r.stdout
    assert "sirius-stuck" not in (_md(env) / "comments_8.txt").read_text(encoding="utf-8")


def test_recon_stuck_003_sin_poder_fechar_no_se_afirma_nada(tmp_path: Path) -> None:
    # Sin historial legible NO se sabe la antigüedad. Interpretar el fallo de
    # lectura como "lleva mucho" publicaría una acusación falsa: es exactamente
    # el patrón de la puerta del corrector, un vacío leído como un hecho.
    env = _setup(tmp_path)
    _seed_issue(env, 9, ["sirius:implement-requested"])
    # No se siembra events_9.txt: la lectura falla.

    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no pude fechar" in r.stdout, r.stdout
    assert "ATASCO" not in r.stdout, r.stdout
    assert "sirius-stuck" not in (_md(env) / "comments_9.txt").read_text(encoding="utf-8")


def test_recon_stuck_004_el_aviso_no_se_repite_en_cada_pasada(tmp_path: Path) -> None:
    # Programado cada 6 horas, un aviso sin deduplicar llenaría la incidencia de
    # copias hasta hacerla ilegible, que es otra forma de no avisar.
    env = _setup(tmp_path)
    _seed_issue(env, 10, ["sirius:repairing"])
    _seed_events(env, 10, [_evento("labeled", "sirius:repairing", _iso(1000), 42)])

    for _ in range(2):
        assert _run_reconcile(env).returncode == 0

    publicado = (_md(env) / "comments_10.txt").read_text(encoding="utf-8")
    assert publicado.count("<!-- sirius-stuck:sirius:repairing:42 -->") == 1, publicado


def test_recon_stuck_005_los_estados_que_esperan_a_un_humano_no_se_denuncian(
    tmp_path: Path,
) -> None:
    # `blocked-decision`, `failed-safely` y `ready-for-merge` esperan a una
    # persona por diseño: llevar semanas ahí es lo correcto, no un atasco.
    for num, etiqueta in (
        (11, "sirius:blocked-decision"),
        (12, "sirius:failed-safely"),
        (13, "sirius:ready-for-merge"),
    ):
        caso = tmp_path / f"caso{num}"
        caso.mkdir()
        env = _setup(caso)
        _seed_issue(env, num, [etiqueta])
        _seed_events(env, num, [_evento("labeled", etiqueta, _iso(100000), num)])

        r = _run_reconcile(env)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "HUMANO" in r.stdout, r.stdout
        assert "ATASCO" not in r.stdout, r.stdout
        assert "sirius-stuck" not in (_md(env) / f"comments_{num}.txt").read_text(encoding="utf-8")


def test_recon_stuck_006_el_umbral_supera_al_job_mas_largo_de_verdad() -> None:
    """El umbral es un número escrito a mano; atarlo al YAML impide que mienta.

    Si alguien sube el revisor de 85 a 200 minutos y nadie toca el umbral, el
    reconciliador empezaría a denunciar como muertas ejecuciones perfectamente
    vivas. Esta prueba lee los `timeout-minutes` REALES de todos los workflows,
    no una copia.
    """
    umbral = _numero_del_reconciliador(r'STUCK_MINUTES="\$\{SIRIUS_STUCK_MINUTES:-(\d+)\}"')
    topes: list[int] = []
    for wf in sorted(REPO_ROOT_WF.glob("*.yml")):
        doc = yaml.safe_load(wf.read_text(encoding="utf-8"))
        for job in (doc.get("jobs") or {}).values():
            if isinstance(job, dict) and isinstance(job.get("timeout-minutes"), int):
                topes.append(job["timeout-minutes"])
    assert topes, "no encontré ningún tope de job: la comparación no mediría nada"
    mas_largo = max(topes)
    assert umbral >= mas_largo * 2, (
        f"umbral {umbral} min no deja holgura sobre el job más largo ({mas_largo} min): "
        "una ejecución viva se denunciaría como muerta"
    )


def _etiquetas_disparadoras() -> set[str]:
    """Las etiquetas con las que arranca cada workflow de trabajo, leídas del YAML."""
    etiquetas: set[str] = set()
    for nombre in _WORKFLOWS_DE_TRABAJO:
        texto = (REPO_ROOT / ".github" / "workflows" / nombre).read_text(encoding="utf-8")
        for m in re.finditer(r"github\.event\.label\.name == '([^']+)'", texto):
            etiquetas.add(m.group(1))
    return etiquetas


def _etiquetas_escritas(env: dict[str, str]) -> set[str]:
    """Toda etiqueta que el reconciliador APLICÓ, incluidas las reaplicaciones.

    El estado final no basta: retirar y volver a poner deja el mismo resultado y
    sin embargo dispara `issues: labeled`, que es arrancar trabajo.
    """
    registro = _md(env) / "added_labels.log"
    if not registro.exists():
        return set()
    return {
        linea.split()[1] for linea in registro.read_text(encoding="utf-8").splitlines() if linea
    }


def test_recon_stuck_007_el_reconciliador_esta_programado_y_sigue_siendo_manual(
    tmp_path: Path,
) -> None:
    doc = yaml.safe_load(RECONCILE_WF.read_text(encoding="utf-8"))
    disparo = doc.get("on") or doc.get(True)
    assert "schedule" in disparo, "sin `schedule:` la detección sigue dependiendo de un humano"
    assert "workflow_dispatch" in disparo, "quitar el disparo manual sería una regresión"
    crons = [e["cron"] for e in disparo["schedule"]]
    assert crons == ["17 */6 * * *"], crons
    # Y sigue sin poder fusionar ni iniciar bloques: la excepción del contrato
    # v1.6 §9.1 se apoya en que este workflow NO es el motor del flujo.
    permisos = doc["permissions"]
    assert permisos["contents"] == "read", permisos
    assert "pull-requests" not in permisos or permisos["pull-requests"] == "read", permisos
    texto = RECONCILE.read_text(encoding="utf-8")
    assert "gh pr merge" not in texto

    # «No inicia bloques» se comprueba EJECUTANDO y mirando CADA escritura de
    # etiqueta, no el estado final.
    #
    # Van cuatro versiones de esta aserción. Las tres primeras medían texto o
    # resultado: (a) que la cadena no apareciera en el archivo; (b) que no
    # cayera en la misma línea que una función de escritura —el repositorio
    # parte esas llamadas en dos—; (c) el estado final, que no ve un «retirar y
    # volver a poner», y esa reaplicación genera un evento nuevo, es decir,
    # arranca trabajo. Las tres pasaban con el defecto puesto.
    #
    # Y había algo peor debajo: el §9.1 decía «no aplica ninguna etiqueta que
    # arranque un bloque», y era FALSO —el caso B aplica `review-requested`—.
    # Por eso la prueba solo miraba una etiqueta: copiaba una afirmación que ya
    # estaba mal. Corregido el texto, esto comprueba lo que ahora dice.
    disparadoras = _etiquetas_disparadoras()
    assert len(disparadoras) == 3, f"esperaba tres disparadoras: {sorted(disparadoras)}"

    maquina = re.search(r'MACHINE_LABELS="([^"]+)"', texto)
    assert maquina, "no encuentro MACHINE_LABELS: la prueba no mediría nada"
    estados = maquina.group(1).split()

    env = _setup(tmp_path)
    for numero, etiqueta in enumerate(estados, start=40):
        _seed_issue(env, numero, [etiqueta])
        _seed_events(env, numero, [_evento("labeled", etiqueta, _iso(5000), numero)])

    assert _run_reconcile(env).returncode == 0

    escritas = _etiquetas_escritas(env)
    prohibidas = sorted(escritas & disparadoras)
    assert not prohibidas, (
        f"desde un estado atascado el reconciliador escribió {prohibidas}, que "
        "arrancan trabajo; el §9.1 dice que no lo hace"
    )


def test_recon_stuck_013_la_unica_disparadora_que_escribe_es_review_requested(
    tmp_path: Path,
) -> None:
    """El §9.1 afirma que la única disparadora que escribe es `review-requested`.

    La redacción anterior decía «ninguna», y era falsa: el caso B la aplica para
    reparar una transición de Quality perdida. Corregido el texto, esta prueba lo
    fija ejecutando: desde `ci-pending` con Quality en verde se escribe esa y
    solo esa, y `implement-requested` no se escribe nunca desde ningún estado.
    """
    env = _setup(tmp_path)
    _seed_ci_pending(env, "success")
    # La misma pasada recorre los DEMÁS caminos del reconciliador, no solo el
    # caso B: caso A, ci-pending sin PR, contradicción, espera humana y una
    # incidencia sin etiquetas. Sin ellos, una escritura insertada en el caso A
    # pasaba las 25 pruebas del fichero en verde —demostrado por mutación—, así
    # que la afirmación del §9.1 no la sostenía ninguna comprobación.
    _seed_issue(env, 50, [], comments="<!-- sirius-completed:b649c92faf98 -->\n")
    _seed_issue(env, 51, ["sirius:ci-pending"], comments="sin ninguna PR\n")
    _seed_events(env, 51, [_evento("labeled", "sirius:ci-pending", _iso(5000), 51)])
    _seed_issue(env, 62, ["sirius:implementing", "sirius:ci-pending"])
    _seed_issue(env, 63, ["sirius:ready-for-merge"])
    _seed_issue(env, 64, [])

    assert _run_reconcile(env).returncode == 0

    escritas = _etiquetas_escritas(env) & _etiquetas_disparadoras()
    assert escritas == {"sirius:review-requested"}, (
        f"el caso B debe escribir `sirius:review-requested` y ninguna otra "
        f"disparadora; escribió {sorted(escritas)}"
    )


def test_recon_stuck_008_el_ultimo_evento_sale_del_conjunto_no_de_una_pagina(
    tmp_path: Path,
) -> None:
    """Con más de una página, `last` no puede aplicarse a cada página aparte.

    `gh --paginate` emite un documento JSON POR PÁGINA, así que un `--jq` con
    `last` devuelve una línea por página. El llamador tomaba la fecha del primer
    trozo y el id del último: una etiqueta reaplicada en la última página se
    habría fechado con la primera, y el marcador de deduplicación habría
    mezclado ambas. Hallazgo P2 de Codex en la PR #143.

    Aquí hay 150 eventos en dos páginas y la reaplicación buena es la última.
    """
    env = _setup(tmp_path)
    _seed_issue(env, 14, ["sirius:repair-requested"])
    vieja, reciente = _iso(9999), _iso(1000)
    ruido: list[dict[str, object]] = [
        _evento("commented", None, _iso(9000 - i), 1000 + i) for i in range(148)
    ]
    eventos = [
        _evento("labeled", "sirius:repair-requested", vieja, 111),
        *ruido,
        _evento("labeled", "sirius:repair-requested", reciente, 999),
    ]
    _seed_events(env, 14, eventos, por_pagina=100)

    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    publicado = (_md(env) / "comments_14.txt").read_text(encoding="utf-8")
    assert "<!-- sirius-stuck:sirius:repair-requested:999 -->" in publicado, (
        f"el marcador debe salir del ÚLTIMO evento del conjunto: {publicado!r}"
    )
    # La FECHA es lo que de verdad se mezclaba: sin `--slurp`, el id salía de la
    # última página y la fecha de la primera. Comprobar solo el marcador dejaba
    # pasar la mutación —verificado— porque el id ya venía de la página buena.
    assert reciente in publicado, (
        f"la fecha publicada debe ser la de la última aplicación ({reciente}): {publicado!r}"
    )
    assert vieja not in publicado, (
        f"se fechó por la primera página ({vieja}), que es el defecto: {publicado!r}"
    )
    edad = int(re.search(r"lleva (\d+) minutos", publicado).group(1))  # type: ignore[union-attr]
    assert 990 <= edad <= 1010, f"la antigüedad publicada ({edad}) no es la del último evento"


def test_recon_stuck_009_las_lecturas_no_pueden_convertirse_en_post(
    tmp_path: Path,
) -> None:
    """`gh api` pasa a POST en cuanto hay un `-f`, salvo `-X GET` explícito.

    `/issues/{n}/events` solo existe en GET, así que sin `-X GET` toda lectura
    fallaba, el estado no se podía fechar y la rama de fallo seguro impedía
    publicar un solo aviso: la detección entera habría estado muerta en
    producción. Hallazgo P1 de Codex en la PR #143.

    El simulado modela ahora esa regla y falla igual que el `gh` real, así que
    esta prueba cae si alguien quita el `-X GET`.
    """
    env = _setup(tmp_path)
    _seed_issue(env, 15, ["sirius:repairing"])
    _seed_events(env, 15, [_evento("labeled", "sirius:repairing", _iso(1000), 5)])

    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sirius-stuck:sirius:repairing:5" in (_md(env) / "comments_15.txt").read_text(
        encoding="utf-8"
    ), "sin `-X GET` la lectura de eventos falla y no se publica nada"


def test_recon_case_b_does_not_overtake_a_healthy_cycle(tmp_path: Path) -> None:
    """Reparar mientras el productor del evento aún puede actuar es adelantarlo.

    Quality acaba de ponerse verde y `advance-sirius-after-quality` puede estar
    encolado. Transicionar ahí no arregla un estado roto: avanza un ciclo sano,
    que es justo lo que los límites 2 y 5 del §9.1 prohíben. Hallazgo P1 de
    Codex en la PR #143.
    """
    env = _setup(tmp_path)
    _seed_ci_pending(env, "success", edad_min=10)

    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "aún puede avanzarlo" in r.stdout, r.stdout
    assert "CORREGIDO" not in r.stdout, r.stdout
    labels = (_md(env) / "labels_55.txt").read_text(encoding="utf-8")
    assert "sirius:ci-pending" in labels
    assert "sirius:review-requested" not in labels


def test_recon_case_b_without_a_datable_state_does_not_repair(tmp_path: Path) -> None:
    # Sin poder fechar `ci-pending` no se sabe si la transición se perdió o está
    # en vuelo. Reparar a ciegas sería inventárselo.
    env = _setup(tmp_path)
    _seed_ci_pending(env, "success")
    (_md(env) / "events_55.txt").unlink()

    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no reparo a ciegas" in r.stdout, r.stdout
    assert "sirius:review-requested" not in (_md(env) / "labels_55.txt").read_text(encoding="utf-8")


# Los tres workflows que hacen el TRABAJO. Cualquier otra etiqueta puede
# disparar notificaciones —`sirius:implementing` lo hace— sin mover el ciclo,
# así que mirar «etiquetas que disparan algún workflow» sería demasiado amplio
# y la prueba pasaría con el defecto puesto. Verificado: con ese conjunto,
# `sirius:implementing` figuraba como disparadora.
_WORKFLOWS_DE_TRABAJO = (
    "implement-sirius-work.yml",
    "review-sirius-work.yml",
    "repair-sirius-work.yml",
)


def _consumo_de_los_workflows() -> dict[str, tuple[str, list[str]]]:
    """Qué etiqueta pone y cuáles retira el paso «Consumir el evento», por workflow.

    Se lee del YAML REAL. Es la fuente correcta: lo que hay que reponer para
    volver a armar el ciclo es exactamente lo que el consumo retiró, ni más ni
    menos. Deducirlo de otra parte —o escribirlo a mano en la prueba— sería
    reconstruir desde fuera lo que estos workflows ya dicen de sí mismos, que es
    la raíz de los dos defectos que esta prueba viene a cerrar.
    """
    consumo: dict[str, tuple[str, list[str]]] = {}
    for nombre in _WORKFLOWS_DE_TRABAJO:
        texto = (REPO_ROOT / ".github" / "workflows" / nombre).read_text(encoding="utf-8")
        m = re.search(
            r'sirius_set_issue_labels "\$GH_REPO" "\$ISSUE_NUMBER" *\\\n\s*((?:"sirius:[^"]+" *)+)',
            texto,
        )
        assert m, f"no encuentro el paso de consumo en {nombre}"
        etiquetas = re.findall(r'"(sirius:[^"]+)"', m.group(1))
        assert len(etiquetas) >= 2, f"consumo inesperado en {nombre}: {etiquetas}"
        disparadora = re.search(r"github\.event\.label\.name == '([^']+)'", texto)
        assert disparadora, f"no encuentro el disparador de {nombre}"
        # etiquetas[0] es la que se PONE (el estado en curso); el resto se retiran.
        consumo[etiquetas[0]] = (disparadora.group(1), etiquetas[1:])
    return consumo


def _reactivacion(etiqueta: str) -> list[str]:
    """Ejecuta la `reactivation_labels` REAL, extraída del script.

    No se puede hacer `source` del reconciliador: al cargarlo se ejecuta y exige
    el repositorio como argumento. Y copiar la tabla aquí la dejaría vieja en
    silencio, que es la forma más común de prueba vacua en este repositorio.
    """
    guion = RECONCILE.read_text(encoding="utf-8")
    inicio = guion.index("reactivation_labels() {")
    fin = guion.index("\n}\n", inicio) + len("\n}\n")
    bloque = guion[inicio:fin]
    salida = subprocess.run(
        ["bash", "-c", f'{bloque}\nreactivation_labels "{etiqueta}"'],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return salida.split()


def test_recon_stuck_010_la_reactivacion_repone_lo_que_el_consumo_retiro() -> None:
    """El aviso debe prescribir una secuencia que ARRANQUE el trabajo de verdad.

    Dos rondas de revisión con el mismo defecto, y por eso esta prueba no
    comprueba una lista escrita a mano sino una REGLA leída de los workflows:

    - Ronda 1: el aviso decía «quita `sirius:repairing` y vuelve a ponerla».
      Dispara `issues: labeled`, pero no pasa el `if:` del job.
    - Ronda 2: proponer solo la etiqueta del `if:` tampoco basta para
      `implementing`: el consumo retira además `sirius:planned`, y
      `sirius_validate_activation.sh` la exige. Sin ella la puerta rechaza la
      activación y retira la etiqueta otra vez.

    La regla que sí se sostiene: **hay que reponer exactamente lo que el paso de
    consumo retiró**, con la disparadora en último lugar para que la puerta
    encuentre el resto ya puesto. Eso se lee del YAML, no de la tabla del
    script, así que la prueba no es circular y notará cualquier cambio futuro en
    lo que esos pasos consumen.
    """
    consumo = _consumo_de_los_workflows()
    assert len(consumo) == 3, f"esperaba tres estados en curso, encontré {sorted(consumo)}"

    guion = RECONCILE.read_text(encoding="utf-8")
    maquina = re.search(r'MACHINE_LABELS="([^"]+)"', guion)
    assert maquina, "no encuentro MACHINE_LABELS: la prueba no mediría nada"
    estados = maquina.group(1).split()

    for en_curso, (disparadora, retiradas) in consumo.items():
        assert en_curso in estados, f"`{en_curso}` no está en MACHINE_LABELS"
        prescrito = _reactivacion(en_curso)
        assert sorted(prescrito) == sorted(retiradas), (
            f"para `{en_curso}` el aviso prescribe {prescrito}, pero el consumo "
            f"retira {retiradas}: la incidencia no arrancaría"
        )
        assert prescrito[-1] == disparadora, (
            f"para `{en_curso}` la etiqueta disparadora `{disparadora}` debe ir la "
            f"ÚLTIMA para que la puerta encuentre el resto ya puesto; va {prescrito}"
        )

    # Y los `*-requested`: reponer la misma etiqueta sí funciona, porque son
    # justamente las disparadoras.
    disparadoras = {d for d, _ in consumo.values()}
    for estado in estados:
        if estado in consumo:
            continue
        assert _reactivacion(estado) == [estado], (
            f"para `{estado}` basta con reponerla; el aviso prescribe otra cosa"
        )
        assert estado in disparadoras, f"`{estado}` no dispara ningún trabajo"


def test_recon_stuck_011_la_promesa_retirada_no_vuelve(tmp_path: Path) -> None:
    """Ancla literal de una redacción revocada, medida sobre el texto PUBLICADO.

    La versión anterior hacía `grep` sobre el fichero del guion, y fallaba en las
    dos direcciones: no veía entrar una promesa nueva con otras palabras, y —peor—
    su aserción positiva quedaba satisfecha por un COMENTARIO de shell aunque el
    aviso publicado ya no contuviera la frase. Cuarta vez en esta PR que un
    `grep` se hace pasar por una comprobación de comportamiento.

    Esto NO garantiza que no vuelva una promesa equivalente con otras palabras
    —eso no es decidible—; es un ancla contra la redacción concreta que tres
    rondas de revisión demostraron falsa.
    """
    env = _setup(tmp_path)
    _seed_issue(env, 22, ["sirius:reviewing"])
    _seed_events(env, 22, [_evento("labeled", "sirius:reviewing", _iso(2000), 22)])
    assert _run_reconcile(env).returncode == 0
    publicado = (_md(env) / "comments_22.txt").read_text(encoding="utf-8")

    for promesa in ("No se queda en silencio", "lo dirá en un comentario"):
        assert promesa not in publicado, (
            f"el aviso vuelve a garantizar algo que no controla: {promesa!r}"
        )
    assert "la ejecución de Actions dice por qué" in publicado, (
        "el aviso debe seguir diciendo dónde mirar cuando no arranque"
    )


def test_recon_stuck_012_el_aviso_publicado_se_lee_bien(tmp_path: Path) -> None:
    """Se mira el texto PUBLICADO, no el guion que lo construye.

    La secuencia de etiquetas se arma con `printf` dentro de comillas simples,
    donde la tilde invertida es literal. Escaparla —como sí hay que hacer en las
    otras líneas, que van entre comillas dobles— publicaba `\\`sirius:planned\\``
    con las barras a la vista, y el aviso se leía roto justo en el paso que el
    usuario tiene que ejecutar.

    Ninguna prueba sobre el guion lo habría visto: el escapado es correcto en un
    contexto e incorrecto en el otro, y ambos son el mismo carácter. Por eso esta
    prueba renderiza el aviso de verdad y lo lee.
    """
    env = _setup(tmp_path)
    _seed_issue(env, 21, ["sirius:implementing"])
    _seed_events(env, 21, [_evento("labeled", "sirius:implementing", _iso(2000), 7)])

    assert _run_reconcile(env).returncode == 0
    publicado = (_md(env) / "comments_21.txt").read_text(encoding="utf-8")

    assert "\\`" not in publicado, f"el aviso publica barras invertidas a la vista: {publicado!r}"
    assert "`sirius:planned`, `sirius:implement-requested`" in publicado, (
        f"la secuencia no se lee como código: {publicado!r}"
    )
    # `printf` REUTILIZA el formato cuando sobran argumentos. Con seis `%s` y
    # siete argumentos, la última línea salía pegada al punto 2 —en Markdown eso
    # la mete DENTRO del ítem, que es lo contrario de lo que se quería— y detrás
    # se colaban diez líneas en blanco. Comprobar subcadenas sueltas no lo veía.
    assert "\n\nSi tras eso el bloque sigue sin arrancar" in publicado, (
        f"la salvedad se pega al punto 2 y GitHub la mete dentro del ítem: {publicado!r}"
    )
    assert publicado.rstrip("\n").endswith("consta siempre."), (
        f"el aviso arrastra líneas en blanco de más: {publicado!r}"
    )


# --------------------------------------------------------------------------- #
# Auditoría adversarial de la PR #146: ocho defectos, y sus pruebas
# --------------------------------------------------------------------------- #


def test_recon_aud_001_si_falla_el_listado_la_pasada_no_pasa_por_exitosa(
    tmp_path: Path,
) -> None:
    """Una red de seguridad que no comprueba nada no puede parecer que sí.

    `mapfile -t open_issues < <( ... )` descarta el estado de salida de la
    sustitución de proceso. Un 503 o un 403 dejaba la lista vacía, `overall_rc`
    en 0 y el resumen del job VACÍO: byte a byte igual que un repositorio sano
    sin incidencias. Las cuatro pasadas diarias se apagaban con aspecto de
    éxito, que es el peor desenlace posible aquí — no detectar y además parecer
    que se ha comprobado.
    """
    env = _setup(tmp_path)
    _seed_issue(env, 70, ["sirius:repairing"])
    _seed_events(env, 70, [_evento("labeled", "sirius:repairing", _iso(5000), 70)])
    env["MOCK_FAIL_LIST"] = "1"

    r = _run_reconcile(env)

    assert r.returncode != 0, (
        "la pasada salió con éxito sin haber podido mirar una sola incidencia:\n"
        f"{r.stdout}{r.stderr}"
    )
    assert "NO ha comprobado nada" in r.stdout, r.stdout


def test_recon_aud_002_un_fallo_al_leer_eventos_no_se_confunde_con_no_haberlos(
    tmp_path: Path,
) -> None:
    """Sin diagnóstico, «no pude leer» y «no hay evento» son el mismo silencio.

    `label_applied_at` llevaba `2>/dev/null` sobre la llamada ENTERA, no solo
    sobre `gh`: se perdían el mensaje de `gh` y los avisos de reintento. Un 403
    por límite de tasa producía una salida idéntica al caso benigno «esta
    incidencia no tiene ese evento». Con límite de tasa el efecto es global: la
    detección se apaga en las cuatro pasadas sin una sola señal. Es la misma
    ceguera que ocultó el defecto del `-X GET`.
    """
    env = _setup(tmp_path)
    _seed_issue(env, 71, ["sirius:repairing"])
    _seed_events(env, 71, [_evento("commented", None, _iso(5000), 71)])
    sin_evento = _run_reconcile(env)

    (tmp_path / "fallo").mkdir()
    otro = _setup(tmp_path / "fallo")
    _seed_issue(otro, 71, ["sirius:repairing"])
    _seed_events(otro, 71, [_evento("labeled", "sirius:repairing", _iso(5000), 71)])
    otro["MOCK_FAIL_EVENTS"] = "1"
    lectura_rota = _run_reconcile(otro)

    assert "no pude fechar" in sin_evento.stdout, sin_evento.stdout
    assert "no pude fechar" in lectura_rota.stdout, lectura_rota.stdout
    assert lectura_rota.stderr != sin_evento.stderr, (
        "un fallo de lectura sale igual que no tener eventos: la detección "
        "puede estar apagada del todo sin que nada lo delate"
    )
    assert "403" in lectura_rota.stderr or "rate" in lectura_rota.stderr.lower(), (
        f"el motivo del fallo no llega a ninguna parte: {lectura_rota.stderr!r}"
    )


def test_recon_aud_003_una_activacion_atascada_recibe_aviso(tmp_path: Path) -> None:
    """`planned` + `implement-requested` no es una contradicción: es el estado normal.

    `sirius_validate_activation.sh` EXIGE `planned` e `implement-sirius-work.yml`
    retira las dos juntas al consumir el evento, así que ese par es el ÚNICO
    estado en que `implement-requested` existe en producción sana. Contarlo como
    contradicción cortaba antes del bucle de estados: una activación cuyo run
    muriera antes de consumir el evento no recibía aviso NUNCA. Justo el caso
    que esta red de seguridad existe para cubrir.
    """
    env = _setup(tmp_path)
    _seed_issue(env, 72, ["sirius:planned", "sirius:implement-requested"])
    _seed_events(env, 72, [_evento("labeled", "sirius:implement-requested", _iso(5000), 72)])

    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CONTRADICCION" not in r.stdout, (
        f"se acusa de incoherente a una activación normal: {r.stdout}"
    )
    publicado = (_md(env) / "comments_72.txt").read_text(encoding="utf-8")
    assert "<!-- sirius-stuck:sirius:implement-requested:72 -->" in publicado, (
        f"una activación atascada se quedó sin aviso: {publicado!r}"
    )


def test_recon_aud_004_una_contradiccion_de_verdad_sigue_siendo_contradiccion(
    tmp_path: Path,
) -> None:
    # Control de la excepción anterior: exceptuar un par no puede convertirse en
    # dejar de detectar los demás.
    env = _setup(tmp_path)
    _seed_issue(env, 73, ["sirius:ci-pending", "sirius:reviewing"])
    _seed_events(env, 73, [_evento("labeled", "sirius:reviewing", _iso(5000), 73)])

    r = _run_reconcile(env)
    assert "CONTRADICCION" in r.stdout, r.stdout
    assert "sirius-stuck" not in (_md(env) / "comments_73.txt").read_text(encoding="utf-8")


def test_recon_aud_005_una_activacion_reciente_no_se_denuncia(tmp_path: Path) -> None:
    # Y el par exceptuado tampoco puede denunciarse cuando es normal y reciente.
    env = _setup(tmp_path)
    _seed_issue(env, 74, ["sirius:planned", "sirius:implement-requested"])
    _seed_events(env, 74, [_evento("labeled", "sirius:implement-requested", _iso(10), 74)])

    r = _run_reconcile(env)
    assert "dentro de lo normal" in r.stdout, r.stdout
    assert "sirius-stuck" not in (_md(env) / "comments_74.txt").read_text(encoding="utf-8")


def test_recon_aud_006_no_se_despierta_al_revisor_sobre_una_pr_en_borrador(
    tmp_path: Path,
) -> None:
    """El productor del evento se niega a mover una PR en borrador; el caso B no.

    `advance-sirius-after-quality.yml` sale sin hacer nada si la PR es borrador,
    y `quality.yml` SÍ corre en borrador: Quality verde, `advance` se niega, y la
    incidencia se queda en `ci-pending`. Es el camino más probable de llegar al
    caso B. Sin mirar `draft`, seis horas después el reconciliador arrancaba al
    revisor —85 minutos de trabajo— sobre una PR que una persona había aparcado
    a propósito. Rompe los límites 2 y 5 del §9.1 que esta misma PR declara.

    La aserción es sobre las etiquetas ESCRITAS, no sobre el estado final: el
    evento `issues: labeled` se dispara aunque algo la retire después.
    """
    borrador = _etiquetas_borrador_del_productor()
    assert borrador, (
        "`advance-sirius-after-quality.yml` ya no comprueba `draft`; esta prueba "
        "asume que sí y habría que revisarla"
    )

    env = _setup(tmp_path)
    _seed_ci_pending(env, "success", borrador=True)

    r = _run_reconcile(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "borrador" in r.stdout, r.stdout
    assert "sirius:review-requested" not in _etiquetas_escritas(env), (
        "se despertó al revisor sobre una PR en borrador, que es justo lo que el "
        "productor del evento se niega a hacer"
    )


def _etiquetas_borrador_del_productor() -> bool:
    """¿`advance-sirius-after-quality.yml` comprueba `draft`? Leído del YAML real."""
    texto = (REPO_ROOT / ".github" / "workflows" / "advance-sirius-after-quality.yml").read_text(
        encoding="utf-8"
    )
    return "draft" in texto


def test_recon_aud_007_ci_pending_atascado_tambien_recibe_aviso(tmp_path: Path) -> None:
    """`ci-pending` era el único estado de máquina sin aviso en la incidencia.

    Su único motor es `advance-sirius-after-quality.yml` con `on: workflow_run`,
    un evento de un solo uso: con Quality en rojo y ese run muerto no se aplica
    `repair-requested`, luego no hay commit nuevo, luego Quality no vuelve a
    correr y no hay `workflow_run` nuevo. Callejón cerrado — y la cabecera del
    guion afirmaba que todos los estados de máquina reciben aviso.
    """
    env = _setup(tmp_path)
    _seed_ci_pending(env, "failure", edad_min=5000)

    for _ in range(2):
        assert _run_reconcile(env).returncode == 0

    publicado = (_md(env) / "comments_55.txt").read_text(encoding="utf-8")
    assert publicado.count("<!-- sirius-stuck:sirius:ci-pending:77 -->") == 1, (
        f"esperaba un solo aviso de atasco, deduplicado: {publicado!r}"
    )
    assert "sirius:repair-requested" in publicado, (
        "el aviso debe decir qué etiqueta aplica una persona para desatascarlo"
    )
    assert "sirius:repair-requested" not in _etiquetas_escritas(env), (
        "el reconciliador no puede aplicarla él: eso sería decidir que la corrección procede"
    )


def test_recon_aud_008_ci_pending_reciente_no_se_denuncia(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed_ci_pending(env, "failure", edad_min=10)

    # Lo corta el guardia de antigüedad del caso B, antes incluso de mirar
    # Quality: da igual cuál de los dos lo pare, lo que no puede es denunciarlo.
    r = _run_reconcile(env)
    assert "EN-CURSO" in r.stdout, r.stdout
    assert "ATASCO" not in r.stdout, r.stdout
    assert "sirius-stuck" not in (_md(env) / "comments_55.txt").read_text(encoding="utf-8")
