"""M13 (§11.5, ADR-122), primera mitad: ``StagedEnginePort.por_clave_exacta``/
``por_prefijo_de_sujeto`` en consulta por lote, en vez de dos consultas SQL
por cada clave o prefijo dentro de un bucle Python.

Nota de arranque (ADR-122): el criterio de aceptación de §11.5-M13 exige un
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

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session

from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.models import MemoryModel, MemoryRevisionModel
from sirius.adapters.persistence.sqlite_decision_repository import build_sqlite_decision_repository
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.staged_engine_port import (
    LIMITE_POR_CONSULTA,
    LIMITE_POR_PREFIJO,
    StagedEnginePort,
    build_staged_engine_port,
)
from sirius.domain.memory import MemoryStatus
from sirius.domain.staged_engine_contracts import ItemCanonico


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


@pytest.mark.integration
def test_por_clave_exacta_conserva_cota_independiente_por_clave(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAUDE-M13-001/CODEX-001 (ronda 2, incidencia #485): antes del
    batching, cada clave ejecutaba su propia consulta con su propio
    ``LIMIT`` (``LIMITE_POR_CONSULTA``), garantizando una cota de filas
    independiente por clave sin importar cuántas devolvieran las demás
    claves de la misma llamada. El batching de la ronda 1 lo sustituyó por
    un único ``LIMIT`` combinado (``LIMITE_POR_CONSULTA * len(utiles)``)
    sobre ``ORDER BY id`` global: una clave con más coincidencias que otra y
    cuyas filas preceden en id puede agotarlo entero y excluir a la otra
    clave por completo. Verificado por mutación: restaurando el ``LIMIT``
    combinado en vez del ``UNION ALL`` por clave, esta prueba falla porque
    el id de ``clave-b`` no aparece entre los ids seleccionados.

    Se intercepta ``_por_ids_mixtos`` (sin tocarlo) para leer los ids que la
    etapa de selección de ``por_clave_exacta`` produjo, en vez de inspeccionar
    la tupla final que ese método devuelve: la tupla final pasa además por el
    recorte agregado ``[:LIMITE_POR_CONSULTA]`` de ``_por_ids_mixtos`` —
    preexistente a esta incidencia, fuera de su alcance (``limits_correccion``
    prohíbe tocar nada fuera de ``por_clave_exacta``/``por_prefijo_de_sujeto``
    y su prueba) — que con ≥2 claves y una de ellas por encima de
    ``LIMITE_POR_CONSULTA`` excluiría a la clave débil de la tupla final por
    sí solo, con o sin este arreglo: matemáticamente, disparar el defecto de
    la etapa de selección exige que la suma de coincidencias de la llamada
    supere ``LIMITE_POR_CONSULTA * len(utiles) >= 2 * LIMITE_POR_CONSULTA``,
    lo que ya excede el recorte agregado posterior de
    ``LIMITE_POR_CONSULTA``; solo mirando la etapa de selección en aislado se
    puede distinguir el código corregido del código con el defecto."""
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    project_id = _project_id(database_path)
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)

    now = datetime.now(UTC).replace(tzinfo=None)
    total_a = LIMITE_POR_CONSULTA * 2 + 8
    with session_scope(session_factory) as session:
        memorias_a = [
            MemoryModel(
                status=MemoryStatus.CURRENT,
                subject_key="clave-a",
                project_id=project_id,
                created_at=now,
                updated_at=now,
            )
            for _ in range(total_a)
        ]
        memoria_b = MemoryModel(
            status=MemoryStatus.CURRENT,
            subject_key="clave-b",
            project_id=project_id,
            created_at=now,
            updated_at=now,
        )
        session.add_all([*memorias_a, memoria_b])
        session.flush()
        id_b = memoria_b.id

    ids_seleccionados: list[tuple[str, int]] = []

    def _capturar_sin_materializar(
        self: StagedEnginePort, session: Session, pares: Sequence[tuple[str, int]]
    ) -> list[ItemCanonico]:
        ids_seleccionados.extend(pares)
        return []

    monkeypatch.setattr(StagedEnginePort, "_por_ids_mixtos", _capturar_sin_materializar)

    puerto = build_staged_engine_port(database_path)
    try:
        puerto.por_clave_exacta(["clave-a", "clave-b"])
    finally:
        puerto.close()

    ids_memoria_seleccionados = {i for k, i in ids_seleccionados if k == "memory"}
    assert id_b in ids_memoria_seleccionados, (
        "el id de 'clave-b' no aparece entre los ids que la etapa de "
        "selección de por_clave_exacta produjo: el volumen de coincidencias "
        "de 'clave-a' desplazó a 'clave-b' dentro de la misma llamada"
    )
    ids_clave_a_seleccionados = ids_memoria_seleccionados - {id_b}
    assert len(ids_clave_a_seleccionados) <= LIMITE_POR_CONSULTA, (
        "'clave-a' aportó más ids de los que su propia cota (LIMITE_POR_CONSULTA) le permite"
    )


