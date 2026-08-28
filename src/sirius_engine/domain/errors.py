"""Domain errors for the Sirius Work Engine core (arquitectura §3.2-3.3).

Every illegal operation raises one of these instead of silently coercing
state, so "toda transición fuera del grafo aprobado falla de forma
explícita" (incidencia #177, requisito 1) holds for both ``WorkItem`` and
``Run``.
"""

from __future__ import annotations


class EngineError(Exception):
    """Base class for every error raised by the Work Engine core."""


class IllegalTransitionError(EngineError):
    """Raised when an operation is attempted from a state the approved graph forbids."""

    def __init__(self, aggregate: str, operation: str, current_state: str) -> None:
        super().__init__(f"cannot {operation} {aggregate} while in state {current_state!r}")
        self.aggregate = aggregate
        self.operation = operation
        self.current_state = current_state


class IllegalPhaseTransitionError(EngineError):
    """Raised when a phase-advancing operation is attempted from a phase the approved cycle forbids.

    Mirrors :class:`IllegalTransitionError` but for the ``fase`` axis
    (arquitectura §3.4: ``PREPARAR -> EJECUTAR -> COMPROBAR -> REVISAR ->
    (REPARAR -> COMPROBAR -> REVISAR)* -> ENTREGAR``), which advances
    independently of ``estado``.
    """

    def __init__(self, aggregate: str, operation: str, current_phase: str) -> None:
        super().__init__(f"cannot {operation} {aggregate} while in phase {current_phase!r}")
        self.aggregate = aggregate
        self.operation = operation
        self.current_phase = current_phase


class DeadlineNotExceededError(EngineError):
    """Raised by ``mark_lost`` when the Run's absolute deadline has not passed yet.

    Arquitectura §3.3: ``LOST`` requires both a state that lacks a
    conclusive ``STATUS`` (checked as an ``IllegalTransitionError``) and the
    absolute deadline having elapsed. The two are independent guards, kept
    as distinct errors so a test can tell which one failed.
    """

    def __init__(self, run_id: str) -> None:
        super().__init__(f"run {run_id} cannot be marked LOST before its deadline elapses")
        self.run_id = run_id


class MutableResourceConflictError(EngineError):
    """Raised when dispatching a Run would collide with an unconfirmed cancellation.

    Arquitectura §3.3: "el despachador tiene prohibido lanzar un sustituto o
    un paso nuevo sobre el mismo recurso mutable" while another Run on that
    resource is ``CANCELLATION_UNCONFIRMED``.
    """

    def __init__(self, recurso_mutable: str, conflicting_run_id: str) -> None:
        super().__init__(
            f"cannot dispatch a run on mutable resource {recurso_mutable!r}: "
            f"run {conflicting_run_id} has an unconfirmed cancellation pending on it"
        )
        self.recurso_mutable = recurso_mutable
        self.conflicting_run_id = conflicting_run_id


class ScopeInvalidatedRunError(EngineError):
    """Raised when retrying or substituting a Run invalidated by a scope change.

    Arquitectura §3.2: un cambio de alcance invalida los Runs que quedan
    obsoletos. Su ``work_package`` describe el alcance viejo, así que ese Run
    no puede originar otro: hay que volver a PREPARAR desde el alcance nuevo.
    Se mantiene distinto de :class:`IllegalTransitionError` porque una
    cancelación ordinaria ya confirmada **sí** admite reintento y sustitución
    (§3.3 solo lo prohíbe mientras la cancelación está sin confirmar), y una
    prueba debe poder distinguir qué guarda saltó.
    """

    def __init__(self, run_id: str, operation: str) -> None:
        super().__init__(
            f"cannot {operation} run {run_id}: it was invalidated by a scope change; "
            "prepare a new run from the current scope instead"
        )
        self.run_id = run_id
        self.operation = operation


class UnknownWorkItemError(EngineError):
    """Raised when a ``work_id`` does not refer to a known WorkItem."""

    def __init__(self, work_id: str) -> None:
        super().__init__(f"unknown work item {work_id!r}")
        self.work_id = work_id


