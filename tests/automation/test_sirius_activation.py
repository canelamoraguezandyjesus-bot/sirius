"""Pruebas de la puerta de validación de activación (incidencia #60).

Ejercitan ``scripts/automation/sirius_validate_activation.sh`` con un ``gh``
simulado y con estado. Sin red ni ``gh`` real. Se omiten en Windows por las
mismas razones documentadas en ``test_sirius_issue.py``.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "scripts" / "automation" / "sirius_validate_activation.sh"


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

_GH_MOCK = r"""#!/usr/bin/env bash
D="$GH_MOCK_DIR"
echo "gh $*" >> "$D/calls.log"
sub="$1"; shift || true
case "$sub" in
  api)
    args="$*"
    # Las etiquetas vienen del OBJETO de la incidencia (`--jq '.labels[].name'`),
    # no de `/issues/<n>/labels` (ADR-027): se despacha por el FILTRO, porque la
    # ruta ya no distingue esta lectura de la del cuerpo, y se aplica el `--jq`
    # real del llamador para que un filtro equivocado no pueda pasar en verde.
    filtro_lbl=""; prev=""
    for a in "$@"; do [ "$prev" = "--jq" ] && filtro_lbl="$a"; prev="$a"; done
    if printf '%s' "$filtro_lbl" | grep -q '[.]labels'; then
      cat "$D/labels.txt" 2>/dev/null \
        | jq -R . | jq -sc '{labels: map(select(length>0) | {name: .})}' | jq -r "$filtro_lbl"
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/comments'; then
      cat "$D/comments.txt" 2>/dev/null; exit 0
    fi
    if printf '%s' "$args" | grep -q 'state'; then
      # Metadatos de la incidencia: {state, is_pr}
      st="$(cat "$D/state.txt" 2>/dev/null || echo open)"
      printf '{"state":"%s","is_pr":%s}\n' "$st" "${MOCK_IS_PR:-false}"
      exit 0
    fi
    # Cuerpo por REST
    cat "$D/body.txt" 2>/dev/null; exit 0
    ;;
  issue)
    action="$1"; shift || true
    case "$action" in
      view)
        if printf '%s' "$*" | grep -q comments; then
          cat "$D/comments.txt" 2>/dev/null
        else
          cat "$D/body.txt" 2>/dev/null
        fi
        exit 0;;
      edit)
        rem=""; prev=""
        for a in "$@"; do [ "$prev" = "--remove-label" ] && rem="$a"; prev="$a"; done
        if [ -n "$rem" ]; then
          if [ "${MOCK_FAIL_REMOVE:-0}" = "1" ]; then echo "remove fail" >&2; exit 1; fi
          if [ -f "$D/labels.txt" ]; then
            grep -Fxv "$rem" "$D/labels.txt" > "$D/labels.txt.tmp" 2>/dev/null
            mv "$D/labels.txt.tmp" "$D/labels.txt" 2>/dev/null || true
          fi
        fi
        exit 0;;
      comment)
        if [ "${MOCK_FAIL_COMMENT:-0}" = "1" ]; then echo "comment fail" >&2; exit 1; fi
        bf=""; prev=""
        for a in "$@"; do [ "$prev" = "--body-file" ] && bf="$a"; prev="$a"; done
        if [ -n "$bf" ]; then
          cat "$bf" >> "$D/comments.txt"
          printf '\n' >> "$D/comments.txt"
        fi
        echo "COMMENT" >> "$D/actions.log"; exit 0;;
    esac;;
