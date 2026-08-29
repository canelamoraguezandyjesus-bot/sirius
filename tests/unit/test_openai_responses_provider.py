"""Unit tests for OpenAIResponsesProvider using a fully simulated client.

No real network call is ever made: ``_FakeOpenAIClient`` stands in for
``openai.OpenAI`` and captures exactly what the adapter sends.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from sirius.adapters.llm.budget import BudgetPolicy, BudgetTracker
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider, _build_error
from sirius.ports.llm import (
    MEMORY_SUGGESTION_DELIMITER,
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMTextDelta,
)

_DUMMY_REQUEST = httpx.Request("POST", "https://api.openai.com/v1/responses")


def _delta_event(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="response.output_text.delta", delta=text)


def _completed_event(
    output_text: str, input_tokens: int = 10, output_tokens: int = 5
) -> SimpleNamespace:
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    response = SimpleNamespace(usage=usage, output_text=output_text)
    return SimpleNamespace(type="response.completed", response=response)


def _failed_event() -> SimpleNamespace:
    response = SimpleNamespace(usage=None, output_text="")
    return SimpleNamespace(type="response.failed", response=response)


class _FakeStream:
    """A finite, closeable iterable standing in for ``openai``'s ``Stream``."""

    def __init__(self, events: list[object]) -> None:
        self._events = events
        self.closed = False

    def __iter__(self) -> Iterator[object]:
        return iter(self._events)

    def close(self) -> None:
        self.closed = True


class _RaisingAfterNStream:
    """Yields a few events, then raises on the next pull. Also closeable."""

    def __init__(self, events_before_raise: list[object], exc: Exception) -> None:
        self._events = list(events_before_raise)
        self._exc = exc
        self.closed = False

    def __iter__(self) -> Iterator[object]:
        return self

    def __next__(self) -> object:
        if self._events:
            return self._events.pop(0)
        raise self._exc

    def close(self) -> None:
        self.closed = True


class _FakeResponses:
    def __init__(self, create_fn: Callable[..., object]) -> None:
        self._create_fn = create_fn
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        return self._create_fn(**kwargs)


class _FakeOpenAIClient:
    def __init__(self, create_fn: Callable[..., object]) -> None:
        self.responses = _FakeResponses(create_fn)


def _request(operation_id: str = "op-1") -> LLMRequest:
    return LLMRequest(operation_id=operation_id, instructions="sé breve", input_text="hola")


def _build_provider(
    create_fn: Callable[..., object],
    *,
    model: str = "gpt-5.6-terra",
    max_output_tokens: int = 111,
    budget_tracker: BudgetTracker | None = None,
) -> tuple[OpenAIResponsesProvider, _FakeOpenAIClient]:
    client = _FakeOpenAIClient(create_fn)
    provider = OpenAIResponsesProvider(
        client=client,  # type: ignore[arg-type]
        model=model,
        max_output_tokens=max_output_tokens,
        budget_tracker=budget_tracker,
        sleep_fn=lambda _seconds: None,
    )
    return provider, client


def test_request_is_built_with_the_expected_parameters() -> None:
    provider, client = _build_provider(
        lambda **kwargs: _FakeStream([_completed_event("ok")]),
        model="gpt-5.6-terra",
        max_output_tokens=222,
    )

    list(provider.stream_response(_request()))

    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "gpt-5.6-terra"
    assert call["instructions"] == "sé breve"
    assert call["input"] == "hola"
    assert call["max_output_tokens"] == 222
    assert call["stream"] is True


def test_store_is_always_false() -> None:
    provider, client = _build_provider(lambda **kwargs: _FakeStream([_completed_event("ok")]))

    list(provider.stream_response(_request()))

    assert client.responses.calls[0]["store"] is False


def test_no_tools_web_search_or_code_execution_are_enabled() -> None:
    provider, client = _build_provider(lambda **kwargs: _FakeStream([_completed_event("ok")]))

    list(provider.stream_response(_request()))

    assert "tools" not in client.responses.calls[0]


