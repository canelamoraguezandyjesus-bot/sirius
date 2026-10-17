"""El juez no frena la voz (ADR-252).

El juez puntúa con el mismo modelo que la charla. Antes pedía con el tope de la charla,
4 096, aunque solo contesta una nota o una palabra, y un turno de voz que lo encontraba en
marcha esperaba a que acabara su petición entera. Ahora pide poco, y si un turno de voz lo
encuentra en marcha, corta su petición. Que no arranque mientras dura una charla de voz lo
mira la ventana (``tests/gui/test_escucha_en_la_ventana.py``).
"""

from __future__ import annotations

import contextlib
import json
import logging
import socket
import threading
from collections.abc import Iterable, Iterator
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from sirius.adapters.llm.ollama_chat import OllamaChatProvider
from sirius.adapters.llm.openai_responses import OpenAIResponsesProvider
from sirius.application.reply_judge import JudgeError, LLMReplyJudge
from sirius.application.robot_conversation import ReplyJudgeService
from sirius.domain.identity import Identity, IdentityVersion
from sirius.domain.reply_judge import JUDGE_MAX_OUTPUT_TOKENS, JudgeScore, TrickVerdict
from sirius.domain.robot_seed import ROBOT_SEED_EXAMPLES, ROBOT_SEED_INSTRUCTIONS
from sirius.ports.llm import (
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)
from sirius.presentation.reply_judge_worker import ReplyJudgeWorker


class _Identidades:
    """La identidad vigente, con la semilla de verdad: el juez la lleva delante."""

    def get_current_identity(self) -> Identity:
        version = IdentityVersion(
            id=1,
            identity_id=1,
            version=1,
            name="Sirius",
            description="El robot del propietario.",
            personality_instructions=ROBOT_SEED_INSTRUCTIONS,
            created_at=datetime(2026, 10, 17),
            examples=ROBOT_SEED_EXAMPLES,
        )
        return Identity(id=1, current_version=version, created_at=datetime(2026, 10, 17))


