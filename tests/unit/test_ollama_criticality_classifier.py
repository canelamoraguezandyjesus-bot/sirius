"""Unit tests for ``OllamaCriticalityClassifierAdapter`` (M21a, ADR-130).

Never touches a real Ollama instance — ``httpx.MockTransport`` stands in for
the local HTTP endpoint, entirely in-process. Pins three things:

- the fail-open contract ``CriticalityClassifierPort`` requires: CRITICO /
  IMPORTANTE become the matching enum member; ORDINARIO and anything else
  (connection refused, timeout, malformed response, a server error, an
  answer outside the closed vocabulary) become ``None``, never an exception;
- the HTTP contract validated against the real local model (ADR-125):
  ``/api/chat`` with ``think: false`` and a closed ``format`` schema, so the
  request body is asserted literally (CODEX-001 of incidencia #518);
- §6.3's structural property at the request level: neither an injected
  client's remote ``base_url`` nor a redirect from localhost ever moves the
  request off the machine — asserted on the hosts the transport actually
  saw, never on ``propose``'s return value, which is ``None`` on both the
  correct and the broken path (CLAUDE-M21A-001 of incidencia #518).
"""

from __future__ import annotations

import json

import httpx
import pytest

from sirius.adapters.ollama_criticality_classifier import OllamaCriticalityClassifierAdapter
from sirius.domain.criticality import Criticality


def _adapter(handler: httpx.MockTransport) -> OllamaCriticalityClassifierAdapter:
    client = httpx.Client(transport=handler, base_url="http://localhost:11434")
    return OllamaCriticalityClassifierAdapter("llama3.2", client=client)


def _answer(level: str) -> httpx.Response:
    """An ``/api/chat`` answer constrained by the closed schema."""
    return httpx.Response(200, json={"message": {"content": json.dumps({"nivel": level})}})


def test_propose_returns_critico_when_ollama_answers_critico() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer("CRITICO")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("no volver a exponer la clave en texto plano") is Criticality.CRITICO


def test_propose_returns_importante_when_ollama_answers_importante() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer("IMPORTANTE")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("recordar revisar el backup semanal") is Criticality.IMPORTANTE


def test_propose_returns_none_when_ollama_answers_ordinario() -> None:
    """ORDINARIO no es una propuesta (D7/M21a): ``None`` significa "no hay
    propuesta", nunca "propuesta de ordinario"."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer("ORDINARIO")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_returns_none_when_the_response_is_empty() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer("")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_returns_none_when_the_response_is_outside_the_closed_vocabulary() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer("nivel-inventado")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.propose("contenido cualquiera") is None


def test_propose_returns_none_when_the_answer_is_prose_instead_of_the_schema() -> None:
    """What the default model does without ``think: false`` and a closed
    ``format`` (ADR-125): prose around the level. It is not parsed as a
    level by accident — it is ``None`` like any other unusable answer."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"message": {"content": "Creo que el nivel es CRITICO porque..."}}
        )

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


def test_propose_sends_the_contract_validated_against_the_real_model() -> None:
    """CODEX-001 (incidencia #518): the request must be the shape ADR-125
    validated with the real local model — ``/api/chat``, reasoning off, a
    closed schema for the answer — not ``/api/generate`` with a free prompt,
    which with the default Qwen3 model reasons for minutes and answers
    outside the vocabulary. Asserted literally on the request body."""
    seen: list[httpx.Request] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _answer("IMPORTANTE")

    adapter = _adapter(httpx.MockTransport(_handle))

    adapter.propose("recordar revisar el backup semanal")

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
        "properties": {"nivel": {"type": "string", "enum": ["CRITICO", "IMPORTANTE", "ORDINARIO"]}},
        "required": ["nivel"],
    }
    assert cuerpo["keep_alive"] == "15m"
    assert cuerpo["options"] == {"temperature": 0.1, "num_ctx": 8192}
    assert [m["role"] for m in cuerpo["messages"]] == ["system", "user"]
    assert cuerpo["messages"][1]["content"] == "recordar revisar el backup semanal"
    assert "CRITICO" in cuerpo["messages"][0]["content"]
    assert "IMPORTANTE" in cuerpo["messages"][0]["content"]
    assert "ORDINARIO" in cuerpo["messages"][0]["content"]


def test_propose_never_targets_a_remote_host() -> None:
    """§6.3's structural property, D7 §6.1, mirrored for criticality: no
    parameter anywhere lets a caller redirect this adapter away from
    localhost."""
    import inspect

    signature = inspect.signature(OllamaCriticalityClassifierAdapter.__init__)
    assert "host" not in signature.parameters
    assert "url" not in signature.parameters
    assert "base_url" not in signature.parameters


def test_propose_ignores_an_injected_clients_remote_base_url() -> None:
    """§6.3's structural property, at the request level: even the test seam
    must not let an injected ``httpx.Client`` with a remote ``base_url``
    redirect the actual request away from localhost."""
    seen_hosts: list[str | None] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        return _answer("CRITICO")

    client = httpx.Client(
        transport=httpx.MockTransport(_handle), base_url="https://servidor-remoto.example"
    )
    adapter = OllamaCriticalityClassifierAdapter("llama3.2", client=client)

    result = adapter.propose("contenido cualquiera")

    assert seen_hosts == ["localhost"]
    assert result is Criticality.CRITICO


def test_propose_never_follows_a_redirect_to_a_remote_host() -> None:
    """CLAUDE-M21A-001 (incidencia #518): an injected client with
    ``follow_redirects=True`` must not let a 307/308 from localhost resend
    this request (and the content) to a remote host. Asserted on the hosts
    the transport saw — ``propose`` returns ``None`` on both the correct and
    the broken path, so its return value cannot tell them apart."""
    seen_hosts: list[str | None] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        return httpx.Response(
            307,
            headers={"Location": "https://remote.example/leak"},
            json={"message": {"content": json.dumps({"nivel": "CRITICO"})}},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(_handle),
        base_url="http://localhost:11434",
        follow_redirects=True,
    )
    adapter = OllamaCriticalityClassifierAdapter("llama3.2", client=client)

    result = adapter.propose("contenido cualquiera")

    assert seen_hosts == ["localhost"]
    assert result is None


@pytest.mark.integration
def test_propose_defaults_to_a_client_pointed_at_localhost() -> None:
    """No injected ``client``: production code always falls back to a client
    hardcoded to localhost, never a remote host, and never raises even
    though nothing is actually listening there."""
    adapter = OllamaCriticalityClassifierAdapter("llama3.2")

    assert adapter.propose("contenido cualquiera") is None
