#!/usr/bin/env python3
"""Empujón de cierre (hook Stop de Claude Code).

Cuando la sesión va a terminar su turno con trabajo en la rama y sin evidencia
de arranque, pide UNA vez que se escriba, o que se diga por qué no hace falta.

Es un empujón, no una garantía, y la diferencia está decidida a propósito
(ADR-001): un hook ``Stop`` vive dentro del proceso que puede morir, así que
no puede prometer nada sobre sesiones cortadas —la garantía viviría donde no
puede cumplirse, que es la familia B de la PR #136—. La garantía dura está en
la puerta del push (``exigir_evidencia_push.py``), que intercepta una acción y
por tanto solo actúa sobre sesiones vivas.

Contra el modo de abandono número uno (la fricción):

- Respeta ``stop_hook_active``: si ya se bloqueó una vez en este turno, deja
  parar. Sin esto, una condición incumplible ataría a la sesión en bucle.
- Solo empuja una vez POR RAMA en cada entorno (marcador local no versionado):
  un empujón en cada turno de una sesión larga acaba con el montaje entero.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys


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
    return salida if codigo == 0 and salida else ""


def _sanear(rama: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", rama)


def _hay_evidencia(rama: str) -> bool:
    if os.path.isfile(os.path.join(".claude", "evidencia", _sanear(rama) + ".md")):
        return True
    codigo, salida = _git("diff", "--name-only", "origin/main...HEAD")
    if codigo != 0:
        return False
    return any(
        ruta.startswith("docs/decisions/ADR-")
        or (ruta.startswith(".claude/evidencia/") and ruta.endswith(".md"))
        for ruta in salida.splitlines()
    )


def _hay_trabajo() -> bool:
    codigo, sucio = _git("status", "--porcelain")
    if codigo == 0 and sucio:
        return True
    codigo, diff = _git("diff", "--name-only", "origin/main...HEAD")
    return codigo == 0 and bool(diff)


def main() -> int:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return 0
    try:
        carga = json.load(sys.stdin)
    except json.JSONDecodeError, UnicodeDecodeError, OSError:
        return 0
    if not isinstance(carga, dict) or carga.get("stop_hook_active"):
        return 0
    rama = _rama_actual()
    if rama in ("", "main"):
        return 0
    marcador = os.path.join(".claude", "evidencia", f".empujon-{_sanear(rama)}")
    if os.path.exists(marcador):
        return 0
    if not _hay_trabajo() or _hay_evidencia(rama):
        return 0
    # El marcador se escribe ANTES de empujar: si el empujón se pierde, que sea
    # hacia el lado silencioso, nunca hacia el bucle.
    try:
        os.makedirs(os.path.dirname(marcador), exist_ok=True)
        with open(marcador, "w", encoding="utf-8") as archivo:
            archivo.write("")
    except OSError:
        pass
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    f"La rama {rama} tiene trabajo sin nota de arranque ni ADR "
                    "(skill disciplina-evidencia, ADR-001). Antes de terminar: "
                    "escribe la evidencia (criterio de parada, afirmación y "
                    "comprobación) en docs/decisions/ o en "
                    f".claude/evidencia/{_sanear(rama)}.md, o di explícitamente "
                    "al usuario por qué este trabajo no la necesita. Este aviso "
                    "no se repetirá en esta rama."
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
