"""Olvidar de verdad en sirius.db (pieza G de ADR-233, ADR-239).

Lo que se olvida se busca después en el fichero entero, byte a byte, también en
los bloques del índice de palabras: buscarlo con SQL no basta, porque un ``LIKE``
sobre un bloque binario se para en el primer cero.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import LargeBinary, String, Text

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.models import Base
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_forget import (
    FORGET_COVERAGE,
    FORGETS,
    build_sqlite_forgetter,
    phrase_matcher,
    without_sentences,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_memory_suggestion_repository import (
    build_sqlite_memory_suggestion_repository,
)
from sirius.adapters.persistence.sqlite_robot_conversation import (
    build_sqlite_robot_conversation_repository,
)
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.facts import FactProposals
from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.domain.facts import Certainty
from sirius.domain.memory import MemoryStatus
from sirius.infrastructure.paths import resolve_paths

pytestmark = pytest.mark.integration

SECRETO = "Zarzamora"


def _base(tmp_path: Path) -> Path:
    rutas = resolve_paths(tmp_path / "datos")
    initialize_persistence(rutas)
    return rutas.data_dir / "sirius.db"


def _en_el_fichero(base: Path, texto: str) -> list[str]:
    """Dónde aparece ``texto``, sin mirar mayúsculas, en cualquier celda de cualquier tabla.

    Las celdas binarias se miran byte a byte: así se ve también lo que el índice de
    palabras guarda en sus bloques, en minúsculas.
    """
    aguja = texto.lower().encode("utf-8")
    encontrado: list[str] = []
    with closing(sqlite3.connect(base)) as conexion:
        tablas = [
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for tabla in tablas:
            for fila in conexion.execute(f'SELECT * FROM "{tabla}"'):
                for valor in fila:
                    if isinstance(valor, bytes):
                        datos = valor.lower()
                    elif isinstance(valor, str):
                        datos = valor.lower().encode("utf-8")
                    else:
                        continue
                    if aguja in datos:
                        encontrado.append(tabla)
    return sorted(set(encontrado))


def test_cada_columna_de_texto_del_esquema_esta_decidida_para_olvidar() -> None:
    """La guarda: una columna de texto nueva rompe esto hasta que se decida qué hace olvidar."""
    columnas = {
        f"{tabla.name}.{columna.name}"
        for tabla in Base.metadata.tables.values()
        for columna in tabla.columns
        if isinstance(columna.type, (Text, String, LargeBinary))
    }
    assert columnas - set(FORGET_COVERAGE) == set(), "columnas sin decidir"
    assert set(FORGET_COVERAGE) - columnas == set(), "decisiones de columnas que no existen"
    assert all(razon.strip() for razon in FORGET_COVERAGE.values())


def test_olvidar_lo_de_algo_lo_borra_de_cada_sitio_que_olvidar_limpia(tmp_path: Path) -> None:
    base = _base(tmp_path)
    conversacion = build_sqlite_conversation_repository(base)
    memoria = build_sqlite_memory_repository(base)
    sugerencias = build_sqlite_memory_suggestion_repository(base)
    charla = build_sqlite_robot_conversation_repository(base)
    try:
        principal = conversacion.get_or_create_main_conversation()
        dicho = conversacion.append_message(
            principal.id, MessageRole.USER, f"La clave es {SECRETO}.", operation_id="a"
        )
        conversacion.append_message(
            principal.id, MessageRole.SIRIUS, f"Apuntada: {SECRETO}.", operation_id="a"
        )
        memoria.create_memory(f"La clave de la alarma es {SECRETO}.", "prueba")
        memoria.record_fact(
            SECRETO, SECRETO, "Es la vecina del tercero", "prueba", since=date(2026, 1, 1)
        )
        memoria.record_fact(
            "Lucía", "trabajo", "Es enfermera", "prueba", since=date(2026, 1, 1), said_by=SECRETO
        )
        sugerencias.create_suggestion(
            f"Su clave es {SECRETO}", person=SECRETO, topic=SECRETO, said_by=SECRETO
        )
        charla.add(principal.id, dicho.sequence, f"Le dijo su clave, {SECRETO}. Y más cosas.")
        charla.save_day(date(2026, 10, 7), f"Habló de {SECRETO}.\nY de la obra.")
        assert _en_el_fichero(base, SECRETO), "el dato tenía que estar antes de olvidarlo"

        informe = build_sqlite_forgetter(base).forget_phrase(SECRETO.lower())

        assert _en_el_fichero(base, SECRETO) == []
        assert (informe.messages, informe.memories, informe.suggestions) == (2, 3, 1)
        assert informe.summaries == 2
        # Lo que no lo nombraba sigue ahí.
        resumen = charla.latest(principal.id)
        assert resumen is not None
        assert resumen.content == "Y más cosas."
        assert charla.day_summary(date(2026, 10, 7)) == "Y de la obra."
    finally:
        for repositorio in (conversacion, memoria, sugerencias, charla):
            repositorio.close()


def test_olvida_eso_borra_el_mensaje_su_respuesta_lo_que_salio_de_el_y_su_resumen(
    tmp_path: Path,
) -> None:
    base = _base(tmp_path)
    conversacion = build_sqlite_conversation_repository(base)
    memoria = build_sqlite_memory_repository(base)
    charla = build_sqlite_robot_conversation_repository(base)
    propuestas = FactProposals(build_sqlite_unit_of_work(base))
    try:
        principal = conversacion.get_or_create_main_conversation()
        antes = conversacion.append_message(
            principal.id, MessageRole.USER, "Mañana voy al dentista.", operation_id="0"
        )
        dicho = conversacion.append_message(
            principal.id, MessageRole.USER, "Mi clave del banco es la de siempre.", operation_id="1"
        )
        # Sirius la repite con otras palabras: también hay que olvidarla.
        conversacion.append_message(
            principal.id, MessageRole.SIRIUS, f"Vale, la de {SECRETO}.", operation_id="1"
        )
        # Lo guardó con «Proponer guardar…», cambiando las palabras.
        sugerencia = propuestas.propose_from_message(dicho.id, f"Su clave es {SECRETO}")
        assert sugerencia is not None
        # El resumen del turno ya lo cubría.
        charla.add(principal.id, dicho.sequence + 1, f"Contó su clave, {SECRETO}.")
        charla.save_day(date.today(), f"Contó su clave, {SECRETO}.")

        informe = build_sqlite_forgetter(base).forget_message(dicho.id)

        assert _en_el_fichero(base, SECRETO) == []
        assert informe.messages == 2
        assert informe.summaries == 2
        mensajes = conversacion.list_messages(principal.id)
        assert [m.content for m in mensajes] == ["Mañana voy al dentista.", None, None]
        assert [m.status for m in mensajes][1:] == [MessageStatus.REDACTED] * 2
        assert mensajes[0].id == antes.id
        assert memoria.list_current_memories() == []
    finally:
        for repositorio in (conversacion, memoria, charla):
            repositorio.close()


def test_olvidar_borra_el_recuerdo_que_salio_del_mensaje_aunque_lo_confirmara(
    tmp_path: Path,
) -> None:
    from sirius.application.facts import ConfirmFactSuggestionUseCase

    base = _base(tmp_path)
    conversacion = build_sqlite_conversation_repository(base)
    memoria = build_sqlite_memory_repository(base)
    unidad = build_sqlite_unit_of_work(base)
    try:
        principal = conversacion.get_or_create_main_conversation()
        dicho = conversacion.append_message(
            principal.id, MessageRole.USER, "Me han subido el sueldo.", operation_id="1"
        )
        sugerencia = FactProposals(unidad).propose_from_message(dicho.id, "Cobra 2.000 euros")
        assert sugerencia is not None
        recuerdo = ConfirmFactSuggestionUseCase(unidad).confirm(sugerencia.id)

        build_sqlite_forgetter(base).forget_message(dicho.id)

        borrado = memoria.get_memory(recuerdo.id)
        assert borrado.status is MemoryStatus.DELETED
        assert borrado.current_revision.content is None
        assert _en_el_fichero(base, "2.000 euros") == []
    finally:
        conversacion.close()
        memoria.close()


def test_un_hecho_dudoso_que_dijo_otro_tambien_se_olvida_por_quien_lo_dijo(
    tmp_path: Path,
) -> None:
    base = _base(tmp_path)
    memoria = build_sqlite_memory_repository(base)
    try:
        memoria.record_fact(
            "propietario",
            "equipo",
            "Es del Atleti",
            "prueba",
            since=date(2026, 1, 1),
            said_by="Ramiro",
            certainty=Certainty.DOUBTFUL,
        )
        build_sqlite_forgetter(base).forget_phrase("Ramiro")
        assert _en_el_fichero(base, "Ramiro") == []
        assert memoria.list_current_facts() == []
    finally:
        memoria.close()


@pytest.mark.parametrize(
    ("resumen", "queda"),
    [
        ("Habló de Ramiro. Y de la obra.", "Y de la obra."),
        ("Habló de Ramiro.", ""),
        ("Primera línea.\nRamiro le debe dinero. Fue al médico.", "Primera línea.\nFue al médico."),
        ("Nada que ver.", "Nada que ver."),
    ],
)
def test_de_un_resumen_solo_se_quitan_las_frases_que_lo_nombran(resumen: str, queda: str) -> None:
    assert without_sentences(resumen, phrase_matcher("Ramiro")) == queda


def test_olvidar_decide_cada_columna_que_limpia_con_su_razon() -> None:
    limpias = {columna for columna, razon in FORGET_COVERAGE.items() if razon == FORGETS}
    assert {"messages.content", "memory_revisions.content", "conversation_summaries.content"} <= (
        limpias
    )


def test_olvidar_va_por_palabras_enteras_y_no_se_lleva_lo_que_no_se_pidio() -> None:
    casa = phrase_matcher("casa")
    assert casa("Llegué a CASA tarde.")
    assert not casa("Se ha casado.")
    assert not casa("Casandra vino.")
    vecino = phrase_matcher("vecino  Ramiro")
    assert vecino("Mi vecino\nRamiro me tiene frito")
    assert not vecino("Ramiro, el vecino")
    assert not phrase_matcher("   ")("cualquier cosa")
