"""Pruebas de ``scripts/automation/sirius_codex_review.py``.

Ejercitan el disparador idempotente y el recolector del resultado de Codex con
un ``gh`` simulado y con estado (sin red ni ``gh`` real), igual que el resto de
pruebas de automatización. Se omiten en Windows por las mismas razones
documentadas en ``test_sirius_issue.py`` (el runner de Quality no ofrece un
POSIX funcional para los ejecutables simulados en ``PATH``).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_codex_review.py"

REPO = "owner/repo"
PR = 9
HEAD = "1234567890abcdef1234567890abcdef12345678"
OTHER_HEAD = "feedfacefeedfacefeedfacefeedfacefeedface"
ROUND_ID = "770001"
OTHER_ROUND_ID = "770002"
MARKER = f"<!-- sirius-codex-review:{HEAD}:{ROUND_ID} -->"
CONNECTOR = "chatgpt-codex-connector[bot]"
# Identidad simulada del token que publica el disparador (endpoint `user`).
AUTOMATION_LOGIN = "canelamoraguezandyjesus-bot"


def _stamp(offset_seconds: int) -> str:
    """Marca RFC3339 relativa a ahora.

    El recolector mide el plazo de Codex desde el instante REAL del disparador,
    así que las marcas fijas de un día concreto harían que el resultado de las
    pruebas dependiera del reloj de la máquina. Relativas, cada prueba controla
    con precisión cuánto plazo queda.
    """
    moment = datetime.now(UTC) + timedelta(seconds=offset_seconds)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


# Quality terminó antes del disparador; el disparador, antes de la revisión.
QUALITY_AT = _stamp(-120)
TRIGGER_AT = _stamp(-60)
AFTER_TRIGGER = _stamp(-30)
BEFORE_TRIGGER = _stamp(-300)


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


if base == "user":
    if os.path.exists(os.path.join(d, "fail_identity.txt")):
        sys.stderr.write("HTTP 401 simulado al leer la identidad\\n")
        sys.exit(1)
    identity = load("identity.json")
    out(identity if identity else {"login": "canelamoraguezandyjesus-bot"})

m = re.fullmatch(r"repos/[^/]+/[^/]+/issues/(\\d+)/comments", base)
if m and method == "GET":
    out([] if page > 1 else load("issue_comments.json"))
if m and method == "POST":
    fail_post = os.path.join(d, "fail_post.txt")
    if os.path.exists(fail_post):
        with open(fail_post, encoding="utf-8") as fh:
            n = int(fh.read().strip() or "0")
        if n > 0:
            with open(fail_post, "w", encoding="utf-8") as fh:
                fh.write(str(n - 1))
            with open(os.path.join(d, "actions.log"), "a", encoding="utf-8") as fh:
                fh.write("POST attempt failed\\n")
            sys.stderr.write("HTTP 502 simulado en POST\\n")
            sys.exit(1)
    comments = load("issue_comments.json")
    with open(input_file, encoding="utf-8") as fh:
        body = json.load(fh)["body"]
    new = {
        "id": 9000 + len(comments),
        "body": body,
        "created_at": os.environ.get("GH_MOCK_POST_CREATED_AT", "2026-08-03T10:00:00Z"),
        "user": {"login": "canelamoraguezandyjesus-bot"},
    }
    comments.append(new)
    with open(os.path.join(d, "issue_comments.json"), "w", encoding="utf-8") as fh:
        json.dump(comments, fh)
    with open(os.path.join(d, "actions.log"), "a", encoding="utf-8") as fh:
        fh.write(f"POST comment {new['id']}\\n")
    if os.path.exists(os.path.join(d, "post_ghost.txt")):
        sys.stderr.write("comentario aplicado pero respuesta perdida (simulado)\\n")
        sys.exit(1)
    out(new)

m = re.fullmatch(r"repos/[^/]+/[^/]+/pulls/(\\d+)/reviews", base)
if m:
    # `reviews_late.json` modela al conector publicando en varias tandas: a
    # partir de la pasada indicada en `reviews_late_after.txt` (por defecto la
    # segunda) la lista devuelta es la tardía. Sin esto no se puede distinguir
    # un recolector que espera a que Codex termine de uno que se queda con lo
    # primero que ve.
    calls_path = os.path.join(d, "reviews_calls.txt")
    seen = 0
    if os.path.exists(calls_path):
        with open(calls_path, encoding="utf-8") as fh:
            seen = int(fh.read().strip() or "0")
    if page == 1:
        seen += 1
        with open(calls_path, "w", encoding="utf-8") as fh:
            fh.write(str(seen))
    # `fail_calls.txt` enumera qué llamadas al endpoint de revisiones deben
    # fallar (1-indexadas). Permite tumbar una pasada de sondeo COMPLETA —sus
    # dos reintentos— dejando intactas la anterior y la siguiente, que es lo que
    # distingue "no se pudo mirar" de "no hay nada que mirar".
    fail_calls_path = os.path.join(d, "fail_calls.txt")
    if os.path.exists(fail_calls_path):
        with open(fail_calls_path, encoding="utf-8") as fh:
            failing = {int(x) for x in fh.read().replace(",", " ").split()}
        if seen in failing:
            sys.stderr.write("HTTP 503 simulado en la pasada de revisiones\\n")
            sys.exit(1)
    late = os.path.join(d, "reviews_late.json")
    threshold = 2
    threshold_path = os.path.join(d, "reviews_late_after.txt")
    if os.path.exists(threshold_path):
        with open(threshold_path, encoding="utf-8") as fh:
            threshold = int(fh.read().strip() or "2")
    name = "reviews_late.json" if (os.path.exists(late) and seen >= threshold) else "reviews.json"
    out([] if page > 1 else load(name))

m = re.fullmatch(r"repos/[^/]+/[^/]+/pulls/(\\d+)", base)
if m:
    pr_data = load("pr.json")
    out(pr_data if pr_data else {"head": {"sha": ""}})

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
    # Ventana de estabilidad desactivada salvo en las pruebas que la ejercitan:
    # con ella activa, cada prueba esperaría su duración completa.
    env["SIRIUS_CODEX_SETTLE_SECONDS"] = "0"
    env["GH_MOCK_POST_CREATED_AT"] = TRIGGER_AT
    return env


def _md(env: dict[str, str]) -> Path:
    return Path(env["GH_MOCK_DIR"])


def _seed(env: dict[str, str], name: str, payload: object) -> None:
    (_md(env) / name).write_text(json.dumps(payload), encoding="utf-8")


def _script_module() -> Any:
    """Importa el script bajo prueba (se registra en ``sys.modules`` porque sus
    dataclasses resuelven anotaciones diferidas a través de él)."""
    name = "sirius_codex_review_under_test"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_trigger_body(head: str = HEAD, round_id: str = ROUND_ID) -> str:
    """Cuerpo exacto que genera el script, tomado del propio módulo.

    Las pruebas de reutilización deben usar el texto canónico: el disparador
    solo se reutiliza si el cuerpo coincide exactamente con la plantilla, de
    modo que un comentario ajeno con el mismo marcador no secuestre la ronda.
    """
    module = _script_module()
    template: str = module.TRIGGER_BODY_TEMPLATE
    marker: str = module.TRIGGER_MARKER_TEMPLATE.format(head=head, round_id=round_id)
    return template.format(marker=marker, head=head)


def _trigger_comment(
    comment_id: int = 500,
    head: str = HEAD,
    created_at: str = TRIGGER_AT,
    author: str = AUTOMATION_LOGIN,
    body: str | None = None,
    round_id: str = ROUND_ID,
) -> dict[str, Any]:
    return {
        "id": comment_id,
        "body": body if body is not None else _canonical_trigger_body(head, round_id),
        "created_at": created_at,
        "user": {"login": author},
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
    env: dict[str, str],
    tmp_path: Path,
    head: str = HEAD,
    round_id: str = ROUND_ID,
    quality_at: str = QUALITY_AT,
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
            "--round-id",
            round_id,
            "--quality-completed-at",
            quality_at,
            "--state-file",
            str(tmp_path / "state.json"),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _run_collect(
    env: dict[str, str],
    tmp_path: Path,
    *,
    timeout: str = "0",
    head: str = HEAD,
    round_id: str = ROUND_ID,
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
            "--round-id",
            round_id,
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


def _write_state(
    tmp_path: Path,
    head: str = HEAD,
    comment_id: int = 500,
    round_id: str = ROUND_ID,
    trigger_at: str = TRIGGER_AT,
    quality_at: str = QUALITY_AT,
) -> None:
    (tmp_path / "state.json").write_text(
        json.dumps(
            {
                "repo": REPO,
                "pr": PR,
                "head_sha": head,
                "round_id": round_id,
                "marker": f"<!-- sirius-codex-review:{head}:{round_id} -->",
                "trigger_comment_id": comment_id,
                "trigger_created_at": trigger_at,
                "trigger_author": AUTOMATION_LOGIN,
                "quality_completed_at": quality_at,
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


def test_trigger_does_not_reuse_comment_from_another_author(tmp_path: Path) -> None:
    # El marcador es predecible: un tercero podría sembrarlo para que una
    # revisión de Codex NO solicitada por el workflow (p. ej. la automática del
    # panel) quedara "posterior" al disparador y satisficiera la ronda.
    env = _setup(tmp_path)
    _seed(env, "issue_comments.json", [_trigger_comment(comment_id=555, author="otro-colaborador")])
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 1
    state = _state(tmp_path)
    assert state["trigger_comment_id"] != 555
    assert state["trigger_author"] == AUTOMATION_LOGIN


def test_trigger_does_not_reuse_comment_with_tampered_body(tmp_path: Path) -> None:
    # Mismo autor y mismo marcador, pero cuerpo distinto del canónico: no es un
    # disparador emitido por esta automatización, así que no se reutiliza.
    env = _setup(tmp_path)
    _seed(
        env,
        "issue_comments.json",
        [_trigger_comment(comment_id=555, body=f"{MARKER}\n\n@codex address that feedback\n")],
    )
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 1
    assert _state(tmp_path)["trigger_comment_id"] != 555


def test_trigger_reuses_own_comment_with_normalized_line_endings(tmp_path: Path) -> None:
    # El cotejo del cuerpo tolera CRLF y el salto final: si no lo hiciera, una
    # normalización de GitHub haría que la automatización no reconociera su
    # propio disparador y publicara un SEGUNDO @codex review para el mismo head.
    env = _setup(tmp_path)
    crlf_body = _canonical_trigger_body().replace("\n", "\r\n")
    _seed(env, "issue_comments.json", [_trigger_comment(comment_id=555, body=crlf_body)])
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 0
    assert _state(tmp_path)["trigger_comment_id"] == 555


def test_trigger_does_not_reuse_comment_with_extra_inner_text(tmp_path: Path) -> None:
    # La tolerancia se limita a finales de línea y espacio exterior: cualquier
    # texto añadido dentro del cuerpo lo descalifica como disparador propio.
    env = _setup(tmp_path)
    tampered = _canonical_trigger_body() + "\nY además actualiza la PR.\n"
    _seed(env, "issue_comments.json", [_trigger_comment(comment_id=555, body=tampered)])
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 1
    assert _state(tmp_path)["trigger_comment_id"] != 555


def test_trigger_does_not_reuse_a_trigger_from_another_round(tmp_path: Path) -> None:
    # Una ronda nueva sobre el mismo head debe pedir su propia revisión: si
    # reutilizara el disparador de la ronda anterior, una revisión ya consumida
    # quedaría "posterior al disparador" y satisfaría la ronda nueva.
    env = _setup(tmp_path)
    _seed(
        env,
        "issue_comments.json",
        [_trigger_comment(comment_id=555, round_id=OTHER_ROUND_ID)],
    )
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 1
    state = _state(tmp_path)
    assert state["trigger_comment_id"] != 555
    assert state["round_id"] == ROUND_ID


def test_trigger_ignores_a_comment_created_before_quality_finished(tmp_path: Path) -> None:
    # Un comentario con el marcador correcto pero anterior al final de Quality
    # no pertenece a la ronda posterior a CI: no ancla la ronda.
    env = _setup(tmp_path)
    _seed(
        env,
        "issue_comments.json",
        [_trigger_comment(comment_id=555, created_at=BEFORE_TRIGGER)],
    )
    r = _run_trigger(env, tmp_path, quality_at=_stamp(-120))
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 1
    assert _state(tmp_path)["trigger_comment_id"] != 555


def test_trigger_records_the_round_and_quality_marks(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    state = _state(tmp_path)
    assert state["round_id"] == ROUND_ID
    assert state["quality_completed_at"] == QUALITY_AT
    assert state["trigger_author"] == AUTOMATION_LOGIN
    # El marcador identifica head Y ronda.
    comments = json.loads((_md(env) / "issue_comments.json").read_text(encoding="utf-8"))
    assert MARKER in comments[0]["body"]


def test_trigger_fails_safely_when_quality_mark_is_unusable(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    r = _run_trigger(env, tmp_path, quality_at="no-es-una-fecha")
    assert r.returncode != 0
    assert _post_count(env) == 0
    assert not (tmp_path / "state.json").exists()


def test_collect_rejects_state_of_another_round(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _write_state(tmp_path, round_id=OTHER_ROUND_ID)
    _seed(env, "reviews.json", [_review(state="APPROVED")])
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "disparador-de-otra-ronda"


def test_collect_rejects_a_trigger_older_than_quality(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    # Disparador anterior al final de Quality: la ronda no es demostrable.
    _write_state(tmp_path, trigger_at=_stamp(-300), quality_at=_stamp(-120))
    _seed(env, "reviews.json", [_review(state="APPROVED")])
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "disparador-anterior-a-quality"


def test_collect_deadline_runs_from_the_trigger_not_from_this_step(tmp_path: Path) -> None:
    # Codex trabaja en paralelo a Claude: si el revisor Claude consumió toda la
    # ventana, aquí NO se concede un plazo nuevo completo. Con un disparador de
    # hace 600 s y un plazo de 300 s, el plazo absoluto ya venció.
    env = _setup(tmp_path)
    _write_state(tmp_path, trigger_at=_stamp(-600), quality_at=_stamp(-700))
    r = _run_collect(env, tmp_path, timeout="300")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "quedan 0 s" in r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"


def test_collect_still_polls_once_when_the_absolute_deadline_expired(tmp_path: Path) -> None:
    # Aunque el plazo absoluto haya vencido, si Codex respondió mientras Claude
    # trabajaba su resultado debe recogerse: sería un timeout falso perderlo.
    env = _setup(tmp_path)
    _write_state(tmp_path, trigger_at=_stamp(-600), quality_at=_stamp(-700))
    _seed(env, "reviews.json", [_review(state="APPROVED", submitted_at=_stamp(-500))])
    r = _run_collect(env, tmp_path, timeout="300")
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "APPROVED"
    assert result["reviewed_head_sha"] == HEAD


def test_trigger_fails_safely_when_identity_is_unknown(tmp_path: Path) -> None:
    # Sin identidad demostrada no se puede distinguir un disparador propio de
    # uno ajeno: parada segura (sin estado, la recolección fallará de forma
    # estructurada) en vez de reutilizar a ciegas o duplicar el disparador.
    env = _setup(tmp_path)
    (_md(env) / "fail_identity.txt").write_text("1", encoding="utf-8")
    r = _run_trigger(env, tmp_path)
    assert r.returncode != 0
    assert _post_count(env) == 0
    assert not (tmp_path / "state.json").exists()


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


def test_trigger_post_is_never_retried(tmp_path: Path) -> None:
    # El POST del disparador no es idempotente: un reintento a ciegas podría
    # publicar dos @codex review. Ante el fallo se falla limpio, sin duplicar.
    env = _setup(tmp_path)
    env["SIRIUS_RETRY_ATTEMPTS"] = "3"
    (_md(env) / "fail_post.txt").write_text("3", encoding="utf-8")
    r = _run_trigger(env, tmp_path)
    assert r.returncode != 0
    log = (_md(env) / "actions.log").read_text(encoding="utf-8")
    assert log.count("POST attempt failed") == 1
    assert _post_count(env) == 0
    assert not (tmp_path / "state.json").exists()


def test_trigger_recovers_when_post_applied_but_response_lost(tmp_path: Path) -> None:
    # El servidor aplicó el comentario pero la respuesta se perdió: la relectura
    # posterior encuentra el marcador y la ronda continúa sin duplicados.
    env = _setup(tmp_path)
    (_md(env) / "post_ghost.txt").write_text("1", encoding="utf-8")
    r = _run_trigger(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _post_count(env) == 1
    state = _state(tmp_path)
    comments = json.loads((_md(env) / "issue_comments.json").read_text(encoding="utf-8"))
    assert len(comments) == 1
    assert state["trigger_comment_id"] == comments[0]["id"]


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
    _seed(env, "pr.json", {"head": {"sha": HEAD}})
    _seed(env, "reactions_500.json", [{"content": "+1", "user": {"login": CONNECTOR}}])
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "APPROVED"
    assert result["reviewed_head_sha"] == HEAD
    assert result["trigger_comment_id"] == 500


def test_collect_thumbs_up_with_moved_head_fails_safely(tmp_path: Path) -> None:
    # La reacción +1 no lleva commit: solo se acepta si el head actual de la PR
    # sigue siendo el esperado. Un head movido durante la ronda es fallo seguro.
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "pr.json", {"head": {"sha": OTHER_HEAD}})
    _seed(env, "reactions_500.json", [{"content": "+1", "user": {"login": CONNECTOR}}])
    r = _run_collect(env, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "head-cambiado"


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


def test_collect_clamps_timeout_above_the_hard_cap(tmp_path: Path) -> None:
    # Una variable de repositorio con un valor excesivo no puede impedir que el
    # recolector escriba su resultado antes de que el paso del workflow expire:
    # la espera se limita al tope y el fallo seguro se emite igualmente.
    env = _setup(tmp_path)
    env["SIRIUS_CODEX_REVIEW_MAX_TIMEOUT_SECONDS"] = "0"
    _write_state(tmp_path)
    r = _run_collect(env, tmp_path, timeout="86400")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "se limita al tope" in r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"


def test_collect_cap_cannot_be_raised_above_the_absolute_limit(tmp_path: Path) -> None:
    # Un "tope" que se leyera solo de una variable de repositorio no sería un
    # tope: configurando espera y máximo a la vez, el recolector esperaría más
    # que el timeout del paso y Actions lo cancelaría antes de escribir su
    # FAILED_SAFELY. El absoluto en código no se puede subir.
    env = _setup(tmp_path)
    env["SIRIUS_CODEX_REVIEW_MAX_TIMEOUT_SECONDS"] = "3600"
    _write_state(tmp_path, trigger_at=_stamp(-7200), quality_at=_stamp(-7300))
    r = _run_collect(env, tmp_path, timeout="3600")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "se aplica el absoluto" in r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"


def test_collect_rejects_non_finite_or_negative_env_values(tmp_path: Path) -> None:
    # `float()` acepta "inf" y "-1": un infinito convertiría cualquier tope en
    # ausencia de tope y un negativo daría un plazo sin sentido.
    env = _setup(tmp_path)
    env["SIRIUS_CODEX_REVIEW_MAX_TIMEOUT_SECONDS"] = "inf"
    _write_state(tmp_path, trigger_at=_stamp(-7200), quality_at=_stamp(-7300))
    r = _run_collect(env, tmp_path, timeout="0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "finito y no negativo" in r.stderr
    assert _result(tmp_path)["status"] == "FAILED_SAFELY"


def test_collect_survives_a_transient_error_inside_one_gh_call(tmp_path: Path) -> None:
    # Un fallo aislado lo absorbe la capa de reintentos de `_gh_api`
    # (SIRIUS_RETRY_ATTEMPTS = 2 en estas pruebas): la pasada de sondeo ni se
    # entera.
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(state="APPROVED")])
    (_md(env) / "fail_remaining.txt").write_text("1", encoding="utf-8")
    r = _run_collect(env, tmp_path, timeout="5")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _result(tmp_path)["status"] == "APPROVED"
    assert "pasada de sondeo fallida" not in r.stderr


def test_collect_survives_a_whole_failed_poll_pass(tmp_path: Path) -> None:
    # Lo que esta prueba sí ejercita —y la anterior no podía— es el `except
    # GhError` del bucle de sondeo: agotados los reintentos, la pasada ENTERA
    # falla. El recolector no debe abortar ni degradar a aprobación: debe
    # reintentar en la pasada siguiente. Requisitos para llegar ahí: agotar los
    # reintentos (fallos >= SIRIUS_RETRY_ATTEMPTS) y que quede plazo absoluto
    # para una segunda pasada (disparador reciente y timeout amplio).
    env = _setup(tmp_path)
    _write_state(tmp_path, trigger_at=_stamp(-5))
    _seed(env, "reviews.json", [_review(state="APPROVED", submitted_at=_stamp(-1))])
    (_md(env) / "fail_remaining.txt").write_text("2", encoding="utf-8")
    r = _run_collect(env, tmp_path, timeout="120")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "pasada de sondeo fallida" in r.stderr
    assert _result(tmp_path)["status"] == "APPROVED"


# --------------------------------------------------------------------------- #
# Varias revisiones posteriores al disparador
# --------------------------------------------------------------------------- #


def test_collect_unions_findings_from_every_review_after_the_trigger(tmp_path: Path) -> None:
    # Codex puede publicar más de una revisión (una tanda de comentarios y
    # después otra). Quedarse con la última descartaría en silencio los
    # hallazgos de las anteriores.
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(
        env,
        "reviews.json",
        [
            _review(review_id=700, state="COMMENTED", submitted_at=_stamp(-40)),
            _review(review_id=701, state="COMMENTED", submitted_at=_stamp(-30)),
        ],
    )
    _seed(env, "review_comments_700.json", [_review_comment(801, "src/a.py", 1)])
    _seed(env, "review_comments_701.json", [_review_comment(802, "src/b.py", 2)])
    r = _run_collect(env, tmp_path, timeout="5")
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "CHANGES_REQUESTED"
    archivos = sorted(item["archivo"] for item in result["observations"])
    assert archivos == ["src/a.py:1", "src/b.py:2"]
    # La numeración es global y determinista sobre la unión.
    assert [item["id"] for item in result["observations"]] == ["CODEX-001", "CODEX-002"]


def test_a_later_approval_cannot_bury_earlier_findings(tmp_path: Path) -> None:
    # El caso peligroso: una revisión con hallazgos y, después, una aprobación.
    # Con "solo la última" la ronda aprobaría un head con defectos ya
    # reportados.
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(
        env,
        "reviews.json",
        [
            _review(review_id=700, state="CHANGES_REQUESTED", submitted_at=_stamp(-40)),
            _review(review_id=701, state="APPROVED", submitted_at=_stamp(-20)),
        ],
    )
    _seed(env, "review_comments_700.json", [_review_comment(801, "src/a.py", 1)])
    r = _run_collect(env, tmp_path, timeout="5")
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "CHANGES_REQUESTED"
    assert len(result["observations"]) == 1


def test_any_review_on_another_sha_stops_the_round(tmp_path: Path) -> None:
    # Basta una revisión que no demuestre haber auditado el head esperado: no
    # se puede saber si sus hallazgos (o su ausencia) se refieren a esta versión.
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(
        env,
        "reviews.json",
        [
            _review(review_id=700, state="APPROVED", submitted_at=_stamp(-40)),
            _review(
                review_id=701,
                state="COMMENTED",
                commit_id=OTHER_HEAD,
                submitted_at=_stamp(-20),
            ),
        ],
    )
    r = _run_collect(env, tmp_path, timeout="5")
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "sha-distinto"


def test_a_reaction_cannot_resolve_an_uninterpretable_review(tmp_path: Path) -> None:
    # Una revisión formal sin comentarios inline visibles es ambigua. Antes, al
    # devolver "seguir esperando", se consultaba la reacción 👍 del disparador y
    # esa señal —mucho más débil— convertía la ambigüedad en aprobación. Con una
    # revisión formal en curso, el 👍 no decide: se espera y, si no se aclara,
    # la ronda termina en fallo seguro.
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [_review(review_id=700, state="COMMENTED")])
    _seed(env, "review_comments_700.json", [])
    _seed(env, "reactions_500.json", [{"content": "+1", "user": {"login": CONNECTOR}}])
    r = _run_collect(env, tmp_path, timeout="0")
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "timeout"


def test_a_reaction_still_approves_when_there_is_no_formal_review(tmp_path: Path) -> None:
    # El camino de la reacción sigue vivo para su caso legítimo: Codex no abrió
    # revisión formal porque no encontró nada.
    env = _setup(tmp_path)
    _write_state(tmp_path)
    _seed(env, "reviews.json", [])
    _seed(env, "pr.json", {"head": {"sha": HEAD}})
    _seed(env, "reactions_500.json", [{"content": "+1", "user": {"login": CONNECTOR}}])
    r = _run_collect(env, tmp_path, timeout="0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _result(tmp_path)["status"] == "APPROVED"


# --------------------------------------------------------------------------- #
# Ventana de estabilidad: esperar a que Codex termine de publicar
# --------------------------------------------------------------------------- #


def test_collect_waits_for_a_review_published_after_the_first_pass(tmp_path: Path) -> None:
    # El conector publica en dos tandas. Devolver el resultado en cuanto la
    # primera revisión visible trae un comentario cerraría el sondeo y la
    # segunda revisión no se consultaría nunca: la unión perdería hallazgos y el
    # corrector recibiría una lista incompleta que parece completa.
    env = _setup(tmp_path)
    env["SIRIUS_CODEX_SETTLE_SECONDS"] = "0"
    _write_state(tmp_path, trigger_at=_stamp(-2))
    _seed(env, "reviews.json", [_review(review_id=700, submitted_at=_stamp(-1))])
    _seed(
        env,
        "reviews_late.json",
        [
            _review(review_id=700, submitted_at=_stamp(-1)),
            _review(review_id=701, submitted_at=_stamp(-1)),
        ],
    )
    _seed(env, "review_comments_700.json", [_review_comment(801, "src/a.py", 1)])
    _seed(env, "review_comments_701.json", [_review_comment(802, "src/b.py", 2)])

    r = _run_collect(env, tmp_path, timeout="120")
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "CHANGES_REQUESTED"
    archivos = sorted(item["archivo"] for item in result["observations"])
    assert archivos == ["src/a.py:1", "src/b.py:2"], (
        "el hallazgo de la segunda tanda debe recogerse, no perderse"
    )
    assert "se reinicia la espera" in r.stderr


def test_collect_delivers_what_it_has_when_the_deadline_beats_the_window(
    tmp_path: Path,
) -> None:
    # Con hallazgos a la vista y la ventana sin cerrar, vencer el plazo absoluto
    # debe entregar lo observado. Declarar un timeout perdiendo hallazgos ya
    # recogidos sería estrictamente peor.
    env = _setup(tmp_path)
    env["SIRIUS_CODEX_SETTLE_SECONDS"] = "900"
    _write_state(tmp_path)  # disparador hace 60 s
    _seed(env, "reviews.json", [_review(review_id=700)])
    _seed(env, "review_comments_700.json", [_review_comment(801)])

    r = _run_collect(env, tmp_path, timeout="5")  # plazo absoluto ya agotado
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "CHANGES_REQUESTED"
    assert len(result["observations"]) == 1
    assert "venció antes de cerrar la ventana" in r.stderr


def test_a_failed_safely_result_is_not_delayed_by_the_window(tmp_path: Path) -> None:
    # Una parada segura por SHA no mejora esperando: el motivo ya es definitivo.
    env = _setup(tmp_path)
    env["SIRIUS_CODEX_SETTLE_SECONDS"] = "900"
    _write_state(tmp_path, trigger_at=_stamp(-2))
    _seed(
        env,
        "reviews.json",
        [_review(review_id=700, commit_id=OTHER_HEAD, submitted_at=_stamp(-1))],
    )

    r = _run_collect(env, tmp_path, timeout="120")
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY"
    assert result["reason"] == "sha-distinto"


def test_a_stable_result_is_delivered_after_the_window(tmp_path: Path) -> None:
    # Si nada cambia, el resultado se entrega en cuanto la ventana se cierra:
    # la espera no puede volverse indefinida.
    env = _setup(tmp_path)
    env["SIRIUS_CODEX_SETTLE_SECONDS"] = "1"
    _write_state(tmp_path, trigger_at=_stamp(-2))
    _seed(
        env,
        "reviews.json",
        [_review(review_id=700, state="APPROVED", submitted_at=_stamp(-1))],
    )

    r = _run_collect(env, tmp_path, timeout="120")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _result(tmp_path)["status"] == "APPROVED"
    assert "se reinicia la espera" not in r.stderr


def test_a_late_ambiguous_review_invalidates_a_stabilizing_result(tmp_path: Path) -> None:
    # Codex aprueba y, mientras la ventana se estabiliza, abre una revisión
    # formal cuyos comentarios todavía no son visibles. Conservar la aprobación
    # dejaría que al vencer el plazo se aprobara el head pese a una revisión
    # pendiente que el propio recolector declara ambigua. La ambigüedad debe
    # descartar lo que se estaba estabilizando y terminar en fallo seguro.
    env = _setup(tmp_path)
    # El escenario exige que ocurran AL MENOS DOS pasadas antes de que venza el
    # plazo: la primera ve la aprobación y la segunda la revisión ambigua. Con
    # un disparador de hace 2 s y un plazo de 3 s el margen quedaba por debajo
    # del segundo —`_stamp` trunca a segundos enteros—, así que en un runner
    # lento solo daba tiempo a una pasada y la prueba aprobaba: verde en local y
    # roja en CI sobre el mismo commit. El plazo se fija con holgura suficiente
    # para que el número de pasadas no dependa de la máquina.
    _write_state(tmp_path, trigger_at=_stamp(0))
    _seed(
        env,
        "reviews.json",
        [_review(review_id=700, state="APPROVED", submitted_at=_stamp(0))],
    )
    _seed(
        env,
        "reviews_late.json",
        [
            _review(review_id=700, state="APPROVED", submitted_at=_stamp(0)),
            _review(review_id=701, state="COMMENTED", submitted_at=_stamp(0)),
        ],
    )
    _seed(env, "review_comments_701.json", [])  # sin comentarios inline visibles

    r = _run_collect(env, tmp_path, timeout="4")
    assert r.returncode == 0, r.stdout + r.stderr
    # Primero la evidencia de que el escenario se ejercitó de verdad: si solo
    # hubiera ocurrido una pasada, este mensaje no estaría y el fallo sería
    # ambiguo.
    assert "ha dejado de ser interpretable" in r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY", "no puede aprobarse con una revisión ambigua"
    assert result["reason"] == "timeout"


def test_a_failed_poll_pass_does_not_invalidate_a_stabilizing_result(tmp_path: Path) -> None:
    # Un error de transporte no es evidencia de ambigüedad: solo de que no se
    # pudo mirar. No debe descartar hallazgos ya observados.
    env = _setup(tmp_path)
    env["SIRIUS_CODEX_SETTLE_SECONDS"] = "1"
    _write_state(tmp_path, trigger_at=_stamp(-2))
    _seed(env, "reviews.json", [_review(review_id=700, submitted_at=_stamp(-1))])
    _seed(env, "review_comments_700.json", [_review_comment(801)])
    # Falla la SEGUNDA pasada por completo: con SIRIUS_RETRY_ATTEMPTS=2, sus dos
    # reintentos son las llamadas 2 y 3. La 1 y la 4 sí responden.
    (_md(env) / "fail_calls.txt").write_text("2,3", encoding="utf-8")

    r = _run_collect(env, tmp_path, timeout="60")
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "CHANGES_REQUESTED"
    assert len(result["observations"]) == 1
    assert "ha dejado de ser interpretable" not in r.stderr


def test_the_poll_pause_never_overshoots_the_deadline(tmp_path: Path) -> None:
    # Con un intervalo de sondeo mayor que el plazo restante, dormir el
    # intervalo completo hacía que el recolector terminara mucho después del
    # plazo que promete. La pausa se acota al tiempo que queda.
    import time as _time

    env = _setup(tmp_path)
    env["SIRIUS_CODEX_POLL_SECONDS"] = "120"
    _write_state(tmp_path, trigger_at=_stamp(-2))
    _seed(env, "reviews.json", [])  # nada que recoger: se agota el plazo

    started = _time.monotonic()
    r = _run_collect(env, tmp_path, timeout="3")
    elapsed = _time.monotonic() - started

    assert r.returncode == 0, r.stdout + r.stderr
    assert _result(tmp_path)["reason"] == "timeout"
    assert elapsed < 60, (
        f"el recolector tardó {elapsed:.0f} s con un plazo restante de ~1 s: "
        "la pausa no se está acotando al plazo"
    )


def test_one_uninterpretable_review_blocks_the_union_of_the_others(tmp_path: Path) -> None:
    # Una revisión trae hallazgos y otra, formal y no aprobatoria, todavía no
    # muestra sus comentarios inline. Devolver los hallazgos de la primera
    # dejaría que la ventana de estabilidad cerrara sobre una lista incompleta
    # —el mismo resultado se repite pasada tras pasada— y los hallazgos de la
    # segunda no llegarían nunca al corrector, con apariencia de lista completa.
    env = _setup(tmp_path)
    _write_state(tmp_path, trigger_at=_stamp(0))
    _seed(
        env,
        "reviews.json",
        [
            _review(review_id=700, state="COMMENTED", submitted_at=_stamp(0)),
            _review(review_id=701, state="COMMENTED", submitted_at=_stamp(0)),
        ],
    )
    _seed(env, "review_comments_700.json", [_review_comment(801, "src/a.py", 1)])
    _seed(env, "review_comments_701.json", [])  # aún sin comentarios visibles

    r = _run_collect(env, tmp_path, timeout="4")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "aún no muestra sus comentarios inline" in r.stderr
    result = _result(tmp_path)
    assert result["status"] == "FAILED_SAFELY", (
        "no puede entregarse una lista parcial mientras una revisión siga sin interpretar"
    )
    assert result["reason"] == "timeout"


def test_the_union_is_delivered_once_every_review_is_interpretable(tmp_path: Path) -> None:
    # Y en cuanto la revisión que faltaba muestra sus comentarios, la unión
    # completa se entrega: la exigencia no puede convertirse en un bloqueo
    # permanente.
    env = _setup(tmp_path)
    _write_state(tmp_path, trigger_at=_stamp(0))
    _seed(
        env,
        "reviews.json",
        [
            _review(review_id=700, state="COMMENTED", submitted_at=_stamp(0)),
            _review(review_id=701, state="COMMENTED", submitted_at=_stamp(0)),
        ],
    )
    _seed(env, "review_comments_700.json", [_review_comment(801, "src/a.py", 1)])
    _seed(env, "review_comments_701.json", [_review_comment(802, "src/b.py", 2)])

    r = _run_collect(env, tmp_path, timeout="30")
    assert r.returncode == 0, r.stdout + r.stderr
    result = _result(tmp_path)
    assert result["status"] == "CHANGES_REQUESTED"
    assert sorted(item["archivo"] for item in result["observations"]) == [
        "src/a.py:1",
        "src/b.py:2",
    ]
