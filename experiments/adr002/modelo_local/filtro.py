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
    "- Respeta el tiempo: si preguntan por lo ANTERIOR o lo derogado, lo "
    "vigente no responde; si preguntan por lo vigente, lo derogado no responde.\n"
    "- Una frase que habla del mismo tema pero no responde a la pregunta no "
    "cuenta.\n"
    "- Si ninguna frase responde, devuelve la lista vacia.\n"
    "- Ante duda razonable, incluyela: es peor perder algo importante que "
    "entregar de mas."
)


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


__all__ = ["CANDIDATOS_MAXIMOS", "ESQUEMA", "INSTRUCCION", "Filtrado", "filtrar"]