esac
exit 0
"""

_PERFILES = REPO_ROOT / "docs" / "implementation" / "work_engine" / "perfiles"


def _version_vigente(rol: str) -> int:
    """La `version:` del perfil, leida como la lee la puerta (ADR-221): con la stdlib."""
    texto = (_PERFILES / f"{rol}.yml").read_text(encoding="utf-8")
    encontrada = re.search(r"^version:\s*(\d+)\s*$", texto, re.MULTILINE)
    assert encontrada is not None, f"{rol}.yml no declara version"
    return int(encontrada.group(1))


_VIGENTE = _version_vigente("implementer")

# El cuerpo completo lleva el `Perfil: rol@N` que todo encargo declara desde C3
# (#333) y que la puerta resuelve desde ADR-221; sin el, el implementador
# pararia en rojo a los seis segundos (#653).
_COMPLETE_BODY = (
    "## Work ID\nSIRIUS-B5-001\n\n## Bloque\nB5\n\n"
    f"Perfil: implementer@{_VIGENTE}\n\n## Objetivo\n"
    + ("Panel de contexto completo. " * 10)
    + "\n\n## Base y dependencias\nB4a-B4f fusionados.\n\n## Alcance permitido\nPanel.\n\n"
    "## Fuera de alcance\nB6, RAG.\n\n"
    "## Requisitos y pruebas de aceptación\nPA-0xx.\n\n"
    "## Validaciones obligatorias\n- pytest\n\n## Rama base\nmain\n\n"
    "## Condiciones de parada\nREADY_FOR_REVIEW\n\n## Salvaguardas\nNo merge automático.\n"
)

# El cuerpo real truncado de #60: termina a mitad de frase en "modelos de".
_TRUNCATED_BODY = (
    "## Work ID\n\nSIRIUS-B5-001\n\n## Bloque\n\nB5 — Panel de contexto completo\n\n"
    "## Objetivo\n\nCompletar la superficie de contexto aprobada.\n\n"
    "## Base y dependencias\n\n- Reutilizar casos de uso; no crear repositorios, modelos de"
)


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
    env["REPOSITORY_OWNER"] = "canela"
    return env


def _md(env: dict[str, str]) -> Path:
    return Path(env["GH_MOCK_DIR"])


def _seed(
    env: dict[str, str],
    labels: list[str],
    body: str = _COMPLETE_BODY,
    state: str = "open",
) -> None:
    md = _md(env)
    (md / "labels.txt").write_text("".join(f"{x}\n" for x in labels), encoding="utf-8")
    (md / "body.txt").write_text(body, encoding="utf-8")
    (md / "state.txt").write_text(state, encoding="utf-8")
    (md / "comments.txt").write_text("", encoding="utf-8")


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(GATE), "owner/repo", "60"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _labels(env: dict[str, str]) -> str:
    return (_md(env) / "labels.txt").read_text(encoding="utf-8")


def _comments(env: dict[str, str]) -> str:
    return (_md(env) / "comments.txt").read_text(encoding="utf-8")


def test_valid_activation_passes_without_changes(tmp_path: Path) -> None:
    # Una incidencia correctamente planificada (planned + cuerpo completo) se
    # activa sin caer en FAILED_SAFELY: la puerta no toca nada.
    env = _setup(tmp_path)
    _seed(env, ["sirius:planned", "sirius:implement-requested"])
    r = _run(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Activacion valida" in r.stdout
    assert "sirius:implement-requested" in _labels(env)  # el evento sigue vivo
    assert "sirius:planned" in _labels(env)
    assert _comments(env) == ""  # silenciosa cuando todo es correcto
    assert "sirius:failed-safely" not in _labels(env)


def test_missing_planned_rejects_without_adding_planned(tmp_path: Path) -> None:
    # Caso real 1 de #60: activación directa sin planned. Se retira el evento,
    # se explica el motivo y NUNCA se añade planned automáticamente.
    env = _setup(tmp_path)
    _seed(env, ["sirius:implement-requested"])
    r = _run(env)
    assert r.returncode == 0, r.stdout + r.stderr
    labels = _labels(env)
    assert "sirius:implement-requested" not in labels
    assert "sirius:planned" not in labels  # prohibido auto-aprobar planificación
    assert "sirius:failed-safely" not in labels  # rechazo temprano, no parada
    comments = _comments(env)
    assert "sirius-activation:rejected:sin-planned" in comments
    assert "@canela" in comments


def test_truncated_body_rejects_activation(tmp_path: Path) -> None:
    # Caso real 2 de #60: planned presente pero cuerpo truncado a mitad de frase.
    env = _setup(tmp_path)
    _seed(env, ["sirius:planned", "sirius:implement-requested"], body=_TRUNCATED_BODY)
    r = _run(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sirius:implement-requested" not in _labels(env)
    assert "sirius-activation:rejected:cuerpo-incompleto" in _comments(env)
    assert "sirius:planned" in _labels(env)  # planned se conserva


def test_failed_safely_state_blocks_reactivation(tmp_path: Path) -> None:
    # Reactivar con failed-safely aún presente exige retirarla conscientemente.
    env = _setup(tmp_path)
    _seed(env, ["sirius:planned", "sirius:failed-safely", "sirius:implement-requested"])
    r = _run(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sirius:implement-requested" not in _labels(env)
    assert "sirius-activation:rejected:estado-incompatible" in _comments(env)


def test_duplicate_activation_while_implementing_rejects(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed(env, ["sirius:implementing", "sirius:implement-requested"])
    r = _run(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sirius:implement-requested" not in _labels(env)
    assert "estado-incompatible" in _comments(env)
    assert "sirius:implementing" in _labels(env)  # el estado en curso no se toca


def test_closed_issue_rejects_activation(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed(env, ["sirius:planned", "sirius:implement-requested"], state="closed")
    r = _run(env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sirius-activation:rejected:incidencia-cerrada" in _comments(env)


def test_repeated_rejection_does_not_duplicate_comment(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed(env, ["sirius:implement-requested"])
    assert _run(env).returncode == 0
    # El usuario repite el mismo error: re-aplica el evento sin arreglar nada.
    md = _md(env)
    with open(md / "labels.txt", "a", encoding="utf-8") as fh:
        fh.write("sirius:implement-requested\n")
    assert _run(env).returncode == 0
    assert _comments(env).count("sirius-activation:rejected:sin-planned") == 1
    assert "sirius:implement-requested" not in _labels(env)


def test_different_reason_gets_its_own_comment(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed(env, ["sirius:implement-requested"])
    assert _run(env).returncode == 0  # rechazo: sin-planned
    md = _md(env)
    (md / "labels.txt").write_text("sirius:planned\nsirius:implement-requested\n", encoding="utf-8")
    (md / "body.txt").write_text(_TRUNCATED_BODY, encoding="utf-8")
    assert _run(env).returncode == 0  # rechazo: cuerpo-incompleto
    comments = _comments(env)
    assert "rejected:sin-planned" in comments
    assert "rejected:cuerpo-incompleto" in comments


def test_removal_failure_is_retryable(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["MOCK_FAIL_REMOVE"] = "1"
    _seed(env, ["sirius:implement-requested"])
    r = _run(env)
    assert r.returncode != 0  # visible y reintentable: el evento no se retiró


def test_pull_request_is_ignored(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    env["MOCK_IS_PR"] = "true"
    _seed(env, ["sirius:implement-requested"])
    r = _run(env)
    assert r.returncode == 0
    assert "sirius:implement-requested" in _labels(env)
    assert _comments(env) == ""


def test_a_rejection_without_diagnosis_keeps_the_label(tmp_path: Path) -> None:
    """Sin diagnóstico publicado, la etiqueta NO se retira.

    `reject()` registraba el fallo de `sirius_comment_once` y seguía retirando
    `sirius:implement-requested` igualmente. La incidencia quedaba solo en
    `sirius:planned`: sin comentario, sin etiqueta de evento y sin nada que la
    reviva. Y además invisible para el reconciliador, porque `planned` es un
    estado de reposo legítimo y no está en `MACHINE_LABELS`.

    Es la clase de fallo que la incidencia #138 vino a eliminar —un callejón
    mudo— reintroducida por la puerta que debía protegerla. Hallazgo P2 de Codex
    en la PR #146.

    Conservando la etiqueta se pierde tiempo, no la incidencia: el estado queda
    como estaba y el próximo intento vuelve a rechazar, con diagnóstico si la
    publicación ya funciona.
    """
    env = _setup(tmp_path)
    env["MOCK_FAIL_COMMENT"] = "1"
    # Sin `sirius:planned`: la puerta rechaza, y al rechazar no podrá comentar.
    _seed(env, ["sirius:implement-requested"])

    r = _run(env)

    assert r.returncode != 0, "un rechazo sin diagnóstico tiene que ser visible y reintentable"
    etiquetas = (_md(env) / "labels.txt").read_text(encoding="utf-8")
    assert "sirius:implement-requested" in etiquetas, (
        "se retiró la etiqueta sin dejar diagnóstico: la incidencia queda muda "
        f"y nada la revive. Etiquetas: {etiquetas!r}"
    )
    assert "sirius-activation:rejected" not in (_md(env) / "comments.txt").read_text(
        encoding="utf-8"
    ), "la prueba no está ejercitando el fallo de publicación"


# --- El Perfil se resuelve en la puerta (ADR-221) ------------------------------


def _sin_perfil(cuerpo: str) -> str:
    return "\n".join(linea for linea in cuerpo.splitlines() if not linea.startswith("Perfil:"))


def test_un_cuerpo_sin_perfil_se_rechaza_antes_de_arrancar(tmp_path: Path) -> None:
    """#653 murio a los seis segundos en el implementador; la puerta lo dice antes y gratis."""
    env = _setup(tmp_path)
    _seed(env, ["sirius:planned", "sirius:implement-requested"], body=_sin_perfil(_COMPLETE_BODY))
    proc = _run(env)
    assert proc.returncode == 0, proc.stderr
    assert "sirius:implement-requested" not in _labels(env)
    assert "sirius:planned" in _labels(env)
    publicado = _comments(env)
    assert "sirius-activation:rejected:perfil-sin-resolver" in publicado
    assert "no declara 'Perfil: rol@N'" in publicado, "el rechazo lleva el detalle del resolutor"


