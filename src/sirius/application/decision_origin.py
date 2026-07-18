"""Consulta de una decisión y su origen (B4b, RF-020, ALCANCE #9).

Mirrors ``GetMemoryOriginUseCase`` (B4a): a small, explicit, read-only
contract so a future caller never touches ``DecisionRepository``,
``EventRepository``, ``ConversationRepository``, SQLAlchemy, or SQLite
directly (AGENTS.md: dependency direction presentation -> application ->
domain). ``DecisionOrigin`` exposes everything RF-020 requires a decision to
observably carry — asunto, proyecto, estado, versión, fecha — together with
the event (and, when it exists, the message) that produced it, in a single
query, so verifying "de dónde procede" a decision never needs more than one
call.

Every failure mode — an unknown decision id, a decision with no recorded
origin, or a source event that has vanished — is translated into the single
typed ``DecisionOriginNotFoundError`` instead of letting a raw
``ValueError``/``KeyError`` from a lower layer escape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius.domain.decision import DecisionStatus
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.event_repository import EventRepository

__all__ = [
    "DecisionOrigin",
    "DecisionOriginNotFoundError",
    "GetDecisionOriginUseCase",
]


class DecisionOriginNotFoundError(LookupError):
    """Raised when a decision, or its recorded origin, cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class DecisionOrigin:
    """Presentation-ready snapshot of a decision and its origin.

    ``message_content`` is ``None`` when the event has no linked message (a
    proposal with no message context) — never a silent failure, since every
    other field is always present.
    """

    decision_id: int
    subject: str
    project_id: int
    status: DecisionStatus
    version: int
    created_at: datetime
    event_id: int
    event_type: str
    actor: str
    event_created_at: datetime
    message_id: int | None
    message_content: str | None


class GetDecisionOriginUseCase:
    """Abre el origen (evento y, si existe, mensaje) de una decisión (RF-020)."""

    def __init__(
        self,
        decision_repository: DecisionRepository,
        event_repository: EventRepository,
        conversation_repository: ConversationRepository,
    ) -> None:
        self._decision_repository = decision_repository
        self._event_repository = event_repository
        self._conversation_repository = conversation_repository

    def get_origin(self, decision_id: int) -> DecisionOrigin:
        """Return the decision and the origin of its current revision.

        Raises ``DecisionOriginNotFoundError`` if ``decision_id`` is unknown,
        the current revision has no recorded ``source_event_id`` (nothing to
        open), or the referenced event no longer exists.
        """
        try:
            decision = self._decision_repository.get_decision(decision_id)
        except Exception as exc:
            raise DecisionOriginNotFoundError(f"Decisión desconocida: {decision_id}") from exc

        source_event_id = decision.current_revision.source_event_id
        if source_event_id is None:
            raise DecisionOriginNotFoundError(
                f"La decisión {decision_id} no tiene un origen registrado."
            )

        event = self._event_repository.get_source(source_event_id)
        if event is None:
            raise DecisionOriginNotFoundError(f"Evento de origen desconocido: {source_event_id}")

        message_content: str | None = None
        if event.message_id is not None:
            message = self._conversation_repository.get_message(event.message_id)
            message_content = message.content if message is not None else None

        return DecisionOrigin(
            decision_id=decision.id,
            subject=decision.subject,
            project_id=decision.project_id,
            status=decision.status,
            version=decision.current_revision.version,
            created_at=decision.created_at,
            event_id=event.id,
            event_type=event.event_type,
            actor=event.actor,
            event_created_at=event.created_at,
            message_id=event.message_id,
            message_content=message_content,
        )
