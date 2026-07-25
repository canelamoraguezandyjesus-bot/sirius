"""Modelo físico experimental ADITIVO sobre el esquema heredado de 0.1.

Este módulo materializa la hipótesis de la alternativa A tal y como quedó
definida de forma medible en el inventario de línea base: *A conserva este
esquema y añade*. Por tanto todo lo que aquí se crea son tablas NUEVAS con
prefijo ``x_``; no se hace ni un solo ALTER, DROP o UPDATE sobre ninguna
tabla de Sirius 0.1.

Si alguna capacidad exigida por los spikes no pudiera obtenerse por pura
adición y requiriese rediseñar una tabla heredada, ese spike terminaría en
``FAIL_STRUCTURAL_MODEL`` y conduciría a B. El modelo es deliberadamente
mínimo: no fija DDL definitivo ni nombres productivos.

Las siete dimensiones ortogonales de estado se declaran aquí de forma
EXPERIMENTAL (ver ``STATE_DIMENSIONS``). El paquete operativo v1.0 exige el
spike pero no enumera las dimensiones canónicas; la incertidumbre que el
spike resuelve es estructural (¿puede el modelo representar N dimensiones
independientes sin un enum monolítico y absorber el enum heredado sin
pérdida?), y esa respuesta no depende de los nombres concretos.
"""

from __future__ import annotations

import sqlite3

# Dimensiones ortogonales experimentales. El enum heredado
# ``memories.status`` (current/archived/deleted) colapsa al menos tres de
# ellas (existencia, disponibilidad y estado epistémico) en un solo valor.
STATE_DIMENSIONS: tuple[str, ...] = (
    "existencia",
    "disponibilidad",
    "epistemico",
    "confianza",
    "aprobacion",
    "sensibilidad",
    "verificacion",
)

# Mapeo del enum heredado a las dimensiones nuevas. Demuestra que un solo
# valor heredado se proyecta sobre varias dimensiones a la vez.
LEGACY_STATUS_PROJECTION: dict[str, dict[str, str]] = {
    "current": {"existencia": "presente", "disponibilidad": "activa", "epistemico": "afirmada"},
    "archived": {"existencia": "presente", "disponibilidad": "archivada", "epistemico": "afirmada"},
    "deleted": {"existencia": "borrada", "disponibilidad": "archivada", "epistemico": "retirada"},
}

_CANONICAL_DDL = """
CREATE TABLE x_scope (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NULL REFERENCES projects (id),
    kind TEXT NOT NULL CHECK (kind IN ('proyecto', 'global')),
    is_closed INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE x_scope_visibility (
    from_scope_id INTEGER NOT NULL REFERENCES x_scope (id),
    to_scope_id INTEGER NOT NULL REFERENCES x_scope (id),
    PRIMARY KEY (from_scope_id, to_scope_id)
);

CREATE TABLE x_assertion (
    id INTEGER PRIMARY KEY,
    legacy_memory_id INTEGER NULL REFERENCES memories (id),
    scope_id INTEGER NOT NULL REFERENCES x_scope (id),
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT NULL,
    recorded_at TEXT NOT NULL,
    recorded_until TEXT NULL,
    corrects_assertion_id INTEGER NULL REFERENCES x_assertion (id)
);

CREATE TABLE x_provenance (
    id INTEGER PRIMARY KEY,
    assertion_id INTEGER NOT NULL REFERENCES x_assertion (id),
    source_kind TEXT NOT NULL,
    source_event_id INTEGER NULL REFERENCES events (id),
    source_message_id INTEGER NULL REFERENCES messages (id),
    detail TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE x_stance (
    id INTEGER PRIMARY KEY,
    subject_assertion_id INTEGER NOT NULL REFERENCES x_assertion (id),
    object_assertion_id INTEGER NOT NULL REFERENCES x_assertion (id),
    stance TEXT NOT NULL CHECK (stance IN ('apoya', 'refuta')),
    strength REAL NOT NULL,
    provenance_id INTEGER NULL REFERENCES x_provenance (id)
);

CREATE TABLE x_state (
    assertion_id INTEGER NOT NULL REFERENCES x_assertion (id),
    dimension TEXT NOT NULL,
    value TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (assertion_id, dimension)
);
"""

# Derivados. Se crean aparte porque los spikes 18 y 10 los destruyen y los
# reconstruyen; ninguno puede ser fuente canónica.
_DERIVED_DDL = """
CREATE VIRTUAL TABLE x_assertion_fts USING fts5(body, content='');

CREATE TABLE x_current_cache (
    assertion_id INTEGER PRIMARY KEY,
    body TEXT NOT NULL,
    scope_id INTEGER NOT NULL
);
"""

CANONICAL_TABLES: tuple[str, ...] = (
    "x_scope",
    "x_scope_visibility",
    "x_assertion",
    "x_provenance",
    "x_stance",
    "x_state",
)

DERIVED_OBJECTS: tuple[str, ...] = ("x_assertion_fts", "x_current_cache")


def install_experimental_model(connection: sqlite3.Connection) -> None:
    """Crea las tablas experimentales. No toca ninguna tabla de 0.1."""
    connection.executescript(_CANONICAL_DDL)
    install_derived(connection)
    connection.commit()


def install_derived(connection: sqlite3.Connection) -> None:
    connection.executescript(_DERIVED_DDL)


