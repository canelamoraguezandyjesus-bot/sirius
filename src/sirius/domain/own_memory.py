"""La memoria propia de Sirius (pieza E de ADR-233, PA-R02-07).

El paso 3 de la personalidad en la 0.2 del plan del robot: «Su propia memoria:
quién es, qué opiniones ha dado y qué bromas funcionaron y cuáles no. Así no se
contradice sin motivo ni repite chistes». Y el paso 5: las dos marcas «sirven ya
como ejemplos».

- **Quién es** ya va en cada petición: la semilla (pieza B).
- **Lo que ya ha dicho de esto**: sus respuestas que comparten palabras con el
  mensaje y que no van ya entre los mensajes recientes. Las marcadas «eso no» no
  entran nunca aquí: no son opiniones que mantener.
- **Lo que sí es y lo que no es**: sus últimas respuestas marcadas «eso es
  Sirius» y «eso no».

Busca por palabras. La búsqueda por significado es de la pieza F.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass

from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.reply_mark import MarkedReply, ReplyMark

#: Cuántas respuestas entran en cada parte de su memoria propia.
OWN_MEMORY_LIMIT = 3

#: Cuántos caracteres de cada respuesta, como mucho.
QUOTE_LIMIT = 300

SAID_HEADING = "# Lo que ya has dicho de esto"
IS_YOU_HEADING = "# Lo que sí eres"
NOT_YOU_HEADING = "# Lo que no eres"

_SAID_GUIDE = (
    "Lo dijiste tú en esta charla, hace un rato o hace días. No te contradigas sin un "
    "motivo: si cambias de opinión, di por qué. Y no repitas el chiste."
)
_IS_YOU_GUIDE = "Respuestas tuyas que él marcó «eso es Sirius». Es el tono, no frases para repetir."
_NOT_YOU_GUIDE = "Respuestas tuyas que él marcó «eso no». No hables así."

#: Palabras que no dicen de qué se habla. Sin tildes y de cuatro letras o más,
#: porque las más cortas ya se descartan por su longitud.
_NOT_TOPIC_WORDS = (
    "ahora algo alguien algun alguna alguno alla alli antes aqui bien buen buena buenas "
    "bueno buenos cada casi claro como contra cosa cosas creo cual cuales cuando cuanto "
    "dame decir desde despues dice dices dicho digo dime donde ella ellas ellos "
    "entonces entre eres esas esos esta estan estas este esto estos estoy fuera gracias "
    "haber habia hace hacer haces hacia hago hasta hola igual jefe luego mejor mira "
    "misma mismo mucha muchas mucho muchos nada nadie nunca opinas otra otras otro "
    "otros para parece pero piensas poco porq porque puede puedes puedo pues quien "
    "quiere quieres quiero saber sabes segun sera seria siempre sino sirius sobre solo "
    "somos tambien tampoco tanto tenemos tengo tiene tienes toda todas todo todos tuya "
    "tuyo vale vamos venga verdad vosotros"
)
_NOT_TOPIC: frozenset[str] = frozenset(_NOT_TOPIC_WORDS.split())
_MIN_LENGTH = 4
_WORD = re.compile(r"[^\W_]+")


@dataclass(frozen=True, slots=True)
class OwnMemory:
    """Lo que entra de su memoria propia en una petición, ya recortado."""

    said: tuple[str, ...] = ()
    is_you: tuple[str, ...] = ()
    not_you: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.said or self.is_you or self.not_you)


def _plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def topic_words(text: str) -> frozenset[str]:
    """Las palabras de ``text`` que dicen de qué se habla: sin tildes, sin las vacías."""
    return frozenset(
        word
        for word in _WORD.findall(_plain(text))
        if len(word) >= _MIN_LENGTH and word not in _NOT_TOPIC and not word.isdigit()
    )


def _forms(word: str) -> set[str]:
    """La palabra y su singular probable: «cebollas» y «cebolla», «opiniones» y «opinion»."""
    forms = {word}
    if word.endswith("es") and len(word) > _MIN_LENGTH + 1:
        forms.add(word[:-2])
    if word.endswith("s") and len(word) > _MIN_LENGTH:
        forms.add(word[:-1])
    return forms


def shared_topic_words(words: Iterable[str], text: str) -> int:
    """Cuántas de ``words`` aparecen en ``text``, en singular o en plural."""
    present = {form for word in topic_words(text) for form in _forms(word)}
    return sum(1 for word in words if _forms(word) & present)


def _quote(text: str) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= QUOTE_LIMIT:
        return one_line
    return one_line[: QUOTE_LIMIT - 1].rstrip() + "…"


def _is_reply(message: Message) -> bool:
    return (
        message.role is MessageRole.SIRIUS
        and message.status is MessageStatus.COMPLETED
        and bool(message.content)
    )


def build_own_memory(
    current_user_message: str,
    messages: Sequence[Message],
    marked: Sequence[MarkedReply],
    *,
    in_request: Collection[int] = (),
) -> OwnMemory:
    """Su memoria propia para responder a ``current_user_message``.

    ``messages`` son los de la charla, en orden; ``in_request``, los ids de los
    que ya van en la petición como mensajes recientes, que no se repiten como
    «ya lo dijiste». ``marked`` son sus respuestas marcadas, en orden.
    """
    replies = {message.id: message for message in messages if _is_reply(message)}
    marks = {reply.message_id: reply.mark for reply in marked}

    words = topic_words(current_user_message)
    candidates = [
        (shared_topic_words(words, message.content or ""), message)
        for message in replies.values()
        if message.id not in in_request and marks.get(message.id) is not ReplyMark.NO_ES_SIRIUS
    ]
    best = sorted(
        ((score, message) for score, message in candidates if score > 0),
        key=lambda pair: (-pair[0], -pair[1].sequence),
    )[:OWN_MEMORY_LIMIT]
    said_messages = sorted((message for _, message in best), key=lambda m: m.sequence)
    said_ids = {message.id for message in said_messages}

    def last_marked(mark: ReplyMark) -> tuple[str, ...]:
        chosen = [
            replies[reply.message_id]
            for reply in marked
            if reply.mark is mark
            and reply.message_id in replies
            and reply.message_id not in said_ids
        ][-OWN_MEMORY_LIMIT:]
        return tuple(_quote(message.content or "") for message in chosen)

    return OwnMemory(
        said=tuple(_quote(message.content or "") for message in said_messages),
        is_you=last_marked(ReplyMark.ES_SIRIUS),
        not_you=last_marked(ReplyMark.NO_ES_SIRIUS),
    )


def render_own_memory(own_memory: OwnMemory) -> list[str]:
    """Las líneas de las instrucciones con su memoria propia; vacías si no hay nada."""
    lines: list[str] = []
    for heading, guide, quotes in (
        (SAID_HEADING, _SAID_GUIDE, own_memory.said),
        (IS_YOU_HEADING, _IS_YOU_GUIDE, own_memory.is_you),
        (NOT_YOU_HEADING, _NOT_YOU_GUIDE, own_memory.not_you),
    ):
        if quotes:
            lines += [heading, guide, *(f"- «{quote}»" for quote in quotes), ""]
    return lines
