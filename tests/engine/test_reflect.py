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
from sirius_engine.domain.mirror import EstadoAcreditado, MirroredWorkItem, OrigenLectura
from sirius_engine.domain.work_item import (
    WorkItem,
    WorkItemClass,
    WorkItemPhase,
    WorkItemState,
)
from sirius_engine.mirror_projection import _LABEL_STATE
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
    reanudacion_publicada: bool = False,
    historial_estados: tuple[EstadoAcreditado, ...] = (),
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
        reanudacion_publicada=reanudacion_publicada,
        historial_estados=historial_estados,
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
    # `reanudacion_publicada=True` porque el guion publica su marcador de
    # permiso ANTES de reponer la etiqueta (CODEX-001, ronda 4, PR #530).
    espejo = _espejo(
        estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR, reanudacion_publicada=True
    )
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

    # Idempotencia (CLAUDE-REVIEWER-001): una segunda pasada sobre el motor ya
    # reactivado, con el mismo espejo, no debe volver a intentar reactivar.
    motor_reactivado = store.get_work_item(_WORK_ID)
    assert motor_reactivado is not None
    segundo = reflejar_desenlace(motor_reactivado, espejo, _episodio())
    assert segundo.pasos == ()
    assert segundo.divergencia is None


def test_reanudacion_desde_needs_decision_resuelve_la_decision_antes_de_caminar_la_fase() -> None:
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_ejecutar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    escalado = store.escalate_work_item(_WORK_ID, now=_AHORA)
    assert escalado.estado is WorkItemState.NEEDS_DECISION
    assert escalado.fase is en_ejecutar.fase is WorkItemPhase.EJECUTAR

    espejo = _espejo(
        estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR, reanudacion_publicada=True
    )
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

    # Idempotencia (CLAUDE-REVIEWER-001): una segunda pasada sobre el motor ya
    # con la decisión resuelta, con el mismo espejo, no debe volver a
    # intentar resolverla.
    motor_resuelto = store.get_work_item(_WORK_ID)
    assert motor_resuelto is not None
    segundo = reflejar_desenlace(motor_resuelto, espejo, _episodio())
    assert segundo.pasos == ()
    assert segundo.divergencia is None


# --- Sección C ter: reanudación que aterriza en PLANNED o DELIVERED ---------
#
# CODEX-001 (ronda 3, PR #530): la corrección de la sección C bis (CODEX-002,
# ronda 2) solo reactivaba/resolvía la decisión dentro de la rama ACTIVE. Pero
# una reanudación real no siempre aterriza ahí: `destino_de_rol` repone
# `sirius:implement-requested` para el implementador, que
# `mirror_projection.py` proyecta como PLANNED -no ACTIVE-; y si el ciclo real
# avanza deprisa (o esta reflexión se ejecuta tarde), el espejo puede llegar a
# proyectar DELIVERED sin que ninguna pasada observara el ACTIVE intermedio.
# Antes de esta corrección, ambas ramas rechazaban el `WorkItem` detenido como
# "hacia atrás" para siempre.


def test_reanudacion_que_aterriza_en_planned_reactiva_sin_camino_de_fase() -> None:
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico="motivo", now=_AHORA)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is WorkItemPhase.PREPARAR

    # El propietario reanudó al implementador: `destino_de_rol` repone
    # `sirius:implement-requested`, que el espejo proyecta como PLANNED/PREPARAR.
    espejo = _espejo(
        estado=WorkItemState.PLANNED,
        fase=WorkItemPhase.PREPARAR,
        etiquetas=("sirius:implement-requested",),
        reanudacion_publicada=True,
    )
    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (PASO_REACTIVADO,)
    assert resultado.divergencia is None

    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    final = aplicados[-1]
    assert final.estado is WorkItemState.ACTIVE
    assert final.fase is WorkItemPhase.PREPARAR

    # Idempotencia (regla 5): una segunda pasada sobre el motor ya reactivado
    # no añade ningún suceso -``pasos == ()``-. No exige ``divergencia is
    # None``: el motor, tras reactivarse, es genuinamente ACTIVE, y ACTIVE ya
    # no es "exactamente el objetivo" que sigue siendo PLANNED
    # (`test_etiqueta_planned_no_toca_nada_porque_el_motor_ya_esta_activo`
    # cubre esa misma regla para un motor que nunca se paró); esto no reabre
    # CODEX-001 porque no hay suceso de más -la reactivación ya ocurrió una
    # sola vez, en la primera pasada-.
    motor_reactivado = store.get_work_item(_WORK_ID)
    assert motor_reactivado is not None
    segundo = reflejar_desenlace(motor_reactivado, espejo, _episodio())
    assert segundo.pasos == ()


