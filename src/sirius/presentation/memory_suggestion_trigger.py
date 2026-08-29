"""Automatic memory-suggestion trigger (SIRIUS-ARQ-0.2 §3.2/§3.6, M6).

Called by the surface that orchestrates sending a message — ``MainWindow``'s
``_on_finished`` — right after a turn ends, never by ``SendMessageUseCase``
itself (§0.1.2): a new capability is always an explicit, separate call, never
a side effect of sending a message.
"""

from __future__ import annotations

from sirius.application.propose_memory_suggestion import ProposeMemorySuggestionUseCase
from sirius.application.send_message import SendMessageResult
from sirius.domain.conversation import MessageStatus

__all__ = ["propose_suggestion_if_completed_with_one"]


def propose_suggestion_if_completed_with_one(
    result: SendMessageResult,
    propose_memory_suggestion_use_case: ProposeMemorySuggestionUseCase,
) -> None:
    """Propose ``result.memory_suggestion`` exactly when the turn completed with one.

    A turn that did not complete (``CANCELLED``/``FAILED``) or that completed
    with no proposal from the provider (``memory_suggestion is None``) never
    calls anything — the same safe default as an ordinary conversation turn
    never persisting a ``Memory`` on its own (§3.2's "nunca se autoguarda").
    """
    if result.outcome is not MessageStatus.COMPLETED:
        return
    if result.memory_suggestion is None:
        return
    propose_memory_suggestion_use_case.propose(
        result.memory_suggestion, message_id=result.sirius_message.id
    )
