"""Unit tests for ``OllamaCategoryClassifierAdapter`` (D7, SIRIUS-ARQ-0.2 §6.1,
ADR-132, incidencia #522).

Never touches a real Ollama instance — ``httpx.MockTransport`` stands in for
the local HTTP endpoint, entirely in-process. Pins three things, mirroring
``tests/unit/test_ollama_criticality_classifier.py`` (its corrected twin,
PR #519):

- the fail-open contract ``CategoryClassifierPort`` requires: a value inside
  the injected vocabulary is returned as-is; anything else (connection
  refused, timeout, malformed response, a server error, an answer outside
  the closed vocabulary) becomes ``None``, never an exception;
- the HTTP contract validated against the real local model (ADR-125):
  ``/api/chat`` with ``think: false`` and a closed ``format`` schema whose
  enum is exactly the vocabulary injected in the constructor, sorted for a
  deterministic request — asserted literally on the request body;
- §6.3's structural property at the request level: neither an injected
  client's remote ``base_url`` nor a redirect from localhost ever moves the
  request off the machine — asserted on the hosts the transport actually
  saw, never on ``classify``'s return value, which is ``None`` on both the
  correct and the broken path.
"""

from __future__ import annotations

import json

import httpx
import pytest

from sirius.adapters.ollama_category_classifier import OllamaCategoryClassifierAdapter

_VOCABULARY = frozenset({"trabajo", "personal"})


def _adapter(handler: httpx.MockTransport) -> OllamaCategoryClassifierAdapter:
    client = httpx.Client(transport=handler, base_url="http://localhost:11434")
    return OllamaCategoryClassifierAdapter("llama3.2", _VOCABULARY, client=client)


def _answer(categoria: str) -> httpx.Response:
    """An ``/api/chat`` answer constrained by the closed schema."""
    return httpx.Response(200, json={"message": {"content": json.dumps({"categoria": categoria})}})


def test_classify_returns_the_categoria_ollama_answers_with() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer("trabajo")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.classify("reunión de equipo") == "trabajo"


def test_classify_returns_none_when_the_response_is_outside_the_closed_vocabulary() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer("categoria-inventada")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.classify("contenido cualquiera") is None


def test_classify_returns_none_when_the_answer_is_prose_instead_of_the_schema() -> None:
    """What the old ``/api/generate`` adapter risked without ``think: false``
    and a closed ``format`` (ADR-125): prose around the category. It is not
    parsed as a category by accident — it is ``None`` like any other unusable
    answer."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"message": {"content": "Creo que la categoría es trabajo porque..."}}
        )

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


def test_classify_sends_the_contract_validated_against_the_real_model() -> None:
    """ADR-125, mirrored for category (ADR-132, incidencia #522): the request
    must be the shape validated with the real local model — ``/api/chat``,
    reasoning off, a closed schema whose enum is exactly the injected
    vocabulary, sorted so the request is deterministic — not
    ``/api/generate`` with a free prompt. Asserted literally on the body."""
    seen: list[httpx.Request] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _answer("trabajo")

    adapter = _adapter(httpx.MockTransport(_handle))

    adapter.classify("reunión de equipo")

    assert len(seen) == 1
    peticion = seen[0]
    assert peticion.method == "POST"
    assert peticion.url.host == "localhost"
    assert peticion.url.path == "/api/chat"
    cuerpo = json.loads(peticion.content)
    assert cuerpo["model"] == "llama3.2"
    assert cuerpo["stream"] is False
    assert cuerpo["think"] is False
    assert cuerpo["format"] == {
        "type": "object",
        "properties": {"categoria": {"type": "string", "enum": ["personal", "trabajo"]}},
        "required": ["categoria"],
    }
    assert cuerpo["keep_alive"] == "15m"
    assert cuerpo["options"] == {"temperature": 0.1, "num_ctx": 8192}
    assert [m["role"] for m in cuerpo["messages"]] == ["system", "user"]
    assert cuerpo["messages"][1]["content"] == "reunión de equipo"
    assert "trabajo" in cuerpo["messages"][0]["content"]
    assert "personal" in cuerpo["messages"][0]["content"]


def test_classify_never_targets_a_remote_host() -> None:
    """§6.3's structural property, D7 §6.1: no parameter anywhere lets a
    caller redirect this adapter away from localhost."""
    import inspect

    signature = inspect.signature(OllamaCategoryClassifierAdapter.__init__)
    assert "host" not in signature.parameters
    assert "url" not in signature.parameters
    assert "base_url" not in signature.parameters


def test_classify_ignores_an_injected_clients_remote_base_url() -> None:
    """§6.3's structural property, at the request level: even the test seam
    must not let an injected ``httpx.Client`` with a remote ``base_url``
    redirect the actual request away from localhost."""
    seen_hosts: list[str | None] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        return _answer("trabajo")

    client = httpx.Client(
        transport=httpx.MockTransport(_handle), base_url="https://servidor-remoto.example"
    )
    adapter = OllamaCategoryClassifierAdapter("llama3.2", _VOCABULARY, client=client)

    result = adapter.classify("contenido cualquiera")

    assert seen_hosts == ["localhost"]
    assert result == "trabajo"


def test_classify_never_follows_a_redirect_to_a_remote_host() -> None:
    """An injected client with ``follow_redirects=True`` must not let a
    307/308 from localhost resend this request (and the content) to a remote
    host. Asserted on the hosts the transport saw — ``classify`` returns
    ``None`` on both the correct and the broken path, so its return value
    cannot tell them apart."""
    seen_hosts: list[str | None] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        return httpx.Response(
            307,
            headers={"Location": "https://remote.example/leak"},
            json={"message": {"content": json.dumps({"categoria": "trabajo"})}},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(_handle),
        base_url="http://localhost:11434",
        follow_redirects=True,
    )
    adapter = OllamaCategoryClassifierAdapter("llama3.2", _VOCABULARY, client=client)

    result = adapter.classify("contenido cualquiera")

    assert seen_hosts == ["localhost"]
    assert result is None


@pytest.mark.integration
def test_classify_defaults_to_a_client_pointed_at_localhost() -> None:
    """No injected ``client``: production code always falls back to a client
    hardcoded to localhost, never a remote host, and never raises even
    though nothing is actually listening there."""
    adapter = OllamaCategoryClassifierAdapter("llama3.2", _VOCABULARY)

    assert adapter.classify("contenido cualquiera") is None