def test_etiqueta_planned_sigue_hacia_atras_si_el_motor_nunca_paro() -> None:
    """Sin una reanudación real de por medio -el motor sigue ACTIVE, nunca se
    paró-, un espejo PLANNED sigue siendo "hacia atrás": CODEX-001 no debe
    convertir cualquier retroceso ordinario a PLANNED en permiso para
    reactivar.
    """
    store = InMemoryWorkEngineStore()
    motor = _work_item_activo(store)
    espejo = _espejo(estado=WorkItemState.PLANNED, fase=WorkItemPhase.PREPARAR)

    resultado = reflejar_desenlace(motor, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante" in resultado.divergencia


def test_reanudacion_que_aterriza_en_delivered_reactiva_y_camina_hasta_entregar() -> None:
    """El ciclo real puede llegar hasta `sirius:completed` sin que ninguna
    pasada de reflejo observara el ACTIVE intermedio -por ejemplo, si
    `sirius-reflejar` no corrió entre la reanudación y el cierre real de la
    incidencia-. El motor sigue detenido (FAILED_SAFELY), pero el espejo ya
    proyecta DELIVERED directamente.
    """
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_comprobar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    en_comprobar = store.begin_work_item_check(_WORK_ID, now=_AHORA)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico="motivo", now=_AHORA)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is en_comprobar.fase is WorkItemPhase.COMPROBAR

    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=None,
        head_sha="deadbeef1234",
        reanudacion_publicada=True,
    )
    resultado = reflejar_desenlace(parado, espejo, _episodio(numero_incidencia=508))

    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_REACTIVADO,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
        PASO_ENTREGADO,
    )
    assert resultado.divergencia is None
    paso_entrega = resultado.pasos[-1]
    assert paso_entrega.resultado == {"numero_incidencia": 508, "merge_sha": "deadbeef1234"}

    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    final = aplicados[-1]
    assert final.estado is WorkItemState.DELIVERED

    # Idempotencia: segunda pasada sobre el motor ya entregado.
    motor_entregado = store.get_work_item(_WORK_ID)
    assert motor_entregado is not None
    segundo = reflejar_desenlace(motor_entregado, espejo, _episodio(numero_incidencia=508))
    assert segundo.pasos == ()
    assert segundo.divergencia is None


# --- Sección C quater: sin marcador de reanudación, la parada se conserva ---
#
# Las secciones C bis y C ter probaron que un espejo que deja de proyectar el
# MISMO estado detenido reanuda. Pero eso solo, sin más, es exactamente lo que
# encontró la revisión independiente de la ronda 4 (CODEX-001, PR #530): una
# etiqueta de parada sustituida a mano, o alterada por una transición parcial
# sin que el propietario escribiera `continua`, TAMBIÉN deja de proyectar el
# mismo estado detenido, y antes de esta corrección eso bastaba para
# reanudar. Estas pruebas fijan `reanudacion_publicada=False` -sin ninguno de
# los tres marcadores de `sirius_resume_on_command.sh` publicado- y esperan
# que la parada se conserve con divergencia, para las tres formas de aterrizar
# que las secciones C bis/C ter cubrían con el marcador presente.


def test_sin_marcador_de_reanudacion_failed_safely_no_reactiva_aunque_el_espejo_cambie() -> None:
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_ejecutar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico="motivo", now=_AHORA)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is en_ejecutar.fase is WorkItemPhase.EJECUTAR

    # Mismo espejo que la reanudación legítima de la sección C bis, pero sin
    # ninguno de los tres marcadores publicados.
    espejo = _espejo(
        estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR, reanudacion_publicada=False
    )
    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante" in resultado.divergencia

    aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert store.get_work_item(_WORK_ID) == parado


def test_sin_marcador_de_reanudacion_needs_decision_no_resuelve_aunque_el_espejo_cambie() -> None:
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_ejecutar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    escalado = store.escalate_work_item(_WORK_ID, now=_AHORA)
    assert escalado.estado is WorkItemState.NEEDS_DECISION
    assert escalado.fase is en_ejecutar.fase is WorkItemPhase.EJECUTAR

    espejo = _espejo(
        estado=WorkItemState.ACTIVE, fase=WorkItemPhase.COMPROBAR, reanudacion_publicada=False
    )
    resultado = reflejar_desenlace(escalado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante" in resultado.divergencia


def test_sin_marcador_de_reanudacion_no_reactiva_aunque_el_espejo_aterrice_en_planned() -> None:
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico="motivo", now=_AHORA)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is WorkItemPhase.PREPARAR

    espejo = _espejo(
        estado=WorkItemState.PLANNED, fase=WorkItemPhase.PREPARAR, reanudacion_publicada=False
    )
    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante" in resultado.divergencia


