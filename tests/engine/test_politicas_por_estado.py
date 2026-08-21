"""Tabla exhaustiva de la capa de POLÍTICA: cada función contra cada estado.

Por qué existe. El defecto H-3 -el corte por presupuesto no salía de
``WAITING``- sobrevivió a la batería completa, a dos revisores independientes y
a cinco rondas de corrección, y entró en ``main``. Su hermano H-7, en el mismo
fichero, sobrevivió además a la corrección de H-3. Los dos son el mismo error:

    una función de política da por supuesto en qué estado está el trabajo,
    y sus pruebas solo la arrancan desde el estado feliz.

Una capa más abajo esto ya no puede pasar: ``test_work_item_transitions.py``
recorre cada operación del dominio contra cada estado, y añadir un estado nuevo
rompe la batería hasta que alguien rellene la casilla. Lo que no tenía esa tabla
era **la capa que llama a las reglas**. Ahí vivían los dos defectos.

Esto es esa tabla. Y la propiedad que fija no es un detalle de cada política,
sino una invariante de todas: **ninguna política puede lanzar
``IllegalTransitionError`` desde ningún estado**. Una política que revienta deja
el trabajo a medias -Run muerto, WorkItem esperando para siempre- que es
exactamente lo que hicieron H-3 y H-7.

No razona ni llama a ningún modelo: es una tabla y un bucle.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from sirius_engine.domain.budget import Budget
from sirius_engine.domain.errors import IllegalTransitionError
from sirius_engine.domain.work_item import WorkItemClass, WorkItemState
from sirius_engine.governance import registrar_gasto, resolver_fallo_tecnico
from sirius_engine.ports.store import WorkEngineStore

_NOW = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
_DEADLINE = _NOW + timedelta(hours=1)

_WORK_ID = "WI-POL"
_RUN_ID = "RUN-POL"


def _crear_con_run_vivo(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    """Deja el WorkItem en ACTIVE y un Run suyo corriendo."""
    store.create_work_item(
        work_id=work_id,
        peticion_original="peticion",
        objetivo="objetivo",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={"presupuesto": {"limite": 10.0}},
        prioridad=1,
        clase=WorkItemClass.INVESTIGACION,
        now=_NOW,
    )
    store.activate_work_item(work_id, now=_NOW)
    store.prepare_run(
        run_id=run_id,
        work_id=work_id,
        paso="paso",
        worker="worker-de-prueba",
        work_package={},
        deadline=_DEADLINE,
        now=_NOW,
    )
    store.dispatch_run(run_id, now=_NOW)
    store.confirm_run_running(run_id, now=_NOW)


Preparador = Callable[[WorkEngineStore, str, str], None]


def _planned(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    store.create_work_item(
        work_id=work_id,
        peticion_original="peticion",
        objetivo="objetivo",
        contexto_origen=(),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={"presupuesto": {"limite": 10.0}},
        prioridad=1,
        clase=WorkItemClass.INVESTIGACION,
        now=_NOW,
    )


def _active(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    _crear_con_run_vivo(store, work_id, run_id)


def _waiting(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    _crear_con_run_vivo(store, work_id, run_id)
    store.dispatch_work_item_async(work_id, now=_NOW)


def _needs_decision(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    _crear_con_run_vivo(store, work_id, run_id)
    store.escalate_work_item(work_id, now=_NOW)


def _paused(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    _crear_con_run_vivo(store, work_id, run_id)
    store.pause_work_item(work_id, now=_NOW)


def _failed_safely(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    _crear_con_run_vivo(store, work_id, run_id)
    store.fail_work_item_safely(work_id, diagnostico="sin progreso", now=_NOW)


def _cancelled(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    _planned(store, work_id, run_id)
    store.cancel_work_item(work_id, now=_NOW)


def _delivered(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    _crear_con_run_vivo(store, work_id, run_id)
    store.begin_work_item_execution(work_id, now=_NOW)
    store.begin_work_item_check(work_id, now=_NOW)
    store.begin_work_item_review(work_id, now=_NOW)
    store.approve_work_item_review(work_id, now=_NOW)
    store.deliver_work_item(work_id, resultado={"ok": True}, now=_NOW)


#: Una entrada por estado. Si mañana aparece un estado nuevo, este diccionario
#: se queda corto y `test_la_tabla_cubre_todos_los_estados` lo dice, en vez de
#: que el estado nuevo se quede sin probar en silencio.
PREPARADORES: dict[WorkItemState, Preparador] = {
    WorkItemState.PLANNED: _planned,
    WorkItemState.ACTIVE: _active,
    WorkItemState.WAITING: _waiting,
    WorkItemState.NEEDS_DECISION: _needs_decision,
    WorkItemState.PAUSED: _paused,
    WorkItemState.FAILED_SAFELY: _failed_safely,
    WorkItemState.CANCELLED: _cancelled,
    WorkItemState.DELIVERED: _delivered,
}


def _cortar_por_presupuesto(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    registrar_gasto(store, work_id=work_id, presupuesto=Budget(limite=10.0), coste=11.0, now=_NOW)


def _resolver_fallo_tecnico(store: WorkEngineStore, work_id: str, run_id: str) -> None:
    resolver_fallo_tecnico(
        store, work_id=work_id, run_id=run_id, diagnostico="el Worker falló", now=_NOW
    )


#: Las funciones de la capa de política: las que traducen un hecho del mundo en
#: transiciones del dominio. Son las que tienen que aguantar cualquier estado,
#: porque el mundo no consulta en qué estado estamos antes de fallar.
POLITICAS: dict[str, Callable[[WorkEngineStore, str, str], None]] = {
    "registrar_gasto (agotado)": _cortar_por_presupuesto,
    "resolver_fallo_tecnico": _resolver_fallo_tecnico,
}


def test_la_tabla_cubre_todos_los_estados() -> None:
    """Anti-vacua: un estado nuevo sin preparador dejaría un hueco silencioso."""
    faltan = sorted(set(WorkItemState) - set(PREPARADORES))
    assert faltan == [], f"estados sin preparador en esta tabla: {faltan}"


@pytest.mark.parametrize("estado", list(WorkItemState), ids=lambda e: e.value)
@pytest.mark.parametrize("politica", sorted(POLITICAS), ids=lambda n: n.split()[0])
def test_ninguna_politica_revienta_desde_ningun_estado(
    store: WorkEngineStore, politica: str, estado: WorkItemState
) -> None:
    """La invariante que H-3 y H-7 violaron, fijada para todos los cruces.

    Una política puede decidir NO hacer nada desde un estado -un aviso que
    llega tarde sobre un trabajo ya entregado no tiene que escalar-, pero no
    puede lanzar: lanzar deja el Run muerto y el WorkItem colgado, sin que
    nadie se entere.
    """
    work_id = f"{_WORK_ID}-{estado.value}"
    run_id = f"{_RUN_ID}-{estado.value}"
    PREPARADORES[estado](store, work_id, run_id)

    preparado = store.get_work_item(work_id)
    assert preparado is not None and preparado.estado is estado, (
        f"el preparador de {estado.value} no dejó el WorkItem en ese estado"
    )

    try:
        POLITICAS[politica](store, work_id, run_id)
    except IllegalTransitionError as error:  # pragma: no cover - solo si hay defecto
        pytest.fail(
            f"«{politica}» revienta desde {estado.value}: {error}. "
            "Una política no puede lanzar por el estado en que la pilla el mundo: "
            "o actúa, o no hace nada, pero deja el estado consistente. "
            "Es el defecto H-3 (y su hermano H-7) otra vez."
        )

    despues = store.get_work_item(work_id)
    assert despues is not None, "la política no puede hacer desaparecer el WorkItem"


# -- La tabla de abajo no puede tener huecos ------------------------------------------


def _metodos_del_dominio_con_guarda_de_estado() -> set[str]:
    """Métodos de ``WorkItem`` que pueden lanzar ``IllegalTransitionError``.

    Se leen del código con ``ast``, no de una lista escrita a mano: una lista a
    mano se queda desactualizada en silencio, que es justo el fallo que esto
    viene a impedir. Se reconocen las DOS formas que usa el dominio hoy: la
    llamada a ``self._require(...)`` y el ``raise IllegalTransitionError``
    escrito directamente -que es como están ``change_scope`` y ``reprioritize``,
    y por eso nadie notó que faltaban de la tabla.
    """
    import ast
    from pathlib import Path

    ruta = Path(__file__).resolve().parents[2] / "src" / "sirius_engine" / "domain" / "work_item.py"
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    clase = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == "WorkItem")
    con_guarda: set[str] = set()
    for metodo in clase.body:
        if not isinstance(metodo, ast.FunctionDef) or metodo.name.startswith("_"):
            continue
        for nodo in ast.walk(metodo):
            llama_require = (
                isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "_require"
            )
            lanza_directo = (
                isinstance(nodo, ast.Raise)
                and isinstance(nodo.exc, ast.Call)
                and isinstance(nodo.exc.func, ast.Name)
                and nodo.exc.func.id == "IllegalTransitionError"
            )
            if llama_require or lanza_directo:
                con_guarda.add(metodo.name)
                break
    return con_guarda


#: Operaciones del dominio con guarda de estado que HOY no están en la tabla de
#: `test_work_item_transitions.py`, fijadas por nombre. La lista existe para que
#: la prueba no sea vacua mientras se cierran: cualquier operación NUEVA que
#: nazca fuera de la tabla rompe la batería igualmente, que es lo que importa.
#: Al meter una en la tabla, se quita de aquí. Cuando quede vacía, se borra la
#: constante y la excepción con ella.
FUERA_DE_LA_TABLA_HOY = frozenset(
    {
        # Las señaló la auditoría del 20-08: guarda de estado, ninguna prueba
        # contra cada estado.
        "change_scope",
        "reprioritize",
        # Estas seis las encontró esta misma guarda al estrenarse, y la
        # auditoría no las había visto. Todas llevan `_require(ACTIVE)` además
        # de su guarda de fase, así que son operaciones de estado a todos los
        # efectos. Meterlas en la tabla no es teclear una línea: la tabla de
        # `test_work_item_transitions.py` modela estados, no fases, y estas
        # exigen las dos cosas a la vez. Eso es trabajo con diseño detrás y va
        # en su propia incidencia (defecto H-8), no de tapadillo aquí.
        "begin_execution",
        "begin_check",
        "begin_review",
        "approve_review",
        "request_repair",
        "resume_after_repair",
    }
)


def test_ninguna_operacion_del_dominio_se_queda_fuera_de_la_tabla() -> None:
    """Guarda 2: un hueco en la tabla es un estado que nadie prueba.

    Sin esto, añadir una operación con guarda de estado y olvidarse de la
    tabla no rompe nada, y la tabla deja de ser exhaustiva sin que nadie se
    entere. Ya pasó: ``change_scope`` y ``reprioritize`` tienen guarda y nunca
    entraron.
    """
    from .test_work_item_transitions import OPERATIONS

    con_guarda = _metodos_del_dominio_con_guarda_de_estado()

    # La tabla nombra algunas variantes con sufijo -"resolve_decision" está como
    # "resolve_decision_continue" y "..._cancel"-, así que una operación cuenta
    # como cubierta si alguna clave de la tabla es su nombre o empieza por él.
    def cubierta(metodo: str) -> bool:
        return any(clave == metodo or clave.startswith(f"{metodo}_") for clave in OPERATIONS)

    fuera = sorted(m for m in con_guarda if not cubierta(m) and m not in FUERA_DE_LA_TABLA_HOY)
    assert fuera == [], (
        f"operaciones del dominio con guarda de estado que nadie prueba contra cada "
        f"estado: {fuera}. Añádelas a OPERATIONS/LEGAL_FROM en "
        "tests/engine/test_work_item_transitions.py."
    )


def test_la_lista_de_excepciones_no_se_queda_obsoleta() -> None:
    """Si alguien cierra el hueco y no borra la excepción, la prueba lo dice.

    Una lista de excepciones que sobrevive a lo que excusaba es la forma más
    silenciosa de que una guarda deje de guardar.
    """
    from .test_work_item_transitions import OPERATIONS

    ya_cubiertas = sorted(FUERA_DE_LA_TABLA_HOY & set(OPERATIONS))
    assert ya_cubiertas == [], (
        f"estas ya están en la tabla: {ya_cubiertas}. Quítalas de FUERA_DE_LA_TABLA_HOY."
    )
