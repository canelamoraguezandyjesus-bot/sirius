"""Ayudantes para afirmar sobre el TEXTO de un script de PowerShell.

Las pruebas estructurales de B13 leen los ``.ps1`` como texto, porque aquí no
hay PowerShell que ejecutarlos. Eso funciona mientras la afirmación distinga
entre lo que el script **hace** y lo que el script **dice**: dos pruebas
fallaron por no distinguirlo.

- Una exigía que no hubiera ``uv sync`` entre la guarda y la implementación. El
  wrapper no lo invoca, pero lo menciona en un comentario y en un mensaje de
  error, y la búsqueda de subcadena no lo sabía.
- Otra exigía que un ``catch`` terminara en un ``throw`` desnudo, delimitando la
  región con un ancla lejana en vez de con la llave de cierre del propio
  bloque. Bastó añadir una línea después del ``catch`` para romperla.

Las dos afirmaciones eran correctas de intención; su mecanismo era frágil. Estos
ayudantes las hacen precisas sin debilitarlas: ``executable_text`` mira solo lo
ejecutable, y ``block_after`` acota exactamente el bloque del que se habla.
"""

from __future__ import annotations

__all__ = ["block_after", "executable_text"]


def executable_text(script: str) -> str:
    """Devuelve el script sin literales de cadena ni comentarios.

    Lo que queda es lo que PowerShell ejecutaría, no lo que documenta. Se
    conserva la longitud en líneas para que un fallo siga siendo legible.

    No es un analizador de PowerShell: cubre comillas dobles, comillas simples,
    comentarios de línea ``#`` y bloques ``<# ... #>``, que es todo lo que
    aparece en estos scripts.
    """
    out: list[str] = []
    index = 0
    length = len(script)
    while index < length:
        char = script[index]

        if char == "<" and script.startswith("<#", index):
            end = script.find("#>", index + 2)
            end = length if end == -1 else end + 2
            out.append("\n" * script.count("\n", index, end))
            index = end
            continue

        if char == "#":
            end = script.find("\n", index)
            index = length if end == -1 else end
            continue

        if char in ('"', "'"):
            quote = char
            cursor = index + 1
            while cursor < length:
                if script[cursor] == "`" and quote == '"':
                    cursor += 2
                    continue
                if script[cursor] == quote:
                    cursor += 1
                    break
                cursor += 1
            out.append("\n" * script.count("\n", index, cursor))
            index = cursor
            continue

        out.append(char)
        index += 1

    return "".join(out)


def block_after(script: str, opening: str, *, start: int = 0) -> str:
    """El bloque ``{ ... }`` que abre ``opening``, hasta su llave de cierre.

    Delimitar por conteo de llaves, y no por el siguiente ancla que se le
    ocurra a quien escribe la prueba, es lo que impide que añadir una línea
    después del bloque rompa una afirmación sobre lo que hay dentro.
    """
    begin = script.index(opening, start)
    brace = script.index("{", begin)
    depth = 0
    for position in range(brace, len(script)):
        if script[position] == "{":
            depth += 1
        elif script[position] == "}":
            depth -= 1
            if depth == 0:
                return script[begin : position + 1]
    raise AssertionError(f"El bloque abierto en {opening!r} no se cierra.")
