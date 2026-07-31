"""Puerto de recuperacion sobre el canon de Sirius 0.1 y su FTS5 medido.

Es la unica pieza comun que toca SQLite. El motor no abre conexiones: pide al
puerto. Esa separacion es lo que ``B04-RF-31`` exige —«ninguna obligacion
exige embeddings, RAG, FTS, vectores, grafos o un modelo concreto»—: sustituir
el sustrato no obliga a tocar el motor ni ningun candidato.

**Ningun metodo devuelve el canon entero.** Un barrido completo es justo lo
que ``B04-RF-14`` prohibe, y ofrecerlo aqui invitaria a saltarse las etapas
desde cualquier candidato. Todas las consultas son dirigidas y acotadas.

El puerto **no modifica Sirius 0.1**: lee su esquema canonico tal como lo deja
la cadena de Alembic, sin DDL adicional, sin indices nuevos y sin escrituras.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.common.contracts import (
    Clase,
    ClaseDeEvidencia,
    Criticidad,
    ItemCanonico,
)

#: Vigencia y disponibilidad tal como las representa el esquema de Sirius 0.1.
_ESTADO_VIGENTE: Final = "current"

#: Consulta base: solo revisiones vigentes, con su ambito y su clave de sujeto.
_SQL_MEMORIAS: Final = """
SELECT m.id, m.subject_key, m.status, m.project_id, m.created_at, r.content
FROM memories AS m
JOIN memory_revisions AS r ON r.memory_id = m.id AND r.is_current = 1
WHERE m.id IN ({marcas})
"""

_SQL_DECISIONES: Final = """
SELECT d.id, d.subject, d.status, d.project_id, d.created_at, r.content
FROM decisions AS d
JOIN decision_revisions AS r ON r.decision_id = d.id AND r.is_current = 1
WHERE d.id IN ({marcas})
"""

_SQL_FTS: Final = "SELECT kind, item_id FROM knowledge_fts WHERE knowledge_fts MATCH ? LIMIT ?"

_SQL_SUBJECT_EXACTO: Final = """
SELECT id FROM memories WHERE subject_key = ?
UNION ALL
SELECT id FROM decisions WHERE subject = ?
"""

#: Cota dura de filas por consulta. No es una tolerancia de rendimiento: es la
#: garantia de que ninguna etapa degenera en barrido.
LIMITE_POR_CONSULTA: Final = 512


class PuertoSqlite:
    """Puerto real sobre una base con el esquema canonico de Sirius 0.1.

    Determinista: toda consulta ordena por identidad estable, de modo que dos
    ejecuciones sobre la misma base devuelven el mismo orden.
    """

    def __init__(self, database_path: Path) -> None:
        self._conexion = sqlite3.connect(str(database_path))
        self._conexion.execute("PRAGMA foreign_keys=ON")
        self._conexion.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conexion.close()

    def __enter__(self) -> PuertoSqlite:
        return self

    def __exit__(self, *_excepcion: object) -> None:
        self.close()

    # -- Lectura de items -------------------------------------------------

    def _items(self, clase: Clase, ids: Sequence[int]) -> list[ItemCanonico]:
        if not ids:
            return []
        acotados = sorted(set(ids))[:LIMITE_POR_CONSULTA]
        marcas = ",".join("?" * len(acotados))
        sql = (_SQL_MEMORIAS if clase is Clase.MEMORIA else _SQL_DECISIONES).format(marcas=marcas)
        filas = self._conexion.execute(sql, acotados).fetchall()
        items = [
            ItemCanonico(
                id=f"{clase.value}:{fila[0]}",
                clase=clase,
                project_id=(None if fila["project_id"] is None else str(fila["project_id"])),
                texto=str(fila["content"] or ""),
                subject_key=str(fila[1] or ""),
                vigente=(str(fila["status"]) == _ESTADO_VIGENTE)
                if clase is Clase.MEMORIA
                else (str(fila["status"]) == "approved"),
                disponible=str(fila["status"]) not in ("deleted", "purged"),
                created_at=str(fila["created_at"]),
                clase_de_evidencia=ClaseDeEvidencia.CANONICA,
                criticidad=Criticidad.ORDINARIA,
            )
            for fila in filas
        ]
        return sorted(items, key=lambda i: i.id)

    def _por_ids_mixtos(self, pares: Sequence[tuple[str, int]]) -> tuple[ItemCanonico, ...]:
        memorias = [i for k, i in pares if k == "memory"]
        decisiones = [i for k, i in pares if k == "decision"]
        items = [*self._items(Clase.MEMORIA, memorias), *self._items(Clase.DECISION, decisiones)]
        return tuple(sorted(items, key=lambda i: i.id))

    # -- Metodos del puerto -----------------------------------------------

    def por_clave_exacta(self, claves: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E1``: coincidencia literal sobre claves normalizadas."""
        encontrados: list[tuple[str, int]] = []
        for clave in sorted(set(claves))[:LIMITE_POR_CONSULTA]:
            for fila in self._conexion.execute(
                "SELECT id FROM memories WHERE subject_key = ? ORDER BY id", (clave,)
            ):
                encontrados.append(("memory", int(fila[0])))
            for fila in self._conexion.execute(
                "SELECT id FROM decisions WHERE subject = ? ORDER BY id", (clave,)
            ):
                encontrados.append(("decision", int(fila[0])))
        return self._por_ids_mixtos(encontrados)

    def por_termino_lexico(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E1``/``E2``: el indice lexico medido, con la consulta saneada.

        Cada termino se cita como literal de FTS5 y se combinan con ``OR``:
        ningun texto de consulta puede alcanzar el parser de FTS5 como
        operador, que es la misma garantia que ya ofrece Sirius 0.1.
        """
        limpios = [t for t in (self._sanear(t) for t in terminos) if t]
        if not limpios:
            return ()
        consulta = " OR ".join(f'"{t}"' for t in sorted(set(limpios)))
        pares = [
            (str(fila["kind"]), int(fila["item_id"]))
            for fila in self._conexion.execute(_SQL_FTS, (consulta, LIMITE_POR_CONSULTA))
        ]
        return self._por_ids_mixtos(pares)

    def por_entidad(self, entity_ids: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E3``: relaciones **desde el canon**, sin indice derivado.

        El esquema de Sirius 0.1 materializa la relacion por ``project_id`` y
        por ``subject_key``; no existe tabla de relaciones, y este puerto no
        crea ninguna. Lo que no esta en el canon, no se inventa aqui.
        """
        encontrados: list[tuple[str, int]] = []
        for entidad in sorted(set(entity_ids))[:LIMITE_POR_CONSULTA]:
            for fila in self._conexion.execute(
                "SELECT id FROM memories WHERE project_id = ? ORDER BY id LIMIT ?",
                (entidad, LIMITE_POR_CONSULTA),
            ):
                encontrados.append(("memory", int(fila[0])))
            for fila in self._conexion.execute(
                "SELECT id FROM decisions WHERE project_id = ? ORDER BY id LIMIT ?",
                (entidad, LIMITE_POR_CONSULTA),
            ):
                encontrados.append(("decision", int(fila[0])))
        return self._por_ids_mixtos(encontrados)

    def historial_y_fuentes(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E4``: historial bruto como **evidencia atribuida no canonica**.

        Los mensajes no son conocimiento confirmado: se devuelven marcados
        como ``ATRIBUIDA`` para que ``B04-RF-13`` se cumpla por construccion y
        ningun candidato pueda presentarlos como verdad canonica.
        """
        limpios = [t for t in (self._sanear(t) for t in terminos) if t]
        if not limpios:
            return ()
        consulta = " OR ".join(f'"{t}"' for t in sorted(set(limpios)))
        filas = self._conexion.execute(
            "SELECT m.id, m.content, m.created_at, m.conversation_id "
            "FROM message_fts JOIN messages AS m ON m.id = message_fts.rowid "
            "WHERE message_fts MATCH ? ORDER BY m.id LIMIT ?",
            (consulta, LIMITE_POR_CONSULTA),
        ).fetchall()
        return tuple(
            ItemCanonico(
                id=f"MENSAJE:{fila[0]}",
                clase=Clase.MEMORIA,
                project_id=None,
                texto=str(fila[1] or ""),
                subject_key=f"mensaje-{fila[0]}",
                vigente=False,
                disponible=True,
                created_at=str(fila[2]),
                clase_de_evidencia=ClaseDeEvidencia.ATRIBUIDA,
                criticidad=Criticidad.ORDINARIA,
            )
            for fila in filas
        )

    @staticmethod
    def _sanear(texto: str) -> str:
        """Solo alfanumericos: ningun operador de FTS5 sobrevive."""
        return "".join(c for c in texto.lower() if c.isalnum())


__all__ = ["LIMITE_POR_CONSULTA", "PuertoSqlite"]
