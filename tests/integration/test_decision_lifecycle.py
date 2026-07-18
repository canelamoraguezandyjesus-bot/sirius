"""End-to-end integration tests for B4b (RF-020, PA-011).

Wires the real SQLite adapters (no fakes) behind ``ProposeDecisionUseCase``,
``ApproveDecisionUseCase`` and ``GetDecisionOriginUseCase`` exactly as
``composition_root`` does, proving the whole vertical slice: a debated
proposal never becomes an approved decision on its own, an explicit
approval does, the approved decision exposes every field RF-020 requires,
its origin is real and queryable, and everything survives reopening the
store.
"""

from pathlib import Path

import pytest

from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.approve_decision import (
    ApprovalNotConfirmedError,
    ApproveDecisionUseCase,
    InvalidDecisionStatusError,
    UnknownDecisionError,
)
from sirius.application.decision_origin import DecisionOriginNotFoundError, GetDecisionOriginUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.supersede_decision import (
    DecisionSupersessionNotConfirmedError,
    InvalidDecisionSupersessionError,
    SupersedeDecisionUseCase,
)
from sirius.application.supersede_decision import (
    UnknownDecisionError as UnknownSupersessionDecisionError,
)
from sirius.domain.conversation import MessageRole
from sirius.domain.decision import DecisionStatus


def _bootstrap(database_path: Path) -> int:
    Base.metadata.create_all(build_engine(database_path))
    project_repository = build_sqlite_project_repository(database_path)
    project_repository.ensure_bootstrap_project()
    project = project_repository.create_project(
        "Proyecto de prueba",
        "Objetivo de prueba",
        state_summary="En curso",
        blockers=(),
        next_step="Siguiente paso",
    )
    return project.id


