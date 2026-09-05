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
    ``<!-- sirius-notification:sirius:<etiqueta>:<head> -->`` que
    ``notify-sirius-state.yml`` publica al aplicarse una etiqueta deja
    constancia fechada de que la incidencia estuvo en ese estado. Es lo que
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
    """

    etiqueta: str
    estado: WorkItemState
    fase: WorkItemPhase | None
    head: str
    orden: int


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
