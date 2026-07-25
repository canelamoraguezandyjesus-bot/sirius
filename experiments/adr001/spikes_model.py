"""Spikes 1-8, 17 y 18: capacidades del modelo físico.

Cada spike responde a una única pregunta: ¿puede la alternativa A (conservar
el esquema heredado y añadir) sostener esta capacidad sin rediseñar ninguna
tabla de Sirius 0.1? Si la respuesta exigiese tocar una tabla heredada, el
spike terminaría en FAIL_STRUCTURAL_MODEL.
"""

from __future__ import annotations

import sqlite3

from experiments.adr001 import xmodel
from experiments.adr001.evidence import (
    FAIL_STRUCTURAL_MODEL,
    PASS,
    SpikeEvidence,
)
from experiments.adr001.fingerprint import LEGACY_TABLES, legacy_fingerprint, legacy_schema_dump
from experiments.adr001.synthetic import fresh_populated_db

T0 = "2026-01-01T00:00:00"
T1 = "2026-02-01T00:00:00"
T2 = "2026-03-01T00:00:00"
T3 = "2026-04-01T00:00:00"


def _prepared() -> tuple[sqlite3.Connection, dict[str, int], str]:
    """Base sintética 0.1 + modelo experimental instalado + ámbitos."""
    database_path, _ids = fresh_populated_db("adr001_model_")
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys=ON")
    before = legacy_fingerprint(connection)
    xmodel.install_experimental_model(connection)
    scopes = xmodel.seed_scopes(connection)
    return connection, scopes, before


def spike_01() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=1,
        nombre="Afirmacion atomica con varias procedencias",
        objetivo=(
            "Comprobar si una unidad atomica de conocimiento puede sostener N procedencias "
            "distintas y trazables al mismo tiempo."
        ),
        incertidumbre=(
            "El modelo heredado guarda la procedencia en un unico TEXT libre (origin) mas un "
            "unico FK opcional (source_event_id): capacidad 1. Se ignora si N procedencias se "
            "pueden anadir sin rediseñar memory_revisions."
        ),
        dataset="1 afirmacion atomica sujeto/predicado/objeto y 3 procedencias heterogeneas.",
        preparacion="Base 0.1 sintetica + tablas x_ + ambitos.",
        operacion="Insertar la afirmacion y 3 filas en x_provenance (evento, mensaje, manual).",
        resultado_esperado="Las 3 procedencias coexisten y se recuperan juntas; 0.1 intacto.",
        criterio_de_fallo=(
            "Que solo pueda registrarse una procedencia, o que haga falta alterar una tabla "
            "heredada para registrar mas de una."
        ),
    )
    connection, scopes, before = _prepared()
    try:
        scope_id = scopes["global"]
        assertion_id = xmodel.insert_assertion(
            connection,
            scope_id=scope_id,
            subject="usuario",
            predicate="prefiere",
            object_="cafe solo",
            valid_from="2020-01-01T00:00:00",
            valid_to=None,
            recorded_at=T1,
        )
        event_id = int(connection.execute("SELECT id FROM events ORDER BY id").fetchone()[0])
        message_id = int(connection.execute("SELECT id FROM messages ORDER BY id").fetchone()[0])
        xmodel.add_provenance(
            connection,
            assertion_id,
            source_kind="evento",
            detail="derivada de un evento",
            recorded_at=T1,
            source_event_id=event_id,
        )
        xmodel.add_provenance(
            connection,
            assertion_id,
            source_kind="mensaje",
            detail="dicha por el usuario en un mensaje",
            recorded_at=T1,
            source_message_id=message_id,
        )
        xmodel.add_provenance(
            connection,
            assertion_id,
            source_kind="manual",
            detail="confirmada a mano por el usuario",
            recorded_at=T2,
        )
        connection.commit()

        provenances = connection.execute(
            "SELECT source_kind, detail FROM x_provenance WHERE assertion_id = ? ORDER BY id",
            (assertion_id,),
        ).fetchall()

        legacy_capacity = connection.execute(
            "SELECT COUNT(*) FROM pragma_table_info('memory_revisions') "
            "WHERE name IN ('origin', 'source_event_id')"
        ).fetchone()[0]

        after = legacy_fingerprint(connection)
        evidence.evidencia = {
            "procedencias_registradas": len(provenances),
            "detalle": [f"{kind}: {detail}" for kind, detail in provenances],
            "columnas_de_procedencia_en_el_modelo_heredado": int(legacy_capacity),
            "procedencias_simultaneas_que_admite_el_modelo_heredado": 1,
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
        }
        ok = len(provenances) == 3 and before == after
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "A soporta procedencia multiple por pura adicion: x_provenance es una tabla nueva "
            "y memory_revisions no se toca."
            if ok
            else "No se pudo obtener procedencia multiple sin rediseñar el modelo heredado."
        )
        return evidence
    finally:
        connection.close()


