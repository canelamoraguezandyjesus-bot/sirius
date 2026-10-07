"""El modelo de huellas de Ollama (pieza F de ADR-233, ADR-238).

Nunca toca un Ollama de verdad: ``httpx.MockTransport`` hace de Ollama.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from sirius.adapters.llm.ollama_embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    OLLAMA_EMBED_URL,
    OllamaEmbedder,
)
from sirius.composition_root import EMBEDDING_MODEL_SETTING, embedding_model
from sirius.ports.embeddings import EmbeddingError


def _huellas(contestar: Callable[[httpx.Request], httpx.Response]) -> OllamaEmbedder:
    return OllamaEmbedder("modelo-de-huellas", transport=httpx.MockTransport(contestar))


def test_pide_las_huellas_al_ollama_de_este_ordenador_todas_de_una_vez() -> None:
    vistas: list[httpx.Request] = []

    def contestar(request: httpx.Request) -> httpx.Response:
        vistas.append(request)
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    huellas = _huellas(contestar).embed(["uno", "dos"])

    assert huellas == [[0.1, 0.2], [0.3, 0.4]]
    [peticion] = vistas
    assert str(peticion.url) == OLLAMA_EMBED_URL == "http://localhost:11434/api/embed"
    cuerpo = json.loads(peticion.content)
    assert cuerpo["model"] == "modelo-de-huellas"
    assert cuerpo["input"] == ["uno", "dos"]


def test_sin_frases_no_pregunta_a_nadie() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("no debía llamar")

    assert _huellas(contestar).embed([]) == []


@pytest.mark.parametrize(
    "respuesta",
    [
        httpx.Response(404, json={"error": "model not found"}),
        httpx.Response(200, text="esto no es JSON"),
        httpx.Response(200, json={"otra": "cosa"}),
        httpx.Response(200, json={"embeddings": [[0.1]]}),
        httpx.Response(200, json={"embeddings": "no es una lista"}),
    ],
    ids=["sin-modelo", "no-json", "sin-huellas", "una-de-menos", "no-lista"],
)
def test_lo_que_no_es_una_huella_por_frase_es_un_error_de_huellas(
    respuesta: httpx.Response,
) -> None:
    with pytest.raises(EmbeddingError):
        _huellas(lambda request: respuesta).embed(["uno", "dos"])


def test_sin_ollama_es_un_error_de_huellas() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=request)

    with pytest.raises(EmbeddingError):
        _huellas(contestar).embed(["uno"])


def test_el_modelo_de_huellas_sale_de_los_ajustes_y_si_no_el_del_plan() -> None:
    assert embedding_model({}) == DEFAULT_EMBEDDING_MODEL == "qwen3-embedding:0.6b"
    assert embedding_model({EMBEDDING_MODEL_SETTING: "  embeddinggemma  "}) == "embeddinggemma"
    assert embedding_model({EMBEDDING_MODEL_SETTING: ""}) == DEFAULT_EMBEDDING_MODEL
    assert embedding_model({EMBEDDING_MODEL_SETTING: 3}) == DEFAULT_EMBEDDING_MODEL


def test_la_huella_de_la_pregunta_espera_poco_y_la_de_los_recuerdos_mas(tmp_path: Path) -> None:
    from sirius.adapters.llm.ollama_embeddings import BACKGROUND_TIMEOUT, QUERY_TIMEOUT
    from sirius.adapters.secrets.fake import FakeSecretStore
    from sirius.composition_root import build_conversation_dependencies

    servicio = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "copias", secret_store=FakeSecretStore()
    ).memory_embedding_service

    assert QUERY_TIMEOUT.read is not None and BACKGROUND_TIMEOUT.read is not None
    assert QUERY_TIMEOUT.read <= 5 < BACKGROUND_TIMEOUT.read
    assert servicio._query_embedder._client.timeout == QUERY_TIMEOUT  # type: ignore[attr-defined]
    assert servicio._embedder._client.timeout == BACKGROUND_TIMEOUT  # type: ignore[attr-defined]
