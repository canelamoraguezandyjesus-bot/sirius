"""Tarea 1: el modelo lee la pregunta y los candidatos, y dice cuales responden.

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
muchisimo a «¿acepto escalas?». Quien lee si distingue las dos.

CORRECCION MEDIDA: DISTINGUIR NO ES EXCLUIR
===========================================

La primera version de la instruccion decia, literalmente: «una frase que niega o
prohibe algo no responde a una pregunta sobre lo que si se hace o se permite».
**Era falsa, y el banco lo dice a la cara.**

`round/metrics.py` cita el §6.1 al definir la fusion de polaridad: «Fundir ambas
es fallo; recuperarlas **marcadas y distinguidas** es correcto». La polaridad es
un requisito de **marcado**, no de exclusion. Lo que `RF-19` prohibe es entregar
una prohibicion como si fuera un permiso; no prohibe entregarla.

Y sobre el banco, contado: **cinco** casos con contenido esperan al menos un
elemento de polaridad negativa, y dos de ellos son preguntas de permiso cuya
respuesta correcta es una prohibicion —«¿Puedo usar vuelos con escala?» espera
«No uses opciones de vuelo con escala»; «¿Usar PostgreSQL?» espera «No usar
PostgreSQL en este proyecto»—. Los **tres** elementos negativos en juego
—`MEMORIA:2`, `MEMORIA:14`, `DECISION:10`— estan marcados como criticos por el
canon.

De modo que aquella regla mandaba tirar justo lo que hay que entregar, y ademas
lo critico. En la corrida publicada eso se ve: el filtro subio los aciertos
exactos de 24 a 30 y bajo la basura de 29 a 5, pero perdio 13 elementos
correctos y **una omision critica mas que la busqueda sin filtro** (12 contra
11). `B04-RF-24` prohibe exactamente esa perdida.

La regla vigente dice lo contrario y lo dice con ejemplo, y ademas manda
devolver **las dos** cuando hay un par opuesto, que es lo que el §6.1 llama
correcto.

SEGUNDA CORRECCION MEDIDA: EL QUE ELIGE SE QUEDA CON UNO
========================================================

Arreglada la polaridad, la corrida v0.2 salio **peor**: las omisiones criticas
subieron de doce a diecisiete. Con el detalle por caso —que se anadio para esto
justamente— se ve donde, y es un patron limpio:

* `N1-44` «Restricciones esenciales, maximo duro 5»: la busqueda entrego **las
  cinco correctas** y el filtro se quedo con **una**;
* `N1-34`, con diez elementos esperados: tiro **siete**;
* `N1-23` «¿cual es la decision de presupuesto actual y cual reemplazo?»: pedia
  las dos, y devolvio una —ademas la sustituida—;
* `N1-30`, que pide tres cosas en una frase: devolvio parte.

Once de los dieciseis elementos correctos perdidos salen de los dos casos cuya
respuesta correcta es mas larga. **El dano crece con el tamano de la respuesta**:
el modelo trata una peticion de lista como si fuera una pregunta de una sola
cosa, y se queda con el candidato que mas se parece.

Y el beneficio no esta donde parecia. Separando los 47 casos:

===========================  ==================  =================
corrida                      aciertos contenido  aciertos ausencia
===========================  ==================  =================
busqueda sola                16/31               8/16
mas el filtro que elige      17/31               12/16
===========================  ==================  =================

De los cinco aciertos que gana, **cuatro son casos en los que lo correcto era no
devolver nada**. Elegir cuales aporta uno y cuesta dieciseis elementos correctos
y seis criticos.

De ahi la compuerta: se queda con la pregunta que funciona —«¿hay algo aqui?»— y
no puede hacer la que rompe. Sobre las decisiones reales de la v0.2, quedarse
solo con ese veredicto da 27/47 con **once** omisiones criticas, las mismas que
la busqueda sola, contra 29/47 con diecisiete del que elige.

Las dos siguen en el codigo y se miden juntas: quien decida cual entra en Sirius
tiene que ver las dos columnas.

FALLA ABIERTO, Y ESO NO ES UN DESCUIDO
======================================

Si el modelo no responde, tarda de mas o devuelve algo que no encaja, este
filtro **devuelve los candidatos intactos**. No descarta nada.

Es deliberado y va contra el instinto de «fallar cerrado». Aqui lo que se
protege es distinto: `B04-RF-24` prohibe perder un elemento critico en silencio,
y este modulo solo puede quitar. Un fallo que quita de mas produce exactamente
la perdida que la norma prohibe; un fallo que no quita nada deja el sistema como
estaba, ruidoso pero completo.

Y por eso mismo ``actuo`` y ``razon`` **no son decoracion**: una corrida en la
que el servidor va lento produce «el filtro no daña», que a simple vista se lee
igual que «el filtro es prudente». Sin contar cuantas veces actuo de verdad, la
medida no distingue un filtro cuidadoso de un filtro apagado. Quien agregue
estas cifras tiene la obligacion de publicar las dos.

EL MODELO NO PUEDE ANADIR
=========================

Devuelve numeros de una lista que se le da, y el esquema del servidor le obliga
a devolver solo eso. Cualquier numero fuera de rango se descarta al leerlo: la
salida es siempre un subconjunto de la entrada.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from experiments.adr002.modelo_local.puerto import (
    ESPERA_FILTRO,
    ProveedorIA,
    enteros_validos,
)

#: Cuantos candidatos se le dan como mucho. Mas de esto no cabe comodo en la
#: ventana de un modelo pequeno y ademas empeora su atencion al medio de la
#: lista, que es un efecto conocido y medido.
CANDIDATOS_MAXIMOS: Final = 30

#: El esquema que el servidor impone a la respuesta. Con esto, un JSON invalido
#: deja de ser improbable y pasa a ser imposible.
ESQUEMA: Final[Mapping[str, Any]] = {
    "type": "object",
    "properties": {"responden": {"type": "array", "items": {"type": "integer"}}},
    "required": ["responden"],
}

#: La instruccion, entera y literal en el codigo. Quien audite esto tiene que
#: poder leer de una vez todo lo que se le dice al modelo; repartirla entre un
#: fichero de configuracion y el codigo haria que nadie la viera completa.
INSTRUCCION: Final = (
    "Eres el filtro de relevancia de una memoria personal. Recibes una PREGUNTA "
    "y una lista numerada de FRASES guardadas. Dices cuales responden a la "
    "pregunta.\n\n"
    "Reglas:\n"
    "- Devuelve solo los numeros de las frases que responden a la pregunta.\n"
    "- Una prohibicion SI responde a una pregunta sobre si algo se puede hacer: "
    "a «¿puedo usar vuelos con escala?», la frase «no uses vuelos con escala» "
    "es la respuesta, y es que no. Incluyela.\n"
    "- Si hay dos frases opuestas sobre lo mismo, devuelve LAS DOS: quien "
    "pregunta tiene que ver que hay un permiso y una prohibicion.\n"
    "- Respeta el tiempo: si preguntan solo por lo ANTERIOR, lo vigente no "
    "responde; si preguntan solo por lo vigente, lo derogado no responde. Pero "
    "si piden LAS DOS —«cual es la actual y cual reemplazo»—, devuelve las dos.\n"
    "- Si la pregunta pide VARIAS cosas o una lista —«todas las restricciones», "
    "«el presupuesto y la preferencia»—, devuelve TODAS las frases que hagan "
    "falta. No elijas la mejor: la respuesta completa son todas.\n"
    "- Frases parecidas entre si NO son repeticiones. Si cinco frases dicen "
    "«restriccion numero 1», «numero 2»... y la pregunta las pide, son cinco "
    "respuestas distintas y van las cinco.\n"
    "- Una frase que habla del mismo tema pero no responde a la pregunta no "
    "cuenta.\n"
    "- Si ninguna frase responde, devuelve la lista vacia.\n"
    "- Ante duda razonable, incluyela: es peor perder algo importante que "
    "entregar de mas."
)

#: La compuerta pregunta **una sola cosa**: si hay algo aprovechable. No elige.
#:
#: Medido sobre el banco: de los cinco aciertos exactos que el filtro que elige
#: gana sobre la busqueda sola, **cuatro** salen de casos donde lo correcto era
#: no devolver nada. Elegir cuales, en cambio, es donde pierde: se lleva
#: dieciseis elementos correctos y seis criticos. Esta pregunta se queda con lo
#: que funciona y no puede hacer lo que rompe.
INSTRUCCION_COMPUERTA: Final = (
    "Recibes una PREGUNTA y una lista numerada de FRASES guardadas en la "
    "memoria personal de alguien. Dices si ALGUNA aporta algo para responder.\n\n"
    "Reglas:\n"
    "- Responde si o no. **No eliges cuales**: solo dices si hay algo "
    "aprovechable en la lista.\n"
    "- Una prohibicion aporta a una pregunta sobre si algo se puede hacer: la "
    "respuesta es que no, y eso es responder.\n"
    "- Una frase derogada aporta si preguntan por lo anterior.\n"
    "- Si todas hablan de otra cosa, di que no.\n"
    "- Ante duda, di que si: es peor perder algo importante que entregar de mas."
)

ESQUEMA_COMPUERTA: Final[Mapping[str, Any]] = {
    "type": "object",
    "properties": {"hay_respuesta": {"type": "boolean"}},
    "required": ["hay_respuesta"],
}


@dataclass(frozen=True, slots=True)
class Filtrado:
    """Lo que el filtro hizo. Descriptivo: no juzga si estuvo bien.

    ``actuo`` en falso significa que el modelo **no decidio**, por la razon que
    diga ``razon``. Quien agregue muchos filtrados tiene que contar esos casos
    aparte o la cifra resultante no significa nada.
    """

    identidades: tuple[str, ...]
    actuo: bool
    razon: str = ""


def _lista(candidatos: Sequence[tuple[str, str]]) -> str:
    return "\n".join(f"{n}. {texto}" for n, (_ident, texto) in enumerate(candidatos, start=1))


def filtrar(
    consulta: str,
    candidatos: Sequence[tuple[str, str]],
    proveedor: ProveedorIA,
    *,
    tope: int = CANDIDATOS_MAXIMOS,
    espera: float = ESPERA_FILTRO,
) -> Filtrado:
    """Los candidatos que responden, segun el modelo. Siempre un subconjunto.

    ``candidatos`` son pares ``(identidad, texto)`` en el orden en que los
    entrego la busqueda, y ese orden se conserva en la salida: el filtro decide
    **que sale**, no en que orden. Si el modelo pudiera reordenar, una medida de
    orden dejaria de ser atribuible a nadie.
    """
    if not candidatos:
        return Filtrado((), False, "no habia candidatos")
    todas = tuple(ident for ident, _ in candidatos)
    if len(candidatos) > tope:
        # Los primeros se filtran y **la cola pasa intacta**: recortarla aqui
        # seria descartar sin que nadie lo mirase, que es lo que este modulo
        # existe para no hacer.
        cabeza = filtrar(consulta, candidatos[:tope], proveedor, tope=tope, espera=espera)
        return Filtrado(cabeza.identidades + todas[tope:], cabeza.actuo, cabeza.razon)

    entrada = f"Pregunta: {consulta}\n\nFrases guardadas:\n{_lista(candidatos)}"
    try:
        crudo = proveedor.responder_json(INSTRUCCION, entrada, ESQUEMA, espera=espera)
    except Exception as fallo:
        # Se captura **cualquier** fallo, y es deliberado.
        #
        # Con solo los dos errores propios de este paquete, un proveedor que
        # dejara escapar los suyos —sin conexion, cuota agotada, clave
        # invalida, demasiadas peticiones— haria **reventar la busqueda
        # entera**. Y eso es exactamente lo contrario de lo que este modulo
        # promete: un filtro que solo puede quitar tiene que degradar a «no
        # quito nada», nunca a «no hay respuesta».
        #
        # El tipo del fallo va en la razon para que quien lea las cifras
        # distinga un servidor caido de un modelo prudente. `BaseException` no
        # se toca: una interrupcion del usuario debe seguir interrumpiendo.
        return Filtrado(todas, False, f"el modelo no decidio ({type(fallo).__name__}): {fallo}")

    elegidos = enteros_validos(crudo, "responden", tope=len(candidatos))
    if elegidos is None:
        return Filtrado(todas, False, "la respuesta no traia una lista de numeros")
    if not elegidos:
        # El modelo dice que ninguno responde. Es una respuesta legitima y hay
        # que respetarla: es como Sirius llega a decir «no tengo eso».
        return Filtrado((), True)
    return Filtrado(tuple(todas[n - 1] for n in sorted(elegidos)), True)


def compuerta(
    consulta: str,
    candidatos: Sequence[tuple[str, str]],
    proveedor: ProveedorIA,
    *,
    tope: int = CANDIDATOS_MAXIMOS,
    espera: float = ESPERA_FILTRO,
) -> Filtrado:
    """Todo o nada: el modelo dice si hay respuesta, no cual. `RF-25`, `RF-26`.

    **No puede truncar una respuesta.** Esa es toda la idea. El que elige se
    lleva por delante cuatro de cinco restricciones o siete de diez, porque
    decide elemento a elemento y se queda con el que mas se parece; este no
    puede hacerlo, porque no decide elemento a elemento.

    Lo que si puede es equivocarse entero y decir «no hay nada» cuando lo habia.
    Medido sobre las decisiones reales de la corrida v0.2: eso pasa **una vez**
    en 47 casos, y **no cuesta ninguna omision critica** —las once de la
    busqueda sola se quedan en once—, mientras que el que elige las sube a
    diecisiete.

    Falla abierto igual que el otro, y por lo mismo: un modulo que solo puede
    quitar tiene que degradar a «no quito nada».
    """
    if not candidatos:
        return Filtrado((), False, "no habia candidatos")
    todas = tuple(ident for ident, _ in candidatos)
    # La cola no juzgada **nunca** se descarta: un «no» sobre las treinta
    # primeras no dice nada de la treinta y una.
    cola = todas[tope:]

    entrada = f"Pregunta: {consulta}\n\nFrases guardadas:\n{_lista(candidatos[:tope])}"
    try:
        crudo = proveedor.responder_json(
            INSTRUCCION_COMPUERTA, entrada, ESQUEMA_COMPUERTA, espera=espera
        )
    except Exception as fallo:
        return Filtrado(todas, False, f"el modelo no decidio ({type(fallo).__name__}): {fallo}")

    hay = crudo.get("hay_respuesta")
    if not isinstance(hay, bool):
        return Filtrado(todas, False, "la respuesta no traia un si o un no")
    if hay:
        return Filtrado(todas, True)
    return Filtrado(cola, True)


__all__ = [
    "CANDIDATOS_MAXIMOS",
    "ESQUEMA",
    "ESQUEMA_COMPUERTA",
    "INSTRUCCION",
    "INSTRUCCION_COMPUERTA",
    "Filtrado",
    "compuerta",
    "filtrar",
]
