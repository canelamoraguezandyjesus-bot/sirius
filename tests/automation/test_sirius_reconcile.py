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
    if printf '%s' "$args" | grep -q '/events'; then
      raw="$D/events_${n}.txt"
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


def _seed_ci_pending(env: dict[str, str], conclusion: str, edad_min: int = 1000) -> None:
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


def test_recon_stuck_007_el_reconciliador_esta_programado_y_sigue_siendo_manual() -> None:
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

    # «No inicia bloques» es no APLICAR `sirius:implement-requested`, no dejar
    # de nombrarla. La versión anterior de esta aserción prohibía que la cadena
    # apareciera en el archivo, y eso es una prueba de grafía: rompía en cuanto
    # el aviso al usuario mencionaba la etiqueta que tiene que aplicar ÉL, y a
    # cambio no habría notado un `--add-label` escrito de otra forma.
    escrituras = (
        "sirius_transition",
        "trigger_transition",
        "sirius_set_issue_labels",
        "--add-label",
    )
    for numero, linea in enumerate(texto.splitlines(), start=1):
        if "sirius:implement-requested" not in linea:
            continue
        for escritura in escrituras:
            assert escritura not in linea, (
                f"línea {numero}: el reconciliador aplicaría "
                f"`sirius:implement-requested` vía `{escritura}`, e iniciaría un bloque"
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


def _etiquetas_que_arrancan_trabajo() -> set[str]:
    etiquetas: set[str] = set()
    for nombre in _WORKFLOWS_DE_TRABAJO:
        texto = (REPO_ROOT / ".github" / "workflows" / nombre).read_text(encoding="utf-8")
        for m in re.finditer(r"github\.event\.label\.name == '([^']+)'", texto):
            etiquetas.add(m.group(1))
    return etiquetas


def _reactivacion(etiqueta: str) -> str:
    """Ejecuta la `reactivation_label` REAL, extraída del script.

    No se puede hacer `source` del reconciliador: al cargarlo se ejecuta y exige
    el repositorio como argumento. Y copiar la tabla aquí la dejaría vieja en
    silencio, que es la forma más común de prueba vacua en este repositorio.
    """
    guion = RECONCILE.read_text(encoding="utf-8")
    inicio = guion.index("reactivation_label() {")
    fin = guion.index("\n}\n", inicio) + len("\n}\n")
    bloque = guion[inicio:fin]
    return subprocess.run(
        ["bash", "-c", f'{bloque}\nreactivation_label "{etiqueta}"'],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()


def test_recon_stuck_010_la_etiqueta_propuesta_arranca_el_trabajo_de_verdad() -> None:
    """El aviso debe proponer una etiqueta que ARRANQUE el ciclo.

    Decía «quita `sirius:repairing` y vuelve a ponerla», pero
    `repair-sirius-work.yml` arranca con
    `if: github.event.label.name == 'sirius:repair-requested'`: reponer la
    etiqueta en curso crea una ejecución cuyo job se salta, y la incidencia se
    queda igual de atascada. El aviso mandaba a hacer algo que no funciona.
    Hallazgo P2 de Codex en la PR #143.

    La comprobación no usa la tabla del script como referencia —sería
    circular—: lee los `if:` REALES de los tres workflows que hacen el trabajo.
    """
    arrancan = _etiquetas_que_arrancan_trabajo()
    assert len(arrancan) == 3, f"esperaba tres etiquetas de arranque, encontré {arrancan}"

    guion = RECONCILE.read_text(encoding="utf-8")
    maquina = re.search(r'MACHINE_LABELS="([^"]+)"', guion)
    assert maquina, "no encuentro MACHINE_LABELS: la prueba no mediría nada"

    en_curso = [x for x in maquina.group(1).split() if x.endswith("ing")]
    assert en_curso, "no hay estados en curso: la prueba no mediría el caso del defecto"

    for etiqueta in maquina.group(1).split():
        propuesta = _reactivacion(etiqueta)
        assert propuesta in arrancan, (
            f"para `{etiqueta}` el aviso propone `{propuesta}`, que no arranca "
            f"ningún trabajo: la incidencia seguiría atascada. Arrancan: {sorted(arrancan)}"
        )

    # Y el defecto exacto: proponer la propia etiqueta en curso no vale.
    for etiqueta in en_curso:
        assert etiqueta not in arrancan, (
            f"`{etiqueta}` no debería arrancar trabajo; si lo hace, esta prueba sobra"
        )
        assert _reactivacion(etiqueta) != etiqueta, (
            f"el aviso propondría reponer `{etiqueta}`, que no arranca nada"
        )
