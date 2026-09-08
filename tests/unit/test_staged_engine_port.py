"""Unit tests for ``sirius.adapters.persistence.staged_engine_port``
(issue #457/ADR-109/ADR-110): the ``PuertoDeRecuperacion`` adapter over the
real Sirius 0.1 schema. Uses a real, migrated SQLite database (like
``tests/integration/test_rank_relevant_knowledge.py``) because the queries
under test are SQL, not pure Python.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from sirius.adapters.persistence.database import build_engine, build_session_factory
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.adapters.persistence.staged_engine_port import (
    IdentificadorInvalidoError,
    StagedEnginePort,
    build_staged_engine_port,
)
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.domain.staged_engine_contracts import SIN_EJES, Clase, EjesDeclarados


def _bootstrap(database_path: Path) -> None:
    upgrade_to_head(database_path)
    build_sqlite_project_repository(database_path).ensure_bootstrap_project()


def test_por_termino_lexico_finds_a_saved_memory(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory = SaveManualMemoryUseCase(build_sqlite_unit_of_work(database_path)).save(
        "terminounicoparabuscar en la memoria"
    )

    puerto = build_staged_engine_port(database_path)
    try:
        encontrados = puerto.por_termino_lexico(["terminounicoparabuscar"])
    finally:
        puerto.close()

    assert [i.id for i in encontrados] == [f"{Clase.MEMORIA.value}:{memory.id}"]
    assert encontrados[0].ejes == SIN_EJES


def test_por_termino_lexico_sin_terminos_utiles_no_ejecuta_consulta(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.por_termino_lexico(["", "  "]) == ()
    finally:
        puerto.close()


def test_por_clave_exacta_finds_by_subject_key(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project = build_sqlite_project_repository(database_path).create_project(
        "Proyecto de prueba", "objetivo", state_summary="", blockers=(), next_step=""
    )
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "texto cualquiera", subject_key="faro-costa-unico", project_id=project.id
    )

    puerto = build_staged_engine_port(database_path)
    try:
        encontrados = puerto.por_clave_exacta(["faro-costa-unico"])
    finally:
        puerto.close()

    assert [i.id for i in encontrados] == [f"{Clase.MEMORIA.value}:{memory.id}"]


def test_por_prefijo_de_sujeto_rejects_a_prefix_shorter_than_three_chars(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project = build_sqlite_project_repository(database_path).create_project(
        "Proyecto de prueba", "objetivo", state_summary="", blockers=(), next_step=""
    )
    unit_of_work = build_sqlite_unit_of_work(database_path)
    SaveManualMemoryUseCase(unit_of_work).save(
        "texto", subject_key="fa-algo-unico", project_id=project.id
    )

    puerto = build_staged_engine_port(database_path)
    try:
        # "fa" tiene menos de 3 caracteres: no es una relacion, es un barrido.
        assert puerto.por_prefijo_de_sujeto(["fa"]) == ()
    finally:
        puerto.close()


def test_por_identificadores_declares_absent_ids_without_raising(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("texto cualquiera")

    puerto = build_staged_engine_port(database_path)
    try:
        materializacion = puerto.por_identificadores(
            [f"{Clase.MEMORIA.value}:{memory.id}", f"{Clase.MEMORIA.value}:999999"]
        )
    finally:
        puerto.close()

    assert [i.id for i in materializacion.items] == [f"{Clase.MEMORIA.value}:{memory.id}"]
    assert materializacion.ausentes == (f"{Clase.MEMORIA.value}:999999",)
    assert materializacion.completa is False


def test_por_identificadores_rejects_a_malformed_identifier(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    puerto = build_staged_engine_port(database_path)
    try:
        with pytest.raises(IdentificadorInvalidoError):
            puerto.por_identificadores(["no-es-un-identificador"])
    finally:
        puerto.close()


def test_historial_y_fuentes_always_empty(tmp_path: Path) -> None:
    """``E4`` no tiene objetivo real en Sirius 0.1: ``RankedKnowledge`` solo
    modela ``Memory``/``Decision`` (ver docstring del módulo bajo prueba)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.historial_y_fuentes(["cualquiera"]) == ()
    finally:
        puerto.close()


