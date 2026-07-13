"""Unit tests for ``ApiKeySettingsUseCase``: the only secret-related API
``presentation`` is allowed to touch. Its surface must never offer a way to
read the key's value back.
"""

from __future__ import annotations

import inspect
import typing

import pytest

from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.api_key_settings import ApiKeySettingsError, ApiKeySettingsUseCase
from sirius.config.secrets_config import OPENAI_API_KEY_SECRET_NAME
from sirius.ports.secrets import SecretStoreError


class _RaisingSecretStore:
    """Test double: every operation raises, to exercise error translation."""

    def get_secret(self, key: str) -> str | None:
        raise SecretStoreError("boom")

    def set_secret(self, key: str, value: str) -> None:
        raise SecretStoreError("boom")

    def delete_secret(self, key: str) -> None:
        raise SecretStoreError("boom")

    def is_secure_backend(self) -> bool:
        return True


def test_has_key_is_false_when_nothing_is_saved() -> None:
    use_case = ApiKeySettingsUseCase(FakeSecretStore())

    assert use_case.has_key() is False


def test_has_key_is_true_after_saving() -> None:
    secret_store = FakeSecretStore()
    use_case = ApiKeySettingsUseCase(secret_store)

    use_case.save_key("sk-fake-value")

    assert use_case.has_key() is True
    # Confirmed independently, through the fake store itself, that saving
    # really persisted the value the use case is supposed to write.
    assert secret_store.get_secret(OPENAI_API_KEY_SECRET_NAME) == "sk-fake-value"


def test_has_key_translates_secret_store_errors() -> None:
    use_case = ApiKeySettingsUseCase(_RaisingSecretStore())

    with pytest.raises(ApiKeySettingsError):
        use_case.has_key()


def test_delete_key_removes_it() -> None:
    secret_store = FakeSecretStore()
    use_case = ApiKeySettingsUseCase(secret_store)
    use_case.save_key("sk-fake-value")

    use_case.delete_key()

    assert use_case.has_key() is False


def test_save_key_translates_secret_store_errors() -> None:
    use_case = ApiKeySettingsUseCase(_RaisingSecretStore())

    with pytest.raises(ApiKeySettingsError):
        use_case.save_key("sk-fake-value")


def test_delete_key_translates_secret_store_errors() -> None:
    use_case = ApiKeySettingsUseCase(_RaisingSecretStore())

    with pytest.raises(ApiKeySettingsError):
        use_case.delete_key()


def test_the_public_api_never_offers_a_way_to_read_the_key_back() -> None:
    """Structural guardrail: only has_key/save_key/delete_key are public,
    and has_key returns a bool — nothing here can ever surface the value."""
    public_methods = {
        name
        for name, _ in inspect.getmembers(ApiKeySettingsUseCase, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    assert public_methods == {"has_key", "save_key", "delete_key"}

    # ``from __future__ import annotations`` makes raw signatures show the
    # string "bool"; resolve it to the real type to check it properly.
    resolved_hints = typing.get_type_hints(ApiKeySettingsUseCase.has_key)
    assert resolved_hints["return"] is bool
