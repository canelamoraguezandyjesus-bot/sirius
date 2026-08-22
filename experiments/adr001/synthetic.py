"""Generación de bases sintéticas con el esquema REAL de Sirius 0.1.

El esquema se obtiene siempre ejecutando la cadena canónica de Alembic
(``upgrade_to_head``) sobre un fichero temporal. Nunca se escribe DDL de
0.1 a mano y nunca se modifica la cadena de migraciones.

Los datos son sintéticos y deterministas. No se usa ningún dato real del
usuario, ni secretos, ni red.
"""

from __future__ import annotations

import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from sirius.adapters.persistence.migrations import upgrade_to_head

# Token único e improbable, usado por los spikes 10 y 19 para buscar
# fragmentos del contenido borrado dentro de los ficheros de la base.
CANARY = "ZQXJ7-CANARIO-SINTETICO-ADR001-42"

_BASE_TS = "2026-01-01T00:00:00"


@dataclass(frozen=True)
class SyntheticIds:
    """Identificadores devueltos por el generador, para que los spikes
    puedan referirse a filas concretas sin volver a consultarlas."""

    conversation_id: int
    active_project_id: int
    other_project_ids: tuple[int, ...]
    memory_ids: tuple[int, ...]
    decision_ids: tuple[int, ...]
    event_ids: tuple[int, ...]
    canary_message_id: int
    canary_memory_id: int


def new_temp_db(prefix: str = "adr001_") -> Path:
    """Un fichero de base de datos nuevo en el directorio temporal del sistema."""
    directory = Path(tempfile.mkdtemp(prefix=prefix))
    return directory / "sintetica.db"


def create_baseline_schema(database_path: Path) -> Path:
    """Aplica la cadena canónica de Alembic hasta head sobre una base nueva."""
    upgrade_to_head(database_path)
    return database_path


