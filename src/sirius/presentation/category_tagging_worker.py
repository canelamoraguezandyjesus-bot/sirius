"""Qt background worker for automatic category classification (D7,
SIRIUS-ARQ-0.2 §6.1).

Mirrors ``conversation_worker.py``/``backup_worker.py``: runs
``TagCategoryUseCase.tag`` on the shared ``QThreadPool`` a caller already
owns, never the GUI thread. A caller enqueues this worker only *after* the
save/confirm/propose/correct use case that produced ``item_id`` has already
returned its result — never inside that use case's own call, and never
inside its ``UnitOfWork`` transaction (§6.1 point 2): this module has no
knowledge of, and no dependency on, when or why it gets enqueued.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.tag_category import CategoryTargetKind, TagCategoryUseCase
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class CategoryTaggingWorkerSignals(QObject):
    """Signals emitted by ``CategoryTaggingWorker``."""

    #: Emitted once ``run()`` finishes, carrying whether a category was
    #: actually written (D7 point 2: ``KnowledgeWidget.refresh()`` only ever
    #: needs to react when something changed).
    finished = Signal(bool)


class CategoryTaggingWorker(QRunnable):
    """Runs ``TagCategoryUseCase.tag`` on a worker thread."""

    def __init__(
        self, tag_category_use_case: TagCategoryUseCase, kind: CategoryTargetKind, item_id: int
    ) -> None:
        super().__init__()
        self._tag_category_use_case = tag_category_use_case
        self._kind = kind
        self._item_id = item_id
        self.signals = CategoryTaggingWorkerSignals()

    def run(self) -> None:
        try:
            tagged = self._tag_category_use_case.tag(self._kind, self._item_id)
        except Exception as exc:  # A worker-boundary catch: report, never crash the pool thread.
            _logger.error(
                "Etiquetado automático de categoría interrumpido (%s, %s: %s)",
                self._kind.value,
                self._item_id,
                type(exc).__name__,
            )
            self.signals.finished.emit(False)
        else:
            self.signals.finished.emit(tagged)
