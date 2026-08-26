"""Reanudar una parada, ejecutando el guion de verdad.

`test_reanudar_una_parada.py` comprueba el invariante leyendo los ficheros. Eso
es útil y barato, pero tiene un techo que este módulo existe para cubrir, y no
es teórico: al sembrar la mutación de control —sacar `sirius:failed-safely` del
conjunto de paradas reanudables y de su rama `case`— la prueba estática pasó en
verde **dos veces seguidas**. La primera porque el nombre seguía apareciendo en
un comentario de cabecera; la segunda, ya filtrando comentarios, porque seguía
apareciendo dentro de un mensaje de error.

Es la misma familia de defecto que este repositorio lleva un año corrigiendo:
una comprobación que se conforma con que algo se MENCIONE certifica
documentación, no comportamiento. Aquí se ejecuta `sirius_resume_on_command.sh`
contra un `gh` simulado y se mira qué etiquetas quedan puestas.
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
SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_resume_on_command.sh"


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
ISSUE = 193
COMMENT_ID = "555"
PR = 194
HEAD = "e90e984ac5ba7fd8f3ea8830d10932c25c324eba"

# `gh` simulado. Las etiquetas se leen del OBJETO de la incidencia (ADR-027), así
# que el despacho es por el FILTRO real del llamador, no por la ruta: un `--jq`
# equivocado no puede pasar en verde. `GH_MOCK_FAIL_COMMENTS=1` simula una
# lectura caída, que NO es lo mismo que un historial vacío.
_GH_MOCK = r"""#!/usr/bin/env bash
D="$GH_MOCK_DIR"
echo "gh $*" >> "$D/calls.log"
sub="$1"; shift || true

filtro=""; prev=""
for a in "$@"; do [ "$prev" = "--jq" ] && filtro="$a"; prev="$a"; done

case "$sub" in
  api)
    args="$*"
    n="$(printf '%s' "$args" | grep -oE 'issues/[0-9]+' | head -1 | cut -d/ -f2)"
    if printf '%s' "$args" | grep -q '/pulls/'; then
      pr="$(printf '%s' "$args" | grep -oE 'pulls/[0-9]+' | cut -d/ -f2)"
      [ -f "$D/pr_${pr}.json" ] || exit 1
      if [ -n "$filtro" ]; then jq -c "$filtro" "$D/pr_${pr}.json"; else cat "$D/pr_${pr}.json"; fi
      exit 0
    fi
    if printf '%s' "$args" | grep -q '/comments'; then
      [ "${GH_MOCK_FAIL_COMMENTS:-0}" = "1" ] && { echo "503" >&2; exit 1; }
      cat "$D/comments_${n}.txt" 2>/dev/null
      exit 0
    fi
    if printf '%s' "$filtro" | grep -q '[.]labels'; then
      [ "${GH_MOCK_FAIL_LABELS:-0}" = "1" ] && { echo "503" >&2; exit 1; }
      cat "$D/labels_${n}.txt" 2>/dev/null \
        | jq -R . | jq -sc '{labels: map(select(length>0) | {name: .})}' | jq -r "$filtro"
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
        [ "${GH_MOCK_FAIL_COMMENTS:-0}" = "1" ] && exit 1
        if printf '%s' "$*" | grep -q comments; then cat "$D/comments_${num}.txt" 2>/dev/null
        else cat "$D/body_${num}.txt" 2>/dev/null; fi
        exit 0;;
      comment)
        bf=""; prev=""
        for a in "$@"; do [ "$prev" = "--body-file" ] && bf="$a"; prev="$a"; done
        if [ -n "$bf" ]; then
          cat "$bf" >> "$D/comments_${num}.txt"; printf '\n' >> "$D/comments_${num}.txt"
        fi
        echo "COMMENT ${num}" >> "$D/actions.log"; exit 0;;
      edit)
        add=""; rem=""; prev=""
        for a in "$@"; do
          [ "$prev" = "--add-label" ] && add="$a"
          [ "$prev" = "--remove-label" ] && rem="$a"
          prev="$a"
        done
        if [ -n "$add" ]; then
          grep -Fxq "$add" "$D/labels_${num}.txt" 2>/dev/null \
            || echo "$add" >> "$D/labels_${num}.txt"
          echo "ADD ${add}" >> "$D/actions.log"
        fi
        if [ -n "$rem" ]; then
          grep -Fxv "$rem" "$D/labels_${num}.txt" > "$D/labels_${num}.tmp" 2>/dev/null || :
          mv "$D/labels_${num}.tmp" "$D/labels_${num}.txt"
          echo "REMOVE ${rem}" >> "$D/actions.log"
        fi
        exit 0;;
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