class _Modelo:
    """Contesta ``respuesta`` y apunta lo que le piden. Con ``espera``, no contesta hasta
    que le cortan o le sueltan, como una petición que Ollama aún está procesando."""

    model_name = "modelo-de-prueba"

    def __init__(self, *, espera: bool = False, respuesta: str = "4") -> None:
        self.peticiones: list[LLMRequest] = []
        self.cortadas: list[str] = []
        self.empezo = threading.Event()
        self._espera = espera
        self._respuesta = respuesta
        self._sigue = threading.Event()

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(request)
        self.empezo.set()
        if self._espera:
            assert self._sigue.wait(5), "nadie cortó ni soltó la petición"
            if request.operation_id in self.cortadas:
                yield LLMCancelled(partial_text="")
                return
        yield LLMCompleted(text=self._respuesta, input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        self.cortadas.append(operation_id)
        self._sigue.set()

    def suelta(self) -> None:
        self._sigue.set()


def _juez(modelo: _Modelo) -> LLMReplyJudge:
    return LLMReplyJudge(_Identidades(), lambda: modelo)  # type: ignore[arg-type]


def test_el_juez_pide_solo_lo_que_cabe_en_una_nota() -> None:
    modelo = _Modelo()

    assert _juez(modelo).score("Venga, jefe, al lío.") == 4

    [peticion] = modelo.peticiones
    assert peticion.max_output_tokens == JUDGE_MAX_OUTPUT_TOKENS
    # Cabe «Le doy un 4 de 5» y algo más; no cabe una respuesta de la charla.
    assert 16 <= JUDGE_MAX_OUTPUT_TOKENS <= 64
    # Un modelo que piensa se gastaría el tope pensando, sin llegar a la nota.
    assert peticion.may_think is False


def test_el_veredicto_tambien_pide_poco_y_sin_pensar() -> None:
    modelo = _Modelo(respuesta="discrepa")

    _juez(modelo).verdict("Voy a dejar el trabajo mañana.", "Ni de broma, jefe.")

    [peticion] = modelo.peticiones
    assert peticion.max_output_tokens == JUDGE_MAX_OUTPUT_TOKENS
    assert peticion.may_think is False


def test_cortar_al_juez_corta_la_peticion_que_tiene_en_marcha() -> None:
    modelo = _Modelo(espera=True)
    juez = _juez(modelo)
    fallo: list[BaseException] = []

    def puntua() -> None:
        try:
            juez.score("Venga, jefe, al lío.")
        except JudgeError as error:
            fallo.append(error)

    hilo = threading.Thread(target=puntua)
    hilo.start()
    assert modelo.empezo.wait(5)

    juez.cancel()
    hilo.join(5)

    assert not hilo.is_alive()
    assert modelo.cortadas == [modelo.peticiones[0].operation_id]
    # La respuesta se queda sin nota, como cuando el juez falla.
    assert len(fallo) == 1


def test_cortar_al_juez_mientras_prepara_la_nota_no_llega_a_preguntar() -> None:
    modelo = _Modelo()
    juez: LLMReplyJudge

    def el_corte_llega_mientras_lee_los_ajustes() -> _Modelo:
        juez.cancel()
        return modelo

    juez = LLMReplyJudge(_Identidades(), el_corte_llega_mientras_lee_los_ajustes)  # type: ignore[arg-type]

    with pytest.raises(JudgeError):
        juez.score("Venga, jefe, al lío.")

    assert modelo.peticiones == []


def test_cortar_al_juez_no_corta_las_preguntas_trampa() -> None:
    modelo = _Modelo(espera=True, respuesta="discrepa")
    juez = _juez(modelo)
    veredicto: list[TrickVerdict] = []
    hilo = threading.Thread(
        target=lambda: veredicto.append(juez.verdict("Voy a dejar el trabajo.", "Ni de broma."))
    )
    hilo.start()
    assert modelo.empezo.wait(5)

    juez.cancel()
    modelo.suelta()
    hilo.join(5)

    assert modelo.cortadas == []
    assert veredicto == [TrickVerdict.DISCREPA]


def test_cortar_al_juez_sin_nada_en_marcha_no_hace_nada() -> None:
    modelo = _Modelo()
    juez = _juez(modelo)

    juez.cancel()
    juez.score("Venga, jefe, al lío.")
    juez.cancel()

    assert modelo.cortadas == []


def test_parar_al_juez_de_la_ventana_corta_su_peticion() -> None:
    cortes: list[str] = []
    servicio = SimpleNamespace(
        judge_pending=lambda should_stop: False, cancel=lambda: cortes.append("cortado")
    )
    trabajo = ReplyJudgeWorker(servicio)  # type: ignore[arg-type]

    trabajo.stop()

    assert cortes == ["cortado"]


# --- Cada proveedor respeta el tope de la petición, sin pasar del suyo ---------------------


def _ollama(cuerpos: list[dict[str, Any]], num_predict: int) -> OllamaChatProvider:
    def contestar(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        fin = {"message": {"content": "4"}, "done": True}
        return httpx.Response(200, content=(json.dumps(fin) + "\n").encode())

    return OllamaChatProvider(
        "modelo-de-prueba", num_predict=num_predict, transport=httpx.MockTransport(contestar)
    )


@pytest.mark.parametrize(("tope_de_la_peticion", "pedido"), [(None, 4096), (32, 32), (9000, 4096)])
def test_ollama_pide_el_tope_menor_entre_el_suyo_y_el_de_la_peticion(
    tope_de_la_peticion: int | None, pedido: int
) -> None:
    cuerpos: list[dict[str, Any]] = []
    peticion = LLMRequest("op", "Instrucciones.", "Hola.", max_output_tokens=tope_de_la_peticion)

    list(_ollama(cuerpos, num_predict=4096).stream_response(peticion))

    assert cuerpos[0]["options"]["num_predict"] == pedido


def test_ollama_apaga_el_pensamiento_solo_si_la_peticion_lo_pide() -> None:
    cuerpos: list[dict[str, Any]] = []
    proveedor = _ollama(cuerpos, num_predict=4096)

    list(proveedor.stream_response(LLMRequest("op-1", "Instrucciones.", "Hola.", may_think=False)))
    list(proveedor.stream_response(LLMRequest("op-2", "Instrucciones.", "Hola.")))

    assert cuerpos[0]["think"] is False
    # La charla, como siempre, sin «think».
    assert "think" not in cuerpos[1]


class _Respuestas:
    def __init__(self) -> None:
        self.pedidos: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Iterator[Any]:
        self.pedidos.append(kwargs)
        return iter(())


@pytest.mark.parametrize(("tope_de_la_peticion", "pedido"), [(None, 4096), (32, 32), (9000, 4096)])
def test_openai_pide_el_tope_menor_entre_el_suyo_y_el_de_la_peticion(
    tope_de_la_peticion: int | None, pedido: int
) -> None:
    respuestas = _Respuestas()
    cliente = SimpleNamespace(responses=respuestas)
    proveedor = OpenAIResponsesProvider(cliente, "gpt-de-prueba", max_output_tokens=4096)  # type: ignore[arg-type]
    peticion = LLMRequest("op", "Instrucciones.", "Hola.", max_output_tokens=tope_de_la_peticion)

    list(proveedor.stream_response(peticion))

    assert respuestas.pedidos[0]["max_output_tokens"] == pedido


# --- Cortar es al momento, aunque Ollama aún no haya escrito nada ----------------------------


class _OllamaQueLee:
    """Un Ollama de mentira que recibe la pregunta y no contesta mientras «la lee», como el
    de verdad con una pregunta larga; con ``primer_trozo``, escribe uno y se queda ahí.

    Si el otro lado cuelga, lo apunta y cierra, como el de verdad, que deja de trabajar en
    esa pregunta en cuanto ve que se ha ido.
    """

    def __init__(self, *, primer_trozo: bool = False) -> None:
        self._servidor = socket.create_server(("127.0.0.1", 0))
        self.puerto: int = self._servidor.getsockname()[1]
        self.tiene_la_pregunta = threading.Event()
        self.colgaron = threading.Event()
        self._primer_trozo = primer_trozo
        threading.Thread(target=self._atiende, daemon=True).start()

    def _atiende(self) -> None:
        conexion, _ = self._servidor.accept()
        with conexion, self._servidor:
            leido = b""
            while b"\r\n\r\n" not in leido:
                leido += conexion.recv(65536)
            if self._primer_trozo:
                linea = json.dumps({"message": {"content": "Ho"}, "done": False}).encode()
                trozo = linea + b"\n"
                conexion.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/x-ndjson\r\n"
                    b"Transfer-Encoding: chunked\r\n\r\n"
                    + f"{len(trozo):x}\r\n".encode()
                    + trozo
                    + b"\r\n"
                )
            self.tiene_la_pregunta.set()
            with contextlib.suppress(OSError):
                while conexion.recv(65536):
                    pass
            self.colgaron.set()


class _AlOllamaDePrueba(httpx.HTTPTransport):
    """La conexión de verdad, pero al puerto del Ollama de mentira: la dirección del
    proveedor es fija."""

    def __init__(self, puerto: int) -> None:
        super().__init__()
        self._puerto = puerto

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.url = request.url.copy_with(host="127.0.0.1", port=self._puerto)
        return super().handle_request(request)


def _pide_en_otro_hilo(
    proveedor: OllamaChatProvider, peticion: LLMRequest
) -> tuple[threading.Thread, list[LLMStreamEvent], threading.Event]:
    eventos: list[LLMStreamEvent] = []
    primer_trozo = threading.Event()

    def pide() -> None:
        for evento in proveedor.stream_response(peticion):
            eventos.append(evento)
            if isinstance(evento, LLMTextDelta):
                primer_trozo.set()

    hilo = threading.Thread(target=pide, daemon=True)
    hilo.start()
    return hilo, eventos, primer_trozo


@pytest.mark.parametrize("primer_trozo", [False, True], ids=["leyendo", "escribiendo"])
def test_cortar_cuelga_la_peticion_sin_esperar_al_siguiente_trozo(primer_trozo: bool) -> None:
    ollama = _OllamaQueLee(primer_trozo=primer_trozo)
    proveedor = OllamaChatProvider("modelo-de-prueba", transport=_AlOllamaDePrueba(ollama.puerto))
    hilo, eventos, trozo = _pide_en_otro_hilo(
        proveedor, LLMRequest("op", "Instrucciones.", "Hola.")
    )
    assert ollama.tiene_la_pregunta.wait(5)
    if primer_trozo:
        assert trozo.wait(5)

    proveedor.cancel("op")
    hilo.join(5)

    # Sin colgar, esperaría al siguiente trozo, que no llega: hasta el tope de lectura.
    assert not hilo.is_alive()
    assert ollama.colgaron.wait(5)
    assert eventos[-1] == LLMCancelled(partial_text="Ho" if primer_trozo else "")


def test_un_fallo_de_red_sin_cortar_sigue_siendo_un_fallo() -> None:
    def se_cae(request: httpx.Request) -> httpx.Response:
        raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

    proveedor = OllamaChatProvider("modelo-de-prueba", transport=httpx.MockTransport(se_cae))

    [evento] = proveedor.stream_response(LLMRequest("op", "Instrucciones.", "Hola."))

    assert isinstance(evento, LLMError)


class _Notas:
    """Una respuesta sin nota, y ninguna nota todavía."""

    def __init__(self) -> None:
        self.guardadas: list[tuple[int, int]] = []

    def add_score(self, message_id: int, score: int, *, warned: bool) -> None:
        del warned
        self.guardadas.append((message_id, score))

    def judge_scores(self) -> list[JudgeScore]:
        return []

    def unjudged_replies(self) -> list[tuple[int, str]]:
        return [(1, "Venga, jefe, al lío.")]


def test_un_turno_de_voz_no_espera_a_la_peticion_del_juez(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ollama = _OllamaQueLee()
    proveedor = OllamaChatProvider("modelo-de-prueba", transport=_AlOllamaDePrueba(ollama.puerto))
    notas = _Notas()
    juez = LLMReplyJudge(_Identidades(), lambda: proveedor)  # type: ignore[arg-type]
    trabajo = ReplyJudgeWorker(ReplyJudgeService(juez, notas))
    hilo = threading.Thread(target=trabajo.run, daemon=True)
    hilo.start()
    assert ollama.tiene_la_pregunta.wait(5)

    # Lo que hace la ventana al empezar un turno de voz (begin_voice_turn).
    trabajo.stop()

    # El hilo del oído espera esto antes de entregar el turno.
    assert trabajo.done.wait(2)
    assert ollama.colgaron.wait(5)
    assert notas.guardadas == []
    # Cortarle no es un fallo del juez: el diario no lo apunta como tal.
    assert "no pudo puntuar" not in caplog.text


# --- Con un Ollama que no deja apagar el pensamiento ----------------------------------------


class _OllamaDeUnaManera:
    """Un Ollama de mentira que contesta ``respuesta``. Con ``rechaza_think``, a una
    petición que apaga el pensamiento le contesta 400, como contestaría uno que no deja
    apagarlo en un modelo que no piensa; si no, la acepta."""

    def __init__(self, *, rechaza_think: bool, respuesta: str = "4") -> None:
        self.cuerpos: list[dict[str, Any]] = []
        self._rechaza_think = rechaza_think
        self._respuesta = respuesta

    def transporte(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._contestar)

    def _contestar(self, request: httpx.Request) -> httpx.Response:
        cuerpo = json.loads(request.content)
        self.cuerpos.append(cuerpo)
        if self._rechaza_think and "think" in cuerpo:
            error = {"error": f'"{cuerpo["model"]}" does not support thinking'}
            return httpx.Response(400, json=error)
        fin = {"message": {"content": self._respuesta}, "done": True}
        return httpx.Response(200, content=(json.dumps(fin) + "\n").encode())


def _juez_con(ollama: _OllamaDeUnaManera) -> LLMReplyJudge:
    proveedor = OllamaChatProvider("gemma3:4b", transport=ollama.transporte())
    return LLMReplyJudge(_Identidades(), lambda: proveedor)  # type: ignore[arg-type]


def test_si_ollama_acepta_apagar_el_pensamiento_el_juez_pregunta_una_vez() -> None:
    # Una respuesta buena no se repite, aunque diga «think».
    ollama = _OllamaDeUnaManera(rechaza_think=False, respuesta="A 4, I think.")

    assert _juez_con(ollama).score("Venga, jefe, al lío.") == 4

    [cuerpo] = ollama.cuerpos
    assert cuerpo["think"] is False
    assert cuerpo["options"]["num_predict"] == JUDGE_MAX_OUTPUT_TOKENS


def test_si_ollama_no_deja_apagar_el_pensamiento_el_juez_pregunta_sin_apagarlo(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ollama = _OllamaDeUnaManera(rechaza_think=True)
    juez = _juez_con(ollama)

    with caplog.at_level(logging.INFO, logger="sirius"):
        assert juez.score("Venga, jefe, al lío.") == 4
        assert juez.score("Eso lo arreglamos en un momento.") == 4

    # El diario lo dice, sin nada de lo que dijo Ollama.
    assert "Ollama no deja apagar el pensamiento de gemma3:4b" in caplog.text
    assert "does not support" not in caplog.text

    # La primera vez lo repite sin apagarlo; después ya no lo apaga: no pierde una
    # petición por nota.
    assert ["think" in cuerpo for cuerpo in ollama.cuerpos] == [True, False, False]
    assert {cuerpo["options"]["num_predict"] for cuerpo in ollama.cuerpos} == {
        JUDGE_MAX_OUTPUT_TOKENS
    }


def test_las_preguntas_trampa_tambien_valen_con_un_ollama_que_no_deja_apagarlo() -> None:
    ollama = _OllamaDeUnaManera(rechaza_think=True, respuesta="discrepa")

    veredicto = _juez_con(ollama).verdict("Voy a dejar el trabajo mañana.", "Ni de broma.")

    assert veredicto is TrickVerdict.DISCREPA


def test_un_400_por_otra_cosa_no_se_repite() -> None:
    cuerpos: list[dict[str, Any]] = []

    def rechaza(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        return httpx.Response(400, json={"error": '"qwen3:4b-thinking" does not support chat'})

    proveedor = OllamaChatProvider("qwen3:4b-thinking", transport=httpx.MockTransport(rechaza))
    juez = LLMReplyJudge(_Identidades(), lambda: proveedor)  # type: ignore[arg-type]

    with pytest.raises(JudgeError):
        juez.score("Venga, jefe, al lío.")

    # Ni el nombre del modelo, que lleva la palabra, lo confunde con un rechazo de think.
    assert len(cuerpos) == 1


def test_la_charla_no_lleva_think_ni_con_un_ollama_que_no_lo_deja_apagar() -> None:
    ollama = _OllamaDeUnaManera(rechaza_think=True, respuesta="Hola, jefe.")
    proveedor = OllamaChatProvider("gemma3:4b", transport=ollama.transporte())

    eventos = list(proveedor.stream_response(LLMRequest("op", "Instrucciones.", "Hola.")))

    assert isinstance(eventos[-1], LLMCompleted)
    [cuerpo] = ollama.cuerpos
    assert "think" not in cuerpo
    assert cuerpo["options"]["num_predict"] == 4096
