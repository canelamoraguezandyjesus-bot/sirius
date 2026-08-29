"""Domain entity for the persistent origin event a memory revision links to.

SIRIUS-ARQ-0.1 S7.1/S7.3 defines a generic ``event`` table ("Auditoría
cronológica de cambios con referencias y contenido redactable") shared by
every future kind of origin event (memory, decision, project...). B4a
implements only the minimal slice RF-019/RF-021 need: the event that records
an explicit, manual memory save, optionally referencing the user message
that triggered it. ``redacted_at`` is part of the architecture's minimum
field list; this codebase's ``Event`` carries no content of its own to
redact (only a ``message_id`` reference, see B4a), so B4d leaves it unused
(always ``None``) here too and instead redacts the referenced *message*
itself (``ConversationRepository.redact_message``, RF-025/DR-012's "El
mensaje fuente se redacta solo si el usuario lo solicita") — mirroring how
``project_revisions.source_event_id`` was added unused in B3c ahead of this
table existing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MANUAL_MEMORY_SAVE_EVENT_TYPE = "memory.manual_save"
MEMORY_CORRECTED_EVENT_TYPE = "memory.corrected"
MEMORY_ARCHIVED_EVENT_TYPE = "memory.archived"
MEMORY_DELETED_EVENT_TYPE = "memory.deleted"
DECISION_PROPOSED_EVENT_TYPE = "decision.proposed"
DECISION_APPROVED_EVENT_TYPE = "decision.approved"
DECISION_SUPERSEDED_EVENT_TYPE = "decision.superseded"
DECISION_ARCHIVED_EVENT_TYPE = "decision.archived"
MEMORY_SUGGESTION_PROPOSED_EVENT_TYPE = "memory_suggestion.proposed"
MEMORY_SUGGESTION_CONFIRMED_EVENT_TYPE = "memory_suggestion.confirmed"
MEMORY_SUGGESTION_REJECTED_EVENT_TYPE = "memory_suggestion.rejected"
USER_ACTOR = "user"


@dataclass(frozen=True, slots=True)
class Event:
    """An immutable audit record of the action that produced a memory revision."""

    id: int
    event_type: str
    actor: str
    message_id: int | None
    created_at: datetime
    redacted_at: datetime | None
