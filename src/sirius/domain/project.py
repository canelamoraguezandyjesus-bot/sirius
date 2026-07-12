"""Domain entity for the single active project."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Project:
    """The single active project Sirius helps carry forward across sessions."""

    id: int
    name: str
    objective: str
    current_state: str
    next_step: str
    created_at: datetime
    updated_at: datetime