def spike_02() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=2,
        nombre="Apoyo y refutacion multiples",
        objetivo="Comprobar si una afirmacion admite varios apoyos y varias refutaciones a la vez.",
        incertidumbre=(
            "El modelo heredado no tiene tabla de relaciones; la unica relacion real es "
            "decisions.supersedes_decision_id, que es 1:1 y solo entre decisiones."
        ),
        dataset="1 afirmacion central, 2 afirmaciones que la apoyan y 2 que la refutan.",
        preparacion="Base 0.1 sintetica + tablas x_ + ambitos.",
        operacion="Insertar 5 afirmaciones y 4 aristas tipadas en x_stance.",
        resultado_esperado="Apoyos y refutaciones coexisten, se cuentan y se consultan por tipo.",
        criterio_de_fallo="Que el modelo solo admita una relacion, o ninguna, sin rediseño.",
    )
    connection, scopes, before = _prepared()
    try:
        scope_id = scopes["global"]

        def add(subject: str, obj: str) -> int:
            return xmodel.insert_assertion(
                connection,
                scope_id=scope_id,
                subject=subject,
                predicate="afirma",
                object_=obj,
                valid_from="2020-01-01T00:00:00",
                valid_to=None,
                recorded_at=T1,
            )

        central = add("central", "la reunion fue el martes")
        supports = [add("apoyo1", "hay un correo del martes"), add("apoyo2", "el acta dice martes")]
        refutes = [
            add("refuta1", "el calendario dice jueves"),
            add("refuta2", "un testigo dice jueves"),
        ]

        for other in supports:
            connection.execute(
                "INSERT INTO x_stance (subject_assertion_id, object_assertion_id, stance, "
                "strength) VALUES (?, ?, 'apoya', 0.8)",
                (other, central),
            )
        for other in refutes:
            connection.execute(
                "INSERT INTO x_stance (subject_assertion_id, object_assertion_id, stance, "
                "strength) VALUES (?, ?, 'refuta', 0.6)",
                (other, central),
            )
        connection.commit()

        counts = dict(
            connection.execute(
                "SELECT stance, COUNT(*) FROM x_stance WHERE object_assertion_id = ? "
                "GROUP BY stance ORDER BY stance",
                (central,),
            ).fetchall()
        )
        after = legacy_fingerprint(connection)
        evidence.evidencia = {
            "apoyos": int(counts.get("apoya", 0)),
            "refutaciones": int(counts.get("refuta", 0)),
            "coexisten_ambas_posturas": bool(counts.get("apoya") and counts.get("refuta")),
            "relaciones_tipadas_en_el_modelo_heredado": 0,
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
        }
        ok = counts.get("apoya") == 2 and counts.get("refuta") == 2 and before == after
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "A soporta apoyo y refutacion multiples por adicion: x_stance es nueva y no sustituye "
            "ninguna relacion heredada."
            if ok
            else "El modelo heredado no admite relaciones multiples tipadas sin rediseño."
        )
        return evidence
    finally:
        connection.close()


def spike_03() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=3,
        nombre="Tiempo valido separado del tiempo de registro",
        objetivo="Comprobar si los dos ejes temporales pueden variar de forma independiente.",
        incertidumbre=(
            "Ninguna tabla heredada tiene columna de validez: solo created_at/updated_at, que "
            "son tiempo de registro (D-02)."
        ),
        dataset="2 afirmaciones con el mismo tiempo valido y distinto tiempo de registro, y "
        "1 con el mismo registro y distinta validez.",
        preparacion="Base 0.1 sintetica + tablas x_ + ambitos.",
        operacion="Insertar afirmaciones variando un eje mientras el otro queda fijo.",
        resultado_esperado="Los dos ejes son ortogonales y se almacenan por separado.",
        criterio_de_fallo="Que un eje quede determinado por el otro o no pueda representarse.",
    )
    connection, scopes, before = _prepared()
    try:
        scope_id = scopes["global"]
        misma_validez_a = xmodel.insert_assertion(
            connection,
            scope_id=scope_id,
            subject="hecho",
            predicate="ocurrio",
            object_="en 2020",
            valid_from="2020-01-01T00:00:00",
            valid_to="2021-01-01T00:00:00",
            recorded_at=T1,
        )
        misma_validez_b = xmodel.insert_assertion(
            connection,
            scope_id=scope_id,
            subject="hecho",
            predicate="ocurrio",
            object_="en 2020 (registrado mas tarde)",
            valid_from="2020-01-01T00:00:00",
            valid_to="2021-01-01T00:00:00",
            recorded_at=T3,
        )
        mismo_registro = xmodel.insert_assertion(
            connection,
            scope_id=scope_id,
            subject="hecho",
            predicate="ocurrio",
            object_="en 2024",
            valid_from="2024-01-01T00:00:00",
            valid_to=None,
            recorded_at=T1,
        )
        connection.commit()

        rows = {
            int(row[0]): (row[1], row[2], row[3])
            for row in connection.execute(
                "SELECT id, valid_from, valid_to, recorded_at FROM x_assertion ORDER BY id"
            ).fetchall()
        }
        eje_valido_igual = rows[misma_validez_a][0] == rows[misma_validez_b][0]
        eje_registro_distinto = rows[misma_validez_a][2] != rows[misma_validez_b][2]
        eje_registro_igual = rows[misma_validez_a][2] == rows[mismo_registro][2]
        eje_valido_distinto = rows[misma_validez_a][0] != rows[mismo_registro][0]

        legacy_validity_columns = connection.execute(
            "SELECT COUNT(*) FROM pragma_table_info('memory_revisions') "
            "WHERE name IN ('valid_from', 'valid_to')"
        ).fetchone()[0]

        after = legacy_fingerprint(connection)
        evidence.evidencia = {
            "misma_validez_distinto_registro": eje_valido_igual and eje_registro_distinto,
            "mismo_registro_distinta_validez": eje_registro_igual and eje_valido_distinto,
            "columnas_de_validez_en_el_modelo_heredado": int(legacy_validity_columns),
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
        }
        ok = (
            eje_valido_igual
            and eje_registro_distinto
            and eje_registro_igual
            and eje_valido_distinto
            and before == after
        )
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "A soporta bitemporalidad por adicion: los dos ejes viven en x_assertion sin tocar "
            "created_at/updated_at heredados."
            if ok
            else "No se pudieron separar los dos ejes temporales sin rediseño."
        )
        return evidence
    finally:
        connection.close()


