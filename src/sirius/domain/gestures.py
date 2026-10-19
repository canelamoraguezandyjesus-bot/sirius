"""Los gestos de Sirius, de una lista cerrada (pieza C de ADR-259; ADR-261).

El plan (§6, «Lo que se hace», 7): el modelo escribe la respuesta con etiquetas como
``[ceja_arriba]``, la cara las hace y lo que no está en la lista se ignora. Es la misma
lista que usará la cabeza.

- **La lista**, ``GESTURES``: cada gesto con su nombre, en minúsculas y sin tildes.
- **Qué es una etiqueta.** Un corchete, de una a tres palabras de letras y otro corchete.
  Las palabras van unidas por guiones bajos, guiones o un blanco, y en mayúsculas o
  minúsculas, con tildes o sin ellas: ``[Guiño]`` y ``[ceja arriba]`` son gestos de la
  lista. Una que no es de la lista solo es etiqueta si va de una pieza, sin blancos, y no
  pegada detrás de una letra o una cifra: ``[bailar]`` lo es, y ``datos[clave]`` o
  ``[nota del autor]`` no. Nunca lo es si la sigue un paréntesis, como un enlace, ni
  dentro de un código entre comillas invertidas.
- **Las etiquetas no se ven, no se dicen y no se guardan.** ``GestureFilter`` las quita
  del texto mientras llega a trozos, aunque una venga partida entre dos, y da cada gesto
  de la lista en su sitio: delante de lo primero que se ve detrás de él. Una que no es de
  la lista se quita igual y no se hace. Con la etiqueta se va un blanco: el de detrás, o
  el de delante si detrás viene una puntuación de cierre o nada; de dos blancos, se queda
  el que lleva más saltos de línea. Al principio, se van los de detrás.
- **Lo que no lleva etiquetas no cambia ni un byte**, y a trozos sale lo mismo que entero,
  se corte por donde se corte: lo que aún puede cambiar con lo que llegue espera.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

#: Los gestos que sabe hacer la cara, y que hará la cabeza.
GESTURES: tuple[str, ...] = (
    "ceja_arriba",
    "cejas_arriba",
    "cejas_fruncidas",
    "sonrisa",
    "guino",
    "ojos_en_blanco",
    "asiente",
    "niega",
)

#: Lo más largo que puede ser lo que va entre los corchetes de una etiqueta.
_LONGEST_NAME = 40
#: Cuántas palabras puede tener.
_MOST_WORDS = 3
#: Lo que une sus palabras.
_JOINERS = "_- "
#: Lo que, detrás de una etiqueta, se lleva el blanco de delante: las puntuaciones que
#: cierran, con las comillas de cierre tipográficas, la doble y la simple.
_CLOSING = ".,;:!?…)]}»\u201d\u2019\"'"


@dataclass(frozen=True, slots=True)
class Gesture:
    """Un gesto de la lista que el modelo escribió, en su sitio entre el texto."""

    name: str


type Piece = str | Gesture


def gestures_line() -> str:
    """Lo que se le dice al modelo de sus gestos, para sus instrucciones."""
    tags = ", ".join(f"[{name}]" for name in GESTURES)
    return (
        "# Tus gestos\n"
        "Tienes cara. Si viene a cuento, haz un gesto escribiendo su etiqueta entre "
        f"corchetes justo donde lo harías. Tienes estos y ninguno más: {tags}. Pocos y "
        "sin explicarlos: no se ven ni se dicen."
    )


def normalize(name: str) -> str:
    """El nombre de un gesto como va en la lista: minúsculas, sin tildes y con guiones
    bajos."""
    plain = "".join(
        char for char in unicodedata.normalize("NFD", name) if unicodedata.category(char) != "Mn"
    )
    return "".join("_" if char in _JOINERS else char for char in plain.lower())


class GestureFilter:
    """Quita las etiquetas de un texto que llega a trozos y da los gestos en su sitio.

    ``feed`` recibe cada trozo y devuelve, en orden, lo que ya se puede enseñar, decir y
    guardar, y los gestos de la lista. Lo que aún puede cambiar con lo que llegue, como
    un corchete abierto, unos blancos o unas comillas invertidas al final, espera: los
    trozos que da no son los que recibe, aunque juntos digan lo mismo. ``finish`` da lo
    que esperaba cuando el texto acaba; con ``cut``, si se cortó antes de acabar, y
    entonces un corchete que aún podía ser una etiqueta se deja, con lo que le sigue.
    """

    def __init__(self) -> None:
        self._text = ""
        #: Hasta dónde se ha leído ``_text``.
        self._read = 0
        #: Cuántas comillas invertidas abrieron el código en que se está; 0, fuera de él.
        self._code = 0
        #: Los blancos leídos que aún no se han dado.
        self._space = ""
        #: Los gestos leídos que esperan a lo primero que se vea detrás.
        self._waiting: list[Gesture] = []
        #: Si lo último leído fue una etiqueta.
        self._after_tag = False
        #: Si ya se ha dado algo que se ve.
        self._shown = False

    def feed(self, chunk: str) -> list[Piece]:
        """Añade ``chunk`` y devuelve lo que ya no puede cambiar."""
        self._text += chunk
        return _joined(self._read_on(finished=False))

    def finish(self, *, cut: bool = False) -> list[Piece]:
        """El texto ha acabado, o se cortó con ``cut``: lo que esperaba."""
        pieces = self._read_on(finished=True, cut=cut)
        if self._space and not self._after_tag:
            pieces.append(self._space)
        self._space = ""
        pieces.extend(self._waiting)
        self._waiting.clear()
        return _joined(pieces)

    def _read_on(self, *, finished: bool, cut: bool = False) -> list[Piece]:
        pieces: list[Piece] = []
        text = self._text
        while self._read < len(text):
            start = self._read
            char = text[start]
            if self._code and char != "`":
                end = text.find("`", start)
                end = len(text) if end == -1 else end
                pieces.append(text[start:end])
            elif char == "`":
                end = _run_end(text, start)
                if end == len(text) and not finished:
                    break
                self._backticks(pieces, text[start:end])
            elif char.isspace():
                end = _space_end(text, start)
                if end == len(text) and not finished:
                    break
                self._blank(text[start:end])
            elif char == "[":
                if cut and _tag_at(text, start, finished=False) is None:
                    # Se cortó cuando aún podía ser una etiqueta: no se da.
                    self._read = len(text)
                    break
                tag = _tag_at(text, start, finished=finished)
                if tag is None:
                    break
                end, name = tag
                if name is not None and self._is_tag(name, text, start):
                    gesture = normalize(name)
                    if gesture in GESTURES:
                        self._waiting.append(Gesture(gesture))
                    self._after_tag = True
                else:
                    end = start + 1
                    self._show(pieces, "[")
            else:
                end = _seen_end(text, start)
                if self._after_tag and char in _CLOSING:
                    self._space = ""
                self._show(pieces, text[start:end])
            self._read = end
        return pieces

    @staticmethod
    def _is_tag(name: str, text: str, start: int) -> bool:
        """Si ``name``, entre los corchetes que empiezan en ``start``, es una etiqueta."""
        if normalize(name) in GESTURES:
            return True
        glued = start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_")
        return " " not in name and not glued

    def _blank(self, space: str) -> None:
        if not self._after_tag or (
            self._shown and (not self._space or space.count("\n") > self._space.count("\n"))
        ):
            self._space = space

    def _backticks(self, pieces: list[Piece], run: str) -> None:
        if not self._code:
            self._show(pieces, run)
            self._code = len(run)
            return
        pieces.append(run)
        if len(run) == self._code or (self._code >= 3 and len(run) >= 3):
            self._code = 0

    def _show(self, pieces: list[Piece], seen: str) -> None:
        """Da ``seen``, con los blancos y los gestos que esperaban delante."""
        if self._space:
            pieces.append(self._space)
            self._space = ""
        pieces.extend(self._waiting)
        self._waiting.clear()
        pieces.append(seen)
        self._after_tag = False
        self._shown = True


def strip_gestures(text: str, *, cut: bool = False) -> tuple[str, tuple[str, ...]]:
    """``text`` sin etiquetas, y los gestos de la lista que llevaba, en orden.

    Con ``cut`` es lo de una respuesta que se cortó antes de acabar: un corchete del final
    que aún podía ser una etiqueta no se da.
    """
    filtro = GestureFilter()
    pieces = filtro.feed(text) + filtro.finish(cut=cut)
    return (
        "".join(piece for piece in pieces if isinstance(piece, str)),
        tuple(piece.name for piece in pieces if isinstance(piece, Gesture)),
    )


def _joined(pieces: list[Piece]) -> list[Piece]:
    """Los trozos de texto seguidos, juntos en uno."""
    joined: list[Piece] = []
    for piece in pieces:
        last = joined[-1] if joined else None
        if isinstance(piece, str) and isinstance(last, str):
            joined[-1] = last + piece
        elif piece:
            joined.append(piece)
    return joined


def _run_end(text: str, start: int) -> int:
    end = start
    while end < len(text) and text[end] == "`":
        end += 1
    return end


def _space_end(text: str, start: int) -> int:
    end = start
    while end < len(text) and text[end].isspace():
        end += 1
    return end


def _seen_end(text: str, start: int) -> int:
    """Hasta dónde llega lo que se ve desde ``start``: hasta un blanco, un corchete, unas
    comillas invertidas o una puntuación de cierre, que va sola."""
    if text[start] in _CLOSING:
        return start + 1
    end = start + 1
    while end < len(text) and not (text[end].isspace() or text[end] in "[`" + _CLOSING):
        end += 1
    return end


def _tag_at(text: str, start: int, *, finished: bool) -> tuple[int, str | None] | None:
    """Lo que hay en ``start``, que es un corchete: dónde acaba y, si puede ser una
    etiqueta, lo que lleva entre los corchetes; ``None`` en su lugar si no puede serlo.
    ``None`` del todo si aún no se sabe, porque el texto acaba antes."""
    end = start + 1
    words = letters = 0
    previous = "["
    while end < len(text) and end - start - 1 <= _LONGEST_NAME:
        char = text[end]
        if char == "]":
            if previous in _JOINERS + "[" or letters < 2:
                return end + 1, None
            if end + 1 == len(text) and not finished:
                return None
            if end + 1 < len(text) and text[end + 1] == "(":
                return end + 1, None
            return end + 1, text[start + 1 : end]
        if char.isalpha():
            if previous in _JOINERS + "[":
                words += 1
                if words > _MOST_WORDS:
                    return end, None
            letters += 1
        elif char not in _JOINERS or previous in _JOINERS + "[":
            return end, None
        previous = char
        end += 1
    if end == len(text) and end - start - 1 <= _LONGEST_NAME and not finished:
        return None
    return end, None
