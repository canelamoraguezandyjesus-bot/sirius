"""B6a contract: FTS5 must be confirmed available in this environment's
SQLite before anything relies on it.

SIRIUS-ARQ-0.1 S7.1/S8.1; ATD-004: "FTS5 forma parte de SQLite... El
contrato exige una prueba que confirme que FTS5 está disponible en el
SQLite de CI antes de asumirlo." A build of SQLite without the FTS5
extension compiled in fails ``CREATE VIRTUAL TABLE ... USING fts5`` with a
clear ``sqlite3.OperationalError`` ("no such module: fts5"); this test
turns that into an explicit, early, unmistakable failure instead of letting
it surface later as a confusing migration error.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text

from sirius.adapters.persistence.database import build_engine


@pytest.mark.integration
def test_the_stdlib_sqlite3_driver_supports_fts5() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        try:
            connection.execute("CREATE VIRTUAL TABLE fts5_probe USING fts5(content)")
        except sqlite3.OperationalError as exc:
            pytest.fail(
                "El SQLite de este entorno no tiene compilado el módulo FTS5 "
                f"(sqlite3.sqlite_version={sqlite3.sqlite_version}): {exc}"
            )
        connection.execute("INSERT INTO fts5_probe(content) VALUES ('sonda de disponibilidad')")
        matches = connection.execute(
            "SELECT content FROM fts5_probe WHERE fts5_probe MATCH 'sonda'"
        ).fetchall()
        assert matches == [("sonda de disponibilidad",)]
    finally:
        connection.close()


@pytest.mark.integration
def test_the_sqlalchemy_engine_used_by_sirius_supports_fts5(tmp_path: Path) -> None:
    engine = build_engine(tmp_path / "fts5_probe.db")
    try:
        with engine.begin() as connection:
            try:
                connection.execute(text("CREATE VIRTUAL TABLE fts5_probe USING fts5(content)"))
            except Exception as exc:  # pragma: no cover - only on an unsupported build
                pytest.fail(f"El motor SQLAlchemy/SQLite de Sirius no soporta FTS5: {exc}")
    finally:
        engine.dispose()
