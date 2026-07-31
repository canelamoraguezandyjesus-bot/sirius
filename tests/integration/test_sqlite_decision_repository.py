from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import Base, DecisionModel, DecisionRevisionModel
from sirius.adapters.persistence.sqlite_decision_repository import (
    SqliteDecisionRepository,
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.domain.decision import DecisionStatus
from sirius.domain.event import DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR


def _build_repository(database_path: Path) -> SqliteDecisionRepository:
    Base.metadata.create_all(build_engine(database_path))
    return build_sqlite_decision_repository(database_path)


def _project_id(database_path: Path) -> int:
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
def test_create_proposal_rejects_empty_subject(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)

    with pytest.raises(ValueError, match="non-empty subject"):
        repository.create_proposal("", project_id, "contenido")

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        assert session.scalars(select(DecisionModel)).first() is None


@pytest.mark.integration
def test_create_proposal_rejects_empty_content(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)

    with pytest.raises(ValueError, match="non-empty content"):
        repository.create_proposal("Motor de persistencia", project_id, "   ")

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        assert session.scalars(select(DecisionModel)).first() is None


@pytest.mark.integration
def test_create_and_recover_a_proposed_decision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)

    created = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")

    assert created.status is DecisionStatus.PROPOSED
    assert created.subject == "Motor de persistencia"
    assert created.project_id == project_id
    assert created.current_revision.version == 1
    assert created.current_revision.content == "Usar SQLite local"

    fetched = repository.get_decision(created.id)
    assert fetched == created


@pytest.mark.integration
def test_create_proposal_without_source_event_id_leaves_it_none(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)

    created = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")

    assert created.current_revision.source_event_id is None


@pytest.mark.integration
def test_create_proposal_with_source_event_id_links_the_revision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    event_repository = build_sqlite_event_repository(database_path)
    event = event_repository.append(DECISION_PROPOSED_EVENT_TYPE, USER_ACTOR, message_id=None)

    linked = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar SQLite local", source_event_id=event.id
    )

    assert linked.current_revision.source_event_id == event.id
    fetched = repository.get_decision(linked.id)
    assert fetched.current_revision.source_event_id == event.id


@pytest.mark.integration
def test_approve_decision_flips_status_without_changing_the_revision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    proposed = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")

    approved = repository.approve_decision(proposed.id)

    assert approved.status is DecisionStatus.APPROVED
    assert approved.current_revision.version == proposed.current_revision.version
    assert approved.current_revision.content == proposed.current_revision.content

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        revisions = session.scalars(
            select(DecisionRevisionModel).where(DecisionRevisionModel.decision_id == proposed.id)
        ).all()
        assert len(revisions) == 1


@pytest.mark.integration
def test_approving_an_already_approved_decision_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    proposed = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(proposed.id)

    with pytest.raises(ValueError, match="Cannot approve"):
        repository.approve_decision(proposed.id)


@pytest.mark.integration
def test_operations_on_unknown_decision_raise(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown decision"):
        repository.get_decision(999)
    with pytest.raises(ValueError, match="Unknown decision"):
        repository.approve_decision(999)


@pytest.mark.integration
def test_decisions_for_different_projects_are_independent(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)

    first = repository.create_proposal("Primera decisión", project_id, "contenido 1")
    second = repository.create_proposal("Segunda decisión", project_id, "contenido 2")

    assert repository.get_decision(first.id).current_revision.content == "contenido 1"
    assert repository.get_decision(second.id).current_revision.content == "contenido 2"


@pytest.mark.integration
def test_decision_state_persists_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    proposed = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(proposed.id)

    reopened_repository = build_sqlite_decision_repository(database_path)
    fetched = reopened_repository.get_decision(proposed.id)

    assert fetched.status is DecisionStatus.APPROVED
    assert fetched.current_revision.content == "Usar SQLite local"


@pytest.mark.integration
def test_supersede_decision_flips_both_statuses_and_links_them(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )

    result = repository.supersede_decision(original.id, substitute.id)

    assert result.id == substitute.id
    assert result.status is DecisionStatus.APPROVED
    assert result.supersedes_decision_id == original.id

    superseded = repository.get_decision(original.id)
    assert superseded.status is DecisionStatus.SUPERSEDED


@pytest.mark.integration
def test_supersede_decision_never_creates_a_new_revision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )

    repository.supersede_decision(original.id, substitute.id)

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        original_revisions = session.scalars(
            select(DecisionRevisionModel).where(DecisionRevisionModel.decision_id == original.id)
        ).all()
        substitute_revisions = session.scalars(
            select(DecisionRevisionModel).where(DecisionRevisionModel.decision_id == substitute.id)
        ).all()
        assert len(original_revisions) == 1
        assert len(substitute_revisions) == 1


