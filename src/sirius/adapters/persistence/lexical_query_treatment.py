"""Tratamiento léxico de consultas para el disparador FTS5 (B6a/B6b).

Portado, sin alterar su algoritmo, desde
``experiments/adr002/candidates/adr002_a/lexical.py`` (rama
``evidence/adr001-spikes``, PR #117): la pieza que la incidencia #455 localiza
como ausente en ``sanitize_fts5_query`` y que el candidato A del laboratorio usaba
para alcanzar el suelo D1 (aciertos exactos >= 29/47) sobre el banco de 47
casos. Solo se porta lo que ``sanitize_fts5_query`` necesita para limpiar una
consulta de palabras vacías y emparejarla por raíces/variantes en vez de por
``OR`` de todos sus tokens: ``VACIAS``, el plegado de diacríticos, la
tokenización por corridas alfanuméricas, la raíz por recorte de sufijos
flexivos y las variantes morfológicas. El resto del laboratorio (lectura de
polaridad/condición, solapamiento entre consulta y texto ya recuperado,
familias de sujeto) pertenece a las etapas E3/E4 de un motor por etapas que
Sirius 0.1 no tiene, y no se porta aquí (fuera del alcance de la incidencia
#455 que cierra ese hallazgo).
"""

from __future__ import annotations

import re
import unicodedata
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


__all__ = [
    "RAIZ_MINIMA",
    "SUFIJOS",
    "VACIAS",
    "plegar",
    "raiz",
    "terminos_significativos",
    "tokenizar",
    "variantes",
]
