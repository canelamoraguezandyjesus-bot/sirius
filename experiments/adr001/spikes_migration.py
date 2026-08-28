"""Spikes 15 y 16: migracion de una base 0.1 representativa y rollback.

El ensayo demuestra VIABILIDAD, no estrategia. No se decide secuencia
productiva, ventana de corte, dual-write, despliegue ni retirada de tablas:
todo eso pertenece a ADR-004.
"""

from __future__ import annotations

import sqlite3

from experiments.adr001 import xmodel
from experiments.adr001.evidence import (
    FAIL_STRUCTURAL_MODEL,
    PASS,
    SpikeEvidence,
)
from experiments.adr001.fingerprint import (
    LEGACY_TABLES,
    legacy_fingerprint,
    legacy_schema_dump,
)
from experiments.adr001.synthetic import fresh_populated_db

T1 = "2026-02-01T00:00:00"

_MIGRATION_STATE_DDL = """
CREATE TABLE x_migration_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    authority TEXT NOT NULL CHECK (authority IN ('legacy', 'experimental')),
    note TEXT NOT NULL
);
"""


def _counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in LEGACY_TABLES
    }


def _backfill(connection: sqlite3.Connection) -> dict[str, int]:
    """Proyecta el conocimiento heredado sobre el modelo experimental.

    Solo LEE de las tablas de 0.1. Cada memoria con revision vigente produce
    exactamente una afirmacion, su procedencia y sus dimensiones de estado.
    """
    scopes = xmodel.seed_scopes(connection)
    rows = connection.execute(
        "SELECT m.id, m.status, m.project_id, r.content, r.origin, r.source_event_id, r.created_at "
        "FROM memories m JOIN memory_revisions r ON r.memory_id = m.id "
        "WHERE r.is_current = 1 ORDER BY m.id"
    ).fetchall()

    creadas = 0
    procedencias = 0
    estados = 0
    for memory_id, status, project_id, content, origin, source_event_id, created_at in rows:
        scope_key = f"proyecto:{project_id}" if project_id is not None else "global"
        scope_id = scopes.get(scope_key, scopes["global"])
        assertion_id = xmodel.insert_assertion(
            connection,
            scope_id=scope_id,
            subject=f"memoria:{memory_id}",
            predicate="afirma",
            # El contenido borrado en 0.1 es NULL; se preserva como marcador.
            object_=content if content is not None else "",
            valid_from=str(created_at),
            valid_to=None,
            recorded_at=str(created_at),
            legacy_memory_id=int(memory_id),
        )
        creadas += 1
        xmodel.add_provenance(
            connection,
            assertion_id,
            source_kind="migracion",
            detail=str(origin),
            recorded_at=T1,
            source_event_id=int(source_event_id) if source_event_id is not None else None,
        )
        procedencias += 1
        proyeccion = xmodel.LEGACY_STATUS_PROJECTION.get(str(status), {})
        for dimension, value in proyeccion.items():
            xmodel.set_state(connection, assertion_id, dimension, value, T1)
            estados += 1
    connection.commit()
    return {"afirmaciones": creadas, "procedencias": procedencias, "estados": estados}