@pytest.mark.integration
def test_supersede_decision_rejects_an_unknown_id_on_either_side(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )

    with pytest.raises(ValueError, match="Unknown decision"):
        repository.supersede_decision(999, substitute.id)
    with pytest.raises(ValueError, match="Unknown decision"):
        repository.supersede_decision(original.id, 999)


@pytest.mark.integration
def test_supersede_decision_rejects_self_supersession(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)

    with pytest.raises(ValueError, match="cannot supersede itself"):
        repository.supersede_decision(original.id, original.id)


@pytest.mark.integration
def test_supersede_decision_rejects_a_non_approved_superseded_decision(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    proposed = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )

    with pytest.raises(ValueError, match="Cannot supersede"):
        repository.supersede_decision(proposed.id, substitute.id)


@pytest.mark.integration
def test_supersede_decision_accepts_an_already_approved_substitute(tmp_path: Path) -> None:
    """Reproduce el caso manual que falló: las dos decisiones ya aprobadas."""
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    other = repository.create_proposal("Motor de persistencia", project_id, "Otra alternativa")
    repository.approve_decision(other.id)

    result = repository.supersede_decision(original.id, other.id)

    assert result.status is DecisionStatus.APPROVED
    assert result.supersedes_decision_id == original.id
    assert repository.get_decision(original.id).status is DecisionStatus.SUPERSEDED
    assert [decision.id for decision in repository.list_current_decisions()] == [other.id]


