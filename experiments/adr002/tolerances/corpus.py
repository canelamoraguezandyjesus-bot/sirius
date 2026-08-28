"""Corpus sintetico de referencia: 5.000 mensajes y 500 recuerdos.

El esquema se obtiene SIEMPRE ejecutando la cadena canonica de Alembic
(``upgrade_to_head``) sobre un fichero temporal. Nunca se escribe DDL de
0.1 a mano y nunca se modifica la cadena de migraciones.

Todo el contenido es sintetico y determinista: no hay datos reales, ni
secretos, ni red. Los tokens de control estan disenados para ser un unico
termino tras la tokenizacion de FTS5, de modo que cada escenario mide lo
que dice medir y no un efecto de tokenizacion.
"""

from __future__ import annotations

import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from sirius.adapters.persistence.migrations import upgrade_to_head

# Volumen de referencia exigido por el paquete de trabajo 02 (§5.2).
MENSAJES = 5_000
RECUERDOS = 500
DECISIONES = 50

_BASE_TS = "2026-01-01T00:00:00"

# Tokens de control. Cada uno es una sola palabra en minusculas sin
# separadores, para que FTS5 lo indexe como un unico termino.
TOKEN_AUSENTE = "zetaausentenoindexado"
TOKEN_UNICO = "zetaunicovigente"
TOKEN_FRECUENTE = "zetafrecuente"
TOKEN_NO_REPORTABLE = "zetaocultoarchivado"
TOKEN_AJENO = "zetaproyectoajeno"

# Cuantos recuerdos vigentes contienen TOKEN_FRECUENTE.
RECUERDOS_CON_TOKEN_FRECUENTE = 200


@dataclass(frozen=True, slots=True)
class CorpusIds:
    """Identificadores devueltos por el generador."""

    conversation_id: int
    proyecto_activo_id: int
    proyecto_ajeno_id: int
    memoria_unica_id: int
    memoria_no_reportable_id: int
    memoria_ajena_id: int
    memorias_vigentes: int
    memorias_frecuentes: int
    mensajes: int
    decisiones_aprobadas: int


def nueva_base_temporal(prefix: str = "adr002_tol_") -> Path:
    """Un fichero de base de datos nuevo en el directorio temporal."""
    return Path(tempfile.mkdtemp(prefix=prefix)) / "linea_base.db"


def _conectar(database_path: Path) -> sqlite3.Connection:
    """Conexion con las mismas garantias que usa Sirius 0.1 en produccion."""
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def construir_esquema(database_path: Path) -> None:
    """Aplica la cadena canonica de Alembic hasta head. No la modifica."""
    upgrade_to_head(database_path)