class UnknownRunError(EngineError):
    """Raised when a ``run_id`` does not refer to a known Run."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"unknown run {run_id!r}")
        self.run_id = run_id


class DuplicateIdError(EngineError):
    """Raised when creating an aggregate whose id already exists."""

    def __init__(self, aggregate: str, aggregate_id: str) -> None:
        super().__init__(f"{aggregate} {aggregate_id!r} already exists")
        self.aggregate = aggregate
        self.aggregate_id = aggregate_id


class ParentNotInProgressError(EngineError):
    """H-27 (auditoría #396): un WorkItem terminal no puede ganar intentos nuevos.

    Un Run es un intento de un paso de SU WorkItem; preparar uno para un padre
    ``DELIVERED`` o ``CANCELLED`` contaría una historia que el dominio declara
    imposible, y el diario la reconstruiría como si fuera legal.
    """

    def __init__(self, work_id: str, estado: str) -> None:
        super().__init__(
            f"work item {work_id!r} is {estado}: a terminal parent cannot gain new runs"
        )
        self.work_id = work_id
        self.estado = estado


class LiveRunsPreventDeliveryError(EngineError):
    """H-27: DELIVERED no puede coexistir con Runs vivos ni con el peligro de H-26.

    Entregar es afirmar que el trabajo terminó; un intento aún vivo -o un
    perdido con cancelación sin confirmar, que es un Worker quizá vivo- dice lo
    contrario a la vez.
    """

    def __init__(self, work_id: str, run_ids: tuple[str, ...]) -> None:
        super().__init__(
            f"work item {work_id!r} cannot be delivered: live or unresolved runs {run_ids!r}"
        )
        self.work_id = work_id
        self.run_ids = run_ids


class UnknownAgentProfileError(EngineError):
    """Raised when an ``AgentProfile`` ref does not resolve to a versioned profile.

    Arquitectura §5.1: un ``AgentProfileRef`` sin perfil correspondiente no
    tiene un valor por defecto razonable -no hay "perfil genérico" al que
    caer- así que se declara explícitamente en vez de dejar que ``None``
    viaje silenciosamente hasta un fallo más difícil de diagnosticar.
    """

    def __init__(self, ref: str) -> None:
        super().__init__(f"unknown agent profile {ref!r}")
        self.ref = ref


class UnknownCapabilityError(EngineError):
    """Raised when a profile requests a capability absent from the registry.

    Arquitectura §6: "una capacidad no registrada no se resuelve; no se
    degrada ni se sustituye por otra" (incidencia #202, requisito A4-P4).
    """

    def __init__(self, nombre: str) -> None:
        super().__init__(f"capability {nombre!r} is not registered in the capability registry")
        self.nombre = nombre


class CapabilityNotGrantedError(EngineError):
    """Raised when a requested capability is registered but absent from the effective envelope.

    Arquitectura §6.1 / incidencia #202 (A4-P5): un ``PermissionEnvelope``
    sin la capacidad pedida IMPIDE la resolución -nunca la concede recortada
    ni la sustituye por otra.
    """

    def __init__(self, nombre: str) -> None:
        super().__init__(
            f"capability {nombre!r} is registered but not granted by the permission envelope"
        )
        self.nombre = nombre


class EgressIncompatibleError(EngineError):
    """Raised when a profile declares both external network and unrestricted write access.

    Arquitectura §6.1 regla 1: red externa (``web.*``) y escritura
    irrestricta al repositorio/contexto privado son incompatibles en un
    mismo Run; la combinación no se degrada ni se advierte, no se resuelve
    (fail-closed antes de ``START``).
    """

    def __init__(self, profile_ref: str) -> None:
        super().__init__(
            f"agent profile {profile_ref!r} declares both external network and "
            "unrestricted write access, which the global egress policy forbids "
            "in the same Run (arquitectura §6.1 regla 1)"
        )
        self.profile_ref = profile_ref


class EgressClassificationError(EngineError):
    """Raised when a context fragment cannot be proven safe to send to a Worker.

    Arquitectura §6.1 regla 4: un fragmento sin clasificación conocida, o sin
    la clasificación ``exportable`` exigida cuando el Worker tiene red
    externa concedida, impide arrancar el Run. Fail-closed: nunca advierte,
    siempre impide (incidencia #202, A4-P3).
    """

    def __init__(self, procedencia: str, *, motivo: str) -> None:
        super().__init__(
            f"context fragment from {procedencia!r} blocks START: {motivo} "
            "(arquitectura §6.1 regla 4, fail-closed)"
        )
        self.procedencia = procedencia
        self.motivo = motivo


class OrdenNoEnlazadaError(EngineError):
    """Raised when the dispatcher is asked to activate a WorkItem without a linked owner order.

    Contrato §12.1: el motor solo puede aplicar la etiqueta de activación
    "solo si existe una orden explícita del propietario, registrada y
    enlazada en la evidencia de ese WorkItem. Sin orden enlazada que
    señalar, el motor no arranca nada." Esta guarda es la que hace cumplir
    esa condición sin excepción (incidencia #240, C2).
    """

    def __init__(self, work_id: str) -> None:
        super().__init__(
            f"work item {work_id!r} has no owner order linked in its evidence; "
            "the dispatcher refuses to activate it (contrato §12.1)"
        )
        self.work_id = work_id


class ClaseNoDespachableError(EngineError):
    """Raised when the dispatcher is asked to dispatch a WorkItem outside its class scope.

    El despachador (C2, incidencia #240; ampliado a auditoría en C4,
    incidencia #256) despacha exclusivamente las clases de la tabla cerrada
    del contrato §12.4 -``programacion`` y ``auditoria``-: es lo único que su
    alcance permitido autoriza. Otras clases (documentacion, investigacion...)
    tienen su propio bloque futuro y no se inventan aquí.
    """

    def __init__(self, work_id: str, clase: str) -> None:
        super().__init__(
            f"work item {work_id!r} has class {clase!r}; the dispatcher only "
            "handles 'programacion' and 'auditoria' work items"
        )
        self.work_id = work_id
        self.clase = clase


class EstadoNoDespachableError(EngineError):
    """Raised when the C2 dispatcher is asked to dispatch a WorkItem that is not ``ACTIVE``.

    Una referencia de orden en ``evidencia`` que sobrevive a una
    cancelación, una pausa, una escalada o una entrega no revive el
    trabajo: solo un ``WorkItem`` de programación actualmente ``ACTIVE``
    -el único estado en que §3.2 sitúa trabajo en curso listo para
    despacharse- puede despacharse (incidencia #240, C2).
    """

    def __init__(self, work_id: str, estado: str) -> None:
        super().__init__(
            f"work item {work_id!r} is in state {estado!r}; the C2 dispatcher only "
            "dispatches work items in state 'active'"
        )
        self.work_id = work_id
        self.estado = estado


class WorkerRuntimeConflictError(EngineError):
    """Raised when a Run is told it ran on a model or runtime other than the one on record.

    Arquitectura §3.3: ``worker`` registra el modelo/runtime **concretos
    usados**. Un Run que ya tiene ese dato no puede cambiarlo después: su
    historia es lo único que sostiene cualquier afirmación posterior sobre
    qué modelo hizo qué (incidencia #217). Sobrescribirlo en silencio
    convertiría esa afirmación en indemostrable, así que la contradicción
    falla de forma explícita, como cualquier otra operación fuera del grafo
    aprobado.
    """

    def __init__(self, campo: str, *, registrado: str, recibido: str) -> None:
        super().__init__(
            f"worker already ran with {campo} {registrado!r}; refusing to overwrite it "
            f"with {recibido!r}"
        )
        self.campo = campo
        self.registrado = registrado
        self.recibido = recibido
