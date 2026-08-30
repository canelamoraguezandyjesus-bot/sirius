"""Unit tests for ``sirius.adapters.persistence.staged_engine_port``
(issue #457/ADR-109/ADR-110): the ``PuertoDeRecuperacion`` adapter over the
real Sirius 0.1 schema. Uses a real, migrated SQLite database (like
``tests/integration/test_rank_relevant_knowledge.py``) because the queries
under test are SQL, not pure Python.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.persistence.database import build_engine, build_session_factory
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.adapters.persistence.staged_engine_port import (
    IdentificadorInvalidoError,
    StagedEnginePort,
    build_staged_engine_port,
)
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.staged_engine_contracts import SIN_EJES, Clase, EjesDeclarados


def _bootstrap(database_path: Path) -> None:
    upgrade_to_head(database_path)
    build_sqlite_project_repository(database_path).ensure_bootstrap_project()


def test_por_termino_lexico_finds_a_saved_memory(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory = SaveManualMemoryUseCase(build_sqlite_unit_of_work(database_path)).save(
        "terminounicoparabuscar en la memoria"
    )

    puerto = build_staged_engine_port(database_path)
    try:
        encontrados = puerto.por_termino_lexico(["terminounicoparabuscar"])
    finally:
        puerto.close()

    assert [i.id for i in encontrados] == [f"{Clase.MEMORIA.value}:{memory.id}"]
    assert encontrados[0].ejes == SIN_EJES


def test_por_termino_lexico_sin_terminos_utiles_no_ejecuta_consulta(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.por_termino_lexico(["", "  "]) == ()
    finally:
        puerto.close()


def test_por_clave_exacta_finds_by_subject_key(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project = build_sqlite_project_repository(database_path).create_project(
        "Proyecto de prueba", "objetivo", state_summary="", blockers=(), next_step=""
    )
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "texto cualquiera", subject_key="faro-costa-unico", project_id=project.id
    )

    puerto = build_staged_engine_port(database_path)
    try:
        encontrados = puerto.por_clave_exacta(["faro-costa-unico"])
    finally:
        puerto.close()

    assert [i.id for i in encontrados] == [f"{Clase.MEMORIA.value}:{memory.id}"]


def test_por_prefijo_de_sujeto_rejects_a_prefix_shorter_than_three_chars(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project = build_sqlite_project_repository(database_path).create_project(
        "Proyecto de prueba", "objetivo", state_summary="", blockers=(), next_step=""
    )
    unit_of_work = build_sqlite_unit_of_work(database_path)
    SaveManualMemoryUseCase(unit_of_work).save(
        "texto", subject_key="fa-algo-unico", project_id=project.id
    )

    puerto = build_staged_engine_port(database_path)
    try:
        # "fa" tiene menos de 3 caracteres: no es una relacion, es un barrido.
        assert puerto.por_prefijo_de_sujeto(["fa"]) == ()
    finally:
        puerto.close()


def test_por_identificadores_declares_absent_ids_without_raising(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("texto cualquiera")

    puerto = build_staged_engine_port(database_path)
    try:
        materializacion = puerto.por_identificadores(
            [f"{Clase.MEMORIA.value}:{memory.id}", f"{Clase.MEMORIA.value}:999999"]
        )
    finally:
        puerto.close()

    assert [i.id for i in materializacion.items] == [f"{Clase.MEMORIA.value}:{memory.id}"]
    assert materializacion.ausentes == (f"{Clase.MEMORIA.value}:999999",)
    assert materializacion.completa is False


def test_por_identificadores_rejects_a_malformed_identifier(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    puerto = build_staged_engine_port(database_path)
    try:
        with pytest.raises(IdentificadorInvalidoError):
            puerto.por_identificadores(["no-es-un-identificador"])
    finally:
        puerto.close()


def test_historial_y_fuentes_always_empty(tmp_path: Path) -> None:
    """``E4`` no tiene objetivo real en Sirius 0.1: ``RankedKnowledge`` solo
    modela ``Memory``/``Decision`` (ver docstring del módulo bajo prueba)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.historial_y_fuentes(["cualquiera"]) == ()
    finally:
        puerto.close()


def test_ejes_por_identidad_overrides_sin_ejes_for_a_declared_item(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory = SaveManualMemoryUseCase(build_sqlite_unit_of_work(database_path)).save(
        "terminounicoconejes en la memoria"
    )
    identidad = f"{Clase.MEMORIA.value}:{memory.id}"
    ejes_declarados = EjesDeclarados(ambito="GLOBAL")

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    puerto = StagedEnginePort(
        session_factory, engine, ejes_por_identidad={identidad: ejes_declarados}
    )
    try:
        (encontrado,) = puerto.por_termino_lexico(["terminounicoconejes"])
    finally:
        puerto.close()

    assert encontrado.ejes == ejes_declarados