def connect(database_path: Path) -> sqlite3.Connection:
    """Conexión con las mismas garantías que usa Sirius 0.1 en producción."""
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def populate_representative(database_path: Path, *, with_canary: bool = True) -> SyntheticIds:
    """Rellena una base 0.1 con datos representativos de todas las tablas.

    Cubre los casos que el paquete exige para el spike 15: mensajes,
    memorias y revisiones, decisiones y revisiones, proyectos y revisiones,
    eventos, índices FTS5, y estados vigente / archivado / sustituido /
    redactado, con relaciones suficientes para detectar pérdidas.
    """
    connection = connect(database_path)
    try:
        cursor = connection.cursor()

        cursor.execute("INSERT INTO conversations (created_at, is_main) VALUES (?, 1)", (_BASE_TS,))
        conversation_id = int(cursor.lastrowid or 0)

        cursor.execute("INSERT INTO identities (created_at) VALUES (?)", (_BASE_TS,))
        identity_id = int(cursor.lastrowid or 0)
        cursor.execute(
            "INSERT INTO identity_versions (identity_id, version, name, description, "
            "personality_instructions, is_current, created_at) VALUES (?, 1, ?, ?, ?, 1, ?)",
            (identity_id, "Sirius", "identidad sintetica", "instrucciones sinteticas", _BASE_TS),
        )

        # Un solo proyecto activo: uq_projects_single_active lo impone.
        active_project_id = _insert_project(cursor, "Proyecto activo", is_active=1)
        other_project_ids = (
            _insert_project(cursor, "Proyecto secundario", is_active=0),
            _insert_project(cursor, "Proyecto terciario", is_active=0),
        )

        for project_id in (active_project_id, *other_project_ids):
            cursor.execute(
                "INSERT INTO project_revisions (project_id, version, objective, state_summary, "
                "blockers_json, next_step, source_event_id, created_at) "
                "VALUES (?, 1, ?, ?, '[]', ?, NULL, ?)",
                (project_id, "objetivo", "estado", "siguiente paso", _BASE_TS),
            )

        message_ids: list[int] = []
        for index in range(6):
            role = "user" if index % 2 == 0 else "sirius"
            content = f"mensaje sintetico numero {index}"
            cursor.execute(
                "INSERT INTO messages (conversation_id, sequence, role, content, created_at, "
                "operation_id, identity_version, status) VALUES (?, ?, ?, ?, ?, ?, 1, 'completed')",
                (conversation_id, index, role, content, _BASE_TS, f"op-{index}"),
            )
            message_ids.append(int(cursor.lastrowid or 0))

        canary_content = (
            f"mensaje con canario {CANARY} incrustado" if with_canary else "sin canario"
        )
        cursor.execute(
            "INSERT INTO messages (conversation_id, sequence, role, content, created_at, "
            "operation_id, identity_version, status) "
            "VALUES (?, 99, 'user', ?, ?, 'op-canary', 1, 'completed')",
            (conversation_id, canary_content, _BASE_TS),
        )
        canary_message_id = int(cursor.lastrowid or 0)

        # Un mensaje redactado: content NULL + redacted_at, estado REDACTED.
        cursor.execute(
            "INSERT INTO messages (conversation_id, sequence, role, content, created_at, "
            "operation_id, identity_version, status, redacted_at) "
            "VALUES (?, 100, 'user', NULL, ?, 'op-redactado', 1, 'redacted', ?)",
            (conversation_id, _BASE_TS, _BASE_TS),
        )

        event_ids: list[int] = []
        for index, message_id in enumerate(message_ids[:3]):
            cursor.execute(
                "INSERT INTO events (event_type, actor, message_id, created_at) "
                "VALUES (?, 'user', ?, ?)",
                (f"memory.created.{index}", message_id, _BASE_TS),
            )
            event_ids.append(int(cursor.lastrowid or 0))

        memory_ids: list[int] = []
        for index in range(4):
            # status recorre el enum heredado completo: current / archived / deleted.
            status = ("current", "current", "archived", "deleted")[index]
            cursor.execute(
                "INSERT INTO memories (status, created_at, updated_at, subject_key, project_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (status, _BASE_TS, _BASE_TS, f"asunto-{index}", active_project_id),
            )
            memory_id = int(cursor.lastrowid or 0)
            memory_ids.append(memory_id)

            # Dos revisiones: una histórica y una vigente (is_current = 1).
            content_v1 = None if status == "deleted" else f"contenido v1 de la memoria {index}"
            content_v2 = None if status == "deleted" else f"contenido v2 de la memoria {index}"
            cursor.execute(
                "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
                "created_at, source_event_id) VALUES (?, 1, ?, ?, 0, ?, ?)",
                (memory_id, content_v1, "origen textual libre", _BASE_TS, event_ids[index % 3]),
            )
            cursor.execute(
                "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
                "created_at, source_event_id) VALUES (?, 2, ?, ?, 1, ?, ?)",
                (memory_id, content_v2, "origen textual libre", _BASE_TS, event_ids[index % 3]),
            )

        cursor.execute(
            "INSERT INTO memories (status, created_at, updated_at, subject_key, project_id) "
            "VALUES ('current', ?, ?, 'asunto-canario', ?)",
            (_BASE_TS, _BASE_TS, active_project_id),
        )
        canary_memory_id = int(cursor.lastrowid or 0)
        canary_memory_content = (
            f"memoria con canario {CANARY} incrustado" if with_canary else "sin canario"
        )
        cursor.execute(
            "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
            "created_at, source_event_id) VALUES (?, 1, ?, 'origen canario', 1, ?, NULL)",
            (canary_memory_id, canary_memory_content, _BASE_TS),
        )

        decision_ids: list[int] = []
        previous_decision_id: int | None = None
        for index in range(3):
            status = ("approved", "superseded", "archived")[index]
            cursor.execute(
                "INSERT INTO decisions (subject, project_id, status, created_at, updated_at, "
                "supersedes_decision_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    f"decision-{index}",
                    active_project_id,
                    status,
                    _BASE_TS,
                    _BASE_TS,
                    previous_decision_id,
                ),
            )
            decision_id = int(cursor.lastrowid or 0)
            decision_ids.append(decision_id)
            previous_decision_id = decision_id
            cursor.execute(
                "INSERT INTO decision_revisions (decision_id, version, content, source_event_id, "
                "is_current, created_at) VALUES (?, 1, ?, ?, 1, ?)",
                (decision_id, f"contenido de la decision {index}", None, _BASE_TS),
            )

        cursor.execute(
            "INSERT INTO llm_usage (year_month, spent_usd, updated_at) VALUES ('2026-01', 1.23, ?)",
            (_BASE_TS,),
        )

        connection.commit()
        return SyntheticIds(
            conversation_id=conversation_id,
            active_project_id=active_project_id,
            other_project_ids=other_project_ids,
            memory_ids=tuple(memory_ids),
            decision_ids=tuple(decision_ids),
            event_ids=tuple(event_ids),
            canary_message_id=canary_message_id,
            canary_memory_id=canary_memory_id,
        )
    finally:
        connection.close()


def _insert_project(cursor: sqlite3.Cursor, name: str, *, is_active: int) -> int:
    cursor.execute(
        "INSERT INTO projects (name, objective, current_state, next_step, is_active, created_at, "
        "updated_at, blockers, status) VALUES (?, ?, ?, ?, ?, ?, ?, '', 'active')",
        (name, "objetivo", "estado", "siguiente paso", is_active, _BASE_TS, _BASE_TS),
    )
    return int(cursor.lastrowid or 0)


def fresh_populated_db(
    prefix: str = "adr001_", *, with_canary: bool = True
) -> tuple[Path, SyntheticIds]:
    """Atajo: base nueva + esquema canónico + datos representativos."""
    database_path = new_temp_db(prefix)
    create_baseline_schema(database_path)
    ids = populate_representative(database_path, with_canary=with_canary)
    return database_path, ids
