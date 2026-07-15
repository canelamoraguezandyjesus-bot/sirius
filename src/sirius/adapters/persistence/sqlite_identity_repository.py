"""SQLite-backed implementation of the identity repository port."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.models import IdentityModel, IdentityVersionModel
from sirius.domain.identity import (
    INITIAL_IDENTITY_DESCRIPTION,
    INITIAL_IDENTITY_NAME,
    INITIAL_PERSONALITY_INSTRUCTIONS,
    Identity,
    IdentityVersion,
    next_identity_version,
)


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_domain_version(model: IdentityVersionModel) -> IdentityVersion:
    return IdentityVersion(
        id=model.id,
        identity_id=model.identity_id,
        version=model.version,
        name=model.name,
        description=model.description,
        personality_instructions=model.personality_instructions,
        created_at=model.created_at.replace(tzinfo=UTC),
    )


def _to_domain_identity(model: IdentityModel, version_model: IdentityVersionModel) -> Identity:
    return Identity(
        id=model.id,
        current_version=_to_domain_version(version_model),
        created_at=model.created_at.replace(tzinfo=UTC),
    )


def _get_current_version_model(session: Session, identity_id: int) -> IdentityVersionModel:
    version_model = session.scalars(
        select(IdentityVersionModel).where(
            IdentityVersionModel.identity_id == identity_id,
            IdentityVersionModel.is_current.is_(True),
        )
    ).first()
    if version_model is None:
        msg = f"Identity {identity_id} has no current version; data is corrupt."
        raise ValueError(msg)
    return version_model


def _find_identity_model(session: Session) -> IdentityModel | None:
    return session.scalars(select(IdentityModel).limit(1)).first()


class SqliteIdentityRepository:
    """Identity repository backed by a local SQLite database."""

    def __init__(self, session_factory: sessionmaker[Session], engine: Engine) -> None:
        self._session_factory = session_factory
        self._engine = engine

    def close(self) -> None:
        """Release every pooled connection this repository's engine holds."""
        self._engine.dispose()

    def get_or_create_current_identity(self) -> Identity:
        with session_scope(self._session_factory) as session:
            identity_model = _find_identity_model(session)
            if identity_model is None:
                now = _utc_now_naive()
                identity_model = IdentityModel(created_at=now)
                session.add(identity_model)
                session.flush()

                version_model = IdentityVersionModel(
                    identity_id=identity_model.id,
                    version=1,
                    name=INITIAL_IDENTITY_NAME,
                    description=INITIAL_IDENTITY_DESCRIPTION,
                    personality_instructions=INITIAL_PERSONALITY_INSTRUCTIONS,
                    is_current=True,
                    created_at=now,
                )
                session.add(version_model)
                session.flush()

                return _to_domain_identity(identity_model, version_model)

            version_model = _get_current_version_model(session, identity_model.id)
            return _to_domain_identity(identity_model, version_model)

    def get_current_identity(self) -> Identity | None:
        with session_scope(self._session_factory) as session:
            identity_model = _find_identity_model(session)
            if identity_model is None:
                return None
            version_model = _get_current_version_model(session, identity_model.id)
            return _to_domain_identity(identity_model, version_model)

    def get_history(self) -> list[IdentityVersion]:
        with session_scope(self._session_factory) as session:
            identity_model = _find_identity_model(session)
            if identity_model is None:
                return []
            version_models = session.scalars(
                select(IdentityVersionModel)
                .where(IdentityVersionModel.identity_id == identity_model.id)
                .order_by(IdentityVersionModel.version)
            ).all()
            return [_to_domain_version(model) for model in version_models]

    def create_new_version(
        self, name: str, description: str, personality_instructions: str
    ) -> Identity:
        with session_scope(self._session_factory) as session:
            identity_model = _find_identity_model(session)
            if identity_model is None:
                msg = "No identity exists yet; call get_or_create_current_identity first."
                raise ValueError(msg)

            current_version_model = _get_current_version_model(session, identity_model.id)
            current_version = _to_domain_version(current_version_model)
            current_version_model.is_current = False
            session.flush()

            new_version_model = IdentityVersionModel(
                identity_id=identity_model.id,
                version=next_identity_version(current_version),
                name=name,
                description=description,
                personality_instructions=personality_instructions,
                is_current=True,
                created_at=_utc_now_naive(),
            )
            session.add(new_version_model)
            session.flush()

            return _to_domain_identity(identity_model, new_version_model)


def build_sqlite_identity_repository(database_path: Path) -> SqliteIdentityRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteIdentityRepository(session_factory, engine)
