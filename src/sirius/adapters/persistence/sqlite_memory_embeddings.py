"""Las huellas de los recuerdos en sirius.db, buscadas con sqlite-vec (pieza F, ADR-238).

Una tabla normal, ``memory_embeddings``, con la huella en un BLOB de float32 y sus
bits, uno por número. Con pocas huellas, la búsqueda las recorre todas con
``vec_distance_cosine`` de sqlite-vec. Con muchas, casi todo el tiempo se va en esos
cosenos (35 de 40 ms con 10.000 huellas de 1.024 números, medido el 16-10-2026): la
búsqueda mira primero los bits de todas y calcula el coseno exacto solo de las más
cercanas (ADR-251).

sqlite-vec se carga solo en las conexiones de este almacén. Si no carga, guardar
sigue funcionando, ``available`` es falso y la búsqueda por significado no
devuelve nada: Sirius sigue buscando por palabras, como hasta ahora.
"""

from __future__ import annotations

import sqlite3
import struct
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sqlite_vec
from sqlalchemy import Engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.domain.memory import MemoryStatus
from sirius.infrastructure.logging import get_logger
from sirius.ports.embeddings import PendingMemory

__all__ = [
    "ONE_STEP_UP_TO",
    "TWO_STEP_CANDIDATES",
    "SqliteMemoryEmbeddingStore",
    "build_sqlite_memory_embedding_store",
    "to_bits",
    "to_blob",
]

_logger = get_logger(__name__)


#: Hasta cuántas huellas la búsqueda va en un solo paso, exacto, como antes de ADR-251.
ONE_STEP_UP_TO = 1_000

#: Cuántas huellas, las más cercanas por bits, pasan al coseno exacto (ADR-251).
TWO_STEP_CANDIDATES = 200


def to_blob(embedding: Sequence[float]) -> bytes:
    """La huella como la guarda y la lee sqlite-vec: float32 seguidos."""
    return struct.pack(f"<{len(embedding)}f", *embedding)


