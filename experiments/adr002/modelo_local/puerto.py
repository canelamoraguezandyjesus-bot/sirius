"""El puerto del modelo local. Dos miembros, y el proveedor fuera.

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

Y sirve para las dos mitades con **una sola pieza**: al guardar escribe las
preguntas que un dato responde —que es lo que hace que entre lo que hoy no
entra— y al buscar elige cuales responden de verdad —que es lo que quita la
basura—.

LO QUE EL MODELO NO PUEDE HACER, POR DISENO
===========================================

**No escribe recuerdos.** Nunca. Solo elige entre lo que el canon ya contiene, y
escribe palabras de busqueda que se guardan como derivado borrable. Un modelo
que pudiera anadir contenido podria inventarse una memoria, y ese es el fallo
que `HaluMem` mide en todos los sistemas del sector: alucinan y omiten al
extraer y al actualizar, y el error se propaga.

Aqui esa puerta esta cerrada por la forma del puerto: ``preguntar`` devuelve
texto, y quien lo llama solo lo usa para **seleccionar identidades ya existentes**
o para **generar terminos de busqueda**. Nada de lo que el modelo diga entra en
el canon como hecho.

LOCAL, Y POR ESO SIN CUOTA Y SIN RED
====================================

La implementacion de referencia habla con un servidor local por HTTP en la
maquina del usuario. Que exponga una interfaz compatible con la de los
proveedores de pago es una comodidad, no una dependencia: el modelo, los pesos y
los datos no salen del equipo.
"""

from __future__ import annotations

import json
from typing import Final, Protocol, runtime_checkable

#: Direccion por defecto del servidor local. Es la de `Ollama`, que es lo que la
#: investigacion de laboratorio propone y lo que corre sin configuracion.
SERVIDOR_POR_DEFECTO: Final = "http://localhost:11434/v1"

#: Modelo por defecto. Se declara aqui y viaja al artefacto de resultados: dos
#: corridas con modelos distintos no son comparables y hay que poder verlo.
MODELO_POR_DEFECTO: Final = "qwen3:14b"

#: Cuanto se espera a una respuesta. Un filtro que tarda mas que la busqueda
#: entera deja de ser un filtro y pasa a ser el cuello de botella.
SEGUNDOS_MAXIMOS: Final = 30.0


class ModeloNoDisponibleError(RuntimeError):
    """El modelo local no responde.

    Error **tipado**, nunca una degradacion silenciosa. Quien llama decide que
    hacer, y en el filtro la decision correcta es dejar pasar todo: perder un
    elemento critico en silencio es peor que entregar de mas.
    """


@runtime_checkable
class ModeloLocal(Protocol):
    """Lo unico que hace falta de un modelo. Dos miembros.

    Que sea tan estrecho es el punto: ni el filtro ni la ingesta saben que hay
    detras, y cambiar de modelo es cambiar el objeto que se les pasa.
    """

    @property
    def identificador(self) -> str:
        """Nombre y version del modelo. Viaja a los resultados."""
        ...

    def preguntar(self, instruccion: str, entrada: str) -> str:
        """Respuesta en texto. Determinista en lo que el proveedor permita."""
        ...


class ModeloOllama:
    """Un modelo servido en local. No sale nada del equipo."""

    def __init__(
        self,
        *,
        modelo: str = MODELO_POR_DEFECTO,
        servidor: str = SERVIDOR_POR_DEFECTO,
        cliente: object | None = None,
    ) -> None:
        self._modelo = modelo
        self._servidor = servidor
        if cliente is not None:
            # Inyectable para poder probar el cauce entero sin servidor.
            self._cliente = cliente
            return
        try:
            from openai import OpenAI
        except ImportError as fallo:  # pragma: no cover - depende de la maquina
            msg = "falta el paquete 'openai'; se usa solo como cliente HTTP del servidor local"
            raise ModeloNoDisponibleError(msg) from fallo
        # La clave es un relleno: el servidor local no la mira. Se pone una
        # constante y no una real para que no pueda colarse una de pago aqui.
        self._cliente = OpenAI(base_url=servidor, api_key="local", timeout=SEGUNDOS_MAXIMOS)

    @property
    def identificador(self) -> str:
        return f"local:{self._modelo}"

    def preguntar(self, instruccion: str, entrada: str) -> str:
        try:
            respuesta = self._cliente.chat.completions.create(  # type: ignore[attr-defined]
                model=self._modelo,
                messages=[
                    {"role": "system", "content": instruccion},
                    {"role": "user", "content": entrada},
                ],
                temperature=0,
            )
        except Exception as fallo:  # pragma: no cover - depende de la maquina
            msg = f"el modelo local no respondio en {self._servidor}"
            raise ModeloNoDisponibleError(msg) from fallo
        return str(respuesta.choices[0].message.content or "")


def numeros_de(texto: str, *, tope: int) -> tuple[int, ...] | None:
    """Los numeros de una respuesta del modelo, o ``None`` si no se entiende.

    Devolver ``None`` en vez de una lista vacia **importa**: vacio significa «el
    modelo dijo que ninguno responde», y no entenderle significa «no se lo que
    dijo». Confundirlos convertiria un fallo de formato en un descarte de todo,
    que es exactamente la perdida silenciosa que hay que evitar.
    """
    try:
        crudo = json.loads(texto[texto.index("{") : texto.rindex("}") + 1])
    except ValueError, json.JSONDecodeError:
        return None
    elegidos = crudo.get("responden")
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
    "MODELO_POR_DEFECTO",
    "SEGUNDOS_MAXIMOS",
    "SERVIDOR_POR_DEFECTO",
    "ModeloLocal",
    "ModeloNoDisponibleError",
    "ModeloOllama",
    "numeros_de",
]