@pytest.mark.integration
def test_debating_alternatives_never_creates_a_decision(tmp_path: Path) -> None:
    """PA-011: nothing short of an explicit call to ``ProposeDecisionUseCase``
    ever inserts a row — a plain conversation about options is not enough,
    because it never calls it at all."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)

    decision_repository = build_sqlite_decision_repository(database_path)
    with pytest.raises(ValueError, match="Unknown decision"):
        decision_repository.get_decision(1)


@pytest.mark.integration
def test_creating_a_proposal_never_produces_an_approved_decision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )

    assert proposed.status is DecisionStatus.PROPOSED


@pytest.mark.integration
def test_approval_without_explicit_confirmation_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )

    with pytest.raises(ApprovalNotConfirmedError):
        ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=False)

    decision_repository = build_sqlite_decision_repository(database_path)
    assert decision_repository.get_decision(proposed.id).status is DecisionStatus.PROPOSED


@pytest.mark.integration
def test_explicit_approval_creates_a_traceable_approved_decision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    conversation = conversation_repository.get_or_create_main_conversation()
    source_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "propongo usar SQLite local para el motor"
    )

    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia",
        project_id,
        "Usar SQLite local",
        message_id=source_message.id,
    )
    approved = ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)

    # RF-020: estado, asunto, versión, fecha, proyecto y origen quedan
    # observables de inmediato.
    assert approved.status is DecisionStatus.APPROVED
    assert approved.subject == "Motor de persistencia"
    assert approved.project_id == project_id
    assert approved.current_revision.version == 1
    assert approved.created_at is not None
    assert approved.current_revision.source_event_id is not None

    # ALCANCE #9: el origen puede consultarse después, y abre el mensaje real.
    origin_use_case = GetDecisionOriginUseCase(
        decision_repository, event_repository, conversation_repository
    )
    origin = origin_use_case.get_origin(proposed.id)

    assert origin.status is DecisionStatus.APPROVED
    assert origin.event_id == approved.current_revision.source_event_id
    assert origin.message_id == source_message.id
    assert origin.message_content == "propongo usar SQLite local para el motor"


@pytest.mark.integration
def test_approving_an_unknown_decision_id_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)

    with pytest.raises(UnknownDecisionError):
        ApproveDecisionUseCase(unit_of_work).approve(999, confirmed=True)


@pytest.mark.integration
def test_approving_an_already_approved_decision_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)

    with pytest.raises(InvalidDecisionStatusError):
        ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)


@pytest.mark.integration
def test_querying_the_origin_of_an_unknown_decision_id_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    origin_use_case = GetDecisionOriginUseCase(
        decision_repository, event_repository, conversation_repository
    )

    with pytest.raises(DecisionOriginNotFoundError):
        origin_use_case.get_origin(999)


@pytest.mark.integration
def test_decision_and_its_origin_survive_closing_and_reopening_the_store(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)

    conversation_repository = build_sqlite_conversation_repository(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    conversation = conversation_repository.get_or_create_main_conversation()
    source_message = conversation_repository.append_message(
        conversation.id, MessageRole.USER, "propongo esta decisión"
    )
    proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia",
        project_id,
        "Usar SQLite local",
        message_id=source_message.id,
    )
    approved = ApproveDecisionUseCase(unit_of_work).approve(proposed.id, confirmed=True)

    conversation_repository.close()
    decision_repository.close()
    event_repository.close()
    unit_of_work.close()

    reopened_conversation_repository = build_sqlite_conversation_repository(database_path)
    reopened_decision_repository = build_sqlite_decision_repository(database_path)
    reopened_event_repository = build_sqlite_event_repository(database_path)

    fetched = reopened_decision_repository.get_decision(approved.id)
    assert fetched.status is DecisionStatus.APPROVED
    assert fetched.current_revision.content == "Usar SQLite local"

    origin = GetDecisionOriginUseCase(
        reopened_decision_repository, reopened_event_repository, reopened_conversation_repository
    ).get_origin(approved.id)
    assert origin.message_content == "propongo esta decisión"


@pytest.mark.integration
def test_a_proposed_decision_can_explicitly_supersede_an_approved_one(tmp_path: Path) -> None:
    """B4c, PA-013: approving a decision that replaces another marks the
    original as SUSTITUIDA (SUPERSEDED) — never deleted, still consultable —
    links it to its successor, and the successor becomes the only one the
    ordinary vigente query returns."""
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    decision_repository = build_sqlite_decision_repository(database_path)

    original = ApproveDecisionUseCase(unit_of_work).approve(
        ProposeDecisionUseCase(unit_of_work)
        .propose("Motor de persistencia", project_id, "Usar SQLite local")
        .id,
        confirmed=True,
    )
    substitute_proposal = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )

    substitute = SupersedeDecisionUseCase(unit_of_work).supersede(
        original.id, substitute_proposal.id, confirmed=True
    )

    assert substitute.status is DecisionStatus.APPROVED
    assert substitute.supersedes_decision_id == original.id

    # The original decision is never deleted: it stays consultable, marked
    # SUPERSEDED rather than APPROVED.
    superseded = decision_repository.get_decision(original.id)
    assert superseded.status is DecisionStatus.SUPERSEDED

    # The persistent link is queryable from either side.
    superseding = decision_repository.get_superseding_decision(original.id)
    assert superseding is not None
    assert superseding.id == substitute.id

    # The ordinary "vigente" query returns only the substitute.
    current_ids = {decision.id for decision in decision_repository.list_current_decisions()}
    assert current_ids == {substitute.id}


@pytest.mark.integration
def test_supersession_without_confirmation_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    original = ApproveDecisionUseCase(unit_of_work).approve(
        ProposeDecisionUseCase(unit_of_work)
        .propose("Motor de persistencia", project_id, "Usar SQLite local")
        .id,
        confirmed=True,
    )
    substitute_proposal = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )

    with pytest.raises(DecisionSupersessionNotConfirmedError):
        SupersedeDecisionUseCase(unit_of_work).supersede(
            original.id, substitute_proposal.id, confirmed=False
        )

    decision_repository = build_sqlite_decision_repository(database_path)
    assert decision_repository.get_decision(original.id).status is DecisionStatus.APPROVED
    assert (
        decision_repository.get_decision(substitute_proposal.id).status is DecisionStatus.PROPOSED
    )


@pytest.mark.integration
def test_debating_alternatives_never_supersedes_a_decision(tmp_path: Path) -> None:
    """PA-013's negative half, mirroring PA-011: nothing short of an explicit
    call to ``SupersedeDecisionUseCase`` ever changes a decision's status to
    SUPERSEDED — an ordinary conversation never calls it."""
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    original = ApproveDecisionUseCase(unit_of_work).approve(
        ProposeDecisionUseCase(unit_of_work)
        .propose("Motor de persistencia", project_id, "Usar SQLite local")
        .id,
        confirmed=True,
    )

    decision_repository = build_sqlite_decision_repository(database_path)
    assert decision_repository.get_decision(original.id).status is DecisionStatus.APPROVED
    assert decision_repository.get_superseding_decision(original.id) is None


@pytest.mark.integration
def test_superseding_an_unknown_decision_id_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    substitute_proposal = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )

    with pytest.raises(UnknownSupersessionDecisionError):
        SupersedeDecisionUseCase(unit_of_work).supersede(
            999, substitute_proposal.id, confirmed=True
        )


@pytest.mark.integration
def test_superseding_with_incompatible_statuses_is_handled_safely(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    project_id = _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    still_proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar SQLite local"
    )
    other_still_proposed = ProposeDecisionUseCase(unit_of_work).propose(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )

    with pytest.raises(InvalidDecisionSupersessionError):
        SupersedeDecisionUseCase(unit_of_work).supersede(
            still_proposed.id, other_still_proposed.id, confirmed=True
        )
