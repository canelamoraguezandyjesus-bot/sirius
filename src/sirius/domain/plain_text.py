"""El texto en llano: en minúsculas y sin tildes (pieza G de ADR-233, ADR-239).

Para comparar lo que escribe el propietario sin que una tilde o una mayúscula
lo cambien todo: «Olvídalo» y «olvidalo», «Lucía» y «lucia».

``plain`` va carácter a carácter: el texto llano mide lo mismo que el texto en
NFC, así que una posición en uno vale en el otro. Con eso se busca una orden en
el texto llano y se recorta lo que dijo con sus tildes y sus mayúsculas.
"""

from __future__ import annotations

import unicodedata

__all__ = ["nfc", "plain"]


def nfc(text: str) -> str:
    """El texto con cada letra acentuada en un solo carácter, como lo teclea Windows."""
    return unicodedata.normalize("NFC", text)


def plain(text: str) -> str:
    """``text`` en minúsculas y sin tildes, con la misma longitud que ``nfc(text)``."""
    return "".join(_plain_char(char) for char in nfc(text))


def _plain_char(char: str) -> str:
    base = unicodedata.normalize("NFD", char)[0]
    lowered = base.lower()
    # Alguna letra se alarga al pasarla a minúscula («İ»): se deja como está para
    # no descuadrar las posiciones.
    return lowered if len(lowered) == 1 else base
