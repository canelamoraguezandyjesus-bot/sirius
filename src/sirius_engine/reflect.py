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
   no se toca nada; se devuelve el motivo. Única excepción: si el motor está
   en FAILED_SAFELY o NEEDS_DECISION, el espejo deja de proyectar ese MISMO
   estado detenido -sea cual sea el estado al que pase a apuntar (ACTIVE,
   PLANNED o DELIVERED, los tres alcanzables tras una reanudación real)- Y
   el historial de confianza lleva publicado alguno de los tres marcadores
   que ``sirius_resume_on_command.sh:290-350`` escribe ANTES de reponer la
   etiqueta (``sirius-resume-stop``, ``sirius-convergence-reset``,
   ``sirius-restart-sin-pr``; ``espejo.reanudacion_publicada``), entonces no
   es "hacia atrás" -es una reanudación autoritativa ya registrada por el
   propietario (CODEX-002/CODEX-001, PR #530)-, así que primero se
   reactiva/resuelve la decisión con el puerto existente que corresponda y
   el camino de fase se calcula igual que siempre, desde ``work_item.fase``
   sin tocar -salvo para ``sirius:implement-requested`` (el único disparador
   que reanuda hacia PLANNED/PREPARAR sea cual sea la fase real en que se
   paró el rol): si el camino hacia PREPARAR no existe porque el motor ya
   estaba más adelante, se reactiva conservando la fase, sin caminarla
   (CODEX-002, ronda 4, PR #530). Sin el marcador -etiqueta de parada
   sustituida a mano o alterada por una transición parcial, sin que el
   propietario escribiera `continua`- no hay reanudación: se conserva la
   parada y se registra divergencia (CODEX-001, ronda 4, PR #530).
4. **Nunca inventa.** El plan usa exclusivamente los puertos ya existentes
   del almacén, con exactamente los datos que el espejo trae (SHA de fusión,
   diagnóstico de fallo); si algo hiciera falta que el espejo no expone o que
   el almacén no sabe hacer, la función no lo inventa -no hay tal caso hoy
   con el vocabulario del mapa etiqueta -> (estado, fase).
5. **Idempotente por construcción.** Si el ``WorkItem`` ya está exactamente
   en el objetivo, el camino calculado está vacío: una segunda pasada sobre
   el mismo espejo no añade ningún suceso.
6. **Recorrer lo acreditado, cuando la foto sola no basta** (ADR-147,
   incidencia #545). Las cinco reglas de arriba comparan DOS FOTOS: el estado
   guardado y lo que las etiquetas vigentes proyectan. Si entre esas dos
   fotos pasó una recuperación entera sin que ninguna pasada la observara -el
   caso real de WI-20260905-034826 / incidencia #537: parada a las 05:17,
   segunda reanudación a las 05:29, dos vueltas de Quality y revisión, y
   ``completed`` a las 07:00-, no hay salto legal entre las dos fotos y la
   regla 3 declara divergencia, para siempre. Cuando -y solo cuando- eso
   pasa, se intenta el **recorrido acreditado**: si el historial DE CONFIANZA
   de la incidencia (``espejo.historial_estados``, los marcadores
   ``sirius-notification`` que el bot publica al aplicarse cada etiqueta)
   acredita una secuencia de estados que conecta el estado guardado con la
   foto, se recorre entera, tramo a tramo, anotando cada transición
   intermedia como suceso propio del diario. No hay ninguna arista nueva: lo
   que se legaliza es RECORRER saltos ya legales -cada tramo lo calculan
   estas mismas cinco reglas, y el ``WorkItem`` intermedio avanza llamando a
   los métodos del dominio, que son los que dicen qué es legal-.

   Y dentro del recorrido, **la salida de una parada la acredita únicamente un
   PERMISO ESCRITO DEL PROPIETARIO posterior a ESA parada, consumido en
   orden**: la k-ésima salida de parada consume el primer permiso aún no
   consumido que sea posterior a ella en el historial
   (``espejo.permisos_reanudacion``, las dos formas de ADR-147: el marcador de
   reanudación y la orden exacta ``continua``). Ni la foto vigente, ni la
   posición de un aviso de estado, ni ninguna otra heurística acreditan una
   salida de parada -esa es la familia de defecto que tumbó las tres rondas de
   la incidencia #539-.

   Y el ORDEN DE PUBLICACIÓN de los avisos no es el orden de aplicación: el
   notificador no serializa entre etiquetas, así que un aviso retrasado se
   salta -no mueve el recorrido ni lo tumba- y lo que se reconstruye es una
   SUBSECUENCIA legal hasta la foto. Nunca se salta un aviso de parada ni el
   tramo final contra la foto (CODEX-001, ronda 2, PR #546). Cada parada que el
   recorrido recrea lleva SU diagnóstico, el que el historial le atribuye, no
   el de la última parada de toda la incidencia (CODEX-003, misma ronda).

7. **Una incidencia CERRADA no puede producir ningún desenlace más** (ADR-173).
   Las seis reglas de arriba leen ETIQUETAS, y una etiqueta es un estado
   intermedio que se queda congelado el día que alguien cierra la incidencia:
   `sirius:ci-pending` proyecta el mismo `(ACTIVE, COMPROBAR)` en el que el
   encargo ya está, así que la regla 5 devuelve el plan vacío, y así se queda
   para siempre. Medido el 12-09-2026: 21 encargos en `active` en
   `DESENLACES.md`, los 21 con la incidencia cerrada, el más viejo del 25-08.
   El dato que faltaba no había que ir a buscarlo: `espejo.cerrada` ya llegaba
   hasta aquí en cada pasada y no lo leía nadie -ni este módulo ni ningún otro
   de `src/` o `scripts/`-. Así que, DESPUÉS del plan que dictan las etiquetas
   y solo si tras aplicarlo el `WorkItem` sigue en un estado no terminal, el
   cierre lo termina como `CANCELLED` por las transiciones que el dominio ya
   admite (`_CIERRE_POR_ESTADO`). No inventa una entrega: un encargo cuya
   incidencia se cerró sin que las etiquetas proyecten `DELIVERED` acaba
   cancelado, no entregado. Y no pisa ninguna divergencia: si el plan declaró
   contradicción, camino hacia atrás o parada sin permiso, se devuelve tal
   cual y el cierre no entra -lo que esta regla cierra es lo que las etiquetas
   dejaron sin cerrar, no lo que dejaron en disputa-.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from sirius_engine.domain.dispatch import DispatchEpisode
from sirius_engine.domain.errors import EngineError
from sirius_engine.domain.mirror import (
    EstadoAcreditado,
    MirroredWorkItem,
    ParadaPublicada,
    PermisoDeReanudacion,
)
from sirius_engine.domain.work_item import (
    TERMINAL_STATES,
    WorkItem,
    WorkItemPhase,
    WorkItemState,
)
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
PASO_CANCELADO = "work_item_cancelled"

#: Única etiqueta que `sirius_resume_on_command.sh:180-186` repone para volver
#: a PLANNED (`destino_de_rol("implementer")`); `sirius:planned` proyecta el
#: mismo (estado, fase) -es el único par de activación válido,
#: `mirror_projection._PAR_DE_ACTIVACION_VALIDO`- pero ningún guion de
#: reanudación la repone nunca (CODEX-003, ronda 5, PR #530).
_ETIQUETA_REANUDACION_A_PLANNED = "sirius:implement-requested"


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


def _reflejar_por_foto(
    work_item: WorkItem,
    espejo: MirroredWorkItem,
    episodio: DispatchEpisode,
    *,
    reanudacion_acreditada: bool,
) -> ResultadoReflejo:
    """El cálculo de siempre: el plan MÍNIMO hacia UNA foto del espejo.

    Pura: no llama al almacén, a GitHub ni al disco. ``episodio`` solo aporta
    ``numero_incidencia`` para el ``resultado`` de una entrega -el motor no
    puede afirmar «entregado» sin decir a qué incidencia corresponde.

    ``reanudacion_acreditada`` es lo único que este cálculo no decide por sí
    mismo: qué autoriza a salir de una parada. Desde la foto actual es
    ``espejo.reanudacion_publicada`` -el permiso escrito del propietario
    vigente, regla 3-; dentro del recorrido acreditado (regla 6) es el permiso
    concreto que ese tramo consume, y nunca lo autoriza la foto. El parámetro
    existe para que esa diferencia se vea en la firma en vez de esconderse en
    un espejo fabricado con el campo cambiado.
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

    # El propietario puede reanudar una parada con una orden explícita
    # (`sirius_resume_on_command.sh:338-350`): repone la etiqueta activa que
    # la parada había retirado, sin tocar el `WorkItem` del motor -que se
    # queda en FAILED_SAFELY o NEEDS_DECISION-. Se calcula UNA sola vez, antes
    # de mirar a qué apunta el espejo, porque la reanudación puede aterrizar
    # en cualquiera de los estados del mapa -no solo ACTIVE-: el destino
    # depende de a qué fase vuelve cada rol (`destino_de_rol`,
    # `sirius_resume_on_command.sh:180-186`, que para el implementador repone
    # `sirius:implement-requested`, y ese proyecta PLANNED, no ACTIVE -
    # `mirror_projection.py:173-175`) y de cuánto haya avanzado ya el ciclo
    # real para cuando esta reflexión se ejecuta (pudo llegar hasta
    # `sirius:completed` sin que ninguna pasada observara el ACTIVE
    # intermedio). Antes de esta corrección solo la rama ACTIVE reanudaba
    # (CODEX-002, PR #530); las ramas PLANNED y DELIVERED seguían rechazando
    # el `WorkItem` detenido como "hacia atrás" para siempre (CODEX-001,
    # ronda 3, PR #530). La vuelta usa los puertos autoritativos que ya
    # existen para esto -``reactivate_work_item`` (``FAILED_SAFELY ->
    # ACTIVE``) y ``resolve_work_item_decision(..., continuar=True)``
    # (``NEEDS_DECISION -> ACTIVE``)-, sin inventar vocabulario nuevo.
    # Ninguna de las dos transiciones toca ``fase``
    # (:meth:`WorkItem.fail_safely`/:meth:`WorkItem.escalate` tampoco la
    # tocaron al parar), así que el camino de fase se sigue calculando desde
    # ``work_item.fase`` tal cual, exactamente como si nunca hubiera parado.
    #
    # Solo cuenta como reanudación cuando se cumplen DOS condiciones, no una:
    # el espejo deja de proyectar el MISMO estado detenido -si sigue en el
    # mismo, es la idempotencia de esa rama la que decide, no una
    # reanudación- Y el historial de confianza lleva publicado alguno de los
    # tres marcadores que ese guion escribe ANTES de reponer la etiqueta
    # (``espejo.reanudacion_publicada``). La primera condición sola no basta:
    # una etiqueta de parada sustituida a mano, o alterada por una transición
    # parcial sin que el propietario escribiera `continua`, también deja de
    # proyectar el mismo estado detenido, y sin el marcador no hay ninguna
    # orden real que autorice a tratar eso como reanudación (CODEX-001, ronda
    # 4, PR #530) -se conserva la parada y se registra divergencia, igual que
    # si el espejo no hubiera cambiado nada-. Y solo se dispara desde
    # FAILED_SAFELY/NEEDS_DECISION: un `WorkItem` que ya está ACTIVE (nunca se
    # paró) sigue las reglas de siempre en cada rama, sin este paso extra -no
    # convierte ningún retroceso ordinario a PLANNED, ni ningún desenlace
    # terminal observado sin más, en permiso para reactivar-.
    pasos_reanudacion: tuple[PasoReflejo, ...] = ()
    estado_efectivo = work_item.estado
    if (
        work_item.estado is WorkItemState.FAILED_SAFELY
        and espejo.estado is not WorkItemState.FAILED_SAFELY
        and reanudacion_acreditada
    ):
        pasos_reanudacion = (PasoReflejo(kind=PASO_REACTIVADO),)
        estado_efectivo = WorkItemState.ACTIVE
    elif (
        work_item.estado is WorkItemState.NEEDS_DECISION
        and espejo.estado is not WorkItemState.NEEDS_DECISION
        and reanudacion_acreditada
    ):
        pasos_reanudacion = (
            PasoReflejo(kind=PASO_DECISION_RESUELTA, resultado={"continuar": True}),
        )
        estado_efectivo = WorkItemState.ACTIVE

    if espejo.estado is WorkItemState.FAILED_SAFELY:
        if work_item.estado is WorkItemState.FAILED_SAFELY:
            return ResultadoReflejo(pasos=())
        if estado_efectivo is not WorkItemState.ACTIVE:
            return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
        diagnostico = espejo.diagnostico_fallo or (
            "la incidencia lleva sirius:failed-safely sin diagnóstico de confianza publicado"
        )
        return ResultadoReflejo(
            pasos=(*pasos_reanudacion, PasoReflejo(kind=PASO_FALLO_SEGURO, diagnostico=diagnostico))
        )

    if espejo.estado is WorkItemState.NEEDS_DECISION:
        if work_item.estado is WorkItemState.NEEDS_DECISION:
            return ResultadoReflejo(pasos=())
        if estado_efectivo is not WorkItemState.ACTIVE:
            return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
        return ResultadoReflejo(pasos=(*pasos_reanudacion, PasoReflejo(kind=PASO_ESCALADO)))

    if espejo.estado is WorkItemState.PLANNED:
        if work_item.estado is WorkItemState.PLANNED:
            return ResultadoReflejo(pasos=())
        # `sirius:planned` proyecta el MISMO (estado, fase) que
        # `sirius:implement-requested` -es el único par de activación válido
        # del mapa etiqueta -> (estado, fase)-, pero solo la segunda es un
        # disparador de reanudación real: `destino_de_rol` nunca repone
        # `sirius:planned`. Sin ella en el espejo, un marcador de reanudación
        # vigente no autoriza reactivar hacia PLANNED -sería tratar una
        # transición parcial o una edición manual posterior al permiso como si
        # fuera la orden que repuso el disparador real (CODEX-003, ronda 5, PR
        # #530)-: se conserva la parada y se registra divergencia, igual que
        # si no hubiera marcador.
        if not pasos_reanudacion or _ETIQUETA_REANUDACION_A_PLANNED not in espejo.etiquetas:
            return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
        assert espejo.fase is not None, (
            "PLANNED siempre trae fase en el mapa etiqueta -> (estado, fase)"
        )
        camino = _camino_de_fase(work_item.fase, espejo.fase)
        if camino is None:
            # `sirius:implement-requested` -el único disparador que reanuda
            # hacia PLANNED- siempre proyecta PREPARAR sea cual sea la fase
            # real en la que se paró el rol (`destino_de_rol` en
            # `sirius_resume_on_command.sh` no lee ni repone fase, solo
            # rol -> etiqueta): es el disparador de reanudación, no una orden
            # de retroceder de fase. Si el motor ya estaba más adelante que
            # PREPARAR cuando se paró, ``reactivate_work_item`` no toca
            # ``fase`` y el resultado correcto es conservarla tal cual -no
            # caminar hacia atrás ni descartar la reactivación ya calculada
            # (CODEX-002, ronda 4, PR #530).
            return ResultadoReflejo(pasos=pasos_reanudacion)
        return ResultadoReflejo(pasos=(*pasos_reanudacion, *camino))

    if espejo.estado is WorkItemState.DELIVERED:
        if work_item.estado is WorkItemState.DELIVERED:
            return ResultadoReflejo(pasos=())
        if estado_efectivo is not WorkItemState.ACTIVE:
            return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
        camino = _camino_de_fase(work_item.fase, WorkItemPhase.ENTREGAR)
        if camino is None:
            return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
        resultado: dict[str, object] = {"numero_incidencia": episodio.numero_incidencia}
        if espejo.head_sha:
            resultado["merge_sha"] = espejo.head_sha
        paso_entregado = PasoReflejo(kind=PASO_ENTREGADO, resultado=resultado)
        return ResultadoReflejo(pasos=(*pasos_reanudacion, *camino, paso_entregado))

    # espejo.estado is ACTIVE: los ocho pares (ACTIVE, fase) del mapa.
    if estado_efectivo is not WorkItemState.ACTIVE:
        return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
    assert espejo.fase is not None, "ACTIVE siempre trae fase en el mapa etiqueta -> (estado, fase)"
    camino = _camino_de_fase(work_item.fase, espejo.fase)
    if camino is None:
        return ResultadoReflejo(pasos=(), divergencia=_divergencia_atras(work_item, espejo))
    return ResultadoReflejo(pasos=(*pasos_reanudacion, *camino))


#: Los dos estados detenidos del dominio. Salir de cualquiera de ellos dentro
#: del recorrido exige un permiso escrito del propietario; ningún otro estado
#: exige nada más que el camino de fase.
_PARADAS: frozenset[WorkItemState] = frozenset(
    {WorkItemState.FAILED_SAFELY, WorkItemState.NEEDS_DECISION}
)


def reflejar_desenlace(
    work_item: WorkItem, espejo: MirroredWorkItem, episodio: DispatchEpisode
) -> ResultadoReflejo:
    """El plan que lleva ``work_item`` hasta donde la incidencia está HOY.

    Dos cálculos, en este orden y nunca al revés (regla 6):

    1. El de siempre, contra la foto actual del espejo
       (:func:`_reflejar_por_foto`). Si encuentra camino -o si no hay nada que
       decir- eso es la respuesta: el recorrido no puede alargar ni cambiar un
       plan mínimo que ya existe.
    2. Solo si ese cálculo declaró divergencia, el **recorrido acreditado**:
       si el historial de confianza acredita una secuencia de saltos ya
       legales que conecta el estado guardado con la foto, y cada salida de
       parada del camino tiene su propio permiso escrito, se recorre entera.
       Si no, se devuelve la divergencia del punto 1 tal cual -mismo texto,
       mismo fail-open, cero pasos.

    Sigue siendo pura: no llama al almacén, a GitHub ni al disco.
    """
    por_foto = _reflejar_por_foto(
        work_item, espejo, episodio, reanudacion_acreditada=espejo.reanudacion_publicada
    )
    if por_foto.divergencia is None:
        return _con_el_cierre(work_item, espejo, episodio, por_foto)
    recorrido = _recorrer_historial_acreditado(work_item, espejo, episodio)
    if recorrido is not None:
        return _con_el_cierre(work_item, espejo, episodio, recorrido)
    return por_foto


#: Cómo termina un ``WorkItem`` no terminal cuando su incidencia se cierra, por
#: el estado en que lo deja el plan de las etiquetas. Ni una transición nueva:
#: son las que el dominio ya admite (``domain/work_item.py:122-141``), y cada
#: una llama al puerto del almacén que ya existía para ella. ``CANCELLED``
#: desde ``NEEDS_DECISION`` va por ``resolve_decision(continuar=False)`` y no
#: por ``cancel`` porque §3.2 lo modela como parte de la decisión registrada,
#: no como un «cancelar» a secas -y el dominio lo hace cumplir-.
_CIERRE_POR_ESTADO: Mapping[WorkItemState, tuple[PasoReflejo, ...]] = {
    WorkItemState.ACTIVE: (
        PasoReflejo(kind=PASO_ESCALADO),
        PasoReflejo(kind=PASO_DECISION_RESUELTA, resultado={"continuar": False}),
    ),
    WorkItemState.NEEDS_DECISION: (
        PasoReflejo(kind=PASO_DECISION_RESUELTA, resultado={"continuar": False}),
    ),
    WorkItemState.FAILED_SAFELY: (PasoReflejo(kind=PASO_CANCELADO),),
    WorkItemState.PLANNED: (PasoReflejo(kind=PASO_CANCELADO),),
}


def _con_el_cierre(
    work_item: WorkItem,
    espejo: MirroredWorkItem,
    episodio: DispatchEpisode,
    plan: ResultadoReflejo,
) -> ResultadoReflejo:
    """Regla 7: una incidencia CERRADA no puede producir ningún desenlace más.

    El cierre no compite con las etiquetas: llega DESPUÉS. Primero se aplica
    el plan que las etiquetas dictan -si dicen ``sirius:completed``, el
    encargo se entrega y aquí no queda nada que hacer-, y solo si tras ese
    plan el ``WorkItem`` sigue en un estado NO terminal entra esta regla, que
    lo termina como ``CANCELLED``.

    **No inventa una entrega.** Un encargo cuya incidencia se cerró sin que
    las etiquetas proyecten ``DELIVERED`` acaba en ``CANCELLED``, aunque su PR
    se hubiera fusionado a mano sin que el ciclo aplicara ``sirius:completed``:
    el motor no puede afirmar una fusión que no observó, y el enlace a la
    incidencia queda en el diario para que un humano lo mire.

    **No pisa ninguna divergencia**: si el plan de las etiquetas declaró una
    -contradicción, camino hacia atrás, parada sin permiso-, se devuelve tal
    cual y el cierre no entra. Lo que esta regla cierra es lo que las
    etiquetas dejaron sin cerrar, no lo que dejaron en disputa.
    """
    if not espejo.cerrada:
        return plan
    tras_el_plan = _avanzar(work_item, plan.pasos)
    if tras_el_plan is None or tras_el_plan.estado in TERMINAL_STATES:
        return plan
    cierre = _CIERRE_POR_ESTADO.get(tras_el_plan.estado)
    if cierre is None:
        # Criterio de parada (b) de ADR-173: antes que inventar una
        # transición, se dice qué falta y no se toca nada.
        return ResultadoReflejo(
            pasos=(),
            divergencia=(
                f"{work_item.work_id}: la incidencia #{episodio.numero_incidencia} está "
                f"cerrada y el motor queda en {tras_el_plan.estado.value}, del que el "
                "vocabulario del almacén no sabe salir hacia un estado terminal; "
                "no se toca nada"
            ),
        )
    return ResultadoReflejo(pasos=(*plan.pasos, *cierre))


def _coincide_con_el_estado_guardado(acreditado: EstadoAcreditado, work_item: WorkItem) -> bool:
    """Si este marcador acredita el mismo ``(estado, fase)`` en que está el motor.

    Un marcador de parada no trae fase (``sirius:failed-safely`` y
    ``sirius:blocked-decision`` proyectan ``fase=None``), así que en esos la
    coincidencia es solo de estado; en los demás tienen que coincidir los dos
    ejes.
    """
    if acreditado.estado is not work_item.estado:
        return False
    return acreditado.fase is None or acreditado.fase is work_item.fase


def _el_almacen_pudo_guardarla(acreditado: EstadoAcreditado, work_item: WorkItem) -> bool:
    """Si esta ocurrencia se publicó a tiempo de ser la que el almacén guardó.

    El almacén no pudo guardar un marcador publicado DESPUÉS de su última
    escritura (``work_item.updated_at``). Una ocurrencia sin instante viene del
    CUERPO de la incidencia, anterior por construcción a todo comentario, y por
    eso nunca se descarta.

    Es una función y no una condición dentro de la comprensión porque el
    instante es opcional y hay que estrecharlo antes de compararlo: en la
    comprensión el estrechamiento no llegaba a la comparación -``mypy``:
    ``Unsupported operand types for >= ("datetime" and "None")``- y el árbol
    quedaba con un error de tipos que, en el árbol de entonces (el head
    ``923202f``, anterior a la actualización de esta rama con ``main``),
    ``scripts/check.ps1`` NO propagaba a su código de salida. Hoy sí lo
    propaga: ADR-153 le añadió ``if ($LASTEXITCODE -ne 0) { exit
    $LASTEXITCODE }`` tras cada comando nativo, así que un error de tipos ya
    deja el guion en rojo. El motivo de que el estrechamiento viva en una
    función con nombre no cambia por eso: es ``mypy``, no el guion.
    """
    publicado_en = acreditado.publicado_en
    return publicado_en is None or publicado_en <= work_item.updated_at


def _ancla_del_recorrido(
    work_item: WorkItem,
    historial: Sequence[EstadoAcreditado],
    paradas: Sequence[ParadaPublicada] = (),
) -> int | None:
    """La OCURRENCIA del historial acreditado que el almacén guardó.

    ``None`` -y entonces no hay recorrido- cuando el historial no menciona el
    estado guardado: recorrerlo sería empezar por un punto que nadie acreditó.

    Cuando el mismo ``(estado, fase)`` aparece varias veces -lo normal en un
    ciclo con dos vueltas de reparación- la posición no dice cuál de ellas es.
    Quedarse siempre con la última no lo demuestra: si el motor se quedó en la
    PRIMERA parada, el recorrido se saltaría entero el tramo intermedio -la
    primera recuperación y la segunda parada- y el diario registraría un salto
    en vez de las transiciones reales (CODEX-002, ronda 2, PR #546). Así que se
    correlaciona con la evidencia que hay, y en este orden:

    1. **Tiempo.** El almacén no pudo guardar una ocurrencia publicada DESPUÉS
       de su última escritura (``work_item.updated_at``): esas quedan
       descartadas. Una ocurrencia sin instante viene del cuerpo de la
       incidencia, anterior por construcción a todo comentario, y no se
       descarta. Si el descarte se las lleva TODAS, el almacén es más antiguo
       que el historial entero y no informa de nada: el recorrido empieza en la
       primera.
    2. **Compatibilidad del diagnóstico.** Si el almacén guarda un diagnóstico
       de parada, una ocurrencia que lleva OTRO diagnóstico distinto no puede
       ser la que el almacén guardó: lo dice su propio texto. Esas quedan
       descartadas, y si el descarte se las lleva todas no hay ancla -el
       recorrido se abandona en vez de anclar en una parada que el diagnóstico
       guardado contradice-. Una ocurrencia SIN diagnóstico no contradice
       nada y se conserva: el respaldo sigue existiendo cuando no hay
       diagnóstico que discrimine (CODEX-002, ronda 3, PR #546; en los
       historiales anteriores a ADR-157 el notificador deduplicaba por estado
       y head, así que una segunda parada sobre el mismo head podía no dejar
       marcador propio).
    3. **Identidad del suceso.** Si exactamente una de las ocurrencias que
       quedan lleva ESE diagnóstico, esa es: no es una preferencia, es el
       mismo texto escrito dos veces.
    4. Y solo si ninguna de las tres discrimina, la más reciente de las que la
       evidencia no descartó, **salvo que quede una parada sin acreditar
       detrás**: si el motor está PARADO y el historial de confianza trae un
       veredicto de parada publicado DESPUÉS de la cota de esa ocurrencia y no
       posterior a ``work_item.updated_at`` -es decir, una parada que el
       almacén pudo guardar y que ningún aviso acredita, porque en los
       historiales anteriores a ADR-157 ``sirius_comment_once`` deduplicaba el
       marcador por ``(etiqueta, head)``-,
       la evidencia no dice en cuál de las dos se quedó el motor y el recorrido
       se abandona (``None``). Anclar en la anterior fijaría una cota que deja
       pasar el permiso escrito para la parada ANTERIOR y acreditaría una
       salida que nadie autorizó (CLAUDE-R7-001 y CLAUDE-R7-002, ronda 7, PR
       #546). La ocurrencia identificada por su DIAGNÓSTICO (punto 3) no
       necesita esta abstención: ahí el suceso está identificado por su propio
       texto, no por la posición.
    """
    candidatos = [
        indice
        for indice, acreditado in enumerate(historial)
        if _coincide_con_el_estado_guardado(acreditado, work_item)
    ]
    if not candidatos:
        return None
    anteriores = [
        indice for indice in candidatos if _el_almacen_pudo_guardarla(historial[indice], work_item)
    ]
    base = anteriores or candidatos
    if work_item.diagnostico is not None:
        base = [
            indice
            for indice in base
            if historial[indice].diagnostico in (None, work_item.diagnostico)
        ]
        if not base:
            return None
        por_identidad = [
            indice for indice in base if historial[indice].diagnostico == work_item.diagnostico
        ]
        if len(por_identidad) == 1:
            return por_identidad[0]
    eleccion = base[-1] if anteriores else base[0]
    if work_item.estado in _PARADAS and _hay_una_parada_posterior_sin_aviso(
        historial[eleccion], paradas, work_item
    ):
        return None
    return eleccion


def _hay_una_parada_posterior_sin_aviso(
    acreditado: EstadoAcreditado, paradas: Sequence[ParadaPublicada], work_item: WorkItem
) -> bool:
    """Si detrás de esta ocurrencia hay otra parada que el almacén pudo guardar.

    Lo que mira es el VEREDICTO, no el aviso: la lista de
    :class:`ParadaPublicada` son los veredictos de parada -que publica siempre
    quien para- y esta función no consulta ``historial_estados`` en ningún
    momento. Así que se abstiene ante CUALQUIER veredicto de parada posterior
    a la cota de esta ocurrencia y publicado a tiempo de que el almacén lo
    guardara, haya dejado esa parada su propio aviso o no. El nombre viene del
    caso que la motivó, no del alcance que tiene.

    El caso que la motivó son los historiales publicados ANTES de ADR-157
    (07-09-2026), en los que ``sirius_comment_once`` deduplicaba el marcador
    por ``(etiqueta, head)`` y la segunda parada sobre el mismo head no dejaba
    aviso propio: mientras ese veredicto exista, la posición no dice en cuál de
    las dos se quedó el motor. Desde ADR-157 el marcador lleva el run del
    evento y cada parada cuyo evento llega a ejecutarse deja el suyo (con el
    hueco que la cola del notificador puede seguir dejando: CODEX-001, ronda
    14, PR #546), pero esta función NO lo aprovecha:
    sobre un historial posterior sigue abandonando el recorrido en cuanto hay
    un veredicto de parada detrás de la cota **y publicado a tiempo de que el
    almacén lo guardara**, aunque su aviso esté escrito y aunque cada parada
    traiga su ``continua``. El efecto observable está en un ancla que no
    discrimina por identidad -un ``sirius:blocked-decision``, que llega sin
    diagnóstico porque ``escalate`` no escribe ninguno-: una recuperación
    autorizada por escrito se declara como divergencia
    (``test_la_abstencion_tambien_alcanza_a_la_parada_posterior_con_aviso_propio``,
    CLAUDE-R9-001, ronda 9, PR #546). Es una limitación viva, y conservadora:
    no acredita ninguna salida que nadie autorizase, solo deja de acreditar
    una que sí lo estaba.

    Y su ALCANCE es solo ese: el veredicto que el almacén PUDO guardar
    (``publicado_en <= work_item.updated_at``), que es el caso en que la
    evidencia no dice en cuál de las dos paradas se quedó el motor. El
    veredicto POSTERIOR a la última escritura del almacén -el caso normal, el
    del tramo que el recorrido reproduce- no abstiene nada: ahí el recorrido
    recrea la parada y le exige su permiso escrito, como fija
    ``test_una_parada_posterior_a_la_ultima_escritura_no_abstiene_el_ancla``
    (CLAUDE-R12-001, ronda 12, PR #546). Quien cubre ese tramo es
    :func:`_paradas_que_el_recorrido_debe_recrear`, que no filtra por tiempo.

    La referencia es la COTA (:func:`_orden_de_la_parada`), no la posición del
    aviso: el veredicto que causó esta misma parada nunca cuenta como parada
    posterior, esté su aviso donde esté.
    """
    cota = _orden_de_la_parada(acreditado)
    return any(
        parada.orden > cota
        and (parada.publicado_en is None or parada.publicado_en <= work_item.updated_at)
        for parada in paradas
    )


def _paradas_que_el_recorrido_debe_recrear(
    ancla: EstadoAcreditado, paradas: Sequence[ParadaPublicada]
) -> list[ParadaPublicada]:
    """Los veredictos de parada que el recorrido tiene que atravesar recreándolos.

    Hermana de :func:`_hay_una_parada_posterior_sin_aviso`, para el caso que
    aquella no cubre: allí se pregunta por el ANCLA -y solo cuando el motor
    está parado, que es cuando la posición del ancla no identifica el suceso-;
    aquí se pregunta por el RECORRIDO entero, con el motor donde esté.

    El bucle de tramos solo exige permiso cuando el ``WorkItem`` simulado ENTRA
    en una parada, y solo entra si esa parada dejó su aviso en
    ``historial_estados``. Un veredicto de parada publicado SIN aviso propio
    -en los historiales anteriores a ADR-157 ``sirius_comment_once``
    deduplicaba el marcador por ``(etiqueta, head)``, y también falta si el
    workflow del notificador falló- se atravesaba sin recrear la parada y sin
    consumir ningún permiso, aunque el motor estuviera anclado ANTES de ella
    (CLAUDE-R10-001, ronda 10, PR #546).

    Lo que se devuelve es la lista de veredictos posteriores a la cota del
    ancla (:func:`_orden_de_la_parada`), y esa cota es la ÚNICA que delimita el
    tramo: el historial de confianza termina en la foto, así que todo veredicto
    por detrás del ancla cae dentro de lo que el recorrido reproduce. El bucle
    va saldando uno por cada parada que recrea, en orden; si al terminar queda
    alguno sin saldar, el recorrido se abandona. La abstención es la salida
    correcta y suficiente: no se inventa ningún tramo de parada ni se relaja
    :func:`_consumir_permiso`, y un veredicto que SÍ tiene su tramo se sigue
    comportando exactamente igual que antes -consumiendo su permiso-.

    Lo que NO se filtra aquí, y la ronda 10 filtraba, es el instante de
    publicación contra ``work_item.updated_at``. Ese predicado es el de
    :func:`_el_almacen_pudo_guardarla` y responde a la pregunta del ANCLA
    -«¿en cuál de las ocurrencias se quedó el almacén?»-, donde es correcto.
    Aquí la pregunta es otra -«¿qué veredictos caen en el tramo que el
    recorrido reproduce?»- y el tramo es, por definición, lo POSTERIOR a la
    última escritura del almacén: todo veredicto suyo tiene
    ``publicado_en > updated_at`` y el filtro dejaba la lista siempre vacía,
    devolviendo intacto el fallo de CLAUDE-R10-001. Un veredicto publicado
    después de la última escritura del almacén es precisamente el que el
    almacén NO vio y el que el recorrido tiene que recrear (CLAUDE-R11-001,
    ronda 11, PR #546;
    ``test_una_parada_fechada_que_ningun_tramo_recrea_abandona_el_recorrido``).
    """
    cota = _orden_de_la_parada(ancla)
    return [parada for parada in paradas if parada.orden > cota]


def _orden_de_la_parada(acreditado: EstadoAcreditado) -> int:
    """La posición de la PARADA REAL, no la del aviso que la anunció.

    El permiso que acredita salir de una parada tiene que ser posterior a la
    parada, y hasta la ronda 5 «la parada» era la posición de su marcador
    ``sirius-notification``. Pero ese marcador lo publica
    ``notify-sirius-state.yml``, cuyo grupo de concurrencia lleva el nombre de
    la etiqueta: los avisos de etiquetas DISTINTAS no se serializan entre sí,
    así que el aviso de una parada puede publicarse DESPUÉS del ``continua``
    que la levantó. Con la secuencia ``[veredicto de parada, continua, aviso de
    la parada]`` no quedaba ningún permiso posterior al aviso y el recorrido
    entero se abandonaba: una recuperación autorizada por escrito quedaba como
    divergencia declarada para siempre (CLAUDE-R4-001, ronda 4, PR #546).

    Lo que sí identifica el suceso es el comentario del VEREDICTO que causó la
    parada (``orden_del_veredicto``): es síncrono, lo publica el propio rol, y
    ``sirius_apply_verdict.sh`` lo escribe SIEMPRE antes de aplicar la etiqueta.
    Cuando la proyección pudo atribuirlo, es él quien fija la posición de la
    parada; si no hay ninguno atribuible, se vuelve a la del aviso, que es lo
    único que hay.

    Lo que NO cambia: el permiso sigue teniendo que ser ESTRICTAMENTE
    posterior a la parada, y un permiso anterior no la levanta
    (``test_un_permiso_anterior_a_la_parada_no_la_levanta``). Esto no relaja el
    criterio de ADR-147: mueve la referencia del aviso al suceso.

    La cota nunca se adelanta a la parada REAL. La proyección se ABSTIENE de
    atribuir cuando hay más de un veredicto de parada pendiente publicado antes
    del marcador y no quedan marcadores detrás que absorban al otro
    (``_atribuir_diagnosticos``, CLAUDE-R6-002): en esa situación devolvemos la
    posición del aviso, que es posterior a todos ellos y por tanto segura. Sin
    esa abstención, el marcador de una serie NUEVA heredaba el veredicto de una
    parada anterior y su cota acreditaba la salida con un permiso escrito ANTES
    de la parada real (CLAUDE-R6-001, ronda 6, PR #546).

    **Alcance: solo ``failed-safely``.** ``orden_del_veredicto`` únicamente lo
    rellena ``_atribuir_diagnosticos`` para los acreditados ``FAILED_SAFELY``,
    porque la identidad del suceso que se transporta es su DIAGNÓSTICO y
    ``sirius:blocked-decision`` no publica ninguno. Un marcador
    ``blocked-decision`` llega siempre con ``orden_del_veredicto is None`` y se
    correlaciona por la posición de su AVISO, así que una recuperación
    autorizada por escrito tras un ``blocked-decision`` con aviso retrasado se
    sigue declarando como divergencia (CLAUDE-R6-003, ronda 6, PR #546).

    Eso NO lo hacía conservador por sí solo, y la ronda 6 lo escribió mal aquí:
    con dos ``blocked-decision`` sobre el mismo head, la cota del aviso de la
    PRIMERA dejaba pasar su propio ``continua`` para resolver la SEGUNDA, cuyo
    aviso deduplicó ``sirius_comment_once`` -así ocurrió en los historiales
    publicados antes de ADR-157 (07-09-2026), que desde entonces da su propio
    aviso a cada parada cuyo evento de etiqueta llega a ejecutarse-. Quien
    cierra ese flanco, para aquellos historiales, es
    :func:`_hay_una_parada_posterior_sin_aviso`, abandonando el recorrido
    (CLAUDE-R7-001 y CLAUDE-R7-002, ronda 7, PR #546; ADR-147).
    """
    if acreditado.orden_del_veredicto is None:
        return acreditado.orden
    return acreditado.orden_del_veredicto


def _consumir_permiso(
    permisos: Sequence[PermisoDeReanudacion], desde: int, posterior_a: int
) -> int | None:
    """El permiso que acredita UNA salida de parada, consumido en orden.

    Devuelve la posición desde la que seguirá buscando la salida SIGUIENTE
    -es decir, el permiso consumido queda detrás- o ``None`` si no queda
    ninguno posterior a ``posterior_a``, y entonces esa salida no está
    acreditada y el recorrido entero se abandona.

    Esta función **no recibe la foto ni el tramo**. No es que no los mire: es
    que no los tiene. La familia de defecto que tumbó las tres rondas de la
    incidencia #539 -acreditar una salida de parada con la etiqueta vigente,
    por una puerta o por otra- deja así de ser expresable (ADR-147, pregunta 4
    de la nota de arranque).

    Que el puntero solo avance es la otra mitad: un permiso no puede acreditar
    dos salidas, porque una vez consumido ya no está en la lista para nadie.
    Y un permiso es UNA autorización, no cada rastro que deja: desde la ronda 6
    la proyección colapsa el recibo de `sirius_resume_on_command.sh` con la
    orden `continua` que lo provocó (CLAUDE-R5-003, decisión del propietario
    del 07-09-2026 en ADR-147), así que esta frase es verdad también para el
    propietario que escribió una sola palabra.
    Un permiso ANTERIOR a la parada tampoco vale, y al saltárselo queda
    descartado para siempre -las paradas siguientes son todavía más tardías-.
    """
    for indice in range(desde, len(permisos)):
        if permisos[indice].orden > posterior_a:
            return indice + 1
    return None


def _recorrer_historial_acreditado(
    work_item: WorkItem, espejo: MirroredWorkItem, episodio: DispatchEpisode
) -> ResultadoReflejo | None:
    """El plan que recorre, tramo a tramo, lo que el historial de confianza acredita.

    ``None`` cuando no hay recorrido posible -y entonces el llamador conserva
    la divergencia de siempre-. Es TODO O NADA: o el recorrido llega hasta la
    foto, o no se devuelve nada; nunca el trozo bueno. Aplicar media
    recuperación dejaría el diario en un punto que nadie acreditó.

    Cada tramo se calcula con la MISMA :func:`_reflejar_por_foto` que la foto
    actual, sobre un espejo derivado del real al que se le cambian
    ``estado``/``fase``/``etiquetas`` por los del estado acreditado y el
    diagnóstico de fallo por el de ESA parada: el resto -el SHA de fusión-
    sigue siendo el del espejo real, porque es el único que hay. El último
    tramo va contra el espejo REAL, no contra un derivado: es el que trae el
    SHA de fusión de la entrega, el diagnóstico de la foto vigente y el que
    garantiza que el recorrido termina exactamente en la foto, no cerca.

    Un aviso que no encaje donde está publicado **no tumba el recorrido: no lo
    mueve**. Solo SEIS de las trece etiquetas se notifican y el notificador no
    serializa entre etiquetas -su grupo de concurrencia lleva el nombre de la
    etiqueta (`notify-sirius-state.yml`)-, así que el orden de publicación de
    los avisos no acredita el orden real de aplicación (ADR-147, nota de
    arranque, pregunta 2). Tratar ese orden como autoritativo hacía que un solo
    aviso retrasado envenenara el recorrido para siempre (CODEX-001, ronda 2,
    PR #546). Lo que se reconstruye es una SUBSECUENCIA legal hasta la foto.

    Con dos excepciones que no se saltan nunca, porque saltarlas sí cambiaría
    lo que el recorrido afirma: un aviso de PARADA -saltárselo sería pasar por
    encima de una parada real sin exigir su permiso- y el tramo final contra la
    foto -el recorrido tiene que TERMINAR en ella-. Y una salida de parada sin
    permiso no es un aviso a destiempo: abandona el recorrido entero, como
    siempre.

    Entre tramo y tramo el ``WorkItem`` avanza llamando a los métodos REALES
    del dominio (:func:`_avanzar`), no a una tabla paralela de estados: si un
    tramo no fuera una transición legal, es la máquina de estados de
    :mod:`sirius_engine.domain.work_item` la que lo dice, y el recorrido se
    abandona. Este módulo no añade ninguna arista.

    Y cada vez que un tramo tiene que SALIR de una parada, se le exige su
    propio permiso escrito del propietario, posterior a esa parada concreta y
    aún no consumido (:func:`_consumir_permiso`). ``orden_de_la_parada`` es la
    posición, en el historial de confianza, del marcador que dejó al motor
    parado: la del ancla mientras el motor sigue en la parada con la que
    empezó, y la del propio tramo cuando el recorrido entra en una parada
    nueva.
    """
    if espejo.etiquetas_contradictorias or espejo.estado is None:
        # Una incidencia con etiquetas de estado contradictorias se sigue
        # tratando como hoy -declarar y no tocar nada-, y sin foto no hay
        # destino al que recorrer.
        return None
    ancla = _ancla_del_recorrido(work_item, espejo.historial_estados, espejo.paradas_publicadas)
    if ancla is None:
        return None
    objetivos = espejo.historial_estados[ancla + 1 :]
    if not objetivos:
        return None

    pasos: list[PasoReflejo] = []
    simulado = work_item
    permiso_siguiente = 0
    orden_de_la_parada = _orden_de_la_parada(espejo.historial_estados[ancla])
    paradas_por_recrear = _paradas_que_el_recorrido_debe_recrear(
        espejo.historial_estados[ancla], espejo.paradas_publicadas
    )
    #: Los tramos: cada estado acreditado que queda por recorrer y, al final,
    #: el espejo REAL. El último no lleva estado acreditado porque la foto no
    #: está en el historial -y no hace falta: después de él no queda ninguna
    #: parada de la que salir.
    tramos: list[tuple[MirroredWorkItem, EstadoAcreditado | None]] = [
        (
            replace(
                espejo,
                estado=acreditado.estado,
                fase=acreditado.fase,
                etiquetas=(acreditado.etiqueta,),
                diagnostico_fallo=acreditado.diagnostico,
            ),
            acreditado,
        )
        for acreditado in objetivos
    ]
    tramos.append((espejo, None))

    for espejo_del_tramo, acreditado in tramos:
        acreditada = False
        permiso_tras_el_tramo = permiso_siguiente
        if simulado.estado in _PARADAS and espejo_del_tramo.estado is not simulado.estado:
            siguiente = _consumir_permiso(
                espejo.permisos_reanudacion, permiso_siguiente, orden_de_la_parada
            )
            if siguiente is None:
                return None
            permiso_tras_el_tramo = siguiente
            acreditada = True
        tramo = _reflejar_por_foto(
            simulado, espejo_del_tramo, episodio, reanudacion_acreditada=acreditada
        )
        avanzado = None if tramo.divergencia is not None else _avanzar(simulado, tramo.pasos)
        if avanzado is None:
            if acreditado is None or espejo_del_tramo.estado in _PARADAS:
                return None
            # Un aviso que no encaja aquí es un aviso publicado fuera del orden
            # en que se aplicó: no mueve el recorrido y tampoco lo tumba. El
            # permiso que este tramo hubiera consumido sigue sin consumir.
            continue
        permiso_siguiente = permiso_tras_el_tramo
        # Un tramo que ENTRA en una parada la RECREA: el veredicto más antiguo
        # de los que el recorrido debía recrear queda saldado. Se consumen en
        # orden, como los permisos, porque la posición del aviso no identifica
        # el suceso.
        if (
            paradas_por_recrear
            and avanzado.estado in _PARADAS
            and avanzado.estado is not simulado.estado
        ):
            paradas_por_recrear.pop(0)
        simulado = avanzado
        if simulado.estado in _PARADAS and acreditado is not None:
            orden_de_la_parada = _orden_de_la_parada(acreditado)
        pasos.extend(tramo.pasos)

    if paradas_por_recrear:
        # Queda un veredicto de parada que el almacén pudo guardar y que
        # ningún tramo recreó: el recorrido habría pasado por encima de él sin
        # exigir su permiso (CLAUDE-R10-001, ronda 10, PR #546).
        return None
    if not pasos:
        return None
    return ResultadoReflejo(pasos=tuple(pasos))


#: Nombre del paso -> método del DOMINIO que lo ejecuta. Hermana de
#: :data:`_APLICAR` (que apunta a los puertos del almacén) y deliberadamente
#: separada: esta se usa para SIMULAR el recorrido antes de tocar nada, y la
#: otra para aplicarlo. Que las dos existan es lo que permite comprobar la
#: legalidad de un tramo sin escribir un solo suceso.
_AVANZAR_DOMINIO: dict[str, str] = {
    PASO_EJECUCION_INICIADA: "begin_execution",
    PASO_COMPROBACION_INICIADA: "begin_check",
    PASO_REVISION_INICIADA: "begin_review",
    PASO_REVISION_APROBADA: "approve_review",
    PASO_REPARACION_SOLICITADA: "request_repair",
    PASO_REPARACION_REANUDADA: "resume_after_repair",
    PASO_ESCALADO: "escalate",
    PASO_REACTIVADO: "reactivate",
    PASO_CANCELADO: "cancel",
}


def _avanzar(work_item: WorkItem, pasos: Sequence[PasoReflejo]) -> WorkItem | None:
    """Avanza una COPIA del ``WorkItem`` por ``pasos``, o ``None`` si alguno es ilegal.

    No toca el almacén: son los métodos del dominio, que devuelven instancias
    nuevas (``WorkItem`` es inmutable). El ``now`` que reciben es el
    ``updated_at`` que el propio ``WorkItem`` ya trae, porque de esta
    simulación solo se leen ``estado`` y ``fase``: la marca de tiempo real la
    pone :func:`aplicar_pasos` cuando se aplica de verdad, y usar aquí un
    ``datetime.now()`` rompería la pureza de :func:`reflejar_desenlace`.
    """
    simulado = work_item
    for paso in pasos:
        try:
            if paso.kind == PASO_ENTREGADO:
                assert paso.resultado is not None
                simulado = simulado.deliver(resultado=paso.resultado, now=simulado.updated_at)
            elif paso.kind == PASO_FALLO_SEGURO:
                assert paso.diagnostico is not None
                simulado = simulado.fail_safely(
                    diagnostico=paso.diagnostico, now=simulado.updated_at
                )
            elif paso.kind == PASO_DECISION_RESUELTA:
                assert paso.resultado is not None
                simulado = simulado.resolve_decision(
                    continuar=bool(paso.resultado["continuar"]), now=simulado.updated_at
                )
            else:
                metodo = getattr(simulado, _AVANZAR_DOMINIO[paso.kind])
                simulado = metodo(now=simulado.updated_at)
        except EngineError:
            return None
    return simulado


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
    PASO_CANCELADO: "cancel_work_item",
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
