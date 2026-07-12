"""Domain entities for the main conversation and its messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MessageRole(StrEnum):
    """Who authored a message."""

    USER = "user"
    SIRIUS = "sirius"


@dataclass(frozen=True, slots=True)
class Conversation:
    """The single main conversation Sirius maintains in 0.1."""

    id: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Message:
    """A single message belonging to a conversation, in stable order."""

    id: int
    conversation_id: int
    sequence: int
    role: MessageRole
    content: str
    created_at: datetime