@pytest.mark.integration
def test_supersede_decision_rejects_an_already_superseded_substitute(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    first = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(first.id)
    second = repository.create_proposal("Motor de persistencia", project_id, "Otra alternativa")
    repository.approve_decision(second.id)
    repository.supersede_decision(first.id, second.id)
    third = repository.create_proposal("Motor de persistencia", project_id, "Una tercera")
    repository.approve_decision(third.id)

    # ``first`` ya está SUSTITUIDA: no puede volver a ser la sustituta vigente.
    with pytest.raises(ValueError, match="PROPOSED or APPROVED decision can supersede"):
        repository.supersede_decision(third.id, first.id)


@pytest.mark.integration
def test_supersede_decision_rejects_a_mismatched_subject_or_project(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    unrelated = repository.create_proposal("Otro asunto", project_id, "Contenido no relacionado")

    with pytest.raises(ValueError, match="same subject and project"):
        repository.supersede_decision(original.id, unrelated.id)


@pytest.mark.integration
def test_supersede_decision_is_rejected_a_second_time(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    first_substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar PostgreSQL"
    )
    repository.supersede_decision(original.id, first_substitute.id)
    second_substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar MySQL"
    )

    with pytest.raises(ValueError, match="Cannot supersede"):
        repository.supersede_decision(original.id, second_substitute.id)


@pytest.mark.integration
def test_list_current_decisions_excludes_proposed_and_superseded(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    still_proposed = repository.create_proposal("Asunto A", project_id, "contenido A")
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )
    repository.supersede_decision(original.id, substitute.id)
    standalone_approved = repository.create_proposal("Asunto B", project_id, "contenido B")
    repository.approve_decision(standalone_approved.id)

    current = repository.list_current_decisions()

    current_ids = {decision.id for decision in current}
    assert current_ids == {substitute.id, standalone_approved.id}
    assert still_proposed.id not in current_ids
    assert original.id not in current_ids


@pytest.mark.integration
def test_list_proposed_decisions_returns_only_proposed(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    still_proposed = repository.create_proposal("Asunto A", project_id, "contenido A")
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )
    repository.supersede_decision(original.id, substitute.id)
    archived = repository.create_proposal("Asunto B", project_id, "contenido B")
    repository.approve_decision(archived.id)
    repository.archive_decision(archived.id)

    proposed = repository.list_proposed_decisions()

    assert [decision.id for decision in proposed] == [still_proposed.id]


@pytest.mark.integration
def test_get_superseding_decision_returns_the_substitute(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )
    repository.supersede_decision(original.id, substitute.id)

    superseding = repository.get_superseding_decision(original.id)

    assert superseding is not None
    assert superseding.id == substitute.id


@pytest.mark.integration
def test_get_superseding_decision_returns_none_when_not_superseded(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    standalone = repository.create_proposal("Asunto A", project_id, "contenido A")
    repository.approve_decision(standalone.id)

    assert repository.get_superseding_decision(standalone.id) is None
    assert repository.get_superseding_decision(999) is None


@pytest.mark.integration
def test_supersession_survives_closing_and_reopening_the_store(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    original = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(original.id)
    substitute = repository.create_proposal(
        "Motor de persistencia", project_id, "Usar PostgreSQL en su lugar"
    )
    repository.supersede_decision(original.id, substitute.id)
    repository.close()

    reopened = build_sqlite_decision_repository(database_path)

    assert reopened.get_decision(original.id).status is DecisionStatus.SUPERSEDED
    assert reopened.get_decision(substitute.id).status is DecisionStatus.APPROVED
    assert reopened.get_decision(substitute.id).supersedes_decision_id == original.id


@pytest.mark.integration
def test_archive_decision_removes_it_from_current_list_without_deleting_content(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    decision = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(decision.id)

    archived = repository.archive_decision(decision.id)

    assert archived.status is DecisionStatus.ARCHIVED
    assert archived.current_revision.content == "Usar SQLite local"
    assert decision.id not in {d.id for d in repository.list_current_decisions()}

    fetched = repository.get_decision(decision.id)
    assert fetched.current_revision.content == "Usar SQLite local"


@pytest.mark.integration
def test_list_archived_decisions_returns_only_archived(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    still_proposed = repository.create_proposal("Asunto A", project_id, "contenido A")
    approved = repository.create_proposal("Asunto B", project_id, "contenido B")
    repository.approve_decision(approved.id)
    to_archive = repository.create_proposal("Asunto C", project_id, "contenido C")
    repository.approve_decision(to_archive.id)
    repository.archive_decision(to_archive.id)

    archived_list = repository.list_archived_decisions()

    assert [d.id for d in archived_list] == [to_archive.id]
    assert still_proposed.id not in [d.id for d in archived_list]
    assert approved.id not in [d.id for d in archived_list]


@pytest.mark.integration
@pytest.mark.parametrize("status_setup", ["proposed", "superseded", "archived"])
def test_archiving_a_non_approved_decision_is_rejected(tmp_path: Path, status_setup: str) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    decision = repository.create_proposal("Asunto", project_id, "contenido")

    if status_setup == "proposed":
        target_id = decision.id
    elif status_setup == "superseded":
        repository.approve_decision(decision.id)
        substitute = repository.create_proposal("Asunto", project_id, "contenido nuevo")
        repository.supersede_decision(decision.id, substitute.id)
        target_id = decision.id
    else:
        repository.approve_decision(decision.id)
        repository.archive_decision(decision.id)
        target_id = decision.id

    with pytest.raises(ValueError, match="Cannot archive"):
        repository.archive_decision(target_id)


@pytest.mark.integration
def test_archiving_an_unknown_decision_raises(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="Unknown decision"):
        repository.archive_decision(999)


@pytest.mark.integration
def test_decision_archive_persists_after_closing_and_reopening_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    project_id = _project_id(database_path)
    decision = repository.create_proposal("Motor de persistencia", project_id, "Usar SQLite local")
    repository.approve_decision(decision.id)
    repository.archive_decision(decision.id)
    repository.close()

    reopened = build_sqlite_decision_repository(database_path)
    fetched = reopened.get_decision(decision.id)
    assert fetched.status is DecisionStatus.ARCHIVED
    assert fetched.current_revision.content == "Usar SQLite local"
    assert [d.id for d in reopened.list_archived_decisions()] == [decision.id]
    reopened.close()


@pytest.mark.integration
def test_failed_proposal_leaves_no_partial_data(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)
    project_id = _project_id(database_path)

    class Boom(Exception):
        pass

    with (
        pytest.raises(Boom),
        session_scope(session_factory) as session,
    ):
        now = datetime.now(UTC).replace(tzinfo=None)
        decision_model = DecisionModel(
            subject="Motor de persistencia",
            project_id=project_id,
            status=DecisionStatus.PROPOSED,
            created_at=now,
            updated_at=now,
        )
        session.add(decision_model)
        session.flush()
        revision_model = DecisionRevisionModel(
            decision_id=decision_model.id,
            version=1,
            content="Usar SQLite local",
            is_current=True,
            created_at=now,
        )
        session.add(revision_model)
        session.flush()
        raise Boom

    with session_scope(session_factory) as session:
        assert session.scalars(select(DecisionModel)).first() is None
        assert session.scalars(select(DecisionRevisionModel)).first() is None
