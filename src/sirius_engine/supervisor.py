"""Supervisor de la vía GitHub (C1, incidencia #232, contrato §12.2).

El punto de entrada es :func:`supervise_runs`: reutiliza
:func:`sirius_engine.recovery.run_recovery_sweep` (A2, ya probado) para
reconciliar el estado remoto -incluida la clasificación de S3 vía
:class:`~sirius_engine.adapters.github_actions_run_observer.GitHubActionsRunObserver`-
y, para cada ``Run`` que la reconciliación deja en ``FINISHED(LOST)``, decide
y aplica UNA acción (:mod:`sirius_engine.domain.supervision`): reactivar,
sustituir Worker o escalar.

Cuatro guardas, en el orden en que se comprueban, cada una con su prueba
dedicada (requisitos de la incidencia #232):

1. **Idempotencia (C1-P2).** Si :class:`~sirius_engine.ports.supervisor_journal.SupervisorJournal`
   ya tiene un episodio para este ``run_id``, no se repite la acción. Un
   ``Run`` solo llega a ``LOST`` una vez -es terminal-, así que esta
   comprobación por sí sola basta para que dos pasadas del supervisor sobre
   el mismo atasco produzcan una sola acción.
2. **Propiedad (C1-P3, §12.2 límite 1).** :func:`_run_gobernado_por_el_motor`
   vuelve a comprobar contra el almacén -nunca se fía del objeto ``Run``
   recibido- que el run pertenece de verdad a un ``WorkItem`` del propio
   almacén.
3. **Jurisdicción (coordinación con el reconciliador, contrato §11).** El
   motor solo actúa sobre ``WorkItem`` de autoridad ``MOTOR``
   (:mod:`sirius_engine.domain.authority`). Para autoridad ``INCIDENCIA``
   -las clases que ``scripts/automation/sirius_reconcile.sh`` ya vigila por
   etiquetas de GitHub-, el motor no actúa: los dos vigilantes nunca
   comparten dominio, así que no puede haber carrera entre ellos. Es la
   misma idea que dice el objetivo de la incidencia -"el motor respeta sus
   marcadores"-, aplicada donde es comprobable: no como una lectura de los
   comentarios del reconciliador, sino como una frontera que hace la
   pregunta irrelevante.
4. **No inventar trabajo (§12.2 límite 2).** Ninguna rama de este módulo
   llama a ``create_work_item`` ni a ``create_and_escalate_work_item``: la
   única vía posible es actuar sobre un ``Run`` ya existente de un
   ``WorkItem`` ya existente.

**Un fallo del supervisor no deja el trabajo peor que como lo encontró**: la
acción sobre un ``Run`` va en su propio ``try``/``except`` -si falla, no se
registra episodio (una pasada futura reintenta) y el barrido sigue con el
resto de Runs, exactamente como ya hace ``run_recovery_sweep`` con
``unobserved_runs``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius_engine.domain.authority import Autoridad, autoridad_de_clase
from sirius_engine.domain.escalation import CausaEscalado, Escalada, construir_escalada
from sirius_engine.domain.events import rebuild_state
from sirius_engine.domain.run import Run, RunOutcome, RunState
from sirius_engine.domain.supervision import (
    SupervisionDecision,
    SupervisionEpisode,
    SupervisorPolicy,
    decidir_politica,
)
from sirius_engine.domain.work_item import WorkItem, WorkItemState
from sirius_engine.ports.notification import NotificationPort
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.ports.supervisor_journal import SupervisorJournal
from sirius_engine.ports.world import RunWorldObserver
from sirius_engine.recovery import RecoverySweepResult, run_recovery_sweep

#: Política por defecto cuando el llamador no configura ninguna. Un único
#: objeto módulo-nivel (no una llamada en la firma) para que el valor por
#: defecto no se reconstruya en cada invocación (B008).
_POLITICA_POR_DEFECTO = SupervisorPolicy()


@dataclass(frozen=True, slots=True)
class SupervisionOutcome:
    """Una acción que el supervisor SÍ aplicó."""

    run_id: str
    work_id: str
    decision: SupervisionDecision
    motivo: str
    resulting_run_id: str | None
    escalada: Escalada | None = None


@dataclass(frozen=True, slots=True)
class SupervisionError:
    """Un intento de acción que falló: no se registra episodio, se reintenta después."""

    run_id: str
    mensaje: str


@dataclass(frozen=True, slots=True)
class SupervisionSweepResult:
    """Qué hizo una pasada de :func:`supervise_runs`."""

    recovery: RecoverySweepResult
    acted: tuple[SupervisionOutcome, ...] = ()
    #: Runs que no pertenecen al almacén del motor (C1-P3): no se tocan.
    skipped_foreign: tuple[str, ...] = ()
    #: Runs de autoridad INCIDENCIA (fuera de la jurisdicción del motor) o
    #: cuyo WorkItem no estaba en un estado desde el que actuar tenga
    #: sentido todavía: no se tocan, pero tampoco es un error.
    deferred: tuple[str, ...] = ()
    errors: tuple[SupervisionError, ...] = ()


def _run_gobernado_por_el_motor(store: WorkEngineStore, run: Run) -> WorkItem | None:
    """El ``WorkItem`` de ``run``, solo si ``run`` es de verdad un Run del propio almacén.

    Defensa en profundidad para C1-P3 (§12.2 límite 1): en vez de confiar en
    el objeto ``Run`` que el llamador entregó, se vuelve a preguntar al
    almacén -la única fuente de verdad de "qué Runs despachó y gobierna el
    motor"- si ese ``run_id`` aparece de verdad entre los Runs de su
    ``work_id``. Un ``Run`` ajeno (fabricado fuera del almacén, o de un
    ``work_id`` que el almacén no conoce) no pasa esta comprobación.
    """
    work_item = store.get_work_item(run.work_id)
    if work_item is None:
        return None
    propios = store.list_runs_for_work_item(run.work_id)
    if not any(propio.run_id == run.run_id for propio in propios):
        return None
    return work_item


def _bajo_jurisdiccion_del_motor(work_item: WorkItem) -> bool:
    """Solo autoridad MOTOR (contrato §11): la única clase que el reconciliador nunca vigila."""
    return autoridad_de_clase(work_item.clase) is Autoridad.MOTOR


def _nuevo_deadline(run: Run, *, now: datetime) -> datetime:
    """Conserva la MISMA duración que ya tenía el intento perdido, reiniciada desde ``now``.

    No es una cota nueva: S3 declaró NO CONCLUYENTE cualquier duración
    derivada de sus mediciones, así que este módulo no fija ninguna. La
    duración que se reutiliza aquí es la que ya decidió quien preparó el Run
    original -un dato del propio dominio, no una medición de este bloque-.
    """
    return now + (run.deadline - run.created_at)


def _reactivar_o_sustituir(
    store: WorkEngineStore,
    run: Run,
    *,
    decision: SupervisionDecision,
    policy: SupervisorPolicy,
    now: datetime,
) -> SupervisionOutcome:
    nuevo_run_id = f"{run.run_id}-S{run.intento + 1}"
    deadline = _nuevo_deadline(run, now=now)
    if decision is SupervisionDecision.REACTIVATE:
        motivo = (
            f"el paso {run.paso!r} se perdió en su intento {run.intento}; se repone "
            "exactamente lo que el consumo retiró: un nuevo intento con el mismo Worker "
            "(contrato §12.2)"
        )
        nuevo = store.retry_run(run.run_id, new_run_id=nuevo_run_id, deadline=deadline, now=now)
        return SupervisionOutcome(
            run_id=run.run_id,
            work_id=run.work_id,
            decision=decision,
            motivo=motivo,
            resulting_run_id=nuevo.run_id,
        )
    assert policy.worker_alternativo is not None  # decidir_politica ya lo exigió
    motivo = (
        f"el Worker {run.worker.adapter!r} perdió el paso {run.paso!r} tras "
        f"{run.intento} intento(s); se sustituye por {policy.worker_alternativo.adapter!r} "
        "(contrato §12.2)"
    )
    nuevo = store.substitute_run_worker(
        run.run_id,
        new_run_id=nuevo_run_id,
        worker=policy.worker_alternativo,
        motivo=motivo,
        deadline=deadline,
        now=now,
    )
    return SupervisionOutcome(
        run_id=run.run_id,
        work_id=run.work_id,
        decision=decision,
        motivo=motivo,
        resulting_run_id=nuevo.run_id,
    )


def _escalar(
    store: WorkEngineStore,
    run: Run,
    work_item: WorkItem,
    *,
    now: datetime,
    notificar: NotificationPort | None,
) -> SupervisionOutcome | None:
    """Escalar por ``AUSENCIA_DE_CONVERGENCIA`` (arquitectura §10, causa 7).

    Devuelve ``None`` -sin actuar- si el ``WorkItem`` no está en un estado
    desde el que escalar tenga sentido todavía: "ante la duda, informa y no
    toca" (misma disciplina que §9.1). No se fuerza ninguna transición que el
    propio Run perdido no justifique por sí solo.
    """
    actual = store.get_work_item(work_item.work_id)
    if actual is None:
        return None
    if actual.estado is WorkItemState.WAITING:
        otros_vivos = [
            otro
            for otro in store.list_runs_for_work_item(work_item.work_id)
            if otro.run_id != run.run_id and otro.estado is not RunState.FINISHED
        ]
        if otros_vivos:
            # Otros pasos siguen en curso: liberar la espera aquí afirmaría
            # un hecho externo que no ha ocurrido para ELLOS. Se difiere.
            return None
        actual = store.observe_work_item_external_fact(work_item.work_id, now=now)
    motivo = (
        f"el paso {run.paso!r} se perdió tras {run.intento} intento(s) sin que la "
        "política de supervisión encontrara una alternativa: ni reintentar ni sustituir "
        "el Worker progresó (arquitectura §10, causa 7)"
    )
    if actual.estado is WorkItemState.ACTIVE:
        escalado = store.escalate_work_item(work_item.work_id, now=now)
    elif actual.estado is WorkItemState.NEEDS_DECISION:
        # La transición YA se aplicó -de esta misma acción en una pasada
        # anterior que murió justo después de escalar, antes de que la
        # notificación se entregara (CODEX-004)-: `escalate_work_item` no
        # se repite (el WorkItem ya no está ACTIVE), solo se reintenta la
        # entrega pendiente. Sin este caso, un fallo de `notificar` dejaba
        # el propietario sin avisar para siempre: la siguiente pasada veía
        # `NEEDS_DECISION` -no `ACTIVE`- y difería sin volver a intentarlo.
        escalado = actual
    else:
        return None
    escalada = construir_escalada(
        escalado,
        causa=CausaEscalado.AUSENCIA_DE_CONVERGENCIA,
        motivo=motivo,
        ocurrida_en=now,
        referencias=(run.run_id,),
    )
    if notificar is not None:
        notificar.notificar(escalada)
    return SupervisionOutcome(
        run_id=run.run_id,
        work_id=work_item.work_id,
        decision=SupervisionDecision.ESCALATE,
        motivo=motivo,
        resulting_run_id=None,
        escalada=escalada,
    )


def _actuar(
    store: WorkEngineStore,
    run: Run,
    work_item: WorkItem,
    *,
    policy: SupervisorPolicy,
    now: datetime,
    notificar: NotificationPort | None,
) -> SupervisionOutcome | None:
    decision = decidir_politica(run, policy=policy)
    if decision in (SupervisionDecision.REACTIVATE, SupervisionDecision.SUBSTITUTE_WORKER):
        return _reactivar_o_sustituir(store, run, decision=decision, policy=policy, now=now)
    return _escalar(store, run, work_item, now=now, notificar=notificar)


def _episodio(run: Run, outcome: SupervisionOutcome, *, now: datetime) -> SupervisionEpisode:
    """Construye el episodio SIN volver a preguntar al mundo.

    Antes se releía vía ``observer.check_run()`` para completar el texto
    "observado", y esa segunda lectura corría DESPUÉS de que la mutación del
    almacén (``retry_run``/``substitute_run_worker``/``escalate_work_item``)
    ya se hubiera aplicado con éxito: si esa relectura fallaba, la excepción
    se propagaba sin capturar (fuera del ``try``/``except`` que aísla
    ``_actuar``), el episodio nunca llegaba a registrarse, y la siguiente
    pasada reintentaba la MISMA acción sobre un Run ya reactivado/sustituido
    -``DuplicateIdError`` permanente-. El desenlace que motiva esta llamada
    ya está en el propio ``run`` (el bucle de :func:`supervise_runs` solo
    llega aquí cuando ``run.desenlace is RunOutcome.LOST``): no hace falta
    ninguna E/S adicional para contarlo.
    """
    assert run.desenlace is not None
    return SupervisionEpisode(
        run_id=run.run_id,
        work_id=run.work_id,
        paso=run.paso,
        intento=run.intento,
        observado=run.desenlace.value,
        decision=outcome.decision,
        motivo=outcome.motivo,
        resulting_run_id=outcome.resulting_run_id,
        recorded_at=now,
    )


def supervise_runs(
    store: WorkEngineStore,
    observer: RunWorldObserver,
    journal: SupervisorJournal,
    *,
    now: datetime,
    policy: SupervisorPolicy = _POLITICA_POR_DEFECTO,
    notificar: NotificationPort | None = None,
) -> SupervisionSweepResult:
    """Reconciliar el mundo y actuar sobre cada ``Run`` que esté ``LOST``.

    No se limita a los Runs que ESTA pasada de :func:`~sirius_engine.recovery.run_recovery_sweep`
    reconcilió: también revisa cualquier ``Run`` que ya estuviera ``LOST`` de
    una pasada anterior -por ejemplo, si el propio supervisor murió justo
    después de que el barrido lo cerrara como perdido, pero antes de decidir
    una política sobre él-. Sin este segundo barrido, un ``Run`` así no
    volvería a aparecer nunca en ``reconciled_run_ids`` (ya es ``FINISHED``,
    y ``run_recovery_sweep`` filtra los Runs terminados) y se quedaría sin
    supervisar para siempre. El marcador de idempotencia
    (``journal.has_episode``) es lo que hace que revisar TODOS los Runs
    ``LOST`` en cada pasada siga produciendo una sola acción por atasco
    (C1-P2), no una repetida.

    Determinista (C1-P5): con el mismo diario, el mismo ``observer`` y el
    mismo ``now``, produce siempre la misma :class:`SupervisionSweepResult`
    -ninguna rama de este módulo lee el reloj real ni usa aleatoriedad-.
    """
    recovery_result = run_recovery_sweep(store, observer, now=now)
    estado = rebuild_state(store.list_events())
    run_ids_perdidos = sorted(
        run_id
        for run_id, run in estado.runs.items()
        if run.estado is RunState.FINISHED and run.desenlace is RunOutcome.LOST
    )

    acted: list[SupervisionOutcome] = []
    skipped_foreign: list[str] = []
    deferred: list[str] = []
    errors: list[SupervisionError] = []

    for run_id in run_ids_perdidos:
        run = store.get_run(run_id)
        if run is None or run.desenlace is not RunOutcome.LOST:
            continue
        if journal.has_episode(run_id):
            continue
        work_item = _run_gobernado_por_el_motor(store, run)
        if work_item is None:
            skipped_foreign.append(run_id)
            continue
        if not _bajo_jurisdiccion_del_motor(work_item):
            deferred.append(run_id)
            continue
        try:
            outcome = _actuar(store, run, work_item, policy=policy, now=now, notificar=notificar)
        except Exception as exc:  # aislar el fallo de ESTE Run del resto del barrido
            errors.append(SupervisionError(run_id=run_id, mensaje=str(exc)))
            continue
        if outcome is None:
            deferred.append(run_id)
            continue
        journal.record(_episodio(run, outcome, now=now))
        acted.append(outcome)

    return SupervisionSweepResult(
        recovery=recovery_result,
        acted=tuple(acted),
        skipped_foreign=tuple(skipped_foreign),
        deferred=tuple(deferred),
        errors=tuple(errors),
    )
