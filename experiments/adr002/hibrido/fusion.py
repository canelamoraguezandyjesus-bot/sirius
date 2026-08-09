"""Fusion de rankings por ``RRF``: como se juntan buscar por palabras y por sentido.

``Reciprocal Rank Fusion`` (Cormack, Clarke y Buettcher, 2009) resuelve un
problema real: dos buscadores distintos devuelven **puntuaciones que no son
comparables**. El ``bm25`` de ``FTS5`` da numeros negativos sin cota; el coseno
de un indice vectorial da entre menos uno y uno. Normalizarlos para poder
sumarlos exige conocer sus distribuciones, que cambian con cada consulta.

``RRF`` no mira las puntuaciones: mira **el puesto**. Cada lista aporta
``1 / (k + puesto)`` y los aportes se suman. Un elemento que sale segundo en las
dos listas gana a uno que sale primero en una y no aparece en la otra, que es
justo lo que se quiere de una fusion: **premiar el acuerdo**.

POR QUE ESTO IMPORTA AQUI
=========================

Las dos mitades del problema medido en `ADR-002` se reparten limpiamente:

* la busqueda por palabras acierta con cifras, nombres y codigos —«1.500 €»,
  «PAA-7», «Nimbo»— y falla cuando el usuario usa otras palabras;
* la busqueda por sentido salva la distancia entre «limite de gasto» y
  «presupuesto maximo», y en cambio confunde cifras parecidas.

Ninguna de las dos es mejor: son **complementarias**, y por eso se fusionan en
vez de elegir una.

DETERMINISTA
============

Con las mismas listas de entrada, la salida es la misma, y los empates se
rompen por identidad estable. No hay flotantes en la decision: el orden depende
de puestos, que son enteros, y el desempate final tambien.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

#: La constante de la formula. Sesenta es el valor del articulo original y el
#: que usan los motores que lo implementan. Amortigua los primeros puestos: sin
#: ella, el primero valdria el doble que el segundo y una lista dominaria.
K_POR_DEFECTO: Final = 60


@dataclass(frozen=True, slots=True)
class Aporte:
    """Lo que una lista concreta aporto a un elemento: su puesto y su peso."""

    lista: str
    puesto: int
    aporte: float


@dataclass(frozen=True, slots=True)
class Fusionado:
    """Un elemento del ranking fusionado, con **de donde** viene cada punto.

    ``aportes`` no es decoracion: sin el, una respuesta fusionada no puede
    explicar por que un elemento subio, y ``B04-RF-28`` exige explicacion por
    resultado. Con el, la explicacion es literal: «segundo por palabras, quinto
    por sentido».
    """

    identidad: str
    puntuacion: float
    aportes: tuple[Aporte, ...]

    @property
    def en_cuantas_listas(self) -> int:
        """En cuantas listas aparecio. Dos es acuerdo; una es una sola opinion."""
        return len(self.aportes)


def fusionar(
    listas: Mapping[str, Sequence[str]], *, k: int = K_POR_DEFECTO
) -> tuple[Fusionado, ...]:
    """Fusiona rankings por puesto. Las puntuaciones de origen **no se miran**.

    ``listas`` son rankings ya ordenados de mejor a peor, cada uno con su
    nombre. Un elemento puede estar en una, en varias o en ninguna.

    El empate se rompe por identidad, no por orden de llegada: dos ejecuciones
    sobre las mismas listas devuelven exactamente lo mismo, que es lo que
    permite comparar dos corridas.
    """
    if k <= 0:
        msg = f"k debe ser positivo y llego {k}; con k cero la formula se indefine"
        raise ValueError(msg)

    acumulado: dict[str, list[Aporte]] = {}
    for nombre, ranking in listas.items():
        vistos: set[str] = set()
        for posicion, identidad in enumerate(ranking, start=1):
            # Un duplicado dentro de la misma lista no suma dos veces: seria
            # una lista votando dos veces por lo mismo.
            if identidad in vistos:
                continue
            vistos.add(identidad)
            acumulado.setdefault(identidad, []).append(
                Aporte(lista=nombre, puesto=posicion, aporte=1.0 / (k + posicion))
            )

    fusionados = [
        Fusionado(
            identidad=identidad,
            puntuacion=sum(a.aporte for a in aportes),
            aportes=tuple(sorted(aportes, key=lambda a: a.lista)),
        )
        for identidad, aportes in acumulado.items()
    ]
    # Mayor puntuacion primero; a igualdad, identidad estable.
    fusionados.sort(key=lambda f: (-f.puntuacion, f.identidad))
    return tuple(fusionados)


def explicar(fusionado: Fusionado) -> str:
    """Frase legible de por que un elemento quedo donde quedo (``RF-28``)."""
    partes = [f"{a.puesto}.º por {a.lista}" for a in fusionado.aportes]
    return " y ".join(partes) if partes else "sin aportes"


__all__ = ["K_POR_DEFECTO", "Aporte", "Fusionado", "explicar", "fusionar"]