def test_sin_marcador_de_reanudacion_no_reactiva_aunque_el_espejo_aterrice_en_delivered() -> None:
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_comprobar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    en_comprobar = store.begin_work_item_check(_WORK_ID, now=_AHORA)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico="motivo", now=_AHORA)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is en_comprobar.fase is WorkItemPhase.COMPROBAR

    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=None,
        head_sha="deadbeef1234",
        reanudacion_publicada=False,
    )
    resultado = reflejar_desenlace(parado, espejo, _episodio(numero_incidencia=508))

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante" in resultado.divergencia


# --- Sección C quinquies: implement-requested reactiva sin retroceder de fase
# (CODEX-002, ronda 4, PR #530) -----------------------------------------------
#
# `destino_de_rol` (`sirius_resume_on_command.sh:180-186`) repone
# `sirius:implement-requested` SOLO para el implementador -`reviewer` recibe
# `review-requested` y `corrector`, `repair-requested`, ninguno de los cuales
# proyecta PLANNED (corrección del enunciado, CODEX-001, ronda 5, PR #530: la
# versión anterior de este comentario y de la ADR-136 afirmaban, los dos por
# error, que la reponía "para cualquier rol"). El escenario real que sí
# reproduce esta sección es otro: el implementador puede haberse parado más
# adelante que PREPARAR -en EJECUTAR, su propia fase real- antes de que el
# propietario reanude, y esa etiqueta siempre proyecta PLANNED/PREPARAR
# (`mirror_projection.py`), no la fase real en la que el motor se paró. Antes
# de esta corrección, `_camino_de_fase(fase_actual, PREPARAR)` devolvía `None`
# en cuanto `fase_actual` no era ya PREPARAR -PREPARAR es la primera fase del
# grafo, así que no hay ningún camino hacia delante hacia ella- y la rama
# PLANNED descartaba TAMBIÉN el paso de reactivación ya calculado, dejando el
# motor parado para siempre.


def test_reanudacion_hacia_planned_desde_una_fase_mas_adelantada_reactiva_sin_caminar() -> None:
    """El motor se paró en EJECUTAR (más adelante que PREPARAR); el propietario
    reanudó y la etiqueta repuesta (`implement-requested`) proyecta
    PLANNED/PREPARAR igualmente. Se espera reactivar conservando EJECUTAR -no
    hay ninguna transición real que retroceda la fase-.
    """
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_ejecutar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico="motivo", now=_AHORA)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is en_ejecutar.fase is WorkItemPhase.EJECUTAR

    espejo = _espejo(
        estado=WorkItemState.PLANNED,
        fase=WorkItemPhase.PREPARAR,
        etiquetas=("sirius:implement-requested",),
        reanudacion_publicada=True,
    )
    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (PASO_REACTIVADO,)
    assert resultado.divergencia is None

    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    final = aplicados[-1]
    assert final.estado is WorkItemState.ACTIVE
    assert final.fase is WorkItemPhase.EJECUTAR

    # Idempotencia: el motor ya reactivado, con el mismo espejo, no vuelve a
    # producir ningún suceso.
    motor_reactivado = store.get_work_item(_WORK_ID)
    assert motor_reactivado is not None
    segundo = reflejar_desenlace(motor_reactivado, espejo, _episodio())
    assert segundo.pasos == ()


def test_reanudacion_no_reactiva_hacia_planned_sin_la_etiqueta_disparadora_real() -> None:
    """`sirius:planned` proyecta el MISMO (estado, fase) que
    `sirius:implement-requested` -es el único par de activación válido del
    mapa etiqueta -> (estado, fase)-, pero ningún guion de reanudación repone
    nunca `sirius:planned`: `destino_de_rol` solo aplica
    `sirius:implement-requested` para el implementador
    (`sirius_resume_on_command.sh:180-186`). Un espejo que lleva
    `sirius:planned` -por ejemplo, tras una transición parcial o una edición
    manual posterior al permiso- no debe reactivarse como si el marcador ya
    publicado autorizara justo esa etiqueta (CODEX-003, ronda 5, PR #530): se
    conserva la parada y se registra divergencia, igual que sin marcador.
    """
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    en_reparar = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    en_reparar = store.begin_work_item_check(_WORK_ID, now=_AHORA)
    en_reparar = store.begin_work_item_review(_WORK_ID, now=_AHORA)
    en_reparar = store.request_work_item_repair(_WORK_ID, now=_AHORA)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico="motivo", now=_AHORA)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is en_reparar.fase is WorkItemPhase.REPARAR

    espejo = _espejo(
        estado=WorkItemState.PLANNED,
        fase=WorkItemPhase.PREPARAR,
        etiquetas=("sirius:planned",),
        reanudacion_publicada=True,
    )
    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante" in resultado.divergencia

    aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert store.get_work_item(_WORK_ID) == parado


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


