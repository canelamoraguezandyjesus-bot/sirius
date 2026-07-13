"""Minimal, presentation-safe API for managing the OpenAI API key.

Deliberately narrow: check whether a key exists, save one, delete one — no
method here ever returns the key's value. This is the *only* way
``presentation`` is allowed to touch the API key (AGENTS.md: "No accedas a
... secretos desde la interfaz"): ``MainWindow`` receives this use case, never
a ``SecretStore``, and never calls ``get_secret``. Only the composition root
retrieves the actual key value, to build ``OpenAIResponsesProvider``.
"""

from __future__ import annotations

from sirius.config.secrets_config import OPENAI_API_KEY_SECRET_NAME
from sirius.ports.secrets import SecretStore, SecretStoreError


class ApiKeySettingsError(RuntimeError):
    """Raised when saving or deleting the API key fails.

    The message is always safe: it never includes the key's value.
    """


class ApiKeySettingsUseCase:
    """Existence-check, save, and delete for the OpenAI API key. Never reads it back."""

    def __init__(self, secret_store: SecretStore) -> None:
        self._secret_store = secret_store

    def has_key(self) -> bool:
        """Return whether a key is currently saved — never the key itself."""
        return self._secret_store.get_secret(OPENAI_API_KEY_SECRET_NAME) is not None

    def save_key(self, value: str) -> None:
        try:
            self._secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, value)
        except SecretStoreError as exc:
            raise ApiKeySettingsError(str(exc)) from exc

    def delete_key(self) -> None:
        try:
            self._secret_store.delete_secret(OPENAI_API_KEY_SECRET_NAME)
        except SecretStoreError as exc:
            raise ApiKeySettingsError(str(exc)) from exc
