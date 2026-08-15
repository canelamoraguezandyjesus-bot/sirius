"""Cambio de alcance versionado (arquitectura §3.2, incidencia #177 requisito 7).

"Cambio de alcance conserva versión e historial: la versión anterior sigue
siendo legible después del cambio." Reprioritización se cubre aquí también:
no es un estado, no versiona (§3.2).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sirius_engine.domain.errors import IllegalTransitionError
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeWorkItem


def test_scope_change_bumps_version_and_keeps_the_previous_version_readable(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-SCOPE"
    original = make_work_item(now=now, work_id=work_id)
    assert original.version == 1

    later = now + timedelta(hours=1)
    changed = store.change_work_item_scope(
        work_id, now=later, objetivo="objetivo revisado", entregable="entregable revisado"
    )

    assert changed.version == 2
    assert changed.objetivo == "objetivo revisado"
    assert changed.entregable == "entregable revisado"
    assert changed.fase is WorkItemPhase.PREPARAR

    versions = store.list_work_item_versions(work_id)
    assert len(versions) == 2
    first_version, second_version = versions
    assert first_version.version == 1
    assert first_version.objetivo == original.objetivo
    assert first_version.entregable == original.entregable
    assert second_version.version == 2
    assert second_version.objetivo == "objetivo revisado"

    # The current pointer moved on, but the first version object is unmutated.
    assert original.objetivo == "objetivo normalizado y confirmado"


def test_scope_change_only_touches_the_fields_given(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-SCOPE-PARTIAL"
    make_work_item(now=now, work_id=work_id)

    changed = store.change_work_item_scope(work_id, now=now, entregable="solo esto cambia")
    assert changed.entregable == "solo esto cambia"
    assert changed.objetivo == "objetivo normalizado y confirmado"
    assert changed.criterio_terminado == "el entregable existe y pasa sus pruebas"


def test_scope_change_forces_redo_preparar_from_any_phase(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-SCOPE-ACTIVE"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    changed = store.change_work_item_scope(work_id, now=now, objetivo="objetivo nuevo")
    assert changed.estado is WorkItemState.ACTIVE
    assert changed.fase is WorkItemPhase.PREPARAR


def test_scope_change_rejected_from_a_terminal_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-SCOPE-TERMINAL"
    make_work_item(now=now, work_id=work_id)
    store.cancel_work_item(work_id, now=now)

    with pytest.raises(IllegalTransitionError):
        store.change_work_item_scope(work_id, now=now, objetivo="demasiado tarde")


# -- Repriorización: no es un estado, no versiona -------------------------------------


def test_reprioritize_does_not_bump_version_or_change_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-REPRIORITIZE"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    reprioritized = store.reprioritize_work_item(work_id, prioridad=9, now=now)
    assert reprioritized.prioridad == 9
    assert reprioritized.version == 1
    assert reprioritized.estado is WorkItemState.ACTIVE
