"""Pruebas de los hooks de la disciplina de evidencia (ADR-001).

Los hooks son guiones autónomos y se prueban como los ejecuta Claude Code: un
proceso con JSON por stdin, contra repositorios git de laboratorio con un
``origin/main`` real. La propiedad central es anti-vacua por construcción: un
ADR ya fusionado en ``main`` NO abre la puerta de otra rama. Ese defecto
exacto —puerta global donde hacía falta puerta por rama— venía en el diseño
de origen y se cazó antes de implementarlo, así que la prueba que lo fija es
la razón de ser de este módulo.

Nota sobre el entorno: Quality corre bajo GitHub Actions, donde los hooks se
eximen a propósito. Cada ejecución de prueba limpia ``GITHUB_ACTIONS`` del
entorno heredado; sin esa limpieza, todas las pruebas de bloqueo serían vacuas
exactamente en CI, que es donde más importan.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PUSH = REPO_ROOT / ".claude" / "hooks" / "exigir_evidencia_push.py"
HOOK_STOP = REPO_ROOT / ".claude" / "hooks" / "recordar_parada.py"

PUSH = {"tool_input": {"command": "git push -u origin trabajo"}}
# Sin refspec: la puerta juzga la rama actual, sea cual sea.
PUSH_ACTUAL = {"tool_input": {"command": "git push"}}


def _run_hook(
    hook: Path,
    payload: object,
    cwd: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("GITHUB_ACTIONS", None)
    if extra_env:
        env.update(extra_env)
    entrada = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(hook)],
        input=entrada,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        check=False,
        timeout=60,
    )


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repo de laboratorio: origin/main real y una rama de trabajo activa."""
    origen = tmp_path / "origen.git"
    _git(tmp_path, "init", "--bare", str(origen))
    trabajo = tmp_path / "trabajo"
    trabajo.mkdir()
    _git(trabajo, "init", "-b", "main")
    _git(trabajo, "config", "user.email", "lab@example.invalid")
    _git(trabajo, "config", "user.name", "Laboratorio")
    (trabajo / "docs" / "decisions").mkdir(parents=True)
    (trabajo / "docs" / "decisions" / "README.md").write_text("registro\n", encoding="utf-8")
    _git(trabajo, "add", "-A")
    _git(trabajo, "commit", "-m", "inicial")
    _git(trabajo, "remote", "add", "origin", str(origen))
    _git(trabajo, "push", "-u", "origin", "main")
    _git(trabajo, "checkout", "-b", "trabajo")
    return trabajo


def _confirma(repo_dir: Path, ruta: str, contenido: str = "x\n") -> None:
    destino = repo_dir / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8")
    _git(repo_dir, "add", "-A")
    _git(repo_dir, "commit", "-m", f"toca {ruta}")


# --------------------------------------------------------------------------- #
# Puerta del push
# --------------------------------------------------------------------------- #


def test_a_command_that_is_not_a_push_is_left_alone(repo: Path) -> None:
    r = _run_hook(HOOK_PUSH, {"tool_input": {"command": "uv run pytest -q"}}, repo)
    assert r.returncode == 0
    assert r.stderr == ""


def test_a_push_without_evidence_is_blocked(repo: Path) -> None:
    r = _run_hook(HOOK_PUSH, PUSH, repo)
    assert r.returncode == 2
    # El mensaje enseña las dos salidas; sin ellas el bloqueo solo frustra.
    assert "docs/decisions" in r.stderr
    assert ".claude/evidencia/trabajo.md" in r.stderr


def test_under_actions_the_gate_steps_aside(repo: Path) -> None:
    # El corrector de la automatización publica sin ADR; los settings del repo
    # se cargan también allí y sin la exención la puerta tumbaba la tubería.
    r = _run_hook(HOOK_PUSH, PUSH, repo, extra_env={"GITHUB_ACTIONS": "true"})
    assert r.returncode == 0


NOTA = (
    "# Nota de arranque\n\n"
    "Criterio de parada: si la segunda ronda trae la misma familia, se para.\n"
    "Afirmación: la puerta solo acepta evidencia que un revisor vería en la PR.\n"
    "Comprobación: pruebas de este módulo, verificadas por mutación.\n"
)


def test_the_branch_note_opens_the_gate(repo: Path) -> None:
    _confirma(repo, ".claude/evidencia/trabajo.md", NOTA)
    assert _run_hook(HOOK_PUSH, PUSH, repo).returncode == 0


def test_an_adr_committed_on_the_branch_opens_the_gate(repo: Path) -> None:
    _confirma(repo, "docs/decisions/ADR-099-prueba.md", NOTA)
    assert _run_hook(HOOK_PUSH, PUSH, repo).returncode == 0


