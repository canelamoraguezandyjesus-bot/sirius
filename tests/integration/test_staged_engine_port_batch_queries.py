"""M13 (§11.5, ADR-120), primera mitad: ``StagedEnginePort.por_clave_exacta``/
``por_prefijo_de_sujeto`` en consulta por lote, en vez de dos consultas SQL
por cada clave o prefijo dentro de un bucle Python.

Nota de arranque (ADR-120): el criterio de aceptación de §11.5-M13 exige un
contador de consultas SQL reales sobre SQLite, no de invocaciones al método
del puerto — mismo instrumento (``event.listen(Engine,
"before_cursor_execute", ...)``) que
``tests/integration/test_memory_decision_list_query_count.py`` ya usa para
ADR-008. Verificado por mutación: restaurando el bucle ``for clave in
utiles``/``for prefijo in utiles`` con dos ``session.execute`` por
iteración, las aserciones de este archivo fallan porque el conteo de
consultas crece con el número de claves/prefijos; con el arreglo, no.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, event

from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_decision_repository import build_sqlite_decision_repository
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.staged_engine_port import build_staged_engine_port


@contextmanager
def _contar_consultas() -> Iterator[list[str]]:
    """Cuenta cada sentencia SQL ejecutada a través de SQLAlchemy en el
    bloque (mismo instrumento que ADR-008 ya usa)."""
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


# Dos tamaños bien distintos, ambos dentro de ``ARGUMENTOS_MAXIMOS`` (16): si
# el número de consultas dependiera de *n*, estos dos conteos serían
# distintos.
POCAS = 3
MUCHAS = 15


@pytest.mark.integration
def test_por_clave_exacta_no_crece_con_el_numero_de_claves(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    project_id = _project_id(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)

    for indice in range(MUCHAS):
        memory_repository.create_memory(
            f"contenido {indice}",
            origin="prueba",
            subject_key=f"clave-{indice}",
            project_id=project_id,
        )
        decision_repository.create_proposal(f"clave-{indice}", project_id, f"contenido {indice}")

    puerto = build_staged_engine_port(database_path)
    try:
        with _contar_consultas() as sentencias:
            resultado_pocas = puerto.por_clave_exacta([f"clave-{i}" for i in range(POCAS)])
        consultas_pocas = len(sentencias)
        assert len(resultado_pocas) == 2 * POCAS  # una memoria y una decisión por clave

        with _contar_consultas() as sentencias:
            resultado_muchas = puerto.por_clave_exacta([f"clave-{i}" for i in range(MUCHAS)])
        consultas_muchas = len(sentencias)
        assert len(resultado_muchas) == 2 * MUCHAS
    finally:
        puerto.close()

    assert consultas_muchas == consultas_pocas, (
        f"por_clave_exacta() ejecutó {consultas_pocas} consultas para {POCAS} "
        f"claves y {consultas_muchas} para {MUCHAS}: el número de consultas "
        "depende del número de claves de la llamada."
    )


@pytest.mark.integration
def test_por_prefijo_de_sujeto_no_crece_con_el_numero_de_prefijos(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    project_id = _project_id(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)

    for indice in range(MUCHAS):
        memory_repository.create_memory(
            f"contenido {indice}",
            origin="prueba",
            subject_key=f"pref{indice}-sujeto",
            project_id=project_id,
        )
        decision_repository.create_proposal(
            f"pref{indice}-sujeto", project_id, f"contenido {indice}"
        )

    puerto = build_staged_engine_port(database_path)
    try:
        with _contar_consultas() as sentencias:
            resultado_pocos = puerto.por_prefijo_de_sujeto([f"pref{i}-" for i in range(POCAS)])
        consultas_pocas = len(sentencias)
        assert len(resultado_pocos) == 2 * POCAS

        with _contar_consultas() as sentencias:
            resultado_muchos = puerto.por_prefijo_de_sujeto([f"pref{i}-" for i in range(MUCHAS)])
        consultas_muchas = len(sentencias)
        assert len(resultado_muchos) == 2 * MUCHAS
    finally:
        puerto.close()

    assert consultas_muchas == consultas_pocas, (
        f"por_prefijo_de_sujeto() ejecutó {consultas_pocas} consultas para "
        f"{POCAS} prefijos y {consultas_muchas} para {MUCHAS}: el número de "
        "consultas depende del número de prefijos de la llamada."
    )
