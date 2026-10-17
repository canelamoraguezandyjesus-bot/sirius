"""Que el modelo de la charla vaya cargando al arrancar (ADR-252).

La primera frase tras abrir Sirius esperaba a que Ollama cargara el modelo. La ventana y
``sirius-oye`` le piden que lo cargue al arrancar, en otro hilo y sin esperarle.
"""

from __future__ import annotations

import json
import logging
import threading
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from sirius.adapters.llm.ollama_chat import OLLAMA_CHAT_URL, OllamaChatProvider
from sirius.application.send_message import SendMessageUseCase
from sirius.ports.llm import LLMRequest


class _Precargable:
    """Un modelo de este ordenador que sabe cargarse; con ``espera``, tarda hasta que se
    le suelta."""

    def __init__(self, *, de_aqui: bool = True, espera: bool = False) -> None:
        self.runs_on_this_computer = de_aqui
        self.hilos: list[str] = []
        self.suelta = threading.Event()
        self._espera = espera

    def warm_up(self) -> None:
        self.hilos.append(threading.current_thread().name)
        if self._espera:
            assert self.suelta.wait(5)


def _charla(proveedor: object) -> SendMessageUseCase:
    return SendMessageUseCase(SimpleNamespace(), SimpleNamespace(), proveedor)  # type: ignore[arg-type]


def test_la_charla_pide_al_modelo_de_aqui_que_cargue_sin_esperarle() -> None:
    modelo = _Precargable(espera=True)

    hilo = _charla(modelo).warm_up_in_background()

    # Ha vuelto con el modelo aún cargando, en su hilo.
    assert hilo is not None
    assert hilo.is_alive()
    modelo.suelta.set()
    hilo.join(5)
    assert modelo.hilos == ["sirius-precarga"]


def test_un_modelo_de_fuera_no_se_precarga() -> None:
    modelo = _Precargable(de_aqui=False)

    assert _charla(modelo).warm_up_in_background() is None
    assert modelo.hilos == []


def test_un_modelo_que_no_sabe_cargarse_no_se_precarga() -> None:
    modelo = SimpleNamespace(runs_on_this_computer=True)

    assert _charla(modelo).warm_up_in_background() is None


# --- Ollama -----------------------------------------------------------------------------


def _ollama(contestar: Any, **ajustes: Any) -> OllamaChatProvider:
    return OllamaChatProvider("gemma3:4b", transport=httpx.MockTransport(contestar), **ajustes)


def test_ollama_carga_el_modelo_sin_preguntar_nada_con_el_contexto_de_la_charla() -> None:
    pedidos: list[tuple[str, dict[str, Any]]] = []

    def contestar(request: httpx.Request) -> httpx.Response:
        pedidos.append((str(request.url), json.loads(request.content)))
        if pedidos[-1][1]["messages"]:
            fin = {"message": {"content": "Hola."}, "done": True}
            return httpx.Response(200, content=(json.dumps(fin) + "\n").encode())
        return httpx.Response(200, json={"done": True, "done_reason": "load"})

    proveedor = _ollama(contestar, num_ctx=6144, num_predict=2048)
    proveedor.warm_up()
    list(proveedor.stream_response(LLMRequest("op", "Instrucciones.", "Hola.")))

    (url, carga), (_, charla) = pedidos
    assert url == OLLAMA_CHAT_URL
    assert carga == {
        "model": "gemma3:4b",
        "messages": [],
        "stream": False,
        "keep_alive": "30m",
        "options": {"num_ctx": 6144, "num_predict": 2048},
    }
    # Con el contexto y la permanencia de la charla: con otro contexto, Ollama volvería a
    # cargar el modelo en la primera frase.
    assert carga["options"] == charla["options"]
    assert carga["keep_alive"] == charla["keep_alive"]


def test_sin_ollama_la_precarga_lo_apunta_y_no_falla(caplog: pytest.LogCaptureFixture) -> None:
    def caido(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    with caplog.at_level(logging.INFO, logger="sirius"):
        _ollama(caido).warm_up()

    assert "No se pudo precargar gemma3:4b (ConnectError)" in caplog.text


def test_si_ollama_no_tiene_el_modelo_la_precarga_lo_apunta_y_no_falla(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def no_lo_tiene(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": 'model "gemma3:4b" not found'})

    with caplog.at_level(logging.INFO, logger="sirius"):
        _ollama(no_lo_tiene).warm_up()

    assert "Ollama no precargó gemma3:4b (404)" in caplog.text
    # Nada de lo que dice Ollama va al diario.
    assert "not found" not in caplog.text
