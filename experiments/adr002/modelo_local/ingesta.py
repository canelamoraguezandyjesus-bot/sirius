"""Tarea 2: al guardar un dato, el modelo escribe las preguntas que responde.

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

Y VA PRIMERO, NO DESPUES
========================

Medido: la busqueda entrega una mediana de **dos** candidatos por pregunta, y en
12 de 47 casos no entrega ninguno. Un filtro sobre una lista de dos elementos no
tiene margen para mejorar la precision; su unico efecto posible es perder
aciertos. Esta tarea es la que ensancha la lista; la del filtro la estrecha.
Medir el filtro antes de esto seria medir el vacio.

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
parafrasis legitima si. Cuesta una segunda llamada local por dato, al guardar y
una sola vez.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from experiments.adr002.modelo_local.puerto import (
    ESPERA_PREGUNTAS,
    InfoModelo,
    ProveedorIA,
    enteros_validos,
)

#: Cuantas preguntas se guardan por dato. Pocas y buenas: cada una es
#: vocabulario que puede traer el dato en busquedas que no le tocaban.
PREGUNTAS_MAXIMAS: Final = 4

ESQUEMA_GENERAR: Final[Mapping[str, Any]] = {
    "type": "object",
    "properties": {"preguntas": {"type": "array", "items": {"type": "string"}}},
    "required": ["preguntas"],
}

ESQUEMA_CRIBA: Final[Mapping[str, Any]] = {
    "type": "object",
    "properties": {"responden": {"type": "array", "items": {"type": "integer"}}},
    "required": ["responden"],
}

INSTRUCCION: Final = (
    "Recibes un DATO guardado en la memoria personal de alguien. Escribes las "
    "preguntas que ese dato responde, tal como las haria esa persona.\n\n"
    "Reglas:\n"
    "- Entre 2 y 4 preguntas, cortas y naturales, en espanol.\n"
    "- Usa las palabras con las que una persona pediria esto, no las del dato: "
    "si el dato dice «presupuesto maximo», una pregunta puede decir «limite de "
    "gasto».\n"
    "- Al menos dos preguntas deben usar palabras que NO aparecen en el dato.\n"
    "- Si el dato es una restriccion, una obligacion o un limite, incluye una "
    "pregunta que use esas palabras.\n"
    "- No inventes informacion que no este en el dato."
)

#: El examen que cada pregunta generada tiene que pasar, aplicado por el mismo
#: modelo. Es el filtro de pertinencia de la tecnica publicada.
INSTRUCCION_DE_CRIBA: Final = (
    "Recibes un DATO guardado y una lista numerada de PREGUNTAS. Dices cuales "
    "de esas preguntas responde el dato de verdad.\n\n"
    "Reglas:\n"
    "- Una pregunta sobre el mismo tema que el dato no responde no cuenta.\n"
    "- Una pregunta que dice lo mismo con otras palabras si cuenta.\n"
    "- Respeta la negacion: un dato que prohibe algo no responde a una pregunta "
    "sobre lo que si se permite."
)


@dataclass(frozen=True, slots=True)
class PreguntasGeneradas:
    """Lo generado para un dato, **con de donde salio**.

    La procedencia no es burocracia: `TOL-207` exige que todo derivado se pueda
    borrar y regenerar desde la fuente. Sin saber que modelo y que pesos lo
    escribieron, al cambiar de modelo no se sabe que hay que regenerar, y se
    acaba con un indice mezclando derivados de dos cerebros distintos.
    """

    preguntas: tuple[str, ...]
    vocabulario_de_categoria: tuple[str, ...] = ()
    info_modelo: InfoModelo | None = None
    #: Vacio si todo fue bien. Con texto, dice por que no se genero nada.
    razon: str = ""
    aportes_descartados: tuple[str, ...] = field(default_factory=tuple)

    @property
    def texto_para_indexar(self) -> str:
        """Lo que se anade al indice de busqueda junto al dato."""
        return " ".join([*self.vocabulario_de_categoria, *self.preguntas])

    @property
    def procedencia(self) -> dict[str, str]:
        """Con que se genero esto. Va al artefacto de resultados tal cual."""
        if self.info_modelo is None:
            return {"proveedor": "", "modelo": "", "huella": ""}
        return {
            "proveedor": self.info_modelo.proveedor,
            "modelo": self.info_modelo.modelo,
            "huella": self.info_modelo.huella,
        }


def _generar(texto: str, proveedor: ProveedorIA, espera: float) -> list[str]:
    crudo = proveedor.responder_json(INSTRUCCION, texto, ESQUEMA_GENERAR, espera=espera)
    preguntas = crudo.get("preguntas")
    if not isinstance(preguntas, list):
        return []
    salida: list[str] = []
    for pregunta in preguntas:
        limpia = pregunta.strip() if isinstance(pregunta, str) else ""
        if limpia and limpia not in salida:
            salida.append(limpia)
    return salida[:PREGUNTAS_MAXIMAS]


def _cribar(
    texto: str, preguntas: Sequence[str], proveedor: ProveedorIA, espera: float
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Las que el dato responde de verdad, y las que se descartan.

    Devolver tambien las descartadas permite auditar el examen: sin ellas, un
    modelo que tirase todo y un modelo que no generase nada se verian iguales.
    """
    if not preguntas:
        return (), ()
    numeradas = "\n".join(f"{n}. {p}" for n, p in enumerate(preguntas, start=1))
    entrada = f"Dato: {texto}\n\nPreguntas:\n{numeradas}"
    crudo = proveedor.responder_json(INSTRUCCION_DE_CRIBA, entrada, ESQUEMA_CRIBA, espera=espera)
    elegidas = enteros_validos(crudo, "responden", tope=len(preguntas))
    if elegidas is None:
        return (), tuple(preguntas)
    aprobadas = tuple(preguntas[n - 1] for n in sorted(elegidas))
    return aprobadas, tuple(p for p in preguntas if p not in aprobadas)


