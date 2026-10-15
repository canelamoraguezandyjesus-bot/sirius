"""Lo que la charla va escribiendo, cortado en frases que ya se pueden decir (ADR-243).

La voz del robot dice la respuesta desde la primera frase, mientras el modelo sigue
escribiendo (PA-R03-02). Lo que dice es lo que da ``prepare_speech_text``, la misma
función de Model Studio, con dos cosas que la voz no se puede saltar.

El código no se dice, y qué es código no lo deciden reglas propias, que en las rondas 2 a
5 de Codex sobre la PR #688 dejaron siempre algún caso fuera. Es código lo que lo es para
CommonMark, leído con un analizador de verdad sobre toda la respuesta llegada, con sus
citas, sus listas y sus sangrías, y lo que la ventana enseña como bloque de código con su
propia regla (B8b, en ``message_view``). Cada bloque se cambia por dos rayas de tres
comillas, que ``prepare_speech_text`` dice que quedan en pantalla, y lo de dentro no llega
a la preparación. Mientras la respuesta sigue, un bloque cuya primera línea aún llega,
unas comillas que aún pueden abrir uno en la ventana o una línea que aún puede ser la raya
de uno paran el corte ahí: lo de detrás no se dice hasta que se sabe qué es.

Y al acabar, lo que se ha quedado a medias no se dice como código ni como marca, porque
``prepare_speech_text`` solo quita lo que está entero (rondas 2 a 4): un bloque abierto es
código hasta el final, como para CommonMark, y se dice que queda en pantalla; del enlace
se cierra el destino, y se dice su texto; y del código en línea y del énfasis se quita lo
que queda suelto. Es ``final_speech_text``.

Para que, trozo a trozo, salga lo mismo que con la respuesta entera, no se imita dónde
cae cada trozo: se comprueba que cortar no cambia nada (ronda 1 de Codex sobre la PR
#688). Se corta detrás de un final de frase y su blanco, o de un salto de línea, y solo
si se cumplen tres cosas:

- lo de delante está cerrado: preparado, sin marcas a medias (``*``, `` ` ``, ``[``,
  ``]``, dos ``_`` seguidos o uno que no va entre letras), que ``prepare_speech_text``
  solo quita cuando se cierran;
- lo de detrás ya dice algo, y no empieza por una marca que al cerrarse pueda dejar a la
  vista una puntuación, que se pegaría a la frase de antes. Un bloque de código sí vale:
  cerrado, o al acabar, se dice «Te dejo el código en pantalla.», y la frase que lo
  presenta no espera al bloque;
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

from markdown_it import MarkdownIt

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
#: La respuesta como la lee CommonMark, solo sus bloques: las citas, las listas y las
#: sangrías de verdad. Sin HTML, como la ventana, que lo enseña como texto.
_MARKDOWN = MarkdownIt("commonmark", {"html": False}).disable(["inline", "text_join"])
#: Los saltos de línea que cuenta ``_MARKDOWN``.
_LINE_END = re.compile(r"\r\n?|\n")
#: Un bloque de código como lo separa la ventana (``_FENCED_CODE_BLOCK`` de
#: ``sirius.presentation.message_view``, B8b): tres comillas en cualquier sitio, lo que
#: las siga en su línea sin comillas, y hasta las tres comillas siguientes.
_WINDOW_CODE_BLOCK = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)
#: Unas comillas que aún pueden abrir uno de esos bloques: sin comillas detrás hasta el
#: final de su línea o de lo llegado.
_WINDOW_OPENING = re.compile(r"```[^\n`]*(?:\n|\Z)")
#: Una línea que aún puede ser la raya de un bloque: detrás de sus blancos, sus citas y sus
#: viñetas, nada todavía, unas cifras que aún pueden ser otra viñeta, o comillas o
#: virgulillas.
_MAY_BE_A_FENCE = re.compile(r"(?:[ \t]*(?:>|[-+*]|\d+[.)]))*[ \t]*(?=[`~]|\d*\Z)")
#: Tres o más comillas fuera de un bloque, que son de un código en línea: se quedan en
#: una, porque ``prepare_speech_text`` las emparejaría como un bloque.
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
        #: Todo lo llegado: qué es código se lee siempre con la respuesta desde el principio.
        self._arrived = ""
        #: Cuánto de lo llegado, ya sin el código, se ha dado.
        self._given = 0

    def feed(self, text: str) -> list[str]:
        """Añade ``text`` y devuelve las frases cerradas que aún no había dado."""
        self._arrived += text
        pending = _without_code(self._arrived, finished=False)[self._given :]
        arrived = prepare_speech_text(pending)
        for cut in reversed(list(_CUT.finditer(pending))):
            end = _piece_end(cut)
            head, rest = pending[:end], pending[end:]
            said = prepare_speech_text(head)
            if _OPEN_MARK.search(said):
                continue
            then = prepare_speech_text(rest)
            if not (_SETTLED_START.match(then) or rest.startswith(_FENCE)):
                continue
            if f"{said} {then}" != arrived:
                continue
            self._given += end
            return _sentences(said)
        return []

    def finish(self) -> list[str]:
        """Lo que queda, cuando la charla ha acabado bien."""
        rest = _without_code(self._arrived, finished=True)[self._given :]
        self._arrived, self._given = "", 0
        return _sentences(_said_at_the_end(rest))


def final_speech_text(text: str) -> str:
    """Lo que se dice de una respuesta entera: lo que da ``prepare_speech_text``, sin código
    ni marcas aunque algo se haya quedado a medias."""
    return _said_at_the_end(_without_code(text, finished=True))


def _said_at_the_end(text: str) -> str:
    """Lo que se dice de lo que queda, ya sin el código, cuando la respuesta ha acabado."""
    text = _UNCLOSED_LINK_TARGET.sub(r"\1)", text)
    return _without_loose_marks(_LOOSE_SYNTAX.sub("", prepare_speech_text(text)))


def _without_code(text: str, *, finished: bool) -> str:
    """``text`` con cada bloque de código cambiado por dos rayas de tres comillas, que
    ``prepare_speech_text`` dice que quedan en pantalla, y sin nada de lo de dentro. Van
    juntas, sin un salto de línea entre ellas: no se puede cortar entre las dos y dejar
    una sola, que se emparejaría con una comilla suelta de antes. Detrás va siempre uno,
    también si la ventana cierra el bloque a media línea, porque lo que sigue lo enseña
    aparte.

    Si la respuesta sigue (``finished`` falso) y desde algún sitio aún no se sabe qué es
    código, de ahí en adelante no queda nada de lo llegado, y un trozo que llegue hasta ahí
    no se dice. Si ahí empieza un bloque seguro, queda su raya, que no se cierra, y lo de
    delante se dice sin esperarlo. Si no, queda una comilla suelta: lo de delante espera,
    porque lo que venga puede no ser código y empezar por una puntuación que va con la
    frase de antes.
    """
    blocks, known, block_starts = _code(text, finished=finished)
    kept: list[str] = []
    cursor = 0
    for start, end in blocks:
        kept.append(_LONG_BACKTICKS.sub("`", text[cursor:start]))
        kept.append(f"{_FENCE}{_FENCE}\n")
        cursor = end
    kept.append(_LONG_BACKTICKS.sub("`", text[cursor:known]))
    if known < len(text):
        kept.append(f"{_FENCE}\n" if block_starts else "`")
    return "".join(kept)


def _code(text: str, *, finished: bool) -> tuple[list[tuple[int, int]], int, bool]:
    """Dónde está el código de ``text``, en orden y sin solaparse, hasta dónde se sabe, y si
    donde ya no se sabe empieza seguro un bloque.

    Es código lo que lo es para CommonMark o para la ventana, que no siempre coinciden:
    tres comillas a media línea no abren un bloque para CommonMark y en la ventana sí, y
    unas comillas dentro de una línea de código no cierran el bloque para CommonMark y en
    la ventana sí. Un bloque que aún crece ya es código hasta donde ha llegado, y su marca
    no cambia aunque crezca. Pero mientras la respuesta sigue, no se sabe nada a partir de
    un bloque cuya primera línea aún no ha llegado entera, ni de unas comillas que aún
    pueden abrir uno en la ventana, y tampoco de un bloque que pasa por ahí. Ni de la
    última línea si aún no ha llegado entera y, detrás de sus blancos, sus citas y sus
    viñetas, no hay nada, unas cifras que aún pueden ser otra viñeta, o comillas o
    virgulillas: puede ser la raya de un bloque, y entonces la línea entera es código,
    también un «1.» que ya parecía el final de una frase. Al acabar se sabe todo: un bloque
    abierto es código hasta el final, como para CommonMark, y unas comillas que no se
    cierran, texto, como en la ventana.

    Donde ya no se sabe empieza seguro un bloque si ahí empieza uno que ya es código y no
    puede dejar de serlo, con su primera línea ya llegada entera. Si su primera línea sigue
    llegando, aún puede no serlo: tres comillas con una más detrás en esa línea ya no abren
    nada.
    """
    starts = [0, *(found.end() for found in _LINE_END.finditer(text))]
    unknown: list[int] = []
    blocks: list[tuple[int, int]] = []
    for token in _MARKDOWN.parse(text):
        if token.type in {"fence", "code_block"} and token.map:
            first, after = token.map
            if finished or first + 1 < len(starts):
                blocks.append((starts[first], starts[after] if after < len(starts) else len(text)))
            else:
                unknown.append(starts[first])
    window_end = 0
    for found in _WINDOW_CODE_BLOCK.finditer(text):
        blocks.append(found.span())
        window_end = found.end()
    opening = _WINDOW_OPENING.search(text, window_end)
    if opening is not None and not finished:
        unknown.append(opening.start())
    if not finished and _MAY_BE_A_FENCE.match(text, starts[-1]):
        unknown.append(starts[-1])
    known, block_starts = min(unknown, default=len(text)), False
    merged: list[tuple[int, int]] = []
    for start, end in sorted(blocks):
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    # Un bloque que pasa por donde ya no se sabe empieza ahí lo que no se sabe, y seguro; uno
    # que va entero por detrás no cuenta todavía.
    while merged and merged[-1][1] > known:
        start, _ = merged.pop()
        if start <= known:
            known, block_starts = start, True
    return merged, known, block_starts


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
