"""Mide en este ordenador lo que tarda Sirius en buscar en su memoria (E-R02-05, ADR-238).

POR QUÉ EXISTE
==============

El plan pide que buscar en la memoria tarde menos de 150 ms (§4, 0.2, paso 2 de
la memoria). Las pruebas lo miran en la nube con huellas de mentira; lo que
cuenta es su ordenador, con el modelo de huellas de verdad. Este guion busca 100
veces en una copia de su memoria y otras 100 en una de 10.000 recuerdos de
prueba, contando la huella de cada pregunta, y dice si el P95 queda por debajo.

Nunca toca su ``sirius.db``: trabaja sobre una copia en una carpeta temporal que
borra al acabar. Las preguntas son las 100 del banco de memoria.

USO
===

    uv run python scripts/medir_busqueda_de_memoria.py

Necesita Ollama abierto y el modelo de huellas instalado
(``ollama pull qwen3-embedding:0.6b``).
"""

from __future__ import annotations

import logging
import random
import sqlite3
import struct
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from sirius.adapters.llm.ollama_embeddings import OllamaEmbedder
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_embeddings import (
    build_sqlite_memory_embedding_store,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.memory_search import MemoryEmbeddingService, MemorySearch
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.composition_root import embedding_model
from sirius.config.settings import load_settings
from sirius.domain.memory_bank import MEMORY_BANK
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.embeddings import EmbeddingError, TextEmbedder

#: El límite del plan para el P95.
LIMITE_MS = 150.0

#: Cuántos recuerdos de prueba lleva la segunda memoria.
RECUERDOS_DE_PRUEBA = 10_000

_TEXTO_DE_PRUEBA = """
abuela agosto amigo arroz bici boda cena chocolate cine coche cocido concierto
cumpleaños dentista domingo fútbol garaje gato gimnasio hermana hospital huerto
madre moto música navidad oficina padre panadería perro playa pueblo sierra
sofá taller trabajo tren vacaciones vecino verano viaje
"""
_PALABRAS = _TEXTO_DE_PRUEBA.split()


def percentil(tiempos: Sequence[float], p: int) -> float:
    """El percentil ``p`` de ``tiempos``, por el método del rango más cercano."""
    ordenados = sorted(tiempos)
    return ordenados[max(0, -(-p * len(ordenados) // 100) - 1)]


class SinSqliteVec(RuntimeError):
    """sqlite-vec no carga en este Python: Sirius buscaría solo por palabras."""


def mide(base: Path, huellas: TextEmbedder, preguntas: Sequence[str]) -> list[float]:
    """Milisegundos de cada búsqueda en ``base``, como la de cada turno, huella incluida.

    Antes calcula las huellas que falten, como hace la ventana al abrirse.
    """
    recuerdos = build_sqlite_memory_repository(base)
    palabras = build_sqlite_knowledge_search_repository(base)
    almacen = build_sqlite_memory_embedding_store(base)
    try:
        if not almacen.available:
            raise SinSqliteVec
        servicio = MemoryEmbeddingService(huellas, almacen)
        servicio.embed_pending()
        busqueda = RankRelevantKnowledgeUseCase(
            memory_repository=recuerdos,
            decision_repository=build_sqlite_decision_repository(base),
            project_repository=build_sqlite_project_repository(base),
            knowledge_search_repository=palabras,
            memory_search=MemorySearch(palabras, recuerdos, servicio),
        )
        tiempos: list[float] = []
        for pregunta in preguntas:
            inicio = time.perf_counter()
            busqueda.rank(pregunta)
            tiempos.append((time.perf_counter() - inicio) * 1000)
        return tiempos
    finally:
        recuerdos.close()
        palabras.close()
        almacen.close()


def llena_de_prueba(base: Path, cuantos: int, modelo: str, dimension: int) -> None:
    """Guarda ``cuantos`` recuerdos de prueba con huellas de ``dimension`` números.

    Las huellas son al azar, con el nombre del modelo de verdad: buscar cuesta lo
    mismo que con las de verdad, y no hace falta calcular 10.000 con el modelo.
    """
    azar = random.Random(cuantos)
    ahora = datetime.now(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.%f")
    with closing(sqlite3.connect(base)) as conexion, conexion:
        filas = []
        for n in range(1, cuantos + 1):
            texto = " ".join(azar.choice(_PALABRAS) for _ in range(4))
            huella = struct.pack(f"<{dimension}f", *(azar.uniform(-1, 1) for _ in range(dimension)))
            filas.append((n, f"Recuerdo de prueba {n}: {texto}.", huella))
        conexion.executemany(
            "INSERT INTO memories (id, status, created_at, updated_at, category_locked)"
            " VALUES (?, 'current', ?, ?, 0)",
            [(n, ahora, ahora) for n, _, _ in filas],
        )
        conexion.executemany(
            "INSERT INTO memory_revisions"
            " (id, memory_id, version, content, origin, is_current, created_at)"
            " VALUES (?, ?, 1, ?, 'prueba', 1, ?)",
            [(n, n, texto, ahora) for n, texto, _ in filas],
        )
        conexion.executemany(
            "INSERT INTO memory_embeddings"
            " (memory_id, revision_id, model, embedding, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            [(n, n, modelo, huella, ahora) for n, _, huella in filas],
        )


def copia_su_memoria(origen: Path, destino: Path) -> int:
    """Copia ``sirius.db`` sin tocarla, aunque Sirius esté abierto. Devuelve cuántos recuerdos."""
    if origen.exists():
        with closing(sqlite3.connect(origen)) as fuente, closing(sqlite3.connect(destino)) as copia:
            fuente.backup(copia)
    upgrade_to_head(destino)
    with closing(sqlite3.connect(destino)) as conexion:
        fila = conexion.execute("SELECT COUNT(*) FROM memories WHERE status = 'current'").fetchone()
    return int(fila[0])


def _linea(nombre: str, tiempos: Sequence[float]) -> str:
    return (
        f"{nombre}: P50 {percentil(tiempos, 50):.0f} ms, P95 {percentil(tiempos, 95):.0f} ms,"
        f" el peor {max(tiempos):.0f} ms"
    )


def main(
    huellas_de: Callable[[str], TextEmbedder] = OllamaEmbedder,
    escribe: Callable[[str], None] = print,
) -> int:
    modelo = embedding_model(load_settings())
    huellas = huellas_de(modelo)
    try:
        dimension = len(huellas.embed(["prueba"])[0])
    except EmbeddingError:
        escribe(f"El modelo de huellas {modelo} no contesta.")
        escribe(f"Abre Ollama y ejecuta: ollama pull {modelo}")
        return 2
    preguntas = [caso.question for caso in MEMORY_BANK]
    with tempfile.TemporaryDirectory() as carpeta:
        suya = Path(carpeta) / "su-memoria.db"
        cuantos = copia_su_memoria(resolve_paths().data_dir / "sirius.db", suya)
        escribe(f"Modelo de huellas: {modelo} ({dimension} números por huella).")
        try:
            en_la_suya = mide(suya, huellas, preguntas)
        except SinSqliteVec:
            escribe("sqlite-vec no carga en este Python: Sirius buscaría solo por palabras.")
            return 3
        escribe(_linea(f"Tu memoria, {cuantos} recuerdos", en_la_suya))
        prueba = Path(carpeta) / "prueba.db"
        upgrade_to_head(prueba)
        llena_de_prueba(prueba, RECUERDOS_DE_PRUEBA, modelo, dimension)
        en_la_de_prueba = mide(prueba, huellas, preguntas)
        escribe(_linea(f"{RECUERDOS_DE_PRUEBA} recuerdos de prueba", en_la_de_prueba))
    pasa = max(percentil(en_la_suya, 95), percentil(en_la_de_prueba, 95)) < LIMITE_MS
    escribe("Pasa: sí." if pasa else f"Pasa: no. El P95 tiene que bajar de {LIMITE_MS:.0f} ms.")
    return 0 if pasa else 1


if __name__ == "__main__":
    logging.disable(logging.WARNING)
    sys.exit(main())
