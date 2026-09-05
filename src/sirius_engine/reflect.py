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
6. **Recorrer lo acreditado, cuando la foto sola no basta** (ADR-144,
   incidencia #539). Las cinco reglas de arriba comparan DOS FOTOS: el estado
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
   los métodos del dominio, que son los que dicen qué es legal-. Y hace falta
   al menos un estado acreditado ESTRICTAMENTE ENTRE el ancla y el destino
   que el historial alcanza, distinto de la foto: lo que se mide es el
   SALTO -¿hay algo entre el ancla y el destino?-, no la coincidencia con la
   foto, porque hay pares del mapa etiqueta -> (estado, fase) que ningún
   marcador ``sirius-notification`` puede producir y contra los que comparar
   con la foto no filtra nada (CLAUDE-REV-001, ronda 1, PR #540). Un
   historial que no acredita nada intermedio no acredita ninguna secuencia, y
   ese salto de una sola observación se sigue rechazando como hoy (CODEX-001,
   ronda 4, PR #530). Y la acreditación es POR TRAMO: si el recorrido pasa
   por una segunda parada, la salida de esa parada la acredita la observación
   que el recorrido toma como objetivo justo DESPUÉS de ella -el marcador que
   el bot publicó, fechado y posterior a la parada- siempre que no sea la
   propia foto, o el marcador real de reanudación; nunca la foto final
   (CODEX-001, ronda 1, PR #540; CLAUDE-R2-001 y CODEX-001, ronda 2).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from sirius_engine.domain.dispatch import DispatchEpisode
from sirius_engine.domain.errors import EngineError
from sirius_engine.domain.mirror import EstadoAcreditado, MirroredWorkItem
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
    ``espejo.reanudacion_publicada`` -el permiso escrito del propietario,
    regla 3-; desde un tramo del recorrido acreditado (regla 6) lo decide
    :func:`_salida_de_parada_acreditada` para ESE tramo, y nunca lo autoriza
    la foto. El parámetro existe para que esa diferencia se vea en la firma en
    vez de esconderse en un espejo fabricado con el campo cambiado.
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
       legales que conecta el estado guardado con la foto, se recorre entera.
       Si no la acredita, se devuelve la divergencia del punto 1 tal cual
       -mismo texto, mismo fail-open, cero pasos.

    Sigue siendo pura: no llama al almacén, a GitHub ni al disco.
    """
    por_foto = _reflejar_por_foto(
        work_item, espejo, episodio, reanudacion_acreditada=espejo.reanudacion_publicada
    )
    if por_foto.divergencia is None:
        return por_foto
    recorrido = _recorrer_historial_acreditado(work_item, espejo, episodio)
    return recorrido if recorrido is not None else por_foto


def _objetivos_acreditados(
    work_item: WorkItem, espejo: MirroredWorkItem
) -> tuple[EstadoAcreditado, ...] | None:
    """Los estados acreditados que quedan POR recorrer, o ``None`` si no hay recorrido.

    Dos exigencias, y las dos son la salvaguarda entera:

    - **Ancla**: el estado guardado del motor tiene que aparecer en el
      historial acreditado, y se toma la coincidencia MÁS RECIENTE -el motor
      está donde se quedó, no donde estuvo la primera vez-. Un marcador de
      parada no trae fase (``sirius:failed-safely`` y
      ``sirius:blocked-decision`` proyectan ``fase=None``), así que en esos la
      coincidencia es solo de estado; en los demás tienen que coincidir los
      dos ejes.
    - **Acreditación intermedia**: tiene que haber al menos una observación
      ESTRICTAMENTE ENTRE el ancla y el destino que el historial alcanza -su
      última observación-, y esa observación intermedia tiene que decir algo
      que la foto no dijera ya. Lo que se mide es el SALTO, no la coincidencia
      con la foto: sin esta forma, un historial cuya única observación
      posterior al ancla es la etiqueta activa repuesta pasaba el filtro
      siempre que la foto vigente no fuera expresable como marcador
      ``sirius-notification`` -y tres pares del mapa etiqueta -> (estado,
      fase) no lo son: ``sirius:ci-pending`` -> (ACTIVE, COMPROBAR) y
      ``sirius:review-requested``/``sirius:reviewing`` -> (ACTIVE, REVISAR),
      porque ``notify-sirius-state.yml`` solo vigila seis etiquetas-. Ese
      salto de una sola observación es exactamente el que el reflector rechaza
      desde CODEX-001 (ronda 4, PR #530): una etiqueta de parada sustituida a
      mano, sin ninguna orden del propietario, no autoriza nada, y la foto que
      la pasada ve muy a menudo es ``ci-pending`` o ``reviewing`` -las tres
      expuestas- porque ``reflejar-desenlace.yml`` se dispara por
      ``workflow_run`` (CLAUDE-REV-001, ronda 1, PR #540).
    """
    historial = espejo.historial_estados
    ancla: int | None = None
    for indice, acreditado in enumerate(historial):
        if acreditado.estado is not work_item.estado:
            continue
        if acreditado.fase is not None and acreditado.fase is not work_item.fase:
            continue
        ancla = indice
    if ancla is None:
        return None
    posteriores = historial[ancla + 1 :]
    if not posteriores:
        return None
    foto = (espejo.estado, espejo.fase)
    # La ÚLTIMA observación es el destino al que el historial llega, no una
    # acreditación de cómo se llegó: lo que acredita el recorrido es lo que
    # hay entre el ancla y ese destino. Y una intermedia que solo repite la
    # foto no acredita nada, porque no dice nada que la foto no dijera ya.
    intermedias = posteriores[:-1]
    if all((acreditado.estado, acreditado.fase) == foto for acreditado in intermedias):
        return None
    return posteriores


def _salida_de_parada_acreditada(
    espejo: MirroredWorkItem,
    objetivos: tuple[EstadoAcreditado, ...],
    indice: int,
    foto: tuple[WorkItemState | None, WorkItemPhase | None],
) -> bool:
    """Qué autoriza a salir de una parada en el tramo ``indice`` del recorrido.

    El recorrido acreditado no es un permiso global: es un permiso POR TRAMO,
    y cada tramo tiene que acreditar el suyo. Un recorrido puede contener más
    de una parada -el historial real de la #537 tiene dos-, y la salida de la
    SEGUNDA no puede apoyarse en la acreditación que autorizó la primera ni,
    peor, en la propia foto final: eso resolvería solo un ``NEEDS_DECISION``
    sin ninguna orden del propietario, que es justo lo que CODEX-001 (ronda 4,
    PR #530) cerró y lo que ADR-144 exige preservar (CODEX-001, ronda 1, PR
    #540).

    Autoriza una de dos cosas, nunca la foto:

    - el marcador REAL de reanudación (``espejo.reanudacion_publicada``, el
      permiso escrito del propietario), que vale para todo el recorrido; o
    - la observación acreditada de ESTE tramo (``objetivos[indice]``) cuando
      no es la foto: es exactamente el marcador que el bot publicó, fechado,
      DESPUÉS de la parada de la que este tramo intenta salir -la primera
      evidencia de que la incidencia volvió a estar viva-. La foto no cuenta:
      es el destino, no evidencia de haber salido.

    Lo que se mide es la evidencia posterior a ESA PARADA, no la posición
    respecto al tramo ni la coincidencia con la foto. Medirla sobre
    ``objetivos[indice + 1 :]`` -la primera forma de esta función- volvía a
    hacer depender la acreditación de la foto por la puerta de atrás: exigía
    una observación de más y contaba como acreditación la ÚLTIMA del
    historial, que es el destino y no una acreditación de cómo se llegó. El
    mismo historial recorría o no según cuál fuera la etiqueta vigente en el
    momento de la pasada (CLAUDE-R2-001 y CODEX-001, ronda 2, PR #540).

    Por construcción, el último tramo del recorrido -el que va contra el
    espejo real- coincide con la foto, así que solo el marcador real puede
    autorizarlo.
    """
    if espejo.reanudacion_publicada:
        return True
    objetivo = objetivos[indice]
    return (objetivo.estado, objetivo.fase) != foto


def _recorrer_historial_acreditado(
    work_item: WorkItem, espejo: MirroredWorkItem, episodio: DispatchEpisode
) -> ResultadoReflejo | None:
    """El plan que recorre, tramo a tramo, lo que el historial de confianza acredita.

    ``None`` cuando no hay recorrido posible -y entonces el llamador conserva
    la divergencia de siempre-. Es TODO O NADA: si cualquier tramo diverge o
    resulta ilegal, no se devuelve el trozo bueno; se abandona entero. Aplicar
    media recuperación dejaría el diario en un punto que nadie acreditó.

    Cada tramo se calcula con la MISMA :func:`_reflejar_por_foto` que la foto
    actual y con su PROPIA acreditación de salida de parada
    (:func:`_salida_de_parada_acreditada`: un recorrido puede contener más de
    una parada, y cada una tiene que acreditar la suya), sobre un espejo
    derivado del real al que solo se le cambian
    ``estado``/``fase``/``etiquetas`` por los del estado acreditado: el resto
    -diagnóstico de fallo, SHA de fusión- sigue siendo el del espejo real,
    porque es el único que hay. Y entre tramo y tramo el ``WorkItem`` avanza
    llamando a los métodos REALES del dominio (:func:`_avanzar`), no a una
    tabla paralela de estados: si un tramo no fuera una transición legal, es
    la máquina de estados de :mod:`sirius_engine.domain.work_item` la que lo
    dice, y el recorrido se abandona. Este módulo no añade ninguna arista.
    """
    if espejo.etiquetas_contradictorias or espejo.estado is None:
        # Invariante 4 de la incidencia #539: una incidencia con etiquetas de
        # estado contradictorias se sigue tratando como hoy -declarar y no
        # tocar nada-, y sin foto no hay destino al que recorrer.
        return None
    objetivos = _objetivos_acreditados(work_item, espejo)
    if objetivos is None:
        return None

    foto = (espejo.estado, espejo.fase)
    pasos: list[PasoReflejo] = []
    simulado = work_item
    for indice, acreditado in enumerate(objetivos):
        espejo_del_tramo = replace(
            espejo,
            estado=acreditado.estado,
            fase=acreditado.fase,
            etiquetas=(acreditado.etiqueta,),
        )
        tramo = _reflejar_por_foto(
            simulado,
            espejo_del_tramo,
            episodio,
            reanudacion_acreditada=_salida_de_parada_acreditada(espejo, objetivos, indice, foto),
        )
        if tramo.divergencia is not None:
            return None
        avanzado = _avanzar(simulado, tramo.pasos)
        if avanzado is None:
            return None
        simulado = avanzado
        pasos.extend(tramo.pasos)

    # El último tramo va contra el espejo REAL, no contra un derivado: es el
    # que trae el SHA de fusión de la entrega y el que garantiza que el
    # recorrido termina exactamente en la foto, no cerca.
    ultimo = _reflejar_por_foto(
        simulado, espejo, episodio, reanudacion_acreditada=espejo.reanudacion_publicada
    )
    if ultimo.divergencia is not None:
        return None
    pasos.extend(ultimo.pasos)
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
