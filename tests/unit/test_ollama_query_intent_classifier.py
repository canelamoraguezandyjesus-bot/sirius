"""Pruebas del ``OllamaQueryIntentClassifierAdapter`` (ADR-164, palanca 1 de
ADR-148).

Nunca toca un Ollama real: ``httpx.MockTransport`` sustituye al extremo HTTP
local, entero dentro del proceso. Fija las mismas tres cosas que sus dos
gemelos ya corregidos (``test_ollama_category_classifier.py``,
``test_ollama_criticality_classifier.py``):

- el contrato de fallo abierto que ``QueryIntentClassifierPort`` exige: una
  respuesta dentro del vocabulario cerrado se devuelve tal cual; cualquier
  otra cosa (conexión rechazada, tiempo agotado, respuesta mal formada, error
  del servidor, un modo fuera de ``M1``-``M5``) es ``None``, nunca una
  excepción;
- el contrato HTTP validado contra el modelo local real (ADR-125):
  ``/api/chat`` con ``think: false`` y un ``format`` cerrado, afirmado
  literalmente sobre el cuerpo de la petición;
- la propiedad estructural de §6.3 a nivel de petición: ni el ``base_url``
  remoto de un cliente inyectado ni una redirección desde localhost mueven la
  consulta fuera de la máquina.
"""

from __future__ import annotations

import inspect
import json

import httpx

from sirius.adapters.ollama_query_intent_classifier import OllamaQueryIntentClassifierAdapter
from sirius.domain.staged_engine_contracts import Cardinalidad, Modo


def _adapter(handler: httpx.MockTransport) -> OllamaQueryIntentClassifierAdapter:
    client = httpx.Client(transport=handler, base_url="http://localhost:11434")
    return OllamaQueryIntentClassifierAdapter(
        "qwen3:4b-instruct", ahora="2026-06-15", client=client
    )


def _answer(**campos: object) -> httpx.Response:
    """Una respuesta de ``/api/chat`` constreñida por el esquema cerrado."""
    cuerpo: dict[str, object] = {
        "modo": "M1",
        "cardinalidad": "EXHAUSTIVA",
        "limite": 0,
        "tiempo_objetivo": "",
        "corte_de_registro": "",
    }
    cuerpo.update(campos)
    return httpx.Response(200, json={"message": {"content": json.dumps(cuerpo)}})


def test_devuelve_la_intencion_que_el_modelo_contesta() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer(
            modo="M2",
            cardinalidad="ACOTADA",
            limite=3,
            tiempo_objetivo="2026-03-20T00:00:00Z",
            corte_de_registro="2026-03-01T00:00:00Z",
        )

    intencion = _adapter(httpx.MockTransport(_handle)).classify_intent("¿qué usábamos antes?")

    assert intencion is not None
    assert intencion.modo is Modo.M2_HISTORICO
    assert intencion.cardinalidad is Cardinalidad.ACOTADA
    assert intencion.limite == 3
    assert intencion.tiempo_objetivo == "2026-03-20T00:00:00Z"
    assert intencion.corte_de_registro == "2026-03-01T00:00:00Z"


def test_la_cadena_vacia_es_no_declarado_y_no_una_fecha_rota() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer(tiempo_objetivo="", corte_de_registro="", limite=0)

    intencion = _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta corriente")

    assert intencion is not None
    assert intencion.tiempo_objetivo is None
    assert intencion.corte_de_registro is None
    assert intencion.limite is None


def test_una_fecha_que_no_es_iso_se_descarta_en_vez_de_llegar_a_g8() -> None:
    """``G8`` compara la fecha con ``created_at`` por orden lexicográfico
    (``src/sirius/domain/staged_engine_gates.py``): una cadena arbitraria
    podría excluir el canon entero en silencio. Se trata como no declarada."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer(tiempo_objetivo="el mes pasado", corte_de_registro="ayer")

    intencion = _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta")

    assert intencion is not None
    assert intencion.tiempo_objetivo is None
    assert intencion.corte_de_registro is None


def test_un_intervalo_se_resuelve_por_su_extremo_final() -> None:
    """La misma traducción que el traductor del banco declara
    (``staged_engine_case_translation._instante``)."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer(tiempo_objetivo="2026-01-10T00:00:00Z/2026-03-20T00:00:00Z")

    intencion = _adapter(httpx.MockTransport(_handle)).classify_intent("entre enero y marzo")

    assert intencion is not None
    assert intencion.tiempo_objetivo == "2026-03-20T00:00:00Z"


def test_un_modo_fuera_de_m1_m5_devuelve_none() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer(modo="M9")

    assert _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta") is None


