"""Unit tests for ``OllamaCriticalityClassifierAdapter`` (M21a, ADR-130).

Calcado de ``test_ollama_category_classifier.py``: never touches a real
Ollama instance — ``httpx.MockTransport`` stands in for the local HTTP
endpoint, entirely in-process. Pins the fail-open contract
``CriticalityClassifierPort`` requires: CRITICO/IMPORTANTE become the
matching enum member; ORDINARIO and anything else (connection refused,
timeout, malformed response, a server error) become ``None``, never an
exception.
"""

from __future__ import annotations

import httpx
import pytest

from sirius.adapters.ollama_criticality_classifier import OllamaCriticalityClassifierAdapter
from sirius.domain.criticality import Criticality


def _adapter(handler: httpx.MockTransport) -> OllamaCriticalityClassifierAdapter:
    client = httpx.Client(transport=handler, base_url="http://localhost:11434")
    return OllamaCriticalityClassifierAdapter("llama3.2", client=client)


def test_propose_returns_critico_when_ollama_answers_critico() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "CRITICO"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("no volver a exponer la clave en texto plano") is Criticality.CRITICO


def test_propose_returns_importante_when_ollama_answers_importante() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "IMPORTANTE"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("recordar revisar el backup semanal") is Criticality.IMPORTANTE


def test_propose_returns_none_when_ollama_answers_ordinario() -> None:
    """ORDINARIO no es una propuesta (D7/M21a): ``None`` significa "no hay
    propuesta", nunca "propuesta de ordinario"."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "ORDINARIO"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_returns_none_when_the_response_is_empty() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": ""})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_returns_none_when_the_response_is_outside_the_closed_vocabulary() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "nivel-inventado"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_returns_none_when_the_connection_is_refused() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_returns_none_when_the_request_times_out() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_returns_none_on_a_server_error_response() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model not found"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_returns_none_on_a_malformed_json_response() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_does_not_follow_redirects() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        if request.url.host == "localhost":
            return httpx.Response(302, headers={"Location": "http://evil.example/api/generate"})
        raise AssertionError("must never leave localhost")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_never_targets_a_remote_host() -> None:
    """§6.3's structural property, D7 §6.1, mirrored for criticality: no
    parameter anywhere lets a caller redirect this adapter away from
    localhost."""
    import inspect

    signature = inspect.signature(OllamaCriticalityClassifierAdapter.__init__)
    assert "host" not in signature.parameters
    assert "url" not in signature.parameters
    assert "base_url" not in signature.parameters


@pytest.mark.integration
def test_propose_defaults_to_a_client_pointed_at_localhost() -> None:
    """No injected ``client``: production code always falls back to a client
    hardcoded to localhost, never a remote host, and never raises even
    though nothing is actually listening there."""
    adapter = OllamaCriticalityClassifierAdapter("llama3.2")

    assert adapter.propose("contenido cualquiera") is None
