#!/usr/bin/env python3
"""Puerta de evidencia para publicar (hook PreToolUse de Claude Code).

Bloquea ``git push`` cuando la rama actual no lleva evidencia de arranque: ni
un ADR tocado en el diff frente a ``origin/main``, ni una nota de rama en
``.claude/evidencia/<rama>.md``. Nació del ADR-001: en la PR #136 el método
falló ocho rondas seguidas y lo único que ató de verdad fue la evidencia
publicada donde el humano podía verla. Esta puerta convierte esa costumbre en
un requisito mecánico en el único punto que una sesión viva no puede saltarse
por descuido: el acto de publicar.

Decisiones de diseño, con su porqué:

- El filtrado del comando vive AQUÍ y no en la configuración del hook. Si la
  sintaxis de filtrado de ``settings.json`` cambiara o no existiera en la
  versión instalada, este guion degrada a ejecutarse en cada herramienta y
  decidir solo; nunca a desaparecer en silencio.
- La evidencia es POR RAMA, nunca global. «Existe algún ADR en el repo» es una
  puerta que el primer ADR deja abierta para siempre (familia A: afirmar más
  de lo que el dato sostiene; el defecto venía en el diseño de origen y se
  cazó antes de implementarlo).
- Exenta bajo GitHub Actions: los settings del repositorio se cargan también
  en el corrector de la automatización, que publica correcciones sin ADR; sin
  la exención esta puerta tumbaría la tubería que ya funciona.
- Si la entrada no se puede leer, NO se bloquea: sin comando legible no se
  sabe si hay push, y bloquear todas las herramientas por un fallo de parseo
  es el modo de abandono número uno de este tipo de montaje. La promesa
  honesta de esta puerta es «un push normal de una sesión viva no pasa sin
  evidencia», no «ningún push puede pasar»: sigue siendo evadible a propósito
  y no aplica fuera de Claude Code.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# PreToolUse: salir con 2 bloquea la herramienta y envía stderr al agente.
BLOQUEO = 2


def _git(*args: str) -> tuple[int, str]:
    try:
        proceso = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=30, check=False
        )
    except OSError, subprocess.SubprocessError:
        return 1, ""
    return proceso.returncode, proceso.stdout.strip()


def _rama_actual() -> str:
    codigo, salida = _git("branch", "--show-current")
    return salida if codigo == 0 and salida else "HEAD"


def _nota_de(rama: str) -> str:
    # El saneado puede colisionar entre ramas deliberadamente parecidas
    # ("a/b" y "a-b"); se acepta: la puerta protege del descuido, no del dolo.
    return re.sub(r"[^A-Za-z0-9._-]", "-", rama) + ".md"


def _hay_evidencia(rama: str) -> tuple[bool, str]:
    nota = os.path.join(".claude", "evidencia", _nota_de(rama))
    if os.path.isfile(nota):
        return True, ""
    codigo, salida = _git("diff", "--name-only", "origin/main...HEAD")
    if codigo != 0:
        return False, "no he podido leer el diff frente a origin/main"
    for ruta in salida.splitlines():
        if ruta.startswith("docs/decisions/ADR-"):
            return True, ""
        if ruta.startswith(".claude/evidencia/") and ruta.endswith(".md"):
            return True, ""
    return False, "el diff frente a origin/main no toca ningún ADR"


def main() -> int:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return 0
    try:
        carga = json.load(sys.stdin)
    except json.JSONDecodeError, UnicodeDecodeError, OSError:
        return 0
    if not isinstance(carga, dict):
        return 0
    entrada = carga.get("tool_input")
    comando = str(entrada.get("command") or "") if isinstance(entrada, dict) else ""
    # Amplio a propósito: un falso positivo se desbloquea con la nota; un falso
    # negativo deja pasar un push sin evidencia, que es lo que no puede pasar.
    if not re.search(r"\bgit\b[^\n]*\bpush\b", comando):
        return 0
    rama = _rama_actual()
    evidencia, detalle = _hay_evidencia(rama)
    if evidencia:
        return 0
    print(
        "PUERTA DE EVIDENCIA - git push bloqueado.\n"
        f"Rama: {rama}. Motivo: {detalle} y no existe .claude/evidencia/{_nota_de(rama)}.\n"
        "Antes de publicar, deja la evidencia de arranque (skill disciplina-evidencia, ADR-001):\n"
        "  1) añade o modifica un ADR en docs/decisions/ y confírmalo en esta rama, o\n"
        f"  2) escribe la nota de arranque en .claude/evidencia/{_nota_de(rama)} (criterio de\n"
        "     parada, afirmación y comprobación) y confírmala para que sea visible en la PR.\n"
        "Exención automática únicamente bajo GITHUB_ACTIONS.",
        file=sys.stderr,
    )
    return BLOQUEO


if __name__ == "__main__":
    sys.exit(main())
