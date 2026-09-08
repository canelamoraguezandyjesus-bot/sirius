"""Adaptador local-only de Ollama para inferir la intención de la consulta
(ADR-164, palanca 1 de ADR-148).

Tercer adaptador con la misma forma estructural que §6.3 exige del filtro de
relevancia y que ``OllamaCategoryClassifierAdapter``/
``OllamaCriticalityClassifierAdapter`` ya tienen: apunta exclusivamente a
``localhost``, sin ningún parámetro de constructor que pueda redirigirlo a un
host remoto, y **falla abierto** ante cualquier problema —Ollama no
instalado, conexión rechazada, tiempo agotado, o una respuesta fuera del
vocabulario cerrado— devolviendo ``None``, nunca lanzando.

El contrato HTTP es el que este repositorio ya validó contra el modelo local
real (ADR-125): ``/api/chat`` con el razonamiento explícitamente apagado
(``think: false``), un esquema JSON cerrado para la respuesta (``format``),
temperatura baja y ``keep_alive`` — no ``/api/generate`` con texto libre, que
con el Qwen3 por defecto razona durante minutos y contesta fuera del
vocabulario. La petición va a una URL absoluta de localhost con
``follow_redirects=False`` por la misma razón que los otros tres: ni el
``base_url`` de un cliente inyectado ni un 307/308 desde localhost pueden
llevar la consulta del usuario fuera de la máquina.

Qué se le pide al modelo, y qué NO
==================================

Se le piden los cuatro ejes que dependen de entender la frase: **modo**
(``M1``-``M5``), **cardinalidad** (``EXACTA``/``ACOTADA``/``EXHAUSTIVA``),
**límite** («dame tres…») y **tiempo** (instante al que se refiere la
pregunta y corte de registro, «qué sabía yo el …»). No se le pide el permiso
ni el propósito: son reglas del producto (``InterpreteDePeticion``), y el
permiso gobierna qué se puede mirar.

Las fechas se le piden en ISO-8601 y se validan aquí con un patrón: una
fecha que no case se descarta como si el modelo no la hubiera declarado
—``None``, «la pregunta no lo dice»—, en vez de viajar a ``G8``, donde una
cadena arbitraria se compara con ``created_at`` por orden lexicográfico y
podría excluir el canon entero en silencio. El «hoy» que el modelo necesita
para resolver una fecha relativa se le da en la instrucción; el llamador
puede fijarlo (la medición del banco usa su ``ahora_declarado``).
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

import httpx

from sirius.domain.query_intent import IntencionDeConsulta
from sirius.domain.staged_engine_contracts import Cardinalidad, Modo
from sirius.infrastructure.logging import get_logger

__all__ = ["OllamaQueryIntentClassifierAdapter"]

_logger = get_logger(__name__)

_OLLAMA_LOCAL_BASE_URL = "http://localhost:11434"
#: Mismo techo que los otros dos clasificadores locales (ADR-125).
_REQUEST_TIMEOUT_SECONDS = 30.0

#: Razonamiento apagado: con él encendido, el Qwen3 por defecto tarda minutos
#: en contestar a una pregunta de una palabra (ADR-125).
_PENSAMIENTO_APAGADO = False
_TEMPERATURA = 0.1
_TAMANO_DE_CONTEXTO = 8192
_PERMANENCIA_DEL_MODELO = "15m"

#: Cadena que el esquema usa para «la pregunta no lo declara». El esquema
#: cerrado de Ollama no admite bien un tipo nulo, así que la ausencia se pide
#: como cadena vacía y se traduce aquí.
_SIN_DECLARAR = ""

#: ISO-8601 de fecha o de instante. Deliberadamente estricto: lo que no case
#: se trata como no declarado (ver el encabezado del módulo).
_PATRON_ISO = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)

_MODOS = tuple(modo.value for modo in Modo)
_CARDINALIDADES = tuple(cardinalidad.value for cardinalidad in Cardinalidad)

_ESQUEMA_RESPUESTA: dict[str, object] = {
    "type": "object",
    "properties": {
        "modo": {"type": "string", "enum": list(_MODOS)},
        "cardinalidad": {"type": "string", "enum": list(_CARDINALIDADES)},
        "limite": {"type": "integer"},
        "tiempo_objetivo": {"type": "string"},
        "corte_de_registro": {"type": "string"},
    },
    "required": ["modo", "cardinalidad", "limite", "tiempo_objetivo", "corte_de_registro"],
}

_INSTRUCCION = """\
Eres el intérprete de preguntas de una memoria personal. Analiza la pregunta \
del usuario y devuelve, en el formato pedido y sin explicaciones, cómo hay \
que consultar la memoria. Hoy es {ahora}.

modo:
- M1: responder ahora con lo que está vigente. Es el modo por defecto.
- M2: revisar el historial, lo que se decidió o se usaba ANTES, lo ya \
sustituido o archivado.
- M3: verificar de dónde viene algo, quién lo dijo o en qué se apoya.
- M4: administrar la propia memoria (qué hay guardado, borrar, corregir).
- M5: revisar una contradicción entre dos cosas recordadas.

