"""Los hechos con su fecha y quién lo dijo (pieza G de ADR-233, ADR-239)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import (
    SqliteMemoryRepository,
    build_sqlite_memory_repository,
)
from sirius.adapters.persistence.sqlite_memory_suggestion_repository import (
    build_sqlite_memory_suggestion_repository,
)
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.facts import (
    ConfirmFactSuggestionUseCase,
    FactProposals,
    FactsUseCase,
)
from sirius.domain.conversation import MessageRole
from sirius.domain.facts import OWNER, Certainty, FactSpan, ProposedFact
from sirius.domain.memory import MemoryStatus
from sirius.infrastructure.paths import resolve_paths

pytestmark = pytest.mark.integration


@pytest.fixture
def base(tmp_path: Path) -> Path:
    rutas = resolve_paths(tmp_path / "datos")
    initialize_persistence(rutas)
    return rutas.data_dir / "sirius.db"


@pytest.fixture
def memoria(base: Path) -> Iterator[SqliteMemoryRepository]:
    repositorio = build_sqlite_memory_repository(base)
    yield repositorio
    repositorio.close()


def test_un_hecho_nuevo_del_mismo_tema_cierra_el_anterior_con_su_fecha(
    memoria: SqliteMemoryRepository,
) -> None:
    memoria.record_fact("propietario", "dónde vive", "Vive en Madrid", "p", since=date(2024, 1, 1))
    nuevo = memoria.record_fact(
        "Propietario", "donde vive", "Vive en Valencia", "p", since=date(2026, 9, 1)
    )

    assert [m.current_revision.content for m in memoria.list_current_facts()] == [
        "Vive en Valencia"
    ]
    historia = memoria.find_fact_history("propietario", "dónde vive")
    assert [(r.content, r.valid_from, r.valid_to) for r in historia] == [
        ("Vive en Madrid", date(2024, 1, 1), date(2026, 9, 1)),
        ("Vive en Valencia", date(2026, 9, 1), None),
    ]
    # El de antes es una revisión vieja: ni la búsqueda ni la charla la ven.
    assert nuevo.current_revision.content == "Vive en Valencia"


def test_hechos_de_temas_o_personas_distintos_no_se_cierran_entre_si(
    memoria: SqliteMemoryRepository,
) -> None:
    memoria.record_fact(
        "propietario", "trabajo", "Trabaja de electricista", "p", since=date.today()
    )
    memoria.record_fact("Lucía", "trabajo", "Lucía es enfermera", "p", since=date.today())
    memoria.record_fact("propietario", None, "Le gusta el café", "p", since=date.today())
    memoria.record_fact("propietario", None, "Le gusta el té", "p", since=date.today())

    assert len(memoria.list_current_facts()) == 4
    assert [m.current_revision.content for m in memoria.list_current_facts("lucia")] == [
        "Lucía es enfermera"
    ]
    assert memoria.known_people() == ["propietario", "Lucía"]


def test_lo_que_dice_sirius_nunca_se_apunta_como_hecho(memoria: SqliteMemoryRepository) -> None:
    with pytest.raises(ValueError, match="Sirius"):
        memoria.record_fact(
            "propietario", "x", "Vive en Cuenca", "p", since=date.today(), said_by="Sirius"
        )


def test_corregir_un_hecho_cierra_hoy_el_de_antes_y_el_nuevo_lo_dice_el(
    memoria: SqliteMemoryRepository,
) -> None:
    hecho = memoria.record_fact(
        "propietario",
        "equipo",
        "Es del Atleti",
        "p",
        since=date(2025, 1, 1),
        said_by="Lucía",
        certainty=Certainty.DOUBTFUL,
    )
    memoria.correct_fact(hecho.id, "Es del Betis", "p")

    viejo, nuevo = memoria.find_fact_history("propietario", "equipo")
    assert (viejo.said_by, viejo.certainty, viejo.valid_to) == ("Lucía", "dudosa", date.today())
    assert (nuevo.said_by, nuevo.certainty, nuevo.valid_from) == (OWNER, "segura", date.today())


def test_borrar_un_hecho_borra_tambien_de_quien_era_de_que_trataba_y_quien_lo_dijo(
    memoria: SqliteMemoryRepository,
) -> None:
    hecho = memoria.record_fact(
        "Lucía", "trabajo", "Es enfermera", "p", since=date.today(), said_by="Marta"
    )
    borrado = memoria.delete_memory(hecho.id)

    assert borrado.status is MemoryStatus.DELETED
    assert (borrado.person, borrado.topic, borrado.current_revision.said_by) == (None, None, None)
    assert memoria.known_people() == []


def test_proponer_desde_un_mensaje_solo_vale_con_uno_suyo(base: Path) -> None:
    conversacion = build_sqlite_conversation_repository(base)
    try:
        principal = conversacion.get_or_create_main_conversation()
        suyo = conversacion.append_message(principal.id, MessageRole.USER, "Vivo en Valencia")
        de_sirius = conversacion.append_message(
            principal.id, MessageRole.SIRIUS, "Tú vives en Cuenca, que lo sé yo."
        )
        propuestas = FactProposals(build_sqlite_unit_of_work(base))

        assert propuestas.propose_from_message(de_sirius.id, "Vive en Cuenca") is None
        sugerencia = propuestas.propose_from_message(suyo.id, "Vive en Valencia")
        assert sugerencia is not None
        assert sugerencia.content == "Vive en Valencia"
    finally:
        conversacion.close()


def test_un_hecho_propuesto_no_entra_hasta_que_dice_que_si(base: Path) -> None:
    unidad = build_sqlite_unit_of_work(base)
    memoria = build_sqlite_memory_repository(base)
    sugerencias = build_sqlite_memory_suggestion_repository(base)
    conversacion = build_sqlite_conversation_repository(base)
    try:
        hechos = FactsUseCase(memoria, sugerencias, conversacion)
        sugerencia = FactProposals(unidad).propose(
            ProposedFact(
                "Lucía",
                "trabajo",
                "Se va a una farmacia",
                since=date(2026, 9, 1),
                said_by="Lucía",
                certainty=Certainty.DOUBTFUL,
            ),
            by_sirius=True,
        )
        assert hechos.current("Lucía") == []
        assert [s.id for s in hechos.pending_facts()] == [sugerencia.id]

        ConfirmFactSuggestionUseCase(unidad).confirm(sugerencia.id)

        assert hechos.history("Lucía", "trabajo") == [
            FactSpan("Se va a una farmacia", date(2026, 9, 1), None, "Lucía", Certainty.DOUBTFUL)
        ]
        assert hechos.pending_facts() == []
    finally:
        for repositorio in (memoria, sugerencias, conversacion):
            repositorio.close()


def test_confirmar_una_correccion_cambia_el_hecho_y_no_crea_otro(base: Path) -> None:
    unidad = build_sqlite_unit_of_work(base)
    memoria = build_sqlite_memory_repository(base)
    sugerencias = build_sqlite_memory_suggestion_repository(base)
    conversacion = build_sqlite_conversation_repository(base)
    try:
        hecho = memoria.record_fact(
            "propietario", "equipo", "Es del Atleti", "p", since=date.today()
        )
        hechos = FactsUseCase(memoria, sugerencias, conversacion)
        correccion = FactProposals(unidad).propose_correction(hecho.id, "Soy del Betis")
        [pendiente] = hechos.pending_corrections()
        assert (pendiente.before, pendiente.after) == ("Es del Atleti", "Soy del Betis")
        assert hechos.pending_facts() == []

        ConfirmFactSuggestionUseCase(unidad).confirm(correccion.id)

        assert [m.id for m in hechos.current()] == [hecho.id]
        assert hechos.current()[0].current_revision.content == "Soy del Betis"
        assert hechos.pending_corrections() == []
    finally:
        for repositorio in (memoria, sugerencias, conversacion):
            repositorio.close()


def test_confirmar_una_sugerencia_de_siempre_sigue_creando_un_recuerdo(base: Path) -> None:
    unidad = build_sqlite_unit_of_work(base)
    sugerencias = build_sqlite_memory_suggestion_repository(base)
    try:
        sugerencia = sugerencias.create_suggestion("Le gusta el café solo")
        recuerdo = ConfirmFactSuggestionUseCase(unidad).confirm(sugerencia.id)
        assert recuerdo.current_revision.content == "Le gusta el café solo"
        assert not recuerdo.is_fact
    finally:
        sugerencias.close()


def test_la_ficha_junta_sus_hechos_y_lo_que_el_dijo_de_ella(base: Path) -> None:
    memoria = build_sqlite_memory_repository(base)
    sugerencias = build_sqlite_memory_suggestion_repository(base)
    conversacion = build_sqlite_conversation_repository(base)
    try:
        principal = conversacion.get_or_create_main_conversation()
        conversacion.append_message(principal.id, MessageRole.USER, "Hoy he visto a lucia")
        conversacion.append_message(principal.id, MessageRole.SIRIUS, "¿Qué tal está Lucía?")
        conversacion.append_message(principal.id, MessageRole.USER, "Luciano no vino")
        memoria.record_fact("Lucía", "trabajo", "Es enfermera", "p", since=date.today())

        ficha = FactsUseCase(memoria, sugerencias, conversacion).card("Lucía")

        assert ficha.facts == ("Es enfermera",)
        assert ficha.mentions == ("Hoy he visto a lucia",)
    finally:
        for repositorio in (memoria, sugerencias, conversacion):
            repositorio.close()