def _sembrar(env: dict[str, str], *, etiquetas: list[str], historial: str) -> None:
    md = _md(env)
    (md / f"labels_{ISSUE}.txt").write_text("".join(f"{x}\n" for x in etiquetas), encoding="utf-8")
    (md / f"comments_{ISSUE}.txt").write_text(historial, encoding="utf-8")
    (md / f"body_{ISSUE}.txt").write_text("cuerpo de la incidencia", encoding="utf-8")
    (md / f"pr_{PR}.json").write_text(
        json.dumps({"state": "open", "merged": False, "head": {"sha": HEAD}}),
        encoding="utf-8",
    )


def _historial(marcador_de_parada: str) -> str:
    """Historial mínimo: la URL de la PR (para localizarla) y la parada."""
    return f"https://github.com/{REPO}/pull/{PR}\n- Head SHA: `{HEAD}`\n{marcador_de_parada}\n"


def _ejecutar(env: dict[str, str], orden: str = "continua") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), REPO, str(ISSUE), COMMENT_ID, orden],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _etiquetas(env: dict[str, str]) -> list[str]:
    fichero = _md(env) / f"labels_{ISSUE}.txt"
    if not fichero.exists():
        return []
    return [x for x in fichero.read_text(encoding="utf-8").splitlines() if x.strip()]


def _comentarios(env: dict[str, str]) -> str:
    fichero = _md(env) / f"comments_{ISSUE}.txt"
    return fichero.read_text(encoding="utf-8") if fichero.exists() else ""


# --------------------------------------------------------------------------- #
# El desenlace que motivó todo esto: la #193, parada por un timeout de Codex
# --------------------------------------------------------------------------- #


def test_una_parada_segura_del_revisor_vuelve_a_revision(tmp_path: Path) -> None:
    """El caso real: Quality en verde, Codex no contestó, ciclo parado.

    Sin esto, la única salida era aplicar la etiqueta a mano — la cirugía que
    ADR-030 vino a eliminar y que se dejó a medias.
    """
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial(f"<!-- sirius-verdict:reviewer:FAILED_SAFELY:{HEAD} -->"),
    )
    resultado = _ejecutar(env)
    assert resultado.returncode == 0, resultado.stderr
    assert "sirius:review-requested" in _etiquetas(env)
    assert "sirius:failed-safely" not in _etiquetas(env)


def test_una_parada_segura_del_corrector_vuelve_a_correccion(tmp_path: Path) -> None:
    """La fase se lee del historial; no es fija."""
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial(f"<!-- sirius-verdict:corrector:FAILED_SAFELY:{HEAD} -->"),
    )
    resultado = _ejecutar(env)
    assert resultado.returncode == 0, resultado.stderr
    assert "sirius:repair-requested" in _etiquetas(env)
    assert "sirius:review-requested" not in _etiquetas(env)


def test_una_parada_precheck_tambien_sabe_de_que_fase_vino(tmp_path: Path) -> None:
    """`stop_safely` publica `:precheck:` y también deja `failed-safely`."""
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial("<!-- sirius-verdict:implementer:precheck:sin-veredicto:run-1 -->"),
    )
    resultado = _ejecutar(env)
    assert resultado.returncode == 0, resultado.stderr
    assert "sirius:implement-requested" in _etiquetas(env)


