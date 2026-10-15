"""Lo que la charla va escribiendo, cortado en frases que ya se pueden decir (ADR-243).

La voz del robot dice la respuesta desde la primera frase, mientras el modelo sigue
escribiendo (PA-R03-02). Lo que dice es lo que da ``prepare_speech_text``, la misma
función de Model Studio, con dos cosas que la voz no se puede saltar. Los bloques de
código se reconocen como los ve Markdown, con su raya al principio de línea, y lo de
dentro no llega a la preparación, que empareja tres comillas estén donde estén (ronda 4 de
Codex sobre la PR #688). Y al acabar, lo que se ha quedado a medias no se dice como código
ni como marca, porque ``prepare_speech_text`` solo quita lo que está entero (rondas 2 a 4):
sus cuatro construcciones con cierre se tratan como si se cerraran. El bloque se cierra, y
se dice que queda en pantalla; del enlace se cierra el destino, y se dice su texto; y del
código en línea y del énfasis se quita lo que queda suelto. Es ``final_speech_text``.

Para que, trozo a trozo, salga lo mismo que con la respuesta entera, no se imita dónde
cae cada trozo: se comprueba que cortar no cambia nada (ronda 1 de Codex sobre la PR
#688). Se corta detrás de un final de frase y su blanco, o de un salto de línea, y solo
si se cumplen tres cosas:

- lo de delante está cerrado: preparado, sin marcas a medias (``*``, `` ` ``, ``[``,
  ``]``, dos ``_`` seguidos o uno que no va entre letras), que ``prepare_speech_text``
  solo quita cuando se cierran;
- lo de detrás ya dice algo, y no empieza por una marca que al cerrarse pueda dejar a la
  vista una puntuación, que se pegaría a la frase de antes. La línea entera que abre un
  bloque de código sí vale: cerrado, o al acabar, se dice «Te dejo el código en
  pantalla.», y la frase que lo presenta no espera al bloque;
- lo de delante y lo de detrás, preparados por separado, dan lo mismo que todo lo llegado
  preparado de una vez. Así una puntuación detrás de los blancos se queda con su frase,
  una raya, un guion o una almohadilla detrás de una frase, o la sangría de una línea, no
  cambian de sentido al cortar, y no se corta dentro de un bloque abierto, porque lo de
  detrás se prepararía como texto y en lo llegado no está.

Lo demás espera a que llegue más o a que la charla acabe. Lo que aún no ha llegado no se
ve: una marca que la respuesta entera empareja con otra de una frase posterior aquí ya
estaba cerrada, y si la que sobra no se quita al acabar, se nota, como en «*a*. Hola 5*3».
Una frase de solo puntos no se dice, como no la dice ``prepare_speech_text`` cuando no
queda otra cosa: la que deja delante si la respuesta empieza por algo que no se lee, como
una raya. Y un bloque de código sin rayas, sangrado con cuatro blancos, se lee: para
Markdown es código, pero también es la sangría de una lista, y no se distingue.
"""

from __future__ import annotations

import re

from sirius.application.prepare_speech_text import prepare_speech_text

#: Dónde se puede cortar: detrás de un final de frase y su blanco, o de un salto de línea.
_CUT = re.compile(r"[.!?…][\"'»”)\]]*\s+|\n")
#: Lo que deja una marca sin cerrar al prepararlo: un trozo así todavía no se dice. Dos
#: guiones bajos seguidos son una marca aunque vayan entre letras (ronda 4 de Codex).
_OPEN_MARK = re.compile(r"[*`\[\]]|(?<!\w)_|_(?!\w)|__")
#: Con qué puede empezar, ya preparado, lo que sigue a un corte: no con una marca que al
#: cerrarse pueda dejar a la vista una puntuación, que se pegaría a la frase de antes. Un
#: guion, una estrella o un más con su blanco que siguen ahí ya no son una viñeta.
_SETTLED_START = re.compile(r"[-*+]\s|[^*_`\[+\-]")
#: Una línea que es una raya de bloque de código para Markdown: hasta tres blancos, tres o
#: más comillas o virgulillas, y lo que siga, que tras comillas no lleva comillas.
_FENCE_LINE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")
#: Tres o más comillas a media línea: para Markdown no son una raya, y se quedan en una.
_LONG_BACKTICKS = re.compile(r"`{3,}")
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
        #: Si lo que espera empieza una línea: la respuesta, y lo que sigue a un corte que se
        #: llevó un salto de línea. Solo una línea puede empezar con la raya de un bloque.
        self._line_start = True

    def feed(self, text: str) -> list[str]:
        """Añade ``text`` y devuelve las frases cerradas que aún no había dado."""
        self._pending += text
        arrived = _prepare(self._pending, line_start=self._line_start)
        for cut in reversed(list(_CUT.finditer(self._pending))):
            end = _piece_end(cut)
            head, rest = self._pending[:end], self._pending[end:]
            said = _prepare(head, line_start=self._line_start)
            if _OPEN_MARK.search(said):
                continue
            rest_line_start = head.endswith("\n")
            then = _prepare(rest, line_start=rest_line_start)
            opens_block = rest_line_start and _opens_code_block(rest)
            if not (_SETTLED_START.match(then) or opens_block):
                continue
            if f"{said} {then}" != arrived:
                continue
            self._pending, self._line_start = rest, rest_line_start
            return _sentences(said)
        return []

    def finish(self) -> list[str]:
        """Lo que queda, cuando la charla ha acabado bien."""
        rest, self._pending = self._pending, ""
        line_start, self._line_start = self._line_start, True
        return _sentences(final_speech_text(rest, line_start=line_start))