# --------------------------------------------------------------------------- #
# Lo que NO es evidencia (auditoría adversarial del ADR-001)
#
# La primera versión de la puerta preguntaba «¿existe el archivo?». La auditoría
# reprodujo cinco formas de pasar sin evidencia real, todas de la misma familia,
# así que la puerta se rehízo en vez de parchearse cinco veces: cuenta SOLO lo
# que un revisor vería en la PR —confirmado, de esta rama y con sustancia—.
# --------------------------------------------------------------------------- #


def test_an_uncommitted_note_is_not_evidence(repo: Path) -> None:
    # `touch` de un archivo suelto era el camino de mínimo esfuerzo del propio
    # remedio que la puerta recomienda: abría sin que nada llegara a la PR.
    destino = repo / ".claude" / "evidencia" / "trabajo.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(NOTA, encoding="utf-8")
    r = _run_hook(HOOK_PUSH, PUSH, repo)
    assert r.returncode == 2, "una nota sin confirmar no viaja en la PR"


def test_an_empty_note_is_not_evidence(repo: Path) -> None:
    _confirma(repo, ".claude/evidencia/trabajo.md", "")
    r = _run_hook(HOOK_PUSH, PUSH, repo)
    assert r.returncode == 2
    assert "vacía o es un esbozo" in r.stderr


def test_touching_the_evidence_readme_is_not_evidence(repo: Path) -> None:
    # Simétrico exacto del caso ya cubierto en docs/decisions: un retoque de
    # documentación de la carpeta no es una nota de arranque.
    _confirma(repo, ".claude/evidencia/README.md", NOTA)
    assert _run_hook(HOOK_PUSH, PUSH, repo).returncode == 2


def test_another_branchs_committed_note_is_not_evidence(repo: Path) -> None:
    # En ramas encadenadas, la nota confirmada de otra rama viaja en el diff.
    _confirma(repo, ".claude/evidencia/otra-rama.md", NOTA)
    r = _run_hook(HOOK_PUSH, PUSH, repo)
    assert r.returncode == 2
    assert ".claude/evidencia/trabajo.md" in r.stderr


def test_a_note_inherited_from_main_does_not_open_a_reused_branch(repo: Path) -> None:
    # Las notas se fusionan a main, así que reutilizar un nombre de rama hacía
    # nacer la puerta abierta: la misma «puerta global» por la vía del archivo.
    _git(repo, "checkout", "main")
    _confirma(repo, ".claude/evidencia/ciclo.md", NOTA)
    _git(repo, "push", "origin", "main")
    _git(repo, "checkout", "-b", "ciclo")
    _confirma(repo, "cambio2.txt")
    assert _run_hook(HOOK_PUSH, PUSH_ACTUAL, repo).returncode == 2


