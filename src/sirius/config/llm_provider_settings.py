"""Configuration for choosing and configuring the LLM provider (V7A).

Provider, model, output token limit, and monthly budget are non-sensitive and
live in ``settings.json`` (see ``sirius.config.settings``), editable from the
"Configuración" tab. The OpenAI API key is never part of that file: it comes
from the injected ``SecretStore`` (Windows Credential Manager in production).
``OPENAI_API_KEY`` may still be read as an explicit developer override when
the secret store has nothing stored — SIRIUS-ARQ-0.1 S11.1: "Los archivos
.env solo se permiten en desarrollo local... nunca son formato de
producción" — it is never the normal user flow.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sirius.config.secrets_config import OPENAI_API_KEY_SECRET_NAME
from sirius.ports.secrets import SecretStore

_DEFAULT_MODEL = "gpt-5.6-terra"  # DR-017: reference model
_DEFAULT_MAX_OUTPUT_TOKENS = 4096  # SIRIUS-ARQ-0.1 S9: "Salida normal 4.096 tokens"
_DEFAULT_MONTHLY_BUDGET_USD = 20.0  # SIRIUS-ARQ-0.1 S9.1: "Envolvente mensual aprobada: 20 USD"


class LLMProviderKind(StrEnum):
    """Which LLMProvider implementation the composition root should build."""

    FAKE = "fake"
    OPENAI = "openai"


class LLMProviderConfigurationError(RuntimeError):
    """Raised when 'openai' is selected but the configuration is not usable.

    The message is always safe: it never includes the key's value or any
    part of it.
    """


@dataclass(frozen=True, slots=True)
class OpenAIProviderSettings:
    """Non-sensitive settings needed to build the OpenAI adapter; no API key here."""

    model: str
    max_output_tokens: int
    monthly_budget_usd: float


def resolve_provider_kind(settings: dict[str, Any]) -> LLMProviderKind:
    """Read the provider selection from persisted settings (key ``llm_provider``).

    Unset (or blank) defaults to ``fake`` — the safe mode when nothing was
    asked for. But once a value *is* present, only ``"fake"`` and ``"openai"``
    are valid: an unrecognized value raises ``LLMProviderConfigurationError``
    instead of silently falling back to fake, so a typo can never be mistaken
    for "OpenAI is off".
    """
    raw_value = settings.get("llm_provider")
    if raw_value is None or not str(raw_value).strip():
        return LLMProviderKind.FAKE

    normalized = str(raw_value).strip().lower()
    if normalized == LLMProviderKind.FAKE.value:
        return LLMProviderKind.FAKE
    if normalized == LLMProviderKind.OPENAI.value:
        return LLMProviderKind.OPENAI

    msg = (
        f"El proveedor configurado ({raw_value!r}) no es válido. "
        "Los únicos valores admitidos son 'fake' y 'openai'."
    )
    raise LLMProviderConfigurationError(msg)


def resolve_openai_api_key(secret_store: SecretStore) -> str | None:
    """Resolve the OpenAI API key: the secret store first, then ``OPENAI_API_KEY``.

    The secret store is the normal production path (a key saved from the
    "Configuración" tab). The environment variable is kept only as an
    explicit development convenience for when nothing has been saved there.
    """
    stored = secret_store.get_secret(OPENAI_API_KEY_SECRET_NAME)
    if stored:
        return stored
    return os.environ.get("OPENAI_API_KEY") or None


def _positive_int(raw_value: Any, setting_name: str) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        msg = f"{setting_name} debe ser un número entero de tokens."
        raise LLMProviderConfigurationError(msg) from exc
    if value <= 0:
        msg = f"{setting_name} debe ser un número positivo de tokens."
        raise LLMProviderConfigurationError(msg)
    return value


def _positive_float(raw_value: Any, setting_name: str) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        msg = f"{setting_name} debe ser un número."
        raise LLMProviderConfigurationError(msg) from exc
    if value <= 0:
        msg = f"{setting_name} debe ser un número positivo."
        raise LLMProviderConfigurationError(msg)
    return value


def resolve_openai_provider_settings(settings: dict[str, Any]) -> OpenAIProviderSettings:
    """Read the non-sensitive OpenAI settings (model, output limit, budget)."""
    model = str(settings.get("openai_model") or "").strip() or _DEFAULT_MODEL

    raw_max_output_tokens = settings.get("openai_max_output_tokens")
    max_output_tokens = (
        _positive_int(raw_max_output_tokens, "El límite de tokens de salida")
        if raw_max_output_tokens is not None
        else _DEFAULT_MAX_OUTPUT_TOKENS
    )

    raw_monthly_budget = settings.get("openai_monthly_budget_usd")
    monthly_budget_usd = (
        _positive_float(raw_monthly_budget, "El presupuesto mensual")
        if raw_monthly_budget is not None
        else _DEFAULT_MONTHLY_BUDGET_USD
    )

    return OpenAIProviderSettings(
        model=model, max_output_tokens=max_output_tokens, monthly_budget_usd=monthly_budget_usd
    )