# --- Sección G: recorrer una recuperación acreditada (ADR-144, #539) -------
#
# Nota de arranque en ADR-144. El caso vivo es WI-20260905-034826 (incidencia
# #537): el motor se quedó en `failed_safely`/`reparar` en su parada de las
# 05:17 del 05-09-2026 y la incidencia siguió sin él -segunda reanudación a
# las 05:29, dos vueltas de Quality+revisión, `completed` a las 07:00-. El
# reflector comparaba su estado guardado con la foto actual, no encontraba
# camino hacia delante y se negaba (fail-open correcto, memoria
# desactualizada). Estas pruebas fijan que el historial de confianza, que sí
# acredita el camino, baste para recorrerlo.


def _acreditado(etiqueta: str, head: str = "1c934781") -> EstadoAcreditado:
    estado, fase = _LABEL_STATE[etiqueta]
    return EstadoAcreditado(etiqueta=etiqueta, estado=estado, fase=fase, head=head)


#: Los marcadores `sirius-notification` reales de la #537, en el orden en que
#: se publicaron (leídos con `gh issue view 537 --json comments`, 05-09-2026).
_HISTORIAL_537: tuple[EstadoAcreditado, ...] = (
    _acreditado("sirius:implementing", "no-head"),
    _acreditado("sirius:repair-requested", "1c934781"),
    _acreditado("sirius:blocked-decision", "1c934781"),
    _acreditado("sirius:failed-safely", "1c934781"),
    _acreditado("sirius:repair-requested", "786c82dc"),
    _acreditado("sirius:ready-for-merge", "92e5b9f4"),
    _acreditado("sirius:completed", "92e5b9f4"),
)


def _motor_parado_en_reparar(store: InMemoryWorkEngineStore) -> WorkItem:
    """El estado exacto en que se quedó WI-20260905-034826: failed_safely/reparar."""
    _work_item_activo(store)
    store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    store.begin_work_item_check(_WORK_ID, now=_AHORA)
    store.begin_work_item_review(_WORK_ID, now=_AHORA)
    store.request_work_item_repair(_WORK_ID, now=_AHORA)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico="sin tiempo", now=_AHORA)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is WorkItemPhase.REPARAR
    return parado


def test_recorrido_acreditado_avanza_el_caso_vivo_de_la_537() -> None:
    """El caso que motivó ADR-144, con el historial real de la incidencia #537.

    El espejo NO trae `reanudacion_publicada`: la segunda reanudación no dejó
    marcador nuevo porque `sirius_comment_once` deduplica por el texto del
    marcador y el head no había cambiado. Lo que acredita el camino son las
    notificaciones de etiqueta posteriores a la parada.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f469485c537c9cec5b37f6131f17d9903a",
        historial_estados=_HISTORIAL_537,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_REACTIVADO,
        PASO_REPARACION_REANUDADA,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
        PASO_ENTREGADO,
    )

    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    entregado = aplicados[-1]
    assert entregado.estado is WorkItemState.DELIVERED
    assert entregado.fase is WorkItemPhase.ENTREGAR
    assert entregado.resultado is not None
    assert entregado.resultado["merge_sha"] == "92e5b9f469485c537c9cec5b37f6131f17d9903a"

    # C1, invariante 3: la pasada siguiente no añade nada.
    segunda = reflejar_desenlace(entregado, espejo, _episodio())
    assert segunda.pasos == ()
    assert segunda.divergencia is None


def test_sin_acreditacion_intermedia_se_declara_y_no_se_toca_nada() -> None:
    """El contraejemplo de la incidencia #539, en su forma más pura.

    Mismo motor y misma foto que el caso vivo, pero el historial de confianza
    se detiene en la parada: nada acredita que la incidencia volviera a estar
    viva. Se conserva exactamente el comportamiento de hoy.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=_HISTORIAL_537[:4],
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante, no se toca nada" in resultado.divergencia