def test_un_perfil_desconocido_se_rechaza_con_el_detalle_del_resolutor(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    cuerpo = _COMPLETE_BODY.replace(f"Perfil: implementer@{_VIGENTE}", "Perfil: implementer@99")
    _seed(env, ["sirius:planned", "sirius:implement-requested"], body=cuerpo)
    proc = _run(env)
    assert proc.returncode == 0, proc.stderr
    assert "sirius:implement-requested" not in _labels(env)
    publicado = _comments(env)
    assert "rejected:perfil-sin-resolver" in publicado
    assert "implementer@99" in publicado and "no está en el manifiesto" in publicado


def test_un_perfil_valido_pero_no_vigente_avisa_y_deja_pasar(tmp_path: Path) -> None:
    """`rol@N` significa un texto (H-28): una version antigua se ejecuta, pero se dice."""
    env = _setup(tmp_path)
    cuerpo = _COMPLETE_BODY.replace(f"Perfil: implementer@{_VIGENTE}", "Perfil: implementer@2")
    _seed(env, ["sirius:planned", "sirius:implement-requested"], body=cuerpo)
    proc = _run(env)
    assert proc.returncode == 0, proc.stderr
    assert "sirius:implement-requested" in _labels(env), "no vigente no es motivo de rechazo"
    publicado = _comments(env)
    assert "sirius-activation:aviso:perfil-no-vigente:implementer@2" in publicado
    assert f"es la {_VIGENTE}" in publicado and "rejected" not in publicado
    assert (
        "Si sigue en `sirius:planned`" in publicado
        and "otra vez justo antes de consumir" in publicado
        and "declara el evento rancio" in publicado
        and "Si ya esta en `sirius:implementing`" in publicado
        and "cancela desde Actions el run" in publicado
        and "escribe `continua`" in publicado
        and "no se ejecutara en esta incidencia" in publicado
        and "ADR-094" in publicado
    ), (
        "el aviso prescribe segun el estado real al leerlo (en `planned`: editar, que vuelve "
        "rancio el evento, y reactivar; en `implementing`: cancelar y `continua`; dejar "
        "terminar: la vigente no se ejecuta aqui) y cita ADR-094: Codex, PR #670, rondas 2 a 7"
    )


def test_el_perfil_vigente_pasa_sin_ningun_comentario(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _seed(env, ["sirius:planned", "sirius:implement-requested"])
    proc = _run(env)
    assert proc.returncode == 0, proc.stderr
    assert "sirius:implement-requested" in _labels(env)
    assert _comments(env).strip() == "", "con el perfil vigente la puerta no dice nada"


def test_un_perfil_ajeno_al_carril_de_ejecucion_no_se_juzga_en_esta_puerta(tmp_path: Path) -> None:
    """`investigador` no resuelve en el carril de ejecucion y no tiene por que: su
    ejecutor es el investigador medido (`investigar-orden.yml`), con su propia
    puerta de reparto. Esta puerta no afirma nada sobre un rol que no es suyo."""
    env = _setup(tmp_path)
    cuerpo = _COMPLETE_BODY.replace(f"Perfil: implementer@{_VIGENTE}", "Perfil: investigador@2")
    _seed(env, ["sirius:planned", "sirius:implement-requested"], body=cuerpo)
    proc = _run(env)
    assert proc.returncode == 0, proc.stderr
    assert "sirius:implement-requested" in _labels(env)
    assert _comments(env).strip() == "", "ni rechazo ni aviso: no es su carril"
    assert "no lo juzga" in proc.stdout


def test_una_instantanea_igual_al_cuerpo_se_juzga_y_se_rechaza_si_no_resuelve(
    tmp_path: Path,
) -> None:
    """El implementador resuelve la instantánea del evento (`ISSUE_BODY`): cuando
    coincide con el cuerpo vigente, es lo que se juzga, y si no resuelve se
    rechaza con la etiqueta retirada (Codex, PR #670, ronda 1)."""
    env = _setup(tmp_path)
    cuerpo = _COMPLETE_BODY.replace(f"Perfil: implementer@{_VIGENTE}", "Perfil: implementer@99")
    _seed(env, ["sirius:planned", "sirius:implement-requested"], body=cuerpo)
    env["ISSUE_BODY"] = cuerpo
    proc = _run(env)
    assert proc.returncode == 0, proc.stderr
    assert "sirius:implement-requested" not in _labels(env), "lo que se iba a ejecutar no resuelve"
    assert "perfil-sin-resolver" in _comments(env)


def test_un_evento_cuyo_perfil_cambio_despues_es_rancio_y_no_toca_ninguna_etiqueta(
    tmp_path: Path,
) -> None:
    """Ronda 5 de Codex en la PR #670: si alguien edita el `Perfil:` después de la
    etiqueta y la retira y vuelve a aplicar, la `sirius:implement-requested` que
    hay ahora es la de OTRA activación; esta puerta, que corre en su propio
    workflow y puede llegar tarde, retiraba esa etiqueta al rechazar la
    instantánea vieja y el trabajo se perdía. Mismo razonamiento que el reparto
    (ADR-167) aplicado al `rol@N` entero: no se valida, no se ejecuta, no se
    toca nada, y se dice."""
    env = _setup(tmp_path)
    _seed(env, ["sirius:planned", "sirius:implement-requested"])
    env["ISSUE_BODY"] = _COMPLETE_BODY.replace(
        f"Perfil: implementer@{_VIGENTE}", "Perfil: implementer@99"
    )
    proc = _run(env)
    assert proc.returncode == 2, proc.stderr
    assert "sirius:implement-requested" in _labels(env), "la etiqueta puede ser de otro evento"
    publicado = _comments(env)
    assert f"sirius-activation:evento-rancio:implementer@99:implementer@{_VIGENTE}" in publicado
    assert "no se valida ni se ejecuta" in publicado and "ninguna etiqueta" in publicado
    assert "rejected" not in publicado
    assert "rancio" in proc.stderr

    # Repetir el mismo evento rancio no duplica el aviso ni toca nada.
    antes = publicado
    proc = _run(env)
    assert proc.returncode == 2
    assert _comments(env) == antes and "sirius:implement-requested" in _labels(env)


def test_un_rol_que_no_esta_en_ningun_carril_se_rechaza(tmp_path: Path) -> None:
    """Una errata (`implementr`) no es un carril ajeno: el reparto la mandaría al
    implementador y moriría allí. Solo se exime lo que otro carril del manifiesto
    reclama como suyo (Codex, PR #670)."""
    env = _setup(tmp_path)
    cuerpo = _COMPLETE_BODY.replace(f"Perfil: implementer@{_VIGENTE}", "Perfil: implementr@4")
    _seed(env, ["sirius:planned", "sirius:implement-requested"], body=cuerpo)
    proc = _run(env)
    assert proc.returncode == 0, proc.stderr
    assert "sirius:implement-requested" not in _labels(env)
    assert "perfil-sin-resolver" in _comments(env)
    assert "no lo juzga" not in proc.stdout


def test_una_instantanea_vacia_del_evento_es_un_evento_rancio(tmp_path: Path) -> None:
    """El evento llegó sin cuerpo y alguien lo escribió después: el implementador
    ejecutaría la instantánea vacía. La puerta no la sustituye por el cuerpo
    actual (Codex, PR #670, ronda 2) ni retira la etiqueta, que puede ser de una
    activación posterior (ronda 5): el evento es rancio y se dice."""
    env = _setup(tmp_path)
    _seed(env, ["sirius:planned", "sirius:implement-requested"])
    env["ISSUE_BODY"] = ""
    proc = _run(env)
    assert proc.returncode == 2, proc.stderr
    assert "sirius:implement-requested" in _labels(env)
    assert f"sirius-activation:evento-rancio:ninguno:implementer@{_VIGENTE}" in _comments(env)


def test_la_comparacion_del_evento_usa_el_parser_canonico_del_perfil(tmp_path: Path) -> None:
    """Ronda 6 de Codex en la PR #670: un `sed` propio leía `implementer@4junk` como
    `implementer@4` y daba por iguales una instantánea que el resolutor no puede
    leer y un cuerpo vigente válido; la puerta seguía, rechazaba la instantánea y
    retiraba una etiqueta que puede ser de otra activación. Las dos se leen ahora
    con `profile_field`, el parser del resolutor: `implementer@Njunk` no es un
    perfil, así que el evento es rancio (`ninguno` frente al vigente)."""
    env = _setup(tmp_path)
    _seed(env, ["sirius:planned", "sirius:implement-requested"])
    env["ISSUE_BODY"] = _COMPLETE_BODY.replace(
        f"Perfil: implementer@{_VIGENTE}", f"Perfil: implementer@{_VIGENTE}junk"
    )
    proc = _run(env)
    assert proc.returncode == 2, proc.stderr
    assert "sirius:implement-requested" in _labels(env), "la etiqueta puede ser de otro evento"
    assert f"sirius-activation:evento-rancio:ninguno:implementer@{_VIGENTE}" in _comments(env)