def test_una_cardinalidad_fuera_del_vocabulario_devuelve_none() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer(cardinalidad="TODAS")

    assert _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta") is None


def test_prosa_en_vez_del_esquema_devuelve_none() -> None:
    """Lo que arriesgaba el viejo ``/api/generate`` sin ``think: false`` ni
    ``format`` cerrado (ADR-125): prosa alrededor de la respuesta."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"message": {"content": "Creo que el modo es M1 porque..."}}
        )

    assert _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta") is None


def test_conexion_rechazada_devuelve_none() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    assert _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta") is None


def test_tiempo_agotado_devuelve_none() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    assert _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta") is None


def test_error_del_servidor_devuelve_none() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model not found"})

    assert _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta") is None


def test_respuesta_mal_formada_devuelve_none() -> None:
    def _handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    assert _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta") is None


def test_envia_el_contrato_validado_contra_el_modelo_real() -> None:
    seen: list[httpx.Request] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _answer()

    _adapter(httpx.MockTransport(_handle)).classify_intent("¿qué formato de informe uso?")

    assert len(seen) == 1
    peticion = seen[0]
    assert peticion.method == "POST"
    assert peticion.url.host == "localhost"
    assert peticion.url.path == "/api/chat"
    cuerpo = json.loads(peticion.content)
    assert cuerpo["model"] == "qwen3:4b-instruct"
    assert cuerpo["stream"] is False
    assert cuerpo["think"] is False
    assert cuerpo["keep_alive"] == "15m"
    assert cuerpo["options"] == {"temperature": 0.1, "num_ctx": 8192}
    assert cuerpo["format"] == {
        "type": "object",
        "properties": {
            "modo": {"type": "string", "enum": ["M1", "M2", "M3", "M4", "M5"]},
            "cardinalidad": {
                "type": "string",
                "enum": ["EXACTA", "ACOTADA", "EXHAUSTIVA"],
            },
            "limite": {"type": "integer"},
            "tiempo_objetivo": {"type": "string"},
            "corte_de_registro": {"type": "string"},
        },
        "required": ["modo", "cardinalidad", "limite", "tiempo_objetivo", "corte_de_registro"],
    }
    assert [m["role"] for m in cuerpo["messages"]] == ["system", "user"]
    assert cuerpo["messages"][1]["content"] == "¿qué formato de informe uso?"
    assert "2026-06-15" in cuerpo["messages"][0]["content"]


def test_el_esquema_no_pide_nunca_permiso_ni_proposito() -> None:
    """El permiso gobierna qué se puede mirar: no se le pregunta al modelo,
    ni siquiera de forma que su respuesta pudiera colarse (ADR-164)."""
    seen: list[httpx.Request] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _answer()

    _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta")

    cuerpo = json.loads(seen[0].content)
    propiedades = cuerpo["format"]["properties"]
    assert "permiso" not in propiedades
    assert "proposito" not in propiedades


def test_ningun_parametro_permite_apuntar_a_un_host_remoto() -> None:
    signature = inspect.signature(OllamaQueryIntentClassifierAdapter.__init__)
    assert "host" not in signature.parameters
    assert "url" not in signature.parameters
    assert "base_url" not in signature.parameters


def test_ignora_el_base_url_remoto_de_un_cliente_inyectado() -> None:
    seen_hosts: list[str | None] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        return _answer()

    client = httpx.Client(
        transport=httpx.MockTransport(_handle), base_url="https://servidor-remoto.example"
    )
    adapter = OllamaQueryIntentClassifierAdapter("qwen3:4b-instruct", client=client)

    intencion = adapter.classify_intent("pregunta")

    assert seen_hosts == ["localhost"]
    assert intencion is not None


def test_nunca_sigue_una_redireccion_a_un_host_remoto() -> None:
    """Un cliente inyectado con ``follow_redirects=True`` no debe permitir
    que un 307/308 desde localhost reenvíe la consulta a un host remoto. Se
    afirma sobre los hosts que vio el transporte: el valor devuelto es
    ``None`` en el camino correcto y en el roto, así que no los distingue."""
    seen_hosts: list[str | None] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        seen_hosts.append(request.url.host)
        return httpx.Response(
            307,
            headers={"Location": "https://remote.example/leak"},
            json={"message": {"content": "{}"}},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(_handle),
        base_url="http://localhost:11434",
        follow_redirects=True,
    )
    adapter = OllamaQueryIntentClassifierAdapter("qwen3:4b-instruct", client=client)

    assert adapter.classify_intent("pregunta") is None
    assert seen_hosts == ["localhost"]
