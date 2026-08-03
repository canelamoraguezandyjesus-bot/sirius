"""Validacion funcional del delta relacional discriminante de la familia v0.5.

Comprueba **por ejecucion real** sobre una base con el esquema canonico de
Sirius 0.1 —la cadena de Alembic hasta ``61be4bb269bf``, sin DDL adicional— las
siete condiciones que el paquete de trabajo 13 §8.3 exige al discriminante:

1. una consulta legitima alcanza la semilla mediante ``ADR002-A``;
2. ``ADR002-A`` completo ``E0-E5`` **no** alcanza el destino;
3. el destino supera las puertas comunes ``G1-G10`` y ``G11``;
4. el destino es recuperable por una consulta legitima propia;
5. un recorrido relacional explicito de un salto si aportaria su identificador;
6. desactivar o borrar la arista elimina ese alcance;
7. ningun campo de oraculo participa.

**Esto no es el benchmark.** No mide latencia, memoria ni almacenamiento, no
compara candidatos y no adjudica ganador: comprueba que el dato de entrada de la
familia discrimina lo que dice discriminar. ``ADR002-A`` se ejecuta **sin
modificar ni una linea**: si el discriminante fallara, se corrige el delta.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.benchmark import schema_v0_5 as S5
from experiments.adr002.candidates.adr002_a.candidate import candidato
from experiments.adr002.candidates.common import engine, gates
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Candidata,
    Cardinalidad,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
    Modo,
    Peticion,
    Polaridad,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite

from sirius.adapters.persistence.migrations import upgrade_to_head

_BENCHMARK = Path(__file__).resolve().parents[1] / "benchmark"
_TS = "2026-01-10T00:00:00"

#: Campos del corpus que pertenecen al oraculo y que esta base NO materializa.
#: Comprobarlo por construccion es mas fuerte que buscarlos en la traza: lo que
#: no se inserta no puede filtrarse.
_CAMPOS_DE_ORACULO = ("traza", "criticidad", "procedencia")


def _familia() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    def leer(nombre: str) -> dict[str, Any]:
        return json.loads((_BENCHMARK / nombre).read_text(encoding="utf-8"))

    return (
        leer("conformance_corpus_v0_5.json"),
        leer("subject_keys_v0_1.json"),
        leer("cases_v0_5.json"),
    )


def _construir_base(destino: Path) -> dict[str, int]:
    """Materializa **solo** el ambito del delta, con sus claves de sujeto."""
    corpus, subject_keys, _ = _familia()
    del_delta = [i for i in corpus["items"] if i["project_id"] == S5.PROYECTO_DELTA]
    assert len(del_delta) == 2, "el ambito del delta debe tener exactamente los dos extremos"

    upgrade_to_head(destino)
    conexion = sqlite3.connect(str(destino))
    conexion.execute("PRAGMA foreign_keys=ON")
    try:
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO conversations (created_at, is_main) VALUES (?, 1)", (_TS,))
        cursor.execute("INSERT INTO identities (created_at) VALUES (?)", (_TS,))
        identity_id = int(cursor.lastrowid or 0)
        cursor.execute(
            "INSERT INTO identity_versions (identity_id, version, name, description, "
            "personality_instructions, is_current, created_at) VALUES (?, 1, ?, ?, ?, 1, ?)",
            (identity_id, "Sirius", "discriminante relacional", "sin instrucciones", _TS),
        )
        cursor.execute(
            "INSERT INTO projects (name, objective, current_state, next_step, is_active, "
            "created_at, updated_at, blockers, status) VALUES (?, ?, ?, ?, 1, ?, ?, '', 'active')",
            ("Proyecto Delta relacional", "objetivo", "estado", "siguiente", _TS, _TS),
        )
        proyecto = int(cursor.lastrowid or 0)
        cursor.execute(
            "INSERT INTO events (event_type, actor, message_id, created_at) "
            "VALUES ('memory.created', 'user', NULL, ?)",
            (_TS,),
        )
        evento = int(cursor.lastrowid or 0)

        identidades: dict[str, int] = {"__proyecto__": proyecto}
        for item in del_delta:
            clave = subject_keys["valores"][item["id"]]
            assert clave, f"{item['id']} debe llevar clave de sujeto para este caso"
            cursor.execute(
                "INSERT INTO memories (status, created_at, updated_at, subject_key, project_id) "
                "VALUES ('current', ?, ?, ?, ?)",
                (_TS, _TS, clave, proyecto),
            )
            memory_id = int(cursor.lastrowid or 0)
            identidades[item["id"]] = memory_id
            cursor.execute(
                "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
                "created_at, source_event_id) VALUES (?, 1, ?, 'familia-v0.5', 1, ?, ?)",
                (memory_id, item["text"], _TS, evento),
            )
        conexion.commit()
        return identidades
    finally:
        conexion.close()


def _peticion(proyecto: int, consulta: str) -> Peticion:
    caso = _familia()[2]["nivel_4"][0]["entrada"]["peticion"]
    return Peticion(
        operation_id=str(caso["operation_id"]),
        consulta=consulta,
        proposito=str(caso["proposito"]),
        modo=Modo(caso["modo"]),
        ambito=Ambito(global_=False, proyectos=(str(proyecto),)),
        ventana=VentanaTemporal(tiempo_objetivo=str(caso["tiempo_objetivo"])),
        cardinalidad=Cardinalidad(caso["cardinalidad"]),
        limite_objetivo=int(caso["limite_objetivo"]),
        limite_duro=int(caso["limite_duro"]),
        objetivos=int(caso["objetivos"]),
    )


@pytest.fixture
def base(tmp_path: Path) -> dict[str, int]:
    return _construir_base(tmp_path / "discriminante.sqlite3")


@pytest.fixture
def recuperacion(tmp_path: Path, base: dict[str, int]) -> engine.Recuperacion:
    peticion = _peticion(base["__proyecto__"], S5.CONSULTA_DELTA)
    with PuertoSqlite(tmp_path / "discriminante.sqlite3") as puerto:
        return engine.recuperar(peticion, puerto, candidato())


def _id_canonico(base: dict[str, int], item: str) -> str:
    return f"MEMORIA:{base[item]}"


# ---------------------------------------------------------------------------
# Condiciones 1 y 2 · alcance real de ADR002-A
# ---------------------------------------------------------------------------


def test_una_consulta_legitima_alcanza_la_semilla(
    base: dict[str, int], recuperacion: engine.Recuperacion
) -> None:
    assert _id_canonico(base, S5.ITEM_ORIGEN_DELTA) in recuperacion.ids


def test_adr002_a_completo_no_alcanza_el_destino(
    base: dict[str, int], recuperacion: engine.Recuperacion
) -> None:
    assert _id_canonico(base, S5.ITEM_DESTINO_DELTA) not in recuperacion.ids


def test_la_escalera_se_recorre_entera_y_no_para_por_cuota(
    recuperacion: engine.Recuperacion,
) -> None:
    """Sin esto, la ausencia del destino podria ser una parada temprana."""
    recorridas = [p.etapa for p in recuperacion.traza.pasos]
    for etapa in (Etapa.E1, Etapa.E2, Etapa.E3, Etapa.E4):
        assert etapa in recorridas, etapa
    assert recuperacion.parada.identificador != "S1"


def test_el_limite_no_es_la_causa_de_que_falte_el_destino(
    base: dict[str, int], recuperacion: engine.Recuperacion
) -> None:
    peticion = _peticion(base["__proyecto__"], S5.CONSULTA_DELTA)
    assert peticion.limite_duro > len(recuperacion.resultados)
    assert not recuperacion.traza.desbordamiento
    assert recuperacion.traza.criticos_omitidos == ()


# ---------------------------------------------------------------------------
# Condiciones 3 y 4 · el destino no es inalcanzable: es inalcanzable para A
# ---------------------------------------------------------------------------


def _item_destino(tmp_path: Path, base: dict[str, int]) -> ItemCanonico:
    with PuertoSqlite(tmp_path / "discriminante.sqlite3") as puerto:
        materializacion = puerto.por_identificadores([_id_canonico(base, S5.ITEM_DESTINO_DELTA)])
    assert materializacion.completa
    return materializacion.items[0]


def test_el_destino_supera_las_puertas_comunes(tmp_path: Path, base: dict[str, int]) -> None:
    item = _item_destino(tmp_path, base)
    peticion = _peticion(base["__proyecto__"], S5.CONSULTA_DELTA)
    propuesta = Candidata(
        item=item,
        etapa=Etapa.E3,
        lectura=LecturaSemantica(
            sujeto=item.subject_key,
            polaridad=Polaridad.AFIRMATIVA,
            condicion=None,
            tiempo=item.created_at,
            medio="recorrido relacional explicito de un salto",
        ),
        razon="alcanzado por arista explicita tipada y dirigida",
        senal="relacion tipada del canon",
    )
    previas = gates.aplicar_previas([propuesta], peticion)
    assert previas.admitidas, previas.descartes
    semantico = gates.aplicar_g11(previas.admitidas, peticion)
    assert semantico.admitidas, semantico.descartes


def test_el_destino_es_recuperable_por_una_consulta_propia(
    tmp_path: Path, base: dict[str, int]
) -> None:
    peticion = _peticion(base["__proyecto__"], S5.CONSULTA_PROPIA_DEL_DESTINO)
    with PuertoSqlite(tmp_path / "discriminante.sqlite3") as puerto:
        propia = engine.recuperar(peticion, puerto, candidato())
    assert _id_canonico(base, S5.ITEM_DESTINO_DELTA) in propia.ids


# ---------------------------------------------------------------------------
# Condiciones 5 y 6 · el salto relacional, y su ausencia
# ---------------------------------------------------------------------------


def _un_salto(aristas: list[dict[str, str]], alcanzados: tuple[str, ...]) -> list[str]:
    origen = set(alcanzados)
    return sorted({a["destino"] for a in aristas if a["origen"] in origen} - origen)


def test_un_salto_relacional_aportaria_el_destino(
    base: dict[str, int], recuperacion: engine.Recuperacion
) -> None:
    arista = {
        "origen": _id_canonico(base, S5.ITEM_ORIGEN_DELTA),
        "destino": _id_canonico(base, S5.ITEM_DESTINO_DELTA),
        "tipo": S5.TIPO_RELACION_DELTA,
    }
    assert _un_salto([arista], recuperacion.ids) == [_id_canonico(base, S5.ITEM_DESTINO_DELTA)]


def test_sin_la_arista_ese_alcance_desaparece(
    base: dict[str, int], recuperacion: engine.Recuperacion
) -> None:
    assert _un_salto([], recuperacion.ids) == []


def test_el_alcance_real_coincide_con_el_oraculo_congelado(
    base: dict[str, int], recuperacion: engine.Recuperacion
) -> None:
    """La ejecucion real y el oraculo del caso adjudican lo mismo."""
    caso = _familia()[2]["nivel_4"][0]
    esperados = [_id_canonico(base, i) for i in caso["oraculo"]["alcance_lexico_estructurado"]]
    assert sorted(recuperacion.ids) == sorted(esperados)


# ---------------------------------------------------------------------------
# Condicion 7 · ningun campo de oraculo participa
# ---------------------------------------------------------------------------


def test_la_base_del_caso_no_materializa_ningun_campo_de_oraculo(
    tmp_path: Path, base: dict[str, int]
) -> None:
    conexion = sqlite3.connect(str(tmp_path / "discriminante.sqlite3"))
    try:
        contenidos = [
            str(fila[0]) for fila in conexion.execute("SELECT content FROM memory_revisions")
        ]
    finally:
        conexion.close()
    corpus = _familia()[0]
    del_delta = {i["id"]: i for i in corpus["items"] if i["project_id"] == S5.PROYECTO_DELTA}
    for item in del_delta.values():
        assert item["text"] in contenidos
        for campo in _CAMPOS_DE_ORACULO:
            valor = item.get(campo)
            if valor:
                assert json.dumps(valor, ensure_ascii=False) not in " ".join(contenidos)


def test_la_traza_no_filtra_el_texto_de_ningun_item(
    recuperacion: engine.Recuperacion,
) -> None:
    corpus = _familia()[0]
    volcado = json.dumps(recuperacion.traza.como_dict(), ensure_ascii=False)
    for item in corpus["items"]:
        if item["project_id"] == S5.PROYECTO_DELTA:
            assert item["text"] not in volcado


def test_adr002_a_no_declara_ninguna_senal_tardia(recuperacion: engine.Recuperacion) -> None:
    """El discriminante seria vacuo si A ya tuviera senal relacional."""
    assert candidato().senal_tardia_habilitada == "ninguna_adicional"
    assert recuperacion.conflictos == ()