def test_manda_la_ultima_parada_publicada(tmp_path: Path) -> None:
    """Un historial largo tiene paradas viejas; la vigente es la última."""
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=(
            f"https://github.com/{REPO}/pull/{PR}\n"
            "<!-- sirius-verdict:implementer:FAILED_SAFELY:aaa111 -->\n"
            "<!-- sirius-verdict:corrector:FAILED_SAFELY:bbb222 -->\n"
            f"<!-- sirius-verdict:reviewer:FAILED_SAFELY:{HEAD} -->\n"
        ),
    )
    resultado = _ejecutar(env)
    assert resultado.returncode == 0, resultado.stderr
    assert "sirius:review-requested" in _etiquetas(env)


def test_una_parada_segura_no_publica_el_marcador_que_perdona_rondas(
    tmp_path: Path,
) -> None:
    """Reanudar una fase caída no borra el listón de convergencia.

    Si lo borrase, un ciclo de verdad estancado podría correr para siempre
    encadenando paradas operativas.
    """
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial(f"<!-- sirius-verdict:reviewer:FAILED_SAFELY:{HEAD} -->"),
    )
    assert _ejecutar(env).returncode == 0
    assert "sirius-convergence-reset" not in _comentarios(env)
    assert "sirius-resume-stop" in _comentarios(env)


# --------------------------------------------------------------------------- #
# Lo que ya funcionaba (ADR-030) tiene que seguir funcionando
# --------------------------------------------------------------------------- #


def test_la_parada_por_convergencia_sigue_reanudando_al_corrector(
    tmp_path: Path,
) -> None:
    env = _setup(tmp_path)
    _sembrar(env, etiquetas=["sirius:blocked-decision"], historial=_historial(""))
    resultado = _ejecutar(env)
    assert resultado.returncode == 0, resultado.stderr
    assert "sirius:repair-requested" in _etiquetas(env)
    assert "sirius:blocked-decision" not in _etiquetas(env)
    assert f"<!-- sirius-convergence-reset:{HEAD} -->" in _comentarios(env)


# --------------------------------------------------------------------------- #
# Lo que NO debe pasar
# --------------------------------------------------------------------------- #


def test_sin_parada_publicada_no_adivina_la_fase(tmp_path: Path) -> None:
    """Adivinar reanudaría la fase equivocada; se para y se explica."""
    env = _setup(tmp_path)
    _sembrar(env, etiquetas=["sirius:failed-safely"], historial=_historial(""))
    resultado = _ejecutar(env)
    assert resultado.returncode != 0
    assert _etiquetas(env) == ["sirius:failed-safely"]
    assert "No he podido reanudar el ciclo" in _comentarios(env)


def test_un_historial_ilegible_no_es_un_historial_vacio(tmp_path: Path) -> None:
    """La invariante de siempre: no pude leer =/= leí y no hay."""
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial(f"<!-- sirius-verdict:reviewer:FAILED_SAFELY:{HEAD} -->"),
    )
    env["GH_MOCK_FAIL_COMMENTS"] = "1"
    resultado = _ejecutar(env)
    assert resultado.returncode != 0
    assert "sirius:review-requested" not in _etiquetas(env)

    # Lo que sí está garantizado hoy: no se reanuda nada a ciegas.
    assert "sirius:failed-safely" in _etiquetas(env), (
        "la parada se levantó sin haber podido leer en qué estado estaba"
    )


def test_el_diagnostico_de_una_lectura_caida_no_debe_afirmar_que_no_hay_pr(
    tmp_path: Path,
) -> None:
    """La familia de defecto que este repositorio lleva un año corrigiendo.

    Nació como `xfail` en ADR-035, describiendo el defecto sin arreglarlo: con
    los comentarios ilegibles, el guion publicaba «No he encontrado ninguna PR
    asociada a esta incidencia». Falso — la PR estaba ahí, lo que falló fue la
    lectura — y el propietario lo recibía como diagnóstico.

    La diferencia importa porque las dos situaciones piden cosas distintas: una
    lectura caída es reintentable y no exige nada de nadie; una PR de verdad
    ausente sí. Decir la segunda cuando pasó la primera manda a una persona a
    buscar un problema que no existe.

    `sirius_find_pr_for_issue` devuelve ahora 2 cuando no pudo leer, y los tres
    ejecutores que la usan distinguen ese caso (ADR-036).
    """
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial(f"<!-- sirius-verdict:reviewer:FAILED_SAFELY:{HEAD} -->"),
    )
    env["GH_MOCK_FAIL_COMMENTS"] = "1"
    resultado = _ejecutar(env)
    salida = resultado.stdout + resultado.stderr
    assert resultado.returncode != 0
    assert "No he encontrado ninguna PR" not in salida, (
        "una lectura caída se está reportando como ausencia de PR"
    )
    assert "Reintentable" in salida, "una lectura caída tiene que decir que se puede reintentar"
    # Y no publica el diagnóstico de la ausencia, que le pediría al propietario
    # actuar sobre algo que nunca se llegó a leer.
    assert "No he podido reanudar el ciclo" not in _comentarios(env)
    assert "sirius:failed-safely" in _etiquetas(env)


