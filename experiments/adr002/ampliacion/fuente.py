"""De donde salen los sinonimos. El proveedor, detras de un puerto de dos miembros.

QUE PROBLEMA RESUELVE, MEDIDO
=============================

La ampliacion de consulta es lo unico que ha movido el resultado en `ADR-002`:
24/47 aciertos y 11 omisiones criticas pasan a 26/47 y 7, sin ninguna regresion.
Pero las 47 ampliaciones que lo consiguieron **las escribi a mano**, una por
caso del banco, y eso no es un sistema: es una tabla que no sirve para la
consulta 48.

Lo que hace falta es que las palabras salgan solas. Este modulo dice **de
donde**.

LO QUE SE MIDIO ANTES DE ESCRIBIR ESTO
======================================

Las 177 palabras que escribi se parten en dos por un criterio mecanico —si
comparten raiz con alguna palabra de la consulta o no— y cada mitad se mide por
separado:

* las 97 **derivables por morfologia**: 24/47 y 11 omisiones, es decir
  **exactamente la linea base**. No aportan absolutamente nada, y tiene sentido:
  el motor ya hace morfologia en `E2`, asi que eran trabajo repetido;
* las 80 **palabras distintas** —sinonimos, hiperonimos, asociaciones—: 26/47 y
  7 omisiones, o sea **la ganancia entera**.

De modo que lo que hay que producir esta acotado y nombrado: no variantes de la
misma palabra, sino **otra palabra que quiera decir lo mismo**. Un derivador
morfologico no puede darla por construccion, y por eso este puerto existe.

POR QUE UN PUERTO Y NO UNA IMPLEMENTACION
=========================================

Porque todavia no se sabe quien gana, y comprometerse ahora seria decidir sin
medir. Un diccionario de sinonimos local seria gratis y sin red, pero es dudoso
que contenga las asociaciones que hacen falta: «presupuesto» no es sinonimo de
«gasto» en ningun diccionario, y sin embargo es la palabra que resuelve el caso
que lleva bloqueando esto desde el principio. Un modelo si tiene esa
asociacion. Con el puerto, cambiar de opinion es cambiar de objeto.
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

#: Cuantas palabras como mucho se anaden a una consulta. No es decoracion: cada
#: palabra anadida es vocabulario que puede traer elementos de mas, y la
#: contaminacion es fallo duro. Existe para acotar a una fuente que genere sin
#: freno, no para recortar la referencia.
#:
#: Doce, y el numero tiene procedencia. La tabla escrita a mano llega a **diez**
#: palabras en un caso, asi que un tope por debajo de diez la mutila: puesto en
#: ocho —como estuvo primero, por una lectura mia equivocada de la tabla— el
#: control dejaba de reproducir su cifra publicada y pasaba de 7 omisiones
#: criticas a 9, cortando justamente las palabras de los tres casos que el
#: propio artefacto senala como los que cargan el peso.
#:
#: No es un umbral ajustado al resultado: se fija **por encima del maximo de la
#: referencia**, que es un dato de la tabla y no una cifra de acierto, y el
#: criterio es que el control tiene que reproducirse intacto. Un control que no
#: reproduce su cifra no sirve para comparar nada.
PALABRAS_MAXIMAS: Final = 12

#: Longitud minima de una palabra util. Las de una o dos letras son articulos y
#: preposiciones: no discriminan y solo ensanchan la busqueda.
LONGITUD_MINIMA: Final = 3


class FuenteNoDisponibleError(RuntimeError):
    """La fuente pedida no puede usarse aqui.

    Error **tipado y explicito**, nunca una degradacion silenciosa a «no amplio
    nada»: un sistema que dice haber ampliado y no lo hizo mide una cosa
    distinta de la que declara y lo hace sin que nadie se entere.
    """


@runtime_checkable
class FuenteDeSinonimos(Protocol):
    """Lo unico que la ampliacion necesita saber de un proveedor. Dos miembros."""

    @property
    def identificador(self) -> str:
        """Nombre y version de la fuente. Viaja al artefacto de resultados."""
        ...

    def sinonimos(self, consulta: str) -> tuple[str, ...]:
        """Palabras con las que ampliar. **Solo ve la consulta.**

        Esa frontera es la que hace que un buen resultado signifique algo: una
        fuente que viera el canon podria devolver justo lo que hay que
        encontrar, y entonces no se estaria midiendo una ampliacion sino un
        oraculo.
        """
        ...


def normalizar(palabra: str) -> str:
    """Minusculas y sin diacriticos, como el indice lexico las guarda."""
    plegada = unicodedata.normalize("NFKD", palabra.strip().lower())
    return "".join(c for c in plegada if not unicodedata.combining(c))


def depurar(palabras: Sequence[str], consulta: str) -> tuple[str, ...]:
    """Limpia lo que una fuente devuelve. Comun a todas, y por eso vive aqui.

    Quita lo vacio, lo corto, lo repetido y lo que ya estaba en la consulta
    —ampliar con una palabra que ya se busco no amplia nada—, y corta al tope.
    Que la cota se aplique aqui y no en cada implementacion evita que un
    proveedor nuevo se salte el limite por descuido.
    """
    ya = {normalizar(p) for p in consulta.split()}
    salida: list[str] = []
    for palabra in palabras:
        limpia = normalizar(palabra)
        if len(limpia) < LONGITUD_MINIMA or limpia in ya or limpia in salida:
            continue
        if not limpia.isalnum():
            continue
        salida.append(limpia)
        if len(salida) == PALABRAS_MAXIMAS:
            break
    return tuple(salida)


class SinonimosNulos:
    """No amplia nada. Es el control: con esta fuente hay que dar la linea base.

    Sin ella, un cambio en el cauce de ampliacion podria mover cifras sin que
    nadie supiera si lo movio la fuente o la cañeria.
    """

    identificador: Final = "sin-ampliacion"

    def sinonimos(self, consulta: str) -> tuple[str, ...]:
        return ()


class SinonimosDeTabla:
    """Las palabras escritas a mano, leidas de un fichero congelado.

    **No es una solucion productiva y no se propone como tal.** Es la referencia
    contra la que se mide cualquier fuente automatica: si una fuente que se
    inventa las palabras iguala a esta, se puede tirar la tabla; si no la
    iguala, la diferencia dice exactamente cuanto falta.

    Indexa por **consulta**, no por identificador de caso: una tabla indexada
    por caso solo funciona sobre el banco, y aqui se quiere poder preguntarle
    por una consulta cualquiera para que el control sea comparable.
    """

    identificador: Final = "tabla-escrita-a-mano-v0.1"

    def __init__(self, por_consulta: Mapping[str, Sequence[str]]) -> None:
        self._por_consulta = {normalizar(k): tuple(v) for k, v in por_consulta.items()}

    @classmethod
    def desde_artefacto(cls, ruta: Path, consultas: Mapping[str, str]) -> SinonimosDeTabla:
        """Carga el artefacto congelado y lo reindexa por texto de consulta.

        ``consultas`` traduce identificador de caso a su texto. Se pide de fuera
        para que este modulo no tenga que conocer el banco.
        """
        if not ruta.exists():
            msg = f"no hay tabla de ampliacion en {ruta.name}"
            raise FuenteNoDisponibleError(msg)
        crudo = json.loads(ruta.read_text(encoding="utf-8"))["ampliaciones"]
        por_consulta: dict[str, Sequence[str]] = {}
        for identificador, palabras in crudo.items():
            consulta = consultas.get(identificador)
            if consulta is not None:
                por_consulta[consulta] = list(palabras)
        return cls(por_consulta)

    def sinonimos(self, consulta: str) -> tuple[str, ...]:
        return tuple(self._por_consulta.get(normalizar(consulta), ()))


__all__ = [
    "LONGITUD_MINIMA",
    "PALABRAS_MAXIMAS",
    "FuenteDeSinonimos",
    "FuenteNoDisponibleError",
    "SinonimosDeTabla",
    "SinonimosNulos",
    "depurar",
    "normalizar",
]
