"""Unit tests for ``KeyringSecretStore``.

Every ``keyring`` call is monkeypatched: no test in this file ever reads,
writes, or deletes anything in the real Windows Credential Manager.
"""

from __future__ import annotations

from typing import Any

import keyring
import keyring.errors
import pytest
from keyring.backends.fail import Keyring as FailKeyring

from sirius.adapters.secrets.keyring_store import KeyringSecretStore
from sirius.config.secrets_config import SIRIUS_KEYRING_SERVICE_NAME
from sirius.ports.secrets import SecretStoreError


class _FakeSecureBackend:
    """Stands in for a real, working OS credential backend."""


def _use_secure_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(keyring, "get_keyring", lambda: _FakeSecureBackend())


def _use_fail_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(keyring, "get_keyring", FailKeyring)


def test_is_secure_backend_true_for_a_real_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_secure_backend(monkeypatch)

    assert KeyringSecretStore().is_secure_backend() is True


def test_is_secure_backend_false_when_keyring_has_no_usable_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_fail_backend(monkeypatch)

    assert KeyringSecretStore().is_secure_backend() is False


def test_get_secret_returns_the_stored_value(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def _get_password(service: str, key: str) -> str | None:
        captured["service"], captured["key"] = service, key
        return "sk-fake"

    monkeypatch.setattr(keyring, "get_password", _get_password)

    result = KeyringSecretStore().get_secret("openai_api_key")

    assert result == "sk-fake"
    assert captured == {"service": SIRIUS_KEYRING_SERVICE_NAME, "key": "openai_api_key"}


def test_get_secret_returns_none_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(keyring, "get_password", lambda service, key: None)

    assert KeyringSecretStore().get_secret("openai_api_key") is None


def test_get_secret_translates_keyring_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(service: str, key: str) -> str | None:
        raise keyring.errors.KeyringLocked("locked")

    monkeypatch.setattr(keyring, "get_password", _raise)

    with pytest.raises(SecretStoreError) as excinfo:
        KeyringSecretStore().get_secret("openai_api_key")
    assert "openai_api_key" not in str(excinfo.value)


def test_set_secret_writes_via_keyring_when_backend_is_secure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_secure_backend(monkeypatch)
    captured: dict[str, Any] = {}

    def _set_password(service: str, key: str, value: str) -> None:
        captured.update(service=service, key=key, value=value)

    monkeypatch.setattr(keyring, "set_password", _set_password)

    KeyringSecretStore().set_secret("openai_api_key", "sk-fake-value")

    assert captured == {
        "service": SIRIUS_KEYRING_SERVICE_NAME,
        "key": "openai_api_key",
        "value": "sk-fake-value",
    }


def test_set_secret_refuses_to_write_when_the_backend_is_insecure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SIRIUS-ARQ-0.1 S11.1: never fall back to plaintext when no secure
    backend is available — refuse the write instead."""
    _use_fail_backend(monkeypatch)

    def _set_password(service: str, key: str, value: str) -> None:
        raise AssertionError("must never attempt to write with an insecure backend")

    monkeypatch.setattr(keyring, "set_password", _set_password)

    with pytest.raises(SecretStoreError):
        KeyringSecretStore().set_secret("openai_api_key", "sk-fake-value")


def test_set_secret_translates_keyring_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_secure_backend(monkeypatch)

    def _raise(service: str, key: str, value: str) -> None:
        raise keyring.errors.PasswordSetError("boom")

    monkeypatch.setattr(keyring, "set_password", _raise)

    with pytest.raises(SecretStoreError) as excinfo:
        KeyringSecretStore().set_secret("openai_api_key", "sk-fake-value")
    assert "sk-fake-value" not in str(excinfo.value)


def test_delete_secret_calls_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def _delete_password(service: str, key: str) -> None:
        captured.update(service=service, key=key)

    monkeypatch.setattr(keyring, "delete_password", _delete_password)

    KeyringSecretStore().delete_secret("openai_api_key")

    assert captured == {"service": SIRIUS_KEYRING_SERVICE_NAME, "key": "openai_api_key"}


def test_delete_secret_is_a_no_op_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(service: str, key: str) -> None:
        raise keyring.errors.PasswordDeleteError("not found")

    monkeypatch.setattr(keyring, "delete_password", _raise)

    KeyringSecretStore().delete_secret("openai_api_key")  # must not raise


def test_delete_secret_translates_other_keyring_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(service: str, key: str) -> None:
        raise keyring.errors.KeyringLocked("locked")

    monkeypatch.setattr(keyring, "delete_password", _raise)

    with pytest.raises(SecretStoreError):
        KeyringSecretStore().delete_secret("openai_api_key")
