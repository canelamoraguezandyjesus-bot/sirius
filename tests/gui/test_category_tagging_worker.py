"""Tests for ``CategoryTaggingWorker`` (D7, SIRIUS-ARQ-0.2 §6.1/§8-M8).

Real ``QThreadPool``, real ``SqliteMemoryRepository``, never Ollama — only a
test double of ``CategoryClassifierPort`` that deliberately blocks until
released. This is what pins §8-M8's acceptance criterion that saving a
memory or a decision never waits for the tagging worker to finish.
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
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.tag_category import CategoryTargetKind, TagCategoryUseCase
from sirius.presentation.category_tagging_worker import CategoryTaggingWorker


class _BlockingClassifier:
    """A ``CategoryClassifierPort`` double that blocks until the test releases it."""

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def classify(self, content: str) -> str | None:
        self.started.set()
        released = self.release.wait(timeout=5)
        assert released, "the test never released the classifier"
        return "trabajo"


class _StaticClassifier:
    def __init__(self, result: str | None) -> None:
        self._result = result

    def classify(self, content: str) -> str | None:
        return self._result


def _bootstrap(database_path: Path) -> None:
    Base.metadata.create_all(build_engine(database_path))


@pytest.mark.gui
def test_saving_a_memory_never_waits_for_the_tagging_worker(qtbot: QtBot, tmp_path: Path) -> None:
    """D7 punto 2: guardar nunca espera al etiquetado — el resultado de
    guardado ya está disponible antes de que se resuelva el etiquetado,
    verificado con un doble del puerto que bloquea deliberadamente hasta que
    la prueba lo libera."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    classifier = _BlockingClassifier()
    tag_category_use_case = TagCategoryUseCase(memory_repository, decision_repository, classifier)
    save_use_case = SaveManualMemoryUseCase(build_sqlite_unit_of_work(database_path))

    # The save use case runs to completion, its result fully usable, with no
    # worker enqueued yet at all — the strongest form of "never waits".
    memory = save_use_case.save("preferencia guardada")
    assert memory.current_revision.content == "preferencia guardada"

    thread_pool = QThreadPool()
    worker = CategoryTaggingWorker(tag_category_use_case, CategoryTargetKind.MEMORY, memory.id)
    thread_pool.start(worker)

    assert classifier.started.wait(timeout=5)
    # The worker is blocked mid-classification; the category is still unset.
    assert memory_repository.get_memory(memory.id).category is None

    classifier.release.set()
    assert thread_pool.waitForDone(5000)

    assert memory_repository.get_memory(memory.id).category == "trabajo"


@pytest.mark.gui
def test_worker_emits_finished_with_whether_it_wrote(qtbot: QtBot, tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    memory = memory_repository.create_memory("contenido", "manual")
    tag_category_use_case = TagCategoryUseCase(
        memory_repository, decision_repository, _StaticClassifier("personal")
    )
    worker = CategoryTaggingWorker(tag_category_use_case, CategoryTargetKind.MEMORY, memory.id)

    with qtbot.waitSignal(worker.signals.finished, timeout=5000) as blocker:
        QThreadPool.globalInstance().start(worker)

    assert blocker.args == [True]
    assert memory_repository.get_memory(memory.id).category == "personal"


@pytest.mark.gui
def test_worker_emits_finished_false_when_the_classifier_could_not_decide(
    qtbot: QtBot, tmp_path: Path
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory_repository = build_sqlite_memory_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    memory = memory_repository.create_memory("contenido", "manual")
    tag_category_use_case = TagCategoryUseCase(
        memory_repository, decision_repository, _StaticClassifier(None)
    )
    worker = CategoryTaggingWorker(tag_category_use_case, CategoryTargetKind.MEMORY, memory.id)

    with qtbot.waitSignal(worker.signals.finished, timeout=5000) as blocker:
        QThreadPool.globalInstance().start(worker)

    assert blocker.args == [False]
    assert memory_repository.get_memory(memory.id).category is None