def drop_derived(connection: sqlite3.Connection) -> None:
    """Elimina todos los derivados, incluidas las tablas sombra de FTS5."""
    connection.execute("DROP TABLE IF EXISTS x_assertion_fts")
    connection.execute("DROP TABLE IF EXISTS x_current_cache")
    connection.commit()


def rebuild_derived(connection: sqlite3.Connection) -> None:
    """Reconstruye los derivados EXCLUSIVAMENTE desde las tablas canónicas."""
    connection.execute("DELETE FROM x_assertion_fts")
    connection.execute("DELETE FROM x_current_cache")
    rows = connection.execute(
        "SELECT id, subject || ' ' || predicate || ' ' || object, scope_id "
        "FROM x_assertion WHERE recorded_until IS NULL ORDER BY id"
    ).fetchall()
    for assertion_id, body, scope_id in rows:
        connection.execute(
            "INSERT INTO x_assertion_fts (rowid, body) VALUES (?, ?)", (assertion_id, body)
        )
        connection.execute(
            "INSERT INTO x_current_cache (assertion_id, body, scope_id) VALUES (?, ?, ?)",
            (assertion_id, body, scope_id),
        )
    connection.commit()


def seed_scopes(connection: sqlite3.Connection) -> dict[str, int]:
    """Un ámbito por proyecto más un ámbito global, con visibilidad cerrada.

    Cerrado significa: desde un ámbito de proyecto solo se ven ese mismo
    ámbito y el global; nunca otro proyecto.
    """
    project_ids = [
        int(row[0]) for row in connection.execute("SELECT id FROM projects ORDER BY id").fetchall()
    ]
    scope_by_project: dict[str, int] = {}

    cursor = connection.execute(
        "INSERT INTO x_scope (project_id, kind, is_closed) VALUES (NULL, 'global', 1)"
    )
    global_scope_id = int(cursor.lastrowid or 0)
    scope_by_project["global"] = global_scope_id

    for project_id in project_ids:
        cursor = connection.execute(
            "INSERT INTO x_scope (project_id, kind, is_closed) VALUES (?, 'proyecto', 1)",
            (project_id,),
        )
        scope_id = int(cursor.lastrowid or 0)
        scope_by_project[f"proyecto:{project_id}"] = scope_id
        connection.execute(
            "INSERT INTO x_scope_visibility (from_scope_id, to_scope_id) VALUES (?, ?)",
            (scope_id, scope_id),
        )
        connection.execute(
            "INSERT INTO x_scope_visibility (from_scope_id, to_scope_id) VALUES (?, ?)",
            (scope_id, global_scope_id),
        )

    connection.execute(
        "INSERT INTO x_scope_visibility (from_scope_id, to_scope_id) VALUES (?, ?)",
        (global_scope_id, global_scope_id),
    )
    connection.commit()
    return scope_by_project


def insert_assertion(
    connection: sqlite3.Connection,
    *,
    scope_id: int,
    subject: str,
    predicate: str,
    object_: str,
    valid_from: str,
    valid_to: str | None,
    recorded_at: str,
    legacy_memory_id: int | None = None,
    corrects_assertion_id: int | None = None,
) -> int:
    cursor = connection.execute(
        "INSERT INTO x_assertion (legacy_memory_id, scope_id, subject, predicate, object, "
        "valid_from, valid_to, recorded_at, recorded_until, corrects_assertion_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)",
        (
            legacy_memory_id,
            scope_id,
            subject,
            predicate,
            object_,
            valid_from,
            valid_to,
            recorded_at,
            corrects_assertion_id,
        ),
    )
    return int(cursor.lastrowid or 0)


def add_provenance(
    connection: sqlite3.Connection,
    assertion_id: int,
    *,
    source_kind: str,
    detail: str,
    recorded_at: str,
    source_event_id: int | None = None,
    source_message_id: int | None = None,
) -> int:
    cursor = connection.execute(
        "INSERT INTO x_provenance (assertion_id, source_kind, source_event_id, "
        "source_message_id, detail, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
        (assertion_id, source_kind, source_event_id, source_message_id, detail, recorded_at),
    )
    return int(cursor.lastrowid or 0)


def set_state(
    connection: sqlite3.Connection,
    assertion_id: int,
    dimension: str,
    value: str,
    recorded_at: str,
) -> None:
    connection.execute(
        "INSERT INTO x_state (assertion_id, dimension, value, recorded_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (assertion_id, dimension) DO UPDATE SET value = excluded.value, "
        "recorded_at = excluded.recorded_at",
        (assertion_id, dimension, value, recorded_at),
    )


def valid_at(connection: sqlite3.Connection, moment: str) -> list[int]:
    """Consulta «válida en T»: sobre el eje de tiempo válido, mirando solo
    los registros vigentes en el eje de tiempo de registro."""
    rows = connection.execute(
        "SELECT id FROM x_assertion WHERE recorded_until IS NULL "
        "AND valid_from <= ? AND (valid_to IS NULL OR valid_to > ?) ORDER BY id",
        (moment, moment),
    ).fetchall()
    return [int(row[0]) for row in rows]


def known_at(connection: sqlite3.Connection, moment: str) -> list[int]:
    """Consulta «conocida en T»: sobre el eje de tiempo de registro,
    reconstruyendo lo que el sistema creía en ese instante."""
    rows = connection.execute(
        "SELECT id FROM x_assertion WHERE recorded_at <= ? "
        "AND (recorded_until IS NULL OR recorded_until > ?) ORDER BY id",
        (moment, moment),
    ).fetchall()
    return [int(row[0]) for row in rows]
