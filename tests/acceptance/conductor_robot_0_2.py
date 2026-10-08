"""Conductor de las pruebas de aceptación de la versión 0.2 del robot (ADR-233).

Las pruebas de ``test_robot_0_2_*.py`` hablan como el plan
(``docs/evolution/PLAN_DEL_ROBOT.md``, §4): el propietario dice algo, Sirius
contesta, «ponte serio», «eso es Sirius», «olvida eso». Este módulo es lo único
que sabe cómo se hace cada cosa en el código. Así las pruebas se escriben antes
que el código, como pide la §3 del plan, y cuando entra una pieza solo cambia su
parte del conductor, no las pruebas.

**La regla del conductor: no implementa nada de Sirius.** Solo llama a lo que
monta ``build_conversation_dependencies`` y a los casos de uso que salen de ahí,
y mira lo que llega al modelo y lo que queda en la base. Si una prueba pasa, es
porque Sirius lo hace, no porque lo haga el conductor. Los dobles de abajo
(``OllamaDeMentira``, ``ResumidorDeMentira``, ``JuezDeMentira``,
``ExtractorDeMentira``) hacen de modelo, nunca de Sirius.

Las piezas de ADR-233 que aún no han entrado levantan ``PiezaPendiente``. Cada
prueba que depende de una va decorada con ``pieza(...)``: mientras la pieza no
está en ``PIEZAS_ENTREGADAS``, es un ``xfail`` estricto que solo acepta esa
excepción, así que la prueba falla por la razón esperada o falla de verdad.
Cuando una pieza entra, se implementan sus métodos aquí y se añade su letra a
``PIEZAS_ENTREGADAS``; la marca desaparece sola y la tabla de
``docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md`` tiene que decirlo, porque
``test_robot_0_2_trazabilidad.py`` lo compara.
"""

from __future__ import annotations

import functools
import itertools
import json
import random
import sqlite3
import struct
import time
import zlib
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, TypeVar, cast

import httpx
import pytest
import sqlite_vec

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.memory_commands import ASK_TO_CONFIRM
from sirius.application.send_message import SendMessageResult
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.settings import load_settings, save_settings
from sirius.domain.blind_test import BlindTestSheet
from sirius.domain.conversation_mode import (
    ENTERING_SERIOUS_MODE,
    MODE_INSTRUCTIONS,
    ConversationMode,
)
from sirius.domain.facts import Certainty, ProposedFact
from sirius.domain.memory_bank import MEMORY_BANK
from sirius.domain.memory_bank import MemoryCase as MemoryCaseDelBanco
from sirius.domain.own_memory import IS_YOU_HEADING, NOT_YOU_HEADING
from sirius.domain.relevance import KnowledgeKind
from sirius.domain.reply_judge import TrickVerdict
from sirius.domain.reply_mark import ReplyMark
from sirius.domain.robot_seed import (
    ROBOT_SEED_EXAMPLES,
    ROBOT_SEED_INSTRUCTIONS,
    ROBOT_SEED_REMINDER,
)
from sirius.infrastructure.paths import ensure_paths, resolve_paths
from sirius.ports.embeddings import EmbeddingError, TextEmbedder
from sirius.ports.llm import (
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)

#: Las letras de la tabla de piezas de ADR-233 que ya han entrado en ``main``.
#: La A es esta: la nota de arranque y estas pruebas.
PIEZAS_ENTREGADAS: frozenset[str] = frozenset({"A", "B", "C", "D", "E", "F", "G"})

#: Qué trae cada pieza, con las palabras de la tabla de ADR-233. La H no es de esa
#: tabla: la decidió el propietario el 08-10-2026, sobre la B y la G (ADR-240).
PIEZAS: Mapping[str, str] = {
    "A": "la nota de arranque y las pruebas de aceptación",
    "B": "la semilla",
    "C": "Ollama para la charla y la prueba a ciegas",
    "D": "«ponte serio» y «para», lo de la deriva y los dos botones",
    "E": "la memoria propia de Sirius, el juez y las 40 preguntas trampa",
    "F": "el banco de memoria de 100 casos y la búsqueda por significado",
    "G": "hechos con fecha y con quién lo dijo, fichas, órdenes de memoria y el sueño",
    "H": (
        "los tres ejemplos que más se parecen a la charla, sus palabras sueltas y su voz "
        "en las órdenes de memoria"
    ),
}


def _adr_de_la_pieza(letra: str) -> str:
    return "ADR-240" if letra == "H" else "ADR-233"


_Prueba = TypeVar("_Prueba", bound=Callable[..., object])


class PiezaPendiente(NotImplementedError):
    """La pieza de ADR-233 que haría esto todavía no ha entrado."""

    def __init__(self, letra: str) -> None:
        super().__init__(f"pieza {letra} de {_adr_de_la_pieza(letra)} pendiente: {PIEZAS[letra]}")
        self.letra = letra


def pieza(letra: str, que: str) -> Callable[[_Prueba], _Prueba]:
    """Marca una prueba como dependiente de la pieza ``letra`` de ADR-233.

    Entregada la pieza, no hace nada y la prueba corre entera. Mientras no lo
    está, la prueba no corre: levanta ``PiezaPendiente`` al empezar, bajo un
    ``xfail`` estricto que solo acepta esa excepción. Que no corra a medias es
    a propósito: una prueba de la pieza G que diera sus primeros pasos con lo que
    ya trajo la D fallaría por una aserción, no por la pieza, el día que entrase
    la D. El cuerpo lo siguen comprobando ruff y mypy desde hoy.
    """
    if letra not in PIEZAS:
        msg = f"ADR-233 no tiene pieza {letra!r}"
        raise ValueError(msg)
    if letra in PIEZAS_ENTREGADAS:
        return lambda prueba: prueba
    marca = pytest.mark.xfail(
        strict=True,
        raises=PiezaPendiente,
        reason=(
            f"Pieza {letra} de {_adr_de_la_pieza(letra)} ({PIEZAS[letra]}): {que}. Cuando "
            "entre, se añade su letra a PIEZAS_ENTREGADAS y esta marca desaparece."
        ),
    )

    def aplicar(prueba: _Prueba) -> _Prueba:
        @functools.wraps(prueba)
        def pendiente(*args: object, **kwargs: object) -> None:
            del args, kwargs
            raise PiezaPendiente(letra)

        return cast("_Prueba", marca(pendiente))

    return aplicar


def _pendiente(letra: str) -> PiezaPendiente:
    return PiezaPendiente(letra)


# --- Dobles: hacen de modelo o de Ollama, nunca de Sirius ---------------------


@dataclass(frozen=True, slots=True)
class Peticion:
    """Lo que recibió el modelo en un turno."""

    instrucciones: str
    texto: str


