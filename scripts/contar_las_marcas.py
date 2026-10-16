"""Da en este ordenador la cuenta de las marcas de E-R02-02 (ADR-247).

POR QUÉ EXISTE
==============

E-R02-02 pasa si, de las últimas 50 respuestas marcadas, 40 o más son «eso es
Sirius», y la cuenta la da Sirius. La lleva el caso de uso de las marcas
(``MarkReplyUseCase.count``, la que fija PA-R02-06), pero ninguna ventana la
enseña: la da esta orden, con esa misma cuenta, y dice qué modelos dieron las
respuestas que cuenta.

Busca su ``sirius.db`` donde la busca la ventana, también si él eligió otra
carpeta para sus datos, y nunca escribe en ella: la lee con una conexión de solo
lectura y trabaja sobre una copia, en una carpeta temporal que borra al acabar,
después de decir si pasa.

USO
===

    uv run python scripts/contar_las_marcas.py
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from collections import Counter
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_robot_conversation import (
    build_sqlite_robot_conversation_repository,
)
from sirius.application.robot_conversation import MarkReplyUseCase
from sirius.composition_root import DATA_PATHS_UNKNOWN, known_data_paths
from sirius.domain.reply_mark import MarkedReply, ReplyMark
from sirius.infrastructure.temporary_folder import temporary_folder

#: Lo que pide E-R02-02: de las últimas 50 respuestas marcadas, 40 o más «eso es Sirius».
ULTIMAS = 50
HACEN_FALTA = 40

#: Los códigos de salida: pasa, no pasa, todavía no hay 50, y Sirius no sabe dónde están.
PASA, NO_PASA, FALTAN_MARCAS, SIN_DATOS = 0, 1, 2, 3

_SI = f"«{ReplyMark.ES_SIRIUS.value}»"
_NO = f"«{ReplyMark.NO_ES_SIRIUS.value}»"


def copia_su_base(origen: Path, destino: Path) -> None:
    """Copia ``sirius.db`` leyéndola con una conexión de solo lectura, aunque Sirius esté
    abierto, y pone la copia al día por si la suya es de una versión anterior."""
    solo_lectura = f"{origen.resolve().as_uri()}?mode=ro"
    with (
        closing(sqlite3.connect(solo_lectura, uri=True)) as fuente,
        closing(sqlite3.connect(destino)) as copia,
    ):
        fuente.backup(copia)
    upgrade_to_head(destino)


def cuenta(base: Path) -> tuple[int, int, list[MarkedReply]]:
    """La cuenta de PA-R02-06 sobre ``base``, y las respuestas que cuenta."""
    marcas = build_sqlite_robot_conversation_repository(base)
    try:
        caso = MarkReplyUseCase(marcas)
        sirius, marcadas = caso.count(ULTIMAS)
        return sirius, marcadas, caso.recent(ULTIMAS)
    finally:
        marcas.close()


def _modelos(respuestas: list[MarkedReply]) -> str:
    """Qué modelos dieron las respuestas, el que más primero."""
    veces = Counter(respuesta.model or "un modelo sin apuntar" for respuesta in respuestas)
    if len(veces) == 1:
        [modelo] = veces
        return f"{'La dio' if len(respuestas) == 1 else 'Las dio'} {modelo}."
    partes = [f"{modelo} en {n}" for modelo, n in veces.most_common()]
    return f"Las dieron {', '.join(partes[:-1])} y {partes[-1]}."


def main(escribe: Callable[[str], None] = print) -> int:
    rutas = known_data_paths()
    base = rutas.data_dir / "sirius.db" if rutas is not None else None
    if base is None or not base.is_file():
        escribe(DATA_PATHS_UNKNOWN)
        return SIN_DATOS
    # Dice si pasa antes de borrar la carpeta: si no se puede borrar, lo avisa después.
    with temporary_folder("sirius-marcas-", escribe) as carpeta:
        copia = carpeta / "sus-marcas.db"
        copia_su_base(base, copia)
        sirius, marcadas, respuestas = cuenta(copia)
        no = marcadas - sirius
        if marcadas < ULTIMAS:
            escribe(f"Respuestas marcadas hasta ahora: {marcadas}.")
            if respuestas:
                escribe(f"De ellas, {sirius} {_SI} y {no} {_NO}. {_modelos(respuestas)}")
            escribe(
                f"Todavía no hay {ULTIMAS} marcadas: llevas {marcadas} y faltan"
                f" {ULTIMAS - marcadas}."
            )
            return FALTAN_MARCAS
        escribe(f"Las últimas {ULTIMAS} respuestas marcadas: {sirius} {_SI} y {no} {_NO}.")
        escribe(_modelos(respuestas))
        if sirius >= HACEN_FALTA:
            escribe(f"Pasa: {sirius} de {ULTIMAS}, y hacen falta {HACEN_FALTA}.")
            return PASA
        escribe(f"No pasa: {sirius} de {ULTIMAS}, y hacen falta {HACEN_FALTA}.")
        return NO_PASA


if __name__ == "__main__":
    logging.disable(logging.WARNING)
    sys.exit(main())
