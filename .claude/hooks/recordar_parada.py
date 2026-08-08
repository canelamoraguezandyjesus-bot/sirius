#!/usr/bin/env python3
"""Empujón de cierre (hook Stop de Claude Code).

Cuando la sesión va a terminar su turno con trabajo en la rama y sin evidencia
de arranque, pide UNA vez que se escriba, o que se diga por qué no hace falta.

Es un empujón, y **no hay ninguna garantía dura detrás**. Hubo una: una puerta
que bloqueaba ``git push`` sin evidencia. Se retiró tras quince defectos en
cuatro rondas, todos con la misma raíz —decidir desde el TEXTO de un comando
si ejecutará un push exige un intérprete de shell completo (ADR-001)—.

Así que este hook es lo único mecánico que queda, y conviene saber qué NO es:
vive dentro del proceso que puede morir, de modo que una sesión cortada no lo
dispara. Prometer más sería la familia B de la PR #136. Sobrevivió a la
retirada porque no parsea comandos: solo consulta git y el estado de la rama.

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
    # git ausente, sin permisos o colgado: todo se resuelve igual, "no sé".
    except Exception:
        return 1, ""
    return proceso.returncode, proceso.stdout.strip()


def _rama_actual() -> str:
    codigo, salida = _git("branch", "--show-current")
    return salida if codigo == 0 and salida else ""


def _sanear(rama: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", rama)


def _base() -> str:
    """Sin respaldo al commit raíz: comparar contra él mete en el diff todo ADR
    fusionado en la historia y daría por documentada cualquier rama nueva. Sin
    base fiable, este empujón calla en vez de mentir en cualquiera de los dos
    sentidos."""
    for ref in ("origin/main", "main", "origin/HEAD"):
        if _git("rev-parse", "--verify", "--quiet", ref)[0] == 0:
            return ref
    return ""


def _hay_evidencia(rama: str) -> bool:
    """Mismo criterio que la puerta del push: confirmada, de esta rama y con
    sustancia. Un criterio más laxo aquí callaría el empujón justo cuando la
    puerta va a bloquear, que es cuando el aviso más falta hace."""
    base = _base()
    if not base:
        return False
    codigo, salida = _git("diff", "--name-only", f"{base}...HEAD")
    if codigo != 0:
        return False
    nota = f".claude/evidencia/{_sanear(rama)}.md"
    for ruta in salida.splitlines():
        if ruta != nota and not (ruta.startswith("docs/decisions/ADR-") and ruta.endswith(".md")):
            continue
        codigo, contenido = _git("show", f"HEAD:{ruta}")
        if codigo != 0:
            continue
        utiles = [linea for linea in contenido.splitlines() if linea.strip()]
        if len(utiles) >= 3 and len(contenido.strip()) >= 120:
            return True
    return False


def _hay_trabajo() -> bool:
    codigo, sucio = _git("status", "--porcelain")
    if codigo == 0 and sucio:
        return True
    base = _base()
    if not base:
        return False
    codigo, diff = _git("diff", "--name-only", f"{base}...HEAD")
    return codigo == 0 and bool(diff)


def main() -> int:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return 0
    try:
        carga = json.load(sys.stdin)
    # Sin entrada legible no hay nada que decidir.
    except Exception:
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
                    "al usuario por qué este trabajo no la necesita. No repetiré este "
                    "aviso para esta rama en este entorno."
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