def spike_04() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=4,
        nombre="Correccion retroactiva sin destruir el estado anterior",
        objetivo="Corregir el pasado dejando intacto lo que se creia antes.",
        incertidumbre=(
            "En 0.1 la correccion crea una revision nueva y marca la anterior is_current = 0, "
            "pero no existe eje de registro para preguntar que se creia en un instante dado."
        ),
        dataset="1 afirmacion registrada en T1 y corregida retroactivamente en T2.",
        preparacion="Base 0.1 sintetica + tablas x_ + ambitos.",
        operacion="Cerrar el registro anterior (recorded_until) e insertar la version corregida.",
        resultado_esperado="La version anterior sigue siendo recuperable con su valor original.",
        criterio_de_fallo=(
            "Que corregir destruya, sobrescriba o haga irrecuperable el valor previo."
        ),
    )
    connection, scopes, before = _prepared()
    try:
        scope_id = scopes["global"]
        original = xmodel.insert_assertion(
            connection,
            scope_id=scope_id,
            subject="coche",
            predicate="es de color",
            object_="azul",
            valid_from="2020-01-01T00:00:00",
            valid_to=None,
            recorded_at=T1,
        )
        connection.commit()
        original_value = connection.execute(
            "SELECT object FROM x_assertion WHERE id = ?", (original,)
        ).fetchone()[0]

        connection.execute("UPDATE x_assertion SET recorded_until = ? WHERE id = ?", (T2, original))
        corrected = xmodel.insert_assertion(
            connection,
            scope_id=scope_id,
            subject="coche",
            predicate="es de color",
            object_="verde",
            valid_from="2020-01-01T00:00:00",
            valid_to=None,
            recorded_at=T2,
            corrects_assertion_id=original,
        )
        connection.commit()

        preserved = connection.execute(
            "SELECT object, valid_from, recorded_at, recorded_until FROM x_assertion WHERE id = ?",
            (original,),
        ).fetchone()
        current = connection.execute(
            "SELECT object FROM x_assertion WHERE recorded_until IS NULL AND subject = 'coche'"
        ).fetchall()

        after = legacy_fingerprint(connection)
        evidence.evidencia = {
            "valor_original_antes_de_corregir": original_value,
            "valor_original_tras_corregir": preserved[0],
            "estado_anterior_preservado": preserved[0] == original_value == "azul",
            "registro_anterior_cerrado_en": preserved[3],
            "valor_vigente_ahora": [row[0] for row in current],
            "correccion_enlazada_al_original": bool(
                connection.execute(
                    "SELECT corrects_assertion_id FROM x_assertion WHERE id = ?", (corrected,)
                ).fetchone()[0]
                == original
            ),
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
        }
        ok = (
            preserved[0] == "azul"
            and preserved[3] == T2
            and [row[0] for row in current] == ["verde"]
            and before == after
        )
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "A soporta correccion retroactiva no destructiva por adicion."
            if ok
            else "La correccion retroactiva destruye o pierde el estado anterior."
        )
        return evidence
    finally:
        connection.close()


def _bitemporal_fixture(connection: sqlite3.Connection, scope_id: int) -> dict[str, int]:
    """Escenario compartido por los spikes 5 y 6."""
    vigente_2020 = xmodel.insert_assertion(
        connection,
        scope_id=scope_id,
        subject="tarifa",
        predicate="vale",
        object_="10 euros",
        valid_from="2020-01-01T00:00:00",
        valid_to="2022-01-01T00:00:00",
        recorded_at=T1,
    )
    vigente_2022 = xmodel.insert_assertion(
        connection,
        scope_id=scope_id,
        subject="tarifa",
        predicate="vale",
        object_="15 euros",
        valid_from="2022-01-01T00:00:00",
        valid_to=None,
        recorded_at=T1,
    )
    connection.execute("UPDATE x_assertion SET recorded_until = ? WHERE id = ?", (T2, vigente_2022))
    corregida = xmodel.insert_assertion(
        connection,
        scope_id=scope_id,
        subject="tarifa",
        predicate="vale",
        object_="18 euros",
        valid_from="2022-01-01T00:00:00",
        valid_to=None,
        recorded_at=T2,
        corrects_assertion_id=vigente_2022,
    )
    connection.commit()
    return {"vigente_2020": vigente_2020, "vigente_2022": vigente_2022, "corregida": corregida}


def spike_05() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=5,
        nombre="Consulta valida en T",
        objetivo="Responder que era cierto en el mundo en un instante T.",
        incertidumbre=(
            "Sin eje de validez, 0.1 no puede distinguir «cierto en T» de «registrado en T»."
        ),
        dataset="Tarifa con dos periodos de validez y una correccion posterior.",
        preparacion="Base 0.1 sintetica + tablas x_ + ambitos + escenario bitemporal.",
        operacion="Consultar valid_at en dos instantes distintos del eje de tiempo valido.",
        resultado_esperado="Cada instante devuelve exactamente la afirmacion valida entonces.",
        criterio_de_fallo=(
            "Que la consulta devuelva las dos, ninguna, o dependa del eje de registro."
        ),
    )
    connection, scopes, before = _prepared()
    try:
        ids = _bitemporal_fixture(connection, scopes["global"])
        en_2021 = xmodel.valid_at(connection, "2021-06-01T00:00:00")
        en_2023 = xmodel.valid_at(connection, "2023-06-01T00:00:00")
        after = legacy_fingerprint(connection)
        evidence.evidencia = {
            "valida_en_2021": en_2021,
            "esperado_2021": [ids["vigente_2020"]],
            "valida_en_2023": en_2023,
            "esperado_2023": [ids["corregida"]],
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
        }
        ok = en_2021 == [ids["vigente_2020"]] and en_2023 == [ids["corregida"]] and before == after
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "A soporta la consulta «valida en T» por adicion."
            if ok
            else "La consulta «valida en T» no es representable sin rediseño."
        )
        return evidence
    finally:
        connection.close()