def test_model_and_max_output_tokens_are_configurable() -> None:
    provider, client = _build_provider(
        lambda **kwargs: _FakeStream([_completed_event("ok")]),
        model="gpt-5.6-luna",
        max_output_tokens=999,
    )

    list(provider.stream_response(_request()))

    assert client.responses.calls[0]["model"] == "gpt-5.6-luna"
    assert client.responses.calls[0]["max_output_tokens"] == 999


def test_deltas_are_yielded_in_order_before_completion() -> None:
    provider, _client = _build_provider(
        lambda **kwargs: _FakeStream(
            [_delta_event("a"), _delta_event("b"), _delta_event("c"), _completed_event("abc")]
        )
    )

    events = list(provider.stream_response(_request()))

    deltas = [e.text for e in events if isinstance(e, LLMTextDelta)]
    assert deltas == ["a", "b", "c"]
    assert isinstance(events[-1], LLMCompleted)


def test_completed_event_produces_final_text_and_records_usage() -> None:
    budget = BudgetTracker(BudgetPolicy())
    completed_event = _completed_event("respuesta", input_tokens=100, output_tokens=50)
    provider, _client = _build_provider(
        lambda **kwargs: _FakeStream([_delta_event("respuesta"), completed_event]),
        budget_tracker=budget,
    )

    events = list(provider.stream_response(_request()))

    completed = events[-1]
    assert isinstance(completed, LLMCompleted)
    assert completed.text == "respuesta"
    assert completed.input_tokens == 100
    assert completed.output_tokens == 50
    assert budget.spent_usd > 0


class _CancelAfterNPullsStream:
    """Yields ``events`` normally; right before the ``(cancel_after + 1)``-th
    pull, invokes ``on_cancel()``. Lets a test put the provider's cancel flag
    up exactly between two already-consumed raw events and the next one —
    i.e. after a full delimiter has already been fed to the splitter, but
    before the terminal event that would otherwise complete the turn."""

    def __init__(
        self, events: list[object], cancel_after: int, on_cancel: Callable[[], None]
    ) -> None:
        self._events = list(events)
        self._cancel_after = cancel_after
        self._on_cancel = on_cancel
        self._pulled = 0
        self.closed = False

    def __iter__(self) -> Iterator[object]:
        return self

    def __next__(self) -> object:
        if self._pulled == self._cancel_after:
            self._on_cancel()
        if not self._events:
            raise StopIteration
        self._pulled += 1
        return self._events.pop(0)

    def close(self) -> None:
        self.closed = True


def test_completed_event_separates_the_memory_suggestion_from_the_clean_text() -> None:
    """SIRIUS-ARQ-0.2 §3.2/§3.6 (M6): the delimiter and the raw proposal after
    it never reach ``LLMTextDelta`` or ``LLMCompleted.text``, and the
    proposal itself lands, clean, in ``LLMCompleted.memory_suggestion``."""
    visible = "Respuesta visible. "
    suggestion = "recordar esto"
    raw = f"{visible}{MEMORY_SUGGESTION_DELIMITER}{suggestion}"
    provider, _client = _build_provider(
        lambda **kwargs: _FakeStream([_delta_event(raw), _completed_event(raw)])
    )

    events = list(provider.stream_response(_request()))

    deltas = [e.text for e in events if isinstance(e, LLMTextDelta)]
    assert deltas == [visible]
    completed = events[-1]
    assert isinstance(completed, LLMCompleted)
    assert completed.text == visible
    assert completed.memory_suggestion == suggestion
    assert MEMORY_SUGGESTION_DELIMITER not in completed.text


def test_completed_event_without_a_delimiter_has_no_memory_suggestion() -> None:
    provider, _client = _build_provider(
        lambda **kwargs: _FakeStream([_delta_event("solo texto"), _completed_event("solo texto")])
    )

    events = list(provider.stream_response(_request()))

    completed = events[-1]
    assert isinstance(completed, LLMCompleted)
    assert completed.memory_suggestion is None


