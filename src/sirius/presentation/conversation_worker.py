"""Qt background worker for sending a message without blocking the GUI thread.

Follows the threading model in SIRIUS-ARQ-0.1 S10.2: the LLM call runs on
``QThreadPool``, never the GUI thread; the result or the error travels back
to the main thread exclusively through Qt signals.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal

from sirius.application.send_message import SendMessageResult, SendMessageUseCase


class SendMessageWorkerSignals(QObject):
    """Signals emitted by ``SendMessageWorker``; queued automatically across threads."""

    succeeded = Signal(object)
    failed = Signal(str)


class SendMessageWorker(QRunnable):
    """Runs ``SendMessageUseCase.send_message`` on a worker thread."""

    def __init__(self, send_message_use_case: SendMessageUseCase, user_text: str) -> None:
        super().__init__()
        self._send_message_use_case = send_message_use_case
        self._user_text = user_text
        self.signals = SendMessageWorkerSignals()

    def run(self) -> None:
        try:
            result: SendMessageResult = self._send_message_use_case.send_message(self._user_text)
        except Exception as exc:  # A worker-boundary catch: report, never crash the pool thread.
            self.signals.failed.emit(str(exc))
        else:
            self.signals.succeeded.emit(result)
