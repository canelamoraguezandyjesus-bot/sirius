"""B12e — listar recuerdos y decisiones vigentes/archivados sin N+1.

Nota de arranque (ADR-008):

1. El fallo vive en ``_load_memory``/``_load_decision``, que ``list_current_*``
   y ``list_archived_*`` llaman una vez por elemento. El arreglo vive en esos
   mismos métodos ``list_*``, que SÍ pueden observar cuántas consultas emiten:
   son el único punto que decide cuántas veces se llama a la carga de
   revisión. Un ``_load_memory`` que muere después de una consulta no puede
   informar de que hizo falta una segunda.
2. Esto NO garantiza que el número de consultas sea el mínimo posible (un
   `JOIN` bajaría de dos a una), solo que deja de crecer con el número de
   elementos listados. Tampoco cambia qué devuelven estos métodos.
3. Criterio de parada, decidido antes de medir: si el número de consultas de
   ``list_current_memories()`` sigue dependiendo de cuántos recuerdos hay,
   la causa no era esta y hay que decirlo en vez de seguir tocando.
4. Lo que hace el fallo imposible en vez de improbable: esta prueba fija que
   el número de consultas no varíe al crecer el conjunto. Verificada por
   mutación (restaurando el `_load_memory`/`_load_decision` por elemento en
   los cuatro métodos listados): con el N+1 puesto, las cuatro aserciones de
   este archivo fallan porque el conteo crece con el número de elementos;
   restaurado el arreglo, las cuatro pasan.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, event

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_decision_repository import (
    SqliteDecisionRepository,
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import (
    SqliteMemoryRepository,
    build_sqlite_memory_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository


@contextmanager
def _contar_consultas() -> Iterator[list[str]]:
    """Cuenta cada sentencia SQL ejecutada a través de SQLAlchemy en el bloque.

    Se engancha a nivel de clase ``Engine`` (no a un motor concreto) porque
    cada repositorio abre el suyo propio por llamada (``session_scope``).
    """
    sentencias: list[str] = []

    def _registrar(
        _conn: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        sentencias.append(statement)

    event.listen(Engine, "before_cursor_execute", _registrar)
    try:
        yield sentencias
    finally:
        event.remove(Engine, "before_cursor_execute", _registrar)


def _build_memory_repository(database_path: Path) -> SqliteMemoryRepository:
    Base.metadata.create_all(build_engine(database_path))
    return build_sqlite_memory_repository(database_path)


def _build_decision_repository(database_path: Path) -> SqliteDecisionRepository:
    Base.metadata.create_all(build_engine(database_path))
    return build_sqlite_decision_repository(database_path)


def _project_id(database_path: Path) -> int:
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="En curso",
        blockers=(),
        next_step="Siguiente paso",
    )
    return project.id


# Dos tamaños de conjunto bien distintos: si el número de consultas
# dependiera de N, estos dos conteos serían distintos.
POCOS = 3
MUCHOS = 25


@pytest.mark.integration
def test_list_current_memories_no_crece_con_el_numero_de_recuerdos(tmp_path: Path) -> None:
    repository = _build_memory_repository(tmp_path / "sirius.db")
    project_id = _project_id(tmp_path / "sirius.db")

    for indice in range(POCOS):
        repository.create_memory(
            f"recuerdo {indice}",
            origin="prueba",
            subject_key=f"asunto-{indice}",
            project_id=project_id,
        )
    with _contar_consultas() as sentencias:
        resultado_pocos = repository.list_current_memories()
    consultas_pocos = len(sentencias)
    assert len(resultado_pocos) == POCOS

    for indice in range(POCOS, MUCHOS):
        repository.create_memory(
            f"recuerdo {indice}",
            origin="prueba",
            subject_key=f"asunto-{indice}",
            project_id=project_id,
        )
    with _contar_consultas() as sentencias:
        resultado_muchos = repository.list_current_memories()
    consultas_muchos = len(sentencias)
    assert len(resultado_muchos) == MUCHOS

    assert consultas_muchos == consultas_pocos, (
        f"list_current_memories() ejecutó {consultas_pocos} consultas para "
        f"{POCOS} recuerdos y {consultas_muchos} para {MUCHOS}: el número de "
        "consultas depende del número de elementos (N+1)."
    )


@pytest.mark.integration
def test_list_archived_memories_no_crece_con_el_numero_de_recuerdos(tmp_path: Path) -> None:
    repository = _build_memory_repository(tmp_path / "sirius.db")
    project_id = _project_id(tmp_path / "sirius.db")

    def _crear_y_archivar(cuantos: int, desde: int) -> None:
        for indice in range(desde, desde + cuantos):
            memoria = repository.create_memory(
                f"recuerdo {indice}",
                origin="prueba",
                subject_key=f"asunto-{indice}",
                project_id=project_id,
            )
            repository.archive_memory(memoria.id)

    _crear_y_archivar(POCOS, 0)
    with _contar_consultas() as sentencias:
        resultado_pocos = repository.list_archived_memories()
    consultas_pocos = len(sentencias)
    assert len(resultado_pocos) == POCOS

    _crear_y_archivar(MUCHOS - POCOS, POCOS)
    with _contar_consultas() as sentencias:
        resultado_muchos = repository.list_archived_memories()
    consultas_muchos = len(sentencias)
    assert len(resultado_muchos) == MUCHOS

    assert consultas_muchos == consultas_pocos, (
        f"list_archived_memories() ejecutó {consultas_pocos} consultas para "
        f"{POCOS} recuerdos archivados y {consultas_muchos} para {MUCHOS}: el "
        "número de consultas depende del número de elementos (N+1)."
    )


@pytest.mark.integration
def test_list_current_decisions_no_crece_con_el_numero_de_decisiones(tmp_path: Path) -> None:
    repository = _build_decision_repository(tmp_path / "sirius.db")
    project_id = _project_id(tmp_path / "sirius.db")

    def _proponer_y_aprobar(cuantos: int, desde: int) -> None:
        for indice in range(desde, desde + cuantos):
            decision = repository.create_proposal(
                f"asunto-{indice}", project_id, f"contenido {indice}"
            )
            repository.approve_decision(decision.id)

    _proponer_y_aprobar(POCOS, 0)
    with _contar_consultas() as sentencias:
        resultado_pocos = repository.list_current_decisions()
    consultas_pocos = len(sentencias)
    assert len(resultado_pocos) == POCOS

    _proponer_y_aprobar(MUCHOS - POCOS, POCOS)
    with _contar_consultas() as sentencias:
        resultado_muchos = repository.list_current_decisions()
    consultas_muchos = len(sentencias)
    assert len(resultado_muchos) == MUCHOS

    assert consultas_muchos == consultas_pocos, (
        f"list_current_decisions() ejecutó {consultas_pocos} consultas para "
        f"{POCOS} decisiones y {consultas_muchos} para {MUCHOS}: el número de "
        "consultas depende del número de elementos (N+1)."
    )


@pytest.mark.integration
def test_list_archived_decisions_no_crece_con_el_numero_de_decisiones(tmp_path: Path) -> None:
    repository = _build_decision_repository(tmp_path / "sirius.db")
    project_id = _project_id(tmp_path / "sirius.db")

    def _proponer_aprobar_y_archivar(cuantos: int, desde: int) -> None:
        for indice in range(desde, desde + cuantos):
            decision = repository.create_proposal(
                f"asunto-{indice}", project_id, f"contenido {indice}"
            )
            repository.approve_decision(decision.id)
            repository.archive_decision(decision.id)

    _proponer_aprobar_y_archivar(POCOS, 0)
    with _contar_consultas() as sentencias:
        resultado_pocos = repository.list_archived_decisions()
    consultas_pocos = len(sentencias)
    assert len(resultado_pocos) == POCOS

    _proponer_aprobar_y_archivar(MUCHOS - POCOS, POCOS)
    with _contar_consultas() as sentencias:
        resultado_muchos = repository.list_archived_decisions()
    consultas_muchos = len(sentencias)
    assert len(resultado_muchos) == MUCHOS

    assert consultas_muchos == consultas_pocos, (
        f"list_archived_decisions() ejecutó {consultas_pocos} consultas para "
        f"{POCOS} decisiones archivadas y {consultas_muchos} para {MUCHOS}: el "
        "número de consultas depende del número de elementos (N+1)."
    )
