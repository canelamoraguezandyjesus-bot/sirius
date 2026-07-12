from sirius import __version__
from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMTextDelta


def test_package_has_version() -> None:
    assert __version__ == "0.1.0.dev0"


def test_fake_provider_is_deterministic() -> None:
    provider = FakeLLMProvider()
    request = LLMRequest(operation_id="op-1", instructions="", input_text="Hola")

    assert provider.health_check() is True
    events = list(provider.stream_response(request))

    deltas = [e for e in events if isinstance(e, LLMTextDelta)]
    completed = [e for e in events if isinstance(e, LLMCompleted)]
    assert "".join(d.text for d in deltas) == "Respuesta simulada de Sirius."
    assert len(completed) == 1
    assert completed[0].text == "Respuesta simulada de Sirius."
