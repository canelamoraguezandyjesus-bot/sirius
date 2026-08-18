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
