"""SQLite-backed implementation of the memory repository port."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import CursorResult, Engine, exists, select, update
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    chunked,
    session_scope,
    sqlite_variable_limit,
)
from sirius.adapters.persistence.models import MemoryModel, MemoryRevisionModel
from sirius.domain.criticality import Criticality
from sirius.domain.facts import OWNER, Certainty, is_sirius, person_key
from sirius.domain.memory import (
    Memory,
    MemoryRevision,
    MemoryStatus,
    ensure_can_archive,
    ensure_can_correct,
    ensure_can_delete,
    ensure_subject_key_has_a_project,
    ensure_valid_origin,
    ensure_valid_subject_key,
    next_revision_version,
)


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_domain_revision(model: MemoryRevisionModel) -> MemoryRevision:
    return MemoryRevision(
        id=model.id,
        memory_id=model.memory_id,
        version=model.version,
        content=model.content,
        origin=model.origin,
        source_event_id=model.source_event_id,
        created_at=model.created_at.replace(tzinfo=UTC),
        valid_from=model.valid_from,
        valid_to=model.valid_to,
        said_by=model.said_by,
        certainty=model.certainty,
    )


def _to_domain_criticality(value: str | None) -> Criticality | None:
    """Validate a raw ``criticality`` column value at load time (M18b,
    ADR-126): an unknown string can never silently become a made-up
    ``Criticality`` member, or turn into ``None`` as if nobody had marked it
    — it fails clearly instead.
    """
    if value is None:
        return None
    try:
        return Criticality(value)
    except ValueError as error:
        msg = f"Unknown criticality value in database: {value!r}"
        raise ValueError(msg) from error


def _to_domain_memory(model: MemoryModel, revision_model: MemoryRevisionModel) -> Memory:
    return Memory(
        id=model.id,
        status=model.status,
        current_revision=_to_domain_revision(revision_model),
        created_at=model.created_at.replace(tzinfo=UTC),
        updated_at=model.updated_at.replace(tzinfo=UTC),
        subject_key=model.subject_key,
        project_id=model.project_id,
        category=model.category,
        category_locked=model.category_locked,
        criticality=_to_domain_criticality(model.criticality),
        person=model.person,
        topic=model.topic,
    )


def _get_current_revision_model(session: Session, memory_id: int) -> MemoryRevisionModel:
    revision_model = session.scalars(
        select(MemoryRevisionModel).where(
            MemoryRevisionModel.memory_id == memory_id,
            MemoryRevisionModel.is_current.is_(True),
        )
    ).first()
    if revision_model is None:
        msg = f"Memory {memory_id} has no current revision; data is corrupt."
        raise ValueError(msg)
    return revision_model


def _load_memory(session: Session, model: MemoryModel) -> Memory:
    revision_model = _get_current_revision_model(session, model.id)
    return _to_domain_memory(model, revision_model)


def _load_memories(session: Session, models: Sequence[MemoryModel]) -> list[Memory]:
    """Load the current revision of every model in a bounded number of queries.

    ``_load_memory`` issues one query per model; called from a list method
    that turns into N+1 queries for N models. This loads every current
    revision the set needs via ``IN (...)`` queries instead, batched to the
    connection's ``SQLITE_LIMIT_VARIABLE_NUMBER`` so a large set doesn't blow
    past SQLite's bound-parameter limit in a single statement.
    """
    if not models:
        return []
    memory_ids = [model.id for model in models]
    revisions_by_memory_id: dict[int, MemoryRevisionModel] = {}
    for batch in chunked(memory_ids, sqlite_variable_limit(session)):
        revision_models = session.scalars(
            select(MemoryRevisionModel).where(
                MemoryRevisionModel.memory_id.in_(batch),
                MemoryRevisionModel.is_current.is_(True),
            )
        ).all()
        revisions_by_memory_id.update(
            (revision.memory_id, revision) for revision in revision_models
        )
    memories = []
    for model in models:
        revision_model = revisions_by_memory_id.get(model.id)
        if revision_model is None:
            msg = f"Memory {model.id} has no current revision; data is corrupt."
            raise ValueError(msg)
        memories.append(_to_domain_memory(model, revision_model))
    return memories


def _add_memory(
    session: Session, content: str, origin: str, *, source_event_id: int | None
) -> tuple[MemoryModel, MemoryRevisionModel]:
    now = _utc_now_naive()
    memory_model = MemoryModel(status=MemoryStatus.CURRENT, created_at=now, updated_at=now)
    session.add(memory_model)
    session.flush()
    revision_model = MemoryRevisionModel(
        memory_id=memory_model.id,
        version=1,
        content=content,
        origin=origin,
        source_event_id=source_event_id,
        is_current=True,
        created_at=now,
    )
    session.add(revision_model)
    session.flush()
    return memory_model, revision_model


def _current_fact_model(session: Session, person: str, topic: str) -> MemoryModel | None:
    """El hecho vigente de ``person`` sobre ``topic``, sin mirar tildes ni mayúsculas."""
    models = session.scalars(
        select(MemoryModel).where(
            MemoryModel.status == MemoryStatus.CURRENT,
            MemoryModel.person.is_not(None),
            MemoryModel.topic.is_not(None),
        )
    ).all()
    keys = (person_key(person), person_key(topic))
    return next(
        (
            model
            for model in models
            if (person_key(model.person or ""), person_key(model.topic or "")) == keys
        ),
        None,
    )


def _close_and_revise(
    session: Session,
    memory_model: MemoryModel,
    content: str,
    origin: str,
    since: date,
    source_event_id: int | None,
) -> MemoryRevisionModel:
    """Cierra la revisión vigente de un hecho en ``since`` y pone otra en su lugar."""
    current = _get_current_revision_model(session, memory_model.id)
    current.is_current = False
    current.valid_to = since
    session.flush()
    now = _utc_now_naive()
    revision_model = MemoryRevisionModel(
        memory_id=memory_model.id,
        version=current.version + 1,
        content=content,
        origin=origin,
        source_event_id=source_event_id,
        is_current=True,
        created_at=now,
    )
    session.add(revision_model)
    memory_model.updated_at = now
    session.flush()
    return revision_model


class SqliteMemoryRepository:
    """Memory repository backed by a local SQLite database.

    Normally owns its ``session_factory`` and opens/commits/closes one short
    session per call (via ``session_scope``). When ``session`` is given
    instead, every call writes through that externally owned session and
    never commits or closes it — this is how ``SqliteUnitOfWork`` binds this
    repository to the same transaction as ``SqliteEventRepository``, so both
    commit or roll back together.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None,
        engine: Engine | None,
        *,
        session: Session | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._external_session = session

    def close(self) -> None:
        """Release every pooled connection this repository's engine holds."""
        if self._engine is not None:
            self._engine.dispose()

    @contextmanager
    def _scope(self) -> Iterator[Session]:
        if self._external_session is not None:
            yield self._external_session
            return
        assert self._session_factory is not None
        with session_scope(self._session_factory) as session:
            yield session

    def create_memory(
        self,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        subject_key: str | None = None,
        project_id: int | None = None,
    ) -> Memory:
        ensure_valid_origin(origin)
        ensure_valid_subject_key(subject_key)
        ensure_subject_key_has_a_project(subject_key, project_id)
        with self._scope() as session:
            memory_model, revision_model = _add_memory(
                session, content, origin, source_event_id=source_event_id
            )
            memory_model.subject_key = subject_key
            memory_model.project_id = project_id
            session.flush()
            return _to_domain_memory(memory_model, revision_model)

    def record_fact(
        self,
        person: str,
        topic: str | None,
        content: str,
        origin: str,
        *,
        since: date,
        said_by: str = OWNER,
        certainty: Certainty = Certainty.SURE,
        source_event_id: int | None = None,
    ) -> Memory:
        """Apunta un hecho de ``person``. Si ya hay uno vigente del mismo tema, lo cierra.

        Pieza G de ADR-233 (ADR-239): el de antes no se borra ni se corrige, se
        cierra con la fecha del nuevo, que pasa a ser su revisión vigente. Así la
        charla solo ve el vigente y la historia guarda los dos, cada uno con quién
        lo dijo y con qué seguridad. Lo que dice Sirius nunca es un hecho.
        """
        ensure_valid_origin(origin)
        if not person.strip() or not content.strip():
            msg = "Un hecho necesita persona y texto."
            raise ValueError(msg)
        if is_sirius(said_by):
            msg = "Lo que dice Sirius nunca es un hecho."
            raise ValueError(msg)
        with self._scope() as session:
            current = _current_fact_model(session, person, topic) if topic is not None else None
            if current is None:
                memory_model, revision_model = _add_memory(
                    session, content, origin, source_event_id=source_event_id
                )
                memory_model.person = person.strip()
                memory_model.topic = topic.strip() if topic is not None else None
            else:
                memory_model = current
                revision_model = _close_and_revise(
                    session, memory_model, content, origin, since, source_event_id
                )
            revision_model.valid_from = since
            revision_model.said_by = said_by.strip()
            revision_model.certainty = Certainty(certainty).value
            session.flush()
            return _to_domain_memory(memory_model, revision_model)

    def list_current_facts(self, person: str | None = None) -> list[Memory]:
        """Los hechos vigentes, de todos o de ``person``, del más nuevo al más viejo."""
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(
                    MemoryModel.status == MemoryStatus.CURRENT,
                    MemoryModel.person.is_not(None),
                )
                .order_by(MemoryModel.updated_at.desc(), MemoryModel.id.desc())
            ).all()
            if person is not None:
                key = person_key(person)
                models = [model for model in models if person_key(model.person or "") == key]
            return _load_memories(session, models)

    def known_people(self) -> list[str]:
        """Las personas con algún hecho vigente, sin repetir, como se apuntaron la primera vez."""
        people: dict[str, str] = {}
        for memory in reversed(self.list_current_facts()):
            if memory.person is not None:
                people.setdefault(person_key(memory.person), memory.person)
        return list(people.values())

    def find_fact_history(self, person: str, topic: str) -> list[MemoryRevision]:
        """La historia del hecho de ``person`` sobre ``topic``, de lo más viejo a lo vigente."""
        with self._scope() as session:
            model = _current_fact_model(session, person, topic)
            if model is None:
                return []
            revision_models = session.scalars(
                select(MemoryRevisionModel)
                .where(MemoryRevisionModel.memory_id == model.id)
                .order_by(MemoryRevisionModel.version)
            ).all()
            return [_to_domain_revision(revision) for revision in revision_models]

    def get_memory(self, memory_id: int) -> Memory:
        with self._scope() as session:
            model = session.get(MemoryModel, memory_id)
            if model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            return _load_memory(session, model)

    def get_memories(self, memory_ids: Sequence[int]) -> list[Memory]:
        """Pieza F (ADR-238): los que trae la búsqueda, en dos consultas y no en una cada uno."""
        if not memory_ids:
            return []
        with self._scope() as session:
            models: list[MemoryModel] = []
            for batch in chunked(list(memory_ids), sqlite_variable_limit(session)):
                models.extend(session.scalars(select(MemoryModel).where(MemoryModel.id.in_(batch))))
            by_id = {memory.id: memory for memory in _load_memories(session, models)}
            return [by_id[memory_id] for memory_id in memory_ids if memory_id in by_id]

    def list_current_memories(self) -> list[Memory]:
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(MemoryModel.status == MemoryStatus.CURRENT)
                .order_by(MemoryModel.id)
            ).all()
            return _load_memories(session, models)

    def list_current_memories_by_category(self, categories: Sequence[str]) -> list[Memory]:
        if not categories:
            return []
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(
                    MemoryModel.status == MemoryStatus.CURRENT,
                    MemoryModel.category.is_not(None),
                )
                .order_by(MemoryModel.id)
            ).all()
            return _load_memories(session, models)

    def list_archived_memories(self) -> list[Memory]:
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(MemoryModel.status == MemoryStatus.ARCHIVED)
                .order_by(MemoryModel.id)
            ).all()
            return _load_memories(session, models)

    def get_history(self, memory_id: int) -> list[MemoryRevision]:
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            revision_models = session.scalars(
                select(MemoryRevisionModel)
                .where(MemoryRevisionModel.memory_id == memory_id)
                .order_by(MemoryRevisionModel.version)
            ).all()
            return [_to_domain_revision(model) for model in revision_models]

    def correct_memory(
        self,
        memory_id: int,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        said_by: str | None = None,
        certainty: Certainty | None = None,
    ) -> Memory:
        """Una revisión nueva de un recuerdo.

        Si es un hecho (pieza G, ADR-239), la de antes se cierra hoy y la nueva vale
        desde hoy, dicha por ``said_by`` —el propietario si no se dice otro— y con
        ``certainty`` —segura si no—: corregir un hecho es decir cómo es ahora.
        """
        ensure_valid_origin(origin)
        if is_sirius(said_by):
            msg = "Lo que dice Sirius nunca es un hecho."
            raise ValueError(msg)
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            memory = _load_memory(session, memory_model)
            ensure_can_correct(memory)

            today = date.today()
            current_revision_model = _get_current_revision_model(session, memory_id)
            current_revision_model.is_current = False
            if memory.is_fact:
                current_revision_model.valid_to = today
            session.flush()

            new_revision_model = MemoryRevisionModel(
                memory_id=memory_id,
                version=next_revision_version(memory.current_revision),
                content=content,
                origin=origin,
                source_event_id=source_event_id,
                is_current=True,
                created_at=_utc_now_naive(),
            )
            if memory.is_fact:
                new_revision_model.valid_from = today
                new_revision_model.said_by = (said_by or OWNER).strip()
                new_revision_model.certainty = Certainty(certainty or Certainty.SURE).value
            session.add(new_revision_model)
            memory_model.updated_at = _utc_now_naive()
            # D7, "Corrección de contenido y reetiquetado" (SIRIUS-ARQ-0.2
            # §6.1): the content that produced the current category no
            # longer describes this memory once corrected. If the category
            # is still the automatic one (category_locked is False), clear
            # it in this same transaction; a user-locked category is never
            # touched by a correction (point 3).
            if not memory_model.category_locked:
                memory_model.category = None
            session.flush()

            return _to_domain_memory(memory_model, new_revision_model)

    def correct_fact(
        self,
        memory_id: int,
        content: str,
        origin: str,
        *,
        source_event_id: int | None = None,
        said_by: str = OWNER,
        certainty: Certainty = Certainty.SURE,
    ) -> Memory:
        """«Eso no es así» confirmado (pieza G, ADR-239): ``correct_memory`` de un hecho."""
        return self.correct_memory(
            memory_id,
            content,
            origin,
            source_event_id=source_event_id,
            said_by=said_by,
            certainty=certainty,
        )

    def archive_memory(self, memory_id: int) -> Memory:
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            memory = _load_memory(session, memory_model)
            ensure_can_archive(memory)

            memory_model.status = MemoryStatus.ARCHIVED
            memory_model.updated_at = _utc_now_naive()
            session.flush()

            return _load_memory(session, memory_model)

    def delete_memory(self, memory_id: int) -> Memory:
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            memory = _load_memory(session, memory_model)
            ensure_can_delete(memory)

            # Redact structured content across the full history; is_current is
            # left untouched so exactly one revision stays marked as current.
            revision_models = session.scalars(
                select(MemoryRevisionModel).where(MemoryRevisionModel.memory_id == memory_id)
            ).all()
            for revision_model in revision_models:
                revision_model.content = None
                # Pieza G (ADR-239): quién lo dijo también cuenta lo que decía.
                revision_model.said_by = None

            memory_model.status = MemoryStatus.DELETED
            # Y de quién era y de qué trataba.
            memory_model.person = None
            memory_model.topic = None
            memory_model.updated_at = _utc_now_naive()
            session.flush()

            return _load_memory(session, memory_model)

    def set_category(
        self, memory_id: int, category: str, *, observed_revision_version: int
    ) -> bool:
        with self._scope() as session:
            # Single atomic UPDATE: the EXISTS subquery re-checks, in the
            # same statement, that the current revision is still the one
            # that was classified — comprobar y escribir son una sola
            # operación atómica de la base de datos (D7 point 2), never a
            # read in Python followed by a separate write.
            statement = (
                update(MemoryModel)
                .where(
                    MemoryModel.id == memory_id,
                    MemoryModel.category_locked.is_(False),
                    exists().where(
                        MemoryRevisionModel.memory_id == MemoryModel.id,
                        MemoryRevisionModel.is_current.is_(True),
                        MemoryRevisionModel.version == observed_revision_version,
                    ),
                )
                .values(category=category)
            )
            result = cast(CursorResult[None], session.execute(statement))
            return result.rowcount > 0

    def set_user_category(self, memory_id: int, category: str) -> Memory:
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            memory_model.category = category
            memory_model.category_locked = True
            session.flush()
            return _load_memory(session, memory_model)

    def list_uncategorized(self) -> list[Memory]:
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(
                    MemoryModel.category.is_(None),
                    MemoryModel.category_locked.is_(False),
                )
                .order_by(MemoryModel.id)
            ).all()
            return _load_memories(session, models)

    def set_user_criticality(self, memory_id: int, criticality: Criticality | None) -> Memory:
        with self._scope() as session:
            memory_model = session.get(MemoryModel, memory_id)
            if memory_model is None:
                msg = f"Unknown memory id: {memory_id}"
                raise ValueError(msg)
            memory_model.criticality = None if criticality is None else criticality.value
            session.flush()
            return _load_memory(session, memory_model)

    def list_current_memories_by_criticality(self, levels: Sequence[Criticality]) -> list[Memory]:
        if not levels:
            return []
        with self._scope() as session:
            models = session.scalars(
                select(MemoryModel)
                .where(
                    MemoryModel.status == MemoryStatus.CURRENT,
                    MemoryModel.criticality.in_([level.value for level in levels]),
                )
                .order_by(MemoryModel.id)
            ).all()
            return _load_memories(session, models)


def build_sqlite_memory_repository(database_path: Path) -> SqliteMemoryRepository:
    """Build a repository backed by a SQLite file at the given path."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return SqliteMemoryRepository(session_factory, engine)


def bind_sqlite_memory_repository(session: Session) -> SqliteMemoryRepository:
    """Bind a repository to an externally owned session (used by ``SqliteUnitOfWork``)."""
    return SqliteMemoryRepository(None, None, session=session)
