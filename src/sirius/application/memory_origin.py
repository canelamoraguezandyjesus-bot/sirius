"""Consulta del origen de un recuerdo manual (B4a, RF-021).

RF-021 "Consultar origen: Abrir el evento o mensaje de procedencia." Mirrors
``ProjectContinuityUseCase``: a small, explicit, read-only contract so a
future caller never touches ``MemoryRepository``, ``EventRepository``,
``ConversationRepository``, SQLAlchemy, or SQLite directly (AGENTS.md:
dependency direction presentation -> application -> domain).

Every failure mode — an unknown memory id, a memory with no recorded origin
(every revision that predates B4a), or a source event that has vanished — is
translated into the single typed ``MemoryOriginNotFoundError`` instead of
letting a raw ``ValueError``/``KeyError`` from a lower layer escape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.event_repository import EventRepository
from sirius.ports.memory_repository import MemoryRepository

__all__ = [
    "GetMemoryOriginUseCase",
    "MemoryOrigin",
    "MemoryOriginNotFoundError",
]


class MemoryOriginNotFoundError(LookupError):
    """Raised when a memory, or its recorded origin, cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class MemoryOrigin:
    """Presentation-ready snapshot of a memory's origin, opened for consultation.

    ``message_content`` is ``None`` when the event has no linked message (a
    save with no message context) — never a silent failure, since
    ``event_type``/``actor``/``created_at`` are always present.
    """

    event_id: int
    event_type: str
    actor: str
    created_at: datetime
    message_id: int | None
    message_content: str | None


class GetMemoryOriginUseCase:
    """Abre el origen (evento y, si existe, mensaje) de un recuerdo (RF-021)."""

    def __init__(
        self,
        memory_repository: MemoryRepository,
        event_repository: EventRepository,
        conversation_repository: ConversationRepository,
    ) -> None:
        self._memory_repository = memory_repository
        self._event_repository = event_repository
        self._conversation_repository = conversation_repository

    def get_origin(self, memory_id: int) -> MemoryOrigin:
        """Return the origin of a memory's current revision.

        Raises ``MemoryOriginNotFoundError`` if ``memory_id`` is unknown, the
        current revision has no recorded ``source_event_id`` (nothing to
        open), or the referenced event no longer exists.
        """
        try:
            memory = self._memory_repository.get_memory(memory_id)
        except Exception as exc:
            raise MemoryOriginNotFoundError(f"Recuerdo desconocido: {memory_id}") from exc

        source_event_id = memory.current_revision.source_event_id
        if source_event_id is None:
            raise MemoryOriginNotFoundError(
                f"El recuerdo {memory_id} no tiene un origen registrado."
            )

        event = self._event_repository.get_source(source_event_id)
        if event is None:
            raise MemoryOriginNotFoundError(f"Evento de origen desconocido: {source_event_id}")

        message_content: str | None = None
        if event.message_id is not None:
            message = self._conversation_repository.get_message(event.message_id)
            message_content = message.content if message is not None else None

        return MemoryOrigin(
            event_id=event.id,
            event_type=event.event_type,
            actor=event.actor,
            created_at=event.created_at,
            message_id=event.message_id,
            message_content=message_content,
        )
