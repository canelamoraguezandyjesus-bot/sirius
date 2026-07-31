"""Inventario, borrado y reconstruccion **completa** del derivado del canon.

El derivado de Sirius 0.1 no son solo dos tablas virtuales: son las tablas
FTS5, sus **tablas sombra** —``_data``, ``_idx``, ``_content``, ``_docsize``,
``_config``— y los **triggers** que las mantienen sincronizadas con el canon.
Reconstruir solo las tablas deja un indice que no se actualiza nunca, y una
prueba que lo compruebe leyendo dos veces el mismo indice ya poblado pasaria
sin detectarlo. Ese fue el defecto 3 del paquete de correccion 01.

El DDL **no se escribe a mano**: se lee de ``sqlite_master``, de modo que la
reconstruccion use exactamente lo que creo la migracion canonica
``61be4bb269bf``. Si esa migracion cambiara, la reconstruccion cambiaria con
ella sin que nadie tenga que acordarse de copiarla aqui.

Este modulo pertenece a la capa comun porque la puerta previa «borrado y
regeneracion desde el canon» vincula a **todos** los candidatos por igual.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

#: Las tablas virtuales del derivado, tal como las nombra la migracion.
TABLAS_FTS: Final[tuple[str, ...]] = ("knowledge_fts", "message_fts")

#: Repoblado **desde el canon**, no desde el propio indice. Un ``rebuild``
#: interno de FTS5 reconstruye desde su tabla de contenido, que es el propio
#: derivado: eso no demuestra que el canon sea la unica autoridad.
BACKFILL_DESDE_EL_CANON: Final[tuple[str, ...]] = (
    "INSERT INTO message_fts(rowid, content) SELECT id, content FROM messages",
    "INSERT INTO knowledge_fts(rowid, kind, item_id, content) "
    "SELECT memory_id * 2, 'memory', memory_id, content FROM memory_revisions "
    "WHERE is_current = 1 AND content IS NOT NULL",
    "INSERT INTO knowledge_fts(rowid, kind, item_id, content) "
    "SELECT decision_id * 2 + 1, 'decision', decision_id, content FROM decision_revisions "
    "WHERE is_current = 1 AND content IS NOT NULL",
)


@dataclass(frozen=True, slots=True)
class Inventario:
    """Objetos derivados presentes en la base, por clase."""

    tablas: tuple[str, ...]
    sombras: tuple[str, ...]
    triggers: tuple[str, ...]

    @property
    def completo(self) -> bool:
        return bool(self.tablas) and bool(self.sombras) and bool(self.triggers)

    @property
    def vacio(self) -> bool:
        return not (self.tablas or self.sombras or self.triggers)


@dataclass(frozen=True, slots=True)
class DdlCanonico:
    """DDL leido del propio esquema: tablas virtuales y triggers."""

    tablas: tuple[str, ...]
    triggers: tuple[str, ...]

    @property
    def completo(self) -> bool:
        """Sin triggers no hay reconstruccion: hay una foto congelada."""
        return bool(self.tablas) and bool(self.triggers)


def inventariar(conexion: sqlite3.Connection) -> Inventario:
    """Todo lo derivado que hay ahora mismo en la base."""
    tablas: list[str] = []
    sombras: list[str] = []
    for (nombre,) in conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall():
        texto = str(nombre)
        if texto in TABLAS_FTS:
            tablas.append(texto)
        elif texto.startswith(TABLAS_FTS):
            sombras.append(texto)
    triggers = [
        str(nombre)
        for (nombre,) in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' AND sql LIKE '%_fts%' "
            "ORDER BY name"
        ).fetchall()
    ]
    return Inventario(tuple(tablas), tuple(sombras), tuple(triggers))


def leer_ddl_canonico(conexion: sqlite3.Connection) -> DdlCanonico:
    """DDL de tablas y triggers, **leido del esquema**, nunca escrito a mano."""
    tablas = tuple(
        str(sql)
        for (sql,) in conexion.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name IN (?, ?) ORDER BY name",
            TABLAS_FTS,
        ).fetchall()
        if sql
    )
    triggers = tuple(
        str(sql)
        for (sql,) in conexion.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND sql LIKE '%_fts%' "
            "ORDER BY name"
        ).fetchall()
        if sql
    )
    return DdlCanonico(tablas, triggers)


def borrar_derivado(conexion: sqlite3.Connection) -> None:
    """Elimina triggers y tablas del derivado. Las sombras caen con su tabla."""
    inventario = inventariar(conexion)
    for trigger in inventario.triggers:
        conexion.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    for tabla in TABLAS_FTS:
        conexion.execute(f"DROP TABLE IF EXISTS {tabla}")
    conexion.commit()


def reconstruir_derivado(conexion: sqlite3.Connection, ddl: DdlCanonico) -> None:
    """Recrea el derivado **entero** y lo repuebla desde el canon.

    Tablas, triggers y contenido, en ese orden. Los triggers se recrean
    **antes** del repoblado para que el estado final sea el mismo que dejo la
    migracion, y no una tabla llena que nadie mantiene.
    """
    if not ddl.completo:
        msg = "el DDL leido no incluye triggers: no habria reconstruccion, solo una foto"
        raise ValueError(msg)
    for sentencia in ddl.tablas:
        conexion.execute(sentencia)
    for sentencia in ddl.triggers:
        conexion.execute(sentencia)
    for sentencia in BACKFILL_DESDE_EL_CANON:
        conexion.execute(sentencia)
    conexion.commit()


def filas_indexadas(conexion: sqlite3.Connection) -> dict[str, int]:
    """Filas por tabla del derivado, para comparar antes y despues."""
    return {
        tabla: int(conexion.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0])
        for tabla in TABLAS_FTS
    }


def fallos_de_reconstruccion(antes: Inventario, despues: Inventario) -> list[str]:
    """La reconstruccion restaura el inventario **completo**, no una parte."""
    fallos: list[str] = []
    for clase, previo, actual in (
        ("tablas", antes.tablas, despues.tablas),
        ("sombras", antes.sombras, despues.sombras),
        ("triggers", antes.triggers, despues.triggers),
    ):
        if sorted(previo) != sorted(actual):
            faltan = sorted(set(previo) - set(actual))
            fallos.append(f"{clase}: la reconstruccion no restauro {faltan or 'el inventario'}")
    return fallos


def objetos_residuales(conexion: sqlite3.Connection, nombres: Sequence[str]) -> tuple[str, ...]:
    """Objetos que deberian haber desaparecido y siguen en el esquema."""
    presentes = {
        str(nombre) for (nombre,) in conexion.execute("SELECT name FROM sqlite_master").fetchall()
    }
    return tuple(sorted(n for n in nombres if n in presentes))


__all__ = [
    "BACKFILL_DESDE_EL_CANON",
    "TABLAS_FTS",
    "DdlCanonico",
    "Inventario",
    "borrar_derivado",
    "fallos_de_reconstruccion",
    "filas_indexadas",
    "inventariar",
    "leer_ddl_canonico",
    "objetos_residuales",
    "reconstruir_derivado",
]
