"""Despachador end-to-end de programación por la vía GitHub (C2, incidencia #240).

Cierra el círculo del propietario-no-mensajero para la clase
``programacion``: la puerta de intención de A5 ya creó y activó el
``WorkItem`` (:mod:`sirius_engine.work_intake`); :func:`dispatch_work_item`
es lo que aplica la vía GitHub -genera el cuerpo desde la plantilla
(:mod:`sirius_engine.issue_body_projection`, proyección del WorkPackage y el
``Perfil:`` de A4) y aplica la etiqueta de activación con la identidad del
motor- sin que el propietario toque GitHub.

Dos guardas, comprobadas en este orden y por la misma razón que
:func:`sirius_engine.supervisor.supervise_runs` las ordena así:

1. **Idempotencia (C2-P3).** Si :class:`~sirius_engine.ports.dispatch_journal.DispatchJournal`
   ya tiene un episodio para este ``work_id``, se devuelve ESE episodio sin
   escribir nada más: dos pasadas sobre el mismo WorkItem producen una sola
   activación. Se comprueba primero, antes de cualquier otra guarda, para
   que ni siquiera un ``work_item`` que ya no cumpliera las guardas
   siguientes (por ejemplo, si su clase cambiara) pueda invalidar un
   episodio ya registrado.
2. **Orden enlazada (C2-P1, contrato §12.1, sin excepción).** Sin una
   referencia reconocible en ``work_item.evidencia``
   (:func:`sirius_engine.domain.dispatch.orden_enlazada`), el motor no
   arranca nada: se levanta
   :class:`~sirius_engine.domain.errors.OrdenNoEnlazadaError` en vez de
   proyectar o escribir cualquier cosa.

La escritura es exactamente la enumerada por
:class:`~sirius_engine.ports.github_writer.GitHubWriterPort` (C2-P4): crear
la incidencia, aplicar la etiqueta. Ninguna otra llamada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sirius_engine.domain.dispatch import DispatchEpisode, orden_enlazada
from sirius_engine.domain.errors import ClaseNoDespachableError, OrdenNoEnlazadaError
from sirius_engine.domain.work_item import WorkItem, WorkItemClass
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
    etiqueta: str = ETIQUETA_ACTIVACION,
    base_branch: str = "main",
) -> DispatchOutcome:
    """Despachar ``work_item`` por la vía GitHub, si no se despachó ya.

    Determinista en sus guardas (mismo ``work_item``/diario -> misma
    decisión); la única E/S es exactamente la enumerada por
    :class:`~sirius_engine.ports.github_writer.GitHubWriterPort`.
    """
    episodio_previo = journal.episode_for(work_item.work_id)
    if episodio_previo is not None:
        return DispatchOutcome(
            work_id=work_item.work_id, ya_despachado=True, episodio=episodio_previo
        )

    if work_item.clase is not WorkItemClass.PROGRAMACION:
        raise ClaseNoDespachableError(work_item.work_id, work_item.clase.value)

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
    writer.aplicar_etiqueta(repo=repo, numero=creada.numero, etiqueta=etiqueta)

    episodio = DispatchEpisode(
        work_id=work_item.work_id,
        orden_enlazada=referencia_orden,
        repo=repo,
        numero_incidencia=creada.numero,
        etiqueta=etiqueta,
        recorded_at=now,
    )
    journal.record(episodio)
    return DispatchOutcome(work_id=work_item.work_id, ya_despachado=False, episodio=episodio)