def test_a_single_branch_clone_fails_closed(tmp_path: Path, repo: Path) -> None:
    """Sin base fiable la puerta se cierra; NUNCA cae al commit raíz.

    Este es el defecto que costó la tercera versión de la puerta, y la prueba
    que lo cubría era vacua: quitaba `origin` pero dejaba `main` local, así que
    pasaba por `main` y jamás ejercitaba el respaldo. Aquí se clona de verdad
    con `--single-branch`, donde no existe ni `origin/main`, ni `main`, ni
    `origin/HEAD`. Comparar contra el commit raíz metía en el diff todo ADR
    fusionado en la historia: cualquier rama nacía con evidencia ajena.
    """
    _git(repo, "checkout", "main")
    _confirma(repo, "docs/decisions/ADR-050-vieja.md", NOTA)
    _git(repo, "push", "origin", "main")
    _git(repo, "checkout", "-b", "nueva")
    _confirma(repo, "codigo.txt")
    _git(repo, "push", "origin", "nueva")

    clon = tmp_path / "clon"
    subprocess.run(
        [
            "git",
            "clone",
            "--single-branch",
            "--branch",
            "nueva",
            str(tmp_path / "origen.git"),
            str(clon),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    for ref in ("origin/main", "main", "origin/HEAD"):
        ausente = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", ref],
            cwd=clon,
            capture_output=True,
            check=False,
            timeout=60,
        )
        assert ausente.returncode != 0, f"el laboratorio no reproduce el clon: {ref} existe"

    r = _run_hook(HOOK_PUSH, PUSH_ACTUAL, clon)
    assert r.returncode == 2, "sin base fiable la puerta debe cerrarse, no abrirse"

    # Y la salida prescrita tiene que FUNCIONAR. La primera versión decía
    # `git fetch origin main`, que en un clon --single-branch actualiza
    # FETCH_HEAD pero no crea ninguna de las tres referencias: seguir la
    # instrucción dejaba el mismo bloqueo para siempre. Un mensaje de ayuda que
    # no ayuda es de la misma familia que el resto —afirmar lo que no se
    # sostiene—, así que la prueba ejecuta lo que el mensaje manda.
    prescrito = re.search(r"Ejecuta `([^`]+)`", r.stderr)
    assert prescrito, "el bloqueo debe decir cómo salir"
    subprocess.run(
        shlex.split(prescrito.group(1)), cwd=clon, check=True, capture_output=True, timeout=60
    )
    _confirma(clon, ".claude/evidencia/nueva.md", NOTA)
    assert _run_hook(HOOK_PUSH, PUSH_ACTUAL, clon).returncode == 0, (
        "tras seguir la instrucción prescrita la puerta debe poder abrirse"
    )


def test_mentioning_a_push_is_not_executing_one(repo: Path) -> None:
    """Buscar la palabra en el texto crudo bloqueaba trabajo cotidiano.

    Sin evidencia en la rama, un buscador, un `git log --grep`, un `echo` a
    documentación y hasta un `git commit` cuyo mensaje contiene «push» caían
    bloqueados. La fricción sin motivo es el modo número uno por el que estos
    montajes acaban desactivados, así que se distingue ejecutar de mencionar.
    """
    for comando in (
        "rg 'git push' .",
        "git log --grep='git push'",
        "echo 'usa git push para publicar' > doc.md",
        "git commit -m 'no hagas push'",
        "grep -rn 'git push' docs/",
    ):
        r = _run_hook(HOOK_PUSH, {"tool_input": {"command": comando}}, repo)
        assert r.returncode == 0, f"mencionar un push no es ejecutarlo: {comando}"

    # Y las formas que SÍ ejecutan un push siguen bloqueando sin evidencia.
    for comando in (
        "git push",
        "git -c core.pager=cat push",
        "GIT_TRACE=1 git push",
        "uv run pytest && git push",
    ):
        r = _run_hook(HOOK_PUSH, {"tool_input": {"command": comando}}, repo)
        assert r.returncode == 2, f"esto sí ejecuta un push: {comando}"


def test_the_gate_asks_the_command_only_whether_it_is_a_push(repo: Path) -> None:
    # El parseo de refspecs se retiró: era la fuente de los doce defectos. La
    # contrapartida es que formas como `-o ci.skip` ya no confunden a la puerta,
    # porque no se le pregunta nada más al texto que "¿es un push?".
    _confirma(repo, ".claude/evidencia/trabajo.md", NOTA)
    for comando in (
        "git push",
        "git push -u origin trabajo",
        "git push -o ci.skip origin trabajo",
        "git push --all origin",
    ):
        r = _run_hook(HOOK_PUSH, {"tool_input": {"command": comando}}, repo)
        assert r.returncode == 0, f"con evidencia en HEAD no debe bloquear: {comando}"

    _git(repo, "checkout", "-b", "sin-nota")
    _confirma(repo, "otro.txt")
    for comando in ("git push", "git push -o ci.skip origin sin-nota"):
        r = _run_hook(HOOK_PUSH, {"tool_input": {"command": comando}}, repo)
        assert r.returncode == 2, f"sin evidencia en HEAD debe bloquear: {comando}"


def test_an_adr_already_merged_in_main_does_not_open_another_branch(repo: Path) -> None:
    # LA prueba anti-vacua: la puerta global («existe algún ADR») se abre para
    # siempre con el primero. La evidencia tiene que ser de ESTA rama.
    #
    # El escenario discriminante es una rama nacida DESPUÉS de que el ADR se
    # fusionara: hereda el ADR en su árbol, así que una puerta que mire el
    # árbol («ls-files», «existe el archivo») la ve abierta, y solo una puerta
    # que mire el diff frente a main la mantiene cerrada. La primera versión
    # de esta prueba creaba la rama ANTES del ADR y no distinguía entre ambas
    # puertas: la mutación global la pasaba. La cazó la mutación, no el ojo.
    _git(repo, "checkout", "main")
    _confirma(repo, "docs/decisions/ADR-050-previa.md", NOTA)
    _git(repo, "push", "origin", "main")
    _git(repo, "checkout", "-b", "heredera")
    _confirma(repo, "src_cambio.txt")
    r = _run_hook(HOOK_PUSH, PUSH_ACTUAL, repo)
    assert r.returncode == 2, "un ADR heredado de main no puede abrir la puerta de otra rama"
    assert ".claude/evidencia/heredera.md" in r.stderr


def test_another_branchs_note_does_not_open_this_one(repo: Path) -> None:
    _confirma(repo, ".claude/evidencia/otra-rama.md")
    # La nota confirmada de OTRA rama aparece en el diff y abriría la puerta
    # por la vía del diff; se retira de la rama para aislar la vía del archivo.
    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "sin-nota")
    r = _run_hook(HOOK_PUSH, PUSH_ACTUAL, repo)
    assert r.returncode == 2
    assert ".claude/evidencia/sin-nota.md" in r.stderr


