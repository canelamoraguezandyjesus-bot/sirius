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
    """

    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


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
    contexto normal").
    """

    id: int
    conversation_id: int
    sequence: int
    role: MessageRole
    content: str
    created_at: datetime
    operation_id: str | None = None
    identity_version: int | None = None
    status: MessageStatus = MessageStatus.COMPLETED
