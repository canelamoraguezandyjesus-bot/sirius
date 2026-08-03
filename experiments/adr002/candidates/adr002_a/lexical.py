"""Recursos lexico-estructurados de ``ADR002-A``. Deterministas y sin red.

Aqui vive lo que distingue a ``ADR002-A``: **como** satisface las etapas de
expansion sin ninguna senal semantica vectorial ni indice relacional derivado.
Todo lo que sigue opera sobre la forma de las palabras y sobre la estructura
que el canon ya tiene —claves de sujeto, ambito, vigencia—, nunca sobre
representaciones densas del significado.

Que ``ADR002-A`` no use vectores **no es un deficit**: ``B04-RF-31`` prohibe
convertir ``RF-17`` en una obligacion de realizacion, y si esta via basta o no
es exactamente la hipotesis que el benchmark pone a prueba.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from typing import Final

#: Corrida alfanumerica: la misma unidad que tokeniza el indice lexico medido.
_CORRIDA: Final = re.compile(r"[^\W_]+", re.UNICODE)

#: Palabras funcionales que no aportan discriminacion lexica. Lista cerrada y
#: declarada: una lista abierta seria un parametro oculto del candidato.
VACIAS: Final[frozenset[str]] = frozenset(
    [
        "a",
        "al",
        "algo",
        "ante",
        "antes",
        "aqui",
        "asi",
        "aun",
        "aunque",
        "cada",
        "como",
        "con",
        "contra",
        "cual",
        "cuando",
        "de",
        "del",
        "desde",
        "donde",
        "dos",
        "el",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "era",
        "eres",
        "es",
        "esa",
        "ese",
        "eso",
        "esta",
        "este",
        "esto",
        "hasta",
        "hay",
        "junto",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "mas",
        "me",
        "mi",
        "mientras",
        "muy",
        "nos",
        "o",
        "otra",
        "otro",
        "para",
        "pero",
        "poco",
        "por",
        "porque",
        "que",
        "quien",
        "se",
        "sea",
        "segun",
        "si",
        "sin",
        "sobre",
        "son",
        "su",
        "sus",
        "tal",
        "tan",
        "te",
        "ti",
        "todo",
        "tras",
        "tu",
        "un",
        "una",
        "uno",
        "unos",
        "y",
        "ya",
    ]
)

#: Marcadores de negacion. ``B04-RF-19`` exige preservarla; detectarla por
#: forma es exactamente lo que un candidato lexico-estructurado puede hacer.
MARCADORES_NEGACION: Final[tuple[str, ...]] = (
    "no",
    "ni",
    "nunca",
    "jamas",
    "sin",
    "tampoco",
    "ningun",
    "ninguna",
    "ninguno",
)

#: Marcadores condicionales y temporales subordinantes.
MARCADORES_CONDICION: Final[tuple[str, ...]] = (
    "si",
    "cuando",
    "mientras",
    "aunque",
    "salvo",
    "excepto",
    "siempre",
    "hasta",
)

#: Sufijos flexivos del castellano, ordenados de mas largo a mas corto. La
#: variante se genera recortando, no consultando ningun recurso externo.
SUFIJOS: Final[tuple[str, ...]] = (
    "aciones",
    "acion",
    "amiento",
    "imiento",
    "adores",
    "ador",
    "antes",
    "ante",
    "ivas",
    "ivo",
    "iva",
    "ales",
    "al",
    "es",
    "as",
    "os",
    "a",
    "e",
    "o",
    "s",
)

#: Longitud minima de una raiz util. Por debajo, recortar produce ruido.
RAIZ_MINIMA: Final = 4


def plegar(palabra: str) -> str:
    """Minuscula sin diacriticos: el mismo pliegue del indice medido."""
    descompuesta = unicodedata.normalize("NFKD", palabra.lower())
    return "".join(c for c in descompuesta if not unicodedata.combining(c))


def tokenizar(texto: str) -> tuple[str, ...]:
    """Corridas alfanumericas plegadas, en orden de aparicion."""
    return tuple(plegar(t) for t in _CORRIDA.findall(texto))


def terminos_significativos(texto: str) -> tuple[str, ...]:
    """Tokens que discriminan: sin vacias y sin duplicados, en orden estable."""
    vistos: list[str] = []
    for token in tokenizar(texto):
        if token in VACIAS or len(token) < 2 or token in vistos:
            continue
        vistos.append(token)
    return tuple(vistos)


def raiz(termino: str) -> str:
    """Raiz por recorte de sufijo flexivo. Determinista y sin diccionario."""
    for sufijo in SUFIJOS:
        if termino.endswith(sufijo) and len(termino) - len(sufijo) >= RAIZ_MINIMA:
            return termino[: -len(sufijo)]
    return termino


def variantes(termino: str) -> tuple[str, ...]:
    """Variantes morfologicas de un termino, incluida su raiz.

    Es la senal de ``E2``: cubre vocabulario **sin asumir equivalencia
    semantica**, que es justo el limite que ``B04 §15.1`` pone a esa etapa.
    """
    base = raiz(termino)
    generadas = {termino, base}
    if len(base) >= RAIZ_MINIMA:
        generadas.update(f"{base}{sufijo}" for sufijo in ("", "s", "es", "a", "o", "as", "os"))
    return tuple(sorted(t for t in generadas if len(t) >= 2))


def polaridad_negativa(texto: str) -> bool:
    """Detecta negacion por marcador lexico (``B04-RF-19``)."""
    return any(token in MARCADORES_NEGACION for token in tokenizar(texto))


def condicion_declarada(texto: str) -> str | None:
    """Devuelve el marcador condicional presente, si lo hay.

    Se devuelve **el marcador**, no la clausula: la traza registra clases y
    decisiones, no contenido, y una condicion transcrita filtraria el texto.
    """
    for token in tokenizar(texto):
        if token in MARCADORES_CONDICION:
            return token
    return None


def sujeto_estructural(subject_key: str | None, texto: str) -> str:
    """Sujeto del item: su clave estructural si existe; si no, su primer termino.

    El canon ya materializa el sujeto en ``subject_key``; usarlo es preferible
    a inferirlo, y recurrir al texto solo cuando falta evita inventar sujetos.
    """
    if subject_key and subject_key.strip():
        return subject_key.strip()
    significativos = terminos_significativos(texto)
    return significativos[0] if significativos else ""


def solapamiento(consulta: Sequence[str], texto: str) -> tuple[str, ...]:
    """Terminos de la consulta presentes en el texto, por raiz compartida.

    Es la senal de ``E3`` para parafrasis y dependencias: dos formas distintas
    de la misma raiz se reconocen sin recurrir a similitud vectorial.
    """
    raices_texto = {raiz(t) for t in terminos_significativos(texto)}
    return tuple(sorted({t for t in consulta if raiz(t) in raices_texto}))


def comparten_estructura(a: str, b: str) -> bool:
    """Dos claves de sujeto emparentadas por prefijo estructural comun."""
    izquierda, derecha = plegar(a), plegar(b)
    if not izquierda or not derecha:
        return False
    return izquierda.split("-")[0] == derecha.split("-")[0]


def ordenar_estable(terminos: Iterable[str]) -> tuple[str, ...]:
    """Orden determinista: sin el, dos ejecuciones podrian diferir."""
    return tuple(sorted(set(terminos)))


__all__ = [
    "MARCADORES_CONDICION",
    "MARCADORES_NEGACION",
    "RAIZ_MINIMA",
    "SUFIJOS",
    "VACIAS",
    "comparten_estructura",
    "condicion_declarada",
    "ordenar_estable",
    "plegar",
    "polaridad_negativa",
    "raiz",
    "solapamiento",
    "sujeto_estructural",
    "terminos_significativos",
    "tokenizar",
    "variantes",
]
