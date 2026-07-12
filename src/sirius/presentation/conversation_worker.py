"""Qt background worker for sending a message without blocking the GUI thread.

Follows the threading model in SIRIUS-ARQ-0.1 S10.2: the LLM call runs on a
dedicated ``QThreadPool``, never the GUI thread; deltas, the final result, or
an unexpected crash travel back to the main thread exclusively through Qt
signals (queued automatically across threads).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.send_message import SendMessageResult, SendMessageUseCase


class SendMessageWorkerSignals(QObject):
    """Signals emitted by ``SendMessageWorker``."""

    delta = Signal(str)
    finished = Signal(object)
    crashed = Signal(str)


class SendMessageWorker(QRunnable):
    """Runs ``SendMessageUseCase.send_message`` on a worker thread."""

    def __init__(
        self, send_message_use_case: SendMessageUseCase, user_text: str, operation_id: str
    ) -> None:
        super().__init__()
        self._send_message_use_case = send_message_use_case
        self._user_text = user_text
        self._operation_id = operation_id
        self.signals = SendMessageWorkerSignals()

    def run(self) -> None:
        try:
            result: SendMessageResult = self._send_message_use_case.send_message(
                self._user_text,
                operation_id=self._operation_id,
                on_delta=self.signals.delta.emit,
            )
        except Exception as exc:  # A worker-boundary catch: report, never crash the pool thread.
            self.signals.crashed.emit(str(exc))
        else:
            self.signals.finished.emit(result)