def spike_06() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=6,
        nombre="Consulta conocida en T",
        objetivo="Responder que creia el sistema en un instante T, aunque hoy sepa otra cosa.",
        incertidumbre=(
            "Sin eje de registro cerrado (recorded_until), no se puede reconstruir la creencia "
            "pasada: 0.1 solo conserva is_current, que es un booleano del presente."
        ),
        dataset="El mismo escenario bitemporal del spike 5.",
        preparacion="Base 0.1 sintetica + tablas x_ + ambitos + escenario bitemporal.",
        operacion="Consultar known_at antes y despues de la correccion.",
        resultado_esperado="Antes de T2 el sistema creia 15 euros; despues, 18 euros.",
        criterio_de_fallo="Que ambas consultas devuelvan lo mismo o pierdan la creencia anterior.",
    )
    connection, scopes, before = _prepared()
    try:
        ids = _bitemporal_fixture(connection, scopes["global"])
        antes = xmodel.known_at(connection, "2026-02-15T00:00:00")
        despues = xmodel.known_at(connection, "2026-03-15T00:00:00")
        valor_antes = connection.execute(
            "SELECT object FROM x_assertion WHERE id = ?", (ids["vigente_2022"],)
        ).fetchone()[0]
        valor_despues = connection.execute(
            "SELECT object FROM x_assertion WHERE id = ?", (ids["corregida"],)
        ).fetchone()[0]
        after = legacy_fingerprint(connection)
        evidence.evidencia = {
            "conocidas_antes_de_la_correccion": antes,
            "conocidas_despues_de_la_correccion": despues,
            "creencia_anterior_recuperable": ids["vigente_2022"] in antes,
            "creencia_anterior_ya_no_vigente": ids["vigente_2022"] not in despues,
            "creencia_nueva_solo_despues": ids["corregida"] in despues
            and ids["corregida"] not in antes,
            "valor_creido_antes": valor_antes,
            "valor_creido_despues": valor_despues,
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
        }
        ok = (
            ids["vigente_2022"] in antes
            and ids["vigente_2022"] not in despues
            and ids["corregida"] in despues
            and ids["corregida"] not in antes
            and before == after
        )
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "A soporta la consulta «conocida en T» por adicion."
            if ok
            else "La creencia pasada no es reconstruible sin rediseño."
        )
        return evidence
    finally:
        connection.close()


def _read_state(connection: sqlite3.Connection, assertion_id: int) -> dict[str, str]:
    """Relee el estado desde SQLite. La evidencia sale de la base, nunca del
    diccionario que se uso para escribirla."""
    return {
        str(row[0]): str(row[1])
        for row in connection.execute(
            "SELECT dimension, value FROM x_state WHERE assertion_id = ? ORDER BY dimension",
            (assertion_id,),
        ).fetchall()
    }


def _assertion_with_state(
    connection: sqlite3.Connection,
    scope_id: int,
    etiqueta: str,
    estado: dict[str, str],
    recorded_at: str,
) -> int:
    assertion_id = xmodel.insert_assertion(
        connection,
        scope_id=scope_id,
        subject="dato",
        predicate="tiene estado",
        object_=etiqueta,
        valid_from="2020-01-01T00:00:00",
        valid_to=None,
        recorded_at=recorded_at,
    )
    for dimension, value in estado.items():
        xmodel.set_state(connection, assertion_id, dimension, value, recorded_at)
    connection.commit()
    return assertion_id


def _legacy_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in LEGACY_TABLES
    }


def _difieren_solo_en(a: dict[str, str], b: dict[str, str], dimension: str) -> bool:
    distintas = [d for d in xmodel.STATE_DIMENSIONS if a[d] != b[d]]
    return distintas == [dimension]