def final_speech_text(text: str, *, line_start: bool = True) -> str:
    """Lo que se dice de un texto que ya no sigue: lo que da ``prepare_speech_text``, sin
    código ni marcas aunque algo se haya quedado a medias. ``line_start`` dice si empieza
    una línea, como la respuesta entera, o sigue a una frase en su misma línea."""
    text, block_open = _markdown_code_blocks(text, line_start=line_start)
    if block_open:
        text += _FENCE
    text = _UNCLOSED_LINK_TARGET.sub(r"\1)", text)
    return _without_loose_marks(_LOOSE_SYNTAX.sub("", prepare_speech_text(text)))


def _prepare(text: str, *, line_start: bool) -> str:
    """``prepare_speech_text`` con los bloques de código como los ve Markdown."""
    return prepare_speech_text(_markdown_code_blocks(text, line_start=line_start)[0])


def _markdown_code_blocks(text: str, *, line_start: bool) -> tuple[str, bool]:
    """``text`` con cada bloque de código como lo ve Markdown y sin lo de dentro, y si el
    último se ha quedado abierto (ronda 4 de Codex sobre la PR #688).

    Solo abre un bloque una línea que es una raya, de comillas o de virgulillas, y solo lo
    cierra otra igual y al menos tan larga: tres comillas a media línea no son una raya,
    estén dentro o fuera de un bloque, y fuera se quedan en una, la de un código en línea.
    Cada bloque queda como dos rayas de tres comillas, que ``prepare_speech_text`` dice que
    quedan en pantalla, y lo que había dentro no llega a la preparación; uno abierto queda
    solo con la suya, y así no se dice nada de lo de dentro aunque traiga comillas. Si
    ``text`` no empieza una línea, su primera línea no puede ser una raya."""
    lines: list[str] = []
    opened = ""
    for number, line in enumerate(text.splitlines(keepends=True)):
        fence = _fence(line) if number or line_start else None
        if not opened:
            if fence is None:
                lines.append(_LONG_BACKTICKS.sub("`", line))
            else:
                opened = fence[0]
                lines.append(f"{_FENCE}\n")
        elif fence is not None and _closes(fence, opened):
            opened = ""
            lines.append(_FENCE + line[len(line.rstrip("\r\n")) :])
    return "".join(lines), bool(opened)


def _fence(line: str) -> tuple[str, str] | None:
    """La raya de bloque de código de ``line`` y lo que la sigue; nada si no es una."""
    found = _FENCE_LINE.fullmatch(line.rstrip("\r\n"))
    if found is None or (found[1].startswith("`") and "`" in found[2]):
        return None
    return found[1], found[2]


def _closes(fence: tuple[str, str], opened: str) -> bool:
    """Si la raya ``fence`` cierra el bloque que abrió ``opened``: igual, al menos tan
    larga y sola en su línea."""
    marks, after = fence
    return marks[0] == opened[0] and len(marks) >= len(opened) and not after.strip()


def _opens_code_block(rest: str) -> bool:
    """Si lo de detrás, que empieza una línea, empieza con la línea entera que abre un
    bloque de código: cerrado, o al acabar, se dice «Te dejo el código en pantalla.», y la
    frase que lo presenta no espera al bloque."""
    first_line, newline, _ = rest.partition("\n")
    return bool(newline) and _fence(first_line) is not None


def _without_loose_marks(text: str) -> str:
    """Sin lo que sobra de un énfasis. Una estrella o un guion bajo solos se quedan entre dos
    letras o cifras, o entre dos blancos, donde pueden ser una multiplicación o parte de un
    nombre, como los deja ``prepare_speech_text``; dos o más seguidos son siempre lo que
    sobra de un énfasis (ronda 4 de Codex sobre la PR #688). Delante del texto cuenta como
    un blanco, porque lo que se dice al acabar empieza donde un corte se llevó los blancos;
    detrás no, porque ahí acaba la respuesta y lo que cuelga no va con nada."""

    def keep_or_drop(run: re.Match[str]) -> str:
        if len(run.group()) > 1:
            return ""
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
