"""Episodio de despacho end-to-end por la vía GitHub (C2, incidencia #240, contrato §12.1).

El contrato autoriza al motor a aplicar ``sirius:implement-requested``
**solo** si existe una orden explícita del propietario, registrada y
**enlazada en la evidencia** del ``WorkItem`` (§12.1, sin excepción). Este
módulo define esa referencia -un prefijo reconocible dentro de
``WorkItem.evidencia``, arquitectura §3.1: "referencias al diario y a
artefactos"- y el episodio append-only que registra qué orden, qué
WorkItem, qué incidencia, qué etiqueta y cuándo (mismo criterio que
:class:`~sirius_engine.domain.supervision.SupervisionEpisode` en C1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius_engine.domain.work_item import WorkItem

#: Prefijo que marca, dentro de ``WorkItem.evidencia``, la referencia a la
#: orden explícita del propietario que autoriza el despacho. Una entrada
#: típica: ``"orden-propietario:issue#241#comentario-987654321"`` o
#: ``"orden-propietario:https://github.com/.../issues/241#issuecomment-987654321"``
#: -cualquier referencia estable y comprobable a dónde quedó registrada la
#: orden. Sin una entrada con este prefijo, el motor no tiene nada que
#: señalar como orden, y por tanto no despacha nada
#: (:func:`sirius_engine.dispatcher.dispatch_work_item`).
MARCADOR_ORDEN_PROPIETARIO = "orden-propietario:"


def orden_enlazada(work_item: WorkItem) -> str | None:
    """La referencia de la orden del propietario enlazada en ``evidencia``, si la hay.

    ``None`` si ``evidencia`` no contiene ninguna entrada con
    :data:`MARCADOR_ORDEN_PROPIETARIO`, o si la entrada existe pero no deja
    ninguna referencia tras el marcador -una entrada vacía "vale" tan poco
    como su ausencia; ninguna de las dos es una orden enlazada de verdad-.
    """
    for entrada in work_item.evidencia:
        if entrada.startswith(MARCADOR_ORDEN_PROPIETARIO):
            referencia = entrada[len(MARCADOR_ORDEN_PROPIETARIO) :].strip()
            if referencia:
                return referencia
    return None


@dataclass(frozen=True, slots=True)
class DispatchEpisode:
    """El episodio completo de una activación del despachador C2.

    Vive en su propio diario append-only
    (:mod:`sirius_engine.ports.dispatch_journal`), hermano de
    :class:`~sirius_engine.domain.supervision.SupervisionEpisode`: mismo
    criterio de separación respecto al diario de eventos del
    ``WorkEngineStore`` -ese diario modela transiciones tipadas de
    ``WorkItem``/``Run``, y no tiene sitio para "qué orden" ni "qué
    incidencia de GitHub" nació de esta activación.
    """

    work_id: str
    orden_enlazada: str
    repo: str
    numero_incidencia: int
    etiqueta: str
    recorded_at: datetime
