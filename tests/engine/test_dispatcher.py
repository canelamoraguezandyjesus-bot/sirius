"""Despachador C2: orden enlazada, sin arranque doble, escritura mínima (incidencia #240).

Cubre C2-P1, C2-P3, C2-P4 y C2-P6. C2-P2 (el cuerpo pasa el validador real)
vive en ``test_issue_body_projection.py``; C2-P5 (credencial temprana) en
``test_github_cli_writer.py`` -cada prueba de terminado vive donde su
comprobación es más directa, en vez de todas repetidas en un único fichero.
"""

from __future__ import annotations

import dataclasses
import inspect
import threading
from datetime import UTC, datetime

import pytest

from sirius_engine.adapters.memory_dispatch_journal import InMemoryDispatchJournal
from sirius_engine.dispatcher import (
    ETIQUETA_ACTIVACION,
    ETIQUETA_INICIAL,
    DispatchOutcome,
    dispatch_work_item,
)
from sirius_engine.domain.dispatch import MARCADOR_ORDEN_PROPIETARIO, DispatchEpisode
from sirius_engine.domain.errors import (
    ClaseNoDespachableError,
    EstadoNoDespachableError,
    OrdenNoEnlazadaError,
)
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, WorkItemState, create_work_item
from sirius_engine.ports.dispatch_journal import Reserva
from sirius_engine.ports.github_writer import IncidenciaCreada
from sirius_engine.profile_field import ProfileRef

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
PERFIL = ProfileRef(ref="implementer", version=1)
ORDEN = f"{MARCADOR_ORDEN_PROPIETARIO}https://github.com/acme/repo/issues/241#issuecomment-1"


def _work_item(
    *,
    work_id: str = "WI-C2-0001",
    evidencia: tuple[str, ...] = (),
    clase: WorkItemClass = WorkItemClass.PROGRAMACION,
    estado: WorkItemState = WorkItemState.ACTIVE,
) -> WorkItem:
    """Un ``WorkItem`` de programación **activo** por defecto: el único estado despachable.

    ``create_work_item`` nace en ``PLANNED`` (§3.2), pero el flujo real
    (``work_intake.aplicar_decision``, rama ``CREAR_Y_ACTIVAR``) siempre
    activa antes de que nada pueda despacharlo; construir aquí directamente
    con ``estado`` como parámetro -en vez de pasar por el almacén- sigue el
    mismo criterio que ya fijó ADR-062 para ``evidencia``: determinista, sin
    E/S, comprobable con ``dataclasses.replace``.
    """
    base = create_work_item(
        work_id=work_id,
        peticion_original="implementa el despachador",
        objetivo="objetivo de prueba con longitud suficiente para el validador real de verdad",
        contexto_origen=("incidencia:240",),
        entregable="entregable de prueba con longitud suficiente para el validador real de verdad",
        criterio_terminado="criterio de prueba con longitud suficiente para el validador real",
        limites={},
        prioridad=1,
        clase=clase,
        now=NOW,
        plan=("preparar",),
    )
    return dataclasses.replace(base, evidencia=evidencia, estado=estado)


@dataclasses.dataclass
class _EscritorSoloVerbosEnumerados:
    """Doble que registra las llamadas a los DOS verbos enumerados y falla ante cualquier otro.

    ``__getattr__`` solo se dispara para atributos que la clase no define
    explícitamente -``crear_incidencia`` y ``aplicar_etiqueta`` no lo
    activan nunca-, así que cualquier tercer verbo que el despachador
    intentara (comentar, cerrar, editar, tocar una PR) cae aquí (C2-P4).
    """

    llamadas: list[tuple[str, dict[str, object]]] = dataclasses.field(default_factory=list)
    siguiente_numero: int = 241

    def crear_incidencia(
        self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
    ) -> IncidenciaCreada:
        self.llamadas.append(
            (
                "crear_incidencia",
                {"repo": repo, "titulo": titulo, "cuerpo": cuerpo, "etiquetas": etiquetas},
            )
        )
        return IncidenciaCreada(
            numero=self.siguiente_numero, url=f"https://x/{self.siguiente_numero}"
        )

    def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
        self.llamadas.append(
            ("aplicar_etiqueta", {"repo": repo, "numero": numero, "etiqueta": etiqueta})
        )

    def __getattr__(self, nombre: str) -> object:
        raise AssertionError(
            f"verbo de escritura no enumerado: {nombre!r} (alcance permitido #240)"
        )


