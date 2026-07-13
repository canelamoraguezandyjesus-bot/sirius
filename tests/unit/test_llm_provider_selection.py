"""Provider selection in the composition root: fake by default, openai opt-in.

No real OpenAI client is ever constructed with a real key here, and no test
ever touches the real Windows Credential Manager: a ``FakeSecretStore`` is
injected everywhere a secret store is needed. When a key is needed to prove
the "openai" branch builds an ``OpenAIResponsesProvider``, a syntactically
shaped but fake value is used and no network call is made (building the
client does not call the network).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import openai
import pytest

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
from sirius.adapters.llm.unconfigured import UnconfiguredLLMProvider
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import _build_llm_provider
from sirius.config.llm_provider_settings import (
    LLMProviderConfigurationError,
    LLMProviderKind,
    resolve_openai_api_key,
    resolve_provider_kind,
)
from sirius.ports.llm import LLMErrorKind, LLMRequest


def _drain_configuration_error(provider: UnconfiguredLLMProvider) -> str:
    request = LLMRequest(operation_id="op-1", instructions="", input_text="")
    events = list(provider.stream_response(request))
    assert len(events) == 1
    event = events[0]
    assert event.kind is LLMErrorKind.CONFIGURATION  # type: ignore[union-attr]
    return event.message  # type: ignore[union-attr]


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _patch_settings(monkeypatch: pytest.MonkeyPatch, settings: dict[str, Any]) -> None:
    monkeypatch.setattr("sirius.composition_root.load_settings", lambda: settings)


def test_default_provider_is_fake_when_unset(tmp_path: Path) -> None:
    assert resolve_provider_kind({}) is LLMProviderKind.FAKE
    provider = _build_llm_provider(tmp_path / "sirius.db", FakeSecretStore())
    assert isinstance(provider, FakeLLMProvider)


def test_unrecognized_provider_value_raises_a_clear_configuration_error() -> None:
    with pytest.raises(LLMProviderConfigurationError, match="not-a-real-provider"):
        resolve_provider_kind({"llm_provider": "not-a-real-provider"})


def test_build_llm_provider_never_raises_for_an_unrecognized_provider_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Sirius must always start, even with a hand-edited invalid setting."""
    _patch_settings(monkeypatch, {"llm_provider": "not-a-real-provider"})

    provider = _build_llm_provider(tmp_path / "sirius.db", FakeSecretStore())

    assert isinstance(provider, UnconfiguredLLMProvider)
    message = _drain_configuration_error(provider)
    assert "not-a-real-provider" in message


def test_openai_without_a_key_never_raises_and_reports_at_send_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_settings(monkeypatch, {"llm_provider": "openai"})

    provider = _build_llm_provider(tmp_path / "sirius.db", FakeSecretStore())

    assert isinstance(provider, UnconfiguredLLMProvider)
    message = _drain_configuration_error(provider)
    assert "Configuración" in message or "clave" in message


def test_openai_with_an_invalid_max_output_tokens_degrades_gracefully(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_settings(
        monkeypatch,
        {"llm_provider": "openai", "openai_max_output_tokens": "not-a-number"},
    )
    secret_store = FakeSecretStore()
    secret_store.set_secret("openai_api_key", "sk-fake-not-a-real-key")

    provider = _build_llm_provider(tmp_path / "sirius.db", secret_store)

    assert isinstance(provider, UnconfiguredLLMProvider)


def test_openai_with_a_key_in_the_secret_store_builds_the_real_adapter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_settings(monkeypatch, {"llm_provider": "openai", "openai_model": "gpt-5.6-terra"})
    secret_store = FakeSecretStore()
    secret_store.set_secret("openai_api_key", "sk-fake-not-a-real-key")

    provider = _build_llm_provider(tmp_path / "sirius.db", secret_store)

    assert isinstance(provider, OpenAIResponsesProvider)


def test_openai_client_is_built_with_max_retries_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The SDK's own retry loop must be disabled: the adapter has its own
    tested retry policy, and letting both retry independently would multiply
    attempts unpredictably (canonical S9 "Reintentos").
    """
    _patch_settings(monkeypatch, {"llm_provider": "openai"})
    secret_store = FakeSecretStore()
    secret_store.set_secret("openai_api_key", "sk-fake-not-a-real-key")
    captured_kwargs: dict[str, Any] = {}
    original_init = openai.OpenAI.__init__

    def _capturing_init(self: openai.OpenAI, **kwargs: Any) -> None:
        captured_kwargs.update(kwargs)
        original_init(self, **kwargs)

    monkeypatch.setattr(openai.OpenAI, "__init__", _capturing_init)

    _build_llm_provider(tmp_path / "sirius.db", secret_store)

    assert captured_kwargs["max_retries"] == 0


def test_resolve_openai_api_key_prefers_the_secret_store_over_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    secret_store = FakeSecretStore()
    secret_store.set_secret("openai_api_key", "sk-from-store")

    assert resolve_openai_api_key(secret_store) == "sk-from-store"


def test_resolve_openai_api_key_falls_back_to_the_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SIRIUS-ARQ-0.1 S11.1: the env var is an explicit, dev-only mechanism
    used only when the secret store has nothing saved — never the normal
    user flow."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")

    assert resolve_openai_api_key(FakeSecretStore()) == "sk-from-env"


def test_resolve_openai_api_key_is_none_when_nothing_is_configured() -> None:
    assert resolve_openai_api_key(FakeSecretStore()) is None