def spike_07() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=7,
        nombre="Siete dimensiones canonicas ortogonales de estado sin enum monolitico",
        objetivo=(
            "Comprobar si el estado puede descomponerse en las SIETE DIMENSIONES CANONICAS "
            "(confirmacion, validez, disponibilidad, sensibilidad, temporalidad, ambito y "
            "autoridad) de forma independiente, y si el enum monolitico heredado pierde "
            "informacion al proyectarlas."
        ),
        incertidumbre=(
            "memories.status es un unico VARCHAR(16) sin CHECK, con un dominio de 3 valores "
            "impuesto por la aplicacion, que colapsa varias dimensiones a la vez (D-03). Se "
            "ignora si las siete canonicas son representables por adicion y si ambito y "
            "autoridad quedan realmente fuera del alcance del enum."
        ),
        dataset=(
            "15 afirmaciones coexistentes: una de partida con las 7 dimensiones canonicas "
            "fijadas, mas 14 variantes que difieren de ella en una sola dimension. Ademas, 7 "
            "afirmaciones independientes para el barrido de mutacion, una por dimension."
        ),
        preparacion="Base 0.1 sintetica creada con la cadena canonica de Alembic + tablas x_ + "
        "ambitos. Se capturan huella, esquema heredado y recuentos heredados de partida.",
        operacion=(
            "1) Fijar las 7 dimensiones canonicas y releerlas desde SQLite. 2) Barrido: por cada "
            "dimension, mutarla en una afirmacion propia y comprobar que las otras seis quedan "
            "intactas. 3) Persistir 15 combinaciones distintas simultaneas y proyectarlas al enum "
            "heredado. 4) Medir que ambito y autoridad no se derivan de confirmacion, validez ni "
            "disponibilidad y que el enum es invariante ante ellas."
        ),
        resultado_esperado=(
            "Las 7 dimensiones canonicas se representan de forma independiente; mutar una deja "
            "intactas las otras seis; coexisten combinaciones que el enum monolitico no puede "
            "expresar; ambito y autoridad no se colapsan con confirmacion, validez ni "
            "disponibilidad; y las tablas heredadas quedan intactas."
        ),
        criterio_de_fallo=(
            "Que cambiar una dimension arrastre otra, que el enum heredado baste para "
            "reconstruir las siete, que ambito o autoridad resulten derivables de las tres "
            "dimensiones que el enum roza, o que haga falta tocar memories."
        ),
    )
    connection, scopes, before = _prepared()
    try:
        scope_id = scopes["global"]
        esquema_heredado_antes = legacy_schema_dump(connection)
        recuentos_heredados_antes = _legacy_counts(connection)
        ddl_memories = str(
            connection.execute("SELECT sql FROM sqlite_master WHERE name = 'memories'").fetchone()[
                0
            ]
        )

        inicial = dict(xmodel.CANONICAL_INITIAL_STATE)

        # --- A. Las siete dimensiones canonicas se representan por separado.
        base_id = _assertion_with_state(connection, scope_id, "base", inicial, T1)
        persistidas = _read_state(connection, base_id)
        siete_representadas = (
            len(persistidas) == 7
            and set(persistidas) == set(xmodel.STATE_DIMENSIONS)
            and persistidas == inicial
        )

        # --- B. Barrido: mutar UNA dimension deja intactas las otras SEIS.
        barrido: dict[str, dict[str, object]] = {}
        for dimension in xmodel.STATE_DIMENSIONS:
            nuevo = xmodel.CANONICAL_STATE_VALUES[dimension][1]
            assertion_id = _assertion_with_state(
                connection, scope_id, f"barrido:{dimension}", inicial, T1
            )
            antes_dim = _read_state(connection, assertion_id)
            xmodel.set_state(connection, assertion_id, dimension, nuevo, T2)
            connection.commit()
            despues_dim = _read_state(connection, assertion_id)
            otras_antes = {k: v for k, v in antes_dim.items() if k != dimension}
            otras_despues = {k: v for k, v in despues_dim.items() if k != dimension}
            barrido[dimension] = {
                "valor_anterior": antes_dim[dimension],
                "valor_nuevo": despues_dim[dimension],
                "cambio_aplicado": despues_dim[dimension] == nuevo != antes_dim[dimension],
                "otras_dimensiones_comprobadas": len(otras_despues),
                "las_otras_seis_intactas": otras_antes == otras_despues,
            }
        independencia_total = all(
            entry["cambio_aplicado"]
            and entry["las_otras_seis_intactas"]
            and entry["otras_dimensiones_comprobadas"] == 6
            for entry in barrido.values()
        )

        # --- C. Combinaciones coexistentes que el enum monolitico no expresa.
        combinaciones: dict[str, dict[str, str]] = {"base": dict(inicial)}
        for dimension in xmodel.STATE_DIMENSIONS:
            for valor in xmodel.CANONICAL_STATE_VALUES[dimension][1:]:
                estado = dict(inicial)
                estado[dimension] = valor
                combinaciones[f"{dimension}={valor}"] = estado
        ids = {
            etiqueta: _assertion_with_state(connection, scope_id, etiqueta, estado, T3)
            for etiqueta, estado in combinaciones.items()
        }
        leidas = {etiqueta: _read_state(connection, aid) for etiqueta, aid in ids.items()}
        tuplas = {tuple(estado[d] for d in xmodel.STATE_DIMENSIONS) for estado in leidas.values()}
        proyecciones = {
            etiqueta: xmodel.project_to_legacy_status(estado) for etiqueta, estado in leidas.items()
        }
        colisiones: dict[str, set[tuple[str, ...]]] = {}
        for etiqueta, valor in proyecciones.items():
            colisiones.setdefault(valor, set()).add(
                tuple(leidas[etiqueta][d] for d in xmodel.STATE_DIMENSIONS)
            )
        mayor_colision = max(len(t) for t in colisiones.values())
        enum_heredado_es_lossy = (
            len(tuplas) == len(combinaciones)
            and len(tuplas) > len(set(proyecciones.values()))
            and mayor_colision >= 2
        )
        # Ejemplo explicito: dos estados que difieren en una dimension que el
        # enum SI roza (confirmacion) y aun asi colapsan al mismo valor.
        colapso_en_confirmacion = (
            proyecciones["base"] == proyecciones["confirmación=provisional"]
            and leidas["base"] != leidas["confirmación=provisional"]
        )

        # --- D. Ambito y autoridad no se colapsan con confirmacion,
        #        validez ni disponibilidad.
        def _triple(estado: dict[str, str]) -> tuple[str, ...]:
            return tuple(estado[d] for d in xmodel.LEGACY_PROJECTION_INPUTS)

        triple_base = _triple(inicial)
        mismo_triple = [estado for estado in leidas.values() if _triple(estado) == triple_base]
        ambitos_con_el_mismo_triple = sorted({estado["ámbito"] for estado in mismo_triple})
        autoridades_con_el_mismo_triple = sorted({estado["autoridad"] for estado in mismo_triple})
        valores_heredados_del_grupo = sorted(
            {xmodel.project_to_legacy_status(estado) for estado in mismo_triple}
        )

        invariancia: dict[str, bool] = {}
        for dimension in ("ámbito", "autoridad"):
            pares = [
                (a, b)
                for a in leidas
                for b in leidas
                if a < b and _difieren_solo_en(leidas[a], leidas[b], dimension)
            ]
            invariancia[dimension] = bool(pares) and all(
                proyecciones[a] == proyecciones[b] for a, b in pares
            )

        ambito_y_autoridad_no_colapsan = (
            "ámbito" not in xmodel.LEGACY_PROJECTION_INPUTS
            and "autoridad" not in xmodel.LEGACY_PROJECTION_INPUTS
            and len(ambitos_con_el_mismo_triple) == 3
            and len(autoridades_con_el_mismo_triple) == 3
            and len(valores_heredados_del_grupo) == 1
            and invariancia["ámbito"]
            and invariancia["autoridad"]
            and bool(barrido["ámbito"]["las_otras_seis_intactas"])
            and bool(barrido["autoridad"]["las_otras_seis_intactas"])
        )

        # --- E. Sirius 0.1 intacto y tablas heredadas sin alterar.
        after = legacy_fingerprint(connection)
        esquema_heredado_despues = legacy_schema_dump(connection)
        recuentos_heredados_despues = _legacy_counts(connection)
        tablas_heredadas_intactas = (
            esquema_heredado_antes == esquema_heredado_despues
            and recuentos_heredados_antes == recuentos_heredados_despues
        )
        valores_distintos_en_datos_heredados = int(
            connection.execute("SELECT COUNT(DISTINCT status) FROM memories").fetchone()[0]
        )

        evidence.evidencia = {
            "dimensiones_canonicas": list(xmodel.STATE_DIMENSIONS),
            "son_exactamente_siete": len(xmodel.STATE_DIMENSIONS) == 7,
            "dimensiones_persistidas": len(persistidas),
            "estado_releido_desde_sqlite": persistidas,
            "siete_dimensiones_representadas_de_forma_independiente": siete_representadas,
            "barrido_una_dimension_a_la_vez": barrido,
            "mutar_una_deja_intactas_las_otras_seis": independencia_total,
            "combinaciones_coexistentes_persistidas": len(combinaciones),
            "combinaciones_distintas_releidas": len(tuplas),
            "valores_distintos_del_enum_heredado": sorted(set(proyecciones.values())),
            "mayor_grupo_de_combinaciones_que_colapsan_al_mismo_valor": mayor_colision,
            "colisiones_por_valor_heredado": {
                valor: len(tuplas_del_valor) for valor, tuplas_del_valor in colisiones.items()
            },
            "el_enum_monolitico_no_puede_expresarlas": enum_heredado_es_lossy,
            "colapso_incluso_en_una_dimension_que_el_enum_roza": colapso_en_confirmacion,
            "dimensiones_que_el_enum_heredado_alcanza": list(xmodel.LEGACY_PROJECTION_INPUTS),
            "ambitos_distintos_con_confirmacion_validez_disponibilidad_iguales": (
                ambitos_con_el_mismo_triple
            ),
            "autoridades_distintas_con_confirmacion_validez_disponibilidad_iguales": (
                autoridades_con_el_mismo_triple
            ),
            "valores_heredados_de_ese_grupo": valores_heredados_del_grupo,
            "enum_invariante_ante_ambito": invariancia["ámbito"],
            "enum_invariante_ante_autoridad": invariancia["autoridad"],
            "ambito_y_autoridad_no_se_colapsan": ambito_y_autoridad_no_colapsan,
            "ddl_memories_heredado": ddl_memories,
            "dominio_del_enum_heredado": list(xmodel.LEGACY_STATUS_VALUES),
            "valores_distintos_en_datos_heredados": valores_distintos_en_datos_heredados,
            "esquema_heredado_sin_cambios": (esquema_heredado_antes == esquema_heredado_despues),
            "recuentos_heredados_sin_cambios": (
                recuentos_heredados_antes == recuentos_heredados_despues
            ),
            "tablas_heredadas_no_alteradas": tablas_heredadas_intactas,
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
            "modelo_experimental": True,
            "ddl_productivo_fijado": False,
            "nombres_fisicos_productivos_fijados": False,
            "nota": (
                "Las SIETE DIMENSIONES son las canonicas fijadas para esta correccion. El "
                "vocabulario de valores de cada dimension y las tablas x_ siguen siendo "
                "EXPERIMENTALES: no fijan DDL definitivo ni nombres fisicos productivos."
            ),
        }
        ok = (
            siete_representadas
            and independencia_total
            and enum_heredado_es_lossy
            and colapso_en_confirmacion
            and ambito_y_autoridad_no_colapsan
            and tablas_heredadas_intactas
            and before == after
        )
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "A soporta las siete dimensiones canonicas por pura adicion: cada una se mueve sin "
            "arrastrar a las otras seis, coexisten combinaciones que el enum monolitico heredado "
            "no puede expresar, y ambito y autoridad quedan fuera de su alcance en lugar de "
            "colapsarse con confirmacion, validez o disponibilidad. El enum heredado se conserva "
            "intacto y queda como proyeccion lossy, no como fuente."
            if ok
            else (
                "Las siete dimensiones canonicas no son representables de forma independiente sin "
                "rediseñar el esquema heredado."
            )
        )
        return evidence
    finally:
        connection.close()


