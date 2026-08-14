"""Convierte una respuesta escrita en algo que se pueda leer en voz alta.

Es una transformación **determinista**: no se pide a otro modelo que resuma ni
reescriba. Dos razones. La primera, coste y latencia: una llamada más por turno
en una sesión de grabación se nota. La segunda, y la que de verdad importa: un
modelo que reescribe puede cambiar lo que Sirius dijo, y entonces lo que se oye
deja de ser lo que está en pantalla y en la memoria.

Lo que sí se hace es quitar lo que no se pronuncia: marcas de Markdown, bloques
de código, enlaces y adornos. Lo que se dice sigue siendo literalmente lo que
Sirius escribió.
"""

from __future__ import annotations

import re

_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((?:[^)]*)\)")
_BARE_URL = re.compile(r"https?://\S+")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_LIST_BULLET = re.compile(r"^\s{0,3}[-*+]\s+", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*{1,3}|_{1,3})(\S.*?\S|\S)\1", re.DOTALL)
_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_HORIZONTAL_RULE = re.compile(r"^\s{0,3}([-*_])\s*(?:\1\s*){2,}$", re.MULTILINE)
_BLANK_RUN = re.compile(r"\n{2,}")
_SPACE_RUN = re.compile(r"[ \t]{2,}")

CODE_BLOCK_SPOKEN_AS = "Te dejo el código en pantalla."
LINK_SPOKEN_AS = "un enlace"


_FENCE_LANGUAGE = re.compile(r"^```[^\n]*\n?|```$", re.MULTILINE)


def prepare_speech_text(text: str, *, read_code: bool = False) -> str:
    """Devuelve el texto listo para sintetizar.

    Cadena vacía si no queda nada que decir, por ejemplo cuando la respuesta
    era solo un bloque de código y ya está en pantalla.

    ``read_code`` es lo que hace el botón «Leer todo»: en vez de decir que el
    código queda en pantalla, lo lee. Existe porque grabando hay un momento en
    que sí quieres oírlo —para comentarlo mientras se ve— y hasta ahora la
    única forma era leerlo tú.

    Los enlaces se siguen diciendo como «un enlace» incluso leyéndolo todo:
    deletrear una dirección en voz alta no le sirve a nadie.
    """
    if not text.strip():
        return ""

    prepared = (
        _FENCE_LANGUAGE.sub("", text)
        if read_code
        else _CODE_FENCE.sub(f" {CODE_BLOCK_SPOKEN_AS} ", text)
    )
    prepared = _MARKDOWN_LINK.sub(r"\1", prepared)
    prepared = _BARE_URL.sub(LINK_SPOKEN_AS, prepared)
    prepared = _INLINE_CODE.sub(r"\1", prepared)
    prepared = _HORIZONTAL_RULE.sub("", prepared)
    prepared = _HEADING.sub("", prepared)
    prepared = _BLOCKQUOTE.sub("", prepared)
    prepared = _LIST_BULLET.sub("", prepared)
    prepared = _EMPHASIS.sub(r"\2", prepared)

    # Un salto simple dentro de un párrafo se lee como espacio; dos o más son
    # una pausa real y se conservan como punto y aparte.
    prepared = _BLANK_RUN.sub("\n", prepared)
    prepared = prepared.replace("\n", ". ")
    prepared = _SPACE_RUN.sub(" ", prepared)
    prepared = re.sub(r"\.\s*\.", ".", prepared)
    prepared = re.sub(r"\s+([,.;:!?])", r"\1", prepared)

    prepared = prepared.strip()
    # Si solo quedan puntos y espacios, no hay nada que decir.
    return prepared if prepared.strip(" .\t\n") else ""
