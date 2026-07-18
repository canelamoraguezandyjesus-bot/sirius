from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.domain.decision import (
    Decision,
    DecisionRevision,
    DecisionStatus,
    ensure_can_approve,
    ensure_valid_content,
    ensure_valid_subject,
)


def _decision(status: DecisionStatus) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=1,
        decision_id=1,
        version=1,
        content="Usar SQLite local en vez de un servidor remoto.",
        source_event_id=9,
        created_at=now,
    )
    return Decision(
        id=1,
        subject="Motor de persistencia",
        project_id=1,
        status=status,
        current_revision=revision,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize("subject", ["", "   ", "\t\n"])
def test_ensure_valid_subject_rejects_empty_subject(subject: str) -> None:
    with pytest.raises(ValueError, match="non-empty subject"):
        ensure_valid_subject(subject)


def test_ensure_valid_subject_accepts_non_empty_subject() -> None:
    ensure_valid_subject("Motor de persistencia")


@pytest.mark.parametrize("content", ["", "   ", "\t\n"])
def test_ensure_valid_content_rejects_empty_content(content: str) -> None:
    with pytest.raises(ValueError, match="non-empty content"):
        ensure_valid_content(content)


def test_ensure_valid_content_accepts_non_empty_content() -> None:
    ensure_valid_content("Usar SQLite local.")


def test_ensure_can_approve_accepts_a_proposed_decision() -> None:
    ensure_can_approve(_decision(DecisionStatus.PROPOSED))


def test_ensure_can_approve_rejects_an_already_approved_decision() -> None:
    with pytest.raises(ValueError, match="Cannot approve"):
        ensure_can_approve(_decision(DecisionStatus.APPROVED))


def test_decision_status_has_only_the_two_states_b4b_needs() -> None:
    assert {member.value for member in DecisionStatus} == {"proposed", "approved"}
