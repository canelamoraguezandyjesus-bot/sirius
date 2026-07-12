"""Persistence contract for Sirius's versioned identity, independent of SQLAlchemy."""

from __future__ import annotations

from typing import Protocol

from sirius.domain.identity import Identity, IdentityVersion


class IdentityRepository(Protocol):
    """Contract implemented by real and simulated identity stores."""

    def get_or_create_current_identity(self) -> Identity:
        """Return the current identity, seeding it from the canonical version if absent."""
        ...

    def get_current_identity(self) -> Identity | None:
        """Return the current identity if it exists, without creating it."""
        ...

    def get_history(self) -> list[IdentityVersion]:
        """Return every identity version, in stable version order."""
        ...

    def create_new_version(
        self, name: str, description: str, personality_instructions: str
    ) -> Identity:
        """Create a new current version without overwriting the previous one."""
        ...
