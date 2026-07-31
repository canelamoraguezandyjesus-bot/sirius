"""Fixture pequeno y propio para las pruebas tecnicas de los candidatos.

**No es el corpus oficial del benchmark**, y no puede serlo: evaluar un
candidato con el corpus congelado v0.4 exige una autorizacion de benchmark que
no existe. Este fixture tiene una docena de items escogidos para ejercitar
**reglas**, no para medir nada: cada uno existe porque activa una puerta, una
transicion o una parada concretas.

El esquema es el canonico de Sirius 0.1 —la cadena de Alembic hasta
``61be4bb269bf``, sin DDL adicional—, de modo que lo que las pruebas ejercitan
es el sustrato real y no una maqueta.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sirius.adapters.persistence.migrations import upgrade_to_head

_TS: Final = "2026-06-01T00:00:00"
_TS_TARDIO: Final = "2026-09-01T00:00:00"

PROYECTO_ACTIVO: Final = "1"
PROYECTO_AJENO: Final = "2"


@dataclass(frozen=True, slots=True)
class Fixture:
    """La base construida y los textos que la traza NO debe filtrar."""

    ruta: Path
    textos: tuple[str, ...]


#: (subject_key, texto, vigente, proyecto_activo, created_at). Cada fila tiene
#: un proposito de prueba declarado en el comentario.
_MEMORIAS: Final[tuple[tuple[str, str, bool, bool, str], ...]] = (
    # E1 exacta por clave, y afirmacion del sujeto "faro".
    ("faro-costa", "el faro ilumina la costa cada noche", True, True, _TS),
    # Polaridad NEGATIVA sobre el mismo sujeto estructural: no debe fusionarse.
    ("faro-niebla", "los faros no iluminan cuando hay niebla", True, True, _TS),
    # Condicion declarada por marcador lexico.
    ("boya-canal", "si la boya falla el canal se cierra", True, True, _TS),
    # Fuera de ambito: G4 debe descartarla con ambito cerrado al activo.
    ("faro-ajeno", "el faro del puerto vecino tambien ilumina", True, False, _TS),
    # No vigente: G6/G7 la excluyen de M1.
    ("faro-antiguo", "el faro antiguo fue retirado del servicio", False, True, _TS),
    # Posterior al corte de registro: G8 la descarta cuando hay corte.
    ("faro-futuro", "el faro nuevo iluminara el nuevo canal", True, True, _TS_TARDIO),
    # Variante morfologica: solo alcanzable por E2 desde "iluminar".
    ("senal-iluminacion", "la iluminacion del muelle depende del generador", True, True, _TS),
    # Parafrasis por raiz compartida con "canal": alcanzable en E3.
    ("dragado-canales", "los canales dragados admiten mayor calado", True, True, _TS),
)

#: (subject, texto, aprobada, proyecto_activo)
_DECISIONES: Final[tuple[tuple[str, str, bool, bool], ...]] = (
    ("faro-mantenimiento", "se aprueba el mantenimiento anual del faro", True, True),
    ("boya-retirada", "se propone retirar la boya del canal", False, True),
)

#: Historial: solo alcanzable por E4, y siempre como evidencia atribuida.
_MENSAJES: Final[tuple[str, ...]] = (
    "alguien comento que el faro estuvo apagado una noche",
    "el patron menciono la niebla del canal",
)


def construir(destino: Path) -> Fixture:
    """Base con el esquema canonico y el fixture pequeno. No mide nada."""
    upgrade_to_head(destino)
    conexion = sqlite3.connect(str(destino))
    conexion.execute("PRAGMA foreign_keys=ON")
    try:
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO conversations (created_at, is_main) VALUES (?, 1)", (_TS,))
        conversation_id = int(cursor.lastrowid or 0)
        cursor.execute("INSERT INTO identities (created_at) VALUES (?)", (_TS,))
        identity_id = int(cursor.lastrowid or 0)
        cursor.execute(
            "INSERT INTO identity_versions (identity_id, version, name, description, "
            "personality_instructions, is_current, created_at) VALUES (?, 1, ?, ?, ?, 1, ?)",
            (identity_id, "Sirius", "pruebas tecnicas", "sin instrucciones", _TS),
        )
        for nombre, activo in (("Proyecto activo", 1), ("Proyecto ajeno", 0)):
            cursor.execute(
                "INSERT INTO projects (name, objective, current_state, next_step, is_active, "
                "created_at, updated_at, blockers, status) VALUES (?, ?, ?, ?, ?, ?, ?, '', "
                "'active')",
                (nombre, "objetivo", "estado", "siguiente", activo, _TS, _TS),
            )
        cursor.execute(
            "INSERT INTO events (event_type, actor, message_id, created_at) "
            "VALUES ('memory.created', 'user', NULL, ?)",
            (_TS,),
        )
        event_id = int(cursor.lastrowid or 0)

        for clave, texto, vigente, activo, creado in _MEMORIAS:
            cursor.execute(
                "INSERT INTO memories (status, created_at, updated_at, subject_key, project_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    "current" if vigente else "archived",
                    creado,
                    creado,
                    clave,
                    int(PROYECTO_ACTIVO) if activo else int(PROYECTO_AJENO),
                ),
            )
            memory_id = int(cursor.lastrowid or 0)
            cursor.execute(
                "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
                "created_at, source_event_id) VALUES (?, 1, ?, 'fixture', 1, ?, ?)",
                (memory_id, texto, creado, event_id),
            )

        for asunto, texto, aprobada, activo in _DECISIONES:
            cursor.execute(
                "INSERT INTO decisions (subject, project_id, status, created_at, updated_at, "
                "supersedes_decision_id) VALUES (?, ?, ?, ?, ?, NULL)",
                (
                    asunto,
                    int(PROYECTO_ACTIVO) if activo else int(PROYECTO_AJENO),
                    "approved" if aprobada else "proposed",
                    _TS,
                    _TS,
                ),
            )
            decision_id = int(cursor.lastrowid or 0)
            cursor.execute(
                "INSERT INTO decision_revisions (decision_id, version, content, source_event_id, "
                "is_current, created_at) VALUES (?, 1, ?, NULL, 1, ?)",
                (decision_id, texto, _TS),
            )

        for indice, texto in enumerate(_MENSAJES):
            cursor.execute(
                "INSERT INTO messages (conversation_id, sequence, role, content, created_at, "
                "operation_id, identity_version, status) VALUES (?, ?, 'user', ?, ?, ?, 1, "
                "'completed')",
                (conversation_id, indice, texto, _TS, f"op-{indice}"),
            )
        conexion.commit()
    finally:
        conexion.close()

    textos = (
        *(t for _c, t, _v, _a, _f in _MEMORIAS),
        *(t for _s, t, _ap, _a in _DECISIONES),
        *_MENSAJES,
    )
    return Fixture(ruta=destino, textos=textos)


def borrar_derivado(ruta: Path) -> None:
    """Elimina el derivado del canon: triggers y tablas del FTS5."""
    conexion = sqlite3.connect(str(ruta))
    try:
        for fila in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%fts%'"
        ).fetchall():
            conexion.execute(f"DROP TRIGGER IF EXISTS {fila[0]}")
        for tabla in ("knowledge_fts", "message_fts"):
            conexion.execute(f"DROP TABLE IF EXISTS {tabla}")
        conexion.commit()
    finally:
        conexion.close()


def regenerar_derivado(ruta: Path) -> None:
    """Reconstruye el derivado **desde el canon**, no desde si mismo.

    Es la garantia de que el derivado es regenerable y no autoritativo: se
    recrea con el mismo DDL de la cadena canonica y se rellena leyendo las
    revisiones vigentes, nunca una copia del propio indice.
    """
    conexion = sqlite3.connect(str(ruta))
    try:
        conexion.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts "
            "USING fts5(kind UNINDEXED, item_id UNINDEXED, content)"
        )
        conexion.execute("CREATE VIRTUAL TABLE IF NOT EXISTS message_fts USING fts5(content)")
        conexion.execute("DELETE FROM knowledge_fts")
        conexion.execute("DELETE FROM message_fts")
        conexion.execute(
            "INSERT INTO knowledge_fts(rowid, kind, item_id, content) "
            "SELECT memory_id * 2, 'memory', memory_id, content FROM memory_revisions "
            "WHERE is_current = 1 AND content IS NOT NULL"
        )
        conexion.execute(
            "INSERT INTO knowledge_fts(rowid, kind, item_id, content) "
            "SELECT decision_id * 2 + 1, 'decision', decision_id, content "
            "FROM decision_revisions WHERE is_current = 1 AND content IS NOT NULL"
        )
        conexion.execute("INSERT INTO message_fts(rowid, content) SELECT id, content FROM messages")
        conexion.commit()
    finally:
        conexion.close()


__all__ = [
    "PROYECTO_ACTIVO",
    "PROYECTO_AJENO",
    "Fixture",
    "borrar_derivado",
    "construir",
    "regenerar_derivado",
]
