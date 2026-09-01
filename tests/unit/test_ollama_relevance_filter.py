"""Unit tests for ``OllamaRelevanceFilterAdapter`` (D7, SIRIUS-ARQ-0.2 §6.3).

Never touches a real Ollama instance: ``httpx.MockTransport`` stands in for
the local HTTP endpoint, entirely in-process. Pins the fail-open contract
``RelevanceFilterPort`` requires: a valid response is parsed into the
expected subset and order; anything else (not installed/connection refused,
accepted-but-never-answered until the timeout, a malformed response) becomes
``candidates`` unmodified, never an exception — §6.4 point 3 requires the
"accepts and never answers" scenario be distinct from an immediate refusal,
so both are exercised with the exception ``httpx`` itself uses to tell them
apart (``ConnectError`` vs. ``ReadTimeout``).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx

from sirius.adapters.ollama_relevance_filter import OllamaRelevanceFilterAdapter
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.relevance import KnowledgeKind, RankedKnowledge


def _decision(decision_id: int, content: str) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content=content,
        source_event_id=None,
        created_at=now,
    )
    return Decision(
        id=decision_id,
        subject="asunto",
        project_id=1,
        status=DecisionStatus.APPROVED,
        current_revision=revision,
        created_at=now,
        updated_at=now,
    )


def _candidate(decision_id: int, content: str) -> RankedKnowledge:
    return RankedKnowledge(
        kind=KnowledgeKind.DECISION,
        item=_decision(decision_id, content),
        subject_matches_query=False,
        project_matches_active=False,
        fts_match=True,
    )


def _adapter(handler: httpx.MockTransport) -> OllamaRelevanceFilterAdapter:
    client = httpx.Client(transport=handler, base_url="http://localhost:11434")
    return OllamaRelevanceFilterAdapter("llama3.2", client=client)


def test_filter_candidates_returns_the_expected_subset_and_order() -> None:
    """§8-M10's dedicated adapter test: a valid local response is parsed
    into exactly the subset and order the response names — position 2, then
    position 1 — never the candidates' own input order restored, since the
    adapter itself never reorders on the caller's behalf either way; the
    exact positions kept is what is under test here."""
    candidates = (_candidate(1, "primero"), _candidate(2, "segundo"), _candidate(3, "tercero"))

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": json.dumps({"responden": [2, 1]})}})

    adapter = _adapter(httpx.MockTransport(_handle))

    result = adapter.filter_candidates("consulta", candidates)

    assert result == (candidates[0], candidates[1])


def test_filter_candidates_returns_candidates_unmodified_when_the_connection_is_refused() -> None:
    """§6.4 point 3: Ollama not installed and connection refused are the
    same immediate-failure scenario — ``httpx.ConnectError``, distinct from
    the accepted-but-hung scenario below."""
    candidates = (_candidate(1, "contenido"),)

    def _handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.filter_candidates("consulta", candidates) == candidates


def test_filter_candidates_returns_candidates_unmodified_when_ollama_accepts_and_hangs() -> None:
    """§6.4 point 3: a double that accepts the connection and never answers
    until the time budget is exhausted — ``httpx.ReadTimeout``, never
    ``ConnectError`` — is a distinct scenario from an immediate refusal."""
    candidates = (_candidate(1, "contenido"),)

    def _handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out waiting for a response", request=request)

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.filter_candidates("consulta", candidates) == candidates


def test_filter_candidates_returns_candidates_unmodified_on_a_malformed_json_response() -> None:
    candidates = (_candidate(1, "contenido"),)

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.filter_candidates("consulta", candidates) == candidates


def test_filter_candidates_returns_candidates_unmodified_when_response_field_is_missing() -> None:
    candidates = (_candidate(1, "contenido"),)

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.filter_candidates("consulta", candidates) == candidates


def test_filter_candidates_returns_candidates_unmodified_when_keep_is_not_a_list_of_ints() -> None:
    candidates = (_candidate(1, "contenido"),)

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"message": {"content": json.dumps({"responden": "todos"})}}
        )

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.filter_candidates("consulta", candidates) == candidates


def test_filter_candidates_returns_candidates_unmodified_when_keep_references_out_of_range() -> (
    None
):
    candidates = (_candidate(1, "contenido"),)

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": json.dumps({"responden": [7]})}})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.filter_candidates("consulta", candidates) == candidates


def test_filter_candidates_returns_candidates_unmodified_on_a_server_error_response() -> None:
    candidates = (_candidate(1, "contenido"),)

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model not found"})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.filter_candidates("consulta", candidates) == candidates


def test_filter_candidates_never_targets_a_remote_host() -> None:
    """§6.3's structural property: no parameter anywhere lets a caller
    redirect this adapter away from localhost."""
    import inspect

    signature = inspect.signature(OllamaRelevanceFilterAdapter.__init__)
    assert "host" not in signature.parameters
    assert "url" not in signature.parameters
    assert "base_url" not in signature.parameters


def test_filter_candidates_ignores_an_injected_clients_remote_base_url() -> None:
    """§6.3's structural property, at the request level: even the test seam
    must not let an injected ``httpx.Client`` with a remote ``base_url``
    redirect the actual request away from localhost."""
    candidates = (_candidate(1, "contenido"),)
    seen_hosts: list[str | None] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        return httpx.Response(200, json={"message": {"content": json.dumps({"responden": [1]})}})

    client = httpx.Client(
        transport=httpx.MockTransport(_handle), base_url="https://servidor-remoto.example"
    )
    adapter = OllamaRelevanceFilterAdapter("llama3.2", client=client)

    result = adapter.filter_candidates("consulta", candidates)

    assert seen_hosts == ["localhost"]
    assert result == candidates


def test_filter_candidates_never_follows_a_redirect_to_a_remote_host() -> None:
    """CODEX-001 regression (PR #452): an injected client with
    ``follow_redirects=True`` must not let a 307/308 from localhost resend
    this request (and its body) to a remote host."""
    candidates = (_candidate(1, "contenido"),)
    seen_hosts: list[str | None] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        return httpx.Response(
            307,
            headers={"Location": "https://remote.example/leak"},
            json={"message": {"content": json.dumps({"responden": [1]})}},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(_handle),
        base_url="http://localhost:11434",
        follow_redirects=True,
    )
    adapter = OllamaRelevanceFilterAdapter("llama3.2", client=client)

    result = adapter.filter_candidates("consulta", candidates)

    assert seen_hosts == ["localhost"]
    assert result == candidates


def test_filter_candidates_returns_candidates_unmodified_when_keep_contains_booleans() -> None:
    """``bool`` is a subclass of ``int`` in Python; a response shaped as
    ``{"responden": [true]}`` is well-formed JSON but not the list of integer
    positions the contract requires, so it must fail open like any other
    unexpected shape rather than being silently accepted as position 1."""
    candidates = (_candidate(1, "primero"), _candidate(2, "segundo"))

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": json.dumps({"responden": [True]})}})

    adapter = _adapter(httpx.MockTransport(_handle))

    assert adapter.filter_candidates("consulta", candidates) == candidates
