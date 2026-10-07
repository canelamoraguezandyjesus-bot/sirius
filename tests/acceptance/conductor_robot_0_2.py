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
import sqlite3
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, TypeVar, cast

import httpx
import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.send_message import SendMessageResult
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.settings import save_settings
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMStreamEvent, LLMTextDelta

#: Las letras de la tabla de piezas de ADR-233 que ya han entrado en ``main``.
#: La A es esta: la nota de arranque y estas pruebas.
PIEZAS_ENTREGADAS: frozenset[str] = frozenset({"A"})

#: Qué trae cada pieza, con las palabras de la tabla de ADR-233.
PIEZAS: Mapping[str, str] = {
    "A": "la nota de arranque y las pruebas de aceptación",
    "B": "la semilla",
    "C": "Ollama para la charla y la prueba a ciegas",
    "D": "«ponte serio» y «para», lo de la deriva y los dos botones",
    "E": "la memoria propia de Sirius, el juez y las 40 preguntas trampa",
    "F": "el banco de memoria de 100 casos y la búsqueda por significado",
    "G": "hechos con fecha y con quién lo dijo, fichas, órdenes de memoria y el sueño",
}

_Prueba = TypeVar("_Prueba", bound=Callable[..., object])


class PiezaPendiente(NotImplementedError):
    """La pieza de ADR-233 que haría esto todavía no ha entrado."""

    def __init__(self, letra: str) -> None:
        super().__init__(f"pieza {letra} de ADR-233 pendiente: {PIEZAS[letra]}")
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
            f"Pieza {letra} de ADR-233 ({PIEZAS[letra]}): {que}. Cuando entre, se "
            "añade su letra a PIEZAS_ENTREGADAS y esta marca desaparece."
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

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(Peticion(request.instructions, request.input_text))
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
    urls: list[httpx.URL] = field(default_factory=list)
    modelos: list[str] = field(default_factory=list)

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
        if request.url.path == "/api/chat":
            lineas = [
                {"message": {"role": "assistant", "content": self.respuesta}, "done": False},
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


class VentanaDePrueba:
    """La ventana de conversación de Sirius, vista desde una prueba (pieza D)."""

    def botones_de_la_respuesta(self, numero: int) -> tuple[str, ...]:
        raise _pendiente("D")

    def pulsa(self, numero: int, boton: str) -> None:
        raise _pendiente("D")

    def indicador_de_modo(self) -> str:
        raise _pendiente("D")

    def quita_el_modo(self) -> None:
        raise _pendiente("D")

    def escribe(self, texto: str) -> None:
        """El propietario escribe ``texto`` en la ventana y espera a que acabe todo el turno."""
        raise _pendiente("D")

    def aviso_del_juez(self) -> str:
        """El aviso del juez tal como se ve; vacío si no se ve."""
        raise _pendiente("E")

    def espera_al_trabajo_de_fondo(self) -> None:
        """Espera a que acabe lo que la ventana haya lanzado en segundo plano."""
        raise _pendiente("F")

    def ofrece_etiquetar_por_categorias(self) -> bool:
        """Si la ventana deja poner o pedir la categoría de un recuerdo."""
        raise _pendiente("F")


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

    def _montar(self) -> ConversationDependencies:
        dependencias = build_conversation_dependencies(
            self.base, self.carpeta / "copias", secret_store=FakeSecretStore()
        )
        dependencias.send_message_use_case.set_llm_provider(self._grabador)
        return dependencias

    # --- Lo que ya existe en Sirius ---

    def di(self, texto: str) -> str:
        """El propietario escribe ``texto``; devuelve lo que contesta Sirius."""
        self._peticiones_antes_del_ultimo_turno = len(self._grabador.peticiones)
        resultado = self._dependencias.send_message_use_case.send_message(texto)
        self._resultados.append(resultado)
        # Un mensaje borrado guarda su contenido como None (PA-016).
        return resultado.sirius_message.content or ""

    @property
    def peticiones(self) -> list[Peticion]:
        """Todo lo que ha recibido el modelo de la charla, en orden."""
        return list(self._grabador.peticiones)

    def hubo_peticion_al_modelo_en_el_ultimo_turno(self) -> bool:
        return len(self._grabador.peticiones) > self._peticiones_antes_del_ultimo_turno

    def reabre(self) -> None:
        """Cierra Sirius y lo vuelve a abrir sobre la misma base."""
        self._dependencias.close_database_connections()
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
        """Una base de 0.1, con la identidad v1 y la semilla vieja, que se abre ya con la 0.2."""
        raise _pendiente("B")

    def semilla_del_robot(self) -> Semilla:
        raise _pendiente("B")

    def identidad_vigente(self) -> tuple[int, str]:
        """La versión vigente de la identidad y su texto de personalidad."""
        raise _pendiente("B")

    def identidad_en_la_version(self, version: int) -> str:
        raise _pendiente("B")

    # --- Pieza C: Ollama para la charla y la prueba a ciegas ---

    def charla_por_ollama(self, modelo: str, ollama: OllamaDeMentira) -> None:
        """Elige Ollama para la charla con ``modelo``, servido por ``ollama``."""
        raise _pendiente("C")

    def preguntas_de_la_prueba_a_ciegas(self) -> tuple[str, ...]:
        raise _pendiente("C")

    def prueba_a_ciegas(self, respuestas_por_modelo: Mapping[str, Sequence[str]]) -> HojaACiegas:
        """Prepara la hoja: cada modelo contesta las preguntas con sus respuestas."""
        raise _pendiente("C")

    def elige_a_ciegas(self, hoja: HojaACiegas, elecciones: Mapping[int, str]) -> str:
        """El propietario elige una letra por pregunta; devuelve el modelo ganador."""
        raise _pendiente("C")

    def modelo_de_la_charla(self) -> str | None:
        raise _pendiente("C")

    # --- Pieza D: modos, deriva y botones ---

    def texto_del_modo(self, modo: str) -> str:
        """Lo que Sirius añade a las instrucciones en el modo ``serio`` o ``para``."""
        raise _pendiente("D")

    def texto_al_entrar_en_modo_serio(self) -> str:
        """Lo que Sirius añade solo en el turno en que entra en el modo serio: el vacile."""
        raise _pendiente("D")

    def recordatorio_de_la_semilla(self) -> str:
        raise _pendiente("D")

    def con_resumidor(self, resumidor: ResumidorDeMentira) -> None:
        raise _pendiente("D")

    def marca(self, respuesta: int, marca: str) -> None:
        """Pulsa «eso es Sirius» o «eso no» en la respuesta ``respuesta`` (desde 1)."""
        raise _pendiente("D")

    def marcas(self) -> list[tuple[int, str]]:
        raise _pendiente("D")

    def detalle_de_la_marca(self, respuesta: int) -> Mapping[str, object]:
        """Con qué versión de la identidad y con qué modelo se dio la respuesta marcada."""
        raise _pendiente("D")

    def cuenta_de_marcas(self, ultimas: int) -> tuple[int, int]:
        """Cuántas «eso es Sirius» hay entre las ``ultimas`` marcadas, y cuántas marcadas."""
        raise _pendiente("D")

    def marcas_posibles(self) -> frozenset[str]:
        raise _pendiente("D")

    def ventana(self, qtbot: Any) -> VentanaDePrueba:
        raise _pendiente("D")

    # --- Pieza E: memoria propia, juez y preguntas trampa ---

    def sirius_opino(self, texto: str) -> None:
        """Guarda una opinión que Sirius ya dio."""
        raise _pendiente("E")

    def encabezado_de_lo_que_no_es(self) -> str:
        raise _pendiente("E")

    def encabezado_de_lo_que_si_es(self) -> str:
        raise _pendiente("E")

    def con_juez(self, juez: JuezDeMentira) -> None:
        raise _pendiente("E")

    def notas_del_juez(self) -> list[int]:
        raise _pendiente("E")

    def avisos_del_juez(self) -> list[int]:
        """Las respuestas (desde 1) tras las que el juez avisó de que Sirius baja."""
        raise _pendiente("E")

    def banco_de_preguntas_trampa(self) -> tuple[PreguntaTrampa, ...]:
        raise _pendiente("E")

    def pasa_el_banco_de_preguntas_trampa(self, juez: JuezDeMentira) -> Mapping[str, str]:
        """Cada pregunta trampa, con el veredicto del juez sobre la respuesta."""
        raise _pendiente("E")

    # --- Pieza F: banco de memoria y búsqueda por significado ---

    def banco_de_memoria(self) -> tuple[CasoDeMemoria, ...]:
        raise _pendiente("F")

    def pasa_el_banco_de_memoria(self) -> Mapping[str, tuple[int, int]]:
        """Aciertos y casos por familia, con el camino real y un buscador determinista."""
        raise _pendiente("F")

    def llena_la_memoria(self, recuerdos: int) -> None:
        raise _pendiente("F")

    def mide_la_busqueda(self, consultas: int) -> list[float]:
        """Milisegundos de cada búsqueda en la memoria, sin contar la huella de la pregunta."""
        raise _pendiente("F")

    def con_ollama_espia(self, ollama: OllamaDeMentira) -> None:
        """Enchufa ``ollama`` a lo que Sirius pida a Ollama, sin tocar el modelo de la charla."""
        raise _pendiente("F")

    def con_huellas(self, huellas: HuellasDeMentira) -> None:
        """Las huellas para buscar por significado las da ``huellas`` en vez del modelo."""
        raise _pendiente("F")

    def guarda_recuerdo(self, texto: str) -> None:
        """El propietario guarda un recuerdo, como desde la ventana."""
        raise _pendiente("F")

    def busca_en_la_memoria(self, texto: str) -> list[str]:
        """Los recuerdos que encuentra la búsqueda de Sirius para ``texto``, del mejor al peor."""
        raise _pendiente("F")

    def huellas_en_la_base(self) -> int:
        """Cuántas huellas de recuerdos hay guardadas en ``sirius.db``, con sqlite-vec."""
        raise _pendiente("F")

    def categoria_del_recuerdo(self, texto: str) -> str | None:
        """La categoría que tiene guardada el recuerdo ``texto``, o ``None``."""
        raise _pendiente("F")

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
        """El propietario confirma un hecho sobre ``persona``, que dijo ``dicho_por``."""
        raise _pendiente("G")

    def hechos_vigentes(self, persona: str = "propietario") -> list[str]:
        raise _pendiente("G")

    def historia(self, persona: str, tema: str) -> list[TramoDeUnHecho]:
        raise _pendiente("G")

    def anota_hecho_desde_la_respuesta(self, respuesta: int) -> str:
        """Intenta guardar como hecho del propietario lo que dijo Sirius; devuelve qué pasó."""
        raise _pendiente("G")

    def con_extractor(self, extractor: ExtractorDeMentira) -> None:
        raise _pendiente("G")

    def sueno(self) -> list[HechoPropuesto]:
        """El «sueño» de la noche: lo que propone y queda pendiente."""
        raise _pendiente("G")

    def acepta(self, propuesta: HechoPropuesto) -> None:
        raise _pendiente("G")

    def resumen_del_dia(self) -> str:
        """El resumen del día que dejó el último «sueño»."""
        raise _pendiente("G")

    def ficha(self, nombre: str) -> Ficha:
        raise _pendiente("G")

    def correcciones_pendientes(self) -> list[tuple[str, str]]:
        """Cada corrección pendiente: el hecho de antes y el texto nuevo."""
        raise _pendiente("G")

    def confirma_las_correcciones(self) -> None:
        raise _pendiente("G")