def spike_08() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=8,
        nombre="Ambito multi-proyecto cerrado",
        objetivo=(
            "Comprobar aislamiento estricto entre proyectos concurrentes con un ambito global."
        ),
        incertidumbre=(
            "El modelo heredado impone proyecto unico activo mediante el indice parcial "
            "uq_projects_single_active (D-04)."
        ),
        dataset="3 proyectos sinteticos, 1 ambito global y afirmaciones en cada ambito.",
        preparacion="Base 0.1 sintetica + tablas x_ + ambitos con visibilidad cerrada.",
        operacion="Consultar desde el ambito de cada proyecto y comprobar que no hay fuga.",
        resultado_esperado="Cada proyecto ve lo suyo y lo global, nunca lo de otro proyecto.",
        criterio_de_fallo="Cualquier fuga entre proyectos, o necesidad de tocar la tabla projects.",
    )
    connection, scopes, before = _prepared()
    try:
        project_ids = [
            int(row[0])
            for row in connection.execute("SELECT id FROM projects ORDER BY id").fetchall()
        ]
        marcas: dict[int, int] = {}
        for project_id in project_ids:
            scope_id = scopes[f"proyecto:{project_id}"]
            marcas[project_id] = xmodel.insert_assertion(
                connection,
                scope_id=scope_id,
                subject=f"proyecto{project_id}",
                predicate="contiene",
                object_=f"dato privado del proyecto {project_id}",
                valid_from="2020-01-01T00:00:00",
                valid_to=None,
                recorded_at=T1,
            )
        global_id = xmodel.insert_assertion(
            connection,
            scope_id=scopes["global"],
            subject="global",
            predicate="contiene",
            object_="dato compartido",
            valid_from="2020-01-01T00:00:00",
            valid_to=None,
            recorded_at=T1,
        )
        connection.commit()

        fugas: dict[str, list[int]] = {}
        aislamiento_ok = True
        for project_id in project_ids:
            scope_id = scopes[f"proyecto:{project_id}"]
            visibles = [
                int(row[0])
                for row in connection.execute(
                    "SELECT a.id FROM x_assertion a "
                    "JOIN x_scope_visibility v ON v.to_scope_id = a.scope_id "
                    "WHERE v.from_scope_id = ? ORDER BY a.id",
                    (scope_id,),
                ).fetchall()
            ]
            esperado = sorted([marcas[project_id], global_id])
            fugas[f"proyecto:{project_id}"] = visibles
            if visibles != esperado:
                aislamiento_ok = False

        # Evidencia de la restriccion heredada: dos proyectos activos a la vez
        # violan el indice parcial unico. No se modifica nada: se revierte.
        try:
            connection.execute("UPDATE projects SET is_active = 1 WHERE is_active = 0")
            connection.commit()
            segundo_activo_permitido = True
        except sqlite3.IntegrityError:
            segundo_activo_permitido = False
        finally:
            connection.rollback()

        after = legacy_fingerprint(connection)
        evidence.evidencia = {
            "visibilidad_por_proyecto": fugas,
            "afirmacion_global": global_id,
            "aislamiento_sin_fugas": aislamiento_ok,
            "el_modelo_heredado_permite_dos_proyectos_activos": segundo_activo_permitido,
            "restriccion_heredada": "uq_projects_single_active (indice parcial unico)",
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
        }
        ok = aislamiento_ok and not segundo_activo_permitido and before == after
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "A soporta multi-proyecto cerrado por adicion: el ambito vive en x_scope y la tabla "
            "projects heredada, con su restriccion de proyecto unico activo, no se toca."
            if ok
            else "El aislamiento multi-proyecto exige rediseñar el modelo heredado."
        )
        return evidence
    finally:
        connection.close()


