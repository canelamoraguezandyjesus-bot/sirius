from sirius.adapters.llm.unconfigured import UnconfiguredLLMProvider
from sirius.ports.llm import LLMError, LLMErrorKind, LLMRequest


def _request() -> LLMRequest:
    return LLMRequest(operation_id="op-1", instructions="", input_text="hola")


def test_health_check_is_always_false() -> None:
    assert UnconfiguredLLMProvider("no configurado").health_check() is False


def test_stream_response_yields_exactly_one_configuration_error() -> None:
    provider = UnconfiguredLLMProvider("Falta una clave de API.")

    events = list(provider.stream_response(_request()))

    assert len(events) == 1
    event = events[0]
    assert isinstance(event, LLMError)
    assert event.kind is LLMErrorKind.CONFIGURATION
    assert event.message == "Falta una clave de API."


def test_cancel_is_a_safe_no_op() -> None:
    provider = UnconfiguredLLMProvider("no configurado")

    provider.cancel("op-1")  # must not raise
