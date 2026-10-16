"""Domain entities for the main conversation and its messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MessageRole(StrEnum):
    """Who authored a message."""

    USER = "user"
    SIRIUS = "sirius"


class MessageStatus(StrEnum):
    """Lifecycle outcome of a message.

    SIRIUS-ARQ-0.1 S5.1: "Al terminar, se guarda la respuesta final... y
    estado COMPLETADO. Ante cancelación o fallo, se conserva el contenido
    parcial con estado CANCELADO o FALLIDO y no se usa como respuesta
    completa." USER messages are always ``COMPLETED``: they are written in a
    single synchronous step and never partial.

    ``REDACTED`` (B4d, RF-025/DR-012) is the architecture's minimal field
    list for ``message`` (S7.3: "contenido NULL solo si REDACTADO"): set only
    when the user explicitly chooses to redact a memory's source message
    while deleting that memory (``DeleteMemoryUseCase``) — never
    automatically, and never for any other message in the conversation.
    """

    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REDACTED = "redacted"


class SourceMessageChoice(StrEnum):
    """The explicit choice RF-025/DR-012 require when deleting a memory:
    whether its source message is preserved untouched or redacted.

    "El mensaje de origen no se elimina automáticamente. El usuario puede
    elegir también redactar su contenido" (Product S7). There is
    deliberately no default: ``DeleteMemoryUseCase.delete`` requires this as
    an explicit keyword argument so an absent, invalid, or ambiguous choice
    fails before any transaction opens.
    """

    PRESERVE = "preserve"
    REDACT = "redact"


@dataclass(frozen=True, slots=True)
class Conversation:
    """The single main conversation Sirius maintains in 0.1."""

    id: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Message:
    """A single message belonging to a conversation, in stable order.

    ``operation_id`` traces which send/receive operation produced the
    message — the USER message and the SIRIUS message of one turn share the
    same ``operation_id``. ``identity_version`` records which version of
    Sirius's identity produced a SIRIUS message (RF-010). Both are ``None``
    for messages predating V6B and ``identity_version`` is always ``None``
    for USER messages. ``status`` is ``CANCELLED``/``FAILED`` only for a
    SIRIUS message whose stream did not complete; such a message keeps its
    partial content for traceability but must be excluded when building the
    recent-history section of a future context (SIRIUS-ARQ-0.1 S5.1/S5.2:
    "Mensajes parciales conservan su contenido y quedan excluidos del
    contexto normal"). A ``REDACTED`` message (B4d) is excluded from that
    same recent-history section for the same reason: ``content`` is ``None``
    and only ``sequence``/``created_at``/the redaction marker itself
    (``status``, ``redacted_at``) remain, per Product S7 "conservando solo
    secuencia, fecha y marcador de eliminación".

    ``content`` is ``str | None`` because it becomes ``None`` exactly once
    redacted; every other status always carries real (possibly partial)
    content.

    ``heard_when_cut`` (ADR-245): si a Sirius le cortaron esta respuesta mientras la
    decía, lo que el propietario llegó a oír de ella; ``None`` si no le cortaron. El
    contenido sigue entero.
    """

    id: int
    conversation_id: int
    sequence: int
    role: MessageRole
    content: str | None
    created_at: datetime
    operation_id: str | None = None
    identity_version: int | None = None
    status: MessageStatus = MessageStatus.COMPLETED
    redacted_at: datetime | None = None
    heard_when_cut: str | None = None


#: Cómo lee Sirius, en los mensajes recientes, una respuesta suya que le cortaron mientras
#: la decía (ADR-245): entera, y detrás lo que el propietario llegó a oír, para que no dé
#: por dicho lo que no sonó.
CUT_HEARD = "(Te cortó mientras lo decías: solo llegó a oír «{heard}».)"
#: Lo mismo, si le cortaron antes de que sonara nada.
CUT_NOTHING_HEARD = "(Te cortó antes de que llegara a oír nada de esto.)"
#: Cómo lo lee quien resume la charla, que habla de él y de Sirius en tercera persona.
CUT_HEARD_IN_SUMMARY = "(Él le cortó mientras lo decía: solo llegó a oír «{heard}».)"
CUT_NOTHING_HEARD_IN_SUMMARY = "(Él le cortó antes de que llegara a oír nada de esto.)"


def cut_note(message: Message, *, in_summary: bool = False) -> str | None:
    """La nota que va detrás de una respuesta que le cortaron, para quien se la lea al
    modelo; ``None`` si no le cortaron (ADR-245).

    Todo lo que le lee al modelo una respuesta pasada la lleva: los mensajes recientes, lo
    que cuestan en el contexto y lo que se le da a resumir. Con ``in_summary``, en
    tercera persona, como habla la entrada del resumen.
    """
    heard = message.heard_when_cut
    if heard is None:
        return None
    if in_summary:
        return CUT_HEARD_IN_SUMMARY.format(heard=heard) if heard else CUT_NOTHING_HEARD_IN_SUMMARY
    return CUT_HEARD.format(heard=heard) if heard else CUT_NOTHING_HEARD
