"""Puerto de consulta del mundo real para el barrido de recuperación (A2, arquitectura §3.5).

El barrido de recuperación (:mod:`sirius_engine.recovery`) necesita saber,
para cada ``Run`` no terminado, qué pasó de verdad mientras el motor podía
estar caído: ¿sigue vivo?, ¿terminó con éxito?, ¿falló?, ¿se perdió?, ¿se
confirmó su cancelación? Ese hecho vive fuera del almacén -en la API de
GitHub, en el estado de un proceso local, en lo que sea que ejecute el paso-
y A2 no tiene ese Adapter real (es A3 y bloques posteriores). Este puerto es
la frontera: en A2, su única implementación es un doble de pruebas.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from sirius_engine.domain.run import Run


class RemoteRunStatus(StrEnum):
    """Lo que el mundo real puede reportar sobre un ``Run`` no terminado.

    Todos los valores menos ``UNKNOWN`` son **afirmaciones sobre el Run**.
    ``UNKNOWN`` es una afirmación sobre la **lectura**, y por eso existe
    (H-2, incidencia #214, ADR-053): sin él, un observador que no pudo leer
    solo podía mentir, inventar o callar.
    """

    #: Sigue vivo y sin desenlace observable; el barrido no actúa sobre él.
    PENDING = "pending"
    #: **No se pudo observar**: la lectura del mundo falló (API caída, permiso
    #: denegado, respuesta ilegible, tiempo agotado). NO es ``PENDING``:
    #: ``PENDING`` afirma que el Run sigue vivo, y eso es justo lo que aquí no
    #: se sabe. Es el mismo principio que ADR-036 fijó para el espejo -«una
    #: lectura caída no es una ausencia»- aplicado al mundo de los Runs.
    #: Quien lo reporte debería explicar en ``diagnostico`` por qué falló la
    #: lectura: el barrido no puede saberlo.
    UNKNOWN = "unknown"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    #: Aislamiento demostrado (o desaparición) sin desenlace explícito.
    LOST = "lost"
    #: El Run tenía una cancelación pedida y el mundo confirma que terminó.
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class RunWorldObservation:
    """Lo que devuelve :meth:`RunWorldObserver.check_run` para un ``Run`` dado.

    ``resultado`` distingue dos cosas que no son la misma (H-2, ADR-053):

    - ``None`` — **no se pudo leer** el resultado. Con ``status=SUCCEEDED``
      es una observación incompleta, no un éxito: el barrido **no** cierra
      el ``Run`` con ella. Un observador que sepa que la lectura falló debe
      reportar ``UNKNOWN`` y decir por qué en ``diagnostico``.
    - Un ``Mapping`` (aunque esté vacío) — **se leyó**. ``{}`` significa que
      el Worker terminó sin devolver campos, que es un hecho.
    """

    status: RemoteRunStatus
    resultado: Mapping[str, object] | None = None
    diagnostico: str | None = None


class RunWorldObserver(Protocol):
    """Contrato que cualquier Adapter de consulta al mundo debe satisfacer.

    En A2 solo existe un doble de pruebas; la implementación real (leer la
    API de GitHub, sondear un proceso local...) es A3 y bloques posteriores.
    """

    def check_run(self, run: Run, *, now: datetime) -> RunWorldObservation:
        """Preguntar al mundo real qué pasó con ``run`` desde su último ``STATUS`` conocido.

        Si la consulta falla, la respuesta correcta es
        ``RunWorldObservation(status=RemoteRunStatus.UNKNOWN, diagnostico=...)``.
        No lo es ``PENDING`` (afirma que el Run sigue vivo) ni ``LOST``
        (afirma que se demostró su aislamiento): un fallo de lectura no es
        un hecho sobre el Run.
        """
        ...