def spike_15() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=15,
        nombre="Migracion de una base Sirius 0.1 representativa",
        objetivo=(
            "Demostrar que una base 0.1 real puede expandirse al modelo nuevo conservando la "
            "semantica, sin perdidas ni duplicaciones y sin dos autoridades simultaneas."
        ),
        incertidumbre=(
            "Se ignora si el backfill puede hacerse sin escribir en las tablas heredadas y sin "
            "perder los casos archivado, sustituido, redactado y borrado."
        ),
        dataset=(
            "Base sintetica con el esquema real de 0.1: mensajes (incluido uno redactado), "
            "memorias con revisiones en los tres estados del enum, decisiones con sustitucion, "
            "3 proyectos con revisiones, eventos, uso de LLM e indices FTS5."
        ),
        preparacion="Linea base: huella de 0.1, recuentos por tabla y head de Alembic.",
        operacion="Expansion aditiva + backfill de solo lectura + reconstruccion de derivados.",
        resultado_esperado=(
            "Cada memoria vigente produce exactamente una afirmacion; 0.1 queda byte a byte igual; "
            "la autoridad sigue siendo unica."
        ),
        criterio_de_fallo=(
            "Perdida, duplicacion, escritura en tablas heredadas, cambio de head, o dos "
            "autoridades a la vez."
        ),
    )

    database_path, _ids = fresh_populated_db("adr001_mig_")
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys=ON")

    huella_base = legacy_fingerprint(connection)
    recuentos_base = _counts(connection)
    head_base = str(connection.execute("SELECT version_num FROM alembic_version").fetchone()[0])
    memorias_vigentes = int(
        connection.execute(
            "SELECT COUNT(*) FROM memories m JOIN memory_revisions r ON r.memory_id = m.id "
            "WHERE r.is_current = 1"
        ).fetchone()[0]
    )

    xmodel.install_experimental_model(connection)
    connection.executescript(_MIGRATION_STATE_DDL)
    connection.execute(
        "INSERT INTO x_migration_state (id, authority, note) VALUES (1, 'legacy', ?)",
        ("durante la expansion la autoridad sigue siendo Sirius 0.1",),
    )
    connection.commit()

    resumen = _backfill(connection)
    xmodel.rebuild_derived(connection)

    huella_tras = legacy_fingerprint(connection)
    recuentos_tras = _counts(connection)
    head_tras = str(connection.execute("SELECT version_num FROM alembic_version").fetchone()[0])

    afirmaciones = int(connection.execute("SELECT COUNT(*) FROM x_assertion").fetchone()[0])
    distintas = int(
        connection.execute("SELECT COUNT(DISTINCT legacy_memory_id) FROM x_assertion").fetchone()[0]
    )
    huerfanas = int(
        connection.execute(
            "SELECT COUNT(*) FROM x_assertion a LEFT JOIN memories m ON m.id = a.legacy_memory_id "
            "WHERE a.legacy_memory_id IS NOT NULL AND m.id IS NULL"
        ).fetchone()[0]
    )
    sin_procedencia = int(
        connection.execute(
            "SELECT COUNT(*) FROM x_assertion a LEFT JOIN x_provenance p "
            "ON p.assertion_id = a.id WHERE p.id IS NULL"
        ).fetchone()[0]
    )
    contenido_conservado = int(
        connection.execute(
            "SELECT COUNT(*) FROM x_assertion a JOIN memory_revisions r "
            "ON r.memory_id = a.legacy_memory_id AND r.is_current = 1 "
            "WHERE a.object = COALESCE(r.content, '')"
        ).fetchone()[0]
    )
    autoridades = [
        str(row[0])
        for row in connection.execute("SELECT authority FROM x_migration_state").fetchall()
    ]
    derivados = int(connection.execute("SELECT COUNT(*) FROM x_current_cache").fetchone()[0])
    connection.close()

    ok = (
        huella_base == huella_tras
        and recuentos_base == recuentos_tras
        and head_base == head_tras
        and afirmaciones == memorias_vigentes
        and distintas == memorias_vigentes
        and huerfanas == 0
        and sin_procedencia == 0
        and contenido_conservado == memorias_vigentes
        and autoridades == ["legacy"]
    )
    evidence.evidencia = {
        "head_alembic_antes": head_base,
        "head_alembic_despues": head_tras,
        "head_sin_cambios": head_base == head_tras,
        "huella_0_1_antes": huella_base,
        "huella_0_1_despues": huella_tras,
        "0_1_byte_a_byte_igual": huella_base == huella_tras,
        "recuentos_heredados_iguales": recuentos_base == recuentos_tras,
        "recuentos": recuentos_base,
        "memorias_vigentes_en_0_1": memorias_vigentes,
        "afirmaciones_creadas": afirmaciones,
        "memorias_distintas_cubiertas": distintas,
        "sin_perdidas": distintas == memorias_vigentes,
        "sin_duplicaciones": afirmaciones == distintas,
        "afirmaciones_huerfanas": huerfanas,
        "afirmaciones_sin_procedencia": sin_procedencia,
        "contenido_conservado_en_todas": contenido_conservado == memorias_vigentes,
        "autoridad_declarada": autoridades,
        "autoridad_unica": autoridades == ["legacy"],
        "derivados_reconstruidos": derivados,
        "resumen_backfill": resumen,
    }
    evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
    evidence.conclusion = (
        "La migracion es viable de forma puramente aditiva: 0.1 queda intacto byte a byte, el head "
        "de Alembic no cambia, no hay perdidas ni duplicaciones y la autoridad sigue siendo unica. "
        "No se decide aqui la estrategia final (ADR-004)."
        if ok
        else "La migracion no conserva la semantica o exige escribir en el modelo heredado."
    )
    return evidence


