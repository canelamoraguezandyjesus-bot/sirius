"""Tests for ``CriticalityProposalWorker`` (M21b, ADR-131).

Calcado de ``test_category_tagging_worker.py``: real ``QThreadPool``, real
``SqliteMemoryRepository``/``SqliteDecisionRepository``, nunca Ollama — solo
un doble de ``CriticalityClassifierPort``. A diferencia del worker de
categoría, este nunca escribe: la única forma de comprobar "escribió o no"
es leer el repositorio después de que el worker termine y confirmar que la
criticidad sigue igual (``ProposeCriticalityUseCase`` ya lo prueba en
``tests/unit/test_propose_criticality_use_case.py``; aquí solo se prueba el
worker en sí — que ejecuta fuera del hilo de la GUI, que emite kind/id/
propuesta, y que un fallo del caso de uso se convierte en ``None`` en vez de
tumbar el hilo del pool).
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QThreadPool
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.application.propose_criticality import ProposeCriticalityUseCase
from sirius.application.set_criticality import CriticalityTargetKind
from sirius.domain.criticality import Criticality
from sirius.presentation.criticality_proposal_worker import CriticalityProposalWorker


class _BlockingClassifier:
    """A ``CriticalityClassifierPort`` double that blocks until the test
    releases it."""

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def propose(self, content: str) -> Criticality | None:
        self.started.set()
        released = self.release.wait(timeout=5)
        assert released, "the test never released the classifier"
        return Criticality.CRITICO


class _StaticClassifier:
    def __init__(self, result: Criticality | None) -> None:
        self._result = result

    def propose(self, content: str) -> Criticality | None:
        return self._result


class _RaisingClassifier:
    def propose(self, content: str) -> Criticality | None:
        raise RuntimeError("el clasificador falló")


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


@pytest.mark.gui
def test_worker_runs_off_the_gui_thread_and_never_writes(qtbot: QtBot, tmp_path: Path) -> None:
    """El worker nunca escribe (regla «Sirius propone, el usuario decide»,
    M18b/ADR-126/ADR-130): mientras está bloqueado a media clasificación, la
    criticidad sigue sin marcar; al terminar, sigue sin marcar — solo la
    señal ``finished`` lleva la propuesta."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    memory = memory_repository.create_memory("contenido sensible", "manual")
    classifier = _BlockingClassifier()
    propose_criticality_use_case = ProposeCriticalityUseCase(
        memory_repository, decision_repository, classifier
    )

    thread_pool = QThreadPool()
    worker = CriticalityProposalWorker(
        propose_criticality_use_case, CriticalityTargetKind.MEMORY, memory.id
    )
    thread_pool.start(worker)

    assert classifier.started.wait(timeout=5)
    assert memory_repository.get_memory(memory.id).criticality is None

    classifier.release.set()
    assert thread_pool.waitForDone(5000)

    assert memory_repository.get_memory(memory.id).criticality is None


@pytest.mark.gui
def test_worker_emits_kind_item_id_and_the_proposal_for_a_memory(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    memory = memory_repository.create_memory("contenido", "manual")
    propose_criticality_use_case = ProposeCriticalityUseCase(
        memory_repository, decision_repository, _StaticClassifier(Criticality.IMPORTANTE)
    )
    worker = CriticalityProposalWorker(
        propose_criticality_use_case, CriticalityTargetKind.MEMORY, memory.id
    )

    with qtbot.waitSignal(worker.signals.finished, timeout=5000) as blocker:
        QThreadPool.globalInstance().start(worker)

    assert blocker.args == [CriticalityTargetKind.MEMORY, memory.id, Criticality.IMPORTANTE]


@pytest.mark.gui
def test_worker_emits_kind_item_id_and_the_proposal_for_a_decision(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="en curso",
        blockers=(),
        next_step="siguiente paso",
    )
    decision = decision_repository.create_proposal("asunto", project.id, "contenido")
    propose_criticality_use_case = ProposeCriticalityUseCase(
        memory_repository, decision_repository, _StaticClassifier(Criticality.CRITICO)
    )
    worker = CriticalityProposalWorker(
        propose_criticality_use_case, CriticalityTargetKind.DECISION, decision.id
    )

    with qtbot.waitSignal(worker.signals.finished, timeout=5000) as blocker:
        QThreadPool.globalInstance().start(worker)

    assert blocker.args == [CriticalityTargetKind.DECISION, decision.id, Criticality.CRITICO]


@pytest.mark.gui
def test_worker_emits_none_when_the_classifier_cannot_decide(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    memory = memory_repository.create_memory("contenido", "manual")
    propose_criticality_use_case = ProposeCriticalityUseCase(
        memory_repository, decision_repository, _StaticClassifier(None)
    )
    worker = CriticalityProposalWorker(
        propose_criticality_use_case, CriticalityTargetKind.MEMORY, memory.id
    )

    with qtbot.waitSignal(worker.signals.finished, timeout=5000) as blocker:
        QThreadPool.globalInstance().start(worker)

    assert blocker.args == [CriticalityTargetKind.MEMORY, memory.id, None]


@pytest.mark.gui
def test_worker_emits_none_when_the_use_case_raises(qtbot: QtBot, tmp_path: Path) -> None:
    """Frontera del worker (calcado de ``CategoryTaggingWorker``): cualquier
    excepción del caso de uso se captura y se reporta como ``None`` en vez de
    tumbar el hilo del pool."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    memory = memory_repository.create_memory("contenido", "manual")
    propose_criticality_use_case = ProposeCriticalityUseCase(
        memory_repository, decision_repository, _RaisingClassifier()
    )
    worker = CriticalityProposalWorker(
        propose_criticality_use_case, CriticalityTargetKind.MEMORY, memory.id
    )

    with qtbot.waitSignal(worker.signals.finished, timeout=5000) as blocker:
        QThreadPool.globalInstance().start(worker)

    assert blocker.args == [CriticalityTargetKind.MEMORY, memory.id, None]