def test_ejes_por_identidad_overrides_sin_ejes_for_a_declared_item(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory = SaveManualMemoryUseCase(build_sqlite_unit_of_work(database_path)).save(
        "terminounicoconejes en la memoria"
    )
    identidad = f"{Clase.MEMORIA.value}:{memory.id}"
    ejes_declarados = EjesDeclarados(ambito="GLOBAL")

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    puerto = StagedEnginePort(
        session_factory, engine, ejes_por_identidad={identidad: ejes_declarados}
    )
    try:
        (encontrado,) = puerto.por_termino_lexico(["terminounicoconejes"])
    finally:
        puerto.close()

    assert encontrado.ejes == ejes_declarados


# -- Ventana de vigencia (ADR-168, hueco H1 de ADR-148) ----------------------


def _proyecto_de_prueba(database_path: Path) -> int:
    """El id del proyecto que `ensure_bootstrap_project` deja creado."""
    repositorio = build_sqlite_project_repository(database_path)
    proyecto = repositorio.get_active_project()
    assert proyecto is not None
    return proyecto.id


def _decision_aprobada(database_path: Path, asunto: str, texto: str) -> int:
    unidad = build_sqlite_unit_of_work(database_path)
    decision = ProposeDecisionUseCase(unidad).propose(
        asunto, _proyecto_de_prueba(database_path), texto
    )
    ApproveDecisionUseCase(unidad).approve(decision.id, confirmed=True)
    return decision.id


def test_por_ventana_de_vigencia_devuelve_la_decision_aprobada_de_la_ventana(
    tmp_path: Path,
) -> None:
    """El camino de entrada que ADR-168 abre: sin una sola palabra de la
    consulta, la ventana sola trae la decisión aprobada."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    decision_id = _decision_aprobada(
        database_path, "descuento-invierno", "Se aplica el descuento de invierno."
    )

    puerto = build_staged_engine_port(database_path)
    try:
        encontrados = puerto.por_ventana_de_vigencia("2020-01-01T00:00:00Z", "2099-01-01T00:00:00Z")
    finally:
        puerto.close()

    assert [item.id for item in encontrados] == [f"{Clase.DECISION.value}:{decision_id}"]


def test_por_ventana_de_vigencia_no_devuelve_lo_registrado_despues_del_fin(
    tmp_path: Path,
) -> None:
    """El final de la ventana es un predicado, no un adorno: lo registrado
    después no entra."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _decision_aprobada(database_path, "descuento-invierno", "Se aplica el descuento.")

    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.por_ventana_de_vigencia("2020-01-01T00:00:00Z", "2020-12-31T00:00:00Z") == ()
    finally:
        puerto.close()


#: Un registro fijado a mano, con hora dentro del día: la frontera que la
#: forma de la cadena decide está en el MISMO día civil que el final de la
#: ventana, así que una prueba con años de separación no la toca.
_REGISTRO_FIJADO = "2026-03-20 09:00:00.000000"


def _fijar_created_at(database_path: Path, decision_id: int, momento: str) -> None:
    """Escribe `created_at` en la fila ya creada, con la forma literal en la
    que el dialecto de SQLAlchemy guarda sus columnas `DateTime`.

    Se hace por escritura directa —igual que el cargador del banco
    (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, ADR-166)—
    porque ningún caso de uso de Sirius 0.1 acepta una fecha de creación: la
    pone el reloj. Sin fijarla, la frontera del mismo día civil dependería
    del reloj del runner y la prueba no fijaría nada.
    """
    engine = build_engine(database_path)
    try:
        with engine.begin() as conexion:
            conexion.execute(
                text("UPDATE decisions SET created_at = :momento WHERE id = :id"),
                {"momento": momento, "id": decision_id},
            )
    finally:
        engine.dispose()


def test_por_ventana_de_vigencia_excluye_lo_registrado_el_mismo_dia_tras_el_final(
    tmp_path: Path,
) -> None:
    """La frontera real: `created_at` y el final de la ventana llegan en
    formas distintas —espacio contra `T`/`Z`— y SQLite las compara como
    CADENAS, así que sin reescribir el extremo a la forma de `created_at` el
    espacio (0x20) ordena antes que la `T` (0x54) y entra todo lo registrado
    más tarde del mismo día civil. Aquí el registro son las 09:00 del 20 de
    marzo y la ventana acaba en la medianoche que abre ese día: no entra.
    """
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    decision_id = _decision_aprobada(
        database_path, "descuento-invierno", "Se aplica el descuento de invierno."
    )
    _fijar_created_at(database_path, decision_id, _REGISTRO_FIJADO)

    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.por_ventana_de_vigencia("2020-01-01T00:00:00Z", "2026-03-20T00:00:00Z") == ()
        # Simétrica, para que la prueba fije la frontera y no solo la
        # exclusión: con la ventana acabando después del registro, entra.
        entra = puerto.por_ventana_de_vigencia("2020-01-01T00:00:00Z", "2026-03-20T23:59:59Z")
        assert [item.id for item in entra] == [f"{Clase.DECISION.value}:{decision_id}"]
    finally:
        puerto.close()


def test_por_ventana_de_vigencia_no_afirma_nada_con_un_final_ilegible(tmp_path: Path) -> None:
    """Un final que no es un instante legible no acota: la ventana devuelve
    vacío en vez de comparar cadenas sueltas contra `created_at`."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    _decision_aprobada(database_path, "descuento-invierno", "Se aplica el descuento.")

    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.por_ventana_de_vigencia("2020-01-01T00:00:00Z", "el mes que viene") == ()
    finally:
        puerto.close()


def test_por_ventana_de_vigencia_no_devuelve_una_propuesta_sin_aprobar(tmp_path: Path) -> None:
    """Una decisión `PROPOSED` no ha empezado ninguna vigencia: aprobarla es
    lo que la empieza (`sirius.domain.decision.DecisionStatus`)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    ProposeDecisionUseCase(build_sqlite_unit_of_work(database_path)).propose(
        "propuesta-sin-aprobar", _proyecto_de_prueba(database_path), "Aún no se ha decidido."
    )

    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.por_ventana_de_vigencia("2020-01-01T00:00:00Z", "2099-01-01T00:00:00Z") == ()
    finally:
        puerto.close()


def test_por_ventana_de_vigencia_no_enumera_memorias(tmp_path: Path) -> None:
    """La restricción de clase de ADR-168, fijada aquí porque es la que
    impide que la ventana degenere en un barrido.

    `MemoryStatus` no es un ciclo de vigencia y su propio modelo lo dice:
    «Superseded revisions are a history concern, not a status of the memory
    itself». Enumerar memorias por ventana obligaría a afirmar «esta memoria
    estaba vigente en enero» sobre un dato que el sustrato no guarda. La
    memoria sigue entrando por las vías léxicas, que no afirman nada sobre su
    vigencia: `test_por_termino_lexico_finds_a_saved_memory`, arriba.
    """
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    SaveManualMemoryUseCase(build_sqlite_unit_of_work(database_path)).save(
        "terminounicoparalaventana en la memoria"
    )

    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.por_ventana_de_vigencia("2020-01-01T00:00:00Z", "2099-01-01T00:00:00Z") == ()
        assert len(puerto.por_termino_lexico(["terminounicoparalaventana"])) == 1
    finally:
        puerto.close()
