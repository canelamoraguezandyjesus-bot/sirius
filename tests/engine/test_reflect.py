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
- Sección G: el recorrido acreditado y el permiso escrito que acredita salir
  de una parada (ADR-147, incidencia #545; material de partida de la PR #540).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sirius_engine.adapters.memory_store import InMemoryWorkEngineStore
from sirius_engine.domain.dispatch import DispatchEpisode
from sirius_engine.domain.mirror import (
    EstadoAcreditado,
    FormaDePermiso,
    MirroredWorkItem,
    OrigenLectura,
    PermisoDeReanudacion,
)
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
    permisos_reanudacion: tuple[PermisoDeReanudacion, ...] = (),
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
        permisos_reanudacion=permisos_reanudacion,
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


# --- Sección G: el recorrido acreditado y el permiso escrito (ADR-147, #545) ---
#
# Nota de arranque en ADR-147. El caso vivo es WI-20260905-034826 (incidencia
# #537): el motor se quedó en `failed_safely`/`reparar` en su parada de las
# 05:17 del 05-09-2026 y la incidencia siguió sin él -segunda orden `continua`
# a las 05:29, dos vueltas de Quality+revisión, `completed` a las 07:00-. El
# reflector comparaba su estado guardado con la foto actual, no encontraba
# camino hacia delante y se negaba (fail-open correcto, memoria
# desactualizada).
#
# El criterio que estas pruebas fijan, y que ADR-147 decidió ANTES de
# escribirlas: la salida de una parada la acredita ÚNICAMENTE un permiso
# escrito del propietario posterior a ESA parada, consumido en orden. Ni la
# foto vigente, ni la posición de un aviso, ni ninguna otra heurística.


def _cronologia(
    *entradas: tuple[str, str],
    desde: datetime | None = None,
) -> tuple[tuple[EstadoAcreditado, ...], tuple[PermisoDeReanudacion, ...]]:
    """El historial de confianza como UNA secuencia, con su ``orden`` compartido.

    Cada entrada es ``("estado", "<etiqueta>")`` -un marcador
    ``sirius-notification``-, ``("marcador"|"orden", "<referencia>")`` -un
    permiso escrito del propietario- o ``("diagnostico", "<texto>")`` -un
    comentario de veredicto ``FAILED_SAFELY`` con su diagnóstico-, en el orden
    en que se publicaron; el ``orden`` se asigna por posición, exactamente como
    hace la proyección real sobre los textos de confianza.

    Que las tres cosas se declaren JUNTAS es deliberado: lo que el reflector
    mide es la posición relativa entre una parada, el permiso que la levanta y
    el diagnóstico que la explica, y unas listas independientes dejarían esa
    relación escrita en ningún sitio -que es justo como se colaba la foto en
    las tres rondas de la #539-.

    Con ``desde``, cada posición recibe además su instante de publicación (un
    minuto por posición, que es todo lo que hace falta para ordenarlos), igual
    que la proyección le pone a cada marcador el ``creado_en`` de su
    comentario. Sin ``desde`` no hay instantes: es el caso del marcador que
    viene del cuerpo de la incidencia, que no tiene ninguno.

    El diagnóstico se atribuye igual que en la proyección -el último publicado
    hasta la posición del marcador, y solo a las paradas ``FAILED_SAFELY``-.
    """
    estados: list[EstadoAcreditado] = []
    permisos: list[PermisoDeReanudacion] = []
    diagnostico_vigente: str | None = None
    for orden, (tipo, referencia) in enumerate(entradas):
        if tipo == "diagnostico":
            diagnostico_vigente = referencia
        elif tipo == "estado":
            estado, fase = _LABEL_STATE[referencia]
            estados.append(
                EstadoAcreditado(
                    etiqueta=referencia,
                    estado=estado,
                    fase=fase,
                    head="1c934781",
                    orden=orden,
                    publicado_en=(desde + timedelta(minutes=orden) if desde is not None else None),
                    diagnostico=(
                        diagnostico_vigente if estado is WorkItemState.FAILED_SAFELY else None
                    ),
                )
            )
        else:
            permisos.append(
                PermisoDeReanudacion(
                    forma=FormaDePermiso.MARCADOR if tipo == "marcador" else FormaDePermiso.ORDEN,
                    referencia=referencia,
                    orden=orden,
                )
            )
    return tuple(estados), tuple(permisos)


#: El historial de confianza REAL de la incidencia #537, medido con
#: `gh api repos/.../issues/537/comments --paginate` el 05-09-2026 y recortado
#: a lo que la proyección extrae: los marcadores `sirius-notification` y los
#: permisos escritos. Los dos hechos que lo hacen el caso vivo:
#:
#: - el ÚNICO marcador de reanudación (`sirius-resume-stop:1c934781`, 04:46:18Z)
#:   es ANTERIOR a la parada de las 05:17 y quedó consumido por la salida del
#:   `blocked-decision` de las 04:37;
#: - lo que hay DESPUÉS de la parada es la orden `continua` del propietario
#:   (05:29:04Z). No hay segundo marcador porque `sirius_comment_once`
#:   deduplica por el texto completo y el head no se había movido.
_CRONOLOGIA_537 = _cronologia(
    ("estado", "sirius:implementing"),
    ("estado", "sirius:repair-requested"),
    ("estado", "sirius:blocked-decision"),
    ("orden", "continua"),
    ("marcador", "<!-- sirius-resume-stop:1c934781 -->"),
    ("estado", "sirius:failed-safely"),
    ("orden", "continua"),
    ("estado", "sirius:repair-requested"),
    ("estado", "sirius:ready-for-merge"),
    ("estado", "sirius:completed"),
)


def _motor_parado_en_reparar(
    store: InMemoryWorkEngineStore,
    *,
    diagnostico: str = "sin tiempo",
    parado_en: datetime = _AHORA,
) -> WorkItem:
    """El estado exacto en que se quedó WI-20260905-034826: failed_safely/reparar.

    ``diagnostico`` y ``parado_en`` son la evidencia que el ALMACÉN guarda de
    su parada -el texto que le llegó y el instante en que la escribió-, y son
    lo que permite correlacionar en qué ocurrencia del historial se quedó
    cuando hay varias iguales (CODEX-002, ronda 2, PR #546).
    """
    _work_item_activo(store)
    store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    store.begin_work_item_check(_WORK_ID, now=_AHORA)
    store.begin_work_item_review(_WORK_ID, now=_AHORA)
    store.request_work_item_repair(_WORK_ID, now=_AHORA)
    parado = store.fail_work_item_safely(_WORK_ID, diagnostico=diagnostico, now=parado_en)
    assert parado.estado is WorkItemState.FAILED_SAFELY
    assert parado.fase is WorkItemPhase.REPARAR
    return parado


def _motor_bloqueado_en_revisar(store: InMemoryWorkEngineStore) -> WorkItem:
    """Un motor anclado en ``needs_decision``/``revisar``: la otra parada del dominio."""
    _work_item_activo(store)
    store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    store.begin_work_item_check(_WORK_ID, now=_AHORA)
    store.begin_work_item_review(_WORK_ID, now=_AHORA)
    bloqueado = store.escalate_work_item(_WORK_ID, now=_AHORA)
    assert bloqueado.estado is WorkItemState.NEEDS_DECISION
    assert bloqueado.fase is WorkItemPhase.REVISAR
    return bloqueado


def test_recorrido_acreditado_avanza_el_caso_vivo_de_la_537() -> None:
    """El caso que motivó ADR-147, con el historial real de la incidencia #537.

    El espejo NO trae `reanudacion_publicada`: el único marcador de
    reanudación es anterior a la parada. Lo que acredita la salida es la orden
    `continua` del propietario de las 05:29, posterior a ella.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _CRONOLOGIA_537
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f469485c537c9cec5b37f6131f17d9903a",
        historial_estados=historial,
        permisos_reanudacion=permisos,
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


def test_sin_permiso_posterior_a_la_parada_se_declara_y_no_se_toca_nada() -> None:
    """Contraejemplo 1 de la incidencia #545: la revivificación H-34 de etiqueta.

    Mismo motor, misma foto y el MISMO camino acreditado que el caso vivo, con
    una sola diferencia: nadie escribió nada tras la parada. La recuperación
    queda como divergencia declarada hasta que una persona la mire. Es la
    consecuencia aceptada y deliberada del encargo: es honesto y no inventa
    permisos.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:implementing"),
        ("estado", "sirius:failed-safely"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    assert permisos == ()
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=historial,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante, no se toca nada" in resultado.divergencia
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.FAILED_SAFELY


def test_un_permiso_anterior_a_la_parada_no_la_levanta() -> None:
    """La premisa que la primera ronda de la #545 midió falsa, convertida en prueba.

    El historial de la #537 contiene un marcador de reanudación, pero es de
    las 04:46 y la parada es de las 05:17: ya lo consumió la salida del
    `blocked-decision` anterior. Un permiso anterior a la parada no acredita
    nada, y al saltárselo queda descartado para siempre.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:implementing"),
        ("marcador", "<!-- sirius-resume-stop:1c934781 -->"),
        ("estado", "sirius:failed-safely"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None


def test_el_marcador_de_reanudacion_acredita_igual_que_la_orden() -> None:
    """Las dos formas del permiso pesan lo mismo (ADR-147).

    Misma cronología que la prueba anterior con el marcador movido DESPUÉS de
    la parada: el recibo de la máquina, cuando existe y es posterior, acredita
    exactamente igual que la orden del propietario.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:implementing"),
        ("estado", "sirius:failed-safely"),
        ("marcador", "<!-- sirius-resume-stop:1c934781 -->"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=historial,
        permisos_reanudacion=permisos,
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


def test_dos_paradas_y_un_solo_permiso_no_acreditan_la_segunda() -> None:
    """Contraejemplo 2 de la incidencia #545 (el de la ronda 3 de la #539).

    El recorrido pasa por un `blocked-decision` intermedio y solo hay UN
    permiso posterior a la primera parada. La primera salida se acredita; la
    segunda no, así que el recorrido se abandona entero: un `needs_decision`
    jamás se resuelve en el almacén sin su permiso.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:blocked-decision"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f4",
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == (), (
        "ni la foto final ni los avisos de estado posteriores acreditan la "
        "salida de la segunda parada: sería resolver un NEEDS_DECISION sin "
        "ninguna orden del propietario"
    )
    assert resultado.divergencia is not None
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.FAILED_SAFELY


def test_dos_paradas_con_su_permiso_cada_una_recorren_entero() -> None:
    """La cara positiva del contraejemplo 2: cada parada con SU permiso.

    Mismo recorrido que la prueba anterior más una segunda orden `continua`,
    esta vez posterior al `blocked-decision`. Las dos salidas quedan
    acreditadas por su propio permiso y el recorrido entero se aplica.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:blocked-decision"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f4",
        historial_estados=historial,
        permisos_reanudacion=permisos,
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


def test_un_permiso_no_puede_acreditar_dos_salidas_de_parada() -> None:
    """El consumo en orden: el puntero solo avanza.

    Un solo `continua`, y está DESPUÉS de las dos paradas del recorrido: es
    posterior a la primera -así que la acredita- y también posterior a la
    segunda. Si el consumo no gastara el permiso -si se limitara a preguntar
    «¿hay alguno posterior a esta parada?»-, ese único `continua` levantaría
    las dos y el `NEEDS_DECISION` se resolvería en el almacén con la palabra
    que el propietario escribió para otra cosa.

    Es la mutación que fija que la k-ésima salida consume el primer permiso
    AÚN NO CONSUMIDO, no simplemente el primero posterior. Su hermana
    `test_dos_paradas_con_su_permiso_cada_una_recorren_entero` fija que dos
    permisos sí bastan.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:failed-safely"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:blocked-decision"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:completed"),
    )
    assert len(permisos) == 1
    assert permisos[0].orden > historial[2].orden, (
        "el único permiso es posterior a las DOS paradas: lo que lo impide no "
        "es su fecha, es que ya se gastó en la primera"
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f4",
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None


#: Dos vueltas de reparación, cada parada con su permiso: el mismo
#: ``(failed_safely, reparar)`` aparece DOS veces (posiciones 0 y 3) y la
#: posición, por sí sola, no dice en cuál de las dos se quedó el almacén.
_DOS_PARADAS_IGUALES: tuple[tuple[str, str], ...] = (
    ("estado", "sirius:failed-safely"),
    ("orden", "continua"),
    ("estado", "sirius:repair-requested"),
    ("estado", "sirius:failed-safely"),
    ("orden", "continua"),
    ("estado", "sirius:repair-requested"),
    ("estado", "sirius:ready-for-merge"),
    ("estado", "sirius:completed"),
)

#: El instante de la posición 0 de ``_DOS_PARADAS_IGUALES``; ``_cronologia``
#: reparte un minuto por posición, así que la segunda parada (posición 3) se
#: publica tres minutos después.
_INICIO_DEL_HISTORIAL = datetime(2026, 9, 5, 5, 0, tzinfo=UTC)

#: Los siete pasos de recorrer las DOS vueltas: la primera recuperación, la
#: segunda parada y la segunda recuperación, ninguna omitida.
_RECORRIDO_DESDE_LA_PRIMERA_PARADA = (
    PASO_REACTIVADO,
    PASO_FALLO_SEGURO,
    PASO_REACTIVADO,
    PASO_REPARACION_REANUDADA,
    PASO_REVISION_INICIADA,
    PASO_REVISION_APROBADA,
    PASO_ENTREGADO,
)

#: Los cinco de recorrer solo la segunda: es lo que corresponde cuando el
#: almacén guardó la SEGUNDA parada, y lo que sería un salto si guardó la
#: primera.
_RECORRIDO_DESDE_LA_SEGUNDA_PARADA = (
    PASO_REACTIVADO,
    PASO_REPARACION_REANUDADA,
    PASO_REVISION_INICIADA,
    PASO_REVISION_APROBADA,
    PASO_ENTREGADO,
)


def _espejo_de_dos_paradas(
    historial: tuple[EstadoAcreditado, ...], permisos: tuple[PermisoDeReanudacion, ...]
) -> MirroredWorkItem:
    return _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )


def test_el_recorrido_ancla_en_la_ocurrencia_que_el_almacen_pudo_guardar() -> None:
    """El tiempo correlaciona: un aviso posterior a la escritura no es el guardado.

    Mismo historial que su gemela y el mismo motor, con una sola diferencia: el
    almacén escribió su parada UN MINUTO después de la primera y dos antes de
    la segunda, así que la segunda no puede ser la que guardó. El recorrido
    empieza en la primera y registra la recuperación intermedia y la segunda
    parada, en vez de saltárselas (CODEX-002, ronda 2, PR #546).
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store, parado_en=_INICIO_DEL_HISTORIAL + timedelta(minutes=1))
    historial, permisos = _cronologia(*_DOS_PARADAS_IGUALES, desde=_INICIO_DEL_HISTORIAL)
    segunda_parada = historial[2]
    assert segunda_parada.estado is WorkItemState.FAILED_SAFELY
    assert segunda_parada.publicado_en == _INICIO_DEL_HISTORIAL + timedelta(minutes=3), (
        "la segunda parada se publica DESPUÉS de la escritura del almacén"
    )

    resultado = reflejar_desenlace(parado, _espejo_de_dos_paradas(historial, permisos), _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == _RECORRIDO_DESDE_LA_PRIMERA_PARADA


def test_el_recorrido_ancla_en_la_segunda_parada_cuando_el_almacen_es_posterior() -> None:
    """La cara opuesta: si el almacén escribió después de las dos, se quedó en la última.

    El mismo historial, minuto a minuto, y un almacén que escribió su parada
    una hora después del final: las dos ocurrencias son posibles, y entonces el
    motor está donde se quedó, no donde estuvo la primera vez. Que las dos
    pruebas den resultados DISTINTOS sobre el mismo historial es lo que
    demuestra que el ancla se correlaciona en vez de elegirse por costumbre.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store, parado_en=_INICIO_DEL_HISTORIAL + timedelta(hours=1))
    historial, permisos = _cronologia(*_DOS_PARADAS_IGUALES, desde=_INICIO_DEL_HISTORIAL)

    resultado = reflejar_desenlace(parado, _espejo_de_dos_paradas(historial, permisos), _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == _RECORRIDO_DESDE_LA_SEGUNDA_PARADA


def test_el_diagnostico_guardado_identifica_la_parada_cuando_el_tiempo_no_discrimina() -> None:
    """La identidad del suceso: el mismo texto escrito dos veces no es una preferencia.

    Sin instantes -el caso del marcador que viene del cuerpo- el tiempo no
    descarta ninguna de las dos ocurrencias. Lo que sí las distingue es el
    diagnóstico que el almacén guarda de SU parada: es el de la primera, y solo
    una ocurrencia del historial lo lleva.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store, diagnostico="la ronda 1 se quedó sin turnos")
    historial, permisos = _cronologia(
        ("diagnostico", "la ronda 1 se quedó sin turnos"),
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("diagnostico", "la ronda 2 agotó el tiempo del job"),
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    assert [acreditado.publicado_en for acreditado in historial] == [None] * len(historial)

    resultado = reflejar_desenlace(parado, _espejo_de_dos_paradas(historial, permisos), _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == _RECORRIDO_DESDE_LA_PRIMERA_PARADA


def test_un_marcador_con_otro_diagnostico_no_ancla_la_parada_guardada() -> None:
    """Un ancla que el diagnóstico guardado CONTRADICE no es un ancla.

    El notificador deduplica por estado y head (`notify-sirius-state.yml`), así
    que una segunda parada `failed-safely` sobre el mismo head puede no dejar
    marcador propio: en el historial solo está el de la PRIMERA, y lleva su
    diagnóstico. El motor, en cambio, guarda el de la segunda. Anclar ahí
    levantaría la segunda parada con el permiso de la primera y entregaría la
    incidencia; lo que corresponde es abstenerse -conservar la parada sin
    permiso- porque el propio texto guardado dice que esa ocurrencia no es la
    suya (CODEX-002, ronda 3, PR #546).
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store, diagnostico="la ronda 2 agotó el tiempo del job")
    historial, permisos = _cronologia(
        ("diagnostico", "la ronda 1 se quedó sin turnos"),
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("diagnostico", "la ronda 2 agotó el tiempo del job"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    paradas = [
        acreditado for acreditado in historial if acreditado.estado is WorkItemState.FAILED_SAFELY
    ]
    assert [acreditado.diagnostico for acreditado in paradas] == [
        "la ronda 1 se quedó sin turnos"
    ], "el historial solo trae el marcador de la PRIMERA parada, con su propio diagnóstico"

    resultado = reflejar_desenlace(parado, _espejo_de_dos_paradas(historial, permisos), _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None


def test_sin_ancla_en_el_historial_no_hay_recorrido() -> None:
    """El estado guardado tiene que estar EN el historial acreditado.

    Un historial que nunca menciona el estado del motor no conecta nada con
    nada: recorrerlo sería empezar por un punto que nadie acreditó, y el
    permiso escrito no diría a qué parada corresponde.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:implementing"),
        ("orden", "continua"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None


def test_un_aviso_publicado_fuera_de_orden_no_envenena_el_recorrido() -> None:
    """El orden de publicación de los avisos NO es el orden de aplicación.

    `notify-sirius-state.yml` incluye el nombre de la etiqueta en su grupo de
    concurrencia, así que dos etiquetas distintas no se serializan entre sí y
    un aviso puede publicarse tarde: aquí el de `sirius:ready-for-merge` llega
    después del de `sirius:completed`. Tratar esa posición como autoritativa
    dejaba el recorrido en cero pasos y «no hay camino hacia delante» para
    siempre, aunque la foto vigente sea `completed` (CODEX-001, ronda 2, PR
    #546). Lo que se reconstruye es una SUBSECUENCIA legal hasta la foto: el
    aviso retrasado no mueve el recorrido y tampoco lo tumba.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:completed"),
        ("estado", "sirius:ready-for-merge"),
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f4",
        historial_estados=historial,
        permisos_reanudacion=permisos,
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


def test_un_aviso_de_PARADA_que_no_encaja_abandona_el_recorrido_entero() -> None:
    """La primera excepción: un aviso de parada no se salta nunca.

    Saltarse un aviso a destiempo es no moverse por él; saltarse una PARADA
    sería pasar por encima de ella sin exigir su permiso, que es exactamente la
    garantía que ADR-147 fija. Aquí el `blocked-decision` no encaja donde está
    publicado -el recorrido ya ha entregado- y el recorrido se abandona entero:
    ni se aplica el trozo bueno ni se resuelve un `NEEDS_DECISION` que nadie
    autorizó.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:completed"),
        ("estado", "sirius:blocked-decision"),
        ("estado", "sirius:completed"),
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f4",
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.FAILED_SAFELY


def test_un_recorrido_que_no_termina_en_la_foto_no_se_aplica() -> None:
    """La segunda excepción: el tramo final contra la foto tampoco se salta.

    El historial acredita aquí una entrega, pero la foto vigente proyecta
    `sirius:reviewing` -que `notify-sirius-state.yml` no notifica, así que
    jamás aparece en el historial-. Un recorrido que llega a `delivered` no
    termina en esa foto, y terminar cerca no es terminar: todo o nada.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:completed"),
    )
    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.REVISAR,
        etiquetas=("sirius:reviewing",),
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None


def test_cada_parada_del_recorrido_conserva_SU_diagnostico() -> None:
    """Un diagnóstico es la evidencia de UNA parada, no del ciclo entero.

    El motor está anclado en `needs_decision` y el historial acredita dos
    fallos seguros con diagnósticos distintos antes de `completed`. Al fabricar
    cada espejo histórico solo se sustituían estado, fase y etiquetas, así que
    los dos sucesos se escribían con el diagnóstico de la ÚLTIMA parada de toda
    la incidencia -el único que el espejo expone- y el diario perdía la
    evidencia real de la primera (CODEX-003, ronda 2, PR #546). El de la foto
    vigente no cambia: lo sigue poniendo el espejo real.
    """
    store = InMemoryWorkEngineStore()
    bloqueado = _motor_bloqueado_en_revisar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:blocked-decision"),
        ("orden", "continua"),
        ("diagnostico", "la ronda 1 se quedó sin turnos"),
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("diagnostico", "la ronda 2 agotó el tiempo del job"),
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        head_sha="92e5b9f4",
        diagnostico_fallo="la ronda 2 agotó el tiempo del job",
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(bloqueado, espejo, _episodio())

    assert resultado.divergencia is None
    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_DECISION_RESUELTA,
        PASO_FALLO_SEGURO,
        PASO_REACTIVADO,
        PASO_REPARACION_SOLICITADA,
        PASO_FALLO_SEGURO,
        PASO_REACTIVADO,
        PASO_REPARACION_REANUDADA,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
        PASO_ENTREGADO,
    )
    diagnosticos = [paso.diagnostico for paso in resultado.pasos if paso.kind == PASO_FALLO_SEGURO]
    assert diagnosticos == [
        "la ronda 1 se quedó sin turnos",
        "la ronda 2 agotó el tiempo del job",
    ], "cada parada se escribe con su propia evidencia, no con la de la última"
    aplicados = aplicar_pasos(store, _WORK_ID, resultado.pasos, now=_AHORA)
    assert aplicados[-1].estado is WorkItemState.DELIVERED


def test_una_parada_sin_diagnostico_atribuible_no_recrea_ninguno() -> None:
    """Abstenerse es la otra mitad: no se inventa un diagnóstico que no es suyo.

    Mismo recorrido, con el diagnóstico de la primera parada publicado DESPUÉS
    de ella -no hay ninguno atribuible hasta ese marcador-. El suceso se
    escribe declarando que no lo hay, en vez de heredar el de la parada
    siguiente.
    """
    store = InMemoryWorkEngineStore()
    bloqueado = _motor_bloqueado_en_revisar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:blocked-decision"),
        ("orden", "continua"),
        ("estado", "sirius:failed-safely"),
        ("diagnostico", "la ronda 2 agotó el tiempo del job"),
        ("orden", "continua"),
        ("estado", "sirius:ready-for-merge"),
        ("estado", "sirius:completed"),
    )
    espejo = _espejo(
        estado=WorkItemState.DELIVERED,
        fase=WorkItemPhase.ENTREGAR,
        etiquetas=("sirius:completed",),
        diagnostico_fallo="la ronda 2 agotó el tiempo del job",
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(bloqueado, espejo, _episodio())

    assert resultado.divergencia is None
    fallos = [paso for paso in resultado.pasos if paso.kind == PASO_FALLO_SEGURO]
    assert len(fallos) == 1
    assert fallos[0].diagnostico == (
        "la incidencia lleva sirius:failed-safely sin diagnóstico de confianza publicado"
    )


def test_el_recorrido_solo_entra_cuando_la_foto_sola_no_basta() -> None:
    """El cálculo por foto manda: el recorrido es el plan B, no el plan A.

    Con un motor ACTIVE/EJECUTAR y una foto ACTIVE/REVISAR, el cálculo de
    siempre ya encuentra camino; el historial acreditado -que aquí describe
    un rodeo por REPARAR- no puede cambiar ese plan mínimo.
    """
    store = InMemoryWorkEngineStore()
    _work_item_activo(store)
    ejecutando = store.begin_work_item_execution(_WORK_ID, now=_AHORA)
    historial, permisos = _cronologia(
        ("estado", "sirius:implementing"),
        ("estado", "sirius:repair-requested"),
        ("orden", "continua"),
    )
    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.REVISAR,
        etiquetas=("sirius:reviewing",),
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(ejecutando, espejo, _episodio())

    assert tuple(paso.kind for paso in resultado.pasos) == (
        PASO_COMPROBACION_INICIADA,
        PASO_REVISION_INICIADA,
    )


def test_las_etiquetas_contradictorias_siguen_sin_recorrer_nada() -> None:
    """Invariante de la incidencia #545: las contradicciones se declaran, no se recorren.

    Con etiquetas de estado que se contradicen no hay foto a la que llegar, y
    un permiso escrito en el historial no cambia eso: el recorrido no tiene
    destino.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _CRONOLOGIA_537
    espejo = _espejo(
        estado=None,
        fase=None,
        etiquetas=("sirius:completed", "sirius:implementing"),
        etiquetas_contradictorias=True,
        historial_estados=historial,
        permisos_reanudacion=permisos,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == ()
    assert resultado.divergencia is not None
    assert "etiquetas de estado que se contradicen" in resultado.divergencia


# --- Sección G bis: la acreditación no mira la foto, ni de refilón ---------
#
# Las tres rondas de la incidencia #539 encontraron la MISMA familia de
# defecto: el criterio de acreditación se apoyaba, por una puerta o por otra,
# en la etiqueta vigente en el instante de la pasada. Estas pruebas son las
# trazas literales de esas rondas, con el criterio de ADR-147.


def test_ni_la_foto_ni_un_aviso_de_estado_acreditan_la_salida_de_una_parada() -> None:
    """CLAUDE-REV-001 (ronda 1, PR #540): el relabelado a mano no es un permiso.

    Motor parado en `failed_safely`/`reparar`, foto `sirius:reviewing` -que
    `notify-sirius-state.yml` NO notifica, así que jamás aparece en el
    historial- y una sola observación del bot tras la parada. Es exactamente
    lo que produce una etiqueta de parada sustituida a mano: el marcador de
    notificación lo publica `github-actions[bot]`, autor de confianza, así que
    la observación es auténtica. Lo que falta es el permiso, y sin él no se
    toca nada.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, _ = _cronologia(
        ("estado", "sirius:implementing"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:failed-safely"),
        ("estado", "sirius:repair-requested"),
    )
    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.REVISAR,
        etiquetas=("sirius:reviewing",),
        historial_estados=historial,
    )

    resultado = reflejar_desenlace(parado, espejo, _episodio())

    assert resultado.pasos == (), (
        "reactivar aquí es leer un relabelado a mano como orden del propietario"
    )
    assert resultado.divergencia is not None
    assert "no hay camino hacia delante, no se toca nada" in resultado.divergencia
    item = store.get_work_item(_WORK_ID)
    assert item is not None
    assert item.estado is WorkItemState.FAILED_SAFELY


def test_el_mismo_historial_con_el_permiso_del_propietario_si_recorre() -> None:
    """La cara positiva de la anterior: lo único que cambia es la palabra escrita.

    Mismo motor, misma foto no notificada y el mismo historial de estados. Se
    añade la orden `continua` del propietario después de la parada, y eso -y
    solo eso- es lo que convierte una divergencia declarada en un recorrido.
    """
    store = InMemoryWorkEngineStore()
    parado = _motor_parado_en_reparar(store)
    historial, permisos = _cronologia(
        ("estado", "sirius:implementing"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
    )
    espejo = _espejo(
        estado=WorkItemState.ACTIVE,
        fase=WorkItemPhase.REVISAR,
        etiquetas=("sirius:reviewing",),
        historial_estados=historial,
        permisos_reanudacion=permisos,
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


def test_la_acreditacion_no_depende_de_la_etiqueta_vigente_en_la_pasada() -> None:
    """CLAUDE-R2-001 y CODEX-001 (ronda 2, PR #540): el mismo historial, dos fotos.

    `reflejar-desenlace.yml` se dispara por `workflow_run`, así que la misma
    recuperación se observa varias veces con etiquetas distintas: primero
    `sirius:ready-for-merge`, minutos después `sirius:completed`. Con el
    criterio anterior el resultado dependía de cuál tocara -dos pasadas sobre
    la misma evidencia con resultado opuesto-. Con el permiso escrito, la
    acreditación es la misma en las dos y solo cambia el destino.
    """
    hasta_ready = (
        ("estado", "sirius:implementing"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:failed-safely"),
        ("orden", "continua"),
        ("estado", "sirius:repair-requested"),
        ("estado", "sirius:ready-for-merge"),
    )

    store_ready = InMemoryWorkEngineStore()
    parado_ready = _motor_parado_en_reparar(store_ready)
    historial, permisos = _cronologia(*hasta_ready)
    resultado_ready = reflejar_desenlace(
        parado_ready,
        _espejo(
            estado=WorkItemState.ACTIVE,
            fase=WorkItemPhase.ENTREGAR,
            etiquetas=("sirius:ready-for-merge",),
            historial_estados=historial,
            permisos_reanudacion=permisos,
        ),
        _episodio(),
    )

    store_completed = InMemoryWorkEngineStore()
    parado_completed = _motor_parado_en_reparar(store_completed)
    historial, permisos = _cronologia(*hasta_ready, ("estado", "sirius:completed"))
    resultado_completed = reflejar_desenlace(
        parado_completed,
        _espejo(
            estado=WorkItemState.DELIVERED,
            fase=WorkItemPhase.ENTREGAR,
            etiquetas=("sirius:completed",),
            head_sha="786c82dc",
            historial_estados=historial,
            permisos_reanudacion=permisos,
        ),
        _episodio(),
    )

    esperado = (
        PASO_REACTIVADO,
        PASO_REPARACION_REANUDADA,
        PASO_REVISION_INICIADA,
        PASO_REVISION_APROBADA,
    )
    assert tuple(paso.kind for paso in resultado_ready.pasos) == esperado
    assert tuple(paso.kind for paso in resultado_completed.pasos) == (*esperado, PASO_ENTREGADO)
    assert resultado_ready.divergencia is None
    assert resultado_completed.divergencia is None
