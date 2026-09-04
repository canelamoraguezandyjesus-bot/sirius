"""``reflejar_desenlace``: el reflejo del desenlace de GitHub en el almacén (C1, #529).

Nota de arranque (ADR-001), cuatro preguntas:

1. ¿Qué se construye? La función pura que calcula, y el ejecutor mecánico
   que aplica, la secuencia mínima de transiciones del almacén que lleva un
   ``WorkItem`` despachado desde ``ACTIVE/PREPARAR`` a lo que su incidencia
   real proyecta -medido: ``dispatch_work_item`` (C2) nunca vuelve a tocar el
   almacén tras despachar, así que hoy los siete ``WorkItem`` reales de la
   ola de criticidad se quedan ahí para siempre (ver
   ``tests/automation/test_reflejar_desenlace_github.py``).
2. ¿Qué prueba lo falsifica? Cada caso de esta batería estuvo en rojo antes
   del cambio -no existía ``reflect.py``-, y las dos mutaciones sembradas
   abajo (quitar «nunca hacia atrás», quitar la idempotencia) hacen caer
   pruebas concretas de aquí.
3. ¿Qué NO cubre esto? No enlaza este comando a ningún workflow
   (``.github/**``, C1b, ADR-002); no declara ninguna clase en
   ``CLASES_CON_ESTADO_PROPIO`` (C2, ADR-101) -eso lo prueba
   ``tests/automation/test_reflejar_desenlace_github.py`` con la clase
   declarada SOLO dentro de la propia prueba, sin tocar la constante real-.
4. Criterio de parada: si reflejar una etiqueta del mapa exigiera un suceso o
   un puerto que el almacén no tuviera hoy, esta batería se detendría con
   ``BLOCKED_BY_DECISION`` en vez de añadirlo. No hizo falta: las nueve
   transiciones que se usan (``begin_work_item_execution``,
   ``begin_work_item_check``, ``begin_work_item_review``,
   ``approve_work_item_review``, ``request_work_item_repair``,
   ``resume_work_item_after_repair``, ``deliver_work_item``,
   ``fail_work_item_safely``, ``escalate_work_item``) ya existían en
   :mod:`sirius_engine.ports.store`, con cero llamantes en producción salvo
   las tres últimas (``deliver``/``fail_safely`` desde gobierno del
   presupuesto, ``escalate`` desde el supervisor) — medido con
   ``grep -rn`` antes de escribir una línea de ``reflect.py``.

Estructura de este fichero:

- Sección A: por cada etiqueta del mapa etiqueta -> (estado, fase)
  (:data:`sirius_engine.mirror_projection._LABEL_STATE`), la secuencia de
  sucesos exacta que produce desde ``ACTIVE/PREPARAR``, verificada
  end-to-end contra ``InMemoryWorkEngineStore.list_events()``.
- Sección B: idempotencia (segunda pasada = cero sucesos).
- Sección C: nunca hacia atrás.
- Sección D: espejo contradictorio / sin etiqueta de estado.
- Sección E: ``completed`` -> ``delivered`` con el SHA de fusión;
  ``failed-safely`` -> ``failed_safely`` con el diagnóstico real.
- Sección F: las dos mutaciones de la nota de arranque, vistas caer.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.domain.dispatch import DispatchEpisode
from sirius_engine.domain.mirror import MirroredWorkItem, OrigenLectura
from sirius_engine.domain.work_item import (
    WorkItem,
    WorkItemClass,
    WorkItemPhase,
    WorkItemState,
)
from sirius_engine.reflect import (
    PASO_COMPROBACION_INICIADA,
    PASO_DECISION_RESUELTA,
    PASO_EJECUCION_INICIADA,
    PASO_ENTREGADO,
    PASO_ESCALADO,
    PASO_FALLO_SEGURO,
    PASO_REACTIVADO,
    PASO_REPARACION_REANUDADA,
    PASO_REPARACION_SOLICITADA,
    PASO_REVISION_APROBADA,
    PASO_REVISION_INICIADA,
    aplicar_pasos,
    reflejar_desenlace,
)

_AHORA = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
_WORK_ID = "WI-20260902-174417"
_REPO = "canelamoraguezandyjesus-bot/sirius"


def _episodio(*, numero_incidencia: int = 508) -> DispatchEpisode:
    return DispatchEpisode(
        work_id=_WORK_ID,
        orden_enlazada=f"diario-del-motor:{_WORK_ID}",
        repo=_REPO,
        numero_incidencia=numero_incidencia,
        etiqueta="sirius:implement-requested",
        recorded_at=_AHORA,
    )


def _espejo(
    *,
    estado: WorkItemState | None,
    fase: WorkItemPhase | None,
    etiquetas: tuple[str, ...] = (),
    etiquetas_contradictorias: bool = False,
    head_sha: str | None = None,
    diagnostico_fallo: str | None = None,
) -> MirroredWorkItem:
    return MirroredWorkItem(
        work_id=f"{_REPO}#508",
        estado=estado,
        fase=fase,
        etiquetas=etiquetas,
        etiquetas_contradictorias=etiquetas_contradictorias,
        cerrada=False,
        pr_url=None,
        head_sha=head_sha,
        rondas=(),
        veredictos=(),
        eventos_quality=(),
        fallos_quality_consecutivos=0,
        origen=OrigenLectura(fuente="test", leido_en=_AHORA),
        diagnostico_fallo=diagnostico_fallo,
    )


def _work_item_activo(store: InMemoryWorkEngineStore) -> WorkItem:
    creado = store.create_work_item(
        work_id=_WORK_ID,
        peticion_original="texto literal",
        objetivo="objetivo real",
        contexto_origen=("incidencia:508",),
        entregable="alcance real",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_AHORA,
    )
    return store.activate_work_item(creado.work_id, now=_AHORA)


# --- Sección A: por cada etiqueta del mapa, la secuencia exacta ------------


@pytest.mark.parametrize(
    ("estado_objetivo", "fase_objetivo", "kinds_esperados"),
    [
        # sirius:implementing / sirius:audit-requested
        (WorkItemState.ACTIVE, WorkItemPhase.EJECUTAR, (PASO_EJECUCION_INICIADA,)),
        # sirius:ci-pending
        (
            WorkItemState.ACTIVE,
            WorkItemPhase.COMPROBAR,
            (PASO_EJECUCION_INICIADA, PASO_COMPROBACION_INICIADA),
        ),
        # sirius:review-requested / sirius:reviewing
        (
            WorkItemState.ACTIVE,
            WorkItemPhase.REVISAR,
            (PASO_EJECUCION_INICIADA, PASO_COMPROBACION_INICIADA, PASO_REVISION_INICIADA),
        ),
        # sirius:repair-requested / sirius:repairing
        (
            WorkItemState.ACTIVE,
            WorkItemPhase.REPARAR,
            (
                PASO_EJECUCION_INICIADA,
                PASO_COMPROBACION_INICIADA,
                PASO_REVISION_INICIADA,
                PASO_REPARACION_SOLICITADA,
            ),
        ),
        # sirius:ready-for-merge
        (
            WorkItemState.ACTIVE,
            WorkItemPhase.ENTREGAR,
            (
                PASO_EJECUCION_INICIADA,
                PASO_COMPROBACION_INICIADA,
                PASO_REVISION_INICIADA,
                PASO_REVISION_APROBADA,
            ),
        ),
    ],
)
def test_cada_etiqueta_activa_produce_su_secuencia_exacta_desde_preparar(
    estado_objetivo: WorkItemState,
    fase_objetivo: WorkItemPhase,
    kinds_esperados: tuple[str, ...],
) -> None:
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=estado_objetivo, fase=fase_objetivo)

    resultado = reflejar_desenlace(motor, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == kinds_esperados
    assert resultado.divergencia is None

    aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    kinds_del_diario = tuple(
        evento.kind for evento in store.list_events() if evento.kind != "work_item_created"
    )
    assert kinds_del_diario == ("work_item_activated", *kinds_esperados)
    final = store.get_work_item(_WORK_ID)
    assert final is not None
    assert final.estado is WorkItemState.ACTIVE
    assert final.fase is fase_objetivo


def test_etiqueta_blocked_decision_escala_en_un_solo_paso() -> None:
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=WorkItemState.NEEDS_DECISION, fase=None)

    resultado = reflejar_desenlace(motor, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (PASO_ESCALADO,)
    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert aplicados[-1].estado is WorkItemState.NEEDS_DECISION


def test_etiqueta_planned_no_toca_nada_porque_el_motor_ya_esta_activo() -> None:
    """El motor de un WorkItem despachado ya dejó PLANNED: es la etiqueta con la
    que nace toda incidencia, y por construcción ya quedó atrás en cuanto el
    ciclo movió la primera etiqueta real.
    """
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=WorkItemState.PLANNED, fase=WorkItemPhase.PREPARAR)

    resultado = reflejar_desenlace(motor, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante" in resultado.divergencia


# --- Sección B: idempotencia -------------------------------------------------


def test_segunda_pasada_sobre_el_mismo_espejo_no_anade_ningun_suceso() -> None:
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.REVISAR)

    primero = reflejar_desenlace(motor, espejo, _episodio())
    assert primero.pasos != ()
    aplicar_pasos(store, _WORK_ID, primero.pasos, now=_AHORA)

    motor_actualizado = store.get_work_item(_WORK_ID)
    assert motor_actualizado is not None
    segundo = reflejar_desenlace(motor_actualizado, espejo, _episodio())

    assert segundo.pasos == ()
    assert segundo.divergencia is None


def test_segunda_pasada_tras_escalar_es_idempotente() -> None:
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=WorkItemState.NEEDS_DECISION, fase=None)

    primero = reflejar_desenlace(motor, espejo, _episodio())
    aplicar_pasos(store, _WORK_ID, primero.pasos, now=_AHORA)
    motor_escalado = store.get_work_item(_WORK_ID)
    assert motor_escalado is not None

    segundo = reflejar_desenlace(motor_escalado, espejo, _episodio())
    assert segundo.pasos == ()


# --- Sección C: nunca hacia atrás -------------------------------------------


def test_nunca_hacia_atras_si_el_motor_ya_paso_el_objetivo() -> None:
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    adelantado = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    adelantado = store.begin_work_item_check(_WORK_ID, now=_AHORA)
    adelantado = store.begin_work_item_review(_WORK_ID, now=_AHORA)
    adelantado = store.approve_work_item_review(_WORK_ID, now=_AHORA)
    assert adelantado.fase is WorkItemPhase.ENTREGAR

    # La incidencia proyecta una etiqueta más ATRÁS que donde ya está el motor.
    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR)
    resultado = reflejar_desenlace(adelantado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante" in resultado.divergencia

    # No se aplicó nada: el motor sigue exactamente donde estaba.
    aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert store.get_work_item(_WORK_ID) == adelantado


# --- Sección C bis: reanudación de una parada por orden del propietario -----
#
# `sirius_resume_on_command.sh:338-350` repone la etiqueta activa que la
# parada había retirado -sin tocar el motor, que se queda en FAILED_SAFELY o
# NEEDS_DECISION-, así que el espejo vuelve a proyectar ACTIVE mientras el
# motor sigue parado. Antes de esta corrección esa combinación se trataba
# como "hacia atrás": divergencia para siempre (CODEX-002, PR #530).


def test_reanudacion_desde_failed_safely_reactiva_antes_de_caminar_la_fase() -> None:
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_ejecutar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico="motivo", now=_AHORA)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is en_ejecutar.fase is WorkItemPhase.EJECUTAR

    # El propietario reanudó y la incidencia quedó, de nuevo, ACTIVE (la
    # etiqueta repuesta por el script apunta a `ci-pending`, fase COMPROBAR).
    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR)
    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_REACTIVADO,
        PASO_COMPROBACION_INICIADA,
    )
    assert resultado.divergencia is None

    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    final = aplicados[-1]
    assert final.estado is WorkItemState.ACTIVE
    assert final.fase is WorkItemPhase.COMPROBAR


def test_reanudacion_desde_needs_decision_resuelve_la_decision_antes_de_caminar_la_fase() -> None:
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_ejecutar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    escalado = store.escalate_work_item(_WORK_ID, now=_AHORA)
    assert escalado.estado is WorkItemState.NEEDS_DECISION
    assert escalado.fase is en_ejecutar.fase is WorkItemPhase.EJECUTAR

    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR)
    resultado = reflejar_desenlace(escalado, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_DECISION_RESUELTA,
        PASO_COMPROBACION_INICIADA,
    )
    assert resultado.pasos[0].resultado == {"continuar": True}
    assert resultado.divergencia is None

    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    final = aplicados[-1]
    assert final.estado is WorkItemState.ACTIVE
    assert final.fase is WorkItemPhase.COMPROBAR


# --- Sección D: contradicción / sin etiqueta --------------------------------


def test_espejo_contradictorio_no_toca_nada_y_registra_el_motivo() -> None:
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(
        estado=None,
        fase=None,
        etiquetas=("sirius:completed", "sirius:failed-safely"),
        etiquetas_contradictorias=True,
    )

    resultado = reflejar_desenlace(motor, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "contradicen" in resultado.divergencia


def test_espejo_sin_etiqueta_de_estado_no_hace_nada_y_no_avisa() -> None:
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=None, fase=None)

    resultado = reflejar_desenlace(motor, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is None


# --- Sección E: completed y failed-safely -----------------------------------


def test_completed_entrega_con_el_numero_de_incidencia_y_el_sha_de_fusion() -> None:
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        head_sha="abc1234deadbeef",
    )

    resultado = reflejar_desenlace(motor, espejo, _episodio(numero_incidencia=508))

    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_EJECUCION_INICIADA,
        PASO_COMPROBACION_INICIADA,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
        PASO_ENTREGADO,
    )
    paso_entrega = resultado.pasos[-1]
    assert paso_entrega.resultado == {"numero_incidencia": 508, "merge_sha": "abc1234deadbeef"}

    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    entregado = aplicados[-1]
    assert entregado.estado is WorkItemState.DELIVERED
    assert entregado.resultado == {"numero_incidencia": 508, "merge_sha": "abc1234deadbeef"}


def test_completed_sin_pasar_por_ready_for_merge_camina_los_pasos_intermedios() -> None:
    """El motor no llama entregado a algo que no pasó por aprobar la revisión
    -mismo criterio que la ventana 3 de ``projection_verifier``-, así que el
    plan mínimo camina TODAS las fases intermedias antes de entregar, en vez
    de saltar directamente a ``deliver_work_item``.
    """
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=WorkItemState.DELIVERED, fase=WorkItemPhase.ENTREGAR)

    resultado = reflejar_desenlace(motor, espejo, _episodio())

    assert resultado.pasos[-1].kind == PASO_ENTREGADO
    assert len(resultado.pasos) == 5


def test_failed_safely_usa_el_diagnostico_del_ultimo_comentario_de_fallo() -> None:
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(
        estado=WorkItemState.FAILED_SAFELY,
        fase=None,
        diagnostico_fallo="uv no estaba instalado en el runner",
    )

    resultado = reflejar_desenlace(motor, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (PASO_FALLO_SEGURO,)
    assert resultado.pasos[0].diagnostico == "uv no estaba instalado en el runner"

    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert aplicados[-1].estado is WorkItemState.FAILED_SAFELY
    assert aplicados[-1].diagnostico == "uv no estaba instalado en el runner"


def test_failed_safely_sin_diagnostico_de_confianza_dice_que_no_hubo_uno() -> None:
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=WorkItemState.FAILED_SAFELY, fase=None, diagnostico_fallo=None)

    resultado = reflejar_desenlace(motor, espejo, _episodio())

    assert resultado.pasos[0].diagnostico is not None
    assert "sin diagnóstico" in resultado.pasos[0].diagnostico


def test_repair_resumed_cierra_el_bucle_desde_reparar_hacia_delante() -> None:
    """El único paso que retrocede en el diagrama de fases -REPARAR -> COMPROBAR,
    el cierre real del bucle revisar-reparar- se toma cuando el motor YA está
    en REPARAR (de una pasada anterior) y la incidencia avanzó a
    ``ci-pending``: es forzosamente hacia delante en el tiempo, aunque
    COMPROBAR preceda a REPARAR en el camino de ida.
    """
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_reparar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    en_reparar = store.begin_work_item_check(_WORK_ID, now=_AHORA)
    en_reparar = store.begin_work_item_review(_WORK_ID, now=_AHORA)
    en_reparar = store.request_work_item_repair(_WORK_ID, now=_AHORA)
    assert en_reparar.fase is WorkItemPhase.REPARAR

    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR)
    resultado = reflejar_desenlace(en_reparar, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (PASO_REPARACION_REANUDADA,)
    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert aplicados[-1].fase is WorkItemPhase.COMPROBAR


# --- Sección F: las dos mutaciones de la nota de arranque, vistas caer -----
#
# Estas dos pruebas documentan, en el propio código, las mutaciones que la
# nota de arranque predijo. No sustituyen la comprobación manual -hecha una
# vez, registrada en el ADR-136-: sirven para que una regresión futura de la
# misma familia se vea caer aquí sin repetir el ejercicio a mano.


def test_mutacion_quitar_nunca_hacia_atras_la_detecta_esta_prueba() -> None:
    """Si `_camino_de_fase` cayera a un `else` que sigue caminando ADELANTE en
    vez de declarar ENTREGAR sin arista de avance, este caso -motor en
    ENTREGAR, objetivo COMPROBAR- dejaría de devolver ``None`` y produciría
    pasos que retroceden. La aserción de la sección C ya lo cubre; aquí se
    deja explícito que es la prueba de la regla, no un efecto colateral de
    otra.
    """
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_entregar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    en_entregar = store.begin_work_item_check(_WORK_ID, now=_AHORA)
    en_entregar = store.begin_work_item_review(_WORK_ID, now=_AHORA)
    en_entregar = store.approve_work_item_review(_WORK_ID, now=_AHORA)

    espejo = _espejo(estado=WorkItemState.ACTIVE, fase=WorkItemPhase.EJECUTAR)
    resultado = reflejar_desenlace(en_entregar, espejo, _episodio())
    assert resultado.pasos == (), (
        "una implementación que no respetara 'nunca hacia atrás' inventaría "
        "pasos aquí: no hay ninguna transición real de ENTREGAR a EJECUTAR"
    )


def test_mutacion_quitar_idempotencia_la_detecta_esta_prueba() -> None:
    """Si la rama ``FAILED_SAFELY`` no comprobara primero si el motor YA está
    ahí, una segunda pasada volvería a intentar ``fail_work_item_safely``
    sobre un WorkItem que ya no está ``ACTIVE`` -y el almacén lo rechazaría
    con ``IllegalTransitionError`` en vez de devolver cero pasos-.
    """
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=WorkItemState.FAILED_SAFELY, fase=None, diagnostico_fallo="motivo")

    primero = reflejar_desenlace(motor, espejo, _episodio())
    aplicados = aplicar_pasos(store, _WORK_ID, primero.pasos, now=_AHORA)
    fallado = aplicados[-1]

    segundo = reflejar_desenlace(fallado, espejo, _episodio())
    assert segundo.pasos == ()
    assert segundo.divergencia is None, (
        "sin la comprobación de idempotencia, esto cae al mismo `pasos=()` pero "
        "por la rama de 'no toca nada porque no es ACTIVE', que es la razón "
        "equivocada: acusaría de divergencia a un WorkItem que en realidad ya "
        "está exactamente donde el espejo dice"
    )
    # Si esto no fuera así, la siguiente línea lanzaría IllegalTransitionError.
    aplicar_pasos(store, _WORK_ID, segundo.pasos, now=_AHORA)
