from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import Base, IdentityModel, IdentityVersionModel
from sirius.adapters.persistence.sqlite_identity_repository import (
    SqliteIdentityRepository,
    build_sqlite_identity_repository,
)
from sirius.domain.identity import (
    INITIAL_IDENTITY_DESCRIPTION,
    INITIAL_IDENTITY_NAME,
    INITIAL_PERSONALITY_INSTRUCTIONS,
)


def _build_repository(database_path: Path) -> SqliteIdentityRepository:
    repository = build_sqlite_identity_repository(database_path)
    Base.metadata.create_all(build_engine(database_path))
    return repository


@pytest.mark.integration
def test_initial_identity_matches_the_canonical_seed(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    identity = repository.get_or_create_current_identity()

    assert identity.current_version.version == 1
    assert identity.current_version.name == INITIAL_IDENTITY_NAME
    assert identity.current_version.description == INITIAL_IDENTITY_DESCRIPTION
    assert identity.current_version.personality_instructions == INITIAL_PERSONALITY_INSTRUCTIONS


@pytest.mark.integration
def test_get_or_create_current_identity_is_idempotent_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    first_repository = _build_repository(database_path)
    first_identity = first_repository.get_or_create_current_identity()

    second_repository = build_sqlite_identity_repository(database_path)
    second_identity = second_repository.get_or_create_current_identity()

    assert second_identity.id == first_identity.id
    assert second_identity.current_version.id == first_identity.current_version.id

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        assert len(session.scalars(select(IdentityModel)).all()) == 1
        assert len(session.scalars(select(IdentityVersionModel)).all()) == 1


@pytest.mark.integration
def test_create_new_version_does_not_overwrite_the_previous_one(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    repository.get_or_create_current_identity()

    updated = repository.create_new_version("Sirius", "nueva descripcion", "nuevas instrucciones")

    assert updated.current_version.version == 2
    assert updated.current_version.description == "nueva descripcion"

    history = repository.get_history()
    assert [v.version for v in history] == [1, 2]
    assert history[0].description == INITIAL_IDENTITY_DESCRIPTION
    assert history[1].description == "nueva descripcion"


@pytest.mark.integration
def test_only_one_current_version_after_several_new_versions(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    repository.get_or_create_current_identity()
    repository.create_new_version("Sirius", "v2", "i2")
    repository.create_new_version("Sirius", "v3", "i3")

    fetched = repository.get_or_create_current_identity()
    assert fetched.current_version.version == 3
    assert fetched.current_version.description == "v3"

    session_factory = build_session_factory(build_engine(database_path))
    with session_scope(session_factory) as session:
        versions = session.scalars(select(IdentityVersionModel)).all()
        current_versions = [v for v in versions if v.is_current]
        assert len(versions) == 3
        assert len(current_versions) == 1
        assert current_versions[0].version == 3


@pytest.mark.integration
def test_history_is_returned_in_stable_version_order(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    repository.get_or_create_current_identity()
    repository.create_new_version("Sirius", "v2", "i2")
    repository.create_new_version("Sirius", "v3", "i3")

    history = repository.get_history()

    assert [v.version for v in history] == [1, 2, 3]
    assert [v.description for v in history] == [INITIAL_IDENTITY_DESCRIPTION, "v2", "v3"]


@pytest.mark.integration
def test_get_history_is_empty_before_any_identity_exists(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    assert repository.get_history() == []


@pytest.mark.integration
def test_create_new_version_without_an_existing_identity_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)

    with pytest.raises(ValueError, match="No identity exists yet"):
        repository.create_new_version("Sirius", "x", "y")


@pytest.mark.integration
def test_identity_state_persists_across_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    repository.get_or_create_current_identity()
    repository.create_new_version("Sirius", "v2", "i2")

    reopened_repository = build_sqlite_identity_repository(database_path)
    fetched = reopened_repository.get_or_create_current_identity()
    history = reopened_repository.get_history()

    assert fetched.current_version.description == "v2"
    assert [v.description for v in history] == [INITIAL_IDENTITY_DESCRIPTION, "v2"]


@pytest.mark.integration
def test_database_rejects_two_current_versions_for_the_same_identity(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    engine = build_engine(database_path)
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    now = datetime.now(UTC).replace(tzinfo=None)
    with session_scope(session_factory) as session:
        identity_model = IdentityModel(created_at=now)
        session.add(identity_model)
        session.flush()
        session.add(
            IdentityVersionModel(
                identity_id=identity_model.id,
                version=1,
                name="Sirius",
                description="d1",
                personality_instructions="i1",
                is_current=True,
                created_at=now,
            )
        )
        identity_id = identity_model.id

    with (
        pytest.raises(IntegrityError),
        session_scope(session_factory) as session,
    ):
        session.add(
            IdentityVersionModel(
                identity_id=identity_id,
                version=2,
                name="Sirius",
                description="d2",
                personality_instructions="i2",
                is_current=True,
                created_at=now,
            )
        )
        session.flush()

    with session_scope(session_factory) as session:
        current_versions = session.scalars(
            select(IdentityVersionModel).where(IdentityVersionModel.is_current.is_(True))
        ).all()
        assert len(current_versions) == 1


@pytest.mark.integration
def test_failed_new_version_rolls_back_both_the_flip_and_the_new_row(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    repository = _build_repository(database_path)
    repository.get_or_create_current_identity()

    session_factory = build_session_factory(build_engine(database_path))

    class Boom(Exception):
        pass

    with (
        pytest.raises(Boom),
        session_scope(session_factory) as session,
    ):
        current_version_model = session.scalars(
            select(IdentityVersionModel).where(IdentityVersionModel.is_current.is_(True))
        ).one()
        current_version_model.is_current = False
        session.flush()
        session.add(
            IdentityVersionModel(
                identity_id=current_version_model.identity_id,
                version=2,
                name="Sirius",
                description="corrupto",
                personality_instructions="corrupto",
                is_current=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        session.flush()
        raise Boom

    fetched = repository.get_or_create_current_identity()
    assert fetched.current_version.version == 1
    assert fetched.current_version.description == INITIAL_IDENTITY_DESCRIPTION
    assert len(repository.get_history()) == 1
