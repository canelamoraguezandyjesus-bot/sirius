"""Arnes de conformidad de ``T0-control``: que sea honesto, no que sea bueno.

Estas pruebas no comprueban que T0 recupere bien. Comprueban que el arnes
**no le anade nada** y que sus incumplimientos salen como resultados en vez de
quedar disimulados: si alguna vez el adaptador empezara a filtrar por ambito, a
truncar por limite o a adjudicar una parada, estas pruebas fallan.

No miden rendimiento, no ejecutan el benchmark y no tocan ``src/sirius``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from experiments.adr002 import custodia_t0
from experiments.adr002.candidates import fixtures
from experiments.adr002.candidates.adr002_a.candidate import candidato
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    Modo,
    Peticion,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.candidates.t0_control import conformance as T0

RAIZ = Path(__file__).resolve().parents[3]

#: Arbol Git de ``src/sirius`` que la ficha congelada de T0 declara como su
#: huella de fuentes. Si este arnes lo cambiara, T0 dejaria de ser T0.
ARBOL_DE_FUENTES_DECLARADO = "6d8558ef1fe4994cb15a12967525bf3496b3c0b8"


@pytest.fixture
def base(tmp_path: Path) -> Path:
    destino = tmp_path / "control.sqlite3"
    fixtures.construir(destino)
    return destino


def _peticion(consulta: str = "faro") -> Peticion:
    return Peticion(
        operation_id="t0-conformidad",
        consulta=consulta,
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=False, proyectos=(fixtures.PROYECTO_ACTIVO,)),
        ventana=VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=5,
        limite_duro=5,
    )


# ---------------------------------------------------------------------------
# El arnes no modifica T0
# ---------------------------------------------------------------------------


def test_el_arnes_no_toca_lo_que_t0_ejecuta() -> None:
    """La cadena de Alembic y cada modulo que T0 ejecuta, byte a byte.

    Antes se comparaba el arbol entero de ``src/sirius`` en HEAD, y eso hacia
    que un avance de ``main`` —ajeno a ADR-002— pusiera rojo un control que
    vigila otra cosa. Lo que hay que garantizar es que T0 siga siendo T0, y eso
    se comprueba sobre lo que T0 de verdad ejecuta. Ver la fe de erratas 07.
    """
    assert custodia_t0.fallos_de_custodia_de_t0(RAIZ) == []


def test_la_excepcion_declarada_conserva_su_estructura() -> None:
    """``domain/decision.py`` cambio en ``main``; ``Decision`` no."""
    assert custodia_t0.fallos_de_la_excepcion_declarada(RAIZ) == []


def test_la_ficha_de_t0_sigue_declarando_el_arbol_de_su_commit() -> None:
    """La afirmacion literal de la ficha, comprobada donde la ficha la hace."""
    observado = subprocess.run(
        ["git", "rev-parse", f"{custodia_t0.COMMIT_DEL_PROTOTIPO}:src/sirius"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert observado == ARBOL_DE_FUENTES_DECLARADO


def test_el_arnes_no_implementa_el_contrato_de_candidato() -> None:
    """Si lo implementara, el motor comun podria ejecutarlo como candidato."""
    from experiments.adr002.candidates.common.contracts import SenalesDeCandidato

    assert not isinstance(T0.control(), SenalesDeCandidato)
    assert not hasattr(T0.ControlT0, "candidatas")
    assert not hasattr(T0.ControlT0, "leer")


def test_el_control_no_declara_senal_tardia() -> None:
    assert T0.control().senal_tardia_habilitada == "no_aplica_no_es_candidato"


# ---------------------------------------------------------------------------
# T0 responde a la misma peticion, y descarta casi toda
# ---------------------------------------------------------------------------


def test_responde_a_la_misma_peticion_que_reciben_los_candidatos(base: Path) -> None:
    respuesta = T0.control().responder(_peticion(), base)
    assert respuesta.ids
    assert respuesta.devueltos == len(respuesta.ids)


def test_declara_los_campos_de_la_peticion_que_ignora(base: Path) -> None:
    respuesta = T0.control().responder(_peticion(), base)
    for campo in ("ambito", "modo", "cardinalidad", "limite_duro", "ventana"):
        assert campo in respuesta.campos_ignorados, campo


def test_declara_las_capacidades_que_no_tiene(base: Path) -> None:
    respuesta = T0.control().responder(_peticion(), base)
    for capacidad in ("etapas_E0_E5", "puertas_G1_G12", "paradas_S1_S7"):
        assert capacidad in respuesta.capacidades_ausentes, capacidad


def test_reproduce_los_incumplimientos_declarados_por_su_ficha(base: Path) -> None:
    respuesta = T0.control().responder(_peticion(), base)
    assert set(respuesta.incumplimientos) == {"RF-06", "RF-14", "RF-19"}


# ---------------------------------------------------------------------------
# Los incumplimientos salen como RESULTADO, no se corrigen
# ---------------------------------------------------------------------------


def test_rf14_el_barrido_completo_se_mide_sobre_lo_ejecutado(base: Path) -> None:
    """No se deduce del codigo: se cuenta lo que la ejecucion recorrio.

    El universo es el canon **vigente** —lo que ``list_current_*`` devuelve—,
    no el total de filas del fixture: T0 recorre lo vigente entero para
    responder una sola consulta, y eso es ``RF-14``.
    """
    import sqlite3

    conexion = sqlite3.connect(str(base))
    try:
        vigentes = int(
            conexion.execute(
                "SELECT (SELECT count(*) FROM memories WHERE status = 'current') "
                "+ (SELECT count(*) FROM decisions WHERE status = 'approved')"
            ).fetchone()[0]
        )
    finally:
        conexion.close()

    respuesta = T0.control().responder(_peticion(), base)
    assert respuesta.universo_recorrido == vigentes
    assert respuesta.devueltos < respuesta.universo_recorrido
    assert respuesta.hubo_barrido_completo


def test_rf06_t0_devuelve_un_item_fuera_del_ambito_pedido(base: Path) -> None:
    """El arnes NO filtra por ambito: hacerlo ocultaria el incumplimiento.

    ``faro-ajeno`` pertenece al proyecto ajeno y la peticion acota al activo.
    ``ADR002-A`` lo descarta en ``G4``; T0 lo entrega.
    """
    respuesta = T0.control().responder(_peticion(), base)
    with PuertoSqlite(base) as puerto:
        ajenos = {
            i.id
            for i in puerto.por_termino_lexico(["faro"])
            if i.project_id == fixtures.PROYECTO_AJENO
        }
    assert ajenos, "el fixture debe tener al menos un item fuera de ambito"
    assert ajenos & set(respuesta.ids), "T0 debe exhibir su fallo de ambito"


def test_el_arnes_no_trunca_por_limite_duro(base: Path) -> None:
    """Truncar aqui inventaria una capacidad que T0 no tiene."""
    estrecha = Peticion(
        operation_id="t0-limite",
        consulta="faro",
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=False, proyectos=(fixtures.PROYECTO_ACTIVO,)),
        ventana=VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=1,
        limite_duro=1,
    )
    holgada = _peticion()
    control = T0.control()
    assert control.responder(estrecha, base).ids == control.responder(holgada, base).ids


# ---------------------------------------------------------------------------
# Contraste con un candidato: el control falsa, no compite
# ---------------------------------------------------------------------------


def test_t0_y_adr002_a_difieren_donde_la_ficha_dice_que_deben_diferir(base: Path) -> None:
    peticion = _peticion()
    with PuertoSqlite(base) as puerto:
        recuperacion = engine.recuperar(peticion, puerto, candidato())
    respuesta = T0.control().responder(peticion, base)

    assert recuperacion.parada.identificador, "A adjudica parada"
    assert respuesta.capacidades_ausentes, "T0 no adjudica ninguna"
    assert set(respuesta.ids) - set(recuperacion.ids), (
        "T0 debe entregar algo que A descarta por puerta: es el control de falsacion"
    )


def test_el_control_es_determinista(base: Path) -> None:
    control = T0.control()
    peticion = _peticion()
    assert control.responder(peticion, base).ids == control.responder(peticion, base).ids


def test_una_base_inexistente_falla_cerrado(tmp_path: Path) -> None:
    with pytest.raises(T0.ControlNoEjecutableError):
        T0.control().responder(_peticion(), tmp_path / "no-existe.sqlite3")


def test_una_consulta_sin_tokens_no_revienta(base: Path) -> None:
    """Contrato productivo: consulta vacia devuelve vacio, nunca error."""
    respuesta = T0.control().responder(_peticion(consulta="   ...   "), base)
    assert respuesta.ids == ()
    assert respuesta.universo_recorrido > 0