def _respuestas(fijas: Sequence[str]) -> Iterator[str]:
    """Las respuestas fijas, en orden, y después «Respuesta N de Sirius.»."""
    siguientes = (f"Respuesta {n} de Sirius." for n in itertools.count(len(fijas) + 1))
    return itertools.chain(fijas, siguientes)


class _ProveedorGrabador:
    """Hace de modelo de la charla: guarda cada petición y contesta lo que toque."""

    #: Con este nombre tiene que quedar apuntada cada respuesta suya (pieza D).
    model_name = "grabador-de-pruebas"

    def __init__(self, respuestas: Iterator[str]) -> None:
        self.peticiones: list[Peticion] = []
        self._respuestas = respuestas
        self._falla_la_proxima = False

    def contesta_despues(self, texto: str) -> None:
        """La próxima respuesta será ``texto``; después sigue con las que tocaban."""
        self._respuestas = itertools.chain([texto], self._respuestas)

    def falla_despues(self) -> None:
        """La próxima petición falla como un modelo que no contesta; las demás, no."""
        self._falla_la_proxima = True

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(Peticion(request.instructions, request.input_text))
        if self._falla_la_proxima:
            self._falla_la_proxima = False
            yield LLMError(kind=LLMErrorKind.CONNECTION, message="el modelo no contesta")
            return
        texto = next(self._respuestas)
        yield LLMTextDelta(text=texto)
        yield LLMCompleted(text=texto, input_tokens=1, output_tokens=len(texto))

    def cancel(self, operation_id: str) -> None:
        del operation_id


@dataclass
class OllamaDeMentira:
    """Un Ollama local de mentira: contesta ``/api/chat`` como el de verdad.

    Responde en el formato de líneas JSON de Ollama y apunta cada llamada:
    a qué dirección fue, a qué ruta y qué modelo pidió. Se enchufa con
    ``transporte()``, un ``httpx.MockTransport``, así que nunca abre la red.
    """

    respuesta: str = "Respuesta de Ollama."
    #: Si está, contesta según el modelo y lo que dijo el propietario.
    responder: Callable[[str, str], str] | None = None
    modelos_instalados: tuple[str, ...] = ()
    urls: list[httpx.URL] = field(default_factory=list)
    modelos: list[str] = field(default_factory=list)
    #: Lo que le llegó a ``/api/chat``, como lo apunta el grabador.
    peticiones: list[Peticion] = field(default_factory=list)

    def transporte(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._contestar)

    def llamadas_a(self, ruta: str) -> int:
        return sum(1 for url in self.urls if url.path == ruta)

    def _contestar(self, request: httpx.Request) -> httpx.Response:
        self.urls.append(request.url)
        cuerpo: dict[str, Any] = json.loads(request.content or b"{}")
        modelo = cuerpo.get("model")
        if isinstance(modelo, str):
            self.modelos.append(modelo)
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": nombre} for nombre in self.modelos_instalados]}
            )
        if request.url.path == "/api/chat":
            mensajes = cuerpo.get("messages", [])
            dicho = next((m["content"] for m in reversed(mensajes) if m.get("role") == "user"), "")
            sistema = next((m["content"] for m in mensajes if m.get("role") == "system"), "")
            self.peticiones.append(Peticion(sistema, dicho))
            respuesta = (
                self.responder(str(modelo), dicho) if self.responder is not None else self.respuesta
            )
            lineas = [
                {"message": {"role": "assistant", "content": respuesta}, "done": False},
                {"message": {"role": "assistant", "content": ""}, "done": True},
            ]
            texto = "\n".join(json.dumps(linea) for linea in lineas) + "\n"
            return httpx.Response(200, text=texto)
        return httpx.Response(404, json={"error": f"ruta no simulada: {request.url.path}"})


@dataclass
class ResumidorDeMentira:
    """Hace de modelo al resumir la charla: apunta qué le dieron y devuelve un texto fijo.

    Con ``copiar=True`` devuelve lo que le dieron, como haría un resumen que
    conserva un dato: sirve para comprobar que olvidar llega también a los
    resúmenes.
    """

    texto: str = "RESUMEN DE LA CHARLA"
    copiar: bool = False
    pedidos: list[str] = field(default_factory=list)

    def resume(self, charla: str) -> str:
        self.pedidos.append(charla)
        return charla if self.copiar else self.texto


class _JuezEnchufado:
    """Enchufa un ``JuezDeMentira`` donde Sirius espera su juez."""

    def __init__(self, juez: JuezDeMentira) -> None:
        self._juez = juez

    def score(self, reply: str) -> int:
        return self._juez.puntua(reply)

    def verdict(self, bad_idea: str, reply: str) -> TrickVerdict:
        del bad_idea
        return TrickVerdict(self._juez.discrepa(reply))


class _ExtractorEnchufado:
    """Enchufa un ``ExtractorDeMentira`` donde Sirius saca hechos al soñar."""

    def __init__(self, extractor: ExtractorDeMentira) -> None:
        self._extractor = extractor

    def extract(self, text: str, provider: object) -> list[ProposedFact]:
        del provider
        return [
            ProposedFact(propuesta.persona, propuesta.tema, propuesta.texto)
            for propuesta in self._extractor.extrae(text)
        ]


class _ResumidorEnchufado:
    """Enchufa un ``ResumidorDeMentira`` donde Sirius espera su resumidor."""

    def __init__(self, resumidor: ResumidorDeMentira) -> None:
        self._resumidor = resumidor

    def summarize(self, text: str, provider: object) -> str:
        del provider
        return self._resumidor.resume(text)


@dataclass
class JuezDeMentira:
    """Hace de juez: devuelve las notas que se le den, en orden, y apunta qué juzgó."""

    notas: Sequence[int] = ()
    veredicto: str = "discrepa"
    juzgadas: list[str] = field(default_factory=list)

    def puntua(self, respuesta: str) -> int:
        self.juzgadas.append(respuesta)
        return self.notas[len(self.juzgadas) - 1]

    def discrepa(self, respuesta: str) -> str:
        self.juzgadas.append(respuesta)
        return self.veredicto


@dataclass(frozen=True, slots=True)
class HechoPropuesto:
    """Lo que un modelo saca de la charla del día: de quién, de qué tema y qué."""

    persona: str
    tema: str
    texto: str


@dataclass
class ExtractorDeMentira:
    """Hace de modelo en el «sueño»: propone los hechos que se le den."""

    propuestas: Sequence[HechoPropuesto] = ()
    leido: list[str] = field(default_factory=list)

    def extrae(self, charla: str) -> Sequence[HechoPropuesto]:
        self.leido.append(charla)
        return self.propuestas