def test_c2_p1_sin_orden_enlazada_no_aplica_la_etiqueta() -> None:
    work_item = _work_item(evidencia=())
    writer = _EscritorSoloVerbosEnumerados()
    journal = InMemoryDispatchJournal()

    with pytest.raises(OrdenNoEnlazadaError):
        dispatch_work_item(
            work_item,
            writer=writer,
            journal=journal,
            repo="acme/repo",
            profile_ref=PERFIL,
            bloque="C2",
            now=NOW,
        )

    assert writer.llamadas == []
    assert journal.episodes() == ()


def test_c2_p1_con_orden_enlazada_si_aplica_la_etiqueta() -> None:
    work_item = _work_item(evidencia=(ORDEN,))
    writer = _EscritorSoloVerbosEnumerados()
    journal = InMemoryDispatchJournal()

    resultado = dispatch_work_item(
        work_item,
        writer=writer,
        journal=journal,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )

    assert resultado.ya_despachado is False
    assert resultado.episodio.numero_incidencia == 241
    assert resultado.episodio.etiqueta == ETIQUETA_ACTIVACION
    verbos = [nombre for nombre, _ in writer.llamadas]
    assert verbos == ["crear_incidencia", "aplicar_etiqueta"]
    _, args_etiqueta = writer.llamadas[1]
    assert args_etiqueta["etiqueta"] == ETIQUETA_ACTIVACION
    assert args_etiqueta["numero"] == 241


def test_c2_p3_dos_pasadas_producen_una_sola_activacion() -> None:
    work_item = _work_item(evidencia=(ORDEN,))
    writer = _EscritorSoloVerbosEnumerados()
    journal = InMemoryDispatchJournal()

    primero = dispatch_work_item(
        work_item,
        writer=writer,
        journal=journal,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )
    segundo = dispatch_work_item(
        work_item,
        writer=writer,
        journal=journal,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )

    assert primero.ya_despachado is False
    assert segundo.ya_despachado is True
    assert segundo.episodio == primero.episodio
    # Solo dos llamadas en total: las de la PRIMERA pasada. La segunda no
    # repitió ninguna escritura.
    assert len(writer.llamadas) == 2


def test_c2_p4_la_escritura_es_exactamente_la_enumerada() -> None:
    work_item = _work_item(evidencia=(ORDEN,))
    writer = _EscritorSoloVerbosEnumerados()
    journal = InMemoryDispatchJournal()

    dispatch_work_item(
        work_item,
        writer=writer,
        journal=journal,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )

    assert {nombre for nombre, _ in writer.llamadas} == {"crear_incidencia", "aplicar_etiqueta"}
    # La primera escritura aplica exactamente la etiqueta inicial de la
    # plantilla real, nunca la de activación directamente.
    _, args_creacion = writer.llamadas[0]
    assert args_creacion["etiquetas"] == (ETIQUETA_INICIAL,)