cardinalidad:
- EXACTA: la pregunta busca un dato concreto («¿qué formato de informe uso?»).
- ACOTADA: la pregunta pide una cantidad concreta («dame las tres…»).
- EXHAUSTIVA: la pregunta pide todo lo que haya de un tema («¿qué \
restricciones tengo?»).

limite: el número de elementos que la pregunta pide explícitamente; 0 si no \
pide ninguno en concreto.

tiempo_objetivo: el instante al que se refiere la pregunta, en ISO-8601 \
(por ejemplo 2026-03-01T00:00:00Z). Cadena vacía si la pregunta se refiere a \
ahora. Si la pregunta abarca un intervalo, el extremo final del intervalo.

corte_de_registro: solo si la pregunta limita lo que se había REGISTRADO \
hasta una fecha («¿qué sabía yo el 1 de marzo?»), en ISO-8601. Cadena vacía \
en cualquier otro caso.\
"""


class OllamaQueryIntentClassifierAdapter:
    """Implementa ``QueryIntentClassifierPort`` contra un modelo local."""

    def __init__(
        self,
        model: str,
        *,
        ahora: str | None = None,
        client: httpx.Client | None = None,
        timeout_seconds: float = _REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._model = model
        self._instruccion = _INSTRUCCION.format(
            ahora=ahora if ahora is not None else datetime.now(UTC).date().isoformat()
        )
        # ``client`` existe solo como costura de prueba (un
        # ``httpx.MockTransport`` nunca sale del proceso); el código de
        # producción cae siempre en un cliente clavado a localhost — ningún
        # parámetro acepta un host remoto, y ``classify_intent`` nunca se fía
        # del ``base_url`` del cliente.
        self._client = client or httpx.Client(
            base_url=_OLLAMA_LOCAL_BASE_URL, timeout=timeout_seconds
        )

    def classify_intent(self, query_text: str) -> IntencionDeConsulta | None:
        try:
            # URL absoluta, no una ruta relativa al ``base_url`` del cliente:
            # el ``base_url`` de un cliente inyectado nunca debe poder desviar
            # la petición fuera de localhost. ``follow_redirects=False``
            # anula cualquier cliente inyectado que los siga: un 307/308
            # desde localhost no debe reenviar la consulta a un host remoto.
            response = self._client.post(
                f"{_OLLAMA_LOCAL_BASE_URL}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": self._instruccion},
                        {"role": "user", "content": query_text},
                    ],
                    "stream": False,
                    "format": dict(_ESQUEMA_RESPUESTA),
                    "think": _PENSAMIENTO_APAGADO,
                    "keep_alive": _PERMANENCIA_DEL_MODELO,
                    "options": {
                        "temperature": _TEMPERATURA,
                        "num_ctx": _TAMANO_DE_CONTEXTO,
                    },
                },
                follow_redirects=False,
            )
            response.raise_for_status()
            return _parse_intencion(response.json())
        except Exception as exc:  # Falla abierto por contrato del puerto.
            _logger.warning(
                "Interpretación de la consulta no disponible, se falla abierto (%s)",
                type(exc).__name__,
            )
            return None


def _parse_intencion(payload: object) -> IntencionDeConsulta:
    """Extrae la intención de una respuesta de ``/api/chat`` constreñida por
    el esquema cerrado. Cualquier cosa inesperada lanza, y
    ``classify_intent`` la convierte en ``None`` como cualquier otro fallo."""
    if not isinstance(payload, dict):
        raise ValueError("respuesta de Ollama sin objeto")
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("respuesta de Ollama sin message")
    answer = json.loads(str(message.get("content", "")))
    if not isinstance(answer, dict):
        raise ValueError("respuesta de Ollama fuera del esquema")
    return IntencionDeConsulta(
        modo=Modo(str(answer["modo"]).strip()),
        cardinalidad=Cardinalidad(str(answer["cardinalidad"]).strip()),
        limite=_limite(answer.get("limite")),
        tiempo_objetivo=_instante(answer.get("tiempo_objetivo")),
        corte_de_registro=_instante(answer.get("corte_de_registro")),
    )


def _limite(declarado: object) -> int | None:
    """El límite pedido, o ``None`` si no se pidió ninguno. Un 0 —lo que la
    instrucción pide cuando la pregunta no acota— es «no declarado», no una
    cuota de cero."""
    if not isinstance(declarado, int | str) or isinstance(declarado, bool):
        return None
    try:
        n = int(declarado)
    except ValueError:
        return None
    return n if n > 0 else None


def _instante(declarado: object) -> str | None:
    """La fecha declarada si es ISO-8601 reconocible; ``None`` si no lo es o
    si el modelo contestó la cadena vacía. Un intervalo se resuelve por su
    extremo final, la misma traducción que el traductor del banco declara
    (``tests/acceptance/staged_engine_case_translation.py``)."""
    if not isinstance(declarado, str):
        return None
    texto = declarado.strip()
    if texto == _SIN_DECLARAR:
        return None
    if "/" in texto:
        texto = texto.split("/")[-1].strip()
    return texto if _PATRON_ISO.match(texto) else None
