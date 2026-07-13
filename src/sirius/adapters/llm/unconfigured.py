"""Stand-in ``LLMProvider`` used when "openai" is selected but not usable yet.

Lets Sirius start normally even with a bad or missing configuration
(RF/V7A: "no debe cerrarse inesperadamente"): the composition root builds this
instead of ``OpenAIResponsesProvider`` whenever provider configuration fails,
and the safe, already-vetted error message only surfaces when the user
actually tries to send a message — never at startup.
"""

from __future__ import annotations

from collections.abc import Iterable

from sirius.ports.llm import LLMError, LLMErrorKind, LLMRequest, LLMStreamEvent


class UnconfiguredLLMProvider:
    """Always reports a configuration error; makes no network call, ever."""

    def __init__(self, message: str) -> None:
        self._message = message

    def health_check(self) -> bool:
        return False

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMError(kind=LLMErrorKind.CONFIGURATION, message=self._message)

    def cancel(self, operation_id: str) -> None:
        del operation_id