@dataclass
class HuellasDeMentira:
    """Hace de modelo de huellas para buscar por significado.

    Las frases de un mismo grupo de ``parecidas`` dan la misma huella, y
    cualquier otra frase da una huella que no se parece a ninguna: así una
    pregunta y un recuerdo sin una sola palabra en común solo pueden
    encontrarse por significado. Apunta cada frase que se le pide.
    """

    parecidas: Sequence[Sequence[str]] = ()
    pedidas: list[str] = field(default_factory=list)
    _sueltas: dict[str, int] = field(default_factory=dict)

    def huella(self, texto: str) -> list[float]:
        self.pedidas.append(texto)
        grupo = next((n for n, frases in enumerate(self.parecidas) if texto in frases), None)
        if grupo is None:
            grupo = len(self.parecidas) + self._sueltas.setdefault(texto, len(self._sueltas))
        huella = [0.0] * (grupo + 1)
        huella[grupo] = 1.0
        return huella


class _HuellasEnchufadas:
    """Enchufa ``HuellasDeMentira`` donde Sirius pide las huellas."""

    model_name = "huellas-de-mentira"

    def __init__(self, huellas: HuellasDeMentira) -> None:
        self._huellas = huellas

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._huellas.huella(texto) for texto in texts]


class _SinHuellas:
    """Sin modelo de huellas, como un Sirius con Ollama cerrado: busca solo por palabras.

    Es lo que usa el conductor si la prueba no enchufa otra cosa. Así ninguna prueba
    acaba hablando con el Ollama de verdad de quien las ejecuta.
    """

    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        del texts
        msg = "sin modelo de huellas en esta prueba"
        raise EmbeddingError(msg)


class _HuellasFijas:
    """Huellas de 1.024 números, como las del modelo de verdad, sin modelo: para medir.

    Cada frase da siempre la misma, una rotación de una base fija. No buscan nada con
    sentido; sirven para que sqlite-vec trabaje lo mismo que con huellas de verdad.
    """

    model_name = "huellas-fijas-1024"
    _BASE = tuple(random.Random(1024).uniform(-1.0, 1.0) for _ in range(1024))

    def huella(self, texto: str) -> list[float]:
        giro = zlib.crc32(texto.encode("utf-8")) % len(self._BASE)
        return list(self._BASE[giro:] + self._BASE[:giro])

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.huella(texto) for texto in texts]


#: Lo que hay que deshacer al acabar cada prueba: lo hace ``tests/conftest.py``.
_DESHACER: list[Callable[[], None]] = []

#: Por dónde escucha el Ollama de este ordenador.
_OLLAMA_LOCAL = ({"localhost", "127.0.0.1", "::1"}, 11434)


def deshaz_los_espias() -> None:
    """Quita lo que haya puesto ``Conductor.con_ollama_espia``. Lo llama ``tests/conftest.py``."""
    while _DESHACER:
        _DESHACER.pop()()


