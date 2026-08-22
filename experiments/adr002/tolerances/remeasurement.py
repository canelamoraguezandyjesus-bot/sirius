"""Remedicion acotada del paquete 02B: ciclo de indices y sesiones.

Corrige dos defectos de metodo del paquete 02, sin tocar nada de lo que
alli era valido:

1. **Ciclo del indice medido una sola vez.** La afirmacion «irrepetible
   por naturaleza» era falsa: borrado, construccion y reconstruccion se
   repiten sobre copias limpias independientes, preparadas SIEMPRE fuera
   del cronometro.
2. **Variacion entre ejecuciones estimada con dos pasadas.** Se ejecutan
   sesiones completas independientes, cada una con su fichero, su motor,
   su cache y su warm-up propio.

``measurements.py`` no se modifica: este modulo reutiliza sus ayudantes
para que la evidencia del paquete 02 siga siendo reproducible tal cual.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from experiments.adr002.tolerances import corpus, measurements
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

CICLOS_MINIMOS = 30
SESIONES_MINIMAS = 5
WARMUP_CICLO = 2


class EvidenciaInsuficienteError(ValueError):
    """Se pidio menos repeticiones o sesiones de las que exige el 02B."""


def _distribucion(muestras: list[float], *, etiqueta: str) -> dict[str, Any]:
    """Resumen nearest-rank de una lista de tiempos, con su resolucion."""
    ordenadas = sorted(muestras)
    n = len(ordenadas)
    return {
        "operacion": etiqueta,
        "n": n,
        "p50_ms": round(percentil(ordenadas, 0.50), 4),
        "p95_ms": round(percentil(ordenadas, 0.95), 4),
        "p99_ms": round(percentil(ordenadas, 0.99), 4),
        "min_ms": round(ordenadas[0], 4),
        "max_ms": round(ordenadas[-1], 4),
        "media_ms": round(sum(ordenadas) / n, 4),
        "resolucion_p99": (
            f"con n={n}, el P99 por rango mas cercano coincide con el maximo observado; "
            f"acota la cola, no la caracteriza"
            if n < 100
            else f"con n={n}, el P99 corresponde a la peor muestra observada"
        ),
    }


# --------------------------------------------------------------------------
# 1. Ciclo del indice repetido sobre copias limpias.
# --------------------------------------------------------------------------


def medir_ciclo_repetido(
    base_referencia: Path,
    *,
    repeticiones: int = CICLOS_MINIMOS,
    warmup: int = WARMUP_CICLO,
) -> dict[str, Any]:
    """Borrado, construccion y reconstruccion desde el canon, N veces.

    Cada repeticion trabaja sobre una **copia limpia e independiente** de
    la base de referencia. La copia, la apertura de la conexion, la
    lectura del DDL y todas las verificaciones ocurren FUERA del
    cronometro: solo se mide la operacion en si.
    """
    if repeticiones < CICLOS_MINIMOS:
        msg = f"{repeticiones} repeticiones; el 02B exige al menos {CICLOS_MINIMOS}"
        raise EvidenciaInsuficienteError(msg)

    borrado: list[float] = []
    construccion: list[float] = []
    reconstruccion: list[float] = []
    rebuild_interno: list[float] = []

    exitos = {
        "borrado_completo": 0,
        "sin_rastro_de_sombras": 0,
        "construccion_filas_identicas": 0,
        "reconstruccion_filas_identicas": 0,
        "integrity_check_ok": 0,
    }
    fallos: list[dict[str, Any]] = []
    directorio = Path(tempfile.mkdtemp(prefix="adr002_ciclo_"))

    try:
        for indice in range(warmup + repeticiones):
            es_warmup = indice < warmup
            copia = directorio / f"ciclo_{indice}.db"

            # --- FUERA DEL CRONOMETRO: copia limpia y estado de partida.
            shutil.copy2(base_referencia, copia)
            connection = sqlite3.connect(str(copia))
            connection.execute("PRAGMA foreign_keys=ON")
            try:
                ddl = measurements._ddl_de_los_derivados(connection)
                triggers = measurements._nombres_triggers_fts(connection)
                filas_originales = measurements._filas_indexadas(connection)

                # --- CRONOMETRO 1: borrado completo del derivado.
                def borrar(conn: sqlite3.Connection = connection, t: list[str] = triggers) -> None:
                    for trigger in t:
                        conn.execute(f"DROP TRIGGER IF EXISTS {trigger}")
                    for tabla in measurements.TABLAS_FTS:
                        conn.execute(f"DROP TABLE IF EXISTS {tabla}")
                    conn.commit()

                _, ms_borrado = cronometrar_una_vez(borrar)

                # --- FUERA: verificacion del borrado.
                desaparicion = measurements._objetos_derivados(connection) == []
                rastro = measurements._rastro_de_sombras(connection) == []

                # --- CRONOMETRO 2: construccion inicial desde el canon.
                def construir(conn: sqlite3.Connection = connection, d: dict = ddl) -> None:
                    for sentencia in d["tablas"]:
                        conn.execute(sentencia)
                    for sentencia in d["triggers"]:
                        conn.execute(sentencia)
                    for sentencia in measurements._BACKFILL_DESDE_CANON:
                        conn.execute(sentencia)
                    conn.commit()

                _, ms_construccion = cronometrar_una_vez(construir)

                # --- FUERA: verificacion de la construccion.
                filas_construidas = measurements._filas_indexadas(connection)
                construccion_ok = filas_construidas == filas_originales

                # --- CRONOMETRO 3: reconstruccion desde el canon.
                def reconstruir(conn: sqlite3.Connection = connection) -> None:
                    for tabla in measurements.TABLAS_FTS:
                        conn.execute(f"DELETE FROM {tabla}")
                    for sentencia in measurements._BACKFILL_DESDE_CANON:
                        conn.execute(sentencia)
                    conn.commit()

                _, ms_reconstruccion = cronometrar_una_vez(reconstruir)

                # --- FUERA: verificacion de la reconstruccion.
                filas_reconstruidas = measurements._filas_indexadas(connection)
                reconstruccion_ok = filas_reconstruidas == filas_originales
                integridad_ok = _integridad(connection)

                # --- Observacion aparte: rebuild interno. NO es evidencia de
                #     reconstruccion desde el canon para knowledge_fts.
                def rebuild(conn: sqlite3.Connection = connection) -> None:
                    for tabla in measurements.TABLAS_FTS:
                        conn.execute(f"INSERT INTO {tabla}({tabla}) VALUES('rebuild')")
                    conn.commit()

                _, ms_rebuild = cronometrar_una_vez(rebuild)

                if es_warmup:
                    continue

                borrado.append(ms_borrado)
                construccion.append(ms_construccion)
                reconstruccion.append(ms_reconstruccion)
                rebuild_interno.append(ms_rebuild)

                exitos["borrado_completo"] += int(desaparicion)
                exitos["sin_rastro_de_sombras"] += int(rastro)
                exitos["construccion_filas_identicas"] += int(construccion_ok)
                exitos["reconstruccion_filas_identicas"] += int(reconstruccion_ok)
                exitos["integrity_check_ok"] += int(integridad_ok)

                if not all(
                    (desaparicion, rastro, construccion_ok, reconstruccion_ok, integridad_ok)
                ):
                    fallos.append(
                        {
                            "repeticion": indice - warmup,
                            "borrado_completo": desaparicion,
                            "sin_rastro": rastro,
                            "construccion_filas_identicas": construccion_ok,
                            "reconstruccion_filas_identicas": reconstruccion_ok,
                            "integrity_check_ok": integridad_ok,
                        }
                    )
            finally:
                connection.close()
                copia.unlink(missing_ok=True)
    finally:
        shutil.rmtree(directorio, ignore_errors=True)

    tasas = {
        clave: {
            "exitos": valor,
            "de": repeticiones,
            "tasa": round(valor / repeticiones, 4),
        }
        for clave, valor in exitos.items()
    }

    return {
        "descripcion": (
            "Ciclo completo repetido sobre copias limpias independientes. La copia, la apertura "
            "de la conexion, la lectura del DDL y todas las verificaciones quedan FUERA del "
            "cronometro."
        ),
        "repeticiones": repeticiones,
        "warmup_descartado": warmup,
        "base_de_cada_repeticion": "copia limpia e independiente de la base de referencia",
        "ddl_procedente_de": "sqlite_master del esquema canonico, nunca escrito a mano",
        "borrado": _distribucion(borrado, etiqueta="borrado completo del derivado"),
        "construccion_desde_canon": _distribucion(
            construccion, etiqueta="construccion inicial desde el canon"
        ),
        "reconstruccion_desde_canon": _distribucion(
            reconstruccion, etiqueta="reconstruccion desde el canon"
        ),
        "observacion_rebuild_interno": {
            **_distribucion(rebuild_interno, etiqueta="rebuild interno de FTS5"),
            "advertencia": (
                "El rebuild interno reconstruye knowledge_fts desde su propia tabla de contenido, "
                "no desde memory_revisions. Se conserva como OBSERVACION y NUNCA como evidencia "
                "de reconstruccion desde el canon."
            ),
        },
        "tasas_de_exito": tasas,
        "todas_las_comprobaciones_al_100": all(t["tasa"] == 1.0 for t in tasas.values()),
        "repeticiones_con_fallo": fallos,
    }


def _integridad(connection: sqlite3.Connection) -> bool:
    for tabla in measurements.TABLAS_FTS:
        try:
            connection.execute(f"INSERT INTO {tabla}({tabla}) VALUES('integrity-check')")
        except sqlite3.Error:
            return False
    return True


# --------------------------------------------------------------------------
# 2. Sesiones completas independientes.
# --------------------------------------------------------------------------


def medir_sesiones(
    base_referencia: Path,
    ids: corpus.CorpusIds,
    *,
    sesiones: int = SESIONES_MINIMAS,
) -> dict[str, Any]:
    """N sesiones independientes, cada una con fichero, motor y warm-up propios."""
    if sesiones < SESIONES_MINIMAS:
        msg = f"{sesiones} sesiones; el 02B exige al menos {SESIONES_MINIMAS}"
        raise EvidenciaInsuficienteError(msg)

    consultas = {
        "cero_resultados": corpus.TOKEN_AUSENTE,
        "un_resultado_exacto": corpus.TOKEN_UNICO,
        "muchos_candidatos": corpus.TOKEN_FRECUENTE,
    }
    directorio = Path(tempfile.mkdtemp(prefix="adr002_sesiones_"))
    por_sesion: list[dict[str, Any]] = []
    formas: dict[str, list[list[str]]] = {clave: [] for clave in consultas}

    try:
        for numero in range(sesiones):
            # --- FUERA DEL CRONOMETRO: fichero y repositorios nuevos.
            copia = directorio / f"sesion_{numero}.db"
            shutil.copy2(base_referencia, copia)
            busqueda = build_sqlite_knowledge_search_repository(copia)
            caso_de_uso = RankRelevantKnowledgeUseCase(
                memory_repository=build_sqlite_memory_repository(copia),
                decision_repository=build_sqlite_decision_repository(copia),
                project_repository=build_sqlite_project_repository(copia),
                knowledge_search_repository=busqueda,
            )
            try:
                medidas: dict[str, Any] = {}
                for clave, consulta in consultas.items():
                    indice: Distribucion = medir(
                        lambda c=consulta, b=busqueda: b.search_knowledge(c),
                        repeticiones=REPS_BARATO,
                        warmup=measurements.WARMUP,
                    )
                    completo: Distribucion = medir(
                        lambda c=consulta, u=caso_de_uso: u.rank(c),
                        repeticiones=REPS_CARO,
                        warmup=measurements.WARMUP,
                    )
                    formas[clave].append(measurements._forma_externa(caso_de_uso.rank(consulta)))
                    medidas[clave] = {
                        "consulta": consulta,
                        "solo_indice_fts5": como_dict(indice),
                        "recuperacion_completa_rank": como_dict(completo),
                    }
                por_sesion.append({"sesion": numero + 1, "escenarios": medidas})
            finally:
                busqueda.close()
                copia.unlink(missing_ok=True)
    finally:
        shutil.rmtree(directorio, ignore_errors=True)

    return {
        "descripcion": (
            "Sesiones completas independientes: cada una usa su propio fichero, su propio motor "
            "SQLAlchemy, su propia cache y su propio warm-up."
        ),
        "sesiones": sesiones,
        "limite_declarado": (
            "Las sesiones son independientes DENTRO DEL MISMO PROCESO: comparten interprete y "
            "maquina. No son procesos separados ni maquinas distintas, asi que acotan la "
            "variacion intra-proceso, no la variacion entre entornos."
        ),
        "corpus_por_sesion": {
            "mensajes": ids.mensajes,
            "memorias_vigentes": ids.memorias_vigentes,
            "identico_en_todas": True,
        },
        "por_sesion": por_sesion,
        "variacion_entre_sesiones": _variacion_entre_sesiones(por_sesion, consultas),
        "estabilidad_entre_sesiones": _estabilidad_entre_sesiones(formas),
    }


def _variacion_entre_sesiones(
    por_sesion: list[dict[str, Any]],
    consultas: dict[str, str],
) -> dict[str, Any]:
    """Peor variacion relativa entre sesiones, con la formula ya declarada.

    ``(max - min) / min`` sobre los valores de un percentil en todas las
    sesiones: es exactamente el peor par posible, y por tanto acota la
    variacion observada sin depender del orden de las sesiones.
    """
    resultado: dict[str, Any] = {}
    peores: list[float] = []

    for clave in consultas:
        por_capa: dict[str, Any] = {}
        for capa in ("solo_indice_fts5", "recuperacion_completa_rank"):
            for percentil_clave in ("p50_ms", "p95_ms"):
                valores = [
                    sesion["escenarios"][clave][capa][percentil_clave] for sesion in por_sesion
                ]
                minimo, maximo = min(valores), max(valores)
                variacion = round((maximo - minimo) / minimo, 4) if minimo else None
                por_capa[f"{capa}__{percentil_clave}"] = {
                    "valores_por_sesion": valores,
                    "min": minimo,
                    "max": maximo,
                    "variacion_max_relativa": variacion,
                }
                if variacion is not None:
                    peores.append(variacion)
        resultado[clave] = por_capa

    resultado["peor_variacion_relativa_observada"] = round(max(peores), 4) if peores else None
    resultado["formula"] = "(max - min) / min sobre el mismo percentil en todas las sesiones"
    return resultado


def _estabilidad_entre_sesiones(formas: dict[str, list[list[str]]]) -> dict[str, Any]:
    """El conjunto y el orden deben ser identicos entre sesiones distintas."""
    detalle: dict[str, Any] = {}
    for clave, observadas in formas.items():
        ordenes = {tuple(f) for f in observadas}
        conjuntos = {frozenset(f) for f in observadas}
        detalle[clave] = {
            "sesiones": len(observadas),
            "tamano_del_resultado": len(observadas[0]) if observadas else 0,
            "ordenes_distintos": len(ordenes),
            "conjuntos_distintos": len(conjuntos),
            "orden_identico_entre_sesiones": len(ordenes) == 1,
            "conjunto_identico_entre_sesiones": len(conjuntos) == 1,
        }
    detalle["resumen"] = {
        "orden_estable_entre_sesiones": all(
            v["orden_identico_entre_sesiones"] for k, v in detalle.items() if k != "resumen"
        ),
        "conjunto_estable_entre_sesiones": all(
            v["conjunto_identico_entre_sesiones"] for k, v in detalle.items() if k != "resumen"
        ),
    }
    return detalle


__all__ = [
    "CICLOS_MINIMOS",
    "SESIONES_MINIMAS",
    "EvidenciaInsuficienteError",
    "medir_ciclo_repetido",
    "medir_sesiones",
]
