"""``reflejar_desenlace``: el reflejo del desenlace de GitHub en el almacén (C1, incidencia #529).

El motor despacha por la vía GitHub (C2, :mod:`sirius_engine.dispatcher`) y
desde entonces no vuelve a enterarse de nada: :func:`dispatch_work_item`
escribe la incidencia y aplica la etiqueta inicial, pero nunca vuelve a tocar
el ``WorkEngineStore`` -ni siquiera para pasar el ``WorkItem`` a ``WAITING``
(``dispatch_work_item_async`` tiene cero llamantes en ``src/``, medido para
esta incidencia). Así que todo trabajo despachado se queda para siempre en
``ACTIVE``/``PREPARAR`` en el diario del motor, mientras su incidencia real
avanza por las siete fases del ciclo revisar-reparar hasta cerrarse. Este
módulo es la costura que falta: dado el ``WorkItem`` vigente y lo que el
espejo de solo lectura (A3, :mod:`sirius_engine.mirror_projection`) proyecta
de su incidencia, calcula y aplica la secuencia MÍNIMA de transiciones del
almacén que lleva del uno al otro.

Dos funciones, deliberadamente separadas:

- :func:`reflejar_desenlace` -pura, sin almacén- calcula el PLAN: qué
  transiciones haría falta aplicar, en qué orden, sin tocar nada. Es lo que
  ``--ensayo`` imprime.
- :func:`aplicar_pasos` -con almacén, sin GitHub ni disco: el almacén que
  reciba puede ser :class:`~sirius_engine.adapters.memory_store.InMemoryWorkEngineStore`
  en una prueba o el durable en producción, ninguno de los dos habla por la
  red- ejecuta ese plan llamando, paso a paso, exactamente los puertos que
  :mod:`sirius_engine.ports.store` ya declara (``begin_work_item_execution``,
  ``begin_work_item_check``, ``begin_work_item_review``,
  ``approve_work_item_review``, ``request_work_item_repair``,
  ``resume_work_item_after_repair``, ``deliver_work_item``,
  ``fail_work_item_safely``, ``escalate_work_item``,
  ``reactivate_work_item``, ``resolve_work_item_decision``). Ninguno es
  nuevo: reflejar no añade vocabulario al almacén, solo lo llama por primera
  vez desde un camino de producción real.

**Reglas, en el orden en que se comprueban** (objetivo de la incidencia):

1. **Etiquetas contradictorias** -> no se toca nada; se devuelve el motivo.
2. **Sin etiqueta de estado reconocida** -> no se toca nada, sin motivo: es
   el estado normal de una incidencia recién despachada.
3. **Nunca hacia atrás.** El plan se calcula caminando hacia delante por el
   grafo real del dominio (arquitectura §3.4): ``PREPARAR -> EJECUTAR ->
   COMPROBAR -> REVISAR -> {REPARAR|ENTREGAR}``, con ``REPARAR -> COMPROBAR``
   como único camino de vuelta (el bucle revisar-reparar real). Si el
   objetivo no es alcanzable caminando solo hacia delante -incluido el caso
   en que el motor ya está más adelante que lo que la incidencia proyecta-,
   no se toca nada; se devuelve el motivo. Única excepción: si el espejo
   proyecta ACTIVE mientras el motor sigue en FAILED_SAFELY o NEEDS_DECISION,
   no es "hacia atrás" -es una reanudación autoritativa ya registrada por el
   propietario (``sirius_resume_on_command.sh``, CODEX-002, PR #530)-, así
   que primero se reactiva/resuelve la decisión con el puerto existente que
   corresponda y el camino de fase se calcula igual que siempre.
4. **Nunca inventa.** El plan usa exclusivamente los puertos ya existentes
   del almacén, con exactamente los datos que el espejo trae (SHA de fusión,
   diagnóstico de fallo); si algo hiciera falta que el espejo no expone o que
   el almacén no sabe hacer, la función no lo inventa -no hay tal caso hoy
   con el vocabulario del mapa etiqueta -> (estado, fase).
5. **Idempotente por construcción.** Si el ``WorkItem`` ya está exactamente
   en el objetivo, el camino calculado está vacío: una segunda pasada sobre
   el mismo espejo no añade ningún suceso.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sirius_engine.domain.dispatch import DispatchEpisode
from sirius_engine.domain.mirror import MirroredWorkItem
from sirius_engine.domain.work_item import WorkItem, WorkItemPhase, WorkItemState
from sirius_engine.ports.store import WorkEngineStore

#: Los nombres de paso son exactamente los ``EventKind`` que produce cada
#: puerto (:mod:`sirius_engine.domain.events`): no es una nomenclatura nueva,
#: es la ya existente, para que una prueba pueda comparar contra
#: ``store.list_events()`` sin traducir nada.
PASO_EJECUCION_INICIADA = "work_item_execution_started"
PASO_COMPROBACION_INICIADA = "work_item_check_started"
PASO_REVISION_INICIADA = "work_item_review_started"
PASO_REVISION_APROBADA = "work_item_review_approved"
PASO_REPARACION_SOLICITADA = "work_item_repair_requested"
PASO_REPARACION_REANUDADA = "work_item_repair_resumed"
PASO_ENTREGADO = "work_item_delivered"
PASO_FALLO_SEGURO = "work_item_failed_safely"
PASO_ESCALADO = "work_item_escalated"
PASO_REACTIVADO = "work_item_reactivated"
PASO_DECISION_RESUELTA = "work_item_decision_resolved"


@dataclass(frozen=True, slots=True)
class PasoReflejo:
    """Un paso planificado: qué transición del almacén, con sus datos si los necesita."""

    kind: str
    resultado: Mapping[str, object] | None = None
    diagnostico: str | None = None


@dataclass(frozen=True, slots=True)
class ResultadoReflejo:
    """El plan que produce :func:`reflejar_desenlace`, listo para aplicarse o imprimirse.

    ``divergencia`` lleva el motivo cuando ``pasos`` está vacío por una razón
    que vale la pena contar -hacia atrás, contradicción, o un estado del
    motor del que el vocabulario de reflejo no sabe salir-. Es ``None`` tanto
    cuando el plan tiene pasos como cuando no hay nada que decir todavía
    -incidencia sin etiqueta de estado, o motor ya en el objetivo (idempotencia)-.
    """

    pasos: tuple[PasoReflejo, ...]
    divergencia: str | None = None


def _describir(work_item: WorkItem) -> str:
    return f"estado={work_item.estado.value} fase={work_item.fase.value}"


def _describir_espejo(espejo: MirroredWorkItem) -> str:
    estado = espejo.estado.value if espejo.estado is not None else "None"
    fase = espejo.fase.value if espejo.fase is not None else "None"
    return f"estado={estado} fase={fase}"


def _camino_de_fase(
    fase_actual: WorkItemPhase, fase_objetivo: WorkItemPhase
) -> tuple[PasoReflejo, ...] | None:
    """El camino MÍNIMO, solo hacia delante, de ``fase_actual`` a ``fase_objetivo``.

    ``None`` si no hay ningún camino hacia delante -incluye el caso en que
    ``fase_actual`` ya dejó atrás ``fase_objetivo``-. Vacío (no ``None``) si
    ya coinciden: idempotencia.

    El único paso que retrocede en el diagrama de fases es
    ``REPARAR -> COMPROBAR`` (``resume_work_item_after_repair``, el cierre
    real del bucle revisar-reparar de arquitectura §3.4): se toma solo cuando
    el objetivo no es ``REPARAR`` -si lo es, el objetivo ya se alcanzó al
    llegar a REVISAR, y pedir reparación es el paso correcto, no un rodeo por
    COMPROBAR-.
    """
    pasos: list[PasoReflejo] = []
    fase = fase_actual
    while fase is not fase_objetivo:
        if fase is WorkItemPhase.PREPARAR:
            pasos.append(PasoReflejo(kind=PASO_EJECUCION_INICIADA))
            fase = WorkItemPhase.EJECUTAR
        elif fase is WorkItemPhase.EJECUTAR:
            pasos.append(PasoReflejo(kind=PASO_COMPROBACION_INICIADA))
            fase = WorkItemPhase.COMPROBAR
        elif fase is WorkItemPhase.COMPROBAR:
            pasos.append(PasoReflejo(kind=PASO_REVISION_INICIADA))
            fase = WorkItemPhase.REVISAR
        elif fase is WorkItemPhase.REVISAR:
            if fase_objetivo is WorkItemPhase.REPARAR:
                pasos.append(PasoReflejo(kind=PASO_REPARACION_SOLICITADA))
                fase = WorkItemPhase.REPARAR
            else:
                pasos.append(PasoReflejo(kind=PASO_REVISION_APROBADA))
                fase = WorkItemPhase.ENTREGAR
        elif fase is WorkItemPhase.REPARAR:
            pasos.append(PasoReflejo(kind=PASO_REPARACION_REANUDADA))
            fase = WorkItemPhase.COMPROBAR
        else:
            # ENTREGAR sin coincidir con el objetivo: no hay arista de avance.
            return None
    return tuple(pasos)


def reflejar_desenlace(
    work_item: WorkItem, espejo: MirroredWorkItem, episodio: DispatchEpisode
) -> ResultadoReflejo:
    """Calcula el plan MÍNIMO que lleva ``work_item`` a lo que ``espejo`` proyecta.

    Pura: no llama al almacén, a GitHub ni al disco. ``episodio`` solo aporta
    ``numero_incidencia`` para el ``resultado`` de una entrega -el motor no
    puede afirmar «entregado» sin decir a qué incidencia corresponde.
    """
    if espejo.etiquetas_contradictorias:
        contradictorias = ", ".join(sorted(espejo.etiquetas))
        return ResultadoReflejo(
            pasos=(),
            divergencia=(
                f"{work_item.work_id}: la incidencia #{episodio.numero_incidencia} lleva "
                f"etiquetas de estado que se contradicen ({contradictorias}); no se toca nada"
            ),
        )
    if espejo.estado is None:
        return ResultadoReflejo(pasos=())

    if espejo.estado is WorkItemState.FAILED_SAFELY:
        if work_item.estado is WorkItemState.FAILED_SAFELY:
            return ResultadoReflejo(pasos=())
        if work_item.estado is not WorkItemState.ACTIVE:
            return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
        diagnostico = espejo.diagnostico_fallo or (
            "la incidencia lleva sirius:failed-safely sin diagnóstico de confianza publicado"
        )
        return ResultadoReflejo(
            pasos=(PasoReflejo(kind=PASO_FALLO_SEGURO, diagnostico=diagnostico),)
        )

    if espejo.estado is WorkItemState.NEEDS_DECISION:
        if work_item.estado is WorkItemState.NEEDS_DECISION:
            return ResultadoReflejo(pasos=())
        if work_item.estado is not WorkItemState.ACTIVE:
            return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
        return ResultadoReflejo(pasos=(PasoReflejo(kind=PASO_ESCALADO),))

    if espejo.estado is WorkItemState.PLANNED:
        if work_item.estado is WorkItemState.PLANNED:
            return ResultadoReflejo(pasos=())
        return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))

    if espejo.estado is WorkItemState.DELIVERED:
        if work_item.estado is WorkItemState.DELIVERED:
            return ResultadoReflejo(pasos=())
        if work_item.estado is not WorkItemState.ACTIVE:
            return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
        camino = _camino_de_fase(work_item.fase, WorkItemPhase.ENTREGAR)
        if camino is None:
            return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
        resultado: dict[str, object] = {"numero_incidencia": episodio.numero_incidencia}
        if espejo.head_sha:
            resultado["merge_sha"] = espejo.head_sha
        return ResultadoReflejo(
            pasos=(*camino, PasoReflejo(kind=PASO_ENTREGADO, resultado=resultado))
        )

    # espejo.estado is ACTIVE: los ocho pares (ACTIVE, fase) del mapa.
    #
    # El propietario puede reanudar una parada con una orden explícita
    # (`sirius_resume_on_command.sh:338-350`): repone la etiqueta activa que
    # la parada había retirado, así que el espejo vuelve a proyectar ACTIVE
    # mientras el motor sigue en FAILED_SAFELY o NEEDS_DECISION. Antes de esta
    # corrección esa combinación se trataba como "hacia atrás" y devolvía
    # divergencia para siempre -el motor nunca llegaba al desenlace final
    # (CODEX-002, PR #530)-. La vuelta usa los puertos autoritativos que ya
    # existen para esto -``reactivate_work_item``
    # (``FAILED_SAFELY -> ACTIVE``) y ``resolve_work_item_decision(...,
    # continuar=True)`` (``NEEDS_DECISION -> ACTIVE``)-, sin inventar
    # vocabulario nuevo. Ninguna de las dos transiciones toca ``fase``
    # (:meth:`WorkItem.fail_safely`/:meth:`WorkItem.escalate` tampoco la
    # tocaron al parar), así que el camino de fase se sigue calculando desde
    # ``work_item.fase`` tal cual, exactamente como si nunca hubiera parado.
    pasos_reanudacion: tuple[PasoReflejo, ...] = ()
    if work_item.estado is WorkItemState.FAILED_SAFELY:
        pasos_reanudacion = (PasoReflejo(kind=PASO_REACTIVADO),)
    elif work_item.estado is WorkItemState.NEEDS_DECISION:
        pasos_reanudacion = (
            PasoReflejo(kind=PASO_DECISION_RESUELTA, resultado={"continuar": True}),
        )
    elif work_item.estado is not WorkItemState.ACTIVE:
        return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
    assert espejo.fase is not None, "ACTIVE siempre trae fase en el mapa etiqueta -> (estado, fase)"
    camino = _camino_de_fase(work_item.fase, espejo.fase)
    if camino is None:
        return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
    return ResultadoReflejo(pasos=(*pasos_reanudacion, *camino))


def _divergencia_atras(work_item: WorkItem, espejo: MirroredWorkItem) -> str:
    return (
        f"{work_item.work_id}: el motor está en {_describir(work_item)} y la incidencia "
        f"proyecta {_describir_espejo(espejo)}; no hay camino hacia delante, no se toca nada"
    )


_APLICAR: dict[str, str] = {
    PASO_EJECUCION_INICIADA: "begin_work_item_execution",
    PASO_COMPROBACION_INICIADA: "begin_work_item_check",
    PASO_REVISION_INICIADA: "begin_work_item_review",
    PASO_REVISION_APROBADA: "approve_work_item_review",
    PASO_REPARACION_SOLICITADA: "request_work_item_repair",
    PASO_REPARACION_REANUDADA: "resume_work_item_after_repair",
    PASO_ESCALADO: "escalate_work_item",
    PASO_REACTIVADO: "reactivate_work_item",
}


def aplicar_pasos(
    store: WorkEngineStore, work_id: str, pasos: Sequence[PasoReflejo], *, now: datetime
) -> tuple[WorkItem, ...]:
    """Aplica ``pasos``, en orden, contra ``store``. Sin GitHub ni disco: lo que el puerto sea.

    Cada paso llama exactamente al puerto de :mod:`sirius_engine.ports.store`
    que le corresponde por nombre -ninguno nuevo-. Si un paso fallara a mitad
    -``store`` levanta una excepción del dominio-, los anteriores ya quedaron
    aplicados y registrados en el diario: recomenzar la reflexión sobre el
    mismo ``work_id`` retoma desde ahí, porque el plan siguiente se calcula
    sobre el ``WorkItem`` ya actualizado.
    """
    aplicados: list[WorkItem] = []
    for paso in pasos:
        if paso.kind == PASO_ENTREGADO:
            assert paso.resultado is not None
            aplicados.append(store.deliver_work_item(work_id, resultado=paso.resultado, now=now))
        elif paso.kind == PASO_FALLO_SEGURO:
            assert paso.diagnostico is not None
            aplicados.append(
                store.fail_work_item_safely(work_id, diagnostico=paso.diagnostico, now=now)
            )
        elif paso.kind == PASO_DECISION_RESUELTA:
            assert paso.resultado is not None
            continuar = bool(paso.resultado["continuar"])
            aplicados.append(
                store.resolve_work_item_decision(work_id, continuar=continuar, now=now)
            )
        else:
            metodo = getattr(store, _APLICAR[paso.kind])
            aplicados.append(metodo(work_id, now=now))
    return tuple(aplicados)
