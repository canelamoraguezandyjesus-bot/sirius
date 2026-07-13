"""Real secret store backed by ``keyring`` (Windows Credential Manager).

Only this module (and its tests) may import ``keyring``: ``application``,
``domain``, and ``presentation`` see the ``SecretStore`` port only
(``sirius.ports.secrets``), never this adapter or the ``keyring`` package
directly (AGENTS.md: "No accedas a ... secretos desde la interfaz").
"""

from __future__ import annotations

import keyring
import keyring.errors
from keyring.backends.fail import Keyring as FailKeyring

from sirius.config.secrets_config import SIRIUS_KEYRING_SERVICE_NAME
from sirius.ports.secrets import SecretStoreError

_UNAVAILABLE_MESSAGE = "El almacén seguro de credenciales de Windows no está disponible."
_ACCESS_FAILED_MESSAGE = "No se pudo acceder al almacén seguro de credenciales de Windows."


class KeyringSecretStore:
    """Stores secrets via ``keyring``, under one stable service name.

    Never falls back to plaintext: if the active backend is not a real
    secure store (``is_secure_backend()`` is False — e.g. keyring found no
    usable OS backend), ``set_secret`` refuses to write instead of silently
    persisting the value some other way (SIRIUS-ARQ-0.1 S11.1).
    """

    def __init__(self, service_name: str = SIRIUS_KEYRING_SERVICE_NAME) -> None:
        self._service_name = service_name

    def is_secure_backend(self) -> bool:
        return not isinstance(keyring.get_keyring(), FailKeyring)

    def get_secret(self, key: str) -> str | None:
        try:
            return keyring.get_password(self._service_name, key)
        except keyring.errors.KeyringError as exc:
            raise SecretStoreError(_ACCESS_FAILED_MESSAGE) from exc

    def set_secret(self, key: str, value: str) -> None:
        if not self.is_secure_backend():
            raise SecretStoreError(_UNAVAILABLE_MESSAGE)
        try:
            keyring.set_password(self._service_name, key, value)
        except keyring.errors.KeyringError as exc:
            raise SecretStoreError(_ACCESS_FAILED_MESSAGE) from exc

    def delete_secret(self, key: str) -> None:
        try:
            keyring.delete_password(self._service_name, key)
        except keyring.errors.PasswordDeleteError:
            return  # Matches FakeSecretStore: deleting an absent key is a no-op.
        except keyring.errors.KeyringError as exc:
            raise SecretStoreError(_ACCESS_FAILED_MESSAGE) from exc


def build_keyring_secret_store() -> KeyringSecretStore:
    """Build the production ``SecretStore`` used by the composition root."""
    return KeyringSecretStore()
