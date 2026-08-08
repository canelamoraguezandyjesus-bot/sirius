#!/usr/bin/env python3
"""Puerta de evidencia para publicar (hook PreToolUse de Claude Code).

Bloquea ``git push`` cuando la rama que se va a publicar no lleva evidencia de
arranque CONFIRMADA y con sustancia: su nota ``.claude/evidencia/<rama>.md`` o
un ADR de ``docs/decisions/``. Nació del ADR-001: en la PR #136 el método falló
ocho rondas seguidas y lo único que ató de verdad fue la evidencia publicada
donde el humano podía verla.

La propiedad, dicha con precisión, porque la primera versión de este archivo
afirmaba de más y una auditoría adversarial lo demostró con cinco escenarios
reproducidos:

    cuenta como evidencia SOLO lo que un revisor vería en la PR.

Es decir: confirmado en la rama (no un archivo suelto del árbol de trabajo),
perteneciente a esa rama (no la nota de otra ni un README de la carpeta), y con
contenido sustantivo (no un archivo vacío). Preguntar «¿existe el archivo?» era
la misma puerta global que el diseño decía haber cazado —el primer archivo la
deja abierta para siempre— reintroducida por otra vía.

Lo que esta puerta NO garantiza, escrito aquí para que nadie lo lea de más:

- No aplica fuera de Claude Code: un push desde otra terminal no la ve.
- Es evadible a propósito (``git -C``, alias, refspecs exóticos). Protege del
  descuido, no del dolo.
- Si el intérprete no arranca (``uv`` ausente, entorno sin sincronizar), el
  hook no se ejecuta y el push pasa. Esa degradación NO se puede cerrar desde
  dentro: es el observador dentro de lo observado (incidencia #138). Por eso
  el arranque se hace lo más corto posible y sin dependencias del proyecto.
- Bajo ``GITHUB_ACTIONS`` se exime a propósito: los agentes de la
  automatización publican correcciones sin ADR y esta puerta los tumbaría.
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


def _rama_publicada(comando: str, actual: str) -> str:
    """Qué rama publica este comando, que no siempre es la rama actual.

    `git push origin otra-rama` desde una rama con nota publicaba la otra sin
    evidencia, y el caso inverso bloqueaba una rama que sí la tenía: la puerta
    juzgaba a quien no iba a viajar. Se lee el destino del comando; ante
    cualquier forma que no se sepa leer se cae a la rama actual, que es el
    caso mayoritario.
    """
    piezas = comando.split()
    try:
        inicio = piezas.index("push") + 1
    except ValueError:
        return actual
    # `git push [opciones] [remoto] [refspec]`: los posicionales, en orden.
    posicionales = [p for p in piezas[inicio:] if not p.startswith("-")]
    if len(posicionales) < 2:
        return actual
    origen = posicionales[1].split(":", 1)[0].strip("+")
    if not origen or origen == "HEAD":
        return actual
    return origen


def _base_de_comparacion() -> str:
    """Contra qué se compara la rama.

    Un clon `--single-branch` no tiene `origin/main`, y entonces la vía del ADR
    quedaba muerta mientras el mensaje seguía ofreciéndola: la puerta bloqueaba
    aunque hubiera evidencia real. Se prueban las referencias en orden y, si
    ninguna existe, se cae al commit raíz, que siempre existe.
    """
    for ref in ("origin/main", "main", "origin/HEAD"):
        codigo, _ = _git("rev-parse", "--verify", "--quiet", ref)
        if codigo == 0:
            return ref
    codigo, salida = _git("rev-list", "--max-parents=0", "HEAD")
    return salida.splitlines()[0] if codigo == 0 and salida else ""


def _tiene_sustancia(ruta: str) -> bool:
    codigo, contenido = _git("show", f"HEAD:{ruta}")
    if codigo != 0:
        return False
    utiles = [linea for linea in contenido.splitlines() if linea.strip()]
    return len(utiles) >= MINIMO_LINEAS and len(contenido.strip()) >= MINIMO_CARACTERES


def _hay_evidencia(rama: str) -> tuple[bool, str]:
    base = _base_de_comparacion()
    if not base:
        return False, "no he podido situar la base de comparación de esta rama"
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
    # Amplio a propósito: un falso positivo se desbloquea escribiendo la nota;
    # un falso negativo deja pasar un push sin evidencia, que es lo que no puede
    # pasar. `git -C` queda fuera por diseño (ver "lo que NO garantiza").
    if not re.search(r"\bgit\b[^\n]*\bpush\b", comando):
        return 0
    rama = _rama_publicada(comando, _rama_actual())
    if rama in ("", "main", "HEAD"):
        return 0
    evidencia, detalle = _hay_evidencia(rama)
    if evidencia:
        return 0
    print(
        "PUERTA DE EVIDENCIA - git push bloqueado.\n"
        f"Rama a publicar: {rama}. Motivo: {detalle}.\n"
        "Solo cuenta como evidencia lo que un revisor vería en la PR: confirmada en\n"
        "esta rama, de esta rama, y con contenido de verdad. Dos salidas:\n"
        "  1) añade o modifica un ADR en docs/decisions/ y confírmalo en esta rama, o\n"
        f"  2) escribe la nota de arranque en .claude/evidencia/{_nota_de(rama)} —criterio\n"
        "     de parada, afirmación y comprobación— y confírmala.\n"
        "Método completo: skill disciplina-evidencia (ADR-001).\n"
        "Exención automática únicamente bajo GITHUB_ACTIONS.",
        file=sys.stderr,
    )
    return BLOQUEO


if __name__ == "__main__":
    sys.exit(main())