def _espia_todo_ollama(ollama: OllamaDeMentira) -> None:
    """Todo lo que se pida al Ollama de este ordenador, lo contesta ``ollama``.

    También lo que pida un cliente que se monte su propia conexión, sin el
    transporte que reparte la raíz de composición: así una prueba ve cualquier
    petición a Ollama, la haga quien la haga.
    """
    original = httpx.HTTPTransport.handle_request
    hosts, puerto = _OLLAMA_LOCAL
    transporte = ollama.transporte()

    def a_este_ordenador(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        if request.url.host in hosts and request.url.port == puerto:
            return transporte.handle_request(request)
        return original(self, request)

    setattr(httpx.HTTPTransport, "handle_request", a_este_ordenador)  # noqa: B010
    _DESHACER.append(lambda: setattr(httpx.HTTPTransport, "handle_request", original))


def seccion(instrucciones: str, encabezado: str) -> str:
    """El trozo de ``instrucciones`` desde ``encabezado`` hasta el siguiente «# ».

    Vacío si el encabezado no está. Sirve para mirar un bloque concreto de lo
    que recibe el modelo sin confundirlo con los mensajes recientes.
    """
    inicio = instrucciones.find(encabezado)
    if inicio < 0:
        return ""
    fin = instrucciones.find("\n# ", inicio + len(encabezado))
    return instrucciones[inicio:] if fin < 0 else instrucciones[inicio:fin]


# --- Lo que el conductor devuelve a las pruebas ------------------------------


@dataclass(frozen=True, slots=True)
class Semilla:
    """La semilla del robot tal como la guarda el código."""

    instrucciones: str
    ejemplos: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class PreguntaACiegas:
    texto: str
    respuestas: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class HojaACiegas:
    preguntas: tuple[PreguntaACiegas, ...]
    lo_que_ve_el_propietario: str


@dataclass(frozen=True, slots=True)
class PreguntaTrampa:
    id: str
    idea_mala: str
    por_que_es_mala: str


@dataclass(frozen=True, slots=True)
class CasoDeMemoria:
    id: str
    familia: str
    pregunta: str


@dataclass(frozen=True, slots=True)
class Ficha:
    """Lo que Sirius junta de una persona: sus hechos y lo que el propietario dijo de ella."""

    nombre: str
    hechos: tuple[str, ...]
    charlas: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TramoDeUnHecho:
    """Un hecho mientras estuvo vigente, con quién lo dijo y con qué seguridad.

    ``seguridad`` es «segura» o «dudosa».
    """

    texto: str
    desde: date
    hasta: date | None
    dicho_por: str = "propietario"
    seguridad: str = "segura"


#: Las siete familias del banco de memoria de §4 del plan.
FAMILIAS_DEL_BANCO_DE_MEMORIA: frozenset[str] = frozenset(
    {
        "personas",
        "gustos",
        "cosas que cambian",
        "fechas",
        "no lo sé",
        "quién dijo qué",
        "olvida eso",
    }
)


#: Palabras de los recuerdos de prueba de ``llena_la_memoria`` y de sus preguntas.
_PALABRAS = """
    abuela agosto alarma amigo anillo arroz autobús avión balcón barco batería bici boda
    bosque cafetera calle cama camión canción carné casa cena cerveza chaqueta chocolate
    cine ciudad coche cocina cocido colegio concierto consulta correo cuadro cumpleaños
    dentista deporte dinero domingo ducha edificio enero escalera escuela examen
    farmacia febrero fiesta flores frigorífico fútbol garaje gato gimnasio guitarra
    hermana hospital huerto iglesia invierno jardín juego julio lámpara lavadora libro
    llaves lluvia madre maleta martes médico mercado mesa montaña moto museo música
    navidad nevera noche oficina ordenador padre panadería pantalón parque perro piscina
    playa plaza primo pueblo puerta radio regalo reloj restaurante revista río ropa
    sábado salón semana sierra silla sofá sopa taller teatro teléfono televisión tienda
    tío trabajo tren universidad vacaciones vecino ventana verano viaje vino zapatos
"""
_VOCABULARIO: tuple[str, ...] = tuple(_PALABRAS.split())


def _blob(huella: Sequence[float]) -> bytes:
    """Una huella como la guarda Sirius: float32 seguidos."""
    return struct.pack(f"<{len(huella)}f", *huella)


class VentanaDePrueba:
    """La ventana de conversación de Sirius, vista desde una prueba (pieza D).

    Es la ventana de verdad, la que monta ``_build_main_window`` al arrancar;
    aquí solo se buscan sus botones y su indicador y se pulsan.
    """

    def __init__(self, ventana: Any, qtbot: Any) -> None:
        self._ventana = ventana
        self._qtbot = qtbot

    def _respuestas(self) -> list[Any]:
        from sirius.presentation.message_view import MessageItemWidget

        lista = self._ventana.message_list
        widgets = [lista.itemWidget(lista.item(i)) for i in range(lista.count())]
        return [
            w
            for w in widgets
            if isinstance(w, MessageItemWidget)
            and any(not boton.isHidden() for boton in w.mark_buttons)
        ]

    def botones_de_la_respuesta(self, numero: int) -> tuple[str, ...]:
        widget = self._respuestas()[numero - 1]
        return tuple(boton.text() for boton in widget.mark_buttons if not boton.isHidden())

    def pulsa(self, numero: int, boton: str) -> None:
        widget = self._respuestas()[numero - 1]
        next(b for b in widget.mark_buttons if b.text() == boton).click()

    def indicador_de_modo(self) -> str:
        etiqueta = self._ventana.mode_label
        return "" if etiqueta.isHidden() else str(etiqueta.text())

    def quita_el_modo(self) -> None:
        self._ventana.release_mode_button.click()

    def escribe(self, texto: str) -> None:
        """El propietario escribe ``texto`` en la ventana y espera a que acabe todo el turno.

        Todo el turno es la respuesta y lo que la ventana lanza después en segundo
        plano, como el juez.
        """
        self._ventana.message_input.setText(texto)
        self._ventana.send_button.click()
        self._qtbot.waitUntil(
            lambda: self._ventana.send_button.isEnabled() and not self._ventana.judge_in_progress,
            timeout=10_000,
        )

    def aviso_del_juez(self) -> str:
        """El aviso del juez tal como se ve cuando ha terminado de puntuar; vacío si no se ve.

        La ventana lanza el juez en segundo plano al abrirse: se espera a que acabe.
        """
        self._qtbot.waitUntil(lambda: not self._ventana.judge_in_progress, timeout=10_000)
        etiqueta = self._ventana.judge_label
        return "" if etiqueta.isHidden() else str(etiqueta.text())

    def espera_al_trabajo_de_fondo(self) -> None:
        """Espera a que acabe lo que la ventana haya lanzado en segundo plano."""
        ventana = self._ventana
        self._qtbot.waitUntil(
            lambda: (
                not ventana.judge_in_progress
                and not ventana.embedding_in_progress
                and not ventana.knowledge_widget.has_pending_criticality_proposal
            ),
            timeout=10_000,
        )

    def ofrece_etiquetar_por_categorias(self) -> bool:
        """Si la ventana deja poner o pedir la categoría de un recuerdo."""
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QAbstractButton

        textos = [boton.text() for boton in self._ventana.findChildren(QAbstractButton)]
        textos += [accion.text() for accion in self._ventana.findChildren(QAction)]
        return any("categor" in texto.lower() for texto in textos)


# --- El conductor ------------------------------------------------------------


class Conductor:
    """Sirius de verdad, montado como en producción, con un modelo grabador.

    Arranca la persistencia con ``initialize_persistence``, configura el
    proyecto que la charla de 0.1 todavía exige y monta las dependencias con
    ``build_conversation_dependencies``. El único cambio frente a producción es
    el modelo: un grabador que guarda cada petición y contesta lo que toque.

    ``di`` llama a lo mismo que llama la ventana
    (``presentation/conversation_worker.py``): ``send_message``. Si una pieza
    pone algo delante, como las órdenes de memoria, la ventana y ``di`` tienen
    que seguir llamando a lo mismo, o estas pruebas dejarían de mirar lo que
    usa el propietario.
    """

    def __init__(
        self,
        carpeta: Path,
        *,
        respuestas: Sequence[str] = (),
        ajustes: Mapping[str, object] | None = None,
    ) -> None:
        if ajustes:
            save_settings(dict(ajustes))
        self.carpeta = carpeta
        self._ollama: OllamaDeMentira | None = None
        self._charla_por_ollama = False
        self._resumidor: ResumidorDeMentira | None = None
        self._juez: JuezDeMentira | None = None
        self._hoja: BlindTestSheet | None = None
        self._huellas: HuellasDeMentira | None = None
        self._huellas_fijas: _HuellasFijas | None = None
        self._huellas_de_ollama = False
        self._extractor: ExtractorDeMentira | None = None
        rutas = resolve_paths()
        initialize_persistence(rutas)
        self.base = rutas.data_dir / "sirius.db"
        self._grabador = _ProveedorGrabador(_respuestas(respuestas))
        self._dependencias = self._montar()
        # ContextBuilder de 0.1 exige un proyecto configurado para conversar
        # (B3c). El robot no tiene proyectos; hasta que eso cambie, se crea uno.
        if not self._dependencias.initial_project_use_case.is_configured():
            self._dependencias.initial_project_use_case.create_initial_project(
                "Charla con Sirius", "Charlar con Sirius"
            )
        self._resultados: list[SendMessageResult] = []
        self._peticiones_antes_del_ultimo_turno = 0
        self._vistas_antes_del_ultimo_turno = 0

    def _montar(self) -> ConversationDependencies:
        dependencias = build_conversation_dependencies(
            self.base,
            self.carpeta / "copias",
            secret_store=FakeSecretStore(),
            ollama_transport=self._ollama.transporte() if self._ollama is not None else None,
            conversation_summarizer=(
                _ResumidorEnchufado(self._resumidor) if self._resumidor is not None else None
            ),
            reply_judge=_JuezEnchufado(self._juez) if self._juez is not None else None,
            text_embedder=self._modelo_de_huellas(),
            # Sin extractor enchufado, uno que no propone nada: ninguna prueba
            # acaba soñando con el Ollama de verdad de quien las ejecuta.
            fact_extractor=_ExtractorEnchufado(self._extractor or ExtractorDeMentira()),
        )
        if not self._charla_por_ollama:
            dependencias.send_message_use_case.set_llm_provider(self._grabador)
        return dependencias

    def _modelo_de_huellas(self) -> TextEmbedder | None:
        """Quién da las huellas: el doble que haya enchufado la prueba, o ninguno.

        ``None`` es el modelo de huellas de verdad, el de producción; solo se usa con
        ``con_ollama_espia``, que se queda con todo lo que va a Ollama.
        """
        if self._huellas is not None:
            return _HuellasEnchufadas(self._huellas)
        if self._huellas_fijas is not None:
            return self._huellas_fijas
        if self._huellas_de_ollama:
            return None
        return _SinHuellas()

    # --- Lo que ya existe en Sirius ---

    def di(self, texto: str) -> str:
        """El propietario escribe ``texto``; devuelve lo que contesta Sirius."""
        self._peticiones_antes_del_ultimo_turno = len(self._grabador.peticiones)
        self._vistas_antes_del_ultimo_turno = len(self.peticiones)
        resultado = self._dependencias.send_message_use_case.send_message(texto)
        self._resultados.append(resultado)
        # Un mensaje borrado guarda su contenido como None (PA-016).
        return resultado.sirius_message.content or ""

    @property
    def peticiones(self) -> list[Peticion]:
        """Todo lo que ha recibido el modelo de la charla, en orden.

        Con la charla en Ollama, el modelo de la charla es el Ollama de mentira.
        """
        if self._charla_por_ollama and self._ollama is not None:
            return list(self._ollama.peticiones)
        return list(self._grabador.peticiones)

    def hubo_peticion_al_modelo_en_el_ultimo_turno(self) -> bool:
        return len(self._grabador.peticiones) > self._peticiones_antes_del_ultimo_turno

    def peticiones_del_ultimo_turno(self) -> list[Peticion]:
        """Lo que recibió el modelo de la charla en el último ``di``."""
        return self.peticiones[self._vistas_antes_del_ultimo_turno :]

    def lo_vio_el_modelo_en_el_ultimo_turno(self, texto: str) -> bool:
        """Si ``texto`` llegó al modelo de la charla en el último ``di``, sin
        distinguir mayúsculas, en sus instrucciones o en lo que se le dijo."""
        buscado = texto.casefold()
        return any(
            buscado in peticion.instrucciones.casefold() or buscado in peticion.texto.casefold()
            for peticion in self.peticiones_del_ultimo_turno()
        )

    def el_modelo_falla_en_la_proxima_peticion(self) -> None:
        """La próxima petición al modelo de la charla falla, como si no contestara."""
        self._grabador.falla_despues()

    def reabre(self) -> None:
        """Cierra Sirius y lo vuelve a abrir sobre la misma base, arranque incluido."""
        self._dependencias.close_database_connections()
        initialize_persistence(resolve_paths())
        self._dependencias = self._montar()

    def cierra(self) -> None:
        self._dependencias.close_database_connections()

    def busca_en_toda_la_base(self, texto: str) -> list[str]:
        """Las columnas de texto de TODA la base que contienen ``texto``.

        Recorre cada tabla de ``sqlite_master``, también las internas de la
        búsqueda por palabras, y devuelve ``tabla.columna`` por cada sitio
        donde aparece, sin distinguir mayúsculas.
        """
        encontrados: list[str] = []
        with sqlite3.connect(self.base) as conexion:
            tablas = [
                fila[0]
                for fila in conexion.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                    " AND name NOT LIKE 'sqlite_%'"
                )
            ]
            for tabla in tablas:
                columnas = [fila[1] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')]
                for columna in columnas:
                    consulta = (
                        f'SELECT 1 FROM "{tabla}" WHERE CAST("{columna}" AS TEXT)'
                        " LIKE ? COLLATE NOCASE LIMIT 1"
                    )
                    if conexion.execute(consulta, (f"%{texto}%",)).fetchone():
                        encontrados.append(f"{tabla}.{columna}")
        return encontrados

    # --- Pieza B: la semilla ---

    @classmethod
    def desde_una_base_de_0_1(cls, carpeta: Path) -> Conductor:
        """Una base de 0.1, con la identidad v1 y la semilla vieja, que se abre ya con la 0.2.

        La base se crea como la dejó 0.1: esquema al día y la identidad con su
        primera versión, sin pasar por el arranque de ahora. Después se abre
        Sirius sobre ella como en producción.
        """
        rutas = resolve_paths()
        ensure_paths(rutas)
        base = rutas.data_dir / "sirius.db"
        upgrade_to_head(base)
        identidades = build_sqlite_identity_repository(base)
        try:
            identidades.get_or_create_current_identity()
            assert len(identidades.get_history()) == 1
        finally:
            identidades.close()
        return cls(carpeta)

    def semilla_del_robot(self) -> Semilla:
        return Semilla(
            instrucciones=ROBOT_SEED_INSTRUCTIONS,
            ejemplos=tuple((dicho, sirius) for _, dicho, sirius in ROBOT_SEED_EXAMPLES),
        )

    def identidad_vigente(self) -> tuple[int, str]:
        """La versión vigente de la identidad y su texto de personalidad."""
        identidades = build_sqlite_identity_repository(self.base)
        try:
            identidad = identidades.get_current_identity()
        finally:
            identidades.close()
        assert identidad is not None
        vigente = identidad.current_version
        return vigente.version, vigente.personality_instructions

    def ejemplos_en(self, peticion: Peticion) -> list[tuple[str, str]]:
        """Los ejemplos de la semilla que lleva ``peticion``, en el orden en que van.

        Un ejemplo cuenta si va entero: quién habla, lo que dice y lo que contesta
        Sirius, como los escribe la semilla.
        """
        encontrados: list[tuple[int, tuple[str, str]]] = []
        for quien, dicho, sirius in ROBOT_SEED_EXAMPLES:
            sitio = peticion.instrucciones.find(f"{quien}: «{dicho}»\nSirius: «{sirius}»")
            if sitio >= 0:
                encontrados.append((sitio, (dicho, sirius)))
        return [ejemplo for _, ejemplo in sorted(encontrados)]

    @staticmethod
    def huellas_que_acercan(mensaje: str, ejemplos: Sequence[tuple[str, str]]) -> HuellasDeMentira:
        """Un modelo de huellas para el que ``mensaje`` se parece a ``ejemplos`` y a nada más.

        Sirius mide el parecido de un ejemplo por lo que se le dice en él.
        """
        return HuellasDeMentira(parecidas=[[mensaje, *(dicho for dicho, _ in ejemplos)]])

    def ejemplos_guardados_en_la_identidad(self) -> tuple[tuple[str, str], ...]:
        """Los ejemplos que guarda la versión vigente de la identidad: lo dicho y lo contestado."""
        raise _pendiente("H")

    def marco_de_los_ejemplos(self) -> str:
        """Lo que va delante de los ejemplos en cada petición."""
        raise _pendiente("H")

    def frase_de_siempre_al_olvidar(self) -> str:
        """Lo que contesta Sirius a «olvida eso» cuando el modelo no le pone la voz."""
        raise _pendiente("H")

    def pregunta_para_confirmar(self) -> str:
        """Cómo acaba la pregunta de Sirius tras «eso no es así»: un «sí» la contesta."""
        return ASK_TO_CONFIRM

    def identidad_en_la_version(self, version: int) -> str:
        identidades = build_sqlite_identity_repository(self.base)
        try:
            historia = identidades.get_history()
        finally:
            identidades.close()
        return next(v.personality_instructions for v in historia if v.version == version)

    # --- Pieza C: Ollama para la charla y la prueba a ciegas ---

    def charla_por_ollama(self, modelo: str, ollama: OllamaDeMentira) -> None:
        """Elige Ollama para la charla con ``modelo``, servido por ``ollama``.

        Guarda los ajustes como lo haría el propietario y vuelve a montar
        Sirius: desde aquí la charla va por el conector de verdad, y el
        grabador deja de hacer de modelo.
        """
        ajustes = dict(load_settings())
        ajustes["llm_provider"] = "ollama"
        ajustes["ollama_chat_model"] = modelo
        save_settings(ajustes)
        self._ollama = ollama
        self._charla_por_ollama = True
        self.reabre()

    def preguntas_de_la_prueba_a_ciegas(self) -> tuple[str, ...]:
        return self._dependencias.blind_test_use_case.questions()

    def prueba_a_ciegas(self, respuestas_por_modelo: Mapping[str, Sequence[str]]) -> HojaACiegas:
        """Prepara la hoja: cada modelo contesta las preguntas con sus respuestas.

        Los modelos los sirve un Ollama de mentira que contesta, a cada modelo
        y a cada pregunta, lo de ``respuestas_por_modelo``. La hoja la prepara
        el caso de uso de verdad, preguntando por el conector de verdad.
        """
        preguntas = self.preguntas_de_la_prueba_a_ciegas()
        self._ollama = OllamaDeMentira(
            responder=lambda modelo, dicho: respuestas_por_modelo[modelo][preguntas.index(dicho)],
            modelos_instalados=tuple(respuestas_por_modelo),
        )
        self.reabre()
        caso = self._dependencias.blind_test_use_case
        assert caso.installed_models() == tuple(sorted(respuestas_por_modelo))
        self._hoja = caso.prepare(list(respuestas_por_modelo))
        # Lo que enseña la ventana en cada pregunta: el texto y «letra) respuesta».
        vista = [
            linea
            for item in self._hoja.items
            for linea in (item.question, *(f"{letra}) {texto}" for letra, texto in item.options))
        ]
        return HojaACiegas(
            preguntas=tuple(
                PreguntaACiegas(texto=item.question, respuestas=dict(item.options))
                for item in self._hoja.items
            ),
            lo_que_ve_el_propietario="\n".join(vista),
        )

    def elige_a_ciegas(self, hoja: HojaACiegas, elecciones: Mapping[int, str]) -> str:
        """El propietario elige una letra por pregunta; devuelve el modelo ganador.

        Desde aquí la charla va por el Ollama de mentira con el ganador, como en
        producción: al reabrir, Sirius la monta otra vez con él.
        """
        assert self._hoja is not None, "primero hay que preparar la prueba a ciegas"
        caso = self._dependencias.blind_test_use_case
        resultado = caso.result(self._hoja, elecciones)
        assert resultado.winner is not None, f"empate entre {resultado.tied}"
        caso.choose(resultado.winner)
        self._charla_por_ollama = True
        return resultado.winner

    def modelo_de_la_charla(self) -> str | None:
        return self._dependencias.blind_test_use_case.chat_model()

    # --- Pieza D: modos, deriva y botones ---

    def texto_del_modo(self, modo: str) -> str:
        """Lo que Sirius añade a las instrucciones en el modo ``serio`` o ``para``."""
        return MODE_INSTRUCTIONS[ConversationMode(modo)]

    def texto_al_entrar_en_modo_serio(self) -> str:
        """Lo que Sirius añade solo en el turno en que entra en el modo serio: el vacile."""
        return ENTERING_SERIOUS_MODE

    def recordatorio_de_la_semilla(self) -> str:
        return ROBOT_SEED_REMINDER

    def con_resumidor(self, resumidor: ResumidorDeMentira) -> None:
        """Los resúmenes de la charla los hace ``resumidor`` en vez del modelo."""
        self._resumidor = resumidor
        self.reabre()

    def _id_de_la_respuesta(self, respuesta: int) -> int:
        return self._resultados[respuesta - 1].sirius_message.id

    def marca(self, respuesta: int, marca: str) -> None:
        """Pulsa «eso es Sirius» o «eso no» en la respuesta ``respuesta`` (desde 1)."""
        self._dependencias.mark_reply_use_case.mark(
            self._id_de_la_respuesta(respuesta), ReplyMark(marca)
        )

    def marcas(self) -> list[tuple[int, str]]:
        numeros = {r.sirius_message.id: n for n, r in enumerate(self._resultados, start=1)}
        return [
            (numeros[marcada.message_id], marcada.mark.value)
            for marcada in self._dependencias.mark_reply_use_case.marked_replies()
        ]

    def detalle_de_la_marca(self, respuesta: int) -> Mapping[str, object]:
        """Con qué versión de la identidad y con qué modelo se dio la respuesta marcada."""
        identificador = self._id_de_la_respuesta(respuesta)
        marcada = next(
            m
            for m in self._dependencias.mark_reply_use_case.marked_replies()
            if m.message_id == identificador
        )
        return {"modelo": marcada.model, "version_de_identidad": marcada.identity_version}

    def cuenta_de_marcas(self, ultimas: int) -> tuple[int, int]:
        """Cuántas «eso es Sirius» hay entre las ``ultimas`` marcadas, y cuántas marcadas."""
        return self._dependencias.mark_reply_use_case.count(ultimas)

    def marcas_posibles(self) -> frozenset[str]:
        return frozenset(
            marca.value for marca in self._dependencias.mark_reply_use_case.possible_marks()
        )

    def ventana(self, qtbot: Any) -> VentanaDePrueba:
        """La ventana principal, montada como al arrancar, con la charla ya cargada."""
        from sirius.main import _build_main_window

        ventanas: list[Any] = []
        ventana = _build_main_window(self._dependencias, ventanas)
        qtbot.addWidget(ventana)
        return VentanaDePrueba(ventana, qtbot)

    # --- Pieza E: memoria propia, juez y preguntas trampa ---

    def sirius_opino(self, texto: str) -> None:
        """Guarda una opinión que Sirius ya dio.

        Se la hace decir al modelo en un turno de verdad, y la charla sigue con
        otra cosa hasta que esa respuesta ya no va entre los mensajes recientes:
        si después vuelve a una petición, solo puede ser por su memoria propia.
        """
        self._grabador.contesta_despues(texto)
        self.di("¿Y tú qué opinas?")
        dicha = self._resultados[-1].sirius_message.id
        for n in range(1, 100):
            self.di(f"Cambiando de tema, la número {n}.")
            contexto = self._resultados[-1].context
            assert contexto is not None, "un turno de charla siempre monta su contexto"
            if all(mensaje.id != dicha for mensaje in contexto.recent_messages):
                return
        msg = "la opinión no sale nunca de los mensajes recientes"
        raise AssertionError(msg)

    def encabezado_de_lo_que_no_es(self) -> str:
        return NOT_YOU_HEADING

    def encabezado_de_lo_que_si_es(self) -> str:
        return IS_YOU_HEADING

    def con_juez(self, juez: JuezDeMentira) -> None:
        """Las notas y los veredictos del juez los da ``juez`` en vez del modelo local."""
        self._juez = juez
        self.reabre()

    def _deja_puntuar_al_juez(self) -> None:
        """Lo que la ventana lanza en segundo plano al acabar cada turno: el juez.

        ``di`` es el turno y no lo incluye, igual que el turno de la ventana.
        """
        self._dependencias.reply_judge_service.judge_pending()

    def notas_del_juez(self) -> list[int]:
        self._deja_puntuar_al_juez()
        return [nota.score for nota in self._dependencias.reply_judge_service.scores()]

    def avisos_del_juez(self) -> list[int]:
        """Las respuestas (desde 1) tras las que el juez avisó de que Sirius baja."""
        self._deja_puntuar_al_juez()
        avisadas = {
            nota.message_id
            for nota in self._dependencias.reply_judge_service.scores()
            if nota.warned
        }
        return [
            n
            for n, resultado in enumerate(self._resultados, start=1)
            if resultado.sirius_message.id in avisadas
        ]

    def banco_de_preguntas_trampa(self) -> tuple[PreguntaTrampa, ...]:
        return tuple(
            PreguntaTrampa(id=p.id, idea_mala=p.bad_idea, por_que_es_mala=p.why_bad)
            for p in self._dependencias.trick_questions_use_case.questions()
        )

    def pasa_el_banco_de_preguntas_trampa(self, juez: JuezDeMentira) -> Mapping[str, str]:
        """Cada pregunta trampa, con el veredicto del juez sobre la respuesta.

        Con la charla en el Ollama de este ordenador, que es lo único con lo que
        se hacen: con otro modelo, las 40 preguntas podrían costar dinero.
        """
        self.charla_por_ollama("modelo-local", OllamaDeMentira(respuesta="Ni de broma."))
        self.con_juez(juez)
        respuestas = self._dependencias.trick_questions_use_case.run()
        return {
            r.question.id: r.judge_verdict.value if r.judge_verdict is not None else ""
            for r in respuestas
        }

    # --- Pieza F: banco de memoria y búsqueda por significado ---

    def banco_de_memoria(self) -> tuple[CasoDeMemoria, ...]:
        return tuple(
            CasoDeMemoria(id=caso.id, familia=caso.family, pregunta=caso.question)
            for caso in MEMORY_BANK
        )

    def pasa_el_banco_de_memoria(self) -> Mapping[str, tuple[int, int]]:
        """Aciertos y casos por familia, con el camino real y un buscador determinista.

        Es la orden de E-R02-04 (``scripts/pasar_el_banco_de_memoria.py``) con unas
        huellas de mentira hechas para cada caso: la pregunta se parece a lo que
        tiene que encontrar, a lo que hay que olvidar y a lo que dijo Sirius. Así
        «olvida eso» solo acierta si lo olvidado ya no está, y «quién dijo qué»
        solo si lo que dijo Sirius nunca entró como suyo: si entrara, se parecería
        a la pregunta tanto como lo esperado, y por más nuevo saldría antes.
        """
        import pasar_el_banco_de_memoria as orden

        def huellas_de(caso: MemoryCaseDelBanco) -> TextEmbedder:
            parecidas = [caso.question, caso.expected, caso.forget]
            parecidas += [m for m in caso.memories if orden.es_de_sirius(m)]
            grupo = [frase for frase in parecidas if frase is not None]
            return _HuellasEnchufadas(HuellasDeMentira(parecidas=[grupo]))

        return orden.pasa_el_banco(huellas_de, self.carpeta / "banco")

    def llena_la_memoria(self, recuerdos: int) -> None:
        """Guarda ``recuerdos`` recuerdos de prueba, cada uno con su huella de 1.024 números.

        Van directos a la base, en una transacción: por los casos de uso tardaría
        minutos y lo que se mide es buscar, no guardar. Las tablas son las de
        verdad, con sus disparadores, así que la búsqueda por palabras también los
        ve.
        """
        self._huellas_fijas = _HuellasFijas()
        self.reabre()
        ahora = datetime.now(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.%f")
        modelo = self._huellas_fijas.model_name
        with closing(sqlite3.connect(self.base)) as conexion, conexion:
            primero = conexion.execute("SELECT COALESCE(MAX(id), 0) FROM memories").fetchone()[0]
            revision = conexion.execute(
                "SELECT COALESCE(MAX(id), 0) FROM memory_revisions"
            ).fetchone()[0]
            filas = []
            for n in range(1, recuerdos + 1):
                palabras = " ".join(_VOCABULARIO[(n * k) % len(_VOCABULARIO)] for k in (1, 7, 13))
                filas.append((primero + n, revision + n, f"Recuerdo de prueba {n}: {palabras}."))
            conexion.executemany(
                "INSERT INTO memories (id, status, created_at, updated_at, category_locked)"
                " VALUES (?, 'current', ?, ?, 0)",
                [(memoria, ahora, ahora) for memoria, _, _ in filas],
            )
            conexion.executemany(
                "INSERT INTO memory_revisions"
                " (id, memory_id, version, content, origin, is_current, created_at)"
                " VALUES (?, ?, 1, ?, 'prueba', 1, ?)",
                [(rev, memoria, texto, ahora) for memoria, rev, texto in filas],
            )
            conexion.executemany(
                "INSERT INTO memory_embeddings"
                " (memory_id, revision_id, model, embedding, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                [
                    (memoria, rev, modelo, _blob(self._huellas_fijas.huella(texto)), ahora)
                    for memoria, rev, texto in filas
                ],
            )

    def mide_la_busqueda(self, consultas: int) -> list[float]:
        """Milisegundos de cada búsqueda en la memoria, sin contar la huella de la pregunta.

        Mide la búsqueda entera de cada turno, la que hace el contexto: por
        palabras, por significado y cargar lo encontrado. La huella de la pregunta
        sale de ``_HuellasFijas``, que no tarda nada.
        """
        busqueda = self._dependencias.rank_relevant_knowledge_use_case
        tiempos: list[float] = []
        for n in range(consultas):
            pregunta = f"¿Qué sabes de {_VOCABULARIO[(n * 11) % len(_VOCABULARIO)]}?"
            inicio = time.perf_counter()
            busqueda.rank(pregunta)
            tiempos.append((time.perf_counter() - inicio) * 1000)
        return tiempos

    def con_ollama_espia(self, ollama: OllamaDeMentira) -> None:
        """Enchufa ``ollama`` a lo que Sirius pida a Ollama, sin tocar el modelo de la charla.

        Se queda con todo lo que vaya al Ollama de este ordenador, también lo que
        pida un adaptador con su propia conexión, y Sirius se monta con su modelo
        de huellas de verdad.
        """
        _espia_todo_ollama(ollama)
        self._ollama = ollama
        self._huellas_de_ollama = True
        self.reabre()

    def con_huellas(self, huellas: HuellasDeMentira) -> None:
        """Las huellas para buscar por significado las da ``huellas`` en vez del modelo."""
        self._huellas = huellas
        self.reabre()

    def guarda_recuerdo(self, texto: str) -> None:
        """El propietario guarda un recuerdo, como desde la ventana.

        Con lo que la ventana lanza después en segundo plano: calcular su huella.
        """
        self._dependencias.save_manual_memory_use_case.save(texto)
        self._dependencias.memory_embedding_service.embed_pending()

    def busca_en_la_memoria(self, texto: str) -> list[str]:
        """Los recuerdos que encuentra la búsqueda de Sirius para ``texto``, del mejor al peor."""
        return [
            candidato.item.current_revision.content or ""
            for candidato in self._dependencias.rank_relevant_knowledge_use_case.rank(texto)
            if candidato.kind is KnowledgeKind.MEMORY
        ]

    def huellas_en_la_base(self) -> int:
        """Cuántas huellas de recuerdos hay guardadas en ``sirius.db``, con sqlite-vec."""
        with closing(sqlite3.connect(self.base)) as conexion:
            conexion.enable_load_extension(True)
            sqlite_vec.load(conexion)
            conexion.enable_load_extension(False)
            fila = conexion.execute(
                "SELECT COUNT(*) FROM memory_embeddings WHERE vec_length(embedding) > 0"
            ).fetchone()
        return int(fila[0])

    def categoria_del_recuerdo(self, texto: str) -> str | None:
        """La categoría que tiene guardada el recuerdo ``texto``, o ``None``."""
        with closing(sqlite3.connect(self.base)) as conexion:
            fila = conexion.execute(
                "SELECT m.category FROM memories AS m JOIN memory_revisions AS r"
                " ON r.memory_id = m.id AND r.is_current = 1 WHERE r.content = ?",
                (texto,),
            ).fetchone()
        assert fila is not None, f"no hay ningún recuerdo «{texto}»"
        return cast("str | None", fila[0])

    # --- Pieza G: hechos, fichas, órdenes de memoria y el sueño ---

    def anota_hecho(
        self,
        persona: str,
        tema: str,
        texto: str,
        *,
        desde: date | None = None,
        dicho_por: str = "propietario",
        seguridad: str = "segura",
    ) -> None:
        """El propietario confirma un hecho sobre ``persona``, que dijo ``dicho_por``.

        Por donde entra cualquier hecho: se propone y él dice que sí, como al
        aceptar lo que propone el sueño.
        """
        sugerencia = self._dependencias.fact_proposals.propose(
            ProposedFact(persona, tema, texto, desde, dicho_por, Certainty(seguridad))
        )
        self._dependencias.confirm_memory_suggestion_use_case.confirm(sugerencia.id)

    def hechos_vigentes(self, persona: str = "propietario") -> list[str]:
        return [
            memoria.current_revision.content or ""
            for memoria in self._dependencias.facts_use_case.current(persona)
        ]

    def historia(self, persona: str, tema: str) -> list[TramoDeUnHecho]:
        return [
            TramoDeUnHecho(
                tramo.text,
                tramo.since,
                tramo.until,
                dicho_por=tramo.said_by,
                seguridad=tramo.certainty.value,
            )
            for tramo in self._dependencias.facts_use_case.history(persona, tema)
        ]

    def anota_hecho_desde_la_respuesta(self, respuesta: int) -> str:
        """Intenta guardar como hecho del propietario lo que dijo Sirius; devuelve qué pasó.

        Es «Proponer guardar…» sobre la respuesta número ``respuesta`` de Sirius.
        """
        mensaje = self._resultados[respuesta - 1].sirius_message
        sugerencia = self._dependencias.fact_proposals.propose_from_message(
            mensaje.id, mensaje.content or ""
        )
        return "rechazado" if sugerencia is None else "pendiente"

    def con_extractor(self, extractor: ExtractorDeMentira) -> None:
        self._extractor = extractor
        self.reabre()

    def sueno(self) -> list[HechoPropuesto]:
        """El «sueño» de la noche: lo que propone y queda pendiente.

        Como en su ordenador: con un modelo de Ollama elegido para la charla, que es
        con el que sueña. Sin resumidor enchufado, uno de mentira, para que ninguna
        prueba resuma con el Ollama de verdad.
        """
        ajustes = dict(load_settings())
        ajustes.setdefault("ollama_chat_model", "modelo-local")
        save_settings(ajustes)
        if self._resumidor is None:
            self.con_resumidor(ResumidorDeMentira())
        return [
            HechoPropuesto(propuesto.person, propuesto.topic or "", propuesto.text)
            for propuesto in self._dependencias.dream_service.dream(date.today())
        ]

    def acepta(self, propuesta: HechoPropuesto) -> None:
        """Dice que sí a lo que propuso el sueño, como desde la lista de sugerencias."""
        facts = self._dependencias.facts_use_case
        [sugerencia] = [
            pendiente
            for pendiente in facts.pending_facts()
            if (pendiente.person, pendiente.topic or "", pendiente.content)
            == (propuesta.persona, propuesta.tema, propuesta.texto)
        ]
        self._dependencias.confirm_memory_suggestion_use_case.confirm(sugerencia.id)

    def resumen_del_dia(self) -> str:
        """El resumen del día que dejó el último «sueño»."""
        return self._dependencias.dream_service.latest_summary() or ""

    def ficha(self, nombre: str) -> Ficha:
        ficha = self._dependencias.facts_use_case.card(nombre)
        return Ficha(nombre=ficha.name, hechos=ficha.facts, charlas=ficha.mentions)

    def correcciones_pendientes(self) -> list[tuple[str, str]]:
        """Cada corrección pendiente: el hecho de antes y el texto nuevo."""
        return [
            (correccion.before, correccion.after)
            for correccion in self._dependencias.facts_use_case.pending_corrections()
        ]

    def confirma_las_correcciones(self) -> None:
        """Dice que sí a cada corrección pendiente, como desde la lista de sugerencias."""
        for correccion in self._dependencias.facts_use_case.pending_corrections():
            self._dependencias.confirm_memory_suggestion_use_case.confirm(correccion.suggestion_id)
