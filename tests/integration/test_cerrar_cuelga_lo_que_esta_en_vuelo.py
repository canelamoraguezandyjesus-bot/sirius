"""Cerrar Sirius cuelga lo que está pidiendo por la red, sea del trabajo que sea (ADR-255).

Cada prueba pide algo de verdad, por un socket, a un servidor que acepta la conexión y no
contesta nunca: sin colgar, la petición esperaría su tope, de 30 s a 600 s según el
trabajo. Con la fábrica de ``sirius.infrastructure.network``, el cierre la corta en el acto.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import openai
import pytest
from servidor_mudo import ServidorMudo as _Mudo
from servidor_mudo import quita_los_proxies

import sirius.adapters.ollama_criticality_classifier as criticidad
from sirius.adapters.capture.websocket_client import TimeoutWebSocketError, WebSocketClient
from sirius.adapters.llm.ollama_chat import OllamaChatProvider
from sirius.adapters.llm.ollama_embeddings import OllamaEmbedder
from sirius.adapters.ollama_criticality_classifier import OllamaCriticalityClassifierAdapter
from sirius.infrastructure import network
from sirius.infrastructure.network import (
    ConnectionRegistry,
    hang_up_all,
    http_client,
    openai_client,
)
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.llm import LLMCancelled, LLMRequest

pytestmark = pytest.mark.integration

#: Lo que puede tardar en acabar una petición desde que se cuelga.
_EN_EL_ACTO = 0.1


class _Redirige(httpx.BaseTransport):
    """Un transporte de verdad que manda al servidor mudo lo que iba a Ollama: la petición
    abre una conexión real, que se puede colgar."""

    def __init__(self, puerto: int) -> None:
        self._dentro = httpx.HTTPTransport()
        self._puerto = puerto

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.url = request.url.copy_with(host="127.0.0.1", port=self._puerto)
        return self._dentro.handle_request(request)

    def close(self) -> None:
        self._dentro.close()


@pytest.fixture
def mudo() -> Iterator[_Mudo]:
    servidor = _Mudo()
    yield servidor
    servidor.cierra()


@pytest.fixture
def sin_proxies(monkeypatch: pytest.MonkeyPatch) -> None:
    """El SDK de OpenAI lee los proxies del sistema: aquí no, que el servidor es local."""
    quita_los_proxies(monkeypatch)


def _lo_que_tarda_tras_colgar(
    mudo: _Mudo,
    pide: Callable[[], object],
    cuelga: Callable[[], object] = hang_up_all,
    *,
    conectada: threading.Event | None = None,
    sigue: Callable[[], object] = lambda: None,
) -> tuple[float, Exception | None]:
    """Lanza ``pide`` en otro hilo, espera a que tenga su conexión con el servidor mudo,
    cuelga, y devuelve cuánto tardó en acabar desde entonces y con qué fallo, si falló.

    Con ``conectada``, espera a ella en vez de a la conexión, y tras colgar llama a
    ``sigue``: así se cuelga con la conexión aún abriéndose.
    """
    acabo: list[float] = []
    fallo: list[Exception] = []

    def corre() -> None:
        try:
            pide()
        except Exception as error:  # cada adaptador falla a su manera
            fallo.append(error)
        acabo.append(time.perf_counter())

    hilo = threading.Thread(target=corre, daemon=True)
    hilo.start()
    if conectada is None:
        limite = time.perf_counter() + 5
        while not mudo.aceptadas and time.perf_counter() < limite:
            time.sleep(0.01)
        assert mudo.aceptadas, "la petición no llegó a conectar con el servidor mudo"
    else:
        assert conectada.wait(timeout=5), "la petición no llegó a abrir su conexión"
    time.sleep(0.1)
    assert hilo.is_alive(), "acabó sola: el servidor mudo tenía que dejarla esperando"
    colgada = time.perf_counter()
    cuelga()
    sigue()
    hilo.join(timeout=3)
    assert not hilo.is_alive(), "colgar no la cortó: seguiría hasta su tope"
    return acabo[0] - colgada, (fallo[0] if fallo else None)


def test_cerrar_corta_la_peticion_de_huellas_en_vuelo(mudo: _Mudo) -> None:
    """Ronda 2 de Codex sobre la #698: el cierre solo ponía una bandera que se miraba entre
    grupos, y el ``/api/embed`` en curso seguía hasta su tope de 60 s."""
    huellas = OllamaEmbedder(
        "modelo-de-huellas", transport=_Redirige(mudo.puerto), timeout=httpx.Timeout(30.0)
    )

    tarda, fallo = _lo_que_tarda_tras_colgar(mudo, lambda: huellas.embed(["hola"]))

    assert tarda < _EN_EL_ACTO
    assert isinstance(fallo, EmbeddingError)


def test_cerrar_corta_la_propuesta_de_criticidad_en_vuelo(
    mudo: _Mudo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ronda 2 de Codex sobre la #698: no tenía cómo cortarse, y su tope es de 30 s. Se
    prueba el cliente que construye el adaptador, con la fábrica de verdad: solo se le pone
    el transporte que lleva al servidor mudo."""
    fabrica = network.http_client
    monkeypatch.setattr(
        criticidad,
        "http_client",
        lambda **ajustes: fabrica(transport=_Redirige(mudo.puerto), **ajustes),
    )
    clasificador = OllamaCriticalityClassifierAdapter("modelo-local")

    tarda, _ = _lo_que_tarda_tras_colgar(mudo, lambda: clasificador.propose("x"))

    assert tarda < _EN_EL_ACTO


