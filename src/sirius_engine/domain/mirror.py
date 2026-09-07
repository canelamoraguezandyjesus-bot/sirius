"""Tipos del espejo de solo lectura de la vía GitHub (A3, arquitectura §3.5).

Estos tipos NO extienden ``WorkItem``/``Run`` (dominio de A1): son una
proyección aparte, deliberadamente separada, de lo que una incidencia de
GitHub *parece* decir sobre un trabajo. La razón de no reutilizar
``WorkItem``/``Run`` directamente es la misma que hace falta este módulo:
esos tipos representan el estado que EL MOTOR posee y hace avanzar por sus
propias transiciones controladas (arquitectura §3.1-§3.3); una incidencia de
GitHub no pasa por esas transiciones, así que forzarla al mismo tipo
mezclaría "lo que el motor decidió" con "lo que alguien más observó" y haría
más fácil, no más difícil, confundir un espejo con la autoridad.

Todo lo que este módulo produce lleva dos cosas de forma estructural, nunca
opcional:

- **instante de lectura y origen** (:class:`OrigenLectura`), en cada
  proyección, sin excepción (requisito 3 de la incidencia #193);
- **``autoritativo`` fijo a ``False``**, con ``init=False`` para que ningún
  llamador pueda construir una proyección marcada autoritativa por
  accidente: la garantía es estructural (imposible), no una convención que
  alguien podría olvidar (nota de arranque, pregunta 4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState


class EspejoIlegibleError(Exception):
    """Un proveedor de lectura no pudo leer: NO es lo mismo que "no hay".

    Requisito 2 de la incidencia #193: una lectura caída nunca se convierte
    silenciosamente en ausencia. Al ser una excepción -control de flujo
    distinto de devolver un valor vacío- resulta estructuralmente imposible
    que el código que orquesta la proyección confunda "leí y no había nada"
    (un valor vacío legítimo) con "no pude leer" (esta excepción).
    """

    def __init__(self, proveedor: str, motivo: str) -> None:
        self.proveedor = proveedor
        self.motivo = motivo
        super().__init__(f"{proveedor}: {motivo}")


@dataclass(frozen=True, slots=True)
class OrigenLectura:
    """Instante de lectura y procedencia de una proyección (requisito 3)."""

    fuente: str
    leido_en: datetime


@dataclass(frozen=True, slots=True)
class RondaHallazgos:
    """Un registro de ronda ``sirius-round``/``RONDA_HALLAZGOS``, interpretado.

    Espejo de ``scripts.automation.sirius_convergence.round_record``: mismos
    campos sustantivos, sin reinterpretar el significado.
    """

    numero: int
    head: str
    pendientes: int
    gravedad_total: int


@dataclass(frozen=True, slots=True)
class EventoQuality:
    """Un marcador ``<!-- sirius-quality:<head>:<conclusión> -->`` leído.

    A diferencia de ``fallos_quality_consecutivos`` -que reduce el historial a
    la racha vigente-, la secuencia completa de eventos conserva cada
    resultado observado, en el orden en que se publicó: un ciclo con fallos y
    recuperaciones queda distinguible de uno donde Quality nunca se ejecutó.
    """

    head: str
    conclusion: str


@dataclass(frozen=True, slots=True)
class VeredictoPublicado:
    """Un marcador ``<!-- sirius-verdict:<rol>:<veredicto>:<referencia> -->`` leído."""

    rol: str
    veredicto: str
    referencia: str
    publicado_en: datetime


@dataclass(frozen=True, slots=True)
class EstadoAcreditado:
    """Un estado por el que la incidencia PASÓ, probado por un marcador del historial.

    A diferencia de ``estado``/``fase`` -que son la FOTO actual, lo que las
    etiquetas vigentes proyectan-, esto es el camino: cada
    ``<!-- sirius-notification:sirius:<etiqueta>:<head>:<run> -->`` que
    ``notify-sirius-state.yml`` publica al aplicarse una etiqueta deja
    constancia fechada de que la incidencia estuvo en ese estado. El tramo
    del run lo añadió ADR-157; los historiales publicados antes traen el
    marcador sin él y se leen igual. ``head`` guarda SOLO el head -``no-head``
    cuando la incidencia todavía no tenía SHA publicado-: el run se descarta
    al leerlo, para que este campo siga siendo comparable con un SHA
    (CLAUDE-R8-001, ronda 8, PR #546). Es lo que
    permite AVANZAR el almacén del motor por transiciones ya legales cuando
    una recuperación entera ocurrió sin que ninguna pasada de reflejo la
    observara (ADR-147, incidencia #545; material de partida de la PR #540).

    La interpretación de ``etiqueta`` a ``(estado, fase)`` es exactamente la
    misma tabla que usa la foto (``mirror_projection._LABEL_STATE``): aquí no
    se reinterpreta el vocabulario, solo se aplica a otro sitio del historial.

    ``orden`` es la posición de este marcador en el historial de confianza, en
    la MISMA escala que la de :class:`PermisoDeReanudacion`: las dos las
    produce el mismo recorrido de textos, y compararlas es lo que permite
    decir "este permiso es posterior a esta parada" sin volver a mirar la foto
    (ADR-147).

    ``publicado_en`` y ``diagnostico`` son la EVIDENCIA PROPIA de esta
    ocurrencia, y existen porque la posición no la identifica: el mismo
    ``(estado, fase)`` aparece varias veces en un ciclo real, y elegir "la
    última" no demuestra que sea la que el almacén guardó (CODEX-002, ronda 2,
    PR #546). ``publicado_en`` es el instante del comentario que trae el
    marcador -``None`` cuando viene del CUERPO de la incidencia, que no tiene
    instante propio y es, por construcción, anterior a todo comentario-;
    ``diagnostico`` solo lo llevan los marcadores de ``FAILED_SAFELY`` y es lo
    que permite que cada parada del recorrido conserve SU evidencia en vez de
    heredar la de la última parada de toda la incidencia (CODEX-003, ronda 2,
    PR #546). Se empareja consumiendo en orden -cada parada notificada toma el
    diagnóstico no consumido más antiguo publicado ANTES de ella- y no por la
    posición relativa de los dos comentarios ni alineando desde el final, que
    la deduplicación del notificador desmiente (CLAUDE-R5-001, ronda 5, PR
    #546). ``None`` cuando no le toca ninguno, y entonces no se recrea ninguno.

    ``orden_del_veredicto`` es la IDENTIDAD del suceso: la posición, en el
    mismo historial de confianza, del comentario de veredicto que causó esta
    parada -el que trajo su ``diagnostico``-. Existe porque el marcador lo
    publica ``notify-sirius-state.yml``, que es asíncrono y no se serializa
    contra otras etiquetas: el aviso de una parada puede publicarse DESPUÉS
    del ``continua`` que la levantó, y entonces exigir un permiso posterior a
    la POSICIÓN DEL AVISO niega un permiso que el propietario sí escribió
    después de la parada real (CLAUDE-R4-001, ronda 4, PR #546). Con el
    veredicto —que sí es síncrono y precede siempre a su etiqueta— la
    correlación parada-permiso deja de depender de dónde cayó el aviso.
    ``None`` cuando no hay ningún veredicto atribuible: entonces se vuelve a
    ``orden``, que es lo único que hay.
    """

    etiqueta: str
    estado: WorkItemState
    fase: WorkItemPhase | None
    head: str
    orden: int
    publicado_en: datetime | None = None
    diagnostico: str | None = None
    orden_del_veredicto: int | None = None


@dataclass(frozen=True, slots=True)
class ParadaPublicada:
    """Un veredicto de PARADA publicado en el historial de confianza, con su posición.

    Es la evidencia de que el ciclo se detuvo, INDEPENDIENTE del aviso que la
    anunció: ``sirius_apply_verdict.sh`` y las puertas deterministas publican
    siempre el comentario del veredicto, mientras que el marcador
    ``sirius-notification`` lo deduplicaba ``sirius_comment_once`` por
    ``(etiqueta, head)`` -una segunda parada sobre el mismo head no dejaba
    marcador propio- en todo historial publicado ANTES de ADR-157 (fusionado
    en `main` el 07-09-2026), que desde entonces mete el run en el marcador y
    hace que cada parada deje el suyo cuando su evento de etiqueta llega a
    ejecutarse. Esta lista sigue haciendo falta para esos historiales
    antiguos, que ADR-157 declara que «conservan sus huecos», y para los
    huecos que la cola del notificador siga dejando (CODEX-001, ronda 14,
    PR #546; nota de ``_NOTIFICATION_MARKER_RE`` en
    :mod:`sirius_engine.mirror_projection`).
    Sin ella, una parada sin aviso no existe para
    :mod:`sirius_engine.reflect` y el recorrido ancla en el aviso de una
    parada ANTERIOR, cuya cota deja pasar permisos escritos antes de la
    parada real (CLAUDE-R7-001 y CLAUDE-R7-002, ronda 7, PR #546).

    ``orden`` está en la MISMA escala que el de :class:`EstadoAcreditado` y
    :class:`PermisoDeReanudacion`; ``publicado_en`` es el instante del
    comentario que la publicó (``None`` si viene del CUERPO de la incidencia,
    anterior por construcción a todo comentario), y es lo que permite
    preguntar si el almacén PUDO guardarla.
    """

    orden: int
    publicado_en: datetime | None = None


class FormaDePermiso(StrEnum):
    """Las dos formas del permiso escrito del propietario, con el mismo peso.

    Se distinguen para poder contarlas y explicarlas, no para tratarlas
    distinto: la acreditación de salir de una parada no mira la forma
    (ADR-147, decisión del propietario en #545).
    """

    #: Uno de los tres marcadores que ``sirius_resume_on_command.sh`` publica
    #: ANTES de reponer la etiqueta: el RECIBO de la máquina.
    MARCADOR = "marcador"
    #: La orden exacta ``continua`` publicada por el propietario: el PERMISO
    #: mismo. Existe como forma propia porque el recibo puede faltar
    #: estructuralmente -``sirius_comment_once`` deduplica por el texto
    #: completo del marcador, así que dos reanudaciones sobre el mismo head
    #: nunca dejan un segundo recibo (medición de #545)-.
    ORDEN = "orden"


@dataclass(frozen=True, slots=True)
class PermisoDeReanudacion:
    """Un permiso escrito del propietario para salir de una parada, con su posición.

    ``orden`` está en la MISMA escala que el de :class:`EstadoAcreditado`
    -ambos son la posición del texto que lo contiene dentro del historial de
    confianza, del más antiguo al más reciente-, y ``referencia`` guarda el
    texto exacto que lo acredita (el marcador entero, o la orden tal y como se
    normalizó) para que una divergencia se pueda explicar sin releer GitHub.
    """

    forma: FormaDePermiso
    referencia: str
    orden: int


@dataclass(frozen=True, slots=True)
class MirroredWorkItem:
    """Proyección NO-autoritativa de una incidencia de la vía GitHub.

    ``estado``/``fase`` son ``None`` cuando la incidencia no lleva ninguna
    etiqueta ``sirius:*`` reconocida -eso también es un hecho observado, no
    una ausencia de lectura-. También son ``None`` cuando lleva VARIAS
    etiquetas de estado a la vez fuera del único par de activación válido
    (``sirius:planned`` + ``sirius:implement-requested``): en ese caso
    ``etiquetas_contradictorias`` es ``True`` y expone la contradicción en
    vez de que el espejo elija una etiqueta ganadora en silencio.
    """

    work_id: str
    estado: WorkItemState | None
    fase: WorkItemPhase | None
    etiquetas: tuple[str, ...]
    etiquetas_contradictorias: bool
    cerrada: bool
    pr_url: str | None
    head_sha: str | None
    rondas: tuple[RondaHallazgos, ...]
    veredictos: tuple[VeredictoPublicado, ...]
    eventos_quality: tuple[EventoQuality, ...]
    fallos_quality_consecutivos: int
    origen: OrigenLectura
    #: El texto del último comentario de confianza que publicó un veredicto
    #: ``FAILED_SAFELY``/``USAGE_LIMIT_REACHED`` (mismo cuerpo que
    #: ``sirius_apply_verdict.sh`` escribe bajo "🔴 **Me he detenido de forma
    #: segura**"), o ``None`` si ninguno publicó uno. Es lo que C1
    #: (incidencia #529) necesita para llevar el diagnóstico real al almacén
    #: del motor cuando refleja ``sirius:failed-safely``.
    diagnostico_fallo: str | None
    #: ``True`` si el historial de confianza lleva publicado alguno de los
    #: tres marcadores que ``sirius_resume_on_command.sh`` escribe ANTES de
    #: reponer la etiqueta activa (``sirius-resume-stop``,
    #: ``sirius-convergence-reset``, ``sirius-restart-sin-pr``: líneas
    #: 297-324 de ese guion). Es el único hecho que distingue una etiqueta de
    #: parada sustituida por una orden real del propietario de una que
    #: cambió por cualquier otra vía -edición manual, una transición
    #: parcial-: sin este marcador, un cambio de etiqueta sobre un
    #: ``WorkItem`` parado no autoriza reanudar (CODEX-001, ronda 4, PR #530).
    reanudacion_publicada: bool = False
    #: Los estados que el historial DE CONFIANZA acredita, del más antiguo al
    #: más reciente, uno por marcador ``sirius-notification`` con etiqueta
    #: reconocida. Vacío cuando la incidencia no tiene ninguno -lo normal
    #: mientras el ciclo no ha cambiado de etiqueta ni una vez-, y también
    #: cuando los tiene pero ninguno es de confianza.
    historial_estados: tuple[EstadoAcreditado, ...] = ()
    #: La CRONOLOGÍA de los permisos escritos del propietario, del más antiguo
    #: al más reciente. A diferencia de ``reanudacion_publicada`` -que reduce
    #: el historial a un booleano sobre la parada más reciente-, aquí no se
    #: pierde ni el orden ni la cuenta: el recorrido acreditado los consume
    #: uno a uno, y la k-ésima salida de parada solo puede usar uno posterior
    #: a ESA parada y aún no consumido (ADR-147, incidencia #545).
    permisos_reanudacion: tuple[PermisoDeReanudacion, ...] = ()
    #: Los veredictos de PARADA publicados en el historial de confianza, del
    #: más antiguo al más reciente. A diferencia de ``historial_estados`` -que
    #: solo ve las paradas con aviso propio-, aquí están TODAS: es lo que
    #: permite al recorrido abstenerse cuando la evidencia no identifica en
    #: cuál de ellas se quedó el almacén (ADR-147, CLAUDE-R7-001).
    paradas_publicadas: tuple[ParadaPublicada, ...] = ()
    autoritativo: bool = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class MirroredRun:
    """Proyección NO-autoritativa del estado de un run de Actions."""

    run_id: str
    estado_run: str
    conclusion: str | None
    head_sha: str | None
    url: str | None
    origen: OrigenLectura
    autoritativo: bool = field(default=False, init=False)
