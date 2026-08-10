"""El filtro: el modelo lee la pregunta y los candidatos, y dice cuales responden.

QUE ARREGLA, MEDIDO SOBRE EL BANCO
==================================

En los 8 casos donde ya se recupera **todo** lo correcto y aun asi el conjunto
no es exacto, la basura tiene cinco formas contadas:

1. relleno que casa por una palabra del tema —«Nota ordinaria 13 sobre logistica
   de almacen sin valor critico» respondiendo a «¿que condiciones de acceso al
   almacen hay?»—;
2. expansion demasiado ancha desde lo ya recuperado;
3. una palabra funcional haciendo de puente —«¿puedo **usar** vuelos con
   escala?» trayendo «no **usar** PostgreSQL»—;
4. confusion temporal —se pide la decision **anterior** y sale tambien la
   vigente—;
5. lo relacionado pero no preguntado.

Un medidor de parecido ataca 1, 2, 3 y 5. **No puede con la 4**, porque el texto
vigente se parece mas a la pregunta que el derogado. Y tampoco con la polaridad:
«no uses escalas» y «acepta escala si ahorra 200 €» se parecen los dos
muchisimo a «¿acepto escalas?».

Quien lee si distingue las dos. Por eso el filtro es un modelo.

FALLA ABIERTO, Y ESO NO ES UN DESCUIDO
======================================

Si el modelo no responde, tarda de mas o devuelve algo que no se entiende, este
filtro **devuelve los candidatos intactos**. No descarta nada.

Es deliberado y va contra el instinto de «fallar cerrado». Aqui lo que se
protege es distinto: `B04-RF-24` prohibe perder un elemento critico en silencio,
y este modulo solo puede quitar. Un fallo que quita de mas produce exactamente
la perdida que la norma prohibe; un fallo que no quita nada deja el sistema como
estaba, ruidoso pero completo. Entre entregar de mas y perder algo, se entrega
de mas, y queda anotado que el filtro no actuo.

EL MODELO NO PUEDE ANADIR
=========================

Devuelve numeros de una lista que se le da. Cualquier numero fuera de rango se
descarta al leerlo. No hay forma de que el modelo introduzca una identidad que
no estuviera ya entre los candidatos, ni de que escriba contenido: lo que este
modulo entrega es siempre un subconjunto de lo que recibio.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from experiments.adr002.modelo_local.puerto import (
    ModeloLocal,
    ModeloNoDisponibleError,
    numeros_de,
)

#: Cuantos candidatos se le dan como mucho. Mas de esto no cabe comodo en la
#: ventana de un modelo pequeno y ademas empeora su atencion al medio de la
#: lista, que es un efecto conocido y medido.
CANDIDATOS_MAXIMOS: Final = 30

#: La instruccion, entera y literal en el codigo. Quien audite esto tiene que
#: poder leer de una vez todo lo que se le dice al modelo.
INSTRUCCION: Final = (
    "Eres el filtro de una memoria personal. Recibes una pregunta y una lista "
    "numerada de datos guardados. Dices cuales responden a la pregunta.\n\n"
    "Reglas:\n"
    "- Responde SOLO con los numeros de los datos que responden a la pregunta.\n"
    "- Fijate en la negacion: 'no se alquila coche' NO responde a una pregunta "
    "sobre lo que si se hace, y al reves.\n"
    "- Fijate en el tiempo: si preguntan por lo ANTERIOR o lo DEROGADO, lo "
    "vigente no responde; si preguntan por lo vigente, lo derogado no responde.\n"
    "- Un dato que habla del mismo tema pero no responde a la pregunta NO "
    "cuenta.\n"
    "- Ante la duda, INCLUYELO. Es peor perder algo importante que sobrar.\n"
    "- No expliques nada. No inventes datos. No anadas numeros que no esten en "
    "la lista.\n\n"
    'Responde solo con un objeto JSON: {"responden": [1, 4, 7]}'
)


@dataclass(frozen=True, slots=True)
class Filtrado:
    """Lo que el filtro hizo. Descriptivo, para poder explicarlo despues."""

    identidades: tuple[str, ...]
    #: Si el modelo llego a actuar. Falso cuando fallo o no habia nada que hacer.
    actuo: bool
    #: Por que no actuo, cuando no actuo. Vacio si actuo.
    razon: str = ""

    @property
    def descartadas(self) -> int:
        return 0


def _lista(candidatos: Sequence[tuple[str, str]]) -> str:
    return "\n".join(f"{n}. {texto}" for n, (_ident, texto) in enumerate(candidatos, start=1))


def filtrar(
    consulta: str,
    candidatos: Sequence[tuple[str, str]],
    modelo: ModeloLocal,
    *,
    tope: int = CANDIDATOS_MAXIMOS,
) -> Filtrado:
    """Los candidatos que responden, segun el modelo. Siempre un subconjunto.

    ``candidatos`` son pares ``(identidad, texto)`` en el orden en que los
    entrego la busqueda. Se conserva ese orden en la salida: el filtro decide
    **que sale**, no en que orden, y mezclar las dos cosas haria inatribuible
    cualquier medida.
    """
    if not candidatos:
        return Filtrado((), False, "no habia candidatos")
    if len(candidatos) > tope:
        # Se filtran los primeros y el resto pasa intacto: recortar aqui seria
        # descartar sin que nadie lo mirase, que es lo que este modulo existe
        # para no hacer.
        cabeza = filtrar(consulta, candidatos[:tope], modelo, tope=tope)
        cola = tuple(ident for ident, _ in candidatos[tope:])
        return Filtrado(cabeza.identidades + cola, cabeza.actuo, cabeza.razon)

    entrada = f"Pregunta: {consulta}\n\nDatos guardados:\n{_lista(candidatos)}"
    todas = tuple(ident for ident, _ in candidatos)
    try:
        respuesta = modelo.preguntar(INSTRUCCION, entrada)
    except ModeloNoDisponibleError as fallo:
        return Filtrado(todas, False, f"el modelo no respondio: {fallo}")

    elegidos = numeros_de(respuesta, tope=len(candidatos))
    if elegidos is None:
        return Filtrado(todas, False, "no se entendio la respuesta del modelo")
    if not elegidos:
        # El modelo dice que ninguno responde. Es una respuesta legitima y hay
        # que respetarla: es como Sirius llega a decir «no tengo eso».
        return Filtrado((), True)
    # Se ordena por la posicion que traian de la busqueda, **no** por el orden
    # en que el modelo los nombro. El filtro decide que sale; quien ordena es la
    # busqueda y despues las puertas. Si el modelo pudiera reordenar, una medida
    # de orden dejaria de ser atribuible a nadie.
    return Filtrado(tuple(todas[n - 1] for n in sorted(elegidos)), True)


__all__ = ["CANDIDATOS_MAXIMOS", "INSTRUCCION", "Filtrado", "filtrar"]
