"""Tarea 3: el modelo escribe con que otras palabras podria estar guardado.

EL UNICO CASO QUE QUEDA, Y POR QUE NO SE CIERRA CON PALABRAS
============================================================

`N1-30` pregunta «Resume mi preferencia de **redaccion**...» y el dato dice «El
usuario prefiere que **redactes** en tono directo». Comprobado, no supuesto:

* el recorte de sufijos da `preferenci` contra `prefier`: no une;
* las variantes morfologicas: no unen;
* los trigramas: no unen;
* **un lematizador tampoco**: «prefiere» lematiza a *preferir*, un verbo, y
  «preferencia» a *preferencia*, un nombre. Son lemas distintos.

Es **derivacion**, no flexion, y con cambio de raiz encima. Ninguna
normalizacion lexica lo cierra, y la via semantica densa esta cerrada por
medicion. Para el modelo, en cambio, no es un problema: relaciona las dos
formas sin esfuerzo.

QUE SE LE PIDE, Y QUE NO PUEDE HACER
====================================

Se le pide **vocabulario**, nunca contenido. Devuelve palabras sueltas que van a
una busqueda contra el texto ya guardado, de modo que el peor efecto posible de
una palabra inventada es que la busqueda traiga algo de mas —y de eso se ocupa
el filtro—. **No puede aparecer un recuerdo que el usuario no dijo.**

Y no puede filtrarse el oraculo: el modelo ve **solo la consulta**. No ve el
corpus, ni la respuesta esperada, ni ninguna anotacion del banco.

LO QUE CUESTA, DICHO ANTES DE MEDIRLO
=====================================

Una llamada al modelo **por cada busqueda**, no por cada dato guardado. La
latencia medida hoy es de 3,1 s de mediana y 3,6 s de p95, y el presupuesto
declarado por el responsable es de 5 s. Esto lo rompe casi seguro, y esa cifra
hay que publicarla junto al acierto y no debajo.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.modelo_local.puerto import ESPERA_FILTRO, ProveedorIA

#: Cuantas palabras se aceptan. Pocas: cada una es una puerta abierta a ruido, y
#: el coste de una de mas lo paga la precision de todas las busquedas.
PALABRAS_MAXIMAS: Final = 8

ESQUEMA: Final[Mapping[str, Any]] = {
    "type": "object",
    "properties": {"palabras": {"type": "array", "items": {"type": "string"}}},
    "required": ["palabras"],
}

INSTRUCCION: Final = (
    "Alguien busca en su memoria personal con la frase que recibes. Escribes con "
    "que OTRAS palabras podria estar escrito el dato que busca.\n\n"
    "Reglas:\n"
    "- Devuelve palabras sueltas, no frases.\n"
    "- Sobre todo, la misma idea en otra forma de la palabra: si la pregunta "
    "dice «redaccion», el dato puede decir «redactes» o «redactar»; si dice "
    "«preferencia», puede decir «prefiere».\n"
    "- Tambien sinonimos naturales: «presupuesto» por «gasto», «limite» por "
    "«maximo».\n"
    "- No inventes datos ni respondas a la pregunta. Solo palabras.\n"
    "- Entre 3 y 8 palabras."
)


@dataclass(frozen=True, slots=True)
class Ampliacion:
    """Las palabras que se anaden a la busqueda, y si el modelo decidio.

    ``actuo`` en falso significa que no hubo ampliacion, por la razon que diga
    ``razon``. Se cuenta aparte porque una corrida con el servidor caido produce
    «no aporta», que a simple vista se lee igual que «no hacia falta».
    """

    palabras: tuple[str, ...]
    actuo: bool
    razon: str = ""


def _utiles(crudo: Mapping[str, Any], consulta: str, tope: int) -> tuple[str, ...]:
    """Palabras limpias, sin las que ya estaban en la consulta.

    Devolver una palabra que la consulta ya trae no amplia nada y solo gasta
    sitio en el limite de terminos.
    """
    palabras = crudo.get("palabras")
    if not isinstance(palabras, list):
        return ()
    ya = set(lexical.terminos_significativos(consulta))
    salida: list[str] = []
    for palabra in palabras:
        if not isinstance(palabra, str):
            continue
        for token in lexical.terminos_significativos(palabra):
            if token not in ya and token not in salida:
                salida.append(token)
    return tuple(salida[:tope])


def ampliar(
    consulta: str,
    proveedor: ProveedorIA,
    *,
    tope: int = PALABRAS_MAXIMAS,
    espera: float = ESPERA_FILTRO,
) -> Ampliacion:
    """Palabras con las que buscar ademas de las de la consulta.

    Falla **abierto**, como el filtro y por lo mismo: si el modelo no responde,
    la busqueda se queda como estaba en vez de romperse. Ampliar es una mejora;
    no ampliar no rompe nada.
    """
    if not consulta.strip():
        return Ampliacion((), False, "consulta vacia")
    try:
        crudo = proveedor.responder_json(INSTRUCCION, consulta, ESQUEMA, espera=espera)
    except Exception as fallo:
        return Ampliacion((), False, f"el modelo no amplio ({type(fallo).__name__}): {fallo}")
    palabras = _utiles(crudo, consulta, tope)
    if not palabras:
        return Ampliacion((), True, "el modelo no anadio ninguna palabra nueva")
    return Ampliacion(palabras, True)


__all__ = ["ESQUEMA", "INSTRUCCION", "PALABRAS_MAXIMAS", "Ampliacion", "ampliar"]