def spike_17() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=17,
        nombre="Fallo inyectado durante una escritura critica",
        objetivo="Comprobar que un fallo a mitad de una escritura critica no deja estado parcial.",
        incertidumbre=(
            "La escritura critica toca varias tablas canonicas y ademas derivados; se ignora si "
            "el conjunto revierte de forma atomica."
        ),
        dataset="Una escritura de 4 partes: afirmacion, procedencia, estado y derivado.",
        preparacion="Base 0.1 sintetica + tablas x_ + ambitos + una escritura previa correcta.",
        operacion="Repetir la escritura inyectando una excepcion antes del commit y revertir.",
        resultado_esperado="Cero filas nuevas en todas las tablas implicadas, derivados incluidos.",
        criterio_de_fallo="Cualquier fila parcial superviviente tras el fallo.",
    )
    connection, scopes, before = _prepared()
    try:
        scope_id = scopes["global"]
        xmodel.insert_assertion(
            connection,
            scope_id=scope_id,
            subject="previa",
            predicate="es",
            object_="correcta",
            valid_from="2020-01-01T00:00:00",
            valid_to=None,
            recorded_at=T1,
        )
        connection.commit()
        xmodel.rebuild_derived(connection)

        conteo_antes = _counts(connection)

        class FalloInyectado(RuntimeError):
            pass

        excepcion_capturada = False
        try:
            assertion_id = xmodel.insert_assertion(
                connection,
                scope_id=scope_id,
                subject="critica",
                predicate="debe",
                object_="revertirse entera",
                valid_from="2020-01-01T00:00:00",
                valid_to=None,
                recorded_at=T2,
            )
            xmodel.add_provenance(
                connection, assertion_id, source_kind="manual", detail="parcial", recorded_at=T2
            )
            xmodel.set_state(connection, assertion_id, "existencia", "presente", T2)
            connection.execute(
                "INSERT INTO x_assertion_fts (rowid, body) VALUES (?, ?)",
                (assertion_id, "critica debe revertirse entera"),
            )
            connection.execute(
                "INSERT INTO x_current_cache (assertion_id, body, scope_id) VALUES (?, ?, ?)",
                (assertion_id, "critica debe revertirse entera", scope_id),
            )
            raise FalloInyectado("fallo inyectado antes del commit")
        except FalloInyectado:
            excepcion_capturada = True
            connection.rollback()

        conteo_despues = _counts(connection)
        after = legacy_fingerprint(connection)
        evidence.evidencia = {
            "excepcion_inyectada_y_capturada": excepcion_capturada,
            "conteos_antes": conteo_antes,
            "conteos_despues": conteo_despues,
            "sin_estado_parcial": conteo_antes == conteo_despues,
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
        }
        ok = excepcion_capturada and conteo_antes == conteo_despues and before == after
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "La escritura critica es atomica sobre canonico y derivado a la vez; A no se ve "
            "comprometida por este vector."
            if ok
            else "Un fallo a mitad de escritura deja estado parcial."
        )
        return evidence
    finally:
        connection.close()


