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

from sirius.domain.conversation import Message, MessageRole

#: Turnos sin resumir que disparan un resumen: dentro de los 15 a 20 del plan.
TURNS_BETWEEN_SUMMARIES = 18

#: Turnos que se quedan sin resumir, para que lo último vaya con sus palabras.
TURNS_KEPT_VERBATIM = 4


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    conversation_id: int
    up_to_sequence: int
    content: str


def messages_to_summarize(unsummarized: Sequence[Message]) -> tuple[Message, ...]:
    """Los mensajes que toca resumir ya, o ninguno si todavía no toca.

    ``unsummarized`` son los mensajes completos posteriores al último resumen, en
    orden. Un turno es una respuesta de Sirius.
    """
    replies = [i for i, message in enumerate(unsummarized) if message.role is MessageRole.SIRIUS]
    if len(replies) < TURNS_BETWEEN_SUMMARIES:
        return ()
    last_summarized_reply = replies[-TURNS_KEPT_VERBATIM - 1]
    return tuple(unsummarized[: last_summarized_reply + 1])


def summary_input(previous: str | None, messages: Sequence[Message]) -> str:
    """El texto que se le da a resumir: el resumen anterior, si lo hay, y la charla."""
    lines: list[str] = []
    if previous:
        lines += ["Resumen anterior:", previous, "", "Lo que se habló después:"]
    for message in messages:
        speaker = "Él" if message.role is MessageRole.USER else "Sirius"
        lines.append(f"{speaker}: {message.content or ''}")
    return "\n".join(lines)
