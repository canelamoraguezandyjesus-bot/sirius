"""Lo que recuerda haber visto, en la base, como texto (pieza G de la 0.4, ADR-265).

Cada cambio es una fila: cuándo, en UTC, qué cambió y quién, o nadie. Borrar es de verdad,
como olvidar (ADR-239) y como las huellas (ADR-263): la conexión lleva ``secure_delete``,
que pone a ceros lo borrado en el fichero, también el nombre que se quita al retirar un
permiso.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, delete, event, select, update

from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import SightLogModel
from sirius.ports.sight_log import Change, SeenChange


class SqliteSightLog:
    """Lo apuntado, en la tabla ``sight_log``."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._sessions = build_session_factory(engine)

    def close(self) -> None:
        """Suelta las conexiones, como los demás almacenes de la base."""
        self._engine.dispose()

    def add(self, changes: Sequence[SeenChange]) -> None:
        with session_scope(self._sessions) as session:
            session.add_all(
                SightLogModel(seen_at=_naive(seen.at), change=seen.change.value, person=seen.who)
                for seen in changes
            )

    def since(self, moment: datetime) -> tuple[SeenChange, ...]:
        with session_scope(self._sessions) as session:
            rows = session.scalars(
                select(SightLogModel)
                .where(SightLogModel.seen_at >= _naive(moment))
                .order_by(SightLogModel.seen_at, SightLogModel.id)
            )
            return tuple(
                SeenChange(row.seen_at.replace(tzinfo=UTC), Change(row.change), row.person)
                for row in rows
            )

    def drop_before(self, moment: datetime) -> int:
        with session_scope(self._sessions) as session:
            result = session.execute(
                delete(SightLogModel).where(SightLogModel.seen_at < _naive(moment))
            )
            return int(getattr(result, "rowcount", 0) or 0)

    def forget(self, who: str) -> int:
        with session_scope(self._sessions) as session:
            result = session.execute(
                update(SightLogModel).where(SightLogModel.person == who).values(person=None)
            )
            return int(getattr(result, "rowcount", 0) or 0)


def _naive(moment: datetime) -> datetime:
    """``moment`` en UTC y sin zona, como guarda la base sus horas."""
    return moment.astimezone(UTC).replace(tzinfo=None)


def _secure_delete(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA secure_delete=ON")
    cursor.close()


def build_sqlite_sight_log(database_path: Path) -> SqliteSightLog:
    """Lo apuntado de lo que ve, en la base de ``database_path``, con lo borrado a ceros."""
    engine = build_engine(database_path)
    event.listen(engine, "connect", _secure_delete)
    return SqliteSightLog(engine)
