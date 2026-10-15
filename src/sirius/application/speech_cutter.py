"""Lo que la charla va escribiendo, cortado en frases que ya se pueden decir (ADR-243).

La voz del robot dice la respuesta desde la primera frase, mientras el modelo sigue
escribiendo (PA-R03-02). Lo que dice es lo que da ``prepare_speech_text``, la misma
función de Model Studio, sin quitar ni añadir nada: solo cambia el corte en frases.

Para que, trozo a trozo, salga lo mismo que con la respuesta entera, solo se suelta un
trozo cerrado: acaba en un final de frase seguido de un blanco o en un salto de línea,
deja cerrados los bloques de código, y preparado ya no enseña marcas a medias (``*``,
`` ` ``, ``[``, ``]`` o un ``_`` que no va entre letras), que ``prepare_speech_text``
solo quita cuando se cierran. Lo demás espera a cerrarse o a que la charla acabe.
"""

from __future__ import annotations

import re

from sirius.application.prepare_speech_text import prepare_speech_text

#: Dónde se puede cortar: detrás de un final de frase y su blanco, o de un salto de línea.
_CUT = re.compile(r"[.!?…][\"'»”)\]]*\s+|\n")
#: Lo que deja una marca sin cerrar al prepararlo: un trozo así todavía no se dice.
_OPEN_MARK = re.compile(r"[*`\[\]]|(?<!\w)_|_(?!\w)")
#: Entre frase y frase, ya preparado.
_BETWEEN_SENTENCES = re.compile(r"(?<=[.!?…])\s+")
_FENCE = "```"


class SpeechCutter:
    """Recibe lo que la charla escribe y da, en orden, las frases que ya se pueden decir."""

    def __init__(self) -> None:
        self._pending = ""

    def feed(self, text: str) -> list[str]:
        """Añade ``text`` y devuelve las frases cerradas que aún no había dado."""
        self._pending += text
        for match in reversed(list(_CUT.finditer(self._pending))):
            head = self._pending[: match.end()]
            if head.count(_FENCE) % 2:
                continue
            prepared = _prepare(head)
            if _OPEN_MARK.search(prepared):
                continue
            self._pending = self._pending[match.end() :]
            return _sentences(prepared)
        return []

    def finish(self) -> list[str]:
        """Lo que queda, cuando la charla ha acabado bien."""
        rest, self._pending = self._pending, ""
        return _sentences(_prepare(rest))


def _prepare(piece: str) -> str:
    """El trozo preparado para leerse. Sin los blancos de delante: una tanda de saltos de
    línea partida entre dos trozos daría un punto suelto, y entera se queda en un salto."""
    return prepare_speech_text(piece.lstrip())


def _sentences(prepared: str) -> list[str]:
    return [sentence for sentence in _BETWEEN_SENTENCES.split(prepared) if sentence.strip()]