def spike_18() -> SpikeEvidence:
    evidence = SpikeEvidence(
        numero=18,
        nombre="Ningun derivado actua como fuente canonica",
        objetivo=(
            "Comprobar que los derivados se pueden destruir y reconstruir sin perdida y que "
            "ninguna consulta canonica depende de ellos."
        ),
        incertidumbre=(
            "En 0.1 el unico derivado con propagacion transaccional es knowledge_fts (D-09); se "
            "ignora si un derivado nuevo podria convertirse de facto en canon."
        ),
        dataset="6 afirmaciones con sus derivados poblados.",
        preparacion="Base 0.1 sintetica + tablas x_ + ambitos + derivados reconstruidos.",
        operacion="Hash de derivados, DROP total, consulta canonica sin derivados, reconstruccion.",
        resultado_esperado="Consultas canonicas intactas sin derivados y reconstruccion identica.",
        criterio_de_fallo=(
            "Que una consulta canonica falle sin derivados o que el hash no coincida."
        ),
    )
    connection, scopes, before = _prepared()
    try:
        scope_id = scopes["global"]
        for index in range(6):
            xmodel.insert_assertion(
                connection,
                scope_id=scope_id,
                subject=f"sujeto{index}",
                predicate="es",
                object_=f"objeto numero {index}",
                valid_from="2020-01-01T00:00:00",
                valid_to=None,
                recorded_at=T1,
            )
        connection.commit()
        xmodel.rebuild_derived(connection)

        derivado_antes = _derived_dump(connection)
        canonico_antes = xmodel.valid_at(connection, "2021-01-01T00:00:00")

        xmodel.drop_derived(connection)
        derivados_presentes = [
            name
            for name in (
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE name LIKE 'x\\_assertion\\_fts%' "
                    "ESCAPE '\\' OR name = 'x_current_cache'"
                ).fetchall()
            )
        ]
        canonico_sin_derivados = xmodel.valid_at(connection, "2021-01-01T00:00:00")

        xmodel.install_derived(connection)
        xmodel.rebuild_derived(connection)
        derivado_despues = _derived_dump(connection)

        after = legacy_fingerprint(connection)
        evidence.evidencia = {
            "derivados_eliminados_por_completo": derivados_presentes == [],
            "consulta_canonica_con_derivados": canonico_antes,
            "consulta_canonica_sin_derivados": canonico_sin_derivados,
            "la_consulta_canonica_no_depende_del_derivado": canonico_antes
            == canonico_sin_derivados,
            "hash_derivado_antes": derivado_antes,
            "hash_derivado_reconstruido": derivado_despues,
            "reconstruccion_identica": derivado_antes == derivado_despues,
            "huella_0_1_antes": before,
            "huella_0_1_despues": after,
            "0_1_intacto": before == after,
        }
        ok = (
            derivados_presentes == []
            and canonico_antes == canonico_sin_derivados
            and derivado_antes == derivado_despues
            and before == after
        )
        evidence.resultado = PASS if ok else FAIL_STRUCTURAL_MODEL
        evidence.conclusion = (
            "Ningun derivado es canon: se destruyen y se reconstruyen identicos desde las tablas "
            "canonicas, y las consultas canonicas funcionan sin ellos."
            if ok
            else "Algun derivado actua de facto como fuente canonica."
        )
        return evidence
    finally:
        connection.close()


def _counts(connection: sqlite3.Connection) -> dict[str, int]:
    tables = (
        "x_assertion",
        "x_provenance",
        "x_state",
        "x_stance",
        "x_assertion_fts",
        "x_current_cache",
    )
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in tables
    }


def _derived_dump(connection: sqlite3.Connection) -> str:
    import hashlib

    fts = connection.execute("SELECT rowid, body FROM x_assertion_fts ORDER BY rowid").fetchall()
    cache = connection.execute(
        "SELECT assertion_id, body, scope_id FROM x_current_cache ORDER BY assertion_id"
    ).fetchall()
    payload = repr(fts) + "|" + repr(cache)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


ALL_MODEL_SPIKES = (
    spike_01,
    spike_02,
    spike_03,
    spike_04,
    spike_05,
    spike_06,
    spike_07,
    spike_08,
    spike_17,
    spike_18,
)