def test_cerrar_corta_una_peticion_del_sdk_de_openai_en_vuelo(
    mudo: _Mudo, sin_proxies: None
) -> None:
    """Ronda 2 de Codex sobre la #698: la voz de Model Studio va por el SDK de OpenAI, con
    su tope de 600 s. Todos sus clientes salen de ``openai_client``."""
    cliente = openai_client(
        api_key="sk-de-mentira", base_url=f"http://127.0.0.1:{mudo.puerto}/v1", max_retries=0
    )

    tarda, fallo = _lo_que_tarda_tras_colgar(mudo, cliente.models.list)

    assert tarda < _EN_EL_ACTO
    assert isinstance(fallo, openai.APIConnectionError)


def test_colgar_no_pisa_el_corte_de_la_charla(mudo: _Mudo) -> None:
    """La charla cuelga su conexión al cortarla con su propio ``trace`` (ADR-252): el de la
    fábrica va con él, no en su lugar."""
    charla = OllamaChatProvider("modelo-local", transport=_Redirige(mudo.puerto))
    peticion = LLMRequest(operation_id="op-1", instructions="", input_text="hola")
    eventos: list[object] = []

    def pide() -> None:
        eventos.extend(charla.stream_response(peticion))

    tarda, _ = _lo_que_tarda_tras_colgar(mudo, pide, cuelga=lambda: charla.cancel("op-1"))

    assert tarda < _EN_EL_ACTO
    assert isinstance(eventos[-1], LLMCancelled)


def test_al_salir_lo_que_conecta_despues_se_cuelga_en_el_acto(mudo: _Mudo) -> None:
    """Salir de Sirius cuelga también lo que se abra después: un trabajo que aún no había
    llegado a conectar. Con un registro propio, para no dejar sin red a las demás pruebas."""
    registro = ConnectionRegistry()
    cliente = http_client(
        registry=registro,
        transport=_Redirige(mudo.puerto),
        timeout=httpx.Timeout(30.0),
        trust_env=False,
    )
    registro.hang_up_all(final=True)

    empieza = time.perf_counter()
    with pytest.raises(httpx.HTTPError):
        cliente.get("http://127.0.0.1:11434/api/tags")

    assert time.perf_counter() - empieza < _EN_EL_ACTO


def test_al_pedir_cerrar_cuelga_la_conexion_que_aun_se_estaba_abriendo(mudo: _Mudo) -> None:
    """Ronda 4 de Codex sobre la #698: una conexión que se estaba abriendo al pedir cerrar,
    en el DNS o en ``connect_tcp``, aún no estaba apuntada, y colgar no la cortaba: seguía
    hasta su tope. Mientras la ventana se cierra, se cuelga en cuanto acaba de abrirse."""
    registro = ConnectionRegistry()
    cliente = http_client(
        registry=registro,
        transport=_Redirige(mudo.puerto),
        timeout=httpx.Timeout(30.0),
        trust_env=False,
    )
    abriendose = threading.Event()
    sigue = threading.Event()

    def a_medio_abrir(evento: str, info: dict[str, object]) -> None:
        if evento == "connection.connect_tcp.started":
            abriendose.set()
            sigue.wait(timeout=5)

    def pide() -> None:
        cliente.get("http://127.0.0.1:11434/api/tags", extensions={"trace": a_medio_abrir})

    try:
        tarda, fallo = _lo_que_tarda_tras_colgar(
            mudo, pide, cuelga=registro.begin_close, conectada=abriendose, sigue=sigue.set
        )
    finally:
        sigue.set()

    assert tarda < _EN_EL_ACTO
    assert isinstance(fallo, httpx.HTTPError)


