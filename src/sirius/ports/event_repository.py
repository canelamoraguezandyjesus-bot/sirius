"""Persistence contract for origin events, independent of SQLAlchemy."""

from __future__ import annotations

from typing import Protocol

from sirius.domain.event import Event


class EventRepository(Protocol):
    """Contract implemented by real and simulated event stores.

    B4a implements only the two operations RF-019/RF-021 need: recording a
    new event (``append``) and reading one back by id (``get_source``).
    Redaction (``redact_content`` in the approved architecture's full
    ``EventRepository`` contract) belongs to B4d and is not implemented yet.
    """

    def append(self, event_type: str, actor: str, message_id: int | None) -> Event:
        """Record a new immutable origin event and return it."""
        ...

    def get_source(self, event_id: int) -> Event | None:
        """Return an event by id, or ``None`` if it does not exist."""
        ...
