"""Qt background worker for automatic criticality proposal (M21b, ADR-131).

Mirrors ``category_tagging_worker.py``: runs
``ProposeCriticalityUseCase.propose`` on the shared ``QThreadPool`` a caller
already owns, never the GUI thread. Unlike the category worker, this one
never writes anything — ``ProposeCriticalityUseCase`` only reads and
proposes (M21a, ADR-130); the only write remains an explicit
``SetCriticalityUseCase.set()`` call triggered by the user confirming
(never by this worker or its caller).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.propose_criticality import ProposeCriticalityUseCase
from sirius.application.set_criticality import CriticalityTargetKind
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class CriticalityProposalWorkerSignals(QObject):
    """Signals emitted by ``CriticalityProposalWorker``."""

    #: Emitted once ``run()`` finishes, carrying the ``kind``/``item_id`` it
    #: was asked about — so a caller can discard a proposal for a selection
    #: that has since changed — and the proposal itself (``Criticality`` or
    #: ``None``).
    finished = Signal(object, int, object)


class CriticalityProposalWorker(QRunnable):
    """Runs ``ProposeCriticalityUseCase.propose`` on a worker thread. Never
    writes."""

    def __init__(
        self,
        propose_criticality_use_case: ProposeCriticalityUseCase,
        kind: CriticalityTargetKind,
        item_id: int,
    ) -> None:
        super().__init__()
        self._propose_criticality_use_case = propose_criticality_use_case
        self._kind = kind
        self._item_id = item_id
        self.signals = CriticalityProposalWorkerSignals()

    def run(self) -> None:
        try:
            proposal = self._propose_criticality_use_case.propose(self._kind, self._item_id)
        except Exception as exc:  # A worker-boundary catch: report, never crash the pool thread.
            _logger.error(
                "Propuesta automática de criticidad interrumpida (%s, %s: %s)",
                self._kind.value,
                self._item_id,
                type(exc).__name__,
            )
            self.signals.finished.emit(self._kind, self._item_id, None)
        else:
            self.signals.finished.emit(self._kind, self._item_id, proposal)
