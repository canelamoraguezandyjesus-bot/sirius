"""Shared fixtures for the Sirius Work Engine core tests (incidencia #177, #186).

Every test in ``tests/engine/`` drives a :class:`WorkEngineStore` (the
port), never a concrete store directly beyond constructing it here — so the
same test bodies run unmodified against every implementation listed in
``STORE_FACTORIES`` (A1 requisito 9; A2 incidencia #186 requisito 1: la
misma batería pasa con la implementación en memoria de A1 y con el almacén
durable de A2, sin tocar los cuerpos de las pruebas).
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.domain.run import Run
from sirius_engine.domain.work_item import WorkItem, WorkItemClass
from sirius_engine.ports.store import WorkEngineStore


def _make_in_memory_store(tmp_path: Path) -> WorkEngineStore:
    return InMemoryWorkEngineStore()


def _make_durable_store(tmp_path: Path) -> WorkEngineStore:
    return DurableWorkEngineStore(tmp_path / "diario.jsonl")


#: Every store implementation the contract tests must pass against (A2
#: incidencia #186, requisito 1). Adding a future substitute means adding one
#: factory here — no test body changes.
STORE_FACTORIES = (_make_in_memory_store, _make_durable_store)


def pytest_configure(config: pytest.Config) -> None:
    """Añadir la raíz del repo a ``sys.path``.

    ``experiments/`` vive fuera de ``src/`` (que sí está en ``sys.path`` vía
    el ``.pth`` que instala ``uv sync``). Con ``--import-mode=importlib``,
    pytest no añade la raíz del repo por sí solo, así que
    ``tests/engine/test_spike_i3_durability.py`` (incidencia #182, requisito
    3) no podría importar ``experiments.work_engine_spike_i3`` sin esto.
    """
    repo_root = str(Path(__file__).resolve().parents[2])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


MakeWorkItem = Callable[..., WorkItem]
MakeRun = Callable[..., Run]


@pytest.fixture(params=STORE_FACTORIES, ids=lambda factory: factory.__name__)
def store(request: pytest.FixtureRequest, tmp_path: Path) -> WorkEngineStore:
    factory: Callable[[Path], WorkEngineStore] = request.param
    return factory(tmp_path)


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
