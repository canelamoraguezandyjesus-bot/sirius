"""La ingesta: al guardar un dato, el modelo escribe las preguntas que responde.

POR QUE ESTO Y NO AMPLIAR LA CONSULTA
=====================================

Medido sobre el banco: en los casos que no se resuelven, la pregunta y el dato
guardado **no comparten ni una palabra**. «Dame todas las restricciones
esenciales que debo respetar» contra «No usar PostgreSQL en este proyecto»:
cero. Y no es un caso raro, es el patron de los cinco casos que fallan.

Ampliar la consulta con sinonimos ataca eso desde el lado equivocado: hay que
adivinar, en el momento de buscar, con que palabras se guardo algo. Escribir las
preguntas al **guardar** invierte el problema: el dato pasa a contener, en el
indice, las formas en que alguien lo pediria. Ya no hay que adivinar.

Es la tecnica publicada como expansion de documento, con dos diferencias que
importan aqui: el modelo es **local**, de modo que guardar no cuesta dinero ni
red, y lo generado es **derivado**, de modo que se borra y se regenera entero
desde el canon como exige `TOL-207`.

LO QUE SE GENERA NO ES CONTENIDO
================================

Preguntas y palabras de busqueda. **Nunca hechos.** Lo generado va a un indice
de busqueda, no al canon: si el modelo se inventa una pregunta absurda, el peor
efecto posible es que una busqueda traiga algo de mas, y de eso se ocupa el
filtro. No puede aparecer una memoria que el usuario no dijo.

Esa separacion es la respuesta a lo que `HaluMem` mide: los sistemas del sector
alucinan al **extraer** y al **actualizar** memoria, y el error se propaga hasta
la respuesta. Aqui el modelo no extrae ni actualiza nada; solo escribe indices.

COMO SE TIRA LO ALUCINADO, Y COMO **NO**
========================================

La version publicada documenta que el generador inventa terminos ausentes del
original, y que quitarlos mejora la eficacia y encoge el indice. La tentacion es
filtrar por vocabulario: conservar solo preguntas cuyas palabras aparezcan en el
texto del dato.

**Eso seria destruir exactamente lo valioso.** La pregunta que salva el caso que
lleva bloqueando esto desde el principio es «¿cual es el limite de gasto?» para
el dato «El presupuesto maximo del proyecto es 1.500 €», y no comparte ni una
palabra significativa con el. Un filtro por vocabulario la tiraria, y con ella
el unico motivo para hacer todo esto.

Lo que se hace en su lugar es lo que la tecnica publicada hace de verdad: juzgar
la **pertinencia**. Se le devuelven al modelo sus propias preguntas y se le
pregunta cuales responde el dato realmente. Una pregunta alucinada —«¿cuanto
cuesta el vuelo?» para un dato de presupuesto— no supera su propio examen; una
parafrasis legitima si. Cuesta una segunda llamada local por dato, en la ingesta
y una sola vez.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Final

from experiments.adr002.modelo_local.puerto import (
    ModeloLocal,
    ModeloNoDisponibleError,
    numeros_de,
)

#: Cuantas preguntas se guardan por dato. Pocas y buenas: cada una es
#: vocabulario que puede traer el dato en busquedas que no le tocaban.
PREGUNTAS_MAXIMAS: Final = 4

INSTRUCCION: Final = (
    "Recibes un dato guardado en la memoria personal de alguien. Escribes las "
    "preguntas que ese dato responde, tal como las haria esa persona.\n\n"
    "Reglas:\n"
    "- Entre 2 y 4 preguntas, cortas y naturales.\n"
    "- Usa las palabras con las que una persona pediria esto, no las del dato: "
    "si el dato dice 'presupuesto maximo', una pregunta puede decir 'limite de "
    "gasto'.\n"
    "- Si el dato es una restriccion, una obligacion o un limite, incluye una "
    "pregunta que use esas palabras.\n"
    "- No inventes informacion que no este en el dato.\n"
    "- No expliques nada.\n\n"
    'Responde solo con un objeto JSON: {"preguntas": ["...", "..."]}'
)

#: El examen que cada pregunta generada tiene que pasar. Es el equivalente al
#: filtro de pertinencia de la tecnica publicada, y lo aplica el mismo modelo.
INSTRUCCION_DE_CRIBA: Final = (
    "Recibes un dato guardado y una lista numerada de preguntas. Dices cuales "
    "de esas preguntas responde el dato de verdad.\n\n"
    "Reglas:\n"
    "- Una pregunta sobre el mismo tema que el dato NO responde no cuenta.\n"
    "- Una pregunta que dice lo mismo con otras palabras SI cuenta.\n"
    "- Fijate en la negacion: un dato que prohibe algo no responde a una "
    "pregunta sobre lo que si se permite.\n"
    "- No expliques nada.\n\n"
    'Responde solo con un objeto JSON: {"responden": [1, 3]}'
)


def _generar(texto: str, modelo: ModeloLocal) -> list[str]:
    try:
        respuesta = modelo.preguntar(INSTRUCCION, texto)
    except ModeloNoDisponibleError:
        return []
    try:
        crudo = json.loads(respuesta[respuesta.index("{") : respuesta.rindex("}") + 1])
    except ValueError, json.JSONDecodeError:
        return []
    preguntas = crudo.get("preguntas")
    if not isinstance(preguntas, list):
        return []
    salida: list[str] = []
    for pregunta in preguntas:
        if isinstance(pregunta, str) and pregunta.strip() and pregunta.strip() not in salida:
            salida.append(pregunta.strip())
    return salida[:PREGUNTAS_MAXIMAS]


def _cribar(texto: str, preguntas: Sequence[str], modelo: ModeloLocal) -> tuple[str, ...]:
    """Las preguntas que el dato responde de verdad, segun el propio modelo.

    Si la criba no se puede hacer —modelo caido, respuesta ilegible— se
    devuelven **cero** preguntas, no todas. Aqui fallar cerrado si es lo
    correcto, al reves que en el filtro de busqueda: no ampliar un dato lo deja
    como estaba, mientras que indexar preguntas sin cribar mete vocabulario
    alucinado en el indice y contamina busquedas que no tenian nada que ver.
    """
    if not preguntas:
        return ()
    numeradas = "\n".join(f"{n}. {p}" for n, p in enumerate(preguntas, start=1))
    entrada = f"Dato: {texto}\n\nPreguntas:\n{numeradas}"
    try:
        respuesta = modelo.preguntar(INSTRUCCION_DE_CRIBA, entrada)
    except ModeloNoDisponibleError:
        return ()
    elegidas = numeros_de(respuesta, tope=len(preguntas))
    if elegidas is None:
        return ()
    return tuple(preguntas[n - 1] for n in elegidas)


def preguntas_que_responde(texto: str, modelo: ModeloLocal) -> tuple[str, ...]:
    """Preguntas que este dato responde, ya cribadas, para indexarlas junto a el.

    Devuelve vacio, sin levantar, si el modelo no esta disponible: no poder
    ampliar un dato al guardarlo deja el sistema exactamente como estaba, y la
    construccion del indice puede reintentarlo despues sin que nada se haya
    corrompido. Es un derivado; su ausencia no rompe nada.
    """
    return _cribar(texto, _generar(texto, modelo), modelo)


def terminos_para_indexar(
    texto: str,
    modelo: ModeloLocal,
    *,
    vocabulario_de_categoria: Sequence[str] = (),
) -> str:
    """El texto que se anade al indice de busqueda junto al dato.

    ``vocabulario_de_categoria`` son las palabras que nombran la categoria del
    dato —«esencial», «restriccion»— cuando el canon lo marca como critico. Se
    pasan **de fuera** y no las inventa el modelo: quien sabe si un dato es
    critico es el canon.

    Medido sobre el banco, ese vocabulario solo ya sube de 24 a 26 los casos en
    que lo correcto entra entero, y del 79% al 86% los elementos hallados: hay
    cinco casos que piden literalmente «restricciones esenciales» y esperan
    justo los marcados como criticos de su ambito.
    """
    partes = [*vocabulario_de_categoria, *preguntas_que_responde(texto, modelo)]
    return " ".join(partes)


__all__ = [
    "INSTRUCCION",
    "INSTRUCCION_DE_CRIBA",
    "PREGUNTAS_MAXIMAS",
    "preguntas_que_responde",
    "terminos_para_indexar",
]
