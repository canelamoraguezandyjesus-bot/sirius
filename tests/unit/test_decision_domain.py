from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius.domain.decision import (
    Decision,
    DecisionRevision,
    DecisionStatus,
    ensure_can_approve,
    ensure_can_archive,
    ensure_can_supersede,
    ensure_valid_content,
    ensure_valid_subject,
)


def _decision(
    status: DecisionStatus,
    *,
    decision_id: int = 1,
    subject: str = "Motor de persistencia",
    project_id: int = 1,
) -> Decision:
    now = datetime.now(UTC)
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content="Usar SQLite local en vez de un servidor remoto.",
        source_event_id=9,
        created_at=now,
    )
    return Decision(
        id=decision_id,
        subject=subject,
        project_id=project_id,
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


def test_decision_status_has_the_four_states_b4b_b4c_and_b4d_need() -> None:
    assert {member.value for member in DecisionStatus} == {
        "proposed",
        "approved",
        "superseded",
        "archived",
    }


def test_ensure_can_supersede_accepts_an_approved_decision_superseded_by_a_proposed_one() -> None:
    superseded = _decision(DecisionStatus.APPROVED, decision_id=1)
    superseding = _decision(DecisionStatus.PROPOSED, decision_id=2)

    ensure_can_supersede(superseded, superseding)  # must not raise


def test_ensure_can_supersede_rejects_self_supersession() -> None:
    same = _decision(DecisionStatus.APPROVED, decision_id=1)

    with pytest.raises(ValueError, match="cannot supersede itself"):
        ensure_can_supersede(same, same)


def test_ensure_can_supersede_rejects_a_superseded_decision_that_is_not_approved() -> None:
    superseded = _decision(DecisionStatus.PROPOSED, decision_id=1)
    superseding = _decision(DecisionStatus.PROPOSED, decision_id=2)

    with pytest.raises(ValueError, match="Cannot supersede"):
        ensure_can_supersede(superseded, superseding)


def test_ensure_can_supersede_accepts_an_already_approved_superseding_decision() -> None:
    """Antes se rechazaba, y ese rechazo ERA el defecto: si el usuario aprobaba
    la decisión nueva antes de ordenar la sustitución, las dos se quedaban
    vigentes con el mismo peso y sin vínculo."""
    superseded = _decision(DecisionStatus.APPROVED, decision_id=1)
    superseding = _decision(DecisionStatus.APPROVED, decision_id=2)

    ensure_can_supersede(superseded, superseding)


@pytest.mark.parametrize("status", [DecisionStatus.SUPERSEDED, DecisionStatus.ARCHIVED])
def test_ensure_can_supersede_rejects_a_superseding_decision_that_is_not_current(
    status: DecisionStatus,
) -> None:
    """Ni una decisión ya sustituida ni una archivada son vigentes, así que
    ninguna puede pasar a ser la sustituta."""
    superseded = _decision(DecisionStatus.APPROVED, decision_id=1)
    superseding = _decision(status, decision_id=2)

    with pytest.raises(ValueError, match="PROPOSED or APPROVED decision can supersede"):
        ensure_can_supersede(superseded, superseding)


def test_ensure_can_supersede_rejects_a_mismatched_subject() -> None:
    superseded = _decision(DecisionStatus.APPROVED, decision_id=1, subject="Motor de persistencia")
    superseding = _decision(DecisionStatus.PROPOSED, decision_id=2, subject="Otro asunto")

    with pytest.raises(ValueError, match="same subject and project"):
        ensure_can_supersede(superseded, superseding)


def test_ensure_can_supersede_rejects_a_mismatched_project() -> None:
    superseded = _decision(DecisionStatus.APPROVED, decision_id=1, project_id=1)
    superseding = _decision(DecisionStatus.PROPOSED, decision_id=2, project_id=2)

    with pytest.raises(ValueError, match="same subject and project"):
        ensure_can_supersede(superseded, superseding)


def test_ensure_can_supersede_rejects_a_would_be_cyclical_reversal() -> None:
    """Once B has superseded A (A SUPERSEDED, B APPROVED), attempting the
    reverse — A superseding B — must be rejected: A is no longer APPROVED,
    so this can never create a cycle between the two decisions."""
    original = _decision(DecisionStatus.SUPERSEDED, decision_id=1)
    substitute = _decision(DecisionStatus.APPROVED, decision_id=2)

    with pytest.raises(ValueError, match="Cannot supersede"):
        ensure_can_supersede(original, substitute)


def test_ensure_can_archive_accepts_an_approved_decision() -> None:
    ensure_can_archive(_decision(DecisionStatus.APPROVED))  # must not raise


@pytest.mark.parametrize(
    "status", [DecisionStatus.PROPOSED, DecisionStatus.SUPERSEDED, DecisionStatus.ARCHIVED]
)
def test_ensure_can_archive_rejects_non_approved(status: DecisionStatus) -> None:
    with pytest.raises(ValueError, match="Cannot archive"):
        ensure_can_archive(_decision(status))
