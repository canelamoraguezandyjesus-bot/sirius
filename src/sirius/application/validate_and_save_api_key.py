"""Validate an OpenAI API key before storing it in the secure backend."""

from __future__ import annotations

from sirius.config.secrets_config import OPENAI_API_KEY_SECRET_NAME
from sirius.ports.credential_validation import (
    CredentialValidationError,
    CredentialValidator,
)
from sirius.ports.secrets import SecretStore, SecretStoreError

__all__ = [
    "CredentialValidationError",
    "ValidateAndSaveApiKeyError",
    "ValidateAndSaveApiKeyUseCase",
]


class ValidateAndSaveApiKeyError(RuntimeError):
    """Safe failure while writing an already validated key."""


class ValidateAndSaveApiKeyUseCase:
    """Validate first and persist only after successful provider validation."""

    def __init__(self, validator: CredentialValidator, secret_store: SecretStore) -> None:
        self._validator = validator
        self._secret_store = secret_store

    def validate_and_save(self, value: str, model: str) -> None:
        self._validator.validate(value, model)
        try:
            self._secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, value)
        except SecretStoreError as exc:
            raise ValidateAndSaveApiKeyError(
                "No se pudo guardar la clave en el almacén seguro de Windows."
            ) from exc
