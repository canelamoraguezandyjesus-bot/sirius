"""Despachador C2: orden enlazada, sin arranque doble, escritura mínima (incidencia #240).

Cubre C2-P1, C2-P3, C2-P4 y C2-P6. C2-P2 (el cuerpo pasa el validador real)
vive en ``test_issue_body_projection.py``; C2-P5 (credencial temprana) en
``test_github_cli_writer.py`` -cada prueba de terminado vive donde su
comprobación es más directa, en vez de todas repetidas en un único fichero.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from sirius_engine.adapters.memory_dispatch_journal import InMemoryDispatchJournal
from sirius_engine.dispatcher import ETIQUETA_ACTIVACION, ETIQUETA_INICIAL, dispatch_work_item
from sirius_engine.domain.dispatch import MARCADOR_ORDEN_PROPIETARIO
from sirius_engine.domain.errors import ClaseNoDespachableError, OrdenNoEnlazadaError
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, create_work_item
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
) -> WorkItem:
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
    return dataclasses.replace(base, evidencia=evidencia)


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