def test_memory_suggestion_delimiter_split_across_two_deltas_never_leaks() -> None:
    """The adapter's own proof (§8-M6) that the split-safety of §3.2 does not
    depend on the delimiter arriving whole in a single raw fragment: it is
    split here across the boundary between two consecutive deltas, and still
    never reaches ``LLMTextDelta`` or ``LLMCompleted.text``."""
    visible = "Respuesta. "
    suggestion = "recordar esto"
    split_point = len(MEMORY_SUGGESTION_DELIMITER) - 5
    first_chunk = visible + MEMORY_SUGGESTION_DELIMITER[:split_point]
    second_chunk = MEMORY_SUGGESTION_DELIMITER[split_point:] + suggestion
    raw = first_chunk + second_chunk
    provider, _client = _build_provider(
        lambda **kwargs: _FakeStream(
            [_delta_event(first_chunk), _delta_event(second_chunk), _completed_event(raw)]
        )
    )

    events = list(provider.stream_response(_request()))

    deltas = [e.text for e in events if isinstance(e, LLMTextDelta)]
    assert deltas == [visible]
    for delta_text in deltas:
        assert MEMORY_SUGGESTION_DELIMITER not in delta_text
    completed = events[-1]
    assert isinstance(completed, LLMCompleted)
    assert completed.text == visible
    assert MEMORY_SUGGESTION_DELIMITER not in completed.text
    assert completed.memory_suggestion == suggestion


def test_cancelled_after_the_full_delimiter_already_streamed_has_no_delimiter_in_partial_text() -> (
    None
):
    """§3.2: even once the delimiter and the raw proposal already streamed in
    full, a cancellation arriving right after must never persist either in
    ``LLMCancelled.partial_text``."""
    visible = "Respuesta. "
    request = _request(operation_id="op-cancel-after-delimiter")
    provider_box: list[OpenAIResponsesProvider] = []

    def _create(**kwargs: Any) -> object:
        return _CancelAfterNPullsStream(
            [
                _delta_event(visible),
                _delta_event(f"{MEMORY_SUGGESTION_DELIMITER}secreto"),
                _completed_event(f"{visible}{MEMORY_SUGGESTION_DELIMITER}secreto"),
            ],
            cancel_after=2,
            on_cancel=lambda: provider_box[0].cancel(request.operation_id),
        )

    provider, _client = _build_provider(_create)
    provider_box.append(provider)

    events = list(provider.stream_response(request))

    assert [e.text for e in events if isinstance(e, LLMTextDelta)] == [visible]
    last_event = events[-1]
    assert isinstance(last_event, LLMCancelled)
    assert last_event.partial_text == visible
    assert MEMORY_SUGGESTION_DELIMITER not in last_event.partial_text
    assert "secreto" not in last_event.partial_text


def test_response_failed_after_the_full_delimiter_already_streamed_has_no_delimiter() -> None:
    visible = "Respuesta. "
    provider, _client = _build_provider(
        lambda **kwargs: _FakeStream(
            [
                _delta_event(visible),
                _delta_event(f"{MEMORY_SUGGESTION_DELIMITER}secreto"),
                _failed_event(),
            ]
        )
    )

    events = list(provider.stream_response(_request()))

    assert [e.text for e in events if isinstance(e, LLMTextDelta)] == [visible]
    last_event = events[-1]
    assert isinstance(last_event, LLMError)
    assert last_event.partial_text == visible
    assert MEMORY_SUGGESTION_DELIMITER not in last_event.partial_text
    assert "secreto" not in last_event.partial_text


def test_failure_before_first_delta_is_classified_and_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    secret_message = "sk-should-never-leak-1234567890"

    def _raise(**kwargs: Any) -> object:
        response = httpx.Response(
            401, request=_DUMMY_REQUEST, json={"error": {"message": secret_message}}
        )
        raise openai.AuthenticationError(secret_message, response=response, body=None)

    provider, client = _build_provider(_raise)

    events = list(provider.stream_response(_request()))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, LLMError)
    assert event.kind is LLMErrorKind.AUTHENTICATION
    assert secret_message not in event.message
    assert len(client.responses.calls) == 1  # authentication errors are never retried


