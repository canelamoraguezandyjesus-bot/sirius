"""Lo que un modelo local puede inferir de una pregunta (ADR-164, palanca 1
de ADR-148).

Valor puro y cerrado: los cinco campos que la ``Peticion`` del motor por
etapas (``sirius.domain.staged_engine_contracts``) recibe de la pregunta
misma —modo, cardinalidad, límite, tiempo objetivo y corte de registro—, y
ninguno más. El permiso y el propósito NO están aquí a propósito: son reglas
del producto y no pueden depender de lo que un modelo crea entender de la
frase (ADR-164, «Decisión»).

Ningún campo es obligatorio salvo el modo y la cardinalidad: un ``None`` no
significa «el modelo se equivocó», sino «la pregunta no lo declara», y el
intérprete lo traduce al mismo valor que la política uniforme de hoy ya usa
(sin límite que ate, tiempo objetivo «ahora», sin corte de registro).
"""

from __future__ import annotations

from dataclasses import dataclass

from sirius.domain.staged_engine_contracts import Cardinalidad, Modo

__all__ = ["IntencionDeConsulta"]


@dataclass(frozen=True, slots=True)
class IntencionDeConsulta:
    """Lo inferido de una consulta, antes de convertirse en ``Peticion``."""

    modo: Modo
    cardinalidad: Cardinalidad
    #: Cuántos elementos pide la consulta («dame tres…»). ``None`` = no lo
    #: declara, y el intérprete usa un límite que no ata.
    limite: int | None = None
    #: Instante al que se refiere la pregunta, ISO-8601. ``None`` = «ahora».
    tiempo_objetivo: str | None = None
    #: «Qué sabía yo el …», ISO-8601. ``None`` = sin corte.
    corte_de_registro: str | None = None
