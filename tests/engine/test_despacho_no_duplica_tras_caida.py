"""H-29 (auditoría #396): una caída entre el efecto en GitHub y el episodio
durable no puede duplicar la incidencia al reintentar.

La reproducción es la del informe, contada por ESCRITURAS del escritor falso:
el primer intento crea la incidencia y muere antes de grabar el episodio (aquí:
al aplicar la etiqueta, o justo después); el proceso «se reinicia» —el diario
durable se RECARGA desde su fichero, como haría un proceso nuevo— y se
reintenta el mismo ``work_id``. Sin la intención durable y la adopción, el
segundo intento creaba OTRA incidencia.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius_engine.adapters.durable.dispatch_journal import DurableDispatchJournal
from sirius_engine.dispatcher import DispatchOutcome, dispatch_work_item
from sirius_engine.domain.dispatch import MARCADOR_ORDEN_PROPIETARIO
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, create_work_item
from sirius_engine.ports.github_writer import IncidenciaCreada
from sirius_engine.profile_field import ProfileRef

_AHORA = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
_PERFIL = ProfileRef(ref="implementer", version=1)


_ORDEN = f"{MARCADOR_ORDEN_PROPIETARIO}https://github.com/acme/repo/issues/1#issuecomment-1"


def _work_item() -> WorkItem:
    base = create_work_item(
        work_id="WI-H29",
        peticion_original="orden",
        objetivo="objetivo de prueba con longitud suficiente para el validador real",
        contexto_origen=("incidencia:1",),
        entregable="entregable",
        criterio_terminado="criterio",
        limites={},
        prioridad=1,
        clase=WorkItemClass.PROGRAMACION,
        now=_AHORA,
    ).activate(now=_AHORA)
    return dataclasses.replace(base, evidencia=(_ORDEN,))


class _EscritorConCaida:
    """Crea de verdad (cuenta la escritura) y muere al aplicar la etiqueta."""

    def __init__(self) -> None:
        self.creadas: list[str] = []
        self.etiquetadas: list[tuple[int, str]] = []
        self.busquedas: list[str] = []
        self.falla_al_etiquetar = True
        self._siguiente = 100

    def crear_incidencia(
        self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
    ) -> IncidenciaCreada:
        self._siguiente += 1
        self.creadas.append(cuerpo)
        return IncidenciaCreada(
            numero=self._siguiente, url=f"https://github.com/{repo}/issues/{self._siguiente}"
        )

    def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
        if self.falla_al_etiquetar:
            raise ConnectionError("la red murió después de crear y antes de grabar")
        self.etiquetadas.append((numero, etiqueta))

    def buscar_incidencia_por_work_id(self, *, repo: str, work_id: str) -> IncidenciaCreada | None:
        self.busquedas.append(work_id)
        for indice, cuerpo in enumerate(self.creadas, start=101):
            if f"## Work ID\n\n{work_id}" in cuerpo:
                return IncidenciaCreada(
                    numero=indice, url=f"https://github.com/{repo}/issues/{indice}"
                )
        return None


def _despachar(journal: DurableDispatchJournal, escritor: _EscritorConCaida) -> DispatchOutcome:
    return dispatch_work_item(
        _work_item(),
        writer=escritor,
        journal=journal,
        repo="acme/repo",
        profile_ref=_PERFIL,
        bloque="H29",
        now=_AHORA,
    )


def test_h29_una_caida_tras_crear_no_duplica_al_reintentar(tmp_path: Path) -> None:
    """La reproducción del informe: hoy, el reintento crea una SEGUNDA."""
    ruta = tmp_path / "despacho.jsonl"
    escritor = _EscritorConCaida()

    with pytest.raises(ConnectionError):
        _despachar(DurableDispatchJournal(ruta), escritor)
    assert len(escritor.creadas) == 1, "el primer intento tenía que haber creado una"

    # «Reinicio»: diario recargado desde disco, red reparada, mismo work_id.
    escritor.falla_al_etiquetar = False
    resultado = _despachar(DurableDispatchJournal(ruta), escritor)

    assert len(escritor.creadas) == 1, (
        f"el reintento creó OTRA incidencia (total {len(escritor.creadas)}): el efecto "
        "externo se duplicó para el mismo work_id, que es exactamente H-29"
    )
    assert resultado.episodio.numero_incidencia == 101, "el episodio no adoptó la creada"
    assert escritor.etiquetadas, "la adopción tenía que re-aplicar la etiqueta"


def test_h29_una_caida_antes_de_crear_converge_a_una_sola(tmp_path: Path) -> None:
    """La otra ventana: la intención quedó grabada pero no se llegó a crear.
    El reintento busca, no encuentra, y crea UNA."""
    ruta = tmp_path / "despacho.jsonl"

    class _EscritorQueMuereAlCrear(_EscritorConCaida):
        def crear_incidencia(self, **kwargs: object) -> IncidenciaCreada:
            raise ConnectionError("la red murió antes de crear")

    primero = _EscritorQueMuereAlCrear()
    with pytest.raises(ConnectionError):
        _despachar(DurableDispatchJournal(ruta), primero)
    assert primero.creadas == []

    segundo = _EscritorConCaida()
    segundo.falla_al_etiquetar = False
    resultado = _despachar(DurableDispatchJournal(ruta), segundo)
    assert len(segundo.creadas) == 1
    assert resultado.episodio.numero_incidencia == 101
    assert segundo.busquedas, (
        "el reintento no buscó antes de crear: con la intención pendiente, crear "
        "sin buscar es apostar a que la caída fue antes del efecto"
    )


def test_h29_si_la_busqueda_de_adopcion_falla_no_se_crea_nada(tmp_path: Path) -> None:
    """Criterio de parada (a): ante la duda, ninguna incidencia nueva."""
    ruta = tmp_path / "despacho.jsonl"
    primero = _EscritorConCaida()
    with pytest.raises(ConnectionError):
        _despachar(DurableDispatchJournal(ruta), primero)

    class _EscritorConBusquedaRota(_EscritorConCaida):
        def buscar_incidencia_por_work_id(self, **kwargs: object) -> IncidenciaCreada | None:
            raise ConnectionError("la búsqueda de adopción no contesta")

    segundo = _EscritorConBusquedaRota()
    segundo.falla_al_etiquetar = False
    with pytest.raises(ConnectionError):
        _despachar(DurableDispatchJournal(ruta), segundo)
    assert segundo.creadas == [], (
        "con la búsqueda rota se creó una incidencia: si la primera existía, ya hay dos"
    )