def test_failure_after_some_deltas_is_reported_without_a_completed_event() -> None:
    request_obj = httpx.Request("POST", "https://api.openai.com/v1/responses")

    def _create(**kwargs: Any) -> object:
        return _RaisingAfterNStream(
            [_delta_event("empez"), _delta_event("ando")],
            openai.APIConnectionError(request=request_obj),
        )

    provider, _client = _build_provider(_create)

    events = list(provider.stream_response(_request()))

    assert [e.text for e in events if isinstance(e, LLMTextDelta)] == ["empez", "ando"]
    last_event = events[-1]
    assert isinstance(last_event, LLMError)
    assert last_event.kind is LLMErrorKind.CONNECTION
    assert last_event.partial_text == "empezando"
    assert not any(isinstance(e, LLMCompleted) for e in events)


def test_response_failed_event_is_reported_as_invalid_response() -> None:
    provider, _client = _build_provider(lambda **kwargs: _FakeStream([_failed_event()]))

    events = list(provider.stream_response(_request()))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, LLMError)
    assert event.kind is LLMErrorKind.INVALID_RESPONSE
    assert event.partial_text == ""


def test_response_failed_event_after_deltas_carries_the_partial_text() -> None:
    provider, _client = _build_provider(
        lambda **kwargs: _FakeStream(
            [_delta_event("algo "), _delta_event("parcial"), _failed_event()]
        )
    )

    events = list(provider.stream_response(_request()))

    last_event = events[-1]
    assert isinstance(last_event, LLMError)
    assert last_event.kind is LLMErrorKind.INVALID_RESPONSE
    assert last_event.partial_text == "algo parcial"


def test_retries_a_rate_limited_request_then_succeeds() -> None:
    attempts = {"count": 0}

    def _create(**kwargs: Any) -> object:
        attempts["count"] += 1
        if attempts["count"] < 3:
            response = httpx.Response(429, request=_DUMMY_REQUEST, json={})
            raise openai.RateLimitError("rate limited", response=response, body=None)
        return _FakeStream([_completed_event("ok")])

    provider, client = _build_provider(_create)

    events = list(provider.stream_response(_request()))

    assert isinstance(events[-1], LLMCompleted)
    assert len(client.responses.calls) == 3


def test_exceeding_max_retries_surfaces_a_rate_limited_error() -> None:
    def _create(**kwargs: Any) -> object:
        response = httpx.Response(429, request=_DUMMY_REQUEST, json={})
        raise openai.RateLimitError("rate limited", response=response, body=None)

    provider, client = _build_provider(_create)

    events = list(provider.stream_response(_request()))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, LLMError)
    assert event.kind is LLMErrorKind.RATE_LIMITED
    assert len(client.responses.calls) == 3  # 1 original attempt + 2 retries


def test_does_not_retry_authentication_errors() -> None:
    def _create(**kwargs: Any) -> object:
        response = httpx.Response(401, request=_DUMMY_REQUEST, json={})
        raise openai.AuthenticationError("nope", response=response, body=None)

    provider, client = _build_provider(_create)

    list(provider.stream_response(_request()))

    assert len(client.responses.calls) == 1


def test_cancel_before_streaming_sends_no_request() -> None:
    provider, client = _build_provider(lambda **kwargs: _FakeStream([_completed_event("ok")]))

    provider.cancel("op-cancel")
    events = list(provider.stream_response(_request(operation_id="op-cancel")))

    assert len(events) == 1
    assert isinstance(events[0], LLMCancelled)
    assert client.responses.calls == []


def test_cancel_mid_stream_stops_and_closes_the_stream() -> None:
    stream = _FakeStream(
        [_delta_event("a"), _delta_event("b"), _delta_event("c"), _completed_event("abc")]
    )
    provider, _client = _build_provider(lambda **kwargs: stream)

    generator = iter(provider.stream_response(_request(operation_id="op-mid")))
    first = next(generator)
    assert isinstance(first, LLMTextDelta)

    provider.cancel("op-mid")

    second = next(generator)
    assert isinstance(second, LLMCancelled)
    assert second.partial_text == "a"
    with pytest.raises(StopIteration):
        next(generator)
    assert stream.closed is True


