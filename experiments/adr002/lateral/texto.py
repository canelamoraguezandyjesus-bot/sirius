"""El texto de cada dato, en un indice aparte que se puede preguntar distinto.

POR QUE HACE FALTA UN SEGUNDO INDICE DEL MISMO TEXTO
====================================================

Porque lo que cambia no es el texto: es **con que palabras se le pregunta**. La
ampliacion de consulta escribe palabras que la persona no dijo —«prefiere»,
«redactes»— y hay que buscarlas contra el texto guardado. Meterlas en el indice
medido cambiaria el candidato que se esta midiendo; preguntarlas contra una
copia lateral no toca nada y se borra entera.

Es un derivado y se comporta como tal: se regenera desde el canon, byte a byte
igual, sin modelo y sin red. `TOL-207` se cumple solo.

QUE ENTRA, Y QUE NO
===================

Entra el campo `text` de cada elemento, que es lo que la persona guardo, y nada
mas. **No entra `criticidad.razon`**, que explica por que un elemento importa y
esta escrito por quien construyo el banco despues de conocer las preguntas: es
informacion equivalente al oraculo y esta prohibida. Hay una prueba que lo
comprueba.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.common.contracts import ContextoDeEtapa
from experiments.adr002.lateral.candidato import Fuente
from experiments.adr002.projection import contracts as pc

TABLA: Final = "texto_fts"

_DDL: Final = f"CREATE VIRTUAL TABLE {TABLA} USING fts5(identidad UNINDEXED, contenido)"


def construir(ruta: Path, items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Escribe el indice de texto y devuelve el registro de lo escrito."""
    filas: list[tuple[str, str]] = []
    for item in items:
        identidad = pc.referencia_canonica(str(item["id"]))
        if identidad is not None:
            filas.append((identidad, str(item["text"])))
    conexion = sqlite3.connect(str(ruta))
    try:
        conexion.execute(_DDL)
        conexion.executemany(f"INSERT INTO {TABLA} (identidad, contenido) VALUES (?, ?)", filas)
        conexion.commit()
    finally:
        conexion.close()
    return {
        "que_es": "copia lateral del texto guardado, para preguntarle con otras palabras",
        "elementos": len(filas),
        "campos_leidos": ["id", "text"],
        "razon_de_criticidad_leida": False,
    }


def fuente(
    ruta: Path, terminos_extra: Callable[[ContextoDeEtapa], Sequence[str]] | None = None
) -> Fuente:
    """La fuente lateral de texto, para pasarsela al candidato."""
    return Fuente(
        ruta=ruta,
        tabla=TABLA,
        razon="coincide con otras palabras de la misma pregunta",
        senal="ampliacion de la consulta",
        terminos_extra=terminos_extra,
    )


__all__ = ["TABLA", "construir", "fuente"]
