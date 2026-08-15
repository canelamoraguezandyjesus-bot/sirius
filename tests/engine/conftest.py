"""Shared fixtures for the Sirius Work Engine core tests (incidencia #177).

Every test in ``tests/engine/`` drives a :class:`WorkEngineStore` (the
port), never the concrete :class:`InMemoryWorkEngineStore` directly beyond
constructing it here — so the same test bodies can run unmodified against a
future durable implementation (requisito 9).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime

import pytest

from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.domain.run import Run
from sirius_engine.domain.work_item import WorkItem, WorkItemClass
from sirius_engine.ports.store import WorkEngineStore

#: Every store implementation the contract tests must pass against. A1 only
#: has the in-memory one; a future durable store is added here, unchanged.
STORE_FACTORIES = (InMemoryWorkEngineStore,)

MakeWorkItem = Callable[..., WorkItem]
MakeRun = Callable[..., Run]


@pytest.fixture(params=STORE_FACTORIES, ids=lambda factory: factory.__name__)
def store(request: pytest.FixtureRequest) -> WorkEngineStore:
    factory: type[InMemoryWorkEngineStore] = request.param
    return factory()


@pytest.fixture
def now() -> datetime:
    """A fixed instant; never the real system clock (disciplina-evidencia)."""
    return datetime(2026, 8, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def make_work_item(store: WorkEngineStore) -> MakeWorkItem:
    """Create a WorkItem with the minimal set of realistic §3.1 fields."""

    def _make(
        *,
        now: datetime,
        work_id: str = "WI-0001",
        limites: Mapping[str, object] | None = None,
    ) -> WorkItem:
        return store.create_work_item(
            work_id=work_id,
            peticion_original="texto literal de la petición",
            objetivo="objetivo normalizado y confirmado",
            contexto_origen=("incidencia:177",),
            entregable="un entregable de prueba",
            criterio_terminado="el entregable existe y pasa sus pruebas",
            limites={"presupuesto_turnos": 10} if limites is None else limites,
            prioridad=1,
            clase=WorkItemClass.PROGRAMACION,
            now=now,
            plan=("paso-1",),
        )

    return _make


@pytest.fixture
def make_run(store: WorkEngineStore) -> MakeRun:
    """Create a Run with a minimal, opaque work_package snapshot."""

    def _make(
        *,
        now: datetime,
        deadline: datetime,
        run_id: str = "RUN-0001",
        work_id: str = "WI-0001",
        paso: str = "paso-1",
        worker: str = "claude-code",
        recurso_mutable: str | None = None,
    ) -> Run:
        return store.prepare_run(
            run_id=run_id,
            work_id=work_id,
            paso=paso,
            worker=worker,
            work_package={"instrucciones": "instantánea de prueba"},
            deadline=deadline,
            now=now,
            recurso_mutable=recurso_mutable,
        )

    return _make