def test_c2_p6_el_episodio_se_reconstruye_del_diario_sin_github() -> None:
    work_item = _work_item(work_id="WI-C2-RECONSTRUYE", evidencia=(ORDEN,))
    writer = _EscritorSoloVerbosEnumerados()
    journal = InMemoryDispatchJournal()

    dispatch_work_item(
        work_item,
        writer=writer,
        journal=journal,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )

    # Un lector que solo tiene el diario -nunca ``writer``, nunca GitHub-
    # puede reconstruir el episodio completo.
    (episodio,) = journal.episodes()
    assert episodio.work_id == "WI-C2-RECONSTRUYE"
    assert episodio.orden_enlazada == ORDEN[len(MARCADOR_ORDEN_PROPIETARIO) :]
    assert episodio.repo == "acme/repo"
    assert episodio.numero_incidencia == 241
    assert episodio.etiqueta == ETIQUETA_ACTIVACION
    assert episodio.recorded_at == NOW


def test_clase_distinta_de_programacion_no_se_despacha() -> None:
    work_item = _work_item(evidencia=(ORDEN,), clase=WorkItemClass.AUDITORIA)
    writer = _EscritorSoloVerbosEnumerados()
    journal = InMemoryDispatchJournal()

    with pytest.raises(ClaseNoDespachableError):
        dispatch_work_item(
            work_item,
            writer=writer,
            journal=journal,
            repo="acme/repo",
            profile_ref=PERFIL,
            bloque="C2",
            now=NOW,
        )
    assert writer.llamadas == []


# --- Revisión de la incidencia #240, ronda 2 -----------------------------


@pytest.mark.parametrize(
    "estado",
    [
        WorkItemState.PLANNED,
        WorkItemState.WAITING,
        WorkItemState.NEEDS_DECISION,
        WorkItemState.PAUSED,
        WorkItemState.FAILED_SAFELY,
        WorkItemState.CANCELLED,
        WorkItemState.DELIVERED,
    ],
)
def test_estado_no_activo_no_se_despacha(estado: WorkItemState) -> None:
    """CODEX-004: una referencia de orden que sobrevive a la cancelación no revive el trabajo."""
    work_item = dataclasses.replace(_work_item(evidencia=(ORDEN,)), estado=estado)
    writer = _EscritorSoloVerbosEnumerados()
    journal = InMemoryDispatchJournal()

    with pytest.raises(EstadoNoDespachableError):
        dispatch_work_item(
            work_item,
            writer=writer,
            journal=journal,
            repo="acme/repo",
            profile_ref=PERFIL,
            bloque="C2",
            now=NOW,
        )

    assert writer.llamadas == []
    assert journal.episodes() == ()
    # La reserva no queda en pie: un reintento posterior puede volver a obtenerla.
    assert journal.reservar(work_item.work_id).obtenida is True


def test_etiqueta_no_es_un_parametro_configurable() -> None:
    """CODEX-002: contrato §12.1 solo autoriza ``ETIQUETA_ACTIVACION``; no hay forma de variarla."""
    parametros = inspect.signature(dispatch_work_item).parameters
    assert "etiqueta" not in parametros

    with pytest.raises(TypeError):
        dispatch_work_item(  # type: ignore[call-arg]
            _work_item(evidencia=(ORDEN,)),
            writer=_EscritorSoloVerbosEnumerados(),
            journal=InMemoryDispatchJournal(),
            repo="acme/repo",
            profile_ref=PERFIL,
            bloque="C2",
            now=NOW,
            etiqueta="sirius:repair-requested",
        )


