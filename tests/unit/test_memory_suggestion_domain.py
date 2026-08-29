from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.domain.memory_suggestion import (
    MemorySuggestion,
    MemorySuggestionStatus,
    ensure_can_confirm,
    ensure_can_reject,
)


def _suggestion(status: MemorySuggestionStatus, *, suggestion_id: int = 1) -> MemorySuggestion:
    now = datetime.now(UTC)
    return MemorySuggestion(
        id=suggestion_id,
        content="Usar SQLite local para el motor de persistencia.",
        status=status,
        source_event_id=9,
        created_at=now,
        resolved_at=None if status is MemorySuggestionStatus.PENDING else now,
    )


def test_memory_suggestion_status_has_exactly_the_three_states_m4_needs() -> None:
    assert {member.value for member in MemorySuggestionStatus} == {
        "pending",
        "confirmed",
        "rejected",
    }


def test_ensure_can_confirm_accepts_a_pending_suggestion() -> None:
    ensure_can_confirm(_suggestion(MemorySuggestionStatus.PENDING))  # must not raise


def test_ensure_can_confirm_rejects_an_already_confirmed_suggestion() -> None:
    with pytest.raises(ValueError, match="Cannot confirm"):
        ensure_can_confirm(_suggestion(MemorySuggestionStatus.CONFIRMED))


def test_ensure_can_confirm_rejects_an_already_rejected_suggestion() -> None:
    """No hay camino de vuelta desde un estado terminal (§3.3): una sugerencia
    ya rechazada no puede confirmarse."""
    with pytest.raises(ValueError, match="Cannot confirm"):
        ensure_can_confirm(_suggestion(MemorySuggestionStatus.REJECTED))


def test_ensure_can_reject_accepts_a_pending_suggestion() -> None:
    ensure_can_reject(_suggestion(MemorySuggestionStatus.PENDING))  # must not raise


def test_ensure_can_reject_rejects_an_already_rejected_suggestion() -> None:
    with pytest.raises(ValueError, match="Cannot reject"):
        ensure_can_reject(_suggestion(MemorySuggestionStatus.REJECTED))


def test_ensure_can_reject_rejects_an_already_confirmed_suggestion() -> None:
    """No hay camino de vuelta desde un estado terminal (§3.3): una sugerencia
    ya confirmada no puede rechazarse."""
    with pytest.raises(ValueError, match="Cannot reject"):
        ensure_can_reject(_suggestion(MemorySuggestionStatus.CONFIRMED))
