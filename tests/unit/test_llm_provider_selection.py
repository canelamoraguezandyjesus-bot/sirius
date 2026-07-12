"""Provider selection in the composition root: fake by default, openai opt-in.

No real OpenAI client is ever constructed with a real key here; when a key is
needed to prove the "openai" branch builds an ``OpenAIResponsesProvider``,
a syntactically-shaped but fake value is used and no network call is made
(building the client does not call the network).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import openai
import pytest

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
from sirius.composition_root import _build_llm_provider
from sirius.config.llm_provider_settings import (
    LLMProviderConfigurationError,
    LLMProviderKind,
    resolve_provider_kind,
)


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIRIUS_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SIRIUS_OPENAI_MODEL", raising=False)
    monkeypatch.delenv("SIRIUS_OPENAI_MAX_OUTPUT_TOKENS", raising=False)


def test_default_provider_is_fake_when_unset(tmp_path: Path) -> None:
    assert resolve_provider_kind() is LLMProviderKind.FAKE
    assert isinstance(_build_llm_provider(tmp_path / "sirius.db"), FakeLLMProvider)


def test_unrecognized_provider_value_raises_a_clear_configuration_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SIRIUS_LLM_PROVIDER", "not-a-real-provider")

    with pytest.raises(LLMProviderConfigurationError, match="not-a-real-provider"):
        resolve_provider_kind()
    with pytest.raises(LLMProviderConfigurationError, match="not-a-real-provider"):
        _build_llm_provider(tmp_path / "sirius.db")


def test_openai_without_a_key_raises_a_clear_configuration_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SIRIUS_LLM_PROVIDER", "openai")

    with pytest.raises(LLMProviderConfigurationError, match="OPENAI_API_KEY"):
        _build_llm_provider(tmp_path / "sirius.db")


def test_openai_with_an_invalid_max_output_tokens_raises_a_clear_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SIRIUS_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-a-real-key")
    monkeypatch.setenv("SIRIUS_OPENAI_MAX_OUTPUT_TOKENS", "not-a-number")

    with pytest.raises(LLMProviderConfigurationError):
        _build_llm_provider(tmp_path / "sirius.db")


def test_openai_with_a_key_builds_the_real_adapter_without_any_network_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SIRIUS_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-a-real-key")
    monkeypatch.setenv("SIRIUS_OPENAI_MODEL", "gpt-5.6-terra")

    provider = _build_llm_provider(tmp_path / "sirius.db")

    assert isinstance(provider, OpenAIResponsesProvider)


def test_openai_client_is_built_with_max_retries_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The SDK's own retry loop must be disabled: the adapter has its own
    tested retry policy, and letting both retry independently would multiply
    attempts unpredictably (canonical S9 "Reintentos").
    """
    monkeypatch.setenv("SIRIUS_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-a-real-key")
    captured_kwargs: dict[str, Any] = {}
    original_init = openai.OpenAI.__init__

    def _capturing_init(self: openai.OpenAI, **kwargs: Any) -> None:
        captured_kwargs.update(kwargs)
        original_init(self, **kwargs)

    monkeypatch.setattr(openai.OpenAI, "__init__", _capturing_init)

    _build_llm_provider(tmp_path / "sirius.db")

    assert captured_kwargs["max_retries"] == 0
