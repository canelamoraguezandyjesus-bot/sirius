"""El resumen de una charla larga (pieza D de ADR-233, PA-R02-05).

El paso 6 de la personalidad en la 0.2 del plan del robot: contra la deriva, la
charla larga se resume cada 15 a 20 turnos. Aquí se fija cuándo: cuando hay 18
turnos sin resumir, se resume todo menos los cuatro últimos, que siguen yendo tal
cual. El resumen sustituye en las peticiones a los mensajes que cubre; los
mensajes no se borran.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sirius.domain.conversation import Message, MessageRole, cut_note

#: Turnos sin resumir que disparan un resumen: dentro de los 15 a 20 del plan.
TURNS_BETWEEN_SUMMARIES = 18

#: Turnos que se quedan sin resumir, para que lo último vaya con sus palabras.
TURNS_KEPT_VERBATIM = 4

#: Quién habla en la charla que se da a resumir, al principio de cada línea: él y Sirius.
OWNER_SPEAKER = "Él"
SIRIUS_SPEAKER = "Sirius"


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    conversation_id: int
    up_to_sequence: int
    content: str


def messages_to_summarize(
    unsummarized: Sequence[Message], *, after_a_summary: bool = False
) -> tuple[Message, ...]:
    """Los mensajes que toca resumir ya, o ninguno si todavía no toca.

    ``unsummarized`` son los mensajes completos posteriores al último resumen, en
    orden. Un turno es una respuesta de Sirius.

    ``after_a_summary``: si ya hubo un resumen, sus cuatro últimos turnos siguen
    sin resumir pero ya contaron para él. El siguiente llega 18 turnos después del
    anterior, y no 14 (ronda 2 de Codex).
    """
    replies = [i for i, message in enumerate(unsummarized) if message.role is MessageRole.SIRIUS]
    needed = TURNS_BETWEEN_SUMMARIES + (TURNS_KEPT_VERBATIM if after_a_summary else 0)
    if len(replies) < needed:
        return ()
    last_summarized_reply = replies[-TURNS_KEPT_VERBATIM - 1]
    return tuple(unsummarized[: last_summarized_reply + 1])


def summary_input(previous: str | None, messages: Sequence[Message]) -> str:
    """El texto que se le da a resumir: el resumen anterior, si lo hay, y la charla. Una
    respuesta que le cortaron va entera y con lo que se oyó de ella detrás, como en los
    mensajes recientes: si no, al resumirla quedaría por dicha entera (ronda 1 de Codex
    sobre la PR #690, ADR-245)."""
    lines: list[str] = []
    if previous:
        lines += ["Resumen anterior:", previous, "", "Lo que se habló después:"]
    for message in messages:
        speaker = OWNER_SPEAKER if message.role is MessageRole.USER else SIRIUS_SPEAKER
        lines.append(f"{speaker}: {message.content or ''}")
        note = cut_note(message, in_summary=True)
        if note is not None:
            lines.append(note)
    return "\n".join(lines)


def said_turns(text: str) -> tuple[str, ...]:
    """Los comienzos de turno que lleva ``text``, escrito como ``summary_input`` o como el
    día que sueña: «Él:» o «Sirius:» al principio de una línea. Son paradas: el modelo que
    resume o que saca hechos podría seguir la charla en vez de hacer lo suyo, como en la
    charla (incidencia #700, ronda 1 de Codex sobre la PR #701)."""
    lines = text.splitlines()
    return tuple(
        f"\n{speaker}:"
        for speaker in (OWNER_SPEAKER, SIRIUS_SPEAKER)
        if any(line.startswith(f"{speaker}: ") for line in lines)
    )
