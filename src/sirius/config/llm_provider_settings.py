"""Provisional (pre-V7) configuration for choosing and configuring the LLM provider.

This is explicitly temporary: until V7 introduces Windows Credential Manager
and a real secret store, the API key is read *only* from the ``OPENAI_API_KEY``
environment variable, never written to ``settings.json``, SQLite, logs, or
error messages. Provider selection and model/limits are non-sensitive and
read from environment variables so no secret ever needs to be persisted to
enable "openai" mode.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

_DEFAULT_MODEL = "gpt-5.6-terra"  # DR-017: reference model
_DEFAULT_MAX_OUTPUT_TOKENS = 4096  # SIRIUS-ARQ-0.1 S9: "Salida normal 4.096 tokens"


class LLMProviderKind(StrEnum):
    """Which LLMProvider implementation the composition root should build."""

    FAKE = "fake"
    OPENAI = "openai"


class LLMProviderConfigurationError(RuntimeError):
    """Raised when 'openai' is selected but the key or model are not usable.

    The message is always safe: it never includes the key's value or any
    part of it.
    """


@dataclass(frozen=True, slots=True)
class OpenAIProviderSettings:
    """Non-sensitive settings needed to build the OpenAI adapter; no API key here."""

    model: str
    max_output_tokens: int


def resolve_provider_kind() -> LLMProviderKind:
    """Read the provider selection from ``SIRIUS_LLM_PROVIDER``.

    Unset (or blank) defaults to ``fake`` — the safe mode when nothing was
    asked for. But once the user *has* set a value, only ``"fake"`` and
    ``"openai"`` are valid: an unrecognized value raises
    ``LLMProviderConfigurationError`` instead of silently falling back to
    fake, so a typo can never be mistaken for "OpenAI is off".
    """
    raw_value = os.environ.get("SIRIUS_LLM_PROVIDER")
    if raw_value is None or not raw_value.strip():
        return LLMProviderKind.FAKE

    normalized = raw_value.strip().lower()
    if normalized == LLMProviderKind.FAKE.value:
        return LLMProviderKind.FAKE
    if normalized == LLMProviderKind.OPENAI.value:
        return LLMProviderKind.OPENAI

    msg = (
        f"SIRIUS_LLM_PROVIDER={raw_value!r} no es válido. "
        "Los únicos valores admitidos son 'fake' y 'openai'."
    )
    raise LLMProviderConfigurationError(msg)


def resolve_openai_api_key() -> str | None:
    """Read the API key exclusively from ``OPENAI_API_KEY``. Never persisted."""
    return os.environ.get("OPENAI_API_KEY") or None


def resolve_openai_provider_settings() -> OpenAIProviderSettings:
    """Read the non-sensitive OpenAI settings (model, output token limit)."""
    model = os.environ.get("SIRIUS_OPENAI_MODEL", "").strip() or _DEFAULT_MODEL
    raw_max_output_tokens = os.environ.get("SIRIUS_OPENAI_MAX_OUTPUT_TOKENS", "").strip()
    max_output_tokens = _DEFAULT_MAX_OUTPUT_TOKENS
    if raw_max_output_tokens:
        try:
            max_output_tokens = int(raw_max_output_tokens)
        except ValueError as exc:
            msg = "SIRIUS_OPENAI_MAX_OUTPUT_TOKENS must be a whole number of tokens."
            raise LLMProviderConfigurationError(msg) from exc
    if max_output_tokens <= 0:
        msg = "SIRIUS_OPENAI_MAX_OUTPUT_TOKENS must be a positive number of tokens."
        raise LLMProviderConfigurationError(msg)
    return OpenAIProviderSettings(model=model, max_output_tokens=max_output_tokens)