def test_al_cerrarse_de_verdad_la_ventana_no_cuelga_lo_que_conecta_despues(
    mudo: _Mudo,
) -> None:
    """Tras cerrarse de verdad una ventana puede abrirse otra con las mismas dependencias, al
    cambiar de proyecto: lo que se abra después no se cuelga."""
    registro = ConnectionRegistry()
    cliente = http_client(
        registry=registro,
        transport=_Redirige(mudo.puerto),
        timeout=httpx.Timeout(0.3),
        trust_env=False,
    )
    registro.begin_close()
    registro.end_close()

    with pytest.raises(httpx.ReadTimeout):
        cliente.get("http://127.0.0.1:11434/api/tags")


def test_colgar_no_corta_la_orden_de_captura(mudo: _Mudo) -> None:
    """La orden de captura no se cuelga: su WebSocket no es de la fábrica, y el cierre la
    espera para saber cómo quedó la grabación (ADR-255). Ahora se cuelga al pedir cerrar,
    antes de esperarla (ronda 3 de Codex sobre la #698): sigue sin tocarla."""
    captura = WebSocketClient("127.0.0.1", mudo.puerto, timeout_seconds=1.0)
    fallo: list[Exception] = []

    def conecta() -> None:
        try:
            captura.connect()
        except Exception as error:  # el servidor mudo no saluda: acaba por su tope
            fallo.append(error)

    hilo = threading.Thread(target=conecta, daemon=True)
    hilo.start()
    limite = time.perf_counter() + 5
    while not mudo.aceptadas and time.perf_counter() < limite:
        time.sleep(0.01)
    assert mudo.aceptadas, "la orden no llegó a conectar con el servidor mudo"

    hang_up_all()
    time.sleep(0.3)

    assert hilo.is_alive(), "colgar cortó la orden de captura, que tenía que esperarse"
    hilo.join(timeout=3)
    assert isinstance(fallo[0], TimeoutWebSocketError)


_SALIR = """
import sys, time
from types import SimpleNamespace

import httpx
from PySide6.QtCore import QRunnable, QThreadPool, QTimer
from PySide6.QtWidgets import QApplication

from sirius.adapters.llm.ollama_embeddings import OllamaEmbedder
from sirius.main import _release_on_quit

puerto = int(sys.argv[1])


class Redirige(httpx.BaseTransport):
    def __init__(self):
        self._dentro = httpx.HTTPTransport()

    def handle_request(self, request):
        request.url = request.url.copy_with(host="127.0.0.1", port=puerto)
        return self._dentro.handle_request(request)


class Huellas(QRunnable):
    def run(self):
        huellas = OllamaEmbedder("m", transport=Redirige(), timeout=httpx.Timeout(8.0))
        try:
            huellas.embed(["hola"])
        except Exception:
            pass


app = QApplication([])
_release_on_quit(app, SimpleNamespace(local_listening=SimpleNamespace(close=lambda: None)))


def sal():
    print(time.time(), flush=True)
    app.quit()


QThreadPool.globalInstance().start(Huellas())
QTimer.singleShot(700, sal)
sys.exit(app.exec())
"""


def test_salir_de_sirius_no_espera_a_unas_huellas_colgadas(mudo: _Mudo, tmp_path: Path) -> None:
    """La medida de la #699: con el ``sys.exit(app.exec())`` de Sirius, el proceso no salía
    hasta que acababa el trabajador del pool. Con unas huellas colgadas, su tope; aquí, 8 s.
    """
    guion = tmp_path / "salir.py"
    guion.write_text(_SALIR, encoding="utf-8")
    entorno = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join(sys.path),
        QT_QPA_PLATFORM="offscreen",
        PYTHONDONTWRITEBYTECODE="1",
    )
    errores = tmp_path / "errores.txt"
    with errores.open("w", encoding="utf-8") as salida_de_errores:
        proceso = subprocess.Popen(
            [sys.executable, str(guion), str(mudo.puerto)],
            stdout=subprocess.PIPE,
            stderr=salida_de_errores,
            env=entorno,
            text=True,
        )
        assert proceso.stdout is not None
        linea = proceso.stdout.readline()
        proceso.wait(timeout=30)
        tardo = time.time() - float(linea) if linea.strip() else None

    assert proceso.returncode == 0, errores.read_text(encoding="utf-8")[-2000:]
    assert tardo is not None
    assert mudo.aceptadas, "las huellas tenían que estar esperando al servidor mudo"
    # Medido: 0,47 s con el arreglo y 7,80 s sin él; el margen es para la máquina cargada.
    assert tardo < 2, f"salir esperó {tardo:.2f} s a las huellas colgadas"
