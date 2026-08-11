"""B12e (ronda 2) — el ``IN (...)`` de _load_memories/_load_decisions no es ilimitado.

Nota de arranque:

1. El fallo vive en ``_load_memories``/``_load_decisions``
   (``sqlite_memory_repository.py``/``sqlite_decision_repository.py``): cuando
   el lote de ids supera ``SQLITE_LIMIT_VARIABLE_NUMBER`` de la conexión, el
   ``IN (...)`` construido con un parámetro por id revienta con
   ``OperationalError: too many SQL variables`` en vez de devolver la lista.
   El arreglo vive en esas mismas dos funciones, que son las únicas que
   deciden cuántos ids entran en cada sentencia ``IN``.
2. Esto NO garantiza el mínimo teórico de consultas (trocear en lotes emite
   más de una consulta cuando el lote excede el límite); solo garantiza que
   el método no falla ni cambia lo que devuelve, cualquiera que sea el
   tamaño del lote frente al límite de la conexión.
3. Criterio de parada, decidido antes de medir: si tras trocear el ``IN``
   sigue apareciendo ``OperationalError: too many SQL variables`` con un
   límite bajo y un lote que lo supera en 1, la causa no era el troceo y hay
   que decirlo en vez de seguir parcheando.
4. Lo que hace el fallo imposible en vez de improbable: esta prueba fija el
   límite de variables de la conexión SQLite a un valor bajo (20, el mínimo
   por encima de las 12 columnas del INSERT más ancho que el propio montaje
   de la prueba necesita) —en vez de esperar a acumular decenas de miles de
   recuerdos reales para tocar el límite por defecto (32766 desde SQLite
   3.32, o 999 en versiones anteriores)— y comprueba que listar un lote que
   lo supera en 1 no falla y devuelve todos los elementos. Verificada por
   mutación: con el ``IN`` sin trocear restaurado (``git stash`` sobre los
   dos ficheros de repositorio, dejando esta prueba intacta), ambas
   aserciones fallan con ``OperationalError: too many SQL variables``; con
   el arreglo, pasan.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, event

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import (
    build_sqlite_memory_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository

LIMITE_VARIABLES = 20  # por encima de las 12 columnas del INSERT más ancho (projects)
POR_ENCIMA_DEL_LIMITE = LIMITE_VARIABLES + 1


@contextmanager
def _limite_de_variables_sqlite(limite: int) -> Iterator[None]:
    """Fuerza ``SQLITE_LIMIT_VARIABLE_NUMBER`` a ``limite`` en cada conexión nueva.

    Reproduce con pocas filas el mismo escenario que el límite real de
    SQLite (miles/decenas de miles) exigiría acumular para golpear.
    """

    def _fijar_limite(dbapi_connection: sqlite3.Connection, _connection_record: Any) -> None:
        dbapi_connection.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, limite)

    event.listen(Engine, "connect", _fijar_limite)
    try:
        yield
    finally:
        event.remove(Engine, "connect", _fijar_limite)


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


@pytest.mark.integration
def test_list_current_memories_no_revienta_por_encima_del_limite_de_variables(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    with _limite_de_variables_sqlite(LIMITE_VARIABLES):
        Base.metadata.create_all(build_engine(database_path))
        repository = build_sqlite_memory_repository(database_path)
        project_id = _project_id(database_path)

        for indice in range(POR_ENCIMA_DEL_LIMITE):
            repository.create_memory(
                f"recuerdo {indice}",
                origin="prueba",
                subject_key=f"asunto-{indice}",
                project_id=project_id,
            )

        resultado = repository.list_current_memories()

    assert len(resultado) == POR_ENCIMA_DEL_LIMITE
    assert {memoria.current_revision.content for memoria in resultado} == {
        f"recuerdo {indice}" for indice in range(POR_ENCIMA_DEL_LIMITE)
    }


@pytest.mark.integration
def test_list_current_decisions_no_revienta_por_encima_del_limite_de_variables(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    with _limite_de_variables_sqlite(LIMITE_VARIABLES):
        Base.metadata.create_all(build_engine(database_path))
        repository = build_sqlite_decision_repository(database_path)
        project_id = _project_id(database_path)

        for indice in range(POR_ENCIMA_DEL_LIMITE):
            decision = repository.create_proposal(
                f"asunto-{indice}", project_id, f"contenido {indice}"
            )
            repository.approve_decision(decision.id)

        resultado = repository.list_current_decisions()

    assert len(resultado) == POR_ENCIMA_DEL_LIMITE
    assert {decision.current_revision.content for decision in resultado} == {
        f"contenido {indice}" for indice in range(POR_ENCIMA_DEL_LIMITE)
    }