def spike_16() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=16,
        nombre="Rollback",
        objetivo="Demostrar que la expansion puede deshacerse por completo y sin residuo.",
        incertidumbre=(
            "Se ignora si al revertir queda algun objeto huerfano (indices automaticos, sombras "
            "FTS5) que impida volver exactamente al estado anterior."
        ),
        dataset="La misma base migrada del spike 15.",
        preparacion="Capturar el esquema completo y la huella antes de expandir.",
        operacion="Expandir, hacer backfill y despues eliminar todo lo experimental.",
        resultado_esperado=(
            "El esquema completo y la huella vuelven a ser identicos a los de partida y la base "
            "sigue siendo utilizable por el codigo real de Sirius 0.1."
        ),
        criterio_de_fallo="Cualquier residuo en sqlite_master o cualquier cambio en 0.1.",
    )

    database_path, _ids = fresh_populated_db("adr001_roll_")
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys=ON")

    esquema_base = legacy_schema_dump(connection)
    esquema_completo_base = _full_schema(connection)
    huella_base = legacy_fingerprint(connection)
    head_base = str(connection.execute("SELECT version_num FROM alembic_version").fetchone()[0])

    xmodel.install_experimental_model(connection)
    connection.executescript(_MIGRATION_STATE_DDL)
    connection.execute(
        "INSERT INTO x_migration_state (id, authority, note) VALUES (1, 'legacy', 'ensayo')"
    )
    connection.commit()
    _backfill(connection)
    xmodel.rebuild_derived(connection)
    objetos_tras_expandir = len(_full_schema(connection).splitlines())

    # Rollback: eliminar TODO lo experimental, derivados y sombras incluidos.
    xmodel.drop_derived(connection)
    for table in reversed((*xmodel.CANONICAL_TABLES, "x_migration_state")):
        connection.execute(f"DROP TABLE IF EXISTS {table}")
    connection.commit()

    esquema_tras = legacy_schema_dump(connection)
    esquema_completo_tras = _full_schema(connection)
    huella_tras = legacy_fingerprint(connection)
    head_tras = str(connection.execute("SELECT version_num FROM alembic_version").fetchone()[0])
    residuo = [
        line
        for line in esquema_completo_tras.splitlines()
        if "|x_" in line or line.startswith("x_")
    ]
    connection.close()

    utilizable, detalle_uso = _still_usable_by_sirius(database_path)

    ok = (
        esquema_base == esquema_tras
        and esquema_completo_base == esquema_completo_tras
        and huella_base == huella_tras
        and head_base == head_tras
        and residuo == []
        and utilizable
    )
    evidence.evidencia = {
        "objetos_en_sqlite_master_tras_expandir": objetos_tras_expandir,
        "objetos_en_sqlite_master_tras_rollback": len(esquema_completo_tras.splitlines()),
        "objetos_en_sqlite_master_al_inicio": len(esquema_completo_base.splitlines()),
        "esquema_completo_identico_al_inicial": esquema_completo_base == esquema_completo_tras,
        "residuo_experimental": residuo,
        "huella_0_1_antes": huella_base,
        "huella_0_1_tras_rollback": huella_tras,
        "0_1_byte_a_byte_igual": huella_base == huella_tras,
        "head_alembic_sin_cambios": head_base == head_tras,
        "base_sigue_siendo_utilizable_por_sirius_0_1": utilizable,
        "detalle_de_uso_real": detalle_uso,
    }
    evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
    evidence.conclusion = (
        "El rollback es total y sin residuo: sqlite_master vuelve a ser identico, 0.1 queda byte a "
        "byte igual y el codigo real de Sirius 0.1 sigue leyendo la base sin cambios."
        if ok
        else "El rollback deja residuo o altera el modelo heredado."
    )
    return evidence


def _full_schema(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        "SELECT type, name, tbl_name FROM sqlite_master ORDER BY type, name"
    ).fetchall()
    return "\n".join(f"{r[0]}|{r[1]}|{r[2]}" for r in rows)


def _still_usable_by_sirius(database_path) -> tuple[bool, str]:
    """Abre la base con el codigo REAL de Sirius 0.1 y lee de ella."""
    try:
        from sirius.adapters.persistence.migrations import get_supported_schema_version
        from sirius.adapters.persistence.sqlite_conversation_repository import (
            build_sqlite_conversation_repository,
        )

        version = get_supported_schema_version()
        repository = build_sqlite_conversation_repository(database_path)
        conversation = repository.get_main_conversation()
        if conversation is None:
            return False, "no se encontro la conversacion principal"
        messages = repository.list_messages(conversation.id)
        return True, (
            f"schema_version={version}; conversacion={conversation.id}; mensajes={len(messages)}"
        )
    except Exception as error:
        return False, f"fallo al usar el codigo real de 0.1: {error!r}"


ALL_MIGRATION_SPIKES = (spike_15, spike_16)
