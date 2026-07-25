"""Huellas deterministas para demostrar que Sirius 0.1 no se toca.

Un spike solo puede afirmar que la capacidad se obtuvo «por adición» si la
huella de todo lo heredado (esquema y datos) es idéntica antes y después.
"""

from __future__ import annotations

import hashlib
import sqlite3

LEGACY_TABLES: tuple[str, ...] = (
    "alembic_version",
    "conversations",
    "messages",
    "projects",
    "project_revisions",
    "memories",
    "memory_revisions",
    "events",
    "decisions",
    "decision_revisions",
    "identities",
    "identity_versions",
    "llm_usage",
)


def legacy_schema_dump(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        "SELECT type, name, tbl_name, COALESCE(sql, '') FROM sqlite_master "
        "WHERE name NOT LIKE 'x\\_%' ESCAPE '\\' "
        "AND tbl_name NOT LIKE 'x\\_%' ESCAPE '\\' "
        "ORDER BY type, name"
    ).fetchall()
    return "\n".join(f"{r[0]}|{r[1]}|{r[2]}|{r[3]}" for r in rows)


def legacy_data_dump(connection: sqlite3.Connection) -> str:
    parts: list[str] = []
    for table in LEGACY_TABLES:
        rows = connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
        parts.append(f"== {table} ({len(rows)}) ==")
        parts.extend(repr(row) for row in rows)
    return "\n".join(parts)


def legacy_fingerprint(connection: sqlite3.Connection) -> str:
    combined = legacy_schema_dump(connection) + "\n#DATA#\n" + legacy_data_dump(connection)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def table_names(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    return [str(row[0]) for row in rows]


def dump_hash(connection: sqlite3.Connection, tables: tuple[str, ...]) -> str:
    parts: list[str] = []
    for table in tables:
        rows = connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
        parts.append(f"== {table} ({len(rows)}) ==")
        parts.extend(repr(row) for row in rows)
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
