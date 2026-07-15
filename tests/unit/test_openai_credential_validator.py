"""Unit tests for the OpenAI credential validation adapter.

All clients are local fakes. No test performs network access.
"""

from __future__ import annotations

import pytest

from sirius.adapters.llm.openai_credential_validator import OpenAICredentialValidator
from sirius.ports.credential_validation import (
    CredentialValidationError,
    CredentialValidationKind,
)


class _FakeModels:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.retrieved: list[str] = []

    def retrieve(self, model: str) -> object:
        self.retrieved.append(model)
        if self.error is not None:
            raise self.error
        return object()


class _FakeClient:
    def __init__(self, models: _FakeModels) -> None:
        self.models = models


def test_validation_uses_the_candidate_key_and_configured_model() -> None:
    models = _FakeModels()
    received_credentials: list[str] = []

    def factory(credential: str) -> _FakeClient:
        received_credentials.append(credential)
        return _FakeClient(models)

    validator = OpenAICredentialValidator(factory)
    validator.validate("sk-candidate", "gpt-model")

    assert received_credentials == ["sk-candidate"]
    assert models.retrieved == ["gpt-model"]


@pytest.mark.parametrize(
    ("credential", "model"),
    [("", "gpt-model"), ("   ", "gpt-model"), ("sk-candidate", "")],
)
def test_blank_configuration_is_rejected_before_building_a_client(
    credential: str,
    model: str,
) -> None:
    factory_calls: list[str] = []

    def factory(value: str) -> _FakeClient:
        factory_calls.append(value)
        return _FakeClient(_FakeModels())

    validator = OpenAICredentialValidator(factory)

    with pytest.raises(CredentialValidationError) as raised:
        validator.validate(credential, model)

    assert raised.value.kind is CredentialValidationKind.CONFIGURATION
    assert factory_calls == []


def test_unexpected_provider_failure_is_safe_and_typed() -> None:
    secret_marker = "sk-must-not-leak"
    validator = OpenAICredentialValidator(
        lambda credential: _FakeClient(_FakeModels(RuntimeError(secret_marker)))
    )

    with pytest.raises(CredentialValidationError) as raised:
        validator.validate("sk-candidate", "gpt-model")

    assert raised.value.kind is CredentialValidationKind.UNKNOWN
    assert secret_marker not in str(raised.value)
