"""Lo que mejor casa por palabras va antes que lo más reciente (ADR-238, ronda 2 de Codex)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.memory_search import MemorySearch
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.infrastructure.paths import resolve_paths

pytestmark = pytest.mark.integration


def test_el_puesto_por_palabras_llega_hasta_el_orden_final(tmp_path: Path) -> None:
    rutas = resolve_paths(tmp_path / "datos")
    initialize_persistence(rutas)
    base = rutas.data_dir / "sirius.db"
    memoria = build_sqlite_memory_repository(base)
    decisiones = build_sqlite_decision_repository(base)
    proyectos = build_sqlite_project_repository(base)
    busqueda = build_sqlite_knowledge_search_repository(base)
    try:
        mejor = memoria.create_memory("Toby es el perro de mi hermana: Toby.", "prueba")
        peor = memoria.create_memory(
            "Ayer en la playa había mucha gente y un perro que de lejos me recordó a Toby.",
            "prueba",
        )
        # El que mejor casa es el más viejo: si el orden fuera por fecha, iría detrás.
        with closing(sqlite3.connect(base)) as conexion, conexion:
            conexion.execute(
                "UPDATE memories SET updated_at = '2020-01-01 00:00:00.000000' WHERE id = ?",
                (mejor.id,),
            )
        assert busqueda.search_memory_ids("Toby", 12) == [mejor.id, peor.id]

        ranking = RankRelevantKnowledgeUseCase(
            memoria,
            decisiones,
            proyectos,
            busqueda,
            memory_search=MemorySearch(busqueda, memoria, None),
        ).rank("Toby")

        assert [candidato.item_id for candidato in ranking] == [mejor.id, peor.id]
    finally:
        for repositorio in (memoria, decisiones, proyectos, busqueda):
            repositorio.close()
