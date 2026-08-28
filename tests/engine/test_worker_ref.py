"""Con qué se ejecutó cada Run: adapter, perfil y modelo/runtime (§3.3, H-6, ADR-054).

La arquitectura §3.3 define el campo ``worker`` de un Run como «adapter +
perfil + (si aplica) modelo/runtime concretos usados». Mientras fue una
cadena libre, el motor no podía comparar dos Runs por modelo, ni explicar
una sustitución de Worker en términos de con qué se ejecutó, ni sostener
ninguna afirmación sobre qué modelo hizo qué (incidencia #217).

Estas pruebas fijan esa propiedad. Todas menos las dos últimas corren contra
cada implementación del puerto (``STORE_FACTORIES`` en ``conftest``); las dos
últimas necesitan reabrir un diario en disco y construyen el almacén durable
directamente, como ya hace ``test_durable_journal.py``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.domain.errors import WorkerRuntimeConflictError
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.domain.worker_ref import WorkerRef
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeRun

_PERFIL = "perfiles/corrector"


def _worker(**overrides: Any) -> WorkerRef:
    campos: dict[str, Any] = {
        "adapter": "claude-code",
        "perfil_ref": _PERFIL,
        "perfil_version": 2,
    }
    campos.update(overrides)
    return WorkerRef(**campos)


def test_un_run_dice_con_que_modelo_y_runtime_se_ejecuto(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    """El dato nace cuando el Worker acepta el encargo, y el Run lo conserva.

    ``DISPATCHED -> RUNNING`` es, según §3.3, el instante en que ``STATUS``
    confirma que el Worker aceptó: es ahí donde un Worker remoto revela con
    qué modelo va a ejecutar, así que es ahí donde se anota.
    """
    make_run(run_id="RUN-1", now=now, deadline=now + timedelta(hours=1), worker=_worker())
    store.dispatch_run("RUN-1", now=now)

    corriendo = store.confirm_run_running(
        "RUN-1", now=now, modelo="claude-opus-5", runtime="claude-code-cli-2.4"
    )

    assert corriendo.worker.adapter == "claude-code"
    assert corriendo.worker.perfil_ref == _PERFIL
    assert corriendo.worker.perfil_version == 2
    assert corriendo.worker.modelo == "claude-opus-5"
    assert corriendo.worker.runtime == "claude-code-cli-2.4"


def test_dos_runs_del_mismo_perfil_se_comparan_por_modelo(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    """La pregunta que H-6 impedía contestar: ¿rinde igual el modelo barato?

    Requiere poder decir que dos Runs comparten adapter y perfil y difieren
    SOLO en el modelo. Con una cadena libre no hay nada que comparar.
    """
    deadline = now + timedelta(hours=1)
    for run_id, modelo in (("RUN-CARO", "claude-opus-5"), ("RUN-BARATO", "claude-haiku-4")):
        make_run(run_id=run_id, now=now, deadline=deadline, worker=_worker())
        store.dispatch_run(run_id, now=now)
        store.confirm_run_running(run_id, now=now, modelo=modelo)

    caro = store.get_run("RUN-CARO")
    barato = store.get_run("RUN-BARATO")
    assert caro is not None and barato is not None

    assert caro.worker.same_profile(barato.worker)
    assert caro.worker != barato.worker
    assert {run.worker.modelo for run in store.list_runs_for_work_item("WI-0001")} == {
        "claude-opus-5",
        "claude-haiku-4",
    }


def test_la_sustitucion_de_worker_se_explica_por_el_modelo(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    """Sustituir el modelo dejando adapter y perfil intactos es una sustitución legítima.

    Y el Run anterior conserva el modelo con el que él se ejecutó: la
    sustitución queda explicada en términos de con qué corrió cada uno.
    """
    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-1", now=now, deadline=deadline, worker=_worker())
    store.dispatch_run("RUN-1", now=now)
    store.confirm_run_running("RUN-1", now=now, modelo="claude-opus-5")
    store.fail_run("RUN-1", diagnostico="agotó el presupuesto de turnos", now=now)

    sustituto = store.substitute_run_worker(
        "RUN-1",
        new_run_id="RUN-2",
        worker=_worker(modelo="claude-haiku-4"),
        motivo="probar si el modelo barato basta para este paso",
        deadline=deadline + timedelta(hours=1),
        now=now,
    )

    anterior = store.get_run("RUN-1")
    assert anterior is not None
    assert anterior.worker.modelo == "claude-opus-5"
    assert sustituto.worker.modelo == "claude-haiku-4"
    assert sustituto.worker.same_profile(anterior.worker)
    assert sustituto.sustituye_a == "RUN-1"
    assert sustituto.motivo_sustitucion == "probar si el modelo barato basta para este paso"


def test_un_reintento_no_hereda_el_modelo_del_intento_anterior(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    """Un Run recién PREPARADO no puede afirmar con qué modelo se ejecutó: aún no lo hizo.

    Heredar el modelo del intento anterior sería afirmar más de lo que el
    dato sostiene. El adapter y el perfil sí se heredan: son la elección
    del llamador, no una observación.
    """
    deadline = now + timedelta(hours=1)
    make_run(run_id="RUN-1", now=now, deadline=deadline, worker=_worker())
    store.dispatch_run("RUN-1", now=now)
    store.confirm_run_running("RUN-1", now=now, modelo="claude-opus-5", runtime="cli-2.4")
    store.fail_run("RUN-1", diagnostico="timeout de red", now=now)

    reintento = store.retry_run(
        "RUN-1", new_run_id="RUN-2", deadline=deadline + timedelta(hours=1), now=now
    )

    assert reintento.intento == 2
    assert reintento.worker.adapter == "claude-code"
    assert reintento.worker.perfil_ref == _PERFIL
    assert reintento.worker.perfil_version == 2
    assert reintento.worker.modelo is None
    assert reintento.worker.runtime is None


def test_un_run_no_puede_reescribir_con_que_modelo_se_ejecuto(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    """Si el modelo ya consta, anotar otro distinto falla en vez de sobrescribir."""
    make_run(
        run_id="RUN-1",
        now=now,
        deadline=now + timedelta(hours=1),
        worker=_worker(modelo="claude-opus-5"),
    )
    store.dispatch_run("RUN-1", now=now)

    with pytest.raises(WorkerRuntimeConflictError):
        store.confirm_run_running("RUN-1", now=now, modelo="claude-haiku-4")


def test_anotar_el_mismo_modelo_que_ya_constaba_no_es_conflicto(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    """Confirmar lo que ya se sabía no es reescribir: no hay nada que contradecir."""
    make_run(
        run_id="RUN-1",
        now=now,
        deadline=now + timedelta(hours=1),
        worker=_worker(modelo="claude-opus-5"),
    )
    store.dispatch_run("RUN-1", now=now)

    corriendo = store.confirm_run_running("RUN-1", now=now, modelo="claude-opus-5")

    assert corriendo.worker.modelo == "claude-opus-5"


def test_no_anotar_nada_deja_el_modelo_desconocido(
    store: WorkEngineStore, make_run: MakeRun, now: datetime
) -> None:
    """``None`` es «no se sabe», y se conserva como tal (ADR-036).

    No se rellena con el adapter, ni con el perfil, ni con una cadena vacía:
    un dato ausente no puede disfrazarse de dato presente.
    """
    make_run(run_id="RUN-1", now=now, deadline=now + timedelta(hours=1), worker=_worker())
    store.dispatch_run("RUN-1", now=now)

    corriendo = store.confirm_run_running("RUN-1", now=now)

    assert corriendo.worker.modelo is None
    assert corriendo.worker.runtime is None


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("adapter", ""),
        ("adapter", "   "),
        ("perfil_ref", ""),
        ("perfil_ref", "   "),
        ("modelo", ""),
        ("modelo", "   "),
        ("runtime", ""),
        ("runtime", "   "),
    ],
)
def test_un_worker_mal_formado_es_inconstruible(campo: str, valor: str) -> None:
    """La forma la impide el tipo, no un revisor: no hay ``WorkerRef`` vacío que crear."""
    with pytest.raises(ValueError):
        _worker(**{campo: valor})


@pytest.mark.parametrize("version", [0, -1])
def test_un_perfil_sin_version_valida_es_inconstruible(version: int) -> None:
    """Sin versión de perfil no se puede comparar: la v1 y la v2 no son el mismo perfil."""
    with pytest.raises(ValueError):
        _worker(perfil_version=version)


def _preparar_run_durable(store: DurableWorkEngineStore, *, now: datetime) -> None:
    # H-27: el padre tiene que existir y estar en curso antes del intento.
    store.create_work_item(
        work_id="WI-0001",
        peticion_original="p",
        objetivo="objetivo normalizado y confirmado",
        contexto_origen=("incidencia:177",),
        entregable="e",
        criterio_terminado="c",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=now,
        plan=("paso-1",),
    )
    store.activate_work_item("WI-0001", now=now)
    store.prepare_run(
        run_id="RUN-1",
        work_id="WI-0001",
        paso="paso-1",
        worker=_worker(),
        work_package={"instrucciones": "instantánea de prueba"},
        deadline=now + timedelta(hours=1),
        now=now,
    )
    store.dispatch_run("RUN-1", now=now)


def test_el_modelo_sobrevive_al_reinicio_del_almacen_durable(tmp_path: Path, now: datetime) -> None:
    """El dato solo sirve si sigue ahí mañana: se persiste y se recupera entero.

    Si el diario guardara solo el adapter, la respuesta a «¿qué modelo hizo
    esto?» se perdería en el primer reinicio, que es justo el fallo que H-6
    describe como irrecuperable si se llega a B1/C2 sin haberlo diseñado.
    """
    diario = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(diario)
    _preparar_run_durable(store, now=now)
    store.confirm_run_running("RUN-1", now=now, modelo="claude-opus-5", runtime="cli-2.4")

    reabierto = DurableWorkEngineStore(diario)
    recuperado = reabierto.get_run("RUN-1")

    assert recuperado is not None
    assert recuperado.worker == _worker(modelo="claude-opus-5", runtime="cli-2.4")


def test_un_worker_sin_modelo_sobrevive_al_reinicio_como_desconocido(
    tmp_path: Path, now: datetime
) -> None:
    """Round-trip del caso de hoy: sin Worker real, el modelo se persiste como ``None``."""
    diario = tmp_path / "diario.jsonl"
    store = DurableWorkEngineStore(diario)
    _preparar_run_durable(store, now=now)

    reabierto = DurableWorkEngineStore(diario)
    recuperado = reabierto.get_run("RUN-1")

    assert recuperado is not None
    assert recuperado.worker == _worker()
    assert recuperado.worker.modelo is None