def test_una_incidencia_sin_parada_no_se_toca(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _sembrar(env, etiquetas=["sirius:reviewing"], historial=_historial(""))
    resultado = _ejecutar(env)
    assert resultado.returncode == 0
    assert _etiquetas(env) == ["sirius:reviewing"]


def test_la_orden_tiene_que_ser_exacta(tmp_path: Path) -> None:
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial(f"<!-- sirius-verdict:reviewer:FAILED_SAFELY:{HEAD} -->"),
    )
    resultado = _ejecutar(env, orden="continua cuando puedas")
    assert resultado.returncode == 0
    assert _etiquetas(env) == ["sirius:failed-safely"]


def test_la_orden_vale_aunque_lleve_la_firma_que_anade_la_herramienta(tmp_path: Path) -> None:
    """Una firma anexada por el servidor no puede invalidar la orden.

    Pasó de verdad: dos incidencias quedaron bloqueadas porque quien podía dar
    la orden comentaba por API, y la herramienta le añadía sola un bloque de
    atribución detrás. El cuerpo dejaba de ser exactamente `continua` y la
    guarda lo rechazaba, correctamente pero por el motivo equivocado.
    """
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial(f"<!-- sirius-verdict:reviewer:FAILED_SAFELY:{HEAD} -->"),
    )
    resultado = _ejecutar(
        env,
        orden="continua\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_",
    )
    assert resultado.returncode == 0
    assert _etiquetas(env) == ["sirius:review-requested"], resultado.stdout + resultado.stderr


def test_el_texto_antes_de_la_firma_sigue_invalidando_la_orden(tmp_path: Path) -> None:
    """La guarda solo perdona la firma, no cualquier texto.

    Es el control negativo de la prueba de arriba: sin él, recortar por la
    primera línea de guiones podría convertir en válida una mención casual
    seguida de cualquier separador.
    """
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial(f"<!-- sirius-verdict:reviewer:FAILED_SAFELY:{HEAD} -->"),
    )
    resultado = _ejecutar(
        env,
        orden="continua cuando puedas\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_",
    )
    assert resultado.returncode == 0
    assert _etiquetas(env) == ["sirius:failed-safely"]


# --------------------------------------------------------------------------- #
# H-23: la incidencia que se para ANTES de producir ninguna PR
# --------------------------------------------------------------------------- #
#
# Le pasó a #333 el 25-08-2026: vio que completar su encargo exigía tocar
# `.github/**`, que ADR-002 le prohíbe, y se detuvo sin escribir una línea. Es la
# conducta correcta -la alternativa era entregar «una vuelta completa falsa»,
# palabras del propio implementador-. Y sin embargo quedaba muerta: reponer la
# etiqueta disparadora volvía a bloquear en el acto, y `continua` exigía un head
# que no existía.
#
# Un sistema cuya única salida para la parada temprana es la muerte **castiga lo
# que debería premiar**, y con el tiempo enseña a no pararse.


def _historial_sin_pr(marcador_de_parada: str) -> str:
    """Igual que `_historial`, pero sin ninguna URL de PR: nunca se creó."""
    return f"El bloque se detuvo antes de crear rama.\n{marcador_de_parada}\n"


