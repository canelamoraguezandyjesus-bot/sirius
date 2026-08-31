"""M13 (§11.5, ADR-120/incidencia #489), segunda mitad: la ampliación por
categoría de ``_rank_via_staged_engine`` deja de enumerar la totalidad del
corpus vigente — integrada sobre M14 (índice de categoría buscable de
activación múltiple, con restricción de ámbito, incidencia #486).

Nota de arranque (ADR-120/§11.5-M13): el criterio de aceptación exige contar
filas devueltas por el repositorio, no invocaciones a
``list_current_memories()``/``list_current_decisions()`` — esas ya se
invocaban una sola vez por ``rank()`` antes de este encargo, así que esa
cuenta no cambiaría aunque el corpus completo se siguiera enumerando. Los
dobles de este archivo envuelven el repositorio real y cuentan ambas cosas:
cuántas veces se llama al método de enumeración completa (debe ser cero con
la puerta abierta) y cuántas filas devuelve el método filtrado por categoría
(debe depender del tamaño del subconjunto ya categorizado, no del tamaño del
corpus vigente completo).

Bajo M14, ``category_index_matches_query``/``category_index_activated`` no
comparan la categoría de un candidato contra un término concreto de la
consulta: activan la ampliación para **todo** candidato con categoría no
nula en cuanto la consulta contiene cualquier término del vocabulario
(``activa_categoria_buscable``, ADR-113) — a diferencia del intento anterior
a M14 (incidencia #485), que solo consultaba por el único término activado.
Por eso la consulta SQL filtra por el vocabulario completo
(``WHERE category IN (<vocabulario>)``), y el subconjunto que no crece con
el corpus es "todo lo ya categorizado", no "todo lo etiquetado con este
término" — de ahí que, en este archivo, lo que queda fuera de la categoría
sean memorias sin clasificar (``category is None``), no memorias con una
categoría distinta.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from sirius.adapters.persistence import staged_engine_candidate
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_decision_repository import (
    SqliteDecisionRepository,
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import (
    SqliteMemoryRepository,
    build_sqlite_memory_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.adapters.persistence.staged_engine_port import build_staged_engine_port
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.set_category import SetCategoryUseCase
from sirius.application.tag_category import CategoryTargetKind
from sirius.domain.decision import Decision
from sirius.domain.memory import Memory, MemoryRevision


class _ContandoMemoriasPorCategoria:
    """Envuelve un ``SqliteMemoryRepository`` real; delega todo, pero cuenta
    las filas que ``list_current_memories_by_category`` devuelve y cuántas
    veces se llama a ``list_current_memories`` (la enumeración completa)."""

    def __init__(self, real: SqliteMemoryRepository) -> None:
        self._real = real
        self.filas_por_categoria: list[int] = []
        self.veces_enumeracion_completa = 0

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        return self._real.create_memory(
            content,
            origin,
            source_event_id=source_event_id,
            subject_key=subject_key,
            project_id=project_id,
        )

    def get_memory(self, memory_id: int) -> Memory:
        return self._real.get_memory(memory_id)

    def list_current_memories(self) -> list[Memory]:
        self.veces_enumeracion_completa += 1
        return self._real.list_current_memories()

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        resultado = self._real.list_current_memories_by_category(categories)
        self.filas_por_categoria.append(len(resultado))
        return resultado

    def list_archived_memories(self) -> list[Memory]:
        return self._real.list_archived_memories()

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        return self._real.get_history(memory_id)

    def correct_memory(
        self, memory_id: int, content: str, origin: str, *, source_event_id: int | None = None
    ) -> Memory:
        return self._real.correct_memory(
            memory_id, content, origin, source_event_id=source_event_id
        )

    def archive_memory(self, memory_id: int) -> Memory:
        return self._real.archive_memory(memory_id)

    def delete_memory(self, memory_id: int) -> Memory:
        return self._real.delete_memory(memory_id)

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        return self._real.set_category(
            memory_id, category, observed_revision_version=observed_revision_version
        )

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        return self._real.set_user_category(memory_id, category)

    def list_uncategorized(self) -> list[Memory]:
        return self._real.list_uncategorized()


class _ContandoDecisionesPorCategoria:
    """Mirror de ``_ContandoMemoriasPorCategoria`` para
    ``SqliteDecisionRepository``."""

    def __init__(self, real: SqliteDecisionRepository) -> None:
        self._real = real
        self.filas_por_categoria: list[int] = []
        self.veces_enumeracion_completa = 0

    def create_proposal(
        self, subject: str, project_id: int, content: str, *, source_event_id: int | None = None
    ) -> Decision:
        return self._real.create_proposal(
            subject, project_id, content, source_event_id=source_event_id
        )

    def get_decision(self, decision_id: int) -> Decision:
        return self._real.get_decision(decision_id)

    def approve_decision(self, decision_id: int) -> Decision:
        return self._real.approve_decision(decision_id)

    def supersede_decision(
        self, superseded_decision_id: int, superseding_decision_id: int
    ) -> Decision:
        return self._real.supersede_decision(superseded_decision_id, superseding_decision_id)

    def list_current_decisions(self) -> list[Decision]:
        self.veces_enumeracion_completa += 1
        return self._real.list_current_decisions()

    def list_current_decisions_by_category(self, categories: Sequence[str]) -> list[Decision]:
        resultado = self._real.list_current_decisions_by_category(categories)
        self.filas_por_categoria.append(len(resultado))
        return resultado

    def list_proposed_decisions(self) -> list[Decision]:
        return self._real.list_proposed_decisions()

    def archive_decision(self, decision_id: int) -> Decision:
        return self._real.archive_decision(decision_id)

    def list_archived_decisions(self) -> list[Decision]:
        return self._real.list_archived_decisions()

    def get_superseding_decision(self, decision_id: int) -> Decision | None:
        return self._real.get_superseding_decision(decision_id)

    def set_category(
        self, decision_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        return self._real.set_category(
            decision_id, category, observed_revision_version=observed_revision_version
        )

    def set_user_category(self, decision_id: int, category: str) -> Decision:
        return self._real.set_user_category(decision_id, category)

    def list_uncategorized(self) -> list[Decision]:
        return self._real.list_uncategorized()


_VOCABULARY = frozenset({"trabajo", "personal"})

#: Elementos sin clasificar todavía (``category is None``): bastantes más que
#: los ya categorizados, para que un barrido completo del corpus y una
#: consulta filtrada por categoría devuelvan números de filas bien distintos.
SIN_CATEGORIA = 30
CATEGORIZADOS = 3


@pytest.mark.integration
def test_solo_por_categoria_no_enumera_el_corpus_completo(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto de prueba", "objetivo", state_summary="estado", blockers=(), next_step="siguiente"
    )
    project_repository.complete_active_project(project.id)
    project_repository.create_project(
        "Proyecto activo", "objetivo", state_summary="estado", blockers=(), next_step="siguiente"
    )
    unit_of_work = build_sqlite_unit_of_work(database_path)

    real_memory_repository = build_sqlite_memory_repository(database_path)
    real_decision_repository = build_sqlite_decision_repository(database_path)
    tag_use_case = SetCategoryUseCase(real_memory_repository, real_decision_repository)

    # Sin clasificar: nunca deben aparecer en la consulta filtrada por
    # categoría, bajo M14 tanto como bajo M9 (``category is None`` nunca
    # coincide).
    for indice in range(SIN_CATEGORIA):
        SaveManualMemoryUseCase(unit_of_work).save(f"contenido neutro sin relacion alguna {indice}")

    for indice in range(CATEGORIZADOS):
        memoria = SaveManualMemoryUseCase(unit_of_work).save(
            f"contenido neutro tambien sin relacion {indice}"
        )
        tag_use_case.set(CategoryTargetKind.MEMORY, memoria.id, "trabajo")

    memory_repository = _ContandoMemoriasPorCategoria(real_memory_repository)
    decision_repository = _ContandoDecisionesPorCategoria(real_decision_repository)

    puerto = build_staged_engine_port(database_path)
    candidato = staged_engine_candidate.candidato()
    try:
        use_case = RankRelevantKnowledgeUseCase(
            memory_repository=memory_repository,
            decision_repository=decision_repository,
            project_repository=build_sqlite_project_repository(database_path),
            knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
            category_vocabulary=_VOCABULARY,
            category_matching_enabled=True,
            staged_engine_port=puerto,
            staged_engine_candidate=candidato,
        )
        # "trabajo" activa el índice de categoría (M14: cualquier término del
        # vocabulario basta) y no aparece en el contenido de ninguna
        # memoria: el motor por etapas no admite nada por sí mismo, así que
        # todo lo que ``rank()`` devuelva llega por el bloque de ampliación
        # por categoría.
        resultado = use_case.rank("trabajo")
    finally:
        puerto.close()

    assert len(resultado) == CATEGORIZADOS
    assert all(candidate.category_match is True for candidate in resultado)

    # El criterio literal: contar filas, no invocaciones. El repositorio
    # nunca enumera el corpus vigente completo (0 invocaciones), y la única
    # consulta filtrada por categoría devuelve exactamente el subconjunto ya
    # categorizado (3 filas), no las 33 memorias vigentes que hay en total.
    assert memory_repository.veces_enumeracion_completa == 0
    assert memory_repository.filas_por_categoria == [CATEGORIZADOS]
    assert decision_repository.veces_enumeracion_completa == 0
    # Ninguna decisión existe en este caso; la consulta por categoría sigue
    # ejecutándose (mismo camino que memorias) y devuelve cero filas.
    assert decision_repository.filas_por_categoria == [0]


@pytest.mark.integration
def test_filas_por_categoria_depende_del_subconjunto_no_del_total(tmp_path: Path) -> None:
    """Repite el escenario anterior con un corpus bastante mayor sin
    clasificar, y confirma que el número de filas devueltas por categoría no
    cambia: depende del subconjunto ya categorizado, no del tamaño total del
    corpus vigente (§11.5-M13, literal)."""
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    unit_of_work = build_sqlite_unit_of_work(database_path)

    real_memory_repository = build_sqlite_memory_repository(database_path)
    real_decision_repository = build_sqlite_decision_repository(database_path)
    tag_use_case = SetCategoryUseCase(real_memory_repository, real_decision_repository)

    for indice in range(CATEGORIZADOS):
        memoria = SaveManualMemoryUseCase(unit_of_work).save(f"contenido neutro objetivo {indice}")
        tag_use_case.set(CategoryTargetKind.MEMORY, memoria.id, "trabajo")

    memory_repository = _ContandoMemoriasPorCategoria(real_memory_repository)

    with_few_outside = memory_repository.list_current_memories_by_category(tuple(_VOCABULARY))
    assert len(with_few_outside) == CATEGORIZADOS

    # Un corpus mucho mayor sin clasificar, añadido después.
    for indice in range(SIN_CATEGORIA * 5):
        SaveManualMemoryUseCase(unit_of_work).save(
            f"contenido neutro adicional sin relacion {indice}"
        )

    with_many_outside = memory_repository.list_current_memories_by_category(tuple(_VOCABULARY))
    assert len(with_many_outside) == CATEGORIZADOS

    assert memory_repository.filas_por_categoria == [CATEGORIZADOS, CATEGORIZADOS]
