"""OpenAI credential validation adapter.

Validation is deliberately separate from ``OpenAIResponsesProvider.health_check``.
It performs one minimal provider request and never persists or logs the
credential. Tests inject a fake client factory, so the normal suite never uses
network access.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

import openai

from sirius.infrastructure.logging import get_logger
from sirius.ports.credential_validation import (
    CredentialValidationError,
    CredentialValidationKind,
)

_logger = get_logger(__name__)


class _ModelsResource(Protocol):
    def retrieve(self, model: str) -> object: ...


class _OpenAIClient(Protocol):
    @property
    def models(self) -> _ModelsResource: ...


ClientFactory = Callable[[str], _OpenAIClient]


def _default_client_factory(credential: str) -> _OpenAIClient:
    return cast(
        _OpenAIClient,
        openai.OpenAI(api_key=credential, max_retries=0, timeout=10.0),
    )


def _classify_exception(exc: Exception) -> CredentialValidationKind:
    if isinstance(exc, openai.AuthenticationError):
        return CredentialValidationKind.AUTHENTICATION
    if isinstance(exc, openai.PermissionDeniedError):
        return CredentialValidationKind.PERMISSION
    if isinstance(exc, openai.RateLimitError):
        return CredentialValidationKind.RATE_LIMITED
    if isinstance(exc, openai.APITimeoutError):
        return CredentialValidationKind.TIMEOUT
    if isinstance(exc, openai.APIConnectionError | openai.InternalServerError):
        return CredentialValidationKind.CONNECTION
    return CredentialValidationKind.UNKNOWN


class OpenAICredentialValidator:
    """Validate a candidate key against the configured OpenAI model."""

    def __init__(self, client_factory: ClientFactory = _default_client_factory) -> None:
        self._client_factory = client_factory

    def validate(self, credential: str, model: str) -> None:
        if not credential.strip() or not model.strip():
            raise CredentialValidationError(CredentialValidationKind.CONFIGURATION)

        try:
            client = self._client_factory(credential)
            client.models.retrieve(model)
        except Exception as exc:
            kind = _classify_exception(exc)
            _logger.warning("Validación de credencial rechazada (%s)", kind.value)
            raise CredentialValidationError(kind) from exc