def poblar(database_path: Path) -> CorpusIds:
    """Rellena el corpus de referencia con el volumen exigido."""
    connection = _conectar(database_path)
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

        proyecto_activo_id = _insertar_proyecto(cursor, "Proyecto activo", is_active=1)
        proyecto_ajeno_id = _insertar_proyecto(cursor, "Proyecto ajeno", is_active=0)
        for project_id in (proyecto_activo_id, proyecto_ajeno_id):
            cursor.execute(
                "INSERT INTO project_revisions (project_id, version, objective, state_summary, "
                "blockers_json, next_step, source_event_id, created_at) "
                "VALUES (?, 1, ?, ?, '[]', ?, NULL, ?)",
                (project_id, "objetivo", "estado", "siguiente paso", _BASE_TS),
            )

        # --- 5.000 mensajes.
        mensajes = [
            (
                conversation_id,
                indice,
                "user" if indice % 2 == 0 else "sirius",
                f"mensaje sintetico numero {indice} sobre presupuesto reunion y calendario",
                _BASE_TS,
                f"op-{indice}",
                1,
                "completed",
            )
            for indice in range(MENSAJES)
        ]
        cursor.executemany(
            "INSERT INTO messages (conversation_id, sequence, role, content, created_at, "
            "operation_id, identity_version, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            mensajes,
        )

        cursor.execute(
            "INSERT INTO events (event_type, actor, message_id, created_at) "
            "VALUES ('memory.created', 'user', NULL, ?)",
            (_BASE_TS,),
        )
        event_id = int(cursor.lastrowid or 0)

        # --- 500 recuerdos, cada uno con dos revisiones (una vigente).
        memoria_unica_id = 0
        memoria_no_reportable_id = 0
        memoria_ajena_id = 0
        memorias_vigentes = 0
        memorias_frecuentes = 0

        for indice in range(RECUERDOS):
            # Reparto determinista: un recuerdo con token unico, uno
            # archivado con token no reportable, uno vigente en el proyecto
            # ajeno, y el resto vigentes en el proyecto activo.
            if indice == 0:
                estado, project_id, extra = "current", proyecto_activo_id, TOKEN_UNICO
            elif indice == 1:
                estado, project_id, extra = "archived", proyecto_activo_id, TOKEN_NO_REPORTABLE
            elif indice == 2:
                estado, project_id, extra = "current", proyecto_ajeno_id, TOKEN_AJENO
            else:
                estado, project_id = "current", proyecto_activo_id
                extra = TOKEN_FRECUENTE if indice <= RECUERDOS_CON_TOKEN_FRECUENTE + 2 else ""

            cursor.execute(
                "INSERT INTO memories (status, created_at, updated_at, subject_key, project_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (estado, _BASE_TS, _BASE_TS, f"asunto-{indice}", project_id),
            )
            memory_id = int(cursor.lastrowid or 0)

            if indice == 0:
                memoria_unica_id = memory_id
            elif indice == 1:
                memoria_no_reportable_id = memory_id
            elif indice == 2:
                memoria_ajena_id = memory_id

            if estado == "current":
                memorias_vigentes += 1
            if extra == TOKEN_FRECUENTE:
                memorias_frecuentes += 1

            cuerpo = f"recuerdo sintetico {indice} sobre presupuesto anual y calendario {extra}"
            cursor.execute(
                "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
                "created_at, source_event_id) VALUES (?, 1, ?, 'origen', 0, ?, ?)",
                (memory_id, f"version previa del recuerdo {indice}", _BASE_TS, event_id),
            )
            cursor.execute(
                "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
                "created_at, source_event_id) VALUES (?, 2, ?, 'origen', 1, ?, ?)",
                (memory_id, cuerpo, _BASE_TS, event_id),
            )

        # --- Decisiones aprobadas, para que rank() las recorra tambien.
        decisiones_aprobadas = 0
        for indice in range(DECISIONES):
            cursor.execute(
                "INSERT INTO decisions (subject, project_id, status, created_at, updated_at, "
                "supersedes_decision_id) VALUES (?, ?, 'approved', ?, ?, NULL)",
                (f"asunto de decision {indice}", proyecto_activo_id, _BASE_TS, _BASE_TS),
            )
            decision_id = int(cursor.lastrowid or 0)
            decisiones_aprobadas += 1
            cursor.execute(
                "INSERT INTO decision_revisions (decision_id, version, content, source_event_id, "
                "is_current, created_at) VALUES (?, 1, ?, NULL, 1, ?)",
                (decision_id, f"contenido de la decision {indice} sobre calendario", _BASE_TS),
            )

        cursor.execute(
            "INSERT INTO llm_usage (year_month, spent_usd, updated_at) VALUES ('2026-01', 0.0, ?)",
            (_BASE_TS,),
        )

        connection.commit()
        return CorpusIds(
            conversation_id=conversation_id,
            proyecto_activo_id=proyecto_activo_id,
            proyecto_ajeno_id=proyecto_ajeno_id,
            memoria_unica_id=memoria_unica_id,
            memoria_no_reportable_id=memoria_no_reportable_id,
            memoria_ajena_id=memoria_ajena_id,
            memorias_vigentes=memorias_vigentes,
            memorias_frecuentes=memorias_frecuentes,
            mensajes=MENSAJES,
            decisiones_aprobadas=decisiones_aprobadas,
        )
    finally:
        connection.close()


def _insertar_proyecto(cursor: sqlite3.Cursor, name: str, *, is_active: int) -> int:
    cursor.execute(
        "INSERT INTO projects (name, objective, current_state, next_step, is_active, created_at, "
        "updated_at, blockers, status) VALUES (?, ?, ?, ?, ?, ?, ?, '', 'active')",
        (name, "objetivo", "estado", "siguiente paso", is_active, _BASE_TS, _BASE_TS),
    )
    return int(cursor.lastrowid or 0)


def corpus_de_referencia(prefix: str = "adr002_tol_") -> tuple[Path, CorpusIds]:
    """Atajo: base nueva + esquema canonico + corpus de referencia."""
    database_path = nueva_base_temporal(prefix)
    construir_esquema(database_path)
    ids = poblar(database_path)
    return database_path, ids
