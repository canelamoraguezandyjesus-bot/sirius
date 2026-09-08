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
podría excluir el canon entero en silencio.

Validar no basta: hay que NORMALIZAR
====================================

El patrón admite tres escrituras del mismo instante —``2026-03-01``,
``2026-03-01T00:00:00Z`` y ``2026-03-01 00:00:00``— y ``G8`` compara el
corte con ``created_at`` por orden lexicográfico, donde el separador manda:
``created_at`` llega de SQLite como ``str(datetime)``, es decir
``"AAAA-MM-DD HH:MM:SS.ffffff"`` con **espacio**, y el espacio (0x20)
siempre ordena antes que la ``T`` (0x54). Devolver la cadena verbatim
dejaría que el formato que el modelo eligió esa vez decidiera, por
accidente, si el día del corte entra o no. Por eso los dos instantes se
reemiten aquí en una forma canónica única:

- **corte de registro**: la pregunta que lo produce («¿qué sabía yo el 1 de
  marzo?») es de grano DÍA, y la respuesta es lo que estaba registrado **al
  final** de ese día. El corte se canoniza, por tanto, al final del día que
  nombra —``"AAAA-MM-DD 23:59:59.999999"``, misma forma que ``created_at``
  y por tanto comparable con ella—, de modo que las tres escrituras del
  mismo día admiten exactamente el mismo conjunto.
- **tiempo objetivo**: es un instante, no un día, y ``G8`` lo compara con
  ``valid_from``/``valid_to``, que son ISO-8601 con zona. Se canoniza a UTC
  con desfase explícito (``…+00:00``); una fecha desnuda es su medianoche,
  que es como el banco adjudica los casos con tiempo objetivo declarado.

El «hoy» que el modelo necesita para resolver una fecha relativa se le da en
la instrucción, resuelto **en cada consulta** —una aplicación de escritorio
se deja abierta durante días y el «hoy» del arranque envejece en silencio—;
el llamador puede fijarlo (la medición del banco usa su ``ahora_declarado``).
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, time

import httpx

from sirius.domain.query_intent import IntencionDeConsulta
from sirius.domain.staged_engine_contracts import Cardinalidad, Modo
from sirius.infrastructure.logging import get_logger

__all__ = ["OllamaQueryIntentClassifierAdapter", "instante_utc"]

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

#: Forma con la que ``created_at`` llega del canon: ``str(datetime)`` sobre
#: una columna ``Mapped[datetime]`` de SQLite
#: (``sirius.adapters.persistence.staged_engine_port``). El corte de registro
#: se reemite en ESTA forma porque ``G8`` los compara por orden lexicográfico.
_FORMATO_DE_CREATED_AT = "%Y-%m-%d %H:%M:%S.%f"

#: Último instante representable de un día en la forma de ``created_at``: el
#: corte de registro de un día D admite todo lo registrado durante D.
_FINAL_DEL_DIA = time(23, 59, 59, 999999)

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
        # El «hoy» no se congela en el constructor: Sirius es una aplicación
        # de escritorio que se deja abierta durante días, y el adaptador se
        # construye UNA vez por arranque (``composition_root``). Con la
        # fecha resuelta aquí, «¿qué decidí ayer?» seguiría anclada al día
        # del arranque y el desfase crecería en silencio. Con ``ahora``
        # fijado por el llamador —la medición del banco usa su
        # ``ahora_declarado``— se respeta lo que declaró.
        self._ahora = ahora
        # ``client`` existe solo como costura de prueba (un
        # ``httpx.MockTransport`` nunca sale del proceso); el código de
        # producción cae siempre en un cliente clavado a localhost — ningún
        # parámetro acepta un host remoto, y ``classify_intent`` nunca se fía
        # del ``base_url`` del cliente.
        self._client = client or httpx.Client(
            base_url=_OLLAMA_LOCAL_BASE_URL, timeout=timeout_seconds
        )

    def _instruccion(self) -> str:
        """La instrucción de ESTA consulta, con el «hoy» del momento en que
        se pregunta salvo que el llamador lo haya fijado."""
        ahora = self._ahora if self._ahora is not None else datetime.now(UTC).date().isoformat()
        return _INSTRUCCION.format(ahora=ahora)

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
                        {"role": "system", "content": self._instruccion()},
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
        tiempo_objetivo=_tiempo_objetivo(answer.get("tiempo_objetivo")),
        corte_de_registro=_corte_de_registro(answer.get("corte_de_registro")),
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


def instante_utc(valor: str | None) -> datetime | None:
    """Un ISO-8601 leído como instante UTC, o ``None`` si no lo es.

    Sin zona declarada se asume UTC, y no la zona local de la máquina: todo
    lo que este módulo emite, y el ``created_at`` con el que se compara, son
    UTC por construcción. Comparar un ingenuo con un consciente por ``!=``
    no lanza —simplemente da siempre «distintos»—, así que asumir la zona
    aquí es lo que hace comparables dos escrituras del mismo instante.
    """
    if valor is None:
        return None
    try:
        momento = datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return momento.replace(tzinfo=UTC) if momento.tzinfo is None else momento.astimezone(UTC)


def _iso_declarado(declarado: object) -> str | None:
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


def _tiempo_objetivo(declarado: object) -> str | None:
    """El instante al que se refiere la pregunta, canonizado a UTC.

    Se emite con desfase explícito (``…+00:00``) porque ``G8`` lo compara
    con ``valid_from``/``valid_to``, que son ISO-8601 con zona. Una fecha
    desnuda es su medianoche: es un instante, no un día.
    """
    texto = _iso_declarado(declarado)
    momento = instante_utc(texto)
    return None if momento is None else momento.isoformat()


def _corte_de_registro(declarado: object) -> str | None:
    """El corte de registro, canonizado al FINAL del día que nombra y en la
    forma de ``created_at``.

    Las tres escrituras que ``_PATRON_ISO`` admite para el mismo día
    —``AAAA-MM-DD``, ``AAAA-MM-DDT00:00:00Z`` y ``AAAA-MM-DD 00:00:00``—
    tienen que admitir el mismo conjunto: la pregunta que produce un corte
    («¿qué sabía yo el 1 de marzo?») es de grano día, y la hora que el
    modelo escriba —o deje de escribir— es formato, no información. Ver el
    encabezado del módulo.
    """
    texto = _iso_declarado(declarado)
    momento = instante_utc(texto)
    if momento is None:
        return None
    final = datetime.combine(momento.date(), _FINAL_DEL_DIA)
    return final.strftime(_FORMATO_DE_CREATED_AT)
