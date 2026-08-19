"""Validador de egress fail-closed, por fragmento (arquitectura §6.1 regla 4).

Dos comprobaciones independientes, ninguna con excepciones:

1. Un fragmento SIN clasificar (``clasificacion is None``) impide arrancar el
   Run siempre -la clasificación es un dato obligatorio del WorkPackage
   (arquitectura §4.1: "clasificación obligatoria: alimenta 6.1").
2. Cuando el perfil tiene red externa concedida, cada fragmento debe estar
   clasificado como ``"exportable"`` -nunca ``"privado"``-, porque ese
   contexto va a salir del perímetro (§6.1 regla 2: "todo contexto que viaja
   a un Worker con red externa pasa por ExportSafeBrief").

No advierte ni degrada: lanza antes de que exista ningún ``WorkerRequest``
(incidencia #202, A4-P3).
"""

from __future__ import annotations

from collections.abc import Iterable

from sirius_engine.domain.context_fragment import ContextFragment
from sirius_engine.domain.errors import EgressClassificationError


def validar_egress_fail_closed(*, fragmentos: Iterable[ContextFragment], red: bool) -> None:
    """Lanzar :class:`EgressClassificationError` ante el primer fragmento inseguro."""
    for fragmento in fragmentos:
        if fragmento.clasificacion is None:
            raise EgressClassificationError(fragmento.procedencia, motivo="sin clasificar")
        if red and fragmento.clasificacion != "exportable":
            raise EgressClassificationError(
                fragmento.procedencia,
                motivo="clasificado como 'privado' pero el perfil tiene red externa concedida",
            )