def preguntas_que_responde(
    texto: str,
    proveedor: ProveedorIA,
    *,
    vocabulario_de_categoria: Sequence[str] = (),
    espera: float = ESPERA_PREGUNTAS,
) -> PreguntasGeneradas:
    """Preguntas cribadas para indexar junto al dato, con su procedencia.

    Falla **cerrado**, al reves que el filtro de busqueda, y a proposito: no
    ampliar un dato lo deja exactamente como estaba y se puede reintentar
    despues sin que nada se haya corrompido, mientras que indexar preguntas sin
    cribar mete vocabulario alucinado en el indice y contamina busquedas que no
    tenian nada que ver.

    ``vocabulario_de_categoria`` son las palabras que nombran la categoria del
    dato —«esencial», «restriccion»— cuando el canon lo marca como critico. Se
    pasan **de fuera** y no las inventa el modelo: quien sabe si un dato es
    critico es el canon. Por eso sobreviven aunque el modelo no responda: medido
    sobre el banco, ese vocabulario solo ya sube de 24 a 26 los casos en que lo
    correcto entra entero, y del 79% al 86% los elementos hallados.
    """
    categoria = tuple(vocabulario_de_categoria)
    try:
        generadas = _generar(texto, proveedor, espera)
        aprobadas, descartadas = _cribar(texto, generadas, proveedor, espera)
        info = proveedor.info_modelo()
    except Exception as fallo:
        # Cualquier fallo, no solo los dos de este paquete. Guardar un dato no
        # puede romperse porque un proveedor de otra familia levante un error
        # suyo —sin conexion, cuota agotada, clave invalida—: la ampliacion es
        # un derivado, y quedarse sin ella deja el sistema exactamente como
        # estaba. Que reventara el guardado seria perder el dato por no poder
        # adornarlo. `BaseException` no se toca: una interrupcion interrumpe.
        return PreguntasGeneradas(
            (), categoria, None, f"no se genero nada ({type(fallo).__name__}): {fallo}"
        )
    return PreguntasGeneradas(aprobadas, categoria, info, "", descartadas)


__all__ = [
    "ESQUEMA_CRIBA",
    "ESQUEMA_GENERAR",
    "INSTRUCCION",
    "INSTRUCCION_DE_CRIBA",
    "PREGUNTAS_MAXIMAS",
    "PreguntasGeneradas",
    "preguntas_que_responde",
]
