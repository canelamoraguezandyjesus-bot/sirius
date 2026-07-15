"""Unit tests for validate-before-save credential handling."""

from __future__ import annotations

import pytest

from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.validate_and_save_api_key import (
    ValidateAndSaveApiKeyError,
    ValidateAndSaveApiKeyUseCase,
)
from sirius.config.secrets_config import OPENAI_API_KEY_SECRET_NAME
from sirius.ports.credential_validation import (
    CredentialValidationError,
    CredentialValidationKind,
)
from sirius.ports.secrets import SecretStoreError


class _RecordingValidator:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def validate(self, credential: str, model: str) -> None:
        self.calls.append((credential, model))
        if self.error is not None:
            raise self.error


class _FailingSecretStore(FakeSecretStore):
    def set_secret(self, key: str, value: str) -> None:
        raise SecretStoreError("internal detail")


def test_validates_before_saving() -> None:
    validator = _RecordingValidator()
    secret_store = FakeSecretStore()
    use_case = ValidateAndSaveApiKeyUseCase(validator, secret_store)

    use_case.validate_and_save("sk-candidate", "gpt-model")

    assert validator.calls == [("sk-candidate", "gpt-model")]
    assert secret_store.get_secret(OPENAI_API_KEY_SECRET_NAME) == "sk-candidate"


def test_failed_validation_never_writes_the_candidate_key() -> None:
    error = CredentialValidationError(CredentialValidationKind.AUTHENTICATION)
    validator = _RecordingValidator(error)
    secret_store = FakeSecretStore()
    use_case = ValidateAndSaveApiKeyUseCase(validator, secret_store)

    with pytest.raises(CredentialValidationError) as raised:
        use_case.validate_and_save("sk-invalid", "gpt-model")

    assert raised.value.kind is CredentialValidationKind.AUTHENTICATION
    assert secret_store.get_secret(OPENAI_API_KEY_SECRET_NAME) is None


def test_secure_store_failure_is_translated_without_exposing_the_key() -> None:
    validator = _RecordingValidator()
    use_case = ValidateAndSaveApiKeyUseCase(validator, _FailingSecretStore())

    with pytest.raises(ValidateAndSaveApiKeyError) as raised:
        use_case.validate_and_save("sk-secret-candidate", "gpt-model")

    assert "sk-secret-candidate" not in str(raised.value)
    assert "internal detail" not in str(raised.value)
