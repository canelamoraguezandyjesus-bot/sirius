"""Unit tests for B7a's LLMErrorKind -> mensaje accionable mapping (RF-028).

Pure/deterministic: no Qt, no network, no real keys.
"""

from __future__ import annotations

import pytest

from sirius.ports.llm import LLMErrorKind
from sirius.presentation.error_messages import describe_error, failed_send_message

_GENERIC_MESSAGE = describe_error(None)

_NON_GENERIC_KINDS = [kind for kind in LLMErrorKind if kind is not LLMErrorKind.UNKNOWN]


@pytest.mark.parametrize("kind", _NON_GENERIC_KINDS)
def test_each_known_error_kind_has_a_distinct_actionable_message(kind: LLMErrorKind) -> None:
    message = describe_error(kind)
    assert message
    assert message != _GENERIC_MESSAGE


def test_all_error_kinds_are_covered_exhaustively() -> None:
    """Guards against a future ``LLMErrorKind`` member silently falling back
    to the generic message: ``describe_error`` raises for anything unmapped,
    so adding a member without a message here fails this test immediately."""
    for kind in LLMErrorKind:
        describe_error(kind)


def test_unknown_kind_uses_the_generic_message() -> None:
    assert describe_error(LLMErrorKind.UNKNOWN) == _GENERIC_MESSAGE


def test_none_kind_uses_the_generic_message() -> None:
    assert describe_error(None) == _GENERIC_MESSAGE


@pytest.mark.parametrize("kind", list(LLMErrorKind))
def test_failed_send_message_appends_the_support_reference(kind: LLMErrorKind) -> None:
    text = failed_send_message(kind, "op-123")
    assert text == f"{describe_error(kind)} (ref: op-123)"


def test_failed_send_message_never_leaks_a_raw_provider_message() -> None:
    """RNF-018: only ``kind`` and the reference feed the label, never the
    provider's raw ``LLMError.message`` (which could contain request/response
    details). Simulate a secret-looking provider message to prove it never
    appears in the output."""
    secret_looking_message = "Bearer sk-live-super-secret-token-should-never-appear"
    text = failed_send_message(LLMErrorKind.AUTHENTICATION, "op-456")
    assert secret_looking_message not in text
