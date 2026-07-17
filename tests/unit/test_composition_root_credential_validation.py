"""Composition tests for credential validation wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.validate_and_save_api_key import ValidateAndSaveApiKeyUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.config.secrets_config import OPENAI_API_KEY_SECRET_NAME
from sirius.config.settings import load_settings, save_settings


@pytest.fixture(autouse=True)
def isolated_local_appdata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path / "appdata"))


def test_dependencies_expose_validate_before_save_use_case(tmp_path: Path) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db",
        tmp_path / "backups",
        secret_store=FakeSecretStore(),
    )

    assert isinstance(
        dependencies.validate_and_save_api_key_use_case,
        ValidateAndSaveApiKeyUseCase,
    )


def test_activate_configured_llm_provider_selects_openai_and_swaps_the_provider(
    tmp_path: Path,
) -> None:
    """B2a: once a key is saved, onboarding calls this to activate the real
    provider in the same run — no restart, no rebuild of persistence."""
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, "sk-fake-not-a-real-key")
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db",
        tmp_path / "backups",
        secret_store=secret_store,
    )

    dependencies.activate_configured_llm_provider()

    assert load_settings()["llm_provider"] == "openai"
    assert isinstance(
        dependencies.send_message_use_case._llm_provider,
        OpenAIResponsesProvider,
    )


def test_activate_configured_llm_provider_preserves_other_settings(tmp_path: Path) -> None:
    save_settings({"user_name": "Ada"})
    secret_store = FakeSecretStore()
    secret_store.set_secret(OPENAI_API_KEY_SECRET_NAME, "sk-fake-not-a-real-key")
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db",
        tmp_path / "backups",
        secret_store=secret_store,
    )

    dependencies.activate_configured_llm_provider()

    settings = load_settings()
    assert settings["user_name"] == "Ada"
    assert settings["llm_provider"] == "openai"
