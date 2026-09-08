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
from datetime import UTC, datetime
from unittest import mock

import httpx
import pytest

from sirius.adapters import ollama_query_intent_classifier
from sirius.adapters.ollama_query_intent_classifier import (
    OllamaQueryIntentClassifierAdapter,
    instante_utc,
)
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
    # Los dos instantes salen canonizados, no verbatim: el objetivo a UTC
    # con desfase explícito, y el corte al final del día que nombra y en la
    # forma de ``created_at`` (encabezado del módulo del adaptador).
    assert intencion.tiempo_objetivo == "2026-03-20T00:00:00+00:00"
    assert intencion.corte_de_registro == "2026-03-01 23:59:59.999999"


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
    assert intencion.tiempo_objetivo == "2026-03-20T00:00:00+00:00"


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


# --------------------------------------------------------------------------
# El instante emitido es comparable, no solo válido (ADR-164, incidencia #570)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "escritura",
    ["2026-03-01", "2026-03-01T00:00:00Z", "2026-03-01 00:00:00"],
)
def test_las_tres_escrituras_del_mismo_dia_dan_el_mismo_corte(escritura: str) -> None:
    """``_PATRON_ISO`` admite tres formas del mismo día y ``G8`` compara el
    corte con ``created_at`` por orden lexicográfico, donde el separador
    manda (``" "`` < ``"T"``). Sin canonizar, la forma que el modelo eligiera
    esa vez decidiría por accidente si el día del corte entra o no."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer(corte_de_registro=escritura)

    intencion = _adapter(httpx.MockTransport(_handle)).classify_intent(
        "¿qué sabía yo el 1 de marzo?"
    )

    assert intencion is not None
    assert intencion.corte_de_registro == "2026-03-01 23:59:59.999999"


def test_el_corte_canonizado_admite_lo_registrado_durante_el_dia_del_corte() -> None:
    """La semántica declarada: «¿qué sabía yo el D?» es lo registrado AL
    FINAL de D. Un ``created_at`` del propio día D —la forma con que el
    canon lo persiste, ``str(datetime)`` con separador espacio— tiene que
    quedar por debajo del corte en el orden lexicográfico que ``G8`` usa."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer(corte_de_registro="2026-03-01")

    intencion = _adapter(httpx.MockTransport(_handle)).classify_intent(
        "¿qué sabía yo el 1 de marzo?"
    )

    assert intencion is not None
    corte = intencion.corte_de_registro
    assert corte is not None
    assert corte > "2026-03-01 14:22:03.123456"
    assert corte < "2026-03-02 00:00:00.000000"


@pytest.mark.parametrize(
    "escritura",
    ["2026-03-20", "2026-03-20T00:00:00Z", "2026-03-20 00:00:00", "2026-03-20T02:00:00+02:00"],
)
def test_el_tiempo_objetivo_sale_en_utc_con_desfase_explicito(escritura: str) -> None:
    """``G8`` compara el objetivo con ``valid_from``/``valid_to``, que son
    ISO-8601 con zona. Una fecha desnuda es su medianoche: es un instante,
    no un día."""

    def _handle(request: httpx.Request) -> httpx.Response:
        return _answer(tiempo_objetivo=escritura)

    intencion = _adapter(httpx.MockTransport(_handle)).classify_intent("pregunta")

    assert intencion is not None
    assert intencion.tiempo_objetivo == "2026-03-20T00:00:00+00:00"


@pytest.mark.parametrize(
    "escritura",
    ["2026-03-01T00:00:00Z", "2026-03-01T00:00:00+00:00", "2026-03-01 00:00:00"],
)
def test_instante_utc_lee_el_mismo_instante_escrito_de_tres_formas(escritura: str) -> None:
    """La normalización que la medición del banco comparte
    (``scripts/medir_interprete_de_peticion.py::_instante``): sin asumir UTC
    para un valor sin zona, comparar ingenuo con consciente por ``!=`` no
    lanza, da siempre «distintos», y un instante idéntico se puntúa como
    fallo en los casos con tiempo declarado."""
    assert instante_utc(escritura) == datetime(2026, 3, 1, tzinfo=UTC)


def test_instante_utc_devuelve_none_ante_lo_que_no_es_iso() -> None:
    assert instante_utc(None) is None
    assert instante_utc("ayer") is None


def test_el_hoy_de_la_instruccion_se_resuelve_en_cada_consulta() -> None:
    """El adaptador se construye una sola vez por arranque
    (``composition_root.build_conversation_dependencies``) y Sirius es una
    aplicación de escritorio que se deja abierta durante días: con el «hoy»
    congelado en el constructor, «¿qué decidí ayer?» quedaría anclada al día
    del arranque y el desfase crecería en silencio."""
    instrucciones: list[str] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        cuerpo = json.loads(request.content.decode("utf-8"))
        instrucciones.append(cuerpo["messages"][0]["content"])
        return _answer()

    client = httpx.Client(transport=httpx.MockTransport(_handle), base_url="http://localhost:11434")
    adaptador = OllamaQueryIntentClassifierAdapter("qwen3:4b-instruct", client=client)

    dias = iter([datetime(2026, 3, 1, 9, tzinfo=UTC), datetime(2026, 3, 2, 9, tzinfo=UTC)])

    class _CalendarioFalso:
        @staticmethod
        def now(zona: object = None) -> datetime:
            return next(dias)

    with mock.patch.object(ollama_query_intent_classifier, "datetime", _CalendarioFalso):
        adaptador.classify_intent("¿qué decidí ayer?")
        adaptador.classify_intent("¿qué decidí ayer?")

    assert "Hoy es 2026-03-01." in instrucciones[0]
    assert "Hoy es 2026-03-02." in instrucciones[1]


def test_un_ahora_fijado_por_el_llamador_se_respeta_en_cada_consulta() -> None:
    """La medición del banco fija su ``ahora_declarado``: resolver el «hoy»
    por llamada no puede pisarlo."""
    instrucciones: list[str] = []

    def _handle(request: httpx.Request) -> httpx.Response:
        cuerpo = json.loads(request.content.decode("utf-8"))
        instrucciones.append(cuerpo["messages"][0]["content"])
        return _answer()

    adaptador = _adapter(httpx.MockTransport(_handle))
    adaptador.classify_intent("pregunta")
    adaptador.classify_intent("otra pregunta")

    assert all("Hoy es 2026-06-15." in instruccion for instruccion in instrucciones)