def test_una_parada_sin_pr_reactiva_la_fase_que_se_paro(tmp_path: Path) -> None:
    """El desenlace de #333: sin PR, se autoriza repetir desde cero."""
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial_sin_pr("<!-- sirius-verdict:implementer:FAILED_SAFELY:1 -->"),
    )
    resultado = _ejecutar(env)

    assert resultado.returncode == 0, resultado.stderr
    assert "sirius:implement-requested" in _etiquetas(env), (
        "sin PR, la incidencia tiene que volver a la fase que se paró; si no, la "
        f"parada temprana sigue siendo una muerte. Etiquetas: {_etiquetas(env)}"
    )
    assert "sirius:failed-safely" not in _etiquetas(env)


def test_una_parada_sin_pr_publica_un_permiso_QUE_NO_MIENTE(tmp_path: Path) -> None:
    """El marcador no puede autorizar «sobre un head» que no existe.

    `sirius-convergence-reset` y `sirius-resume-stop` llevan los dos un head,
    porque los dos autorizan continuar sobre una versión concreta. Reutilizar
    cualquiera de ellos aquí escribiría en el historial —que es lo único que
    después dice qué se permitió— una autorización sobre algo inexistente.
    """
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial_sin_pr("<!-- sirius-verdict:implementer:FAILED_SAFELY:1 -->"),
    )
    _ejecutar(env)

    publicado = _comentarios(env)
    assert "sirius-restart-sin-pr" in publicado, (
        "falta el marcador propio del reinicio sin PR; el historial no diría que "
        "lo autorizado fue empezar de cero"
    )
    assert "sirius-convergence-reset" not in publicado, (
        "un reinicio sin PR no perdona rondas: no hubo rondas que contar"
    )
    assert "sirius-resume-stop:" not in publicado


def test_una_parada_sin_pr_NO_manda_el_trabajo_al_corrector(tmp_path: Path) -> None:
    """La mitad sutil de H-23, y la que no se ve leyendo.

    `sirius:blocked-decision` volvía SIEMPRE a `sirius:repair-requested`, porque
    esa parada la emite la política de convergencia y esa siempre para al
    corrector. Sin PR, el corrector se detiene en el acto por «sin-pr»: sería
    cambiar una parada muda por otra, y encima con aspecto de haber funcionado.
    """
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:blocked-decision"],
        historial=_historial_sin_pr("<!-- sirius-verdict:implementer:FAILED_SAFELY:1 -->"),
    )
    resultado = _ejecutar(env)

    assert resultado.returncode == 0, resultado.stderr
    etiquetas = _etiquetas(env)
    assert "sirius:repair-requested" not in etiquetas, (
        "sin PR no se manda al corrector: se detendría en el acto por «sin-pr» y "
        f"la incidencia quedaría igual de muerta. Etiquetas: {etiquetas}"
    )
    assert "sirius:implement-requested" in etiquetas


def test_sin_pr_y_sin_saber_que_fase_se_paro_no_se_inventa_ninguna(tmp_path: Path) -> None:
    """Ante la duda se para, que es la regla de siempre.

    Sin PR y sin marcador de rol publicado no hay forma de saber qué repetir.
    Elegir una fase a ojo reanudaría la equivocada, que es peor que no reanudar.

    **Esta pasa con las dos versiones del guion, y es deliberado.** Las otras
    tres fallan sin el arreglo; ésta no, porque no fija comportamiento nuevo:
    protege contra la SOBRECORRECCIÓN de abrir la puerta tanto que se reanude a
    ciegas. Se deja escrito para que nadie la lea como una prueba vacua.
    """
    env = _setup(tmp_path)
    _sembrar(
        env,
        etiquetas=["sirius:failed-safely"],
        historial=_historial_sin_pr("no hay ningun marcador de veredicto aqui"),
    )
    resultado = _ejecutar(env)

    assert resultado.returncode != 0
    etiquetas = _etiquetas(env)
    assert "sirius:implement-requested" not in etiquetas
    assert "sirius:review-requested" not in etiquetas
    assert "sirius:repair-requested" not in etiquetas
