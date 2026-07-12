"""Provider-neutral secret storage contract."""

from __future__ import annotations

from typing import Protocol


class SecretStore(Protocol):
    """Contract implemented by real and simulated secret stores."""

    def get_secret(self, key: str) -> str | None:
        """Return the stored secret for key, or None if absent."""
        ...

    def set_secret(self, key: str, value: str) -> None:
        """Store or replace the secret for key."""
        ...

    def delete_secret(self, key: str) -> None:
        """Remove the secret for key if present."""
        ...
