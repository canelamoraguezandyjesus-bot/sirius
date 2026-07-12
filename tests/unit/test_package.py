from sirius import __version__
from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.ports.llm import LLMRequest


def test_package_has_version() -> None:
    assert __version__ == "0.1.0.dev0"


def test_fake_provider_is_deterministic() -> None:
    provider = FakeLLMProvider()
    request = LLMRequest(operation_id="op-1", instructions="", input_text="Hola")

    assert provider.health_check() is True
    assert "".join(chunk.text for chunk in provider.stream_response(request)) == (
        "Respuesta simulada de Sirius."
    )