@pytest.mark.integration
def test_por_prefijo_de_sujeto_conserva_cota_independiente_por_prefijo(tmp_path: Path) -> None:
    """CLAUDE-M13-001/CODEX-001 (ronda 2, incidencia #485): reproducción de
    la reportada por Codex en la PR #487 — una tabla con 128 sujetos
    ``aaa-*`` (más que ``LIMITE_POR_PREFIJO``) seguidos de uno ``bbb-*``: con
    el ``LIMIT`` combinado que introdujo el batching, ``por_prefijo_de_sujeto
    (("aaa-", "bbb-"))`` devuelve los 128 ``aaa-*`` y omite el ``bbb-*``,
    alterando qué candidatos se admiten frente al invariante «sin alterar qué
    se admite ni en qué orden» de ADR-122. A diferencia de
    ``por_clave_exacta``, aquí el recorte agregado y preexistente de
    ``_por_ids_mixtos`` (``LIMITE_POR_CONSULTA`` = 512) no interfiere: el
    total de coincidencias de esta llamada (~129) queda muy por debajo, así
    que la tupla final que devuelve el método basta para observar el
    arreglo. Verificado por mutación: restaurando el ``LIMIT`` combinado
    (``LIMITE_POR_PREFIJO * len(utiles)``) en vez del ``UNION ALL`` por
    prefijo, esta prueba falla porque ``bbb-sujeto`` desaparece del
    resultado."""
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    project_id = _project_id(database_path)
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)

    now = datetime.now(UTC).replace(tzinfo=None)
    total_aaa = LIMITE_POR_PREFIJO * 2
    with session_scope(session_factory) as session:
        memorias_aaa = [
            MemoryModel(
                status=MemoryStatus.CURRENT,
                subject_key=f"aaa-{indice}",
                project_id=project_id,
                created_at=now,
                updated_at=now,
            )
            for indice in range(total_aaa)
        ]
        memoria_bbb = MemoryModel(
            status=MemoryStatus.CURRENT,
            subject_key="bbb-sujeto",
            project_id=project_id,
            created_at=now,
            updated_at=now,
        )
        session.add_all([*memorias_aaa, memoria_bbb])
        session.flush()
        for indice, memoria in enumerate([*memorias_aaa, memoria_bbb]):
            session.add(
                MemoryRevisionModel(
                    memory_id=memoria.id,
                    version=1,
                    content=f"contenido {indice}",
                    origin="prueba",
                    is_current=True,
                    created_at=now,
                )
            )
    engine.dispose()

    puerto = build_staged_engine_port(database_path)
    try:
        resultado = puerto.por_prefijo_de_sujeto(["aaa-", "bbb-"])
    finally:
        puerto.close()

    claves_presentes = {item.subject_key for item in resultado}
    assert "bbb-sujeto" in claves_presentes, (
        "'bbb-sujeto' desapareció del resultado: el volumen de coincidencias "
        "del prefijo 'aaa-' desplazó al prefijo 'bbb-' dentro de la misma "
        "llamada"
    )
    ids_aaa_presentes = [item for item in resultado if item.subject_key != "bbb-sujeto"]
    assert len(ids_aaa_presentes) <= LIMITE_POR_PREFIJO, (
        "el prefijo 'aaa-' aportó más filas de las que su propia cota "
        "(LIMITE_POR_PREFIJO) le permite"
    )
