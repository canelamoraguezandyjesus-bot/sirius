"""Lo que la charla va escribiendo, cortado en frases que ya se pueden decir (ADR-243).

La voz del robot dice la respuesta desde la primera frase, mientras el modelo sigue
escribiendo (PA-R03-02). Lo que dice es lo que da ``prepare_speech_text``, la misma
función de Model Studio, sin quitar ni añadir nada: solo cambia el corte en frases.

Para que, trozo a trozo, salga lo mismo que con la respuesta entera, no se imita dónde
cae cada trozo: se comprueba que cortar no cambia nada (ronda 1 de Codex sobre la PR
#688). Se corta detrás de un final de frase y su blanco, o de un salto de línea, y solo
si se cumplen tres cosas:

- lo de delante está cerrado: sin un bloque de código abierto y, preparado, sin marcas a
  medias (``*``, `` ` ``, ``[``, ``]`` o un ``_`` que no va entre letras), que
  ``prepare_speech_text`` solo quita cuando se cierran;
- lo de detrás ya dice algo, y no empieza por una marca que al cerrarse pueda dejar a la
  vista una puntuación, que se pegaría a la frase de antes. Una línea que abre un bloque
  de código sí vale: cerrado, se dice «Te dejo el código en pantalla.», y la frase que lo
  presenta no espera al bloque entero;
- lo de delante y lo de detrás, preparados por separado, dan lo mismo que todo lo llegado
  preparado de una vez. Así una puntuación detrás de los blancos se queda con su frase, y
  una raya, un guion o una almohadilla detrás de una frase, o la sangría de una línea, no
  cambian de sentido al cortar.

Lo demás espera a que llegue más o a que la charla acabe. Lo que aún no ha llegado no se
ve: una marca que la respuesta entera empareja con otra de una frase posterior, como en
«*a*. Hola b*», aquí ya estaba cerrada. Y una frase de solo puntos no se dice, como no
la dice ``prepare_speech_text`` cuando no queda otra cosa: la que deja delante si la
respuesta empieza por algo que no se lee, como una raya.
"""

from __future__ import annotations

import re

from sirius.application.prepare_speech_text import prepare_speech_text

#: Dónde se puede cortar: detrás de un final de frase y su blanco, o de un salto de línea.
_CUT = re.compile(r"[.!?…][\"'»”)\]]*\s+|\n")
#: Lo que deja una marca sin cerrar al prepararlo: un trozo así todavía no se dice.
_OPEN_MARK = re.compile(r"[*`\[\]]|(?<!\w)_|_(?!\w)")
#: Con qué puede empezar, ya preparado, lo que sigue a un corte: no con una marca que al
#: cerrarse pueda dejar a la vista una puntuación, que se pegaría a la frase de antes. Un
#: guion, una estrella o un más con su blanco que siguen ahí ya no son una viñeta.
_SETTLED_START = re.compile(r"[-*+]\s|[^*_`\[+\-]")
#: La línea que abre un bloque de código: cerrado, se dice «Te dejo el código en pantalla.».
_CODE_BLOCK_START = re.compile(r"\s*```(?:\w[\w+-]*)?\n")
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
        arrived = prepare_speech_text(self._pending)
        for cut in reversed(list(_CUT.finditer(self._pending))):
            end = _piece_end(cut)
            head, rest = self._pending[:end], self._pending[end:]
            if head.count(_FENCE) % 2:
                continue
            said = prepare_speech_text(head)
            if _OPEN_MARK.search(said):
                continue
            then = prepare_speech_text(rest)
            if not (_SETTLED_START.match(then) or _CODE_BLOCK_START.match(rest)):
                continue
            if f"{said} {then}" != arrived:
                continue
            self._pending = rest
            return _sentences(said)
        return []

    def finish(self) -> list[str]:
        """Lo que queda, cuando la charla ha acabado bien."""
        rest, self._pending = self._pending, ""
        return _sentences(prepare_speech_text(rest))


def _piece_end(cut: re.Match[str]) -> int:
    """Dónde acaba lo de delante: detrás del corte o, si se lleva un salto de línea, detrás
    del último, y la sangría de la línea siguiente se queda con ella."""
    line_break = cut.group().rfind("\n")
    return cut.end() if line_break < 0 else cut.start() + line_break + 1


def _sentences(prepared: str) -> list[str]:
    """Las frases del trozo que dicen algo: no las de solo puntos."""
    return [s for s in _BETWEEN_SENTENCES.split(prepared) if s.strip(" .\t\n")]