@dataclasses.dataclass
class _DiarioQueSenalaReservaEnCurso:
    """Envuelve :class:`InMemoryDispatchJournal` y señala cuándo una llamada
    concurrente a ``reservar`` encuentra la reserva de otra todavía en curso
    -sin episodio grabado-.

    Arrancar el hilo B no basta para garantizar que haya ejecutado
    ``reservar()`` antes de liberar al hilo A: si el planificador reanuda
    primero a A, este puede grabar el episodio antes de que B reserve, y B
    tomaría entonces la ruta de "ya despachado" en vez de la ruta de
    "esperar la reserva en curso" -la que esta prueba necesita ejercitar
    (revisión de la incidencia #240, ronda 3, CODEX-001)-. Esta señal deja
    esperar de forma determinista a que B haya llegado a ``reservar()``
    mientras A sigue bloqueado, sin tocar el despachador de producción.
    """

    _delegate: InMemoryDispatchJournal
    reserva_en_curso_detectada: threading.Event

    def episode_for(self, work_id: str) -> DispatchEpisode | None:
        return self._delegate.episode_for(work_id)

    def record(self, episode: DispatchEpisode) -> None:
        self._delegate.record(episode)

    def episodes(self) -> tuple[DispatchEpisode, ...]:
        return self._delegate.episodes()

    def reservar(self, work_id: str) -> Reserva:
        reserva = self._delegate.reservar(work_id)
        if not reserva.obtenida and reserva.episodio is None:
            self.reserva_en_curso_detectada.set()
        return reserva

    def liberar(self, work_id: str) -> None:
        self._delegate.liberar(work_id)


def test_dos_hilos_concurrentes_para_el_mismo_work_id_producen_una_sola_activacion() -> None:
    """CODEX-003: la reserva atómica decide, sin intercalado, cuál hilo escribe.

    Reproduce exactamente la intercalación del hallazgo: los dos hilos
    llegan a ``episode_for``/``reservar`` para el mismo ``work_id`` antes de
    que ninguno haya escrito nada. El hilo B se libera solo DESPUÉS de que el
    hilo A ya obtuvo la reserva (``a_en_curso``) Y de que el hilo B ya
    intentó reservar y encontró la de A en curso (``reserva_en_curso_detectada``,
    CODEX-001) -pero A sigue escribiendo en GitHub (bloqueado en
    ``continuar``)-: es el hueco donde, sin la reserva atómica, ``episode_for``
    seguía devolviendo ``None`` para B. Con la reserva, B tiene que esperar el
    episodio de A en vez de escribir el suyo.
    """
    work_item = _work_item(evidencia=(ORDEN,))
    reserva_en_curso_detectada = threading.Event()
    journal = _DiarioQueSenalaReservaEnCurso(InMemoryDispatchJournal(), reserva_en_curso_detectada)
    a_en_curso = threading.Event()
    continuar = threading.Event()

    class _EscritorDeAQueBloqueaHastaSenal(_EscritorSoloVerbosEnumerados):
        def crear_incidencia(
            self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
        ) -> IncidenciaCreada:
            a_en_curso.set()
            assert continuar.wait(timeout=5)
            return super().crear_incidencia(
                repo=repo, titulo=titulo, cuerpo=cuerpo, etiquetas=etiquetas
            )

    writer = _EscritorDeAQueBloqueaHastaSenal()
    resultados: list[DispatchOutcome | None] = [None, None]

    def _despachar(indice: int) -> None:
        resultados[indice] = dispatch_work_item(
            work_item,
            writer=writer,
            journal=journal,
            repo="acme/repo",
            profile_ref=PERFIL,
            bloque="C2",
            now=NOW,
        )

    hilo_a = threading.Thread(target=_despachar, args=(0,))
    hilo_a.start()
    assert a_en_curso.wait(timeout=5)

    hilo_b = threading.Thread(target=_despachar, args=(1,))
    hilo_b.start()
    assert reserva_en_curso_detectada.wait(timeout=5)

    continuar.set()
    hilo_a.join(timeout=5)
    hilo_b.join(timeout=5)
    assert not hilo_a.is_alive()
    assert not hilo_b.is_alive()

    # Solo el hilo A escribió: dos llamadas en total, nunca cuatro.
    assert len(writer.llamadas) == 2
    verbos = [nombre for nombre, _ in writer.llamadas]
    assert verbos == ["crear_incidencia", "aplicar_etiqueta"]
    primero, segundo = resultados
    assert primero is not None
    assert segundo is not None
    assert primero.episodio == segundo.episodio
    assert {primero.ya_despachado, segundo.ya_despachado} == {True, False}