def test_touching_the_decisions_readme_is_not_evidence(repo: Path) -> None:
    # Solo cuentan los ADR (docs/decisions/ADR-*): retocar el README o la
    # plantilla no es una decisión registrada.
    _confirma(repo, "docs/decisions/README.md", "retoque\n")
    assert _run_hook(HOOK_PUSH, PUSH, repo).returncode == 2


def test_unreadable_input_does_not_blind_block(repo: Path) -> None:
    # Sin comando legible no se sabe si hay push; bloquear TODAS las
    # herramientas por un fallo de parseo es el modo de abandono número uno.
    assert _run_hook(HOOK_PUSH, "esto no es json", repo).returncode == 0


# --------------------------------------------------------------------------- #
# Empujón de cierre
# --------------------------------------------------------------------------- #


def _hay_bloqueo(r: subprocess.CompletedProcess[str]) -> bool:
    return '"decision"' in r.stdout and '"block"' in r.stdout


def test_stop_hook_active_lets_the_turn_end(repo: Path) -> None:
    _confirma(repo, "cambio.txt")
    r = _run_hook(HOOK_STOP, {"stop_hook_active": True}, repo)
    assert r.returncode == 0
    assert not _hay_bloqueo(r)


def test_under_actions_the_nudge_steps_aside(repo: Path) -> None:
    _confirma(repo, "cambio.txt")
    r = _run_hook(HOOK_STOP, {}, repo, extra_env={"GITHUB_ACTIONS": "true"})
    assert r.returncode == 0
    assert not _hay_bloqueo(r)


def test_work_without_evidence_nudges_exactly_once(repo: Path) -> None:
    _confirma(repo, "cambio.txt")
    primero = _run_hook(HOOK_STOP, {}, repo)
    assert primero.returncode == 0
    assert _hay_bloqueo(primero), "la primera parada con trabajo sin evidencia debe empujar"
    assert "trabajo" in primero.stdout
    segundo = _run_hook(HOOK_STOP, {}, repo)
    assert segundo.returncode == 0
    assert not _hay_bloqueo(segundo), "el empujón por rama es UNO: repetirlo mata el montaje"


def test_with_evidence_the_nudge_stays_silent(repo: Path) -> None:
    _confirma(repo, ".claude/evidencia/trabajo.md", NOTA)
    r = _run_hook(HOOK_STOP, {}, repo)
    assert not _hay_bloqueo(r)


def test_without_work_the_nudge_stays_silent(repo: Path) -> None:
    # Rama recién creada, árbol limpio, sin diff frente a main: no hay nada
    # que documentar y empujar aquí sería fricción pura.
    r = _run_hook(HOOK_STOP, {}, repo)
    assert r.returncode == 0
    assert not _hay_bloqueo(r)


def test_on_main_the_nudge_stays_silent(repo: Path) -> None:
    _git(repo, "checkout", "main")
    (repo / "suelto.txt").write_text("x\n", encoding="utf-8")
    r = _run_hook(HOOK_STOP, {}, repo)
    assert not _hay_bloqueo(r)


# --------------------------------------------------------------------------- #
# La configuración declara lo que los guiones implementan
# --------------------------------------------------------------------------- #


def test_settings_wire_both_hooks_to_existing_scripts() -> None:
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]
    pre = hooks["PreToolUse"][0]
    # El propietario trabaja con PowerShell y las sesiones remotas con Bash:
    # cubrir solo una de las dos dejaría la puerta sin efecto en la otra.
    assert pre["matcher"] == "Bash|PowerShell"
    comandos = [h["command"] for grupo in hooks.values() for e in grupo for h in e["hooks"]]
    for comando in comandos:
        guion = comando.split()[-1]
        assert (REPO_ROOT / guion).is_file(), f"el hook declara un guion inexistente: {guion}"
    assert any("exigir_evidencia_push.py" in c for c in comandos)
    assert any("recordar_parada.py" in c for c in comandos)
