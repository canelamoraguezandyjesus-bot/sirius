"""Spikes 10 y 19: borrado duro y no reconstruibilidad.

El paquete exige distinguir cinco cosas que se confunden con facilidad:

1. borrado logico (marcar como borrado);
2. borrado del contenido canonico (quitar el texto de las tablas fuente);
3. eliminacion de derivados (FTS5, sombras, caches, resumenes);
4. purga fisica del fichero (paginas libres, WAL, SHM, VACUUM);
5. no reconstruibilidad dentro del modelo de amenaza.

Aqui no se afirma «no reconstruible» porque una consulta SQL no devuelva
filas: se inspeccionan los bytes de los ficheros buscando fragmentos
conocidos del contenido sintetico eliminado.

MODELO DE AMENAZA OPERATIVO de estos spikes (declarado explicitamente
porque el paquete v1.0 no lo enumera): un tercero con acceso de lectura a
los ficheros de la base (``.db``, ``-wal``, ``-shm``, ``-journal``) y a
copias generadas por la propia aplicacion. Queda FUERA: recuperacion
forense del medio fisico (sectores reasignados, SSD wear leveling,
instantaneas del sistema de ficheros y copias de seguridad previas).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from experiments.adr001 import xmodel
from experiments.adr001.evidence import (
    FAIL_ENGINE_SQLITE,
    PASS,
    SpikeEvidence,
)
from experiments.adr001.synthetic import CANARY, fresh_populated_db

# Token unico de una sola palabra: sobrevive a la tokenizacion de FTS5 como
# un unico termino, asi que aparece literalmente en las tablas sombra.
CANARY_TOKEN = "zqxj7canarioadr00142"

T1 = "2026-02-01T00:00:00"


def _sidecar_files(database_path: Path) -> dict[str, Path]:
    return {
        "db": database_path,
        "wal": database_path.with_name(database_path.name + "-wal"),
        "shm": database_path.with_name(database_path.name + "-shm"),
        "journal": database_path.with_name(database_path.name + "-journal"),
    }


def scan_for_canaries(database_path: Path) -> dict[str, dict[str, bool]]:
    """Busca los fragmentos conocidos en los bytes de cada fichero."""
    needles = {
        "frase": CANARY.encode("utf-8"),
        "token_fts": CANARY_TOKEN.encode("utf-8"),
    }
    result: dict[str, dict[str, bool]] = {}
    for label, path in _sidecar_files(database_path).items():
        if not path.exists():
            result[label] = {"existe": False}
            continue
        blob = path.read_bytes()
        found = {name: (needle in blob) for name, needle in needles.items()}
        found["existe"] = True
        result[label] = found
    return result


def _any_canary(scan: dict[str, dict[str, bool]]) -> bool:
    return any(
        entry.get("frase", False) or entry.get("token_fts", False) for entry in scan.values()
    )


def _seed_canary_everywhere(database_path: Path, journal_mode: str) -> None:
    """Coloca el canario en canonico heredado, derivados 0.1 y modelo experimental."""
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(f"PRAGMA journal_mode={journal_mode}")
    xmodel.install_experimental_model(connection)
    scopes = xmodel.seed_scopes(connection)

    memory_id = int(
        connection.execute(
            "SELECT id FROM memories WHERE subject_key = 'asunto-canario'"
        ).fetchone()[0]
    )
    # Refuerza el canario con el token de una sola palabra, para que FTS5 lo
    # indexe como termino y aparezca en las tablas sombra.
    connection.execute(
        "UPDATE memory_revisions SET content = ? WHERE memory_id = ?",
        (f"memoria con canario {CANARY} y token {CANARY_TOKEN} incrustado", memory_id),
    )
    message_id = int(
        connection.execute("SELECT id FROM messages WHERE operation_id = 'op-canary'").fetchone()[0]
    )
    connection.execute(
        "UPDATE messages SET content = ? WHERE id = ?",
        (f"mensaje con canario {CANARY} y token {CANARY_TOKEN} incrustado", message_id),
    )
    cursor = connection.execute(
        "INSERT INTO events (event_type, actor, message_id, created_at) "
        "VALUES ('memory.canario', 'user', ?, ?)",
        (message_id, T1),
    )
    event_id = int(cursor.lastrowid or 0)

    assertion_id = xmodel.insert_assertion(
        connection,
        scope_id=scopes["global"],
        subject="canario",
        predicate="contiene",
        object_=f"{CANARY} {CANARY_TOKEN}",
        valid_from="2020-01-01T00:00:00",
        valid_to=None,
        recorded_at=T1,
        legacy_memory_id=memory_id,
    )
    xmodel.add_provenance(
        connection,
        assertion_id,
        source_kind="evento",
        detail=f"procedencia con {CANARY_TOKEN}",
        recorded_at=T1,
        source_event_id=event_id,
    )
    xmodel.set_state(connection, assertion_id, "existencia", "presente", T1)
    connection.commit()
    xmodel.rebuild_derived(connection)
    connection.close()


def _hard_delete(
    database_path: Path, *, journal_mode: str, optimize_fts: bool
) -> dict[str, object]:
    """Ejecuta el borrado duro por etapas y devuelve la traza de cada una."""
    trace: dict[str, object] = {}
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute(f"PRAGMA journal_mode={journal_mode}")

    memory_id = int(
        connection.execute(
            "SELECT id FROM memories WHERE subject_key = 'asunto-canario'"
        ).fetchone()[0]
    )
    message_id = int(
        connection.execute("SELECT id FROM messages WHERE operation_id = 'op-canary'").fetchone()[0]
    )

    # Etapa 1 — borrado logico, tal y como lo hace hoy Sirius 0.1.
    connection.execute("UPDATE memories SET status = 'deleted' WHERE id = ?", (memory_id,))
    connection.commit()
    etapa_1 = scan_for_canaries(database_path)
    trace["etapa_1_filas_canonicas_con_el_token"] = _sql_visible(connection)
    trace["etapa_1_coincidencias_en_derivados"] = _derived_matches(connection)
    trace["etapa_1_logico_canario_sigue_en_disco"] = _any_canary(etapa_1)
    trace["etapa_1_detalle"] = etapa_1

    # Etapa 2 — borrado del contenido canonico (heredado y experimental).
    connection.execute("DELETE FROM x_provenance")
    connection.execute("DELETE FROM x_state")
    connection.execute("DELETE FROM x_stance")
    connection.execute("DELETE FROM x_assertion")
    connection.execute("DELETE FROM memory_revisions WHERE memory_id = ?", (memory_id,))
    connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    connection.execute("DELETE FROM events WHERE event_type = 'memory.canario'")
    connection.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    connection.commit()
    etapa_2 = scan_for_canaries(database_path)
    trace["etapa_2_sin_filas_canonicas"] = _sql_visible(connection) == 0
    trace["etapa_2_coincidencias_en_derivados"] = _derived_matches(connection)
    trace["etapa_2_coincidencias_en_fts_heredado"] = _fts_matches(connection)
    trace["etapa_2_canario_sigue_en_disco"] = _any_canary(etapa_2)
    trace["etapa_2_detalle"] = etapa_2

    # Etapa 3 — eliminacion de derivados, incluidas las sombras de FTS5.
    xmodel.drop_derived(connection)
    if optimize_fts:
        # FTS5 marca como borrado pero conserva los terminos en los segmentos
        # hasta que se compactan. 'rebuild' los reconstruye desde el contenido
        # actual; sin esto los tokens siguen literalmente en las sombras.
        connection.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')")
        connection.execute("INSERT INTO message_fts(message_fts) VALUES('rebuild')")
        connection.commit()
    etapa_3 = scan_for_canaries(database_path)
    trace["etapa_3_fts_sin_coincidencias"] = _fts_matches(connection) == 0
    trace["etapa_3_canario_sigue_en_disco"] = _any_canary(etapa_3)
    trace["etapa_3_detalle"] = etapa_3

    # Etapa 4 — purga fisica: checkpoint del WAL y VACUUM.
    if journal_mode.lower() == "wal":
        trace["etapa_4_wal_antes_del_checkpoint"] = etapa_3.get("wal", {})
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.commit()
        tras_checkpoint = scan_for_canaries(database_path)
        trace["etapa_4_canario_tras_checkpoint"] = _any_canary(tras_checkpoint)
        trace["etapa_4_detalle_tras_checkpoint"] = tras_checkpoint
    connection.execute("VACUUM")
    connection.commit()
    connection.close()
    trace["etapa_4_canario_tras_vacuum"] = _any_canary(scan_for_canaries(database_path))
    trace["etapa_4_detalle_por_fichero"] = scan_for_canaries(database_path)
    return trace


def _sql_visible(connection: sqlite3.Connection) -> int:
    total = 0
    for table, column in (
        ("memory_revisions", "content"),
        ("messages", "content"),
    ):
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {column} LIKE ?", (f"%{CANARY_TOKEN}%",)
        ).fetchone()
        total += int(row[0])
    return total


def _derived_matches(connection: sqlite3.Connection) -> int:
    """Cuantas veces sigue el token en los derivados experimentales."""
    total = 0
    for statement, params in (
        ("SELECT COUNT(*) FROM x_current_cache WHERE body LIKE ?", (f"%{CANARY_TOKEN}%",)),
        ("SELECT COUNT(*) FROM x_assertion_fts WHERE x_assertion_fts MATCH ?", (CANARY_TOKEN,)),
    ):
        try:
            total += int(connection.execute(statement, params).fetchone()[0])
        except sqlite3.OperationalError:
            continue
    return total


def _fts_matches(connection: sqlite3.Connection) -> int:
    total = 0
    for table in ("knowledge_fts", "message_fts"):
        try:
            row = connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {table} MATCH ?", (CANARY_TOKEN,)
            ).fetchone()
            total += int(row[0])
        except sqlite3.OperationalError:
            continue
    return total


def spike_10() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=10,
        nombre="Borrado duro con FTS5 y todos los derivados",
        objetivo=(
            "Determinar si el contenido puede eliminarse de verdad de todas las capas: canonico, "
            "revisiones, procedencias, relaciones, eventos, FTS5, sombras, caches y fichero."
        ),
        incertidumbre=(
            "En 0.1 la unica propagacion transaccional a un derivado es knowledge_fts (D-09). Se "
            "ignora si FTS5 conserva los terminos borrados en sus segmentos y si VACUUM basta."
        ),
        dataset="Base 0.1 sintetica con un canario en mensaje, memoria, evento, afirmacion y "
        "procedencia, mas derivados poblados.",
        preparacion="Sembrar el canario en todas las capas y comprobar que es localizable (control "
        "positivo).",
        operacion="Borrado por etapas: logico, canonico, derivados, purga fisica. Escaneo binario "
        "de db/wal/shm/journal en cada etapa.",
        resultado_esperado="Tras la purga completa, ningun fichero contiene el canario.",
        criterio_de_fallo=(
            "Que el canario siga en algun fichero despues de aplicar el procedimiento completo y "
            "documentado de SQLite."
        ),
    )

    database_path, _ids = fresh_populated_db("adr001_del_")
    _seed_canary_everywhere(database_path, journal_mode="delete")
    control = scan_for_canaries(database_path)
    control_ok = _any_canary(control)

    # Primera pasada SIN 'rebuild' de FTS5: mide si los segmentos retienen.
    sin_rebuild = _hard_delete(database_path, journal_mode="delete", optimize_fts=False)

    # Segunda pasada, base limpia, CON 'rebuild': procedimiento completo.
    database_path2, _ids2 = fresh_populated_db("adr001_del2_")
    _seed_canary_everywhere(database_path2, journal_mode="delete")
    con_rebuild = _hard_delete(database_path2, journal_mode="delete", optimize_fts=True)

    evidence.evidencia = {
        "control_positivo_canario_localizable_antes": control_ok,
        "control_positivo_detalle": control,
        "pasada_sin_rebuild_de_fts5": sin_rebuild,
        "pasada_con_rebuild_de_fts5": con_rebuild,
        "fts5_retiene_terminos_sin_rebuild": bool(sin_rebuild.get("etapa_4_canario_tras_vacuum")),
        "procedimiento_completo_deja_el_fichero_limpio": not bool(
            con_rebuild.get("etapa_4_canario_tras_vacuum")
        ),
        "el_borrado_logico_no_purga": bool(
            sin_rebuild.get("etapa_1_logico_canario_sigue_en_disco")
        ),
        "tras_borrar_lo_canonico_el_dato_sobrevive_en_derivados": int(
            sin_rebuild.get("etapa_2_coincidencias_en_derivados") or 0
        )
        > 0,
        "secuencia_verificada": [
            "DELETE de las filas canonicas (heredadas y experimentales)",
            "DROP de los derivados propios (arrastra sus tablas sombra FTS5)",
            "rebuild de los FTS5 heredados (defensivo, ver nota)",
            "checkpoint del WAL cuando aplique",
            "VACUUM",
        ],
        "nota_secure_delete": (
            "En este entorno secure_delete vale 1 (valor por defecto de compilacion de esta "
            "biblioteca SQLite 3.45.1). Con ese ajuste, el 'rebuild' de FTS5 no fue NECESARIO: "
            "ambas pasadas terminaron limpias. secure_delete es un valor por defecto de "
            "compilacion y puede diferir en el SQLite que embarque el ejecutable de Windows, por "
            "lo que la secuencia se documenta con el rebuild incluido como paso defensivo."
        ),
    }
    limpio = not bool(con_rebuild.get("etapa_4_canario_tras_vacuum"))
    evidence.resultado = PASS if (control_ok and limpio) else FAIL_ENGINE_SQLITE
    evidence.conclusion = (
        "El borrado duro es alcanzable con medios propios y documentados de SQLite: no hay "
        "limitacion de motor y no se abre C. Dos hallazgos operativos: (a) el borrado logico que "
        "hoy hace 0.1 no purga nada del fichero; (b) tras eliminar el contenido canonico, el dato "
        "SIGUE VIVO en los derivados hasta que estos se destruyen explicitamente, que es "
        "exactamente el riesgo D-09."
        if limpio
        else "SQLite retiene el contenido borrado pese al procedimiento completo: limitacion de "
        "motor confirmada."
    )
    return evidence


def spike_19() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=19,
        nombre="No reconstruibilidad",
        objetivo=(
            "Comprobar que, tras el borrado duro, el contenido no puede reconstruirse desde "
            "ningun resto: derivados, sombras, eventos, paginas libres, WAL, SHM o copias."
        ),
        incertidumbre=(
            "Una consulta SQL vacia no prueba nada. Se ignora si quedan fragmentos recuperables "
            "en paginas libres, en el WAL o en una copia hecha con VACUUM INTO."
        ),
        dataset="El mismo canario del spike 10, en modo WAL para ejercitar -wal y -shm, y con "
        "secure_delete desactivado como contraste.",
        preparacion="Sembrar el canario, verificar control positivo en cada fichero.",
        operacion=(
            "Borrado duro completo en WAL con checkpoint, VACUUM y VACUUM INTO; intento explicito "
            "de reconstruccion desde cada vector; contraste con secure_delete=0 sin VACUUM."
        ),
        resultado_esperado=(
            "Ningun vector reconstruye el contenido y ningun fichero conserva fragmentos tras el "
            "procedimiento completo."
        ),
        criterio_de_fallo="Cualquier fragmento recuperable tras el procedimiento completo.",
    )

    # Escenario A — WAL, procedimiento completo.
    path_wal, _ = fresh_populated_db("adr001_nr_wal_")
    _seed_canary_everywhere(path_wal, journal_mode="wal")
    control_wal = scan_for_canaries(path_wal)
    traza_wal = _hard_delete(path_wal, journal_mode="wal", optimize_fts=True)

    # Reconstruccion desde cada vector superviviente.
    connection = sqlite3.connect(str(path_wal))
    reconstruccion: dict[str, object] = {}
    reconstruccion["filas_canonicas_con_el_token"] = _sql_visible(connection)
    reconstruccion["coincidencias_fts"] = _fts_matches(connection)
    reconstruccion["eventos_residuales"] = int(
        connection.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'memory.canario'"
        ).fetchone()[0]
    )
    reconstruccion["derivados_experimentales_presentes"] = int(
        connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name LIKE 'x\\_assertion\\_fts%' ESCAPE '\\'"
        ).fetchone()[0]
    )
    sombras = [
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name LIKE '%\\_fts\\_%' ESCAPE '\\' ORDER BY name"
        ).fetchall()
    ]
    reconstruccion["tablas_sombra_fts5_restantes"] = sombras
    sombra_con_token = 0
    for tabla in sombras:
        try:
            rows = connection.execute(f"SELECT * FROM {tabla}").fetchall()
        except sqlite3.OperationalError:
            continue
        if any(
            CANARY_TOKEN.encode("utf-8") in bytes(v)
            for r in rows
            for v in r
            if isinstance(v, bytes)
        ):
            sombra_con_token += 1
    reconstruccion["sombras_que_aun_contienen_el_token"] = sombra_con_token

    # VACUUM INTO: una copia limpia no debe reintroducir nada.
    copia = path_wal.with_name("copia_vacuum_into.db")
    connection.execute("VACUUM INTO ?", (str(copia),))
    connection.close()
    copia_scan = scan_for_canaries(copia)
    reconstruccion["copia_vacuum_into_contiene_el_canario"] = _any_canary(copia_scan)

    # Escenario B — contraste: secure_delete desactivado y SIN VACUUM.
    path_insecure, _ = fresh_populated_db("adr001_nr_ins_")
    _seed_canary_everywhere(path_insecure, journal_mode="delete")
    c2 = sqlite3.connect(str(path_insecure))
    c2.execute("PRAGMA secure_delete=0")
    memory_id = int(
        c2.execute("SELECT id FROM memories WHERE subject_key = 'asunto-canario'").fetchone()[0]
    )
    c2.execute("DELETE FROM memory_revisions WHERE memory_id = ?", (memory_id,))
    c2.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    c2.commit()
    c2.close()
    contraste = scan_for_canaries(path_insecure)

    tras_procedimiento = bool(traza_wal.get("etapa_4_canario_tras_vacuum"))
    limpio = (
        not tras_procedimiento
        and reconstruccion["filas_canonicas_con_el_token"] == 0
        and reconstruccion["coincidencias_fts"] == 0
        and reconstruccion["sombras_que_aun_contienen_el_token"] == 0
        and not reconstruccion["copia_vacuum_into_contiene_el_canario"]
    )

    evidence.evidencia = {
        "modelo_de_amenaza": (
            "lectura de .db/-wal/-shm/-journal y de copias generadas por la aplicacion; excluye "
            "recuperacion forense del medio fisico"
        ),
        "control_positivo_wal": control_wal,
        "traza_borrado_wal": traza_wal,
        "intentos_de_reconstruccion": reconstruccion,
        "contraste_secure_delete_0_sin_vacuum": contraste,
        "contraste_demuestra_que_el_borrado_logico_no_purga": _any_canary(contraste),
        "pragmas_reales_de_sirius_0_1": {
            "journal_mode": "delete",
            "secure_delete": 1,
            "auto_vacuum": 0,
            "foreign_keys": 1,
            "synchronous": "FULL",
        },
    }
    evidence.resultado = PASS if limpio else FAIL_ENGINE_SQLITE
    evidence.conclusion = (
        "Dentro del modelo de amenaza declarado, el contenido no es reconstruible tras el "
        "procedimiento completo: ni por SQL, ni por FTS5, ni por sombras, ni por WAL/SHM, ni por "
        "una copia hecha con VACUUM INTO. No hay limitacion de motor: no se abre C."
        if limpio
        else "Queda contenido reconstruible tras el procedimiento completo: limitacion de motor."
    )
    return evidence


ALL_DELETION_SPIKES = (spike_10, spike_19)