def test_cancelling_repeatedly_is_a_safe_no_op() -> None:
    provider, client = _build_provider(lambda **kwargs: _FakeStream([_completed_event("ok")]))

    provider.cancel("op-repeat")
    provider.cancel("op-repeat")
    provider.cancel("op-repeat")
    events = list(provider.stream_response(_request(operation_id="op-repeat")))

    assert isinstance(events[0], LLMCancelled)
    assert client.responses.calls == []


def test_budget_exceeded_blocks_before_sending_any_request() -> None:
    policy = BudgetPolicy(monthly_limit_usd=0.0)
    budget = BudgetTracker(policy)
    provider, client = _build_provider(
        lambda **kwargs: _FakeStream([_completed_event("ok")]), budget_tracker=budget
    )

    events = list(provider.stream_response(_request()))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, LLMError)
    assert event.kind is LLMErrorKind.BUDGET_EXCEEDED
    assert client.responses.calls == []


def test_health_check_never_calls_the_network() -> None:
    provider, client = _build_provider(lambda **kwargs: _FakeStream([_completed_event("ok")]))

    assert provider.health_check() is True
    assert client.responses.calls == []


@pytest.mark.parametrize(
    ("exc_factory", "expected_kind"),
    [
        (
            lambda: openai.AuthenticationError(
                "x", response=httpx.Response(401, request=_DUMMY_REQUEST, json={}), body=None
            ),
            LLMErrorKind.AUTHENTICATION,
        ),
        (
            lambda: openai.PermissionDeniedError(
                "x", response=httpx.Response(403, request=_DUMMY_REQUEST, json={}), body=None
            ),
            LLMErrorKind.PERMISSION,
        ),
        (
            lambda: openai.RateLimitError(
                "x", response=httpx.Response(429, request=_DUMMY_REQUEST, json={}), body=None
            ),
            LLMErrorKind.RATE_LIMITED,
        ),
        (lambda: openai.APIConnectionError(request=_DUMMY_REQUEST), LLMErrorKind.CONNECTION),
        (lambda: openai.APITimeoutError(request=_DUMMY_REQUEST), LLMErrorKind.TIMEOUT),
        (
            lambda: openai.InternalServerError(
                "x", response=httpx.Response(500, request=_DUMMY_REQUEST, json={}), body=None
            ),
            LLMErrorKind.CONNECTION,
        ),
        (lambda: RuntimeError("something else"), LLMErrorKind.UNKNOWN),
    ],
)
def test_exceptions_are_classified_safely_without_leaking_their_message(
    exc_factory: Callable[[], Exception], expected_kind: LLMErrorKind
) -> None:
    def _raise(**kwargs: Any) -> object:
        raise exc_factory()

    provider, _client = _build_provider(_raise)

    events = list(provider.stream_response(_request(operation_id="op-once")))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, LLMError)
    assert event.kind is expected_kind
    # The message is always one of the fixed, safe strings - never str(exc).
    assert event.message in {
        "La credencial del proveedor no es válida.",
        "La credencial no tiene permiso para esta operación.",
        "El proveedor está limitando las peticiones; inténtalo de nuevo en un momento.",
        "No se pudo contactar con el proveedor.",
        "El proveedor tardó demasiado en responder.",
        "No se pudo completar la petición al proveedor.",
    }


@pytest.mark.parametrize("kind", list(LLMErrorKind))
def test_every_error_kind_has_a_safe_message(kind: LLMErrorKind) -> None:
    """Guards against a future ``LLMErrorKind`` member reaching ``_build_error``.

    ``_build_error`` indexes ``_SAFE_MESSAGES`` directly, so a kind missing from
    that table raises ``KeyError`` at the exact moment the provider is already
    failing — the worst possible time to add a second failure. The presentation
    table over this same enum has had an exhaustiveness guard for a while
    (``tests/unit/test_error_messages.py``); this one did not, and the gap was
    not hypothetical: ``CONFIGURATION`` was added to the enum, the presentation
    table picked it up and this one did not.
    """
    error = _build_error(kind)
    assert error.kind is kind
    assert error.message
