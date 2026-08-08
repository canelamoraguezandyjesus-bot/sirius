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
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_STOP = REPO_ROOT / ".claude" / "hooks" / "recordar_parada.py"


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


NOTA = (
    "# Nota de arranque\n\n"
    "Criterio de parada: si la segunda ronda trae la misma familia, se para.\n"
    "Afirmación: el empujón solo calla con evidencia que un revisor vería.\n"
    "Comprobación: pruebas de este módulo, verificadas por mutación.\n"
)


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


def test_settings_declare_only_the_stop_hook_and_it_exists() -> None:
    """La puerta del push se retiró; queda solo el empujón de cierre.

    Quince defectos en cuatro rondas de revisión, todos en la misma pieza y
    todos con la misma raíz: decidir, a partir del TEXTO de un comando de
    shell, si ese comando ejecutará un push. Eso exige un intérprete de shell
    completo —comillas, sustitución de comandos, subshells, continuaciones de
    línea, alias—, y cada ronda encontró otra forma. Es la lección de la
    incidencia #138 en otro disfraz: un texto de shell no dice qué va a
    ejecutar sin un shell que lo interprete.

    El empujón sobrevive porque NO parsea comandos: solo consulta git y el
    estado de la rama. Esta prueba fija que la puerta no vuelve por inercia;
    si alguien la reintroduce, que sea con la decisión tomada de nuevo.
    """
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]
    assert list(hooks) == ["Stop"], "la puerta del push se retiró (ADR-001)"
    comandos = [h["command"] for grupo in hooks.values() for e in grupo for h in e["hooks"]]
    assert comandos == ["uv run python .claude/hooks/recordar_parada.py"]
    assert HOOK_STOP.is_file()
    # Y el guion retirado no puede quedar huérfano en el árbol.
    assert not (REPO_ROOT / ".claude" / "hooks" / "exigir_evidencia_push.py").exists()
