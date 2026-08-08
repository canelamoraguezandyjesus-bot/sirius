#!/usr/bin/env python3
"""Puerta de evidencia para publicar (hook PreToolUse de Claude Code).

Bloquea ``git push`` cuando **el commit que tienes delante** —``HEAD``— no lleva
evidencia de arranque confirmada y con sustancia: su nota
``.claude/evidencia/<rama>.md`` o un ADR de ``docs/decisions/``.

Por qué esta puerta es tan simple, que es su única virtud
=========================================================

La versión anterior intentaba deducir de la línea de comandos QUÉ publica
``git push`` para juzgar esa rama. Dos rondas de revisión encontraron doce
defectos, todos de la misma familia y todos en ese punto: el fallback de base
abría la puerta en clones ``--single-branch``; la rama se identificaba pero la
evidencia se seguía leyendo de ``HEAD``; ``--all`` publicaba todas y solo se
miraba una; un operando de opción (``-o ci.skip``) se tomaba por el nombre de
la rama y bloqueaba trabajo legítimo.

No eran doce problemas: era uno. ``git push`` admite ``--all``, ``--mirror``,
refspecs múltiples, ``HEAD:rama``, opciones con operandos, alias y ``-C``.
Reconstruir su semántica parseando texto es una carrera que se pierde ronda a
ronda, y la revisión tiene razón en todas. Así que la puerta dejó de adivinar.

La propiedad que comprueba, entera:

    el HEAD actual lleva evidencia que un revisor vería en la PR

Confirmada en el árbol (no un archivo suelto), perteneciente a esta rama (no la
nota de otra ni un README de la carpeta) y con contenido sustantivo (no un
esbozo para pasar el trámite).

Lo que NO cubre, dicho aquí en vez de fingido en el código
=========================================================

- **Publicar una rama distinta de la actual** (``git push origin otra``,
  ``--all``, ``--mirror``, refspecs múltiples). El parseo era la fuente de los
  doce defectos y se retiró entero; cubrir estos casos exige preguntarle a git,
  no adivinar, y eso queda para cuando haya un caso real que lo justifique.
- **Pushes fuera de Claude Code**, ``git -C`` y alias: la puerta no los ve.
- **Si el lanzador no arranca** (``uv`` ausente, entorno sin sincronizar), el
  hook no se ejecuta y el push pasa. Esa degradación no se puede cerrar desde
  dentro: es el observador dentro de lo observado (incidencia #138).
- **La calidad** de la evidencia. Se comprueba que exista y no sea un esbozo.

Protege del descuido, no del dolo. Bajo ``GITHUB_ACTIONS`` se exime a
propósito: los agentes de la automatización publican correcciones sin ADR.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# PreToolUse: salir con 2 bloquea la herramienta y envía stderr al agente.
BLOQUEO = 2

# Una nota que no dice nada no es evidencia. El umbral es deliberadamente bajo:
# distingue "archivo creado para pasar la puerta" de "alguien escribió algo",
# no juzga la calidad, que no es cosa de un guion.
MINIMO_CARACTERES = 120
MINIMO_LINEAS = 3


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


def _nota_de(rama: str) -> str:
    # El saneado puede colisionar entre ramas deliberadamente parecidas
    # ("a/b" y "a-b"); se acepta: la puerta protege del descuido, no del dolo.
    return re.sub(r"[^A-Za-z0-9._-]", "-", rama) + ".md"


def _base_de_comparacion() -> str:
    """Contra qué se compara el HEAD, o cadena vacía si no hay base fiable.

    NO existe respaldo al commit raíz. Lo hubo, y abría la puerta de par en par
    en un clon `--single-branch`: comparar contra el raíz mete en el diff todo
    ADR fusionado en la historia, así que cualquier rama nacía con evidencia
    ajena. Sin base fiable esta puerta falla CERRADA y dice qué hacer.
    """
    for ref in ("origin/main", "main", "origin/HEAD"):
        codigo, _ = _git("rev-parse", "--verify", "--quiet", ref)
        if codigo == 0:
            return ref
    return ""


def _tiene_sustancia(ruta: str) -> bool:
    codigo, contenido = _git("show", f"HEAD:{ruta}")
    if codigo != 0:
        return False
    utiles = [linea for linea in contenido.splitlines() if linea.strip()]
    return len(utiles) >= MINIMO_LINEAS and len(contenido.strip()) >= MINIMO_CARACTERES


def _hay_evidencia(rama: str) -> tuple[bool, str]:
    base = _base_de_comparacion()
    if not base:
        return False, (
            "no encuentro una base con la que comparar (ni origin/main, ni main, "
            "ni origin/HEAD). Ejecuta `git fetch origin main` y repite"
        )
    codigo, salida = _git("diff", "--name-only", f"{base}...HEAD")
    if codigo != 0:
        return False, f"no he podido leer el diff frente a {base}"
    nota = f".claude/evidencia/{_nota_de(rama)}"
    candidatos = [
        ruta
        for ruta in salida.splitlines()
        if ruta == nota or (ruta.startswith("docs/decisions/ADR-") and ruta.endswith(".md"))
    ]
    if not candidatos:
        return False, f"el diff frente a {base} no toca ningún ADR ni {nota}"
    if any(_tiene_sustancia(ruta) for ruta in candidatos):
        return True, ""
    return False, f"la evidencia de esta rama ({', '.join(candidatos)}) está vacía o es un esbozo"


def main() -> int:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return 0
    try:
        carga = json.load(sys.stdin)
    # Sin entrada legible no se sabe si hay push: no se bloquea a ciegas.
    except Exception:
        return 0
    if not isinstance(carga, dict):
        return 0
    entrada = carga.get("tool_input")
    comando = str(entrada.get("command") or "") if isinstance(entrada, dict) else ""
    # Lo único que se le pregunta al comando es "¿es un push?". Nada más: cada
    # pregunta adicional al texto fue un defecto (ver la cabecera del archivo).
    if not re.search(r"\bgit\b[^\n]*\bpush\b", comando):
        return 0
    rama = _rama_actual()
    if rama in ("", "main"):
        return 0
    evidencia, detalle = _hay_evidencia(rama)
    if evidencia:
        return 0
    print(
        "PUERTA DE EVIDENCIA - git push bloqueado.\n"
        f"Rama actual: {rama}. Motivo: {detalle}.\n"
        "Solo cuenta como evidencia lo que un revisor vería en la PR: confirmada en\n"
        "esta rama, de esta rama, y con contenido de verdad. Dos salidas:\n"
        "  1) añade o modifica un ADR en docs/decisions/ y confírmalo en esta rama, o\n"
        f"  2) escribe la nota de arranque en .claude/evidencia/{_nota_de(rama)} —criterio\n"
        "     de parada, afirmación y comprobación— y confírmala.\n"
        "Método completo: skill disciplina-evidencia (ADR-001).\n"
        "Esta puerta juzga el HEAD actual; no cubre publicar otra rama ni --all.\n"
        "Exención automática únicamente bajo GITHUB_ACTIONS.",
        file=sys.stderr,
    )
    return BLOQUEO


if __name__ == "__main__":
    sys.exit(main())
