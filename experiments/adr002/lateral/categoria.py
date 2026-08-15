"""La categoria de un elemento, hecha buscable. Sin modelo y sin coste.

EL AGUJERO QUE TAPA, CONTADO CASO POR CASO
==========================================

De las once omisiones criticas que quedan tras la corrida v0.4, **seis** son el
mismo agujero, y no es de recuperacion sino de indexacion:

* `N1-31` «Dame todas las restricciones esenciales que debo respetar» devuelve
  **nada**, y espera cinco elementos: «El presupuesto maximo del proyecto es
  1.500 €», «El acceso al almacen requiere autorizacion previa», «Acepta escala
  solo si ahorra mas de 200 €», «No uses opciones de vuelo con escala» y «No
  usar PostgreSQL en este proyecto»;
* `N1-02` «¿Que restricciones de transporte tengo?» devuelve **nada**, y espera
  «En este viaje no se alquila coche».

Ninguno de esos textos contiene la palabra «restriccion». Ni «esencial». La
pregunta nombra **la categoria del dato**, y la categoria no vive en el texto:
vive en la criticidad que el canon ya declara aparte. Un indice construido sobre
el texto no puede encontrarla por mucho que se afine, porque la palabra buscada
no esta escrita en ninguna parte del texto.

Ni un modelo lo arregla: la ampliacion escrita por el modelo se midio dos veces
y no movio estos casos, porque el modelo tampoco puede saber que el canon marca
ese dato como critico si no se lo dicen.

QUE SE INDEXA, Y QUE NO
=======================

Se indexa **el nombre de la categoria**, no su contenido. Para cada elemento con
criticidad distinta de ordinaria se escriben las palabras con las que alguien
pediria esa categoria, y sus variantes morfologicas, porque `FTS5` no lematiza:
sin ellas, «restricciones» en plural no encuentra «restriccion» en singular.

**No se indexa `razon_segura`.** Esta prohibido y ademas seria hacer trampa: esa
razon describe *por que* el elemento importa, y contiene informacion equivalente
al oraculo. Aqui solo entra que el elemento **pertenece** a una categoria, que es
un dato del elemento guardado —como su ambito o su vigencia— y que Sirius conoce
en tiempo de ejecucion.

POR QUE ESTO NO ES UN BARRIDO
=============================

Indexar «restriccion» en los diecinueve criticos del canon podria parecer que
convierte cualquier pregunta con esa palabra en un barrido de los diecinueve.
No lo es, y la razon es el ambito: `G4` filtra por proyecto antes de entregar, de
modo que `N1-31` se queda con los criticos **de su ambito**, que son exactamente
los cinco que espera. Los doce del expediente Gamma son de otro ambito y no
salen. El filtro de ambito ya existia; lo que faltaba era llegar a la puerta.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.lateral.candidato import ConIndiceLateral
from experiments.adr002.projection import contracts as pc

TABLA: Final = "categoria_fts"

_DDL: Final = f"CREATE VIRTUAL TABLE {TABLA} USING fts5(identidad UNINDEXED, contenido)"

#: Las palabras con las que alguien pide esta categoria. Son **las mismas** que
#: se congelaron antes de la primera medicion, en `modelo_local/medir.py`, y se
#: repiten aqui sin tocarlas: elegirlas ahora, sabiendo que casos fallan, seria
#: fijar la medida sobre el resultado, que es lo que el §8.1 prohibe.
VOCABULARIO: Final[tuple[str, ...]] = (
    "esencial",
    "restriccion",
    "critica",
    "obligatoria",
    "imprescindible",
)

#: Que niveles cuentan. El canon declara `CRITICO` e `IMPORTANTE`; lo ordinario
#: no lleva categoria y por eso no se indexa nada para el.
NIVEL_ORDINARIO: Final = "ORDINAR"


def palabras_de_categoria(vocabulario: tuple[str, ...] = VOCABULARIO) -> tuple[str, ...]:
    """El vocabulario con sus variantes, que es lo que se indexa de verdad.

    `FTS5` no lematiza: casa tokens enteros. Sin las variantes, «restricciones»
    —como lo escribe la pregunta del banco— no encontraria «restriccion».
    """
    salida: list[str] = []
    for palabra in vocabulario:
        for variante in lexical.variantes(palabra):
            if variante not in salida:
                salida.append(variante)
    return tuple(salida)


def identidades_con_categoria(criticidad: Mapping[str, Any]) -> tuple[str, ...]:
    """Las identidades cuya criticidad aplicada no es ordinaria.

    Se lee **solo el nivel**. `razon_segura` no se toca ni se devuelve.
    """
    salida: list[str] = []
    for identificador, aplicada in criticidad.items():
        if not isinstance(aplicada, Mapping):
            continue
        if str(aplicada.get("nivel", "")).upper().startswith(NIVEL_ORDINARIO):
            continue
        identidad = pc.referencia_canonica(str(identificador))
        if identidad is not None and identidad not in salida:
            salida.append(identidad)
    return tuple(salida)


def construir(ruta: Path, criticidad: Mapping[str, Any]) -> dict[str, Any]:
    """Escribe el indice de categoria y devuelve el registro de lo escrito.

    Determinista y sin red: dos corridas sobre el mismo canon dan byte a byte lo
    mismo. Es un derivado y `TOL-207` se cumple solo, porque se regenera entero
    desde la criticidad publicada sin depender de ningun modelo ni de ninguna
    huella de pesos.
    """
    palabras = palabras_de_categoria()
    contenido = " ".join(palabras)
    identidades = identidades_con_categoria(criticidad)
    conexion = sqlite3.connect(str(ruta))
    try:
        conexion.execute(_DDL)
        conexion.executemany(
            f"INSERT INTO {TABLA} (identidad, contenido) VALUES (?, ?)",
            [(identidad, contenido) for identidad in identidades],
        )
        conexion.commit()
    finally:
        conexion.close()
    return {
        "que_es": "el nombre de la categoria de cada elemento no ordinario, hecho buscable",
        "vocabulario_congelado": list(VOCABULARIO),
        "palabras_indexadas": list(palabras),
        "identidades": list(identidades),
        "razon_segura_leida": False,
    }


class ConCategoria(ConIndiceLateral):
    """`ADR002-A` mas la categoria buscable."""

    def __init__(self, ruta: Path) -> None:
        super().__init__(
            ruta,
            tabla=TABLA,
            razon="el canon lo declara de esta categoria",
            senal="categoria declarada en el canon",
        )


__all__ = [
    "NIVEL_ORDINARIO",
    "TABLA",
    "VOCABULARIO",
    "ConCategoria",
    "construir",
    "identidades_con_categoria",
    "palabras_de_categoria",
]
