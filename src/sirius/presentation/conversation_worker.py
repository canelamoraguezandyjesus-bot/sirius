"""Qt background worker for sending a message without blocking the GUI thread.

Follows the threading model in SIRIUS-ARQ-0.1 S10.2: the LLM call runs on a
dedicated ``QThreadPool``, never the GUI thread; deltas, the final result, or
an unexpected crash travel back to the main thread exclusively through Qt
signals (queued automatically across threads).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.send_message import SendMessageResult, SendMessageUseCase
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class SendMessageWorkerSignals(QObject):
    """Signals emitted by ``SendMessageWorker``."""

    delta = Signal(str)
    finished = Signal(object)
    crashed = Signal(str)


class SendMessageWorker(QRunnable):
    """Runs ``SendMessageUseCase.send_message`` on a worker thread."""

    def __init__(
        self,
        send_message_use_case: SendMessageUseCase,
        user_text: str,
        operation_id: str,
        extra_instructions: str = "",
    ) -> None:
        super().__init__()
        self._send_message_use_case = send_message_use_case
        self._user_text = user_text
        self._operation_id = operation_id
        self._extra_instructions = extra_instructions
        self.signals = SendMessageWorkerSignals()

    def run(self) -> None:
        _logger.info("Operación %s iniciada", self._operation_id)
        try:
            result: SendMessageResult = self._send_message_use_case.send_message(
                self._user_text,
                operation_id=self._operation_id,
                on_delta=self.signals.delta.emit,
                extra_instructions=self._extra_instructions,
            )
        except Exception as exc:  # A worker-boundary catch: report, never crash the pool thread.
            _logger.error(
                "Operación %s interrumpida por una excepción (%s)",
                self._operation_id,
                type(exc).__name__,
            )
            self.signals.crashed.emit(str(exc))
        else:
            _logger.info("Operación %s finalizada: %s", self._operation_id, result.outcome.value)
            self.signals.finished.emit(result)
