"""Provider-neutral secret storage contract.

Method names mirror SIRIUS-ARQ-0.1 S4 exactly: ``get_secret``,
``set_secret``, ``delete_secret``, ``is_secure_backend``.
"""

from __future__ import annotations

from typing import Protocol


class SecretStoreError(RuntimeError):
    """Raised when a secret store operation fails.

    The message is always safe: it never includes the secret's value, only a
    fixed, generic description of what went wrong.
    """


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

    def is_secure_backend(self) -> bool:
        """Return whether the active backend is a real, secure credential store.

        SIRIUS-ARQ-0.1 S11.1: "Si el backend seguro no está disponible,
        Sirius no cae silenciosamente a texto plano." Callers must treat a
        ``False`` result as a reason to refuse writing a secret, not as
        permission to fall back to plaintext.
        """
        ...
