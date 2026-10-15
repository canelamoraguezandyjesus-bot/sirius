"""Lo que la charla va escribiendo, cortado en frases que ya se pueden decir (ADR-243).

La voz del robot dice la respuesta desde la primera frase, mientras el modelo sigue
escribiendo (PA-R03-02). Lo que dice es lo que da ``prepare_speech_text``, la misma
función de Model Studio, sin quitar ni añadir nada: solo cambia el corte en frases. Y que
al acabar, lo que se ha quedado a medias no se dice como código ni como marca, cosa que
``prepare_speech_text`` no mira porque solo quita lo que está entero (rondas 2 y 3 de
Codex sobre la PR #688). Sus cuatro construcciones con cierre se tratan como si se
cerraran: el bloque de código se cierra, y se dice que queda en pantalla; del enlace se
cierra el destino, y se dice su texto; y del código en línea y del énfasis se quita lo que
queda suelto. Es ``final_speech_text``.

Para que, trozo a trozo, salga lo mismo que con la respuesta entera, no se imita dónde
cae cada trozo: se comprueba que cortar no cambia nada (ronda 1 de Codex sobre la PR
#688). Se corta detrás de un final de frase y su blanco, o de un salto de línea, y solo
si se cumplen tres cosas:

- lo de delante está cerrado: sin un bloque de código abierto y, preparado, sin marcas a
  medias (``*``, `` ` ``, ``[``, ``]`` o un ``_`` que no va entre letras), que
  ``prepare_speech_text`` solo quita cuando se cierran;
- lo de detrás ya dice algo, y no empieza por una marca que al cerrarse pueda dejar a la
  vista una puntuación, que se pegaría a la frase de antes. Un bloque de código sí vale:
  cerrado, o al acabar, se dice «Te dejo el código en pantalla.», y la frase que lo
  presenta no espera al bloque entero;
- lo de delante y lo de detrás, preparados por separado, dan lo mismo que todo lo llegado
  preparado de una vez. Así una puntuación detrás de los blancos se queda con su frase, y
  una raya, un guion o una almohadilla detrás de una frase, o la sangría de una línea, no
  cambian de sentido al cortar.

Lo demás espera a que llegue más o a que la charla acabe. Lo que aún no ha llegado no se
ve: una marca que la respuesta entera empareja con otra de una frase posterior aquí ya
estaba cerrada, y si la que sobra no se quita al acabar, se nota, como en «*a*. Hola 5*3».
Y una frase de solo puntos no se dice, como no la dice ``prepare_speech_text`` cuando no
queda otra cosa: la que deja delante si la respuesta empieza por algo que no se lee, como
una raya.
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
#: Un bloque de código: cerrado, o al acabar, se dice «Te dejo el código en pantalla.».
_CODE_BLOCK_START = re.compile(r"\s*```")
#: El destino de un enlace que no se cierra en lo que queda de respuesta: se cierra donde
#: acaba la dirección, en el primer blanco, y del enlace se dice el texto, como de uno
#: entero.
_UNCLOSED_LINK_TARGET = re.compile(r"(\[[^\]]+\]\([^\s)]*)(?=[^)]*\Z)")
#: Corchetes y comillas de código que quedan al acabar, ya preparado: ninguno es ya de un
#: enlace ni de un código enteros, y no se dicen.
_LOOSE_SYNTAX = re.compile(r"[`\[\]]")
#: Estrellas y guiones bajos seguidos.
_MARK_RUN = re.compile(r"[*_]+")
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
        return _sentences(final_speech_text(rest))


def final_speech_text(text: str) -> str:
    """Lo que se dice de un texto que ya no sigue: lo que da ``prepare_speech_text``, sin
    código ni marcas aunque algo se haya quedado a medias."""
    if text.count(_FENCE) % 2:
        text = f"{text}\n{_FENCE}"
    text = _UNCLOSED_LINK_TARGET.sub(r"\1)", text)
    return _without_loose_marks(_LOOSE_SYNTAX.sub("", prepare_speech_text(text)))


def _without_loose_marks(text: str) -> str:
    """Sin lo que sobra de un énfasis. Una estrella o un guion bajo solo se quedan entre dos
    letras o cifras, o entre dos blancos, donde pueden ser una multiplicación o parte de un
    nombre, como los deja ``prepare_speech_text``. Delante del texto cuenta como un blanco,
    porque lo que se dice al acabar empieza donde un corte se llevó los blancos; detrás no,
    porque ahí acaba la respuesta y lo que cuelga no va con nada."""

    def keep_or_drop(run: re.Match[str]) -> str:
        before = text[run.start() - 1 : run.start()] or " "
        after = text[run.end() : run.end() + 1]
        between_words = before.isalnum() and after.isalnum()
        between_blanks = before.isspace() and after.isspace()
        return run.group() if between_words or between_blanks else ""

    return _MARK_RUN.sub(keep_or_drop, text)


def _piece_end(cut: re.Match[str]) -> int:
    """Dónde acaba lo de delante: detrás del corte o, si se lleva un salto de línea, detrás
    del último, y la sangría de la línea siguiente se queda con ella."""
    line_break = cut.group().rfind("\n")
    return cut.end() if line_break < 0 else cut.start() + line_break + 1


def _sentences(prepared: str) -> list[str]:
    """Las frases del trozo que dicen algo: no las de solo puntos."""
    return [s for s in _BETWEEN_SENTENCES.split(prepared) if s.strip(" .\t\n")]
