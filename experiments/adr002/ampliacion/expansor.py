"""Cuando se amplia una consulta. La politica, separada de la fuente.

DOS POLITICAS, Y LA DIFERENCIA ESTA MEDIDA
==========================================

**Ampliar siempre**: cada consulta se amplia antes de buscar. Da 26/47 aciertos
y 7 omisiones criticas, que es el mejor resultado obtenido en `ADR-002`. Cuesta
una consulta a la fuente por cada busqueda.

**Ampliar solo si la primera busqueda no basto**: se busca con lo que el usuario
escribio; si el motor declara suficiencia distinta de completa, entonces se
amplia y se vuelve a buscar. Da 25/47 y 8 omisiones, y amplia **21 de 47**
consultas en vez de las 47.

Ninguna de las dos es «la buena» y no se elige aqui:

* si la fuente es local y gratuita, ampliar siempre no cuesta nada y da mas;
* si la fuente es un modelo al otro lado de la red, ampliar siempre convierte
  un sistema de memoria personal en algo que **no funciona sin conexion**, y
  entonces pagar un acierto por la mitad de las llamadas y por seguir
  funcionando desconectado es probablemente el mejor trato.

Lo que este modulo garantiza es que la decision sea **explicita y medible**, no
una consecuencia accidental de donde se puso una llamada.

POR QUE EL DISPARADOR NO SE AFINA
=================================

La politica tardia pierde un caso frente a la de siempre, porque en el la
primera busqueda declaro suficiencia completa cuando no lo era. Se podria
buscar un disparador que recuperase ese caso —mirar el numero de resultados,
mezclar condiciones—, y no se hace: afinar el disparador contra el banco es
ajustar la medida al resultado, que es lo que `§8.1` prohibe. El disparador es
el que el motor ya declara, y su coste esta publicado.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from experiments.adr002.ampliacion.fuente import FuenteDeSinonimos, depurar


class Politica(StrEnum):
    """Cuando se llama a la fuente."""

    NUNCA = "NUNCA"
    SIEMPRE = "SIEMPRE"
    #: Solo si la primera busqueda no declaro suficiencia completa.
    SI_NO_BASTO = "SI_NO_BASTO"


#: La unica suficiencia que evita ampliar bajo la politica tardia.
SUFICIENCIA_QUE_BASTA: Final = "COMPLETA"


@dataclass(frozen=True, slots=True)
class Ampliacion:
    """Lo que se hizo con una consulta. Descriptivo: no juzga si estuvo bien."""

    consulta_original: str
    palabras_anadidas: tuple[str, ...]
    se_amplio: bool
    #: Consultas a la fuente que esta peticion provoco. Es el coste real, y se
    #: cuenta en vez de estimarse.
    llamadas_a_la_fuente: int

    @property
    def consulta_final(self) -> str:
        if not self.palabras_anadidas:
            return self.consulta_original
        return f"{self.consulta_original} {' '.join(self.palabras_anadidas)}"


class Expansor:
    """Aplica una politica sobre una fuente. No busca: solo decide las palabras.

    Guarda en memoria lo que ya pregunto: la misma consulta no se paga dos
    veces. Es una cache de proceso, deliberadamente sin persistencia, porque
    persistir sinonimos es un derivado mas y tendria que declararse, borrarse y
    regenerarse como cualquier otro.
    """

    def __init__(self, fuente: FuenteDeSinonimos, politica: Politica = Politica.SIEMPRE) -> None:
        self._fuente = fuente
        self._politica = politica
        self._memoria: dict[str, tuple[str, ...]] = {}
        #: Instrumentacion. Cuantas veces se hablo con la fuente de verdad.
        self.llamadas_a_la_fuente = 0

    @property
    def identificador_de_la_fuente(self) -> str:
        return self._fuente.identificador

    @property
    def politica(self) -> Politica:
        return self._politica

    def _consultar(self, consulta: str) -> tuple[str, ...]:
        if consulta in self._memoria:
            return self._memoria[consulta]
        self.llamadas_a_la_fuente += 1
        palabras = depurar(self._fuente.sinonimos(consulta), consulta)
        self._memoria[consulta] = palabras
        return palabras

    def para(self, consulta: str, *, basto: bool | None = None) -> Ampliacion:
        """Que palabras anadir a esta consulta, segun la politica.

        ``basto`` es el resultado de la primera busqueda y solo lo mira la
        politica tardia. Pedirlo de fuera mantiene a este modulo sin saber
        buscar, que es lo que permite probarlo sin motor.
        """
        antes = self.llamadas_a_la_fuente
        if self._politica is Politica.NUNCA:
            return Ampliacion(consulta, (), False, 0)
        if self._politica is Politica.SI_NO_BASTO and basto is not False:
            # Sin haber buscado —``basto`` nulo— no se amplia: la politica
            # tardia exige una primera busqueda, y adivinarla seria otra
            # politica distinta con el mismo nombre.
            return Ampliacion(consulta, (), False, 0)
        palabras = self._consultar(consulta)
        return Ampliacion(consulta, palabras, bool(palabras), self.llamadas_a_la_fuente - antes)


def recuperar_con_ampliacion(
    peticion: Any,
    buscar: Callable[[Any], Any],
    expansor: Expansor,
) -> tuple[Any, Ampliacion]:
    """Busca aplicando la politica, y devuelve tambien **que se amplio**.

    Devolver la ampliacion junto al resultado no es comodidad: sin ella, una
    respuesta obtenida tras ampliar no puede explicar con que palabras se
    encontro, y `B04-RF-28` exige explicacion por resultado.

    ``buscar`` recibe una peticion y devuelve lo que el motor devuelva. Se pasa
    como funcion para que este modulo no dependa del motor y pueda probarse con
    una busqueda de mentira.
    """
    if expansor.politica is Politica.SIEMPRE:
        ampliacion = expansor.para(peticion.consulta)
        if not ampliacion.se_amplio:
            return buscar(peticion), ampliacion
        return buscar(dataclasses.replace(peticion, consulta=ampliacion.consulta_final)), ampliacion

    primera = buscar(peticion)
    if expansor.politica is Politica.NUNCA:
        return primera, Ampliacion(peticion.consulta, (), False, 0)

    basto = str(getattr(primera, "suficiencia", "")) == SUFICIENCIA_QUE_BASTA
    ampliacion = expansor.para(peticion.consulta, basto=basto)
    if not ampliacion.se_amplio:
        return primera, ampliacion
    return buscar(dataclasses.replace(peticion, consulta=ampliacion.consulta_final)), ampliacion


__all__ = [
    "SUFICIENCIA_QUE_BASTA",
    "Ampliacion",
    "Expansor",
    "Politica",
    "recuperar_con_ampliacion",
]
