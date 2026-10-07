"""El conector de Ollama para la charla (pieza C de ADR-233).

Nunca toca un Ollama de verdad: ``httpx.MockTransport`` hace de Ollama y
contesta en su formato de líneas JSON.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable

import httpx
import pytest

from sirius.adapters.llm.ollama_chat import (
    OLLAMA_CHAT_URL,
    OllamaChatProvider,
    OllamaNotAvailableError,
    list_installed_models,
)
from sirius.ports.llm import (
    MEMORY_SUGGESTION_DELIMITER,
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)

_PETICION = LLMRequest(operation_id="op-1", instructions="Eres Sirius.", input_text="Hola")


def _lineas(*trozos: str, final: dict[str, object] | None = None) -> str:
    lineas: list[dict[str, object]] = [
        {"message": {"role": "assistant", "content": trozo}, "done": False} for trozo in trozos
    ]
    lineas.append({"message": {"role": "assistant", "content": ""}, "done": True, **(final or {})})
    return "\n".join(json.dumps(linea) for linea in lineas) + "\n"


def _proveedor(contestar: Callable[[httpx.Request], httpx.Response]) -> OllamaChatProvider:
    return OllamaChatProvider("modelo-de-prueba", transport=httpx.MockTransport(contestar))


def _eventos(
    proveedor: OllamaChatProvider, peticion: LLMRequest = _PETICION
) -> list[LLMStreamEvent]:
    return list(proveedor.stream_response(peticion))


def _texto(eventos: Iterable[LLMStreamEvent]) -> str:
    return "".join(e.text for e in eventos if isinstance(e, LLMTextDelta))


def test_pide_al_ollama_local_con_la_semilla_como_sistema_y_un_contexto_explicito() -> None:
    vistas: list[httpx.Request] = []

    def contestar(request: httpx.Request) -> httpx.Response:
        vistas.append(request)
        return httpx.Response(200, text=_lineas("Hola, ", "jefe."))

    eventos = _eventos(
        OllamaChatProvider("qwen-x", num_ctx=4096, transport=httpx.MockTransport(contestar))
    )

    [request] = vistas
    assert str(request.url) == OLLAMA_CHAT_URL
    assert request.url.host == "localhost"
    cuerpo = json.loads(request.content)
    assert cuerpo["model"] == "qwen-x"
    assert cuerpo["stream"] is True
    assert cuerpo["options"] == {"num_ctx": 4096}
    assert cuerpo["keep_alive"]
    assert cuerpo["messages"] == [
        {"role": "system", "content": "Eres Sirius."},
        {"role": "user", "content": "Hola"},
    ]
    assert _texto(eventos) == "Hola, jefe."
    assert isinstance(eventos[-1], LLMCompleted)
    assert eventos[-1].text == "Hola, jefe."


def test_el_contexto_por_defecto_es_de_8192_tokens() -> None:
    cuerpos: list[dict[str, object]] = []

    def contestar(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        return httpx.Response(200, text=_lineas("Vale."))

    _eventos(_proveedor(contestar))

    assert cuerpos[0]["options"] == {"num_ctx": 8192}


def test_cuenta_los_tokens_que_dice_ollama_al_terminar() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=_lineas("Vale.", final={"prompt_eval_count": 120, "eval_count": 7})
        )

    completado = _eventos(_proveedor(contestar))[-1]

    assert isinstance(completado, LLMCompleted)
    assert (completado.input_tokens, completado.output_tokens) == (120, 7)


def test_el_razonamiento_interno_no_llega_aunque_venga_partido() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=_lineas("<thi", "nk>Voy a pensar", " un rato</th", "ink>\n\nBuenos ", "días.")
        )

    eventos = _eventos(_proveedor(contestar))

    assert _texto(eventos) == "Buenos días."
    assert isinstance(eventos[-1], LLMCompleted)
    assert eventos[-1].text == "Buenos días."


def test_un_texto_que_empieza_como_una_etiqueta_pero_no_lo_es_se_queda() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_lineas("Dos < tres", " y <thi"))

    eventos = _eventos(_proveedor(contestar))

    assert isinstance(eventos[-1], LLMCompleted)
    assert eventos[-1].text == "Dos < tres y <thi"


def test_la_sugerencia_de_recuerdo_se_separa_y_nunca_llega_al_texto() -> None:
    mitad = len(MEMORY_SUGGESTION_DELIMITER) // 2

    def contestar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=_lineas(
                "Apuntado. ",
                MEMORY_SUGGESTION_DELIMITER[:mitad],
                MEMORY_SUGGESTION_DELIMITER[mitad:] + " Le gusta la tortilla con cebolla.",
            ),
        )

    eventos = _eventos(_proveedor(contestar))

    assert MEMORY_SUGGESTION_DELIMITER not in _texto(eventos)
    completado = eventos[-1]
    assert isinstance(completado, LLMCompleted)
    assert completado.text == "Apuntado. "
    assert completado.memory_suggestion == "Le gusta la tortilla con cebolla."


def test_un_modelo_que_no_esta_instalado_es_un_error_de_configuracion() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'modelo-de-prueba' not found"})

    [evento] = _eventos(_proveedor(contestar))

    assert isinstance(evento, LLMError)
    assert evento.kind is LLMErrorKind.CONFIGURATION


def test_si_ollama_no_contesta_es_un_error_de_conexion() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=request)

    [evento] = _eventos(_proveedor(contestar))

    assert isinstance(evento, LLMError)
    assert evento.kind is LLMErrorKind.CONNECTION
    assert "Ollama" in evento.message


def test_un_error_a_mitad_de_respuesta_conserva_lo_ya_dicho() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        lineas = [
            json.dumps({"message": {"content": "Empez"}, "done": False}),
            json.dumps({"error": "se acabó la memoria"}),
        ]
        return httpx.Response(200, text="\n".join(lineas) + "\n")

    eventos = _eventos(_proveedor(contestar))

    assert isinstance(eventos[-1], LLMError)
    assert eventos[-1].kind is LLMErrorKind.UNKNOWN
    assert eventos[-1].partial_text == "Empez"


def test_una_linea_que_no_es_json_es_una_respuesta_invalida() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="esto no es json\n")

    [evento] = _eventos(_proveedor(contestar))

    assert isinstance(evento, LLMError)
    assert evento.kind is LLMErrorKind.INVALID_RESPONSE


def test_una_respuesta_que_termina_sin_done_es_invalida() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=json.dumps({"message": {"content": "Hola"}}) + "\n")

    eventos = _eventos(_proveedor(contestar))

    assert isinstance(eventos[-1], LLMError)
    assert eventos[-1].kind is LLMErrorKind.INVALID_RESPONSE
    assert eventos[-1].partial_text == "Hola"


def test_una_respuesta_vacia_es_invalida() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_lineas("<think>solo pienso</think>", "  "))

    eventos = _eventos(_proveedor(contestar))

    assert isinstance(eventos[-1], LLMError)
    assert eventos[-1].kind is LLMErrorKind.INVALID_RESPONSE


def test_cancelada_antes_de_empezar_no_pide_nada() -> None:
    vistas: list[httpx.Request] = []

    def contestar(request: httpx.Request) -> httpx.Response:
        vistas.append(request)
        return httpx.Response(200, text=_lineas("Hola."))

    proveedor = _proveedor(contestar)
    proveedor.cancel("op-1")

    assert _eventos(proveedor) == [LLMCancelled(partial_text="")]
    assert vistas == []


def test_cancelada_a_mitad_conserva_lo_ya_dicho() -> None:
    proveedor: OllamaChatProvider

    def contestar(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_lineas("Uno, ", "dos, ", "tres."))

    proveedor = _proveedor(contestar)
    eventos: list[LLMStreamEvent] = []
    for evento in proveedor.stream_response(_PETICION):
        eventos.append(evento)
        if isinstance(evento, LLMTextDelta):
            proveedor.cancel("op-1")

    assert eventos[-1] == LLMCancelled(partial_text="Uno, ")


def test_no_lee_los_proxies_del_sistema() -> None:
    proveedor = _proveedor(lambda request: httpx.Response(200, text=_lineas("Hola.")))

    assert proveedor._client.trust_env is False


def test_dice_con_que_modelo_contesta() -> None:
    assert OllamaChatProvider("gemma-x").model_name == "gemma-x"


def test_los_modelos_instalados_salen_ordenados_y_sin_repetir() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "localhost"
        assert request.url.path == "/api/tags"
        modelos = [{"name": "qwen-x"}, {"name": "gemma-y"}, {"name": "qwen-x"}, {"nombre": "raro"}]
        return httpx.Response(200, json={"models": modelos})

    assert list_installed_models(httpx.MockTransport(contestar)) == ("gemma-y", "qwen-x")


def test_si_ollama_no_contesta_no_hay_lista_de_modelos() -> None:
    def contestar(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=request)

    with pytest.raises(OllamaNotAvailableError, match="Ollama"):
        list_installed_models(httpx.MockTransport(contestar))
