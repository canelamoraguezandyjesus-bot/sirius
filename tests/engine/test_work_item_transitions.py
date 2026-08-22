"""WorkItem state machine: illegal transitions and legal sequences (incidencia #177).

Requisito 1: toda transición fuera del grafo aprobado (arquitectura §3.2)
falla explícitamente — se comprueba de forma EXHAUSTIVA: cada operación
desde cada estado. Requisito 2: al menos un recorrido legal completo, más
WAITING, PAUSED/reanudación y FAILED_SAFELY.

Dos tablas, dos ejes (defecto H-8, incidencia #219, ADR-058)
------------------------------------------------------------

Este fichero tenía UNA tabla, de estados, y ocho operaciones con guarda de
estado se quedaron fuera de ella: ``change_scope`` y ``reprioritize`` -que
rechazan los estados terminales- y las seis del ciclo de fases, que llevan
``_require(ACTIVE)`` **además** de su guarda de fase y por eso se leían como
"operaciones de fase" y nadie las cruzó contra los ocho estados.

El problema de diseño que eso destapó, y por el que H-8 no se cerró el día que
se encontró: seis de las ocho exigen estado **y** fase a la vez, y la tabla solo
modelaba estados. La solución adoptada (ADR-058) es que la fase entre como
coordenada **dependiente**, no como una dimensión más:

- **Tabla A** -``test_only_approved_operations_succeed_from_each_state``-
  pregunta *¿desde qué ESTADOS es legal esta operación?*. La fase es entonces
  una variable molesta, y hay que fijarla en el valor que impide que la guarda
  de fase salte antes que la de estado: cada operación declara en
  ``FASE_DEL_ENSAYO`` la fase en la que se la ensaya.
- **Tabla B** -``test_only_approved_phase_operations_succeed_from_each_phase``-
  pregunta *¿desde qué FASES es legal esta operación de fase?*, con el estado
  fijado en ``ACTIVE``.

El cruce completo estado x fase x operación son 960 casillas, y la mayoría no
pregunta nada nuevo: 13 de las 20 operaciones no miran la fase, así que sus seis
variantes de fase serían el mismo ensayo repetido seis veces. Una tabla que
nadie lee deja de guardar; el detalle está en ADR-058.

El límite honesto de la tabla A está dicho en
``test_las_casillas_sin_fase_preparable_son_exactamente_estas``: hay doce
casillas en las que la fase del ensayo no se puede preparar.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest

from sirius_engine.domain.errors import IllegalPhaseTransitionError, IllegalTransitionError
from sirius_engine.domain.work_item import WorkItem, WorkItemPhase, WorkItemState
from sirius_engine.ports.store import WorkEngineStore

from .conftest import MakeWorkItem

Operation = Callable[[WorkEngineStore, str, datetime], WorkItem]
Arranger = Callable[[WorkEngineStore, MakeWorkItem, str, datetime, WorkItemPhase], None]


def _op_activate(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.activate_work_item(work_id, now=now)


def _op_cancel(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.cancel_work_item(work_id, now=now)


def _op_escalate(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.escalate_work_item(work_id, now=now)


def _op_resolve_continue(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.resolve_work_item_decision(work_id, continuar=True, now=now)


def _op_resolve_cancel(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.resolve_work_item_decision(work_id, continuar=False, now=now)


def _op_dispatch_async(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.dispatch_work_item_async(work_id, now=now)


def _op_observe_external_fact(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.observe_work_item_external_fact(work_id, now=now)


def _op_fail_safely(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.fail_work_item_safely(work_id, diagnostico="sin progreso posible", now=now)


def _op_reactivate(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.reactivate_work_item(work_id, now=now)


def _op_deliver(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.deliver_work_item(work_id, resultado={"entregado": True}, now=now)


def _op_pause(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.pause_work_item(work_id, now=now)


def _op_resume(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.resume_work_item(work_id, now=now)


# -- Las ocho que faltaban (H-8, incidencia #219) --------------------------------------


def _op_begin_execution(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.begin_work_item_execution(work_id, now=now)


def _op_begin_check(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.begin_work_item_check(work_id, now=now)


def _op_begin_review(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.begin_work_item_review(work_id, now=now)


def _op_approve_review(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.approve_work_item_review(work_id, now=now)


def _op_request_repair(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.request_work_item_repair(work_id, now=now)


def _op_resume_after_repair(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.resume_work_item_after_repair(work_id, now=now)


def _op_change_scope(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.change_work_item_scope(work_id, now=now, objetivo="objetivo revisado")


def _op_reprioritize(store: WorkEngineStore, work_id: str, now: datetime) -> WorkItem:
    return store.reprioritize_work_item(work_id, prioridad=7, now=now)


OPERATIONS: dict[str, Operation] = {
    "activate": _op_activate,
    "cancel": _op_cancel,
    "escalate": _op_escalate,
    "resolve_decision_continue": _op_resolve_continue,
    "resolve_decision_cancel": _op_resolve_cancel,
    "dispatch_async": _op_dispatch_async,
    "observe_external_fact": _op_observe_external_fact,
    "fail_safely": _op_fail_safely,
    "reactivate": _op_reactivate,
    "deliver": _op_deliver,
    "pause": _op_pause,
    "resume": _op_resume,
    # H-8: tienen guarda de estado y nunca estuvieron en esta tabla.
    "begin_execution": _op_begin_execution,
    "begin_check": _op_begin_check,
    "begin_review": _op_begin_review,
    "approve_review": _op_approve_review,
    "request_repair": _op_request_repair,
    "resume_after_repair": _op_resume_after_repair,
    "change_scope": _op_change_scope,
    "reprioritize": _op_reprioritize,
}

#: Las operaciones que ADEMÁS de la guarda de estado tienen guarda de fase
#: (``_require_phase``). Escritas a mano aquí, y contrastadas contra el código
#: con ``ast`` por ``test_ninguna_operacion_de_fase_se_queda_fuera_de_la_tabla``
#: en ``test_politicas_por_estado.py``: una lista a mano que nadie contrasta se
#: queda obsoleta en silencio, que es exactamente cómo nació H-8.
OPERACIONES_CON_GUARDA_DE_FASE = frozenset(
    {
        "begin_execution",
        "begin_check",
        "begin_review",
        "approve_review",
        "request_repair",
        "resume_after_repair",
        "deliver",
    }
)

#: La fase en la que la tabla A ensaya cada operación: **la única en la que su
#: guarda de fase no salta**. Sin esto, la casilla no probaría nada de lo que
#: cree probar: ``begin_check`` desde ``WAITING`` en fase ``PREPARAR`` lanza
#: igual con y sin ``_require(ACTIVE)`` -solo cambia el tipo del error-, así que
#: la casilla sería vacua para la guarda de estado, que es lo que la tabla A
#: mide. Las operaciones sin guarda de fase se ensayan en ``PREPARAR``, la fase
#: inicial, porque no la miran.
FASE_DEL_ENSAYO: dict[str, WorkItemPhase] = {
    "activate": WorkItemPhase.PREPARAR,
    "cancel": WorkItemPhase.PREPARAR,
    "escalate": WorkItemPhase.PREPARAR,
    "resolve_decision_continue": WorkItemPhase.PREPARAR,
    "resolve_decision_cancel": WorkItemPhase.PREPARAR,
    "dispatch_async": WorkItemPhase.PREPARAR,
    "observe_external_fact": WorkItemPhase.PREPARAR,
    "fail_safely": WorkItemPhase.PREPARAR,
    "reactivate": WorkItemPhase.PREPARAR,
    "pause": WorkItemPhase.PREPARAR,
    "resume": WorkItemPhase.PREPARAR,
    "change_scope": WorkItemPhase.PREPARAR,
    "reprioritize": WorkItemPhase.PREPARAR,
    # Con guarda de fase: cada una en la fase que su guarda acepta (§3.4).
    "begin_execution": WorkItemPhase.PREPARAR,
    "begin_check": WorkItemPhase.EJECUTAR,
    "begin_review": WorkItemPhase.COMPROBAR,
    "approve_review": WorkItemPhase.REVISAR,
    "request_repair": WorkItemPhase.REVISAR,
    "resume_after_repair": WorkItemPhase.REPARAR,
    "deliver": WorkItemPhase.ENTREGAR,
}

#: Toda operación que no versiona ni cambia de estado sigue siendo legal
#: mientras el trabajo no haya terminado: §3.2 dice que ``cambiar alcance`` y
#: ``repriorizar`` valen "desde cualquier estado no terminal".
_NO_TERMINALES = frozenset({"change_scope", "reprioritize"})

#: The approved graph of arquitectura §3.2 (+ §3.4 para las de fase), hardcoded
#: independently of the implementation so this test can actually catch a wrong
#: guard. Cada operación de fase aparece aquí solo bajo ``ACTIVE`` porque todas
#: llevan ``_require(ACTIVE)``; en qué fase son legales lo dice ``LEGAL_PHASE_FROM``.
LEGAL_FROM: dict[WorkItemState, frozenset[str]] = {
    WorkItemState.PLANNED: frozenset({"activate", "cancel", "pause"}) | _NO_TERMINALES,
    WorkItemState.ACTIVE: frozenset(
        {
            "escalate",
            "dispatch_async",
            "fail_safely",
            "deliver",
            "pause",
            "begin_execution",
            "begin_check",
            "begin_review",
            "approve_review",
            "request_repair",
            "resume_after_repair",
        }
    )
    | _NO_TERMINALES,
    WorkItemState.WAITING: frozenset({"observe_external_fact", "pause"}) | _NO_TERMINALES,
    WorkItemState.NEEDS_DECISION: frozenset(
        {"resolve_decision_continue", "resolve_decision_cancel"}
    )
    | _NO_TERMINALES,
    WorkItemState.PAUSED: frozenset({"resume"}) | _NO_TERMINALES,
    WorkItemState.FAILED_SAFELY: frozenset({"reactivate", "cancel"}) | _NO_TERMINALES,
    WorkItemState.CANCELLED: frozenset(),
    WorkItemState.DELIVERED: frozenset(),
}

#: El ciclo revisar-reparar de §3.4, escrito a mano igual que ``LEGAL_FROM``:
#: ``PREPARAR -> EJECUTAR -> COMPROBAR -> REVISAR -> (REPARAR -> COMPROBAR ->
#: REVISAR)* -> ENTREGAR``. Es el oráculo de la tabla B.
LEGAL_PHASE_FROM: dict[WorkItemPhase, frozenset[str]] = {
    WorkItemPhase.PREPARAR: frozenset({"begin_execution"}),
    WorkItemPhase.EJECUTAR: frozenset({"begin_check"}),
    # Dos salidas: si las validaciones pasan se revisa; si fallan se repara sin
    # pasar por revisión — lo que hace la vía GitHub en cada CI roja.
    WorkItemPhase.COMPROBAR: frozenset({"begin_review", "request_repair"}),
    WorkItemPhase.REVISAR: frozenset({"approve_review", "request_repair"}),
    WorkItemPhase.REPARAR: frozenset({"resume_after_repair"}),
    WorkItemPhase.ENTREGAR: frozenset({"deliver"}),
}

#: Los dos estados que admiten UNA sola fase, y cuál.
#:
#: Esto es un ARGUMENTO, no una búsqueda exhaustiva de caminos, y conviene que
#: se lea como tal (ADR-036: «no pude» y «no hay» no son lo mismo). Sus patas:
#:
#: ``PLANNED``. La fase solo avanza con las seis operaciones del ciclo, y las
#: seis exigen ``ACTIVE`` -lo fija la tabla A-. La única otra operación que toca
#: la fase es ``change_scope``, que la devuelve a ``PREPARAR``
#: (``tests/engine/test_phase_cycle.py``,
#: ``test_scope_change_forces_redo_from_any_phase_including_mid_cycle``). Y el
#: único camino de vuelta a ``PLANNED`` es reanudar una pausa tomada en
#: ``PLANNED``, y ni ``pause`` ni ``resume`` cambian la fase
#: (``test_pausar_y_reanudar_conservan_la_fase``).
#:
#: ``DELIVERED``. Solo se entra con ``deliver``, que exige fase ``ENTREGAR``
#: (tabla B) y no la cambia, y no se sale nunca
#: (``test_no_operation_ever_leaves_a_terminal_state``).
FASE_UNICA: dict[WorkItemState, WorkItemPhase] = {
    WorkItemState.PLANNED: WorkItemPhase.PREPARAR,
    WorkItemState.DELIVERED: WorkItemPhase.ENTREGAR,
}


def _fase_a_preparar(state: WorkItemState, operation_name: str) -> WorkItemPhase:
    """La fase en que se ensaya esta casilla, o la única que el estado admite."""
    unica = FASE_UNICA.get(state)
    return FASE_DEL_ENSAYO[operation_name] if unica is None else unica


def _llevar_a_fase(
    store: WorkEngineStore, work_id: str, now: datetime, fase: WorkItemPhase
) -> None:
    """Recorre el ciclo de §3.4 desde ``PREPARAR`` hasta ``fase``.

    Exige que el WorkItem esté en ``ACTIVE``: son las seis operaciones de fase,
    y todas llevan ``_require(ACTIVE)``. Solo recorre casillas legales, así que
    quitarle una guarda al dominio no rompe la preparación -rompe la casilla
    que la mide, que es de lo que se trata.
    """
    if fase is WorkItemPhase.PREPARAR:
        return
    store.begin_work_item_execution(work_id, now=now)
    if fase is WorkItemPhase.EJECUTAR:
        return
    store.begin_work_item_check(work_id, now=now)
    if fase is WorkItemPhase.COMPROBAR:
        return
    store.begin_work_item_review(work_id, now=now)
    if fase is WorkItemPhase.REVISAR:
        return
    if fase is WorkItemPhase.REPARAR:
        store.request_work_item_repair(work_id, now=now)
        return
    store.approve_work_item_review(work_id, now=now)


def _to_planned(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    work_id: str,
    now: datetime,
    fase: WorkItemPhase,
) -> None:
    # PLANNED solo admite PREPARAR (ver FASE_UNICA): `fase` se ignora aquí a
    # propósito, y la tabla comprueba después en qué fase quedó de verdad.
    make_work_item(now=now, work_id=work_id)


def _to_active(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    work_id: str,
    now: datetime,
    fase: WorkItemPhase,
) -> None:
    _to_planned(store, make_work_item, work_id, now, WorkItemPhase.PREPARAR)
    store.activate_work_item(work_id, now=now)
    _llevar_a_fase(store, work_id, now, fase)


def _to_waiting(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    work_id: str,
    now: datetime,
    fase: WorkItemPhase,
) -> None:
    _to_active(store, make_work_item, work_id, now, fase)
    store.dispatch_work_item_async(work_id, now=now)


def _to_needs_decision(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    work_id: str,
    now: datetime,
    fase: WorkItemPhase,
) -> None:
    _to_active(store, make_work_item, work_id, now, fase)
    store.escalate_work_item(work_id, now=now)


def _to_paused(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    work_id: str,
    now: datetime,
    fase: WorkItemPhase,
) -> None:
    _to_active(store, make_work_item, work_id, now, fase)
    store.pause_work_item(work_id, now=now)


def _to_failed_safely(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    work_id: str,
    now: datetime,
    fase: WorkItemPhase,
) -> None:
    _to_active(store, make_work_item, work_id, now, fase)
    store.fail_work_item_safely(work_id, diagnostico="sin progreso posible", now=now)


def _to_cancelled(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    work_id: str,
    now: datetime,
    fase: WorkItemPhase,
) -> None:
    if fase is WorkItemPhase.PREPARAR:
        # El camino corto de §3.2, que es el que tenía esta tabla.
        _to_planned(store, make_work_item, work_id, now, fase)
        store.cancel_work_item(work_id, now=now)
        return
    # Para el resto de fases hay que pasar por FAILED_SAFELY: cancelar desde
    # PLANNED no puede traer una fase avanzada, y ni `fail_safely` ni `cancel`
    # tocan la fase.
    _to_failed_safely(store, make_work_item, work_id, now, fase)
    store.cancel_work_item(work_id, now=now)


def _to_delivered(
    store: WorkEngineStore,
    make_work_item: MakeWorkItem,
    work_id: str,
    now: datetime,
    fase: WorkItemPhase,
) -> None:
    # DELIVERED solo admite ENTREGAR (ver FASE_UNICA): `deliver` la exige y no
    # la cambia.
    _to_active(store, make_work_item, work_id, now, WorkItemPhase.ENTREGAR)
    store.deliver_work_item(work_id, resultado={"entregado": True}, now=now)


ARRANGERS: dict[WorkItemState, Arranger] = {
    WorkItemState.PLANNED: _to_planned,
    WorkItemState.ACTIVE: _to_active,
    WorkItemState.WAITING: _to_waiting,
    WorkItemState.NEEDS_DECISION: _to_needs_decision,
    WorkItemState.PAUSED: _to_paused,
    WorkItemState.FAILED_SAFELY: _to_failed_safely,
    WorkItemState.CANCELLED: _to_cancelled,
    WorkItemState.DELIVERED: _to_delivered,
}


@pytest.mark.parametrize("state", list(WorkItemState), ids=lambda s: s.value)
def test_only_approved_operations_succeed_from_each_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime, state: WorkItemState
) -> None:
    """Tabla A: cada operación contra cada estado, 20 x 8 = 160 casillas."""
    for operation_name, operation in OPERATIONS.items():
        work_id = f"WI-{state.value}-{operation_name}"
        fase = _fase_a_preparar(state, operation_name)
        ARRANGERS[state](store, make_work_item, work_id, now, fase)

        preparado = store.get_work_item(work_id)
        assert preparado is not None, f"el preparador de {state.value} no dejó WorkItem"
        assert preparado.estado is state and preparado.fase is fase, (
            f"la casilla ({state.value}, {operation_name}) se iba a medir sobre "
            f"({preparado.estado.value}, {preparado.fase.value}) en vez de sobre "
            f"({state.value}, {fase.value})"
        )

        if operation_name in LEGAL_FROM[state]:
            operation(store, work_id, now)  # must not raise
        else:
            with pytest.raises(IllegalTransitionError) as excinfo:
                operation(store, work_id, now)
            assert excinfo.value.current_state == state


@pytest.mark.parametrize("fase", list(WorkItemPhase), ids=lambda f: f.value)
def test_only_approved_phase_operations_succeed_from_each_phase(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime, fase: WorkItemPhase
) -> None:
    """Tabla B: cada operación con guarda de fase contra cada fase, con el estado en ACTIVE.

    El eje que la tabla A no puede medir. Aquí lo que se exige es
    ``IllegalPhaseTransitionError``, no la de estado: quitarle el
    ``_require_phase`` a una de estas seis hace fallar esta tabla igual que
    quitarle el ``_require(ACTIVE)`` hace fallar la otra.
    """
    for operation_name in sorted(OPERACIONES_CON_GUARDA_DE_FASE):
        work_id = f"WI-FASE-{fase.value}-{operation_name}"
        _to_active(store, make_work_item, work_id, now, fase)

        preparado = store.get_work_item(work_id)
        assert preparado is not None
        assert preparado.estado is WorkItemState.ACTIVE and preparado.fase is fase, (
            f"la casilla ({fase.value}, {operation_name}) se iba a medir sobre "
            f"({preparado.estado.value}, {preparado.fase.value})"
        )

        operation = OPERATIONS[operation_name]
        if operation_name in LEGAL_PHASE_FROM[fase]:
            operation(store, work_id, now)  # must not raise
        else:
            with pytest.raises(IllegalPhaseTransitionError) as excinfo:
                operation(store, work_id, now)
            assert excinfo.value.current_phase == fase


def test_no_operation_ever_leaves_a_terminal_state() -> None:
    for state in (WorkItemState.CANCELLED, WorkItemState.DELIVERED):
        assert LEGAL_FROM[state] == frozenset()


# -- Que las tablas no puedan volverse vacuas ------------------------------------------


def test_toda_operacion_declara_la_fase_en_que_se_la_ensaya() -> None:
    """Una operación nueva sin fase declarada se ensayaría en una fase por azar."""
    assert sorted(FASE_DEL_ENSAYO) == sorted(OPERATIONS)


def test_la_fase_del_ensayo_es_la_que_la_guarda_de_fase_acepta() -> None:
    """Si no lo fuera, la casilla de la tabla A mediría la guarda equivocada.

    Se contrasta contra ``LEGAL_PHASE_FROM``, que es el oráculo escrito a mano
    de §3.4, no contra el código: si alguien cambia la guarda del dominio y
    ajusta ``FASE_DEL_ENSAYO`` para que siga pasando, esto lo dice.
    """
    legal_en: dict[str, set[WorkItemPhase]] = {
        nombre: {f for f, ops in LEGAL_PHASE_FROM.items() if nombre in ops}
        for nombre in OPERACIONES_CON_GUARDA_DE_FASE
    }
    mal = sorted(n for n, fases in legal_en.items() if FASE_DEL_ENSAYO[n] not in fases)
    assert mal == [], f"se ensayan en una fase en la que su guarda de fase salta: {mal}"


def test_la_tabla_de_fases_nombra_a_todas_las_operaciones_con_guarda_de_fase() -> None:
    """Un hueco aquí es una operación de fase que nadie cruza contra las seis fases."""
    nombradas = {nombre for ops in LEGAL_PHASE_FROM.values() for nombre in ops}
    assert nombradas == OPERACIONES_CON_GUARDA_DE_FASE
    assert sorted(LEGAL_PHASE_FROM) == sorted(WorkItemPhase)


def test_las_dos_guardas_lanzan_errores_que_no_se_confunden() -> None:
    """Supuesto de diseño del que dependen doce casillas de la tabla A.

    En las casillas donde la fase del ensayo no se puede preparar (ver
    ``test_las_casillas_sin_fase_preparable_son_exactamente_estas``), lo único
    que distingue «saltó la guarda de estado» de «saltó la guarda de fase» es
    el TIPO del error. El día que uno sea subclase del otro, esas doce dejan de
    medir la guarda de estado -en silencio. Aquí no, en silencio no.
    """
    assert not issubclass(IllegalPhaseTransitionError, IllegalTransitionError)
    assert not issubclass(IllegalTransitionError, IllegalPhaseTransitionError)


def test_las_casillas_sin_fase_preparable_son_exactamente_estas() -> None:
    """El límite honesto de la tabla A, escrito para que no crezca sin que se note.

    ``PLANNED`` y ``DELIVERED`` admiten una sola fase cada uno (``FASE_UNICA``,
    con el argumento allí). En ellos, una operación con guarda de fase no se
    puede ensayar en la fase que su guarda acepta: la casilla sigue exigiendo
    ``IllegalTransitionError``, pero lo que la sostiene ya no es que la
    operación fuera a tener éxito sin la guarda de estado, sino que sin ella
    lanzaría la de FASE, que es un tipo distinto
    (``test_las_dos_guardas_lanzan_errores_que_no_se_confunden``).

    Son doce, y cada una de las siete operaciones con guarda de fase conserva
    al menos seis casillas plenas en los otros seis estados.
    """
    debiles = sorted(
        (estado.value, nombre)
        for estado, unica in FASE_UNICA.items()
        for nombre in OPERACIONES_CON_GUARDA_DE_FASE
        if FASE_DEL_ENSAYO[nombre] is not unica
    )
    assert debiles == [
        ("delivered", "approve_review"),
        ("delivered", "begin_check"),
        ("delivered", "begin_execution"),
        ("delivered", "begin_review"),
        ("delivered", "request_repair"),
        ("delivered", "resume_after_repair"),
        ("planned", "approve_review"),
        ("planned", "begin_check"),
        ("planned", "begin_review"),
        ("planned", "deliver"),
        ("planned", "request_repair"),
        ("planned", "resume_after_repair"),
    ]


# -- Requisito 2: recorridos legales completos --------------------------------------


def test_full_happy_path_planned_to_delivered(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-HAPPY-PATH"
    created = make_work_item(now=now, work_id=work_id)
    assert created.estado is WorkItemState.PLANNED
    assert created.fase is WorkItemPhase.PREPARAR

    activated = store.activate_work_item(work_id, now=now)
    assert activated.estado is WorkItemState.ACTIVE
    assert activated.fase is WorkItemPhase.PREPARAR

    executing = store.begin_work_item_execution(work_id, now=now)
    assert executing.fase is WorkItemPhase.EJECUTAR

    checking = store.begin_work_item_check(work_id, now=now)
    assert checking.fase is WorkItemPhase.COMPROBAR

    reviewing = store.begin_work_item_review(work_id, now=now)
    assert reviewing.fase is WorkItemPhase.REVISAR

    approved = store.approve_work_item_review(work_id, now=now)
    assert approved.fase is WorkItemPhase.ENTREGAR
    assert approved.estado is WorkItemState.ACTIVE

    delivered = store.deliver_work_item(work_id, resultado={"entregado": True}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED
    assert delivered.resultado == {"entregado": True}


def test_waiting_round_trip_then_delivered(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-WAITING"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    waiting = store.dispatch_work_item_async(work_id, now=now)
    assert waiting.estado is WorkItemState.WAITING

    active_again = store.observe_work_item_external_fact(work_id, now=now)
    assert active_again.estado is WorkItemState.ACTIVE

    store.begin_work_item_execution(work_id, now=now)
    store.begin_work_item_check(work_id, now=now)
    store.begin_work_item_review(work_id, now=now)
    store.approve_work_item_review(work_id, now=now)

    delivered = store.deliver_work_item(work_id, resultado={}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED


def test_pause_resume_round_trip_preserves_prior_state(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-PAUSE"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    paused = store.pause_work_item(work_id, now=now)
    assert paused.estado is WorkItemState.PAUSED
    assert paused.paused_from is WorkItemState.ACTIVE

    resumed = store.resume_work_item(work_id, now=now)
    assert resumed.estado is WorkItemState.ACTIVE
    assert resumed.paused_from is None

    store.begin_work_item_execution(work_id, now=now)
    store.begin_work_item_check(work_id, now=now)
    store.begin_work_item_review(work_id, now=now)
    store.approve_work_item_review(work_id, now=now)

    delivered = store.deliver_work_item(work_id, resultado={}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED


def test_pausar_y_reanudar_conservan_la_fase(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    """Una pata del argumento de ``FASE_UNICA``: pausar no es rehacer.

    Si ``pause`` o ``resume`` tocaran la fase, ``PLANNED`` podría llegar a
    tener una fase avanzada y doce casillas de la tabla A serían más fuertes de
    lo que ``FASE_UNICA`` declara. Peor: ``resume`` devolvería el trabajo a un
    punto del ciclo distinto de donde se paró.
    """
    work_id = "WI-PAUSE-FASE"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)
    store.begin_work_item_execution(work_id, now=now)
    en_curso = store.begin_work_item_check(work_id, now=now)
    assert en_curso.fase is WorkItemPhase.COMPROBAR

    paused = store.pause_work_item(work_id, now=now)
    assert paused.estado is WorkItemState.PAUSED
    assert paused.fase is WorkItemPhase.COMPROBAR

    resumed = store.resume_work_item(work_id, now=now)
    assert resumed.estado is WorkItemState.ACTIVE
    assert resumed.fase is WorkItemPhase.COMPROBAR


def test_pause_from_planned_resumes_to_planned(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-PAUSE-PLANNED"
    make_work_item(now=now, work_id=work_id)

    paused = store.pause_work_item(work_id, now=now)
    assert paused.paused_from is WorkItemState.PLANNED

    resumed = store.resume_work_item(work_id, now=now)
    assert resumed.estado is WorkItemState.PLANNED


def test_failed_safely_round_trip_then_delivered(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-FAILED-SAFELY"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    failed = store.fail_work_item_safely(work_id, diagnostico="dependencia rota", now=now)
    assert failed.estado is WorkItemState.FAILED_SAFELY
    assert failed.diagnostico == "dependencia rota"

    reactivated = store.reactivate_work_item(work_id, now=now)
    assert reactivated.estado is WorkItemState.ACTIVE

    store.begin_work_item_execution(work_id, now=now)
    store.begin_work_item_check(work_id, now=now)
    store.begin_work_item_review(work_id, now=now)
    store.approve_work_item_review(work_id, now=now)

    delivered = store.deliver_work_item(work_id, resultado={}, now=now)
    assert delivered.estado is WorkItemState.DELIVERED


def test_escalation_and_decision_to_continue(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-DECISION-CONTINUE"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)

    escalated = store.escalate_work_item(work_id, now=now)
    assert escalated.estado is WorkItemState.NEEDS_DECISION

    resolved = store.resolve_work_item_decision(work_id, continuar=True, now=now)
    assert resolved.estado is WorkItemState.ACTIVE


def test_escalation_and_decision_to_cancel(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    work_id = "WI-DECISION-CANCEL"
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)
    store.escalate_work_item(work_id, now=now)

    resolved = store.resolve_work_item_decision(work_id, continuar=False, now=now)
    assert resolved.estado is WorkItemState.CANCELLED


# ─────────── Las dos entradas a REPARAR: revisión y comprobación fallida ───────────


def _en_fase(
    store: WorkEngineStore, make_work_item: MakeWorkItem, work_id: str, now: datetime
) -> WorkItem:
    """Un WorkItem ACTIVE en fase COMPROBAR, por el camino legal."""
    make_work_item(now=now, work_id=work_id)
    store.activate_work_item(work_id, now=now)
    store.begin_work_item_execution(work_id, now=now)
    return store.begin_work_item_check(work_id, now=now)


def test_comprobar_puede_ir_a_reparar_sin_pasar_por_revisar(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    """El camino de la CI roja, que el motor no podía representar.

    `advance-sirius-after-quality.yml` pasa de `sirius:ci-pending` a
    `sirius:repair-requested` cuando Quality falla: no hay nada que revisar de
    un cambio que no compila. Sin esta arista el motor tenía que elegir entre
    inventar una fase REVISAR que nunca ocurrió, o quedarse en COMPROBAR
    mientras la incidencia decía REPARAR — una divergencia permanente entre las
    dos fuentes (incidencia #250, hallazgo H-D).
    """
    en_comprobar = _en_fase(store, make_work_item, "WI-COMPROBAR", now)
    assert en_comprobar.fase is WorkItemPhase.COMPROBAR

    reparando = store.request_work_item_repair("WI-COMPROBAR", now=now)
    assert reparando.fase is WorkItemPhase.REPARAR

    # Y el bucle cierra igual por esta entrada que por la de revisión.
    vuelta = store.resume_work_item_after_repair("WI-COMPROBAR", now=now)
    assert vuelta.fase is WorkItemPhase.COMPROBAR


def test_revisar_sigue_pudiendo_ir_a_reparar(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    """No regresión: añadir una entrada no puede quitar la que ya existía."""
    _en_fase(store, make_work_item, "WI-REVISAR", now)
    en_revisar = store.begin_work_item_review("WI-REVISAR", now=now)
    assert en_revisar.fase is WorkItemPhase.REVISAR
    assert store.request_work_item_repair("WI-REVISAR", now=now).fase is WorkItemPhase.REPARAR


def test_reparar_no_puede_entrar_otra_vez_en_reparar(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    """Control negativo: la guarda sigue rechazando lo que no es una entrada."""
    _en_fase(store, make_work_item, "WI-DOBLE", now)
    store.request_work_item_repair("WI-DOBLE", now=now)
    with pytest.raises(IllegalPhaseTransitionError):
        store.request_work_item_repair("WI-DOBLE", now=now)


def test_preparar_y_ejecutar_siguen_sin_poder_reparar(
    store: WorkEngineStore, make_work_item: MakeWorkItem, now: datetime
) -> None:
    """Las otras dos fases que no son entrada legal a REPARAR."""
    make_work_item(now=now, work_id="WI-PREPARAR")
    store.activate_work_item("WI-PREPARAR", now=now)
    with pytest.raises(IllegalPhaseTransitionError):
        store.request_work_item_repair("WI-PREPARAR", now=now)
    store.begin_work_item_execution("WI-PREPARAR", now=now)
    with pytest.raises(IllegalPhaseTransitionError):
        store.request_work_item_repair("WI-PREPARAR", now=now)