def to_bits(embedding: Sequence[float]) -> bytes:
    """Un bit por número de la huella, 1 si es positivo, de ocho en ocho por byte.

    Los de las huellas y los de la pregunta salen de aquí, así que siempre se comparan
    con el mismo orden de bits.
    """
    packed = bytearray((len(embedding) + 7) // 8)
    for index, value in enumerate(embedding):
        if value > 0:
            packed[index // 8] |= 1 << (index % 8)
    return bytes(packed)


def _load_sqlite_vec(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
    dbapi_connection.enable_load_extension(True)
    try:
        sqlite_vec.load(dbapi_connection)
    finally:
        dbapi_connection.enable_load_extension(False)


_PENDING = text(
    """
    SELECT m.id AS memory_id, r.id AS revision_id, r.content AS content
    FROM memories AS m
    JOIN memory_revisions AS r ON r.memory_id = m.id AND r.is_current = 1
    LEFT JOIN memory_embeddings AS e
        ON e.memory_id = m.id AND e.revision_id = r.id AND e.model = :model
    WHERE m.status = :current AND r.content IS NOT NULL AND e.memory_id IS NULL
    ORDER BY m.updated_at DESC, m.id DESC
    LIMIT :limit
    """
)

# El CASE, y no un filtro en el WHERE, es lo que asegura que sqlite-vec solo
# compara huellas del mismo tamaño: con otro tamaño da error, y SQLite no promete
# en qué orden mira las condiciones del WHERE. Una huella de ceros da NULL y no
# pasa el umbral. MATERIALIZED hace que el parecido se calcule una vez por
# huella: sin él, SQLite lo calcula para el umbral y otra vez para ordenar, y con
# 10.000 huellas tarda el doble (42 ms frente a 23, medido el 07-10-2026).
_NEAREST = text(
    """
    WITH parecidos AS MATERIALIZED (
        SELECT e.memory_id AS memory_id,
               CASE WHEN length(e.embedding) = :size
                    THEN 1.0 - vec_distance_cosine(e.embedding, :query)
               END AS similarity
        FROM memory_embeddings AS e
        JOIN memories AS m ON m.id = e.memory_id
        JOIN memory_revisions AS r ON r.id = e.revision_id AND r.is_current = 1
        WHERE e.model = :model
          AND m.status = :current
          AND r.content IS NOT NULL
    )
    SELECT memory_id, similarity FROM parecidos
    WHERE similarity >= :min_similarity
    ORDER BY similarity DESC, memory_id DESC
    LIMIT :limit
    """
)

# ADR-251: el primer paso lee del índice (model, bits) los bits de todas las huellas del
# modelo, sin abrir ninguna, y se queda con las más cercanas por bits; el segundo es
# _NEAREST sobre esas. El CASE hace con los bits lo mismo que con las huellas: con otro
# tamaño, NULL, que no pasa.
_NEAREST_IN_TWO_STEPS = text(
    """
    WITH cercanas AS MATERIALIZED (
        SELECT memory_id FROM (
            SELECT memory_id,
                   CASE WHEN length(bits) = :bits_size
                        THEN vec_distance_hamming(vec_bit(bits), vec_bit(:bits))
                   END AS distancia
            FROM memory_embeddings
            WHERE model = :model AND bits IS NOT NULL
        )
        WHERE distancia IS NOT NULL
        ORDER BY distancia, memory_id DESC
        LIMIT :candidates
    ),
    parecidos AS MATERIALIZED (
        SELECT e.memory_id AS memory_id,
               CASE WHEN length(e.embedding) = :size
                    THEN 1.0 - vec_distance_cosine(e.embedding, :query)
               END AS similarity
        FROM cercanas
        JOIN memory_embeddings AS e ON e.memory_id = cercanas.memory_id
        JOIN memories AS m ON m.id = e.memory_id
        JOIN memory_revisions AS r ON r.id = e.revision_id AND r.is_current = 1
        WHERE e.model = :model
          AND m.status = :current
          AND r.content IS NOT NULL
    )
    SELECT memory_id, similarity FROM parecidos
    WHERE similarity >= :min_similarity
    ORDER BY similarity DESC, memory_id DESC
    LIMIT :limit
    """
)

# Cuántas huellas hay del modelo y cuántas tienen bits, del mismo índice.
_COUNT_BITS = text(
    "SELECT COUNT(*) AS total, COUNT(bits) AS with_bits FROM memory_embeddings WHERE model = :model"
)

# El parecido entre dos recuerdos, por sus huellas del mismo modelo (ADR-251).
_BETWEEN = text(
    """
    SELECT CASE WHEN length(a.embedding) = length(b.embedding)
                THEN 1.0 - vec_distance_cosine(a.embedding, b.embedding)
           END AS similarity
    FROM memory_embeddings AS a JOIN memory_embeddings AS b
    WHERE a.memory_id = :first AND b.memory_id = :second
      AND a.model = :model AND b.model = :model
    """
)


_SAVE = text(
    """
    INSERT INTO memory_embeddings (memory_id, revision_id, model, embedding, created_at, bits)
    SELECT :memory_id, :revision_id, :model, :embedding, :created_at, :bits
    WHERE EXISTS (
        SELECT 1 FROM memories AS m
        JOIN memory_revisions AS r ON r.memory_id = m.id
        WHERE m.id = :memory_id AND m.status = :current
          AND r.id = :revision_id AND r.is_current = 1 AND r.content IS NOT NULL
    )
    ON CONFLICT (memory_id) DO UPDATE SET
        revision_id = excluded.revision_id,
        model = excluded.model,
        embedding = excluded.embedding,
        created_at = excluded.created_at,
        bits = excluded.bits
    """
)


class SqliteMemoryEmbeddingStore:
    """``MemoryEmbeddingStore`` sobre la misma base que los recuerdos."""

    def __init__(
        self, session_factory: sessionmaker[Session], engine: Engine, *, available: bool
    ) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._available = available

    @property
    def available(self) -> bool:
        return self._available

    def close(self) -> None:
        self._engine.dispose()

    def pending(self, model: str, limit: int) -> list[PendingMemory]:
        with session_scope(self._session_factory) as session:
            rows = session.execute(
                _PENDING,
                {"model": model, "current": MemoryStatus.CURRENT.value, "limit": limit},
            ).all()
            return [PendingMemory(row.memory_id, row.revision_id, row.content) for row in rows]

    def save(
        self, memory_id: int, revision_id: int, model: str, embedding: Sequence[float]
    ) -> bool:
        """Guarda la huella solo si el recuerdo sigue vigente y esa es su revisión actual.

        En una sola sentencia: si se archiva, se borra o se corrige mientras se
        calculaba, no se guarda (ronda 1 de Codex). Si no, un recuerdo borrado
        recuperaría una huella que los disparadores ya habían quitado, y nadie la
        volvería a quitar.
        """
        with session_scope(self._session_factory) as session:
            result = session.execute(
                _SAVE,
                {
                    "memory_id": memory_id,
                    "revision_id": revision_id,
                    "model": model,
                    "embedding": to_blob(embedding),
                    "bits": to_bits(embedding),
                    # Como guarda SQLAlchemy las fechas en SQLite, y sin el adaptador
                    # de fechas de sqlite3, que está en desuso.
                    "created_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "current": MemoryStatus.CURRENT.value,
                },
            )
            return bool(getattr(result, "rowcount", 0))

    def nearest(
        self, embedding: Sequence[float], model: str, *, min_similarity: float, limit: int
    ) -> list[tuple[int, float]]:
        """Con ``ONE_STEP_UP_TO`` huellas o menos, o si a alguna le faltan los bits, en un
        solo paso exacto; si no, en dos: las ``TWO_STEP_CANDIDATES`` más cercanas por bits
        y, de esas, el coseno exacto (ADR-251)."""
        if not self._available or not embedding:
            return []
        query = to_blob(embedding)
        bits = to_bits(embedding)
        with session_scope(self._session_factory) as session:
            counted = session.execute(_COUNT_BITS, {"model": model}).one()
            two_steps = counted.total > ONE_STEP_UP_TO and counted.with_bits == counted.total
            rows = session.execute(
                _NEAREST_IN_TWO_STEPS if two_steps else _NEAREST,
                {
                    "query": query,
                    "bits": bits,
                    "bits_size": len(bits),
                    "candidates": TWO_STEP_CANDIDATES,
                    "model": model,
                    "current": MemoryStatus.CURRENT.value,
                    "size": len(query),
                    "min_similarity": min_similarity,
                    "limit": limit,
                },
            ).all()
            return [(int(row.memory_id), float(row.similarity)) for row in rows]

    def similarity(self, first: int, second: int, model: str) -> float | None:
        """El parecido entre dos recuerdos por sus huellas de ``model``; ``None`` si a
        alguno le falta, si son de distinto tamaño o si sqlite-vec no cargó."""
        if not self._available:
            return None
        with session_scope(self._session_factory) as session:
            value = session.execute(
                _BETWEEN, {"first": first, "second": second, "model": model}
            ).scalar()
            return None if value is None else float(value)

    def count(self, model: str | None = None) -> int:
        with session_scope(self._session_factory) as session:
            if model is None:
                value = session.execute(text("SELECT COUNT(*) FROM memory_embeddings")).scalar()
            else:
                value = session.execute(
                    text("SELECT COUNT(*) FROM memory_embeddings WHERE model = :model"),
                    {"model": model},
                ).scalar()
            return int(value or 0)


def build_sqlite_memory_embedding_store(database_path: Path) -> SqliteMemoryEmbeddingStore:
    """El almacén de huellas sobre ``database_path``, con sqlite-vec si carga."""
    engine = build_engine(database_path)
    event.listen(engine, "connect", _load_sqlite_vec)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT vec_version()"))
        available = True
    except Exception as exc:  # sin sqlite-vec, Sirius sigue buscando por palabras
        _logger.warning("sqlite-vec no se pudo cargar (%s): solo por palabras", type(exc).__name__)
        engine.dispose()
        engine = build_engine(database_path)
        available = False
    return SqliteMemoryEmbeddingStore(build_session_factory(engine), engine, available=available)
