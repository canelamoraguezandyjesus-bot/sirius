"""Las huellas de quien dio permiso, en la base, ya cifradas (pieza E de la 0.4, ADR-263).

Aquí no se cifra ni se descifra nada: llegan cifradas y salen cifradas. Dar permiso pone
las de una persona en lugar de las que tuviera, en una sola transacción; quitarlo las
borra todas. Borrar es de verdad, como olvidar (ADR-239): la conexión lleva
``secure_delete``, que pone a ceros lo borrado en el fichero, su nombre incluido.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, delete, event, select

from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.adapters.persistence.models import RecognitionPrintModel
from sirius.ports.recognition import PrintKind, SealedPrint


class SqliteRecognitionPrints:
    """Las huellas cifradas, en la tabla ``recognition_prints``."""

    def __init__(
        self, engine: Engine, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._engine = engine
        self._sessions = build_session_factory(engine)
        self._clock = clock

    def close(self) -> None:
        """Suelta las conexiones, como los demás almacenes de la base."""
        self._engine.dispose()

    def replace(self, person: str, prints: Sequence[SealedPrint]) -> None:
        if any(stored.person != person for stored in prints):
            msg = "todas las huellas tienen que ser de quien da el permiso"
            raise ValueError(msg)
        with session_scope(self._sessions) as session:
            session.execute(
                delete(RecognitionPrintModel).where(RecognitionPrintModel.person == person)
            )
            now = self._clock()
            session.add_all(
                RecognitionPrintModel(
                    person=person, kind=stored.kind.value, sealed=stored.sealed, created_at=now
                )
                for stored in prints
            )

    def all(self) -> tuple[SealedPrint, ...]:
        with session_scope(self._sessions) as session:
            rows = session.scalars(select(RecognitionPrintModel).order_by(RecognitionPrintModel.id))
            return tuple(SealedPrint(row.person, PrintKind(row.kind), row.sealed) for row in rows)

    def remove(self, person: str) -> int:
        with session_scope(self._sessions) as session:
            result = session.execute(
                delete(RecognitionPrintModel).where(RecognitionPrintModel.person == person)
            )
            return int(getattr(result, "rowcount", 0) or 0)


def _secure_delete(dbapi_connection: sqlite3.Connection, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA secure_delete=ON")
    cursor.close()


def build_sqlite_recognition_prints(database_path: Path) -> SqliteRecognitionPrints:
    """Las huellas cifradas de la base de ``database_path``, con lo borrado a ceros."""
    engine = build_engine(database_path)
    event.listen(engine, "connect", _secure_delete)
    return SqliteRecognitionPrints(engine)
