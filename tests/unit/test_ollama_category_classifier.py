"""Unit tests for ``OllamaCategoryClassifierAdapter`` (D7, SIRIUS-ARQ-0.2 §6.1).

Never touches a real Ollama instance: ``httpx.MockTransport`` stands in for
the local HTTP endpoint, entirely in-process. Pins the fail-open contract
``CategoryClassifierPort`` requires: a valid response in the vocabulary is
returned as-is; anything else (connection refused, timeout, malformed
response, a value outside the closed vocabulary) becomes ``None``, never an
exception.
"""

from __future__ import annotations

import httpx
import pytest

from sirius.adapters.ollama_category_classifier import OllamaCategoryClassifierAdapter

_VOCABULARY = frozenset({"trabajo", "personal"})


def _adapter(handler: httpx.MockTransport) -> OllamaCategoryClassifierAdapter:
    client = httpx.Client(transport=handler, base_url="http://localhost:11434")
    return OllamaCategoryClassifierAdapter("llama3.2", _VOCABULARY, client=client)


def test_classify_returns_the_categoria_ollama_answers_with() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "trabajo"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.classify("reunión de equipo") == "trabajo"


def test_classify_returns_none_when_the_response_is_outside_the_closed_vocabulary() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "categoria-inventada"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.classify("contenido cualquiera") is None


def test_classify_returns_none_when_the_connection_is_refused() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.classify("contenido cualquiera") is None


def test_classify_returns_none_when_the_request_times_out() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.classify("contenido cualquiera") is None


def test_classify_returns_none_on_a_server_error_response() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model not found"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.classify("contenido cualquiera") is None


def test_classify_returns_none_on_a_malformed_json_response() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.classify("contenido cualquiera") is None


def test_classify_never_targets_a_remote_host() -> None:
    """§6.3's structural property, D7 §6.1: no parameter anywhere lets a
    caller redirect this adapter away from localhost."""
    import inspect

    signature = inspect.signature(OllamaCategoryClassifierAdapter.__init__)
    assert "host" not in signature.parameters
    assert "url" not in signature.parameters
    assert "base_url" not in signature.parameters


@pytest.mark.integration
def test_classify_defaults_to_a_client_pointed_at_localhost() -> None:
    """No injected ``client``: production code always falls back to a client
    hardcoded to localhost, never a remote host, and never raises even
    though nothing is actually listening there."""
    adapter = OllamaCategoryClassifierAdapter("llama3.2", _VOCABULARY)

    assert adapter.classify("contenido cualquiera") is None
