"""El puerto del modelo local. Habla con Ollama por su API nativa.

POR QUE UN MODELO Y NO UN FILTRO DE PARECIDO
============================================

Lo que se iba a montar antes era un reordenador por similitud: un modelo pequeno
que puntua cuanto se parece la pregunta a cada candidato. Arregla la basura
obvia, pero **no lee**. En el ruido medido sobre el banco hay dos formas que un
medidor de parecido no puede tocar:

* **polaridad**: «no uses vuelos con escala» y «acepta escala si ahorra 200 €»
  se parecen muchisimo a «¿acepto escalas?». Las dos. Un parecido alto no dice
  cual responde;
* **tiempo**: «¿que decision de presupuesto usabamos ANTES?» se parece mas a la
  decision vigente que a la derogada, porque el texto vigente es el que habla de
  presupuesto en presente.

Un modelo que entiende la frase si distingue las dos. Por eso el filtro es un
modelo, no una metrica.

POR QUE LA API NATIVA Y NO LA DE COMPATIBILIDAD
===============================================

`Ollama` expone dos interfaces: una compatible con la de los proveedores de pago
en ``/v1``, y la suya propia en ``/api/chat``. Se usa **la suya**, y no por
gusto: solo ella acepta ``format`` con un esquema JSON, que hace que una
respuesta mal formada sea **mecanicamente imposible** en vez de improbable.

La version anterior pedia el formato por escrito en la instruccion y confiaba en
que el modelo obedeciera. Con un modelo pequeno eso falla, y falla justo cuando
mas importa. El esquema lo garantiza el servidor.

Tambien es la unica que acepta ``think``, que apaga el modo razonador. Un modelo
razonando escribe parrafos de pensamiento antes de contestar y tarda mucho mas;
estas dos tareas son clasificacion corta y no lo necesitan.

LO QUE EL MODELO NO PUEDE HACER, POR DISENO
===========================================

**No escribe recuerdos.** Nunca. Solo elige entre lo que el canon ya contiene, y
escribe palabras de busqueda que se guardan como derivado borrable. Un modelo
que pudiera anadir contenido podria inventarse una memoria, y ese es el fallo
que `HaluMem` mide en todos los sistemas del sector: alucinan y omiten al
extraer y al actualizar, y el error se propaga hasta la respuesta.

LOCAL, Y POR ESO SIN CUOTA Y SIN RED
====================================

El servidor corre en la maquina de quien usa Sirius. El modelo, los pesos y los
datos no salen del equipo. Introducir ese servidor es una decision del
responsable del proyecto y no del codigo: `AGENTS.md` obliga a detenerse antes
de «introducir otro proceso, servidor, agente o base de datos», y aqui se hace
porque esta pedido por escrito en la especificacion de la entrega.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, Protocol, runtime_checkable

#: Direccion por defecto del servidor local.
SERVIDOR_POR_DEFECTO: Final = "http://localhost:11434"

#: Modelo por defecto. Cuatro mil millones de parametros, cuantizado, para que
#: quepa **entero** en una grafica de portatil de 6 GB. Uno de catorce mil
#: millones no cabe y se parte entre grafica y procesador, que es lo que hace
#: que estas tareas pasen de segundos a minutos.
MODELO_POR_DEFECTO: Final = "qwen3:4b-instruct"

#: Cuanto texto cabe de una vez. Se fija en vez de heredar el del servidor: con
#: treinta frases mas la instruccion, el valor que trae por defecto se queda
#: corto y el modelo deja de ver el final de la lista **sin avisar**.
CONTEXTO_POR_DEFECTO: Final = 8192

#: Cuanto se queda el modelo cargado entre peticiones. Sin esto, cada busqueda
#: paga la carga entera del modelo desde disco.
PERMANENCIA_POR_DEFECTO: Final = "15m"

#: Temperatura baja, no cero: algunos servidores tratan el cero como «usa tu
#: valor por defecto». Baja y explicita es reproducible de verdad.
TEMPERATURA_POR_DEFECTO: Final = 0.1

#: Cuanto se espera, por tarea. Filtrar ocurre en cada busqueda y el responsable
#: fijo cinco segundos de presupuesto; diez es el punto en que ya se declara
#: fallo. Generar preguntas ocurre una vez al guardar y puede permitirse mas.
ESPERA_FILTRO: Final = 10.0
ESPERA_PREGUNTAS: Final = 30.0

#: Un solo reintento, y con pausa. Dos serian disimular un servidor que no esta.
REINTENTOS: Final = 1
PAUSA_ENTRE_INTENTOS: Final = 0.5


class ModeloNoDisponibleError(RuntimeError):
    """El modelo local no responde, o no esta instalado.

    Error **tipado y en castellano**, nunca una degradacion silenciosa. Quien
    llama decide que hacer, y las dos tareas deciden distinto **a proposito**:
    el filtro deja pasar todo y la ingesta no indexa nada.
    """


class RespuestaInvalidaError(RuntimeError):
    """El servidor contesto algo que no encaja con el esquema pedido.

    Con ``format`` esto no deberia ocurrir. Existe como defensa: si algun dia
    ocurre, se entera alguien en vez de colarse un dato a medias.
    """


@dataclass(frozen=True, slots=True)
class InfoModelo:
    """Quien contesto. Viaja a la procedencia de todo lo que se genere.

    La ``huella`` es el identificador que el servidor da a los pesos concretos.
    Sin ella, «qwen3:4b» de hoy y «qwen3:4b» de dentro de tres meses parecen lo
    mismo en un fichero de resultados y no lo son. `TOL-207` exige poder
    regenerar un derivado; para eso hay que saber **con que** se genero.
    """

    proveedor: str
    modelo: str
    huella: str

    @property
    def completo(self) -> str:
        return f"{self.proveedor}:{self.modelo}@{self.huella}"


@runtime_checkable
class ProveedorIA(Protocol):
    """Lo unico que hace falta de un proveedor de modelo. Dos operaciones."""

    def info_modelo(self) -> InfoModelo:
        """Quien es y con que pesos. Se consulta al servidor, no se supone."""
        ...

    def responder_json(
        self, instruccion: str, entrada: str, esquema: Mapping[str, Any], *, espera: float
    ) -> Mapping[str, Any]:
        """Respuesta que **cumple el esquema**, garantizada por el servidor."""
        ...


class ProveedorOllama:
    """Cliente de la API nativa de `Ollama`. Sin dependencias nuevas.

    Usa la biblioteca estandar en vez de un cliente HTTP de terceros: son dos
    peticiones con JSON, y anadir una dependencia al laboratorio obliga a
    regenerar el fichero de bloqueo del proyecto, que la validacion de calidad
    comprueba con ``--locked`` y rompe en seco si no cuadra.
    """

    def __init__(
        self,
        *,
        modelo: str = MODELO_POR_DEFECTO,
        servidor: str = SERVIDOR_POR_DEFECTO,
        temperatura: float = TEMPERATURA_POR_DEFECTO,
        contexto: int = CONTEXTO_POR_DEFECTO,
        permanencia: str = PERMANENCIA_POR_DEFECTO,
        transporte: Any | None = None,
    ) -> None:
        self._modelo = modelo
        self._servidor = servidor.rstrip("/")
        self._temperatura = temperatura
        self._contexto = contexto
        self._permanencia = permanencia
        #: Inyectable para probar el cauce entero sin servidor. Recibe
        #: ``(ruta, cuerpo, espera)`` y devuelve el JSON de respuesta.
        self._transporte = transporte
        self._info: InfoModelo | None = None

    def _pedir(self, ruta: str, cuerpo: Mapping[str, Any], espera: float) -> Mapping[str, Any]:
        """Una peticion, con **un** reintento. La espera se aplica siempre.

        Que el limite de tiempo valga tambien con transporte inyectado no es un
        detalle: en la version anterior se saltaba justo en las pruebas, de modo
        que lo unico comprobado era el camino que en produccion no se usa.
        """
        ultimo: Exception | None = None
        for intento in range(REINTENTOS + 1):
            try:
                if self._transporte is not None:
                    return dict(self._transporte(ruta, cuerpo, espera))
                peticion = urllib.request.Request(
                    f"{self._servidor}{ruta}",
                    data=json.dumps(cuerpo).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(peticion, timeout=espera) as respuesta:
                    return dict(json.loads(respuesta.read().decode("utf-8")))
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as fallo:
                ultimo = fallo
                if intento < REINTENTOS:
                    time.sleep(PAUSA_ENTRE_INTENTOS)
        msg = (
            f"el modelo local no respondio en {self._servidor}. Comprueba que Ollama "
            f"este arrancado y que el modelo «{self._modelo}» este descargado."
        )
        raise ModeloNoDisponibleError(msg) from ultimo

    def info_modelo(self) -> InfoModelo:
        """Nombre y huella de los pesos, preguntados al servidor.

        Se recuerda: la huella no cambia mientras el proceso vive, y preguntarla
        por cada dato guardado seria una peticion de red por elemento.
        """
        if self._info is not None:
            return self._info
        crudo = self._pedir("/api/show", {"model": self._modelo}, ESPERA_FILTRO)
        detalles = crudo.get("details")
        de_detalles = detalles.get("digest") if isinstance(detalles, Mapping) else None
        huella = str(crudo.get("digest") or de_detalles or "desconocida")
        self._info = InfoModelo(proveedor="ollama", modelo=self._modelo, huella=huella)
        return self._info

    def responder_json(
        self, instruccion: str, entrada: str, esquema: Mapping[str, Any], *, espera: float
    ) -> Mapping[str, Any]:
        """Respuesta conforme al esquema. El servidor la restringe al generarla."""
        cuerpo: dict[str, Any] = {
            "model": self._modelo,
            "messages": [
                {"role": "system", "content": instruccion},
                {"role": "user", "content": entrada},
            ],
            "stream": False,
            "format": dict(esquema),
            #: Apaga el modo razonador. Sin esto, un modelo de la familia Qwen3
            #: escribe su pensamiento antes de contestar y estas tareas pasan de
            #: segundos a minutos.
            "think": False,
            "keep_alive": self._permanencia,
            "options": {"temperature": self._temperatura, "num_ctx": self._contexto},
        }
        crudo = self._pedir("/api/chat", cuerpo, espera)
        mensaje = crudo.get("message")
        contenido = mensaje.get("content") if isinstance(mensaje, Mapping) else None
        if not isinstance(contenido, str) or not contenido.strip():
            msg = "el servidor devolvio una respuesta vacia"
            raise RespuestaInvalidaError(msg)
        try:
            leido = json.loads(contenido)
        except json.JSONDecodeError as fallo:
            msg = "el servidor devolvio algo que no es JSON pese al esquema pedido"
            raise RespuestaInvalidaError(msg) from fallo
        if not isinstance(leido, dict):
            msg = "el servidor devolvio JSON que no es un objeto"
            raise RespuestaInvalidaError(msg)
        return leido


def enteros_validos(crudo: Mapping[str, Any], clave: str, *, tope: int) -> tuple[int, ...] | None:
    """Los enteros de un campo, o ``None`` si el campo no es utilizable.

    Devolver ``None`` en vez de una lista vacia **importa**: vacio significa «el
    modelo dijo que ninguno», y ``None`` significa «no se lo que dijo».
    Confundirlos convertiria un fallo de formato en un descarte de todo, que es
    exactamente la perdida silenciosa que hay que evitar.
    """
    elegidos = crudo.get(clave)
    if not isinstance(elegidos, list):
        return None
    salida: list[int] = []
    for elemento in elegidos:
        if not isinstance(elemento, int) or isinstance(elemento, bool):
            return None
        if 1 <= elemento <= tope and elemento not in salida:
            salida.append(elemento)
    return tuple(salida)


__all__ = [
    "CONTEXTO_POR_DEFECTO",
    "ESPERA_FILTRO",
    "ESPERA_PREGUNTAS",
    "MODELO_POR_DEFECTO",
    "PAUSA_ENTRE_INTENTOS",
    "PERMANENCIA_POR_DEFECTO",
    "REINTENTOS",
    "SERVIDOR_POR_DEFECTO",
    "TEMPERATURA_POR_DEFECTO",
    "InfoModelo",
    "ModeloNoDisponibleError",
    "ProveedorIA",
    "ProveedorOllama",
    "RespuestaInvalidaError",
    "enteros_validos",
]
