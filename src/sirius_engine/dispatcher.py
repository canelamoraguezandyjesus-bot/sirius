"""Despachador end-to-end de programación por la vía GitHub (C2, incidencia #240).

Cierra el círculo del propietario-no-mensajero para la clase
``programacion``: la puerta de intención de A5 ya creó y activó el
``WorkItem`` (:mod:`sirius_engine.work_intake`); :func:`dispatch_work_item`
es lo que aplica la vía GitHub -genera el cuerpo desde la plantilla
(:mod:`sirius_engine.issue_body_projection`, proyección del WorkPackage y el
``Perfil:`` de A4) y aplica la etiqueta de activación con la identidad del
motor- sin que el propietario toque GitHub.

Cuatro guardas, comprobadas en este orden y por la misma razón que
:func:`sirius_engine.supervisor.supervise_runs` las ordena así:

1. **Idempotencia y concurrencia (C2-P3, revisión #240 ronda 2).** La
   reserva atómica de :class:`~sirius_engine.ports.dispatch_journal.DispatchJournal`
   decide, sin intercalado posible, cuál de dos llamadas concurrentes para
   el mismo ``work_id`` escribe: si ya hay un episodio registrado, se
   devuelve ESE episodio; si otra llamada tiene la reserva en curso, se
   espera a que termine y se reutiliza su resultado; solo si ninguna de
   las dos cosas ocurre se obtiene el derecho de escribir. Se comprueba
   primero, antes de cualquier otra guarda, para que ni siquiera un
   ``work_item`` que ya no cumpliera las guardas siguientes (por ejemplo,
   si su clase cambiara) pueda invalidar un episodio ya registrado.
2. **Clase despachable.** Solo ``WorkItemClass.PROGRAMACION`` se despacha
   aquí; cualquier otra clase levanta
   :class:`~sirius_engine.domain.errors.ClaseNoDespachableError`.
3. **Estado activo (revisión #240 ronda 2).** Solo un ``WorkItem`` en
   ``WorkItemState.ACTIVE`` puede despacharse: uno cancelado, pausado,
   escalado o ya entregado levanta
   :class:`~sirius_engine.domain.errors.EstadoNoDespachableError`, aunque
   conserve una referencia de orden en su evidencia.
4. **Orden enlazada (C2-P1, contrato §12.1, sin excepción).** Sin una
   referencia reconocible en ``work_item.evidencia``
   (:func:`sirius_engine.domain.dispatch.orden_enlazada`), el motor no
   arranca nada: se levanta
   :class:`~sirius_engine.domain.errors.OrdenNoEnlazadaError` en vez de
   proyectar o escribir cualquier cosa.

Cualquier guarda 2-4 que falle libera la reserva de la guarda 1
(:meth:`~sirius_engine.ports.dispatch_journal.DispatchJournal.liberar`)
antes de propagar el error, para que una reserva rechazada no deje a una
llamada concurrente esperando un episodio que nunca se va a grabar.

La escritura es exactamente la enumerada por
:class:`~sirius_engine.ports.github_writer.GitHubWriterPort` (C2-P4): crear
la incidencia, aplicar la etiqueta. Ninguna otra llamada. La etiqueta
aplicada es siempre :data:`ETIQUETA_ACTIVACION` -contrato §12.1 no autoriza
transportar ninguna otra-: no es un parámetro que un llamador pueda variar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius_engine.domain.dispatch import DispatchEpisode, orden_enlazada
from sirius_engine.domain.errors import (
    ClaseNoDespachableError,
    EstadoNoDespachableError,
    OrdenNoEnlazadaError,
)
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, WorkItemState
from sirius_engine.issue_body_projection import generar_cuerpo_incidencia
from sirius_engine.ports.dispatch_journal import DispatchJournal
from sirius_engine.ports.github_writer import GitHubWriterPort
from sirius_engine.profile_field import ProfileRef

#: La misma etiqueta que el propietario aplicaría a mano (contrato §12.1):
#: sin atajos ni caminos privilegiados.
ETIQUETA_ACTIVACION = "sirius:implement-requested"

#: La etiqueta con la que nace toda incidencia de trabajo real (misma
#: plantilla: ``.github/ISSUE_TEMPLATE/sirius-work-item.yml`` la aplica de
#: entrada).
ETIQUETA_INICIAL = "sirius:planned"


@dataclass(frozen=True, slots=True)
class DispatchOutcome:
    """El resultado de pedir el despacho de ``work_id``: nuevo o ya conocido."""

    work_id: str
    ya_despachado: bool
    episodio: DispatchEpisode


def dispatch_work_item(
    work_item: WorkItem,
    *,
    writer: GitHubWriterPort,
    journal: DispatchJournal,
    repo: str,
    profile_ref: ProfileRef,
    bloque: str,
    now: datetime,
    base_branch: str = "main",
) -> DispatchOutcome:
    """Despachar ``work_item`` por la vía GitHub, si no se despachó ya.

    Determinista en sus guardas (mismo ``work_item``/diario -> misma
    decisión) incluso bajo concurrencia (la reserva del diario decide, sin
    intercalado posible, cuál llamada escribe); la única E/S es exactamente
    la enumerada por :class:`~sirius_engine.ports.github_writer.GitHubWriterPort`.
    """
    reserva = journal.reservar(work_item.work_id)
    if reserva.episodio is not None:
        return DispatchOutcome(
            work_id=work_item.work_id, ya_despachado=True, episodio=reserva.episodio
        )
    if not reserva.obtenida:
        assert reserva.evento is not None
        reserva.evento.wait()
        return dispatch_work_item(
            work_item,
            writer=writer,
            journal=journal,
            repo=repo,
            profile_ref=profile_ref,
            bloque=bloque,
            now=now,
            base_branch=base_branch,
        )

    try:
        if work_item.clase is not WorkItemClass.PROGRAMACION:
            raise ClaseNoDespachableError(work_item.work_id, work_item.clase.value)

        if work_item.estado is not WorkItemState.ACTIVE:
            raise EstadoNoDespachableError(work_item.work_id, work_item.estado.value)

        referencia_orden = orden_enlazada(work_item)
        if referencia_orden is None:
            raise OrdenNoEnlazadaError(work_item.work_id)

        cuerpo = generar_cuerpo_incidencia(
            work_item, profile_ref=profile_ref, bloque=bloque, base_branch=base_branch
        )
        titulo = f"[SIRIUS] {bloque} — {work_item.objetivo.strip()[:80]}"
        creada = writer.crear_incidencia(
            repo=repo, titulo=titulo, cuerpo=cuerpo, etiquetas=(ETIQUETA_INICIAL,)
        )
        writer.aplicar_etiqueta(repo=repo, numero=creada.numero, etiqueta=ETIQUETA_ACTIVACION)

        episodio = DispatchEpisode(
            work_id=work_item.work_id,
            orden_enlazada=referencia_orden,
            repo=repo,
            numero_incidencia=creada.numero,
            etiqueta=ETIQUETA_ACTIVACION,
            recorded_at=now,
        )
        journal.record(episodio)
    except BaseException:
        journal.liberar(work_item.work_id)
        raise
    return DispatchOutcome(work_id=work_item.work_id, ya_despachado=False, episodio=episodio)
