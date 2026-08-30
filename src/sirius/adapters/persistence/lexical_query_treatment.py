"""Tratamiento léxico de consultas para el disparador FTS5 (B6a/B6b).

Portado, sin alterar su algoritmo, desde
``experiments/adr002/candidates/adr002_a/lexical.py`` (rama
``evidence/adr001-spikes``, PR #117): la pieza que la incidencia #455 localiza
como ausente en ``sanitize_fts5_query`` y que el candidato A del laboratorio usaba
para alcanzar el suelo D1 (aciertos exactos >= 29/47) sobre el banco de 47
casos. La incidencia #455/#456 portó lo que ``sanitize_fts5_query`` necesita
para limpiar una consulta de palabras vacías y emparejarla por
raíces/variantes en vez de por ``OR`` de todos sus tokens: ``VACIAS``, el
plegado de diacríticos, la tokenización por corridas alfanuméricas, la raíz
por recorte de sufijos flexivos y las variantes morfológicas.

ADR-109 diagnosticó que ese porte cierra la brecha de cobertura pero no la
de precisión, y que cerrarla exige, como mínimo, ``G11`` del motor por
etapas (``sirius.domain.staged_engine_gates``) — la puerta de integridad
semántica que exige que cada candidata declare sujeto, polaridad y
condición antes de ordenar. La incidencia #457 porta aquí, sin alterarlas,
las funciones de lectura que ``G11`` necesita y que el porte anterior dejó
fuera por no ser necesarias para limpiar la consulta:
``MARCADORES_NEGACION``, ``MARCADORES_CONDICION``, ``polaridad_negativa``
(con sus cuatro reglas), ``condicion_declarada`` y ``sujeto_estructural``.
El resto del laboratorio (solapamiento entre consulta y texto ya
recuperado, familias de sujeto por prefijo) vive en
``sirius.adapters.persistence.staged_engine_candidate``, que sí es parte de
la fuente de candidatas del motor por etapas.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Final

#: Corrida alfanumérica: la misma unidad que tokeniza el laboratorio.
_CORRIDA: Final = re.compile(r"[^\W_]+", re.UNICODE)

#: Palabras funcionales del castellano que no aportan discriminación léxica.
#: Lista cerrada y declarada, idéntica a la del laboratorio: una lista
#: abierta sería un parámetro oculto del tratamiento.
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

#: Sufijos flexivos del castellano, de más largo a más corto. La variante se
#: genera recortando, no consultando ningún recurso externo.
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

#: Longitud mínima de una raíz útil. Por debajo, recortar produce ruido.
RAIZ_MINIMA: Final = 4

#: Marcadores de negación. Detectarla por forma es lo que un tratamiento
#: léxico-estructurado puede hacer, y ``G11`` la exige antes de ordenar.
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


def plegar(palabra: str) -> str:
    """Minúscula sin diacríticos: el mismo pliegue del índice léxico medido."""
    descompuesta = unicodedata.normalize("NFKD", palabra.lower())
    return "".join(c for c in descompuesta if not unicodedata.combining(c))


def tokenizar(texto: str) -> tuple[str, ...]:
    """Corridas alfanuméricas plegadas, en orden de aparición."""
    return tuple(plegar(t) for t in _CORRIDA.findall(texto))


def terminos_significativos(texto: str) -> tuple[str, ...]:
    """Tokens que discriminan: sin vacías y sin duplicados, en orden estable."""
    vistos: list[str] = []
    for token in tokenizar(texto):
        if token in VACIAS or len(token) < 2 or token in vistos:
            continue
        vistos.append(token)
    return tuple(vistos)


def raiz(termino: str) -> str:
    """Raíz por recorte de sufijo flexivo. Determinista y sin diccionario."""
    for sufijo in SUFIJOS:
        if termino.endswith(sufijo) and len(termino) - len(sufijo) >= RAIZ_MINIMA:
            return termino[: -len(sufijo)]
    return termino


def variantes(termino: str) -> tuple[str, ...]:
    """Variantes morfológicas de un término, incluida su raíz.

    Cubre vocabulario sin asumir equivalencia semántica: la variante es la
    misma palabra flexionada, nunca un sinónimo inferido.
    """
    base = raiz(termino)
    generadas = {termino, base}
    if len(base) >= RAIZ_MINIMA:
        generadas.update(f"{base}{sufijo}" for sufijo in ("", "s", "es", "a", "o", "as", "os"))
    return tuple(sorted(t for t in generadas if len(t) >= 2))


#: Preposiciones que introducen un complemento. Un marcador de negación
#: dentro de uno de ellos —«sin adornos»— modifica; no niega la afirmación.
_INTRODUCEN_COMPLEMENTO: Final[frozenset[str]] = frozenset({"sin", "con", "de", "en", "por"})

#: Conjunciones tras las que empieza una subordinada. Un marcador que
#: aparece detrás niega esa cláusula, no la principal.
_ABREN_SUBORDINADA: Final[frozenset[str]] = frozenset(
    {"pero", "aunque", "mientras", "cuando", "si", "salvo", "excepto", "que", "porque"}
)


def polaridad_negativa(texto: str) -> bool:
    """Negación de la afirmación principal.

    Cuatro reglas que un tratamiento léxico-estructurado puede aplicar sin
    diccionario ni modelo:

    1. ``sin`` como preposición introduce un complemento y modifica: «en
       tono directo y sin adornos» sigue siendo una preferencia afirmada;
    2. un marcador detrás de una conjunción subordinante niega la
       subordinada: «se renovó, pero no consta desde cuándo» afirma que se
       renovó;
    3. un marcador en la principal antes de que aparezca subordinada alguna
       sí la niega: «No uses opciones de vuelo con escala.»;
    4. lo que sigue a dos puntos es contenido citado, y la polaridad de la
       afirmación es la de lo que va delante: «Nota marcada por el usuario:
       no uses esto como memoria.» afirma que la nota está marcada; el
       imperativo que reproduce es lo marcado, no lo afirmado.

    La regla 1 se aplica solo a ``sin``, que es la única de la lista que es
    preposición; ``no``, ``ni``, ``nunca``, ``jamás``, ``tampoco`` y las
    formas de ``ninguno`` niegan allá donde están, y por eso solo las libra
    la regla 2.
    """
    principal, _, _citado = texto.partition(":")
    subordinada_abierta = False
    for token in tokenizar(principal):
        if token in _ABREN_SUBORDINADA:
            subordinada_abierta = True
            continue
        if token not in MARCADORES_NEGACION:
            continue
        if token in _INTRODUCEN_COMPLEMENTO:
            continue
        if subordinada_abierta:
            continue
        return True
    return False


def condicion_declarada(texto: str) -> str | None:
    """Devuelve el marcador condicional presente, si lo hay.

    Se devuelve el marcador, no la cláusula: una condición transcrita
    filtraría el texto.
    """
    for token in tokenizar(texto):
        if token in MARCADORES_CONDICION:
            return token
    return None


def sujeto_estructural(subject_key: str | None, texto: str) -> str:
    """Sujeto del item: su clave estructural si existe; si no, su primer
    término significativo."""
    if subject_key and subject_key.strip():
        return subject_key.strip()
    significativos = terminos_significativos(texto)
    return significativos[0] if significativos else ""


def ordenar_estable(terminos: Iterable[str]) -> tuple[str, ...]:
    """Orden determinista: sin él, dos ejecuciones podrían diferir."""
    return tuple(sorted(set(terminos)))


__all__ = [
    "MARCADORES_CONDICION",
    "MARCADORES_NEGACION",
    "RAIZ_MINIMA",
    "SUFIJOS",
    "VACIAS",
    "condicion_declarada",
    "ordenar_estable",
    "plegar",
    "polaridad_negativa",
    "raiz",
    "sujeto_estructural",
    "terminos_significativos",
    "tokenizar",
    "variantes",
]
