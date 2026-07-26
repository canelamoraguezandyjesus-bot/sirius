"""Escenarios de medicion de la linea base FTS5 (§5.2 del paquete 02).

Todo se mide contra el codigo REAL de recuperacion de Sirius 0.1, que no
se modifica: ``SqliteKnowledgeSearchRepository`` y
``RankRelevantKnowledgeUseCase``, construidos con sus propias fabricas.

Ninguna medicion incluye el tiempo de construccion de fixtures: los
repositorios y el corpus se preparan antes de cronometrar.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.adr002.tolerances import corpus
from experiments.adr002.tolerances.harness import (
    REPS_BARATO,
    REPS_CARO,
    Distribucion,
    como_dict,
    cronometrar_una_vez,
    medir,
    percentil,
)

from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase

WARMUP = 5

# Objetos derivados que la linea base mantiene. Se enumeran aqui para
# poder medir su tamano y comprobar su desaparicion tras el borrado.
TABLAS_FTS = ("knowledge_fts", "message_fts")


@dataclass
class Banco:
    """Corpus construido y repositorios listos. Nada de esto entra en el
    cronometro de las latencias."""

    database_path: Path
    ids: corpus.CorpusIds
    caso_de_uso: RankRelevantKnowledgeUseCase
    busqueda: Any

    def cerrar(self) -> None:
        self.busqueda.close()


def preparar_banco(prefix: str = "adr002_tol_") -> Banco:
    database_path, ids = corpus.corpus_de_referencia(prefix)
    busqueda = build_sqlite_knowledge_search_repository(database_path)
    caso_de_uso = RankRelevantKnowledgeUseCase(
        memory_repository=build_sqlite_memory_repository(database_path),
        decision_repository=build_sqlite_decision_repository(database_path),
        project_repository=build_sqlite_project_repository(database_path),
        knowledge_search_repository=busqueda,
    )
    return Banco(database_path=database_path, ids=ids, caso_de_uso=caso_de_uso, busqueda=busqueda)


# --------------------------------------------------------------------------
# 1-4. Latencia por escenario de consulta.
# --------------------------------------------------------------------------


def medir_latencias(banco: Banco) -> dict[str, Any]:
    """Escenarios 1 a 4: 0 resultados, 1 resultado, muchos candidatos y el
    barrido completo que hace ``rank()``."""
    escenarios: dict[str, Any] = {}

    consultas = {
        "E-LAT-0_cero_resultados": (corpus.TOKEN_AUSENTE, 0),
        "E-LAT-1_un_resultado_exacto": (corpus.TOKEN_UNICO, 1),
        "E-LAT-N_muchos_candidatos": (corpus.TOKEN_FRECUENTE, banco.ids.memorias_frecuentes),
    }

    for nombre, (consulta, esperados) in consultas.items():
        aciertos = banco.busqueda.search_knowledge(consulta)
        indice = medir(
            lambda c=consulta: banco.busqueda.search_knowledge(c),
            repeticiones=REPS_BARATO,
            warmup=WARMUP,
        )
        completo = medir(
            lambda c=consulta: banco.caso_de_uso.rank(c),
            repeticiones=REPS_CARO,
            warmup=WARMUP,
        )
        resultados = banco.caso_de_uso.rank(consulta)
        escenarios[nombre] = {
            "consulta": consulta,
            "aciertos_en_el_indice": len(aciertos),
            "aciertos_esperados_en_el_indice": esperados,
            "resultados_externos_de_rank": len(resultados),
            "solo_indice_fts5": como_dict(indice),
            "recuperacion_completa_rank": como_dict(completo),
        }

    # Escenario 4: el barrido completo se evidencia comparando el coste del
    # indice con el coste total, para una consulta que no acierta nada.
    solo_indice = escenarios["E-LAT-0_cero_resultados"]["solo_indice_fts5"]["p50_ms"]
    total = escenarios["E-LAT-0_cero_resultados"]["recuperacion_completa_rank"]["p50_ms"]
    escenarios["E-BARRIDO_coste_del_barrido_completo"] = {
        "descripcion": (
            "Con cero aciertos en el indice, rank() sigue recorriendo todo el conocimiento "
            "vigente. La diferencia entre el coste total y el del indice es el barrido."
        ),
        "p50_solo_indice_ms": solo_indice,
        "p50_recuperacion_completa_ms": total,
        "p50_barrido_ms": round(total - solo_indice, 4),
        "fraccion_del_coste_atribuible_al_barrido": (
            round((total - solo_indice) / total, 4) if total else None
        ),
        "memorias_vigentes_recorridas": banco.ids.memorias_vigentes,
        "decisiones_recorridas": banco.ids.decisiones_aprobadas,
        "traza_normativa": "B04-RF-14 prohibe el salto a recuperacion amplia",
    }
    return escenarios


# --------------------------------------------------------------------------
# 5. TOL-002: ausencia real frente a contenido no reportable.
# --------------------------------------------------------------------------


def medir_indistinguibilidad(banco: Banco) -> dict[str, Any]:
    """Par pareado ausencia real / contenido existente no reportable.

    Ambas consultas deben producir la misma salida externa. Lo que se mide
    es si el tiempo las distingue. Las muestras se toman INTERCALADAS para
    que cualquier deriva del sistema afecte por igual a las dos ramas.
    """
    ausencia = corpus.TOKEN_AUSENTE
    no_reportable = corpus.TOKEN_NO_REPORTABLE

    # Salida externa observable de cada rama.
    externa_ausencia = banco.caso_de_uso.rank(ausencia)
    externa_no_reportable = banco.caso_de_uso.rank(no_reportable)

    # Control: el contenido no reportable SI existe en el indice.
    aciertos_ausencia = banco.busqueda.search_knowledge(ausencia)
    aciertos_no_reportable = banco.busqueda.search_knowledge(no_reportable)

    pareado_rank = _medir_pareado(
        lambda: banco.caso_de_uso.rank(ausencia),
        lambda: banco.caso_de_uso.rank(no_reportable),
        repeticiones=REPS_CARO,
    )
    pareado_indice = _medir_pareado(
        lambda: banco.busqueda.search_knowledge(ausencia),
        lambda: banco.busqueda.search_knowledge(no_reportable),
        repeticiones=REPS_BARATO,
    )

    return {
        "modelo_de_amenaza": (
            "Observador externo que solo ve la salida de la recuperacion y puede cronometrarla "
            "repetidamente en la misma maquina y proceso. NO se modela un atacante con acceso al "
            "fichero, a las trazas internas ni al canal de otra operacion concurrente. Una "
            "diferencia temporal repetible atribuible a la existencia protegida FALLA aunque "
            "ambas consultas sean rapidas; una diferencia no repetible no prueba lo contrario."
        ),
        "limites": (
            "Medicion en una sola maquina, un solo proceso y una sola configuracion. No es una "
            "garantia criptografica y no sustituye a un analisis de canal lateral: acota lo "
            "observable en este entorno, nada mas."
        ),
        "estado_externo": {
            "ausencia_real": len(externa_ausencia),
            "no_reportable": len(externa_no_reportable),
            "equivalentes": len(externa_ausencia) == len(externa_no_reportable),
        },
        "conteo_externo_equivalente": len(externa_ausencia) == len(externa_no_reportable),
        "texto_externo_equivalente": (
            _forma_externa(externa_ausencia) == _forma_externa(externa_no_reportable)
        ),
        "control_el_contenido_protegido_existe_en_el_indice": {
            "aciertos_ausencia_real": len(aciertos_ausencia),
            "aciertos_no_reportable": len(aciertos_no_reportable),
            "el_control_es_valido": len(aciertos_ausencia) == 0 and len(aciertos_no_reportable) > 0,
        },
        "tiempo_recuperacion_completa": pareado_rank,
        "tiempo_solo_indice_fts5": pareado_indice,
    }


def _forma_externa(resultados: tuple[Any, ...]) -> list[str]:
    """Lo unico que un observador externo ve de cada resultado."""
    return [f"{r.kind}:{r.item_id}" for r in resultados]


def _medir_pareado(
    rama_a: Callable[[], Any],
    rama_b: Callable[[], Any],
    *,
    repeticiones: int,
) -> dict[str, Any]:
    """Muestras intercaladas A,B,A,B... para anular la deriva temporal."""
    import time

    for _ in range(WARMUP):
        rama_a()
        rama_b()

    muestras_a: list[float] = []
    muestras_b: list[float] = []
    for _ in range(repeticiones):
        inicio = time.perf_counter_ns()
        rama_a()
        muestras_a.append((time.perf_counter_ns() - inicio) / 1_000_000)
        inicio = time.perf_counter_ns()
        rama_b()
        muestras_b.append((time.perf_counter_ns() - inicio) / 1_000_000)

    ordenadas_a = sorted(muestras_a)
    ordenadas_b = sorted(muestras_b)
    resumen_a = _resumen(ordenadas_a)
    resumen_b = _resumen(ordenadas_b)

    diferencias = [b - a for a, b in zip(muestras_a, muestras_b, strict=True)]
    ordenadas_dif = sorted(diferencias)
    positivas = sum(1 for d in diferencias if d > 0)

    return {
        "n_por_rama": repeticiones,
        "warmup_descartado": WARMUP,
        "muestreo": "intercalado A,B,A,B para anular deriva",
        "ausencia_real": resumen_a,
        "no_reportable": resumen_b,
        "diferencia_p50_ms": round(resumen_b["p50_ms"] - resumen_a["p50_ms"], 4),
        "diferencia_p95_ms": round(resumen_b["p95_ms"] - resumen_a["p95_ms"], 4),
        "diferencia_p99_ms": round(resumen_b["p99_ms"] - resumen_a["p99_ms"], 4),
        "diferencia_relativa_p50": (
            round((resumen_b["p50_ms"] - resumen_a["p50_ms"]) / resumen_a["p50_ms"], 4)
            if resumen_a["p50_ms"]
            else None
        ),
        "diferencia_pareada_mediana_ms": round(percentil(ordenadas_dif, 0.50), 4),
        "veces_que_no_reportable_tardo_mas": positivas,
        "fraccion_de_signo": round(positivas / repeticiones, 4),
        "nota_sobre_el_signo": (
            "Con ramas indistinguibles la fraccion de signo deberia rondar 0,5. Un valor "
            "sistematicamente alejado indica diferencia repetible, no ruido."
        ),
    }


def _resumen(ordenadas: list[float]) -> dict[str, float]:
    return {
        "p50_ms": round(percentil(ordenadas, 0.50), 4),
        "p95_ms": round(percentil(ordenadas, 0.95), 4),
        "p99_ms": round(percentil(ordenadas, 0.99), 4),
        "min_ms": round(ordenadas[0], 4),
        "max_ms": round(ordenadas[-1], 4),
        "media_ms": round(sum(ordenadas) / len(ordenadas), 4),
    }


# --------------------------------------------------------------------------
# 6-8. Tamano, construccion, reconstruccion y borrado del derivado.
# --------------------------------------------------------------------------


def _paginas_por_objeto(connection: sqlite3.Connection) -> dict[str, int]:
    """Bytes reales por objeto, a traves de la tabla virtual ``dbstat``."""
    page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
    filas = connection.execute(
        "SELECT name, SUM(pgsize) FROM dbstat GROUP BY name ORDER BY name"
    ).fetchall()
    del page_size
    return {str(nombre): int(bytes_) for nombre, bytes_ in filas}


def _bytes_canonicos_indexados(connection: sqlite3.Connection) -> dict[str, int]:
    """Bytes de contenido canonico que los indices cubren."""
    mensajes = int(
        connection.execute(
            "SELECT COALESCE(SUM(LENGTH(content)), 0) FROM messages WHERE content IS NOT NULL"
        ).fetchone()[0]
    )
    memorias = int(
        connection.execute(
            "SELECT COALESCE(SUM(LENGTH(content)), 0) FROM memory_revisions "
            "WHERE is_current = 1 AND content IS NOT NULL"
        ).fetchone()[0]
    )
    decisiones = int(
        connection.execute(
            "SELECT COALESCE(SUM(LENGTH(content)), 0) FROM decision_revisions "
            "WHERE is_current = 1 AND content IS NOT NULL"
        ).fetchone()[0]
    )
    return {
        "messages": mensajes,
        "memory_revisions_vigentes": memorias,
        "decision_revisions_vigentes": decisiones,
        "total_knowledge_fts": memorias + decisiones,
        "total_message_fts": mensajes,
    }


def medir_tamano(database_path: Path) -> dict[str, Any]:
    """Tamano fisico de los indices derivados frente al canon indexado."""
    connection = sqlite3.connect(str(database_path))
    try:
        por_objeto = _paginas_por_objeto(connection)
        canonicos = _bytes_canonicos_indexados(connection)

        def sumar(prefijo: str) -> int:
            return sum(b for nombre, b in por_objeto.items() if nombre.startswith(prefijo))

        knowledge = sumar("knowledge_fts")
        message = sumar("message_fts")
        total_fichero = database_path.stat().st_size

        return {
            "metodo": "tabla virtual dbstat, bytes reales por objeto",
            "tamano_fichero_bytes": total_fichero,
            "bytes_por_objeto_derivado": {
                nombre: b
                for nombre, b in sorted(por_objeto.items())
                if nombre.startswith(TABLAS_FTS)
            },
            "knowledge_fts_bytes": knowledge,
            "message_fts_bytes": message,
            "indices_derivados_bytes": knowledge + message,
            "canon_indexado_bytes": canonicos,
            "ratio_knowledge_fts_sobre_canon": (
                round(knowledge / canonicos["total_knowledge_fts"], 4)
                if canonicos["total_knowledge_fts"]
                else None
            ),
            "ratio_message_fts_sobre_canon": (
                round(message / canonicos["total_message_fts"], 4)
                if canonicos["total_message_fts"]
                else None
            ),
            "ratio_derivados_sobre_fichero": round((knowledge + message) / total_fichero, 4),
            "nota_knowledge_fts_guarda_copia": (
                "knowledge_fts es autocontenida: knowledge_fts_content almacena una copia "
                "literal del texto canonico. message_fts es external content y no la almacena."
            ),
        }
    finally:
        connection.close()


def _ddl_de_los_derivados(connection: sqlite3.Connection) -> dict[str, list[str]]:
    """Lee del propio esquema canonico el DDL de tablas y triggers FTS5.

    No se escribe DDL a mano: se recupera de ``sqlite_master`` para que la
    reconstruccion use exactamente lo que la migracion creo.
    """
    tablas = [
        str(sql)
        for (sql,) in connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name IN (?, ?) ORDER BY name",
            TABLAS_FTS,
        ).fetchall()
    ]
    triggers = [
        str(sql)
        for (sql,) in connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND sql LIKE '%_fts%' "
            "ORDER BY name"
        ).fetchall()
    ]
    return {"tablas": tablas, "triggers": triggers}


_BACKFILL_DESDE_CANON = (
    "INSERT INTO message_fts(rowid, content) SELECT id, content FROM messages",
    "INSERT INTO knowledge_fts(rowid, kind, item_id, content) "
    "SELECT memory_id * 2, 'memory', memory_id, content FROM memory_revisions "
    "WHERE is_current = 1 AND content IS NOT NULL",
    "INSERT INTO knowledge_fts(rowid, kind, item_id, content) "
    "SELECT decision_id * 2 + 1, 'decision', decision_id, content FROM decision_revisions "
    "WHERE is_current = 1 AND content IS NOT NULL",
)


def medir_construccion_y_reconstruccion(database_path: Path) -> dict[str, Any]:
    """Escenarios 6, 7 y 8 sobre una copia, para no alterar el banco."""
    copia = database_path.with_name("copia_construccion.db")
    shutil.copy2(database_path, copia)

    connection = sqlite3.connect(str(copia))
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        ddl = _ddl_de_los_derivados(connection)
        objetos_antes = _objetos_derivados(connection)
        filas_antes = _filas_indexadas(connection)

        # --- Escenario 8: borrado del derivado y comprobacion de desaparicion.
        def borrar() -> None:
            for trigger in _nombres_triggers_fts(connection):
                connection.execute(f"DROP TRIGGER IF EXISTS {trigger}")
            for tabla in TABLAS_FTS:
                connection.execute(f"DROP TABLE IF EXISTS {tabla}")
            connection.commit()

        _, ms_borrado = cronometrar_una_vez(borrar)
        objetos_tras_borrado = _objetos_derivados(connection)
        rastro = _rastro_de_sombras(connection)

        # --- Escenario 6: construccion inicial desde el canon.
        def construir() -> None:
            for sentencia in ddl["tablas"]:
                connection.execute(sentencia)
            for sentencia in ddl["triggers"]:
                connection.execute(sentencia)
            for sentencia in _BACKFILL_DESDE_CANON:
                connection.execute(sentencia)
            connection.commit()

        _, ms_construccion = cronometrar_una_vez(construir)
        objetos_tras_construir = _objetos_derivados(connection)
        filas_tras_construir = _filas_indexadas(connection)

        # --- Escenario 7: reconstruccion. Dos rutas distintas.
        def rebuild_interno() -> None:
            for tabla in TABLAS_FTS:
                connection.execute(f"INSERT INTO {tabla}({tabla}) VALUES('rebuild')")
            connection.commit()

        _, ms_rebuild = cronometrar_una_vez(rebuild_interno)

        def reconstruir_desde_canon() -> None:
            for tabla in TABLAS_FTS:
                connection.execute(f"DELETE FROM {tabla}")
            for sentencia in _BACKFILL_DESDE_CANON:
                connection.execute(sentencia)
            connection.commit()

        _, ms_desde_canon = cronometrar_una_vez(reconstruir_desde_canon)
        filas_tras_reconstruir = _filas_indexadas(connection)

        integridad = {}
        for tabla in TABLAS_FTS:
            try:
                connection.execute(f"INSERT INTO {tabla}({tabla}) VALUES('integrity-check')")
                integridad[tabla] = "OK"
            except sqlite3.Error as error:  # pragma: no cover - defensivo
                integridad[tabla] = f"ERROR: {error}"

        return {
            "E-BORRADO_desaparicion_del_derivado": {
                "ms": round(ms_borrado, 4),
                "objetos_derivados_antes": objetos_antes,
                "objetos_derivados_despues": objetos_tras_borrado,
                "desaparicion_completa": objetos_tras_borrado == [],
                "tablas_sombra_residuales": rastro,
                "sin_rastro_de_sombras": rastro == [],
            },
            "E-CONSTRUCCION_inicial_desde_canon": {
                "ms": round(ms_construccion, 4),
                "objetos_creados": objetos_tras_construir,
                "filas_indexadas": filas_tras_construir,
                "filas_identicas_a_las_originales": filas_tras_construir == filas_antes,
                "ddl_procedente_de": "sqlite_master del esquema canonico, no escrito a mano",
            },
            "E-RECONSTRUCCION": {
                "rebuild_interno_ms": round(ms_rebuild, 4),
                "desde_canon_ms": round(ms_desde_canon, 4),
                "filas_tras_reconstruir": filas_tras_reconstruir,
                "filas_identicas_a_las_originales": filas_tras_reconstruir == filas_antes,
                "integrity_check": integridad,
                "nota": (
                    "El rebuild interno de knowledge_fts se reconstruye desde su propia tabla de "
                    "contenido, no desde memory_revisions. La ruta desde el canon se mide aparte "
                    "porque es la que ADR-001 exige."
                ),
            },
        }
    finally:
        connection.close()


def _objetos_derivados(connection: sqlite3.Connection) -> list[str]:
    return [
        str(nombre)
        for (nombre,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE name LIKE 'knowledge\\_fts%' ESCAPE '\\' "
            "OR name LIKE 'message\\_fts%' ESCAPE '\\' ORDER BY name"
        ).fetchall()
    ]


def _rastro_de_sombras(connection: sqlite3.Connection) -> list[str]:
    return [
        str(nombre)
        for (nombre,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name LIKE '%\\_fts\\_%' ESCAPE '\\' ORDER BY name"
        ).fetchall()
    ]


def _nombres_triggers_fts(connection: sqlite3.Connection) -> list[str]:
    return [
        str(nombre)
        for (nombre,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE '%\\_fts\\_%' "
            "ESCAPE '\\' ORDER BY name"
        ).fetchall()
    ]


def _filas_indexadas(connection: sqlite3.Connection) -> dict[str, int]:
    resultado: dict[str, int] = {}
    for tabla in TABLAS_FTS:
        try:
            resultado[tabla] = int(
                connection.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            )
        except sqlite3.Error:
            resultado[tabla] = -1
    return resultado


# --------------------------------------------------------------------------
# 9. Estabilidad de conjunto y orden.
# --------------------------------------------------------------------------


def medir_estabilidad(banco: Banco, *, repeticiones: int = REPS_CARO) -> dict[str, Any]:
    """Repeticion identica: el conjunto y el orden deben ser identicos."""
    resultados: dict[str, Any] = {}
    for etiqueta, consulta in (
        ("consulta_frecuente", corpus.TOKEN_FRECUENTE),
        ("consulta_unica", corpus.TOKEN_UNICO),
        ("consulta_vacia", corpus.TOKEN_AUSENTE),
    ):
        ordenes = [_forma_externa(banco.caso_de_uso.rank(consulta)) for _ in range(repeticiones)]
        primero = ordenes[0]
        conjuntos = [frozenset(o) for o in ordenes]
        resultados[etiqueta] = {
            "consulta": consulta,
            "repeticiones": repeticiones,
            "tamano_del_resultado": len(primero),
            "ordenes_distintos_observados": len({tuple(o) for o in ordenes}),
            "conjuntos_distintos_observados": len(set(conjuntos)),
            "orden_identico_en_todas": all(o == primero for o in ordenes),
            "conjunto_identico_en_todas": all(c == conjuntos[0] for c in conjuntos),
        }
    resultados["resumen"] = {
        "orden_estable_en_todos_los_escenarios": all(
            v["orden_identico_en_todas"] for k, v in resultados.items() if k != "resumen"
        ),
        "conjunto_estable_en_todos_los_escenarios": all(
            v["conjunto_identico_en_todas"] for k, v in resultados.items() if k != "resumen"
        ),
    }
    return resultados


def medir_fuga_de_ambito(banco: Banco) -> dict[str, Any]:
    """Control ya conocido: se reejecuta al volumen de referencia para
    confirmar que la fuga de B04-RF-06 persiste a escala."""
    resultados = banco.caso_de_uso.rank(corpus.TOKEN_AJENO)
    ajenos = [
        r for r in resultados if getattr(r.item, "project_id", None) == banco.ids.proyecto_ajeno_id
    ]
    return {
        "consulta": corpus.TOKEN_AJENO,
        "resultados_totales": len(resultados),
        "resultados_de_proyecto_ajeno": len(ajenos),
        "hay_fuga": len(ajenos) > 0,
        "traza_normativa": "B04-RF-06, B04-M06 (aislamiento de proyecto: 100 %)",
    }


__all__ = [
    "Banco",
    "Distribucion",
    "medir_construccion_y_reconstruccion",
    "medir_estabilidad",
    "medir_fuga_de_ambito",
    "medir_indistinguibilidad",
    "medir_latencias",
    "medir_tamano",
    "preparar_banco",
]
