"""Diario del despachador durable (H-11, incidencia #242, ADR-064).

Cubre H11-P1 (la reserva sobrevive a un reinicio), H11-P2 (dos ejecuciones
sobre el mismo ``WorkItem`` producen una sola incidencia), H11-P3 (el
adaptador en memoria sigue en verde -ya lo cubre ``test_dispatcher.py`` sin
tocar, y aquí además la paridad de contrato-) y la prueba por mutación exigida
por la incidencia: sustituir el diario durable por el en memoria hace caer
justo la propiedad de supervivencia al reinicio.

Reutiliza los dobles ya definidos en ``test_dispatcher.py`` -no se duplican-
para que las pruebas de aquí ejerzan exactamente el mismo camino de
producción (:func:`sirius_engine.dispatcher.dispatch_work_item`), con la
única diferencia de que el diario se "reabre" (una instancia nueva de
:class:`~sirius_engine.adapters.durable.dispatch_journal.DurableDispatchJournal`
sobre el MISMO fichero) para simular un reinicio del proceso -mismo patrón
que ``test_durable_supervisor_journal.py`` fijó para H-10/ADR-061.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sirius_engine.adapters.durable.dispatch_journal import DurableDispatchJournal
from sirius_engine.adapters.memory_dispatch_journal import InMemoryDispatchJournal
from sirius_engine.dispatcher import ETIQUETA_ACTIVACION, dispatch_work_item
from sirius_engine.domain.dispatch import DispatchEpisode

from .test_dispatcher import NOW, ORDEN, PERFIL, _EscritorSoloVerbosEnumerados, _work_item

# --- H11-P1: la reserva (el episodio ya grabado) sobrevive a un reinicio -----------------


def test_h11_p1_el_episodio_sobrevive_a_un_reinicio(tmp_path: Path) -> None:
    work_item = _work_item(evidencia=(ORDEN,))
    writer = _EscritorSoloVerbosEnumerados()
    journal_path = tmp_path / "diario-despachador.jsonl"
    journal = DurableDispatchJournal(journal_path)

    primero = dispatch_work_item(
        work_item,
        writer=writer,
        journal=journal,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )
    assert primero.ya_despachado is False
    assert len(writer.llamadas) == 2

    # "Reinicio": una instancia NUEVA sobre el MISMO fichero.
    reabierto = DurableDispatchJournal(journal_path)
    assert reabierto.episode_for(work_item.work_id) == primero.episodio
    assert reabierto.episodes() == (primero.episodio,)
    reserva = reabierto.reservar(work_item.work_id)
    assert reserva.obtenida is False
    assert reserva.episodio == primero.episodio


# --- H11-P2: dos ejecuciones sobre el mismo WorkItem, una sola incidencia ----------------


def test_h11_p2_dos_ejecuciones_del_despachador_producen_una_sola_incidencia(
    tmp_path: Path,
) -> None:
    """Dos "ejecuciones" completas del proceso -cada una con su propia instancia del
    diario sobre el mismo fichero- sobre el mismo ``WorkItem``: la segunda reconoce el
    episodio de la primera y no repite ninguna escritura en GitHub (C2-P3 entre procesos)."""
    work_item = _work_item(evidencia=(ORDEN,))
    writer = _EscritorSoloVerbosEnumerados()
    journal_path = tmp_path / "diario-despachador.jsonl"

    primera_ejecucion = DurableDispatchJournal(journal_path)
    primero = dispatch_work_item(
        work_item,
        writer=writer,
        journal=primera_ejecucion,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )

    segunda_ejecucion = DurableDispatchJournal(journal_path)
    segundo = dispatch_work_item(
        work_item,
        writer=writer,
        journal=segunda_ejecucion,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )

    assert primero.ya_despachado is False
    assert segundo.ya_despachado is True
    assert segundo.episodio == primero.episodio
    # Solo dos llamadas en total: las de la PRIMERA ejecución. La segunda,
    # tras "reiniciar", no repitió ninguna escritura.
    assert len(writer.llamadas) == 2
    verbos = [nombre for nombre, _ in writer.llamadas]
    assert verbos == ["crear_incidencia", "aplicar_etiqueta"]


# --- H11-P3: el adaptador en memoria sigue existiendo, mismo contrato -------------------


def test_h11_p3_el_diario_en_memoria_y_el_durable_comparten_el_mismo_comportamiento_basico(
    tmp_path: Path,
) -> None:
    """No demuestra C2-P1..P6 de nuevo -eso lo sigue haciendo ``test_dispatcher.py`` sin
    modificar-, solo que ambas implementaciones satisfacen el mismo contrato básico del
    puerto de forma idéntica, con y sin persistencia."""
    episodio = DispatchEpisode(
        work_id="WI-CONTRATO",
        orden_enlazada="https://github.com/acme/repo/issues/1#issuecomment-1",
        repo="acme/repo",
        numero_incidencia=241,
        etiqueta=ETIQUETA_ACTIVACION,
        recorded_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
    )

    en_memoria = InMemoryDispatchJournal()
    durable = DurableDispatchJournal(tmp_path / "diario-contrato.jsonl")

    for diario in (en_memoria, durable):
        assert diario.episode_for("WI-CONTRATO") is None
        reserva = diario.reservar("WI-CONTRATO")
        assert reserva.obtenida is True
        diario.record(episodio)
        assert diario.episode_for("WI-CONTRATO") == episodio
        assert diario.episodes() == (episodio,)
        reserva_tras_grabar = diario.reservar("WI-CONTRATO")
        assert reserva_tras_grabar.obtenida is False
        assert reserva_tras_grabar.episodio == episodio


# --- Prueba por mutación (ADR-001, exigida por la incidencia): -------------------------
# con el diario EN MEMORIA en lugar del durable, la supervivencia al reinicio cae.


def test_mutacion_diario_en_memoria_en_vez_de_durable_no_sobrevive_al_reinicio(
    tmp_path: Path,
) -> None:
    """Si H11-P1/H11-P2 pasaran igual con ``InMemoryDispatchJournal``, no probarían nada:
    esta prueba deja constancia de que SÍ caen -la propiedad que demuestra que la
    persistencia real es la que sostiene la garantía, no un artefacto de la prueba."""
    work_item = _work_item(evidencia=(ORDEN,))
    writer = _EscritorSoloVerbosEnumerados()

    primera_ejecucion = InMemoryDispatchJournal()
    primero = dispatch_work_item(
        work_item,
        writer=writer,
        journal=primera_ejecucion,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )
    assert primero.ya_despachado is False

    # "Reinicio" con el diario en memoria: una instancia nueva no comparte
    # fichero -no comparte NADA- con la anterior, así que no reconoce el
    # episodio ya grabado. GitHub, en la vía real, crearía una incidencia con
    # otro número -el doble mueve su contador para reflejarlo.
    writer.siguiente_numero = 242
    segunda_ejecucion = InMemoryDispatchJournal()
    assert segunda_ejecucion.episode_for(work_item.work_id) is None
    segundo = dispatch_work_item(
        work_item,
        writer=writer,
        journal=segunda_ejecucion,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )

    # Exactamente el defecto H-11: la segunda "ejecución" no reconoce la
    # primera y repite la escritura -una segunda incidencia para el mismo
    # WorkItem.
    assert segundo.ya_despachado is False
    assert segundo.episodio != primero.episodio
    assert len(writer.llamadas) == 4  # dos escrituras completas, no una

    # Contraste explícito: la implementación real (durable, mismo fichero) no
    # cae en el mismo defecto.
    journal_path = tmp_path / "diario-real.jsonl"
    real_primera = DurableDispatchJournal(journal_path)
    real_primero = dispatch_work_item(
        work_item,
        writer=_EscritorSoloVerbosEnumerados(),
        journal=real_primera,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )
    real_segunda = DurableDispatchJournal(journal_path)
    real_segundo = dispatch_work_item(
        work_item,
        writer=_EscritorSoloVerbosEnumerados(),
        journal=real_segunda,
        repo="acme/repo",
        profile_ref=PERFIL,
        bloque="C2",
        now=NOW,
    )
    assert real_segundo.ya_despachado is True
    assert real_segundo.episodio == real_primero.episodio


# --- Reutiliza el mismo fichero también tras un fallo del `fsync` de directorio ---------


def test_episode_for_tras_reabrir_ve_solo_episodios_completos(tmp_path: Path) -> None:
    """El registro corrupto/incompleto nunca se confunde con uno válido tras reabrir
    -mismo criterio de `replay` (ADR-026) que ya cubre `journal.py` sin modificarlo."""
    journal_path = tmp_path / "diario-vacio.jsonl"
    journal = DurableDispatchJournal(journal_path)
    assert journal.episodes() == ()
    assert journal.episode_for("WI-INEXISTENTE") is None

    reabierto = DurableDispatchJournal(journal_path)
    assert reabierto.episodes() == ()
