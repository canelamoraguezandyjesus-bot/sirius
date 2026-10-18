"""Toda petición a Ollama lleva el tope de salida de sus ajustes (ADR-248).

Con un Ollama de mentira que, sin tope, escribe sin parar, y que con él para ahí, como el
de verdad. Por los sitios que construyen el proveedor: la charla, las preguntas trampa con
su juez, y la prueba a ciegas, que construye el suyo por cada modelo.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import httpx
import pytest
from test_ollama_chat_provider import ollama_que_no_para

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.settings import save_settings
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.embeddings import EmbeddingError

pytestmark = pytest.mark.integration

#: El «Máximo de tokens de salida» de sus ajustes en esta prueba.
_TOPE = 5


class _SinHuellas:
    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        msg = "sin modelo de huellas en esta prueba"
        raise EmbeddingError(msg)


def _sirius(tmp_path: Path, vistas: list[dict[str, object]]) -> ConversationDependencies:
    save_settings(
        {
            "llm_provider": "ollama",
            "ollama_chat_model": "qwen3:4b-instruct",
            "openai_max_output_tokens": _TOPE,
        }
    )
    rutas = resolve_paths()
    initialize_persistence(rutas)

    def contestar(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            modelos = [{"name": "qwen3:4b-instruct"}, {"name": "gemma3:4b"}]
            return httpx.Response(200, json={"models": modelos})
        vistas.append(json.loads(request.content))
        return ollama_que_no_para(request)

    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        ollama_transport=httpx.MockTransport(contestar),
        text_embedder=_SinHuellas(),
    )
    if not deps.initial_project_use_case.is_configured():
        deps.initial_project_use_case.create_initial_project("Charla con Sirius", "Charlar")
    return deps


def _topes(vistas: list[dict[str, object]]) -> set[object]:
    return {
        cuerpo["options"].get("num_predict") if isinstance(cuerpo["options"], dict) else None
        for cuerpo in vistas
    }


def test_la_charla_pide_el_tope_de_sus_ajustes_y_acaba_en_el(tmp_path: Path) -> None:
    vistas: list[dict[str, object]] = []
    deps = _sirius(tmp_path, vistas)
    try:
        resultado = deps.send_message_use_case.send_message("Cuéntame algo largo.")
    finally:
        deps.close_database_connections()

    assert _topes(vistas) == {_TOPE}
    assert (resultado.sirius_message.content or "").count("bla") == _TOPE


def test_las_preguntas_trampa_y_su_juez_piden_el_tope_de_sus_ajustes(tmp_path: Path) -> None:
    vistas: list[dict[str, object]] = []
    deps = _sirius(tmp_path, vistas)
    try:
        # Para con la respuesta de la segunda ya pedida: la primera vuelve con su veredicto.
        # Parar con el veredicto en marcha lo corta, y esa respuesta no vuelve: se guarda
        # para pedirle solo el veredicto la vez siguiente (ronda 1 de Codex sobre la #698).
        respuestas = deps.trick_questions_use_case.run(should_stop=lambda: len(vistas) >= 3)
    finally:
        deps.close_database_connections()

    assert respuestas
    # La respuesta a la idea mala, por la charla, y su veredicto, por el juez.
    assert len(vistas) >= 2
    assert _topes(vistas) == {_TOPE}


def test_la_prueba_a_ciegas_pide_el_tope_de_sus_ajustes_con_cada_modelo(tmp_path: Path) -> None:
    vistas: list[dict[str, object]] = []
    deps = _sirius(tmp_path, vistas)
    try:
        deps.blind_test_use_case.prepare(["qwen3:4b-instruct", "gemma3:4b"])
    finally:
        deps.close_database_connections()

    assert {cuerpo["model"] for cuerpo in vistas} == {"qwen3:4b-instruct", "gemma3:4b"}
    assert _topes(vistas) == {_TOPE}