def test_la_foto_repetida_en_el_historial_no_es_acreditacion_intermedia() -> None:
    """Prueba adversaria: el historial no dice NADA que la foto no dijera ya.

    Es el caso que CODEX-001 (ronda 4, PR #530) cerró y que este cambio no
    puede reabrir: una etiqueta de parada sustituida por otra sin ninguna
    orden del propietario. El único estado acreditado tras la parada es el de
    la propia foto, así que no hay ninguna secuencia que recorrer -solo el
    salto que el reflector ya rechazaba.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=(*_HISTORIAL_537[:4], _acreditado("sirius:completed", "92e5b9f4")),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None


def test_el_recorrido_ancla_en_la_ULTIMA_coincidencia_con_el_estado_guardado() -> None:
    """El motor está donde se quedó, no donde estuvo la primera vez.

    Este historial para dos veces en seguro. Anclando en la PRIMERA parada, el
    recorrido intentaría llevar el motor hasta ENTREGAR y desde ahí volver a
    REPARAR para la segunda vuelta -y no existe ninguna arista de ENTREGAR a
    REPARAR-, así que se abandonaría entero y el motor se quedaría
    desactualizado. Anclando en la última -que es donde el motor se quedó de
    verdad- el camino existe.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=(
            _acreditado("sirius:implementing", "no-head"),
            _acreditado("sirius:failed-safely", "1c934781"),
            _acreditado("sirius:repair-requested", "1c934781"),
            _acreditado("sirius:ready-for-merge", "1c934781"),
            _acreditado("sirius:failed-safely", "786c82dc"),
            _acreditado("sirius:repair-requested", "786c82dc"),
            _acreditado("sirius:ready-for-merge", "92e5b9f4"),
            _acreditado("sirius:completed", "92e5b9f4"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_REACTIVADO,
        PASO_REPARACION_REANUDADA,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
        PASO_ENTREGADO,
    ), "anclar en la PRIMERA parada habría abandonado el recorrido entero"


def test_sin_ancla_en_el_historial_no_hay_recorrido() -> None:
    """El estado guardado tiene que estar EN el historial acreditado.

    Un historial que nunca menciona el estado del motor no conecta nada con
    nada: recorrerlo sería empezar por un punto que nadie acreditó.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=(
            _acreditado("sirius:implementing", "no-head"),
            _acreditado("sirius:ready-for-merge", "92e5b9f4"),
            _acreditado("sirius:completed", "92e5b9f4"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None


def test_un_tramo_ilegal_abandona_el_recorrido_entero() -> None:
    """Todo o nada: si un tramo no es una transición real, no se aplica ninguno.

    El historial acredita aquí un retroceso imposible (de ENTREGAR a
    EJECUTAR). El recorrido no puede "saltárselo" ni aplicar solo el trozo
    bueno: se abandona entero y se declara la divergencia de siempre.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=(
            *_HISTORIAL_537[:4],
            _acreditado("sirius:ready-for-merge", "92e5b9f4"),
            _acreditado("sirius:implementing", "92e5b9f4"),
            _acreditado("sirius:completed", "92e5b9f4"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert store.get_work_item(_WORK_ID) is not None
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.FAILED_SAFELY


def test_el_recorrido_solo_entra_cuando_la_foto_sola_no_basta() -> None:
    """El cálculo por foto manda: el recorrido es el plan B, no el plan A.

    Con un motor ACTIVE/EJECUTAR y una foto ACTIVE/REVISAR, el cálculo de
    siempre ya encuentra camino; el historial acreditado -que aquí describe
    un rodeo por REPARAR- no puede cambiar ese plan mínimo.
    """
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    ejecutando = store.begin_work_item_execution(_WORK_ID, now=_AHORA)

    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.REVISAR,
        etiquetas=("sirius:reviewing",),
        historial_estados=(
            _acreditado("sirius:implementing", "no-head"),
            _acreditado("sirius:repair-requested", "1c934781"),
        ),
    )

    resultado = reflejar_desenlace(ejecutando, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_COMPROBACION_INICIADA,
        PASO_REVISION_INICIADA,
    )


# --- Sección G bis: la acreditación mide el salto, y es por tramo ----------
#
# Los dos agujeros que la revisión independiente de la PR #540 encontró en la
# sección G: la exigencia de acreditación intermedia se medía comparando con
# la foto -y hay pares (estado, fase) que ningún marcador puede producir, así
# que la comparación era falsa por construcción y no filtraba nada-, y la
# salida de una SEGUNDA parada dentro del recorrido se autorizaba sola.


def test_una_sola_observacion_posterior_no_acredita_aunque_la_foto_sea_reviewing() -> None:
    """CLAUDE-REV-001: la foto `sirius:reviewing` no la produce ningún marcador.

    Traza de la revisión: motor parado en `failed_safely`/`reparar`, espejo en
    (ACTIVE, REVISAR) por `sirius:reviewing`, sin marcador de reanudación, y
    un historial en el que lo ÚNICO acreditado tras la parada es una sola
    observación -exactamente lo que produce una etiqueta de parada sustituida
    a mano, porque `notify-sirius-state.yml` publica el marcador como
    `github-actions[bot]`, autor de confianza-.

    `notify-sirius-state.yml` solo vigila seis etiquetas, así que
    `sirius:reviewing` -> (ACTIVE, REVISAR) NUNCA aparece en el historial:
    comparar con la foto era una comprobación vacía. Lo que hay que medir es
    el salto, y aquí no hay nada entre el ancla y el destino.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.REVISAR,
        etiquetas=("sirius:reviewing",),
        historial_estados=(
            _acreditado("sirius:implementing", "no-head"),
            _acreditado("sirius:repair-requested", "1c934781"),
            _acreditado("sirius:failed-safely", "1c934781"),
            _acreditado("sirius:repair-requested", "786c82dc"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == (), (
        "una sola observación posterior al ancla no acredita ninguna secuencia: "
        "reactivar aquí es leer un relabelado a mano como orden del propietario"
    )
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante, no se toca nada" in resultado.divergencia
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.FAILED_SAFELY


def test_una_sola_observacion_posterior_no_acredita_aunque_la_foto_sea_ci_pending() -> None:
    """La gemela del anterior en la otra fase expuesta: `sirius:ci-pending`.

    `sirius:ci-pending` -> (ACTIVE, COMPROBAR) tampoco es una de las seis
    etiquetas notificadas, y `reflejar-desenlace.yml` se dispara por
    `workflow_run` al completarse los workflows del ciclo, así que esta foto
    es de las que la pasada real ve más a menudo.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.COMPROBAR,
        etiquetas=("sirius:ci-pending",),
        historial_estados=(
            _acreditado("sirius:implementing", "no-head"),
            _acreditado("sirius:failed-safely", "1c934781"),
            _acreditado("sirius:repair-requested", "786c82dc"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None


def test_la_acreditacion_intermedia_real_sigue_recorriendo_con_una_foto_no_notificada() -> None:
    """El endurecimiento no cierra el caso legítimo: mide el salto, no la foto.

    Mismo motor y misma foto no notificada (`sirius:reviewing`) que la prueba
    de arriba, pero aquí el historial SÍ acredita algo entre el ancla y el
    destino: tras la parada hubo DOS rondas de reparación, y la segunda
    `repair-requested` -sobre un head nuevo- es la observación intermedia que
    acredita el salto.

    Todas las etiquetas del historial son de las SEIS que
    `notify-sirius-state.yml` vigila, que son las únicas que
    `_interpretar_historial_estados` puede devolver: la cara positiva del
    endurecimiento tiene que demostrarse sobre una entrada que la proyección
    real pueda emitir, no sobre un `sirius:ci-pending` acreditado que ningún
    marcador `sirius-notification` produce jamás (CLAUDE-R2-002, ronda 2, PR
    #540). La foto sí puede ser `sirius:reviewing`: ahí es donde las etiquetas
    no notificadas aparecen de verdad en producción.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.REVISAR,
        etiquetas=("sirius:reviewing",),
        historial_estados=(
            _acreditado("sirius:implementing", "no-head"),
            _acreditado("sirius:failed-safely", "1c934781"),
            _acreditado("sirius:repair-requested", "786c82dc"),
            _acreditado("sirius:repair-requested", "92e5b9f4"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_REACTIVADO,
        PASO_REPARACION_REANUDADA,
        PASO_REVISION_INICIADA,
    )
    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert aplicados[-1].estado is WorkItemState.ACTIVE
    assert aplicados[-1].fase is WorkItemPhase.REVISAR


def test_la_segunda_parada_del_recorrido_no_sale_acreditada_por_la_foto_final() -> None:
    """CODEX-001 (ronda 1, PR #540): cada parada acredita su propia salida.

    El recorrido llega a un `blocked-decision` intermedio y lo único que hay
    DESPUÉS de esa segunda parada es la propia foto final. Resolver ahí la
    decisión sería continuar un `NEEDS_DECISION` sin ninguna orden del
    propietario -exactamente la salvaguarda de ADR-144-, así que el recorrido
    se abandona entero.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f469485c537c9cec5b37f6131f17d9903a",
        historial_estados=(
            _acreditado("sirius:failed-safely", "1c934781"),
            _acreditado("sirius:repair-requested", "786c82dc"),
            _acreditado("sirius:blocked-decision", "786c82dc"),
            _acreditado("sirius:completed", "92e5b9f4"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == (), (
        "la foto final no acredita la salida de la parada intermedia: "
        "sería resolver un NEEDS_DECISION sin orden del propietario"
    )
    assert resultado.divergencia is not None
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.FAILED_SAFELY


def test_la_segunda_parada_sale_cuando_una_observacion_posterior_la_acredita() -> None:
    """La cara positiva: la acreditación por tramo no prohíbe la segunda parada.

    Mismo recorrido que el anterior, pero ahora el historial acredita que la
    incidencia volvió a estar viva DESPUÉS del `blocked-decision` -otra
    `repair-requested` y un `ready-for-merge`, dos marcadores del bot
    posteriores a esa parada-, así que las dos salidas quedan acreditadas por
    su propia evidencia y el recorrido entero se aplica.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f469485c537c9cec5b37f6131f17d9903a",
        historial_estados=(
            _acreditado("sirius:failed-safely", "1c934781"),
            _acreditado("sirius:repair-requested", "786c82dc"),
            _acreditado("sirius:blocked-decision", "786c82dc"),
            _acreditado("sirius:repair-requested", "92e5b9f4"),
            _acreditado("sirius:ready-for-merge", "92e5b9f4"),
            _acreditado("sirius:completed", "92e5b9f4"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_REACTIVADO,
        PASO_ESCALADO,
        PASO_DECISION_RESUELTA,
        PASO_REPARACION_REANUDADA,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
        PASO_ENTREGADO,
    )
    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert aplicados[-1].estado is WorkItemState.DELIVERED


def test_una_sola_observacion_posterior_tampoco_acredita_desde_una_decision_bloqueada() -> None:
    """La exigencia mide el SALTO, y por eso vale para cualquier ancla del mapa.

    Motor detenido en `NEEDS_DECISION`/`REVISAR`, foto `sirius:ci-pending` ->
    (ACTIVE, COMPROBAR) -que ningún marcador `sirius-notification` puede
    producir- y un historial cuya única observación posterior al ancla es una
    `sirius:repair-requested`. Comparando con la foto, la comprobación era
    vacía y el motor resolvía la decisión y avanzaba dos fases apoyado en un
    solo marcador. Midiendo el salto, no hay nada entre el ancla y el destino:
    se declara y no se toca nada. El ancla es aquí `sirius:blocked-decision`,
    el único caso del mapa que ancla SOLO por estado -proyecta `fase=None`-,
    así que esta prueba cubre además esa forma de ancla.

    Antes anclaba en un `sirius:reviewing` acreditado y describía un motor
    vivo «sin ninguna parada de por medio». Las dos cosas eran imposibles a la
    vez: `sirius:reviewing` no es una de las SEIS etiquetas que
    `notify-sirius-state.yml` notifica, así que nunca aparece en el historial
    (CLAUDE-R2-002, ronda 2, PR #540); y con un ancla producible NO existe
    ninguna versión con el motor vivo, porque las tres etiquetas notificadas
    que proyectan ACTIVE son `implementing` (EJECUTAR), `repair-requested`
    (REPARAR) y `ready-for-merge` (ENTREGAR): desde las dos primeras el
    cálculo por foto ya alcanza `ci-pending` y `reviewing` -no hay divergencia
    que rescatar, así que el recorrido ni se intenta-, y desde ENTREGAR
    `_camino_de_fase` no tiene ninguna arista de avance, así que ningún
    recorrido llega a la foto. Medido con `_LABEL_STATE` y con la condición
    `if` de `notify-sirius-state.yml`.
    """
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    store.begin_work_item_check(_WORK_ID, now=_AHORA)
    store.begin_work_item_review(_WORK_ID, now=_AHORA)
    bloqueado = store.escalate_work_item(_WORK_ID, now=_AHORA)
    assert bloqueado.estado is WorkItemState.NEEDS_DECISION
    assert bloqueado.fase is WorkItemPhase.REVISAR

    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.COMPROBAR,
        etiquetas=("sirius:ci-pending",),
        historial_estados=(
            _acreditado("sirius:implementing", "no-head"),
            _acreditado("sirius:blocked-decision", "1c934781"),
            _acreditado("sirius:repair-requested", "1c934781"),
        ),
    )

    resultado = reflejar_desenlace(bloqueado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante, no se toca nada" in resultado.divergencia
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.NEEDS_DECISION


# --- Sección G ter: la salida de una parada no depende de la etiqueta vigente
#
# CLAUDE-R2-001 y CODEX-001 (ronda 2, PR #540): la primera forma de
# `_salida_de_parada_acreditada` pedía una observación posterior AL TRAMO
# -`objetivos[indice + 1:]`- en vez de la observación posterior A LA PARADA, y
# contaba como acreditación la ÚLTIMA del historial. El resultado era que el
# MISMO historial acreditado recorría o no según cuál fuera la etiqueta
# vigente en el instante de la pasada. Estas dos pruebas son el mismo
# historial visto con dos fotos distintas.

#: El historial acreditado del caso vivo de la #537 hasta `ready-for-merge`,
#: con las cinco etiquetas notificadas que `notify-sirius-state.yml` publica.
_HISTORIAL_HASTA_READY: tuple[EstadoAcreditado, ...] = (
    _acreditado("sirius:implementing", "no-head"),
    _acreditado("sirius:repair-requested", "1c934781"),
    _acreditado("sirius:failed-safely", "1c934781"),
    _acreditado("sirius:repair-requested", "786c82dc"),
    _acreditado("sirius:ready-for-merge", "786c82dc"),
)


def test_el_recorrido_acreditado_avanza_con_la_foto_intermedia_ready_for_merge() -> None:
    """La pasada que corre ANTES de `sirius:completed` recorre igual.

    `reflejar-desenlace.yml` se dispara por `workflow_run` al completarse los
    workflows del ciclo, así que la foto que la pasada ve más a menudo es una
    intermedia -aquí `sirius:ready-for-merge`, justo después del workflow de
    revisión-. El historial es el caso vivo de la #537 con un marcador menos, y
    acredita marcador a marcador la salida de la parada: la
    `sirius:repair-requested` de `786c82dc` es una observación del bot fechada
    DESPUÉS del `failed-safely`.

    Pidiendo una observación posterior al TRAMO, esta recuperación se
    rechazaba entera -`objetivos[1:]` era solo `ready-for-merge`, que ES la
    foto- mientras que la de la prueba siguiente, con el mismo historial más un
    marcador, sí se recorría. Dos pasadas sobre la misma evidencia con
    resultado opuesto, decidido por la etiqueta vigente.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:ready-for-merge",),
        historial_estados=_HISTORIAL_HASTA_READY,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_REACTIVADO,
        PASO_REPARACION_REANUDADA,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
    )
    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert aplicados[-1].estado is WorkItemState.ACTIVE
    assert aplicados[-1].fase is WorkItemPhase.ENTREGAR


def test_el_mismo_historial_recorre_igual_cuando_la_foto_ya_es_completed() -> None:
    """La gemela de la anterior: mismo historial, un marcador y una foto más.

    Minutos después se aplica `sirius:completed`, su marcador entra en el
    historial y la foto pasa a (DELIVERED, ENTREGAR). El recorrido es el mismo
    más la entrega. Que las dos pasen es lo que fija que la acreditación de
    salir de la parada ya no dependa de cuál sea la etiqueta vigente.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="786c82dc9d0f4a6f0f9a1b2c3d4e5f60718293a4",
        historial_estados=(
            *_HISTORIAL_HASTA_READY,
            _acreditado("sirius:completed", "786c82dc"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_REACTIVADO,
        PASO_REPARACION_REANUDADA,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
        PASO_ENTREGADO,
    )
    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert aplicados[-1].estado is WorkItemState.DELIVERED


def test_la_traza_literal_de_codex_recorre_los_siete_pasos_hasta_entregar() -> None:
    """CODEX-001 (ronda 2, PR #540), con su historial literal.

    `failed-safely → repair-requested → blocked-decision → repair-requested →
    completed`: el segundo `repair-requested` es una observación del bot
    posterior a la segunda parada y distinta de la foto, así que acredita su
    salida. Pidiendo una observación posterior AL TRAMO solo se miraba
    `completed` -que ES la foto-, y el recorrido se abandonaba entero.

    Su hermana `test_la_segunda_parada_del_recorrido_no_sale_acreditada_por_la
    _foto_final` conserva el rechazo cuando después del `blocked-decision` no
    hay nada más que la propia foto.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f469485c537c9cec5b37f6131f17d9903a",
        historial_estados=(
            _acreditado("sirius:failed-safely", "1c934781"),
            _acreditado("sirius:repair-requested", "786c82dc"),
            _acreditado("sirius:blocked-decision", "786c82dc"),
            _acreditado("sirius:repair-requested", "92e5b9f4"),
            _acreditado("sirius:completed", "92e5b9f4"),
        ),
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_REACTIVADO,
        PASO_ESCALADO,
        PASO_DECISION_RESUELTA,
        PASO_REPARACION_REANUDADA,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
        PASO_ENTREGADO,
    )
    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert aplicados[-1].estado is WorkItemState.DELIVERED
