"""ContextFragment: fragmento de contexto que puede viajar en un WorkerRequest (arquitectura §4.1).

La clasificación es obligatoria como dato -``None`` es un valor legítimo del
campo, que significa "sin clasificar"- porque alimenta la política de egress
de :mod:`sirius_engine.egress` (§6.1): un fragmento no se autoclasifica solo
con redactarlo, así que este tipo nunca infiere ``clasificacion`` a partir de
``contenido``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

#: "privado" = contexto interno del repositorio/incidencia, nunca sale del
#: perímetro; "exportable" = puede viajar a un Worker con red externa
#: concedida (§6.1 regla 3).
Clasificacion = Literal["privado", "exportable"]


@dataclass(frozen=True, slots=True)
class ContextFragment:
    """Un fragmento de contexto con procedencia y clasificación (WorkPackage §4.1)."""

    contenido: str
    procedencia: str
    clasificacion: Clasificacion | None
