"""Las tres correcciones que la ronda primaria hizo necesarias.

Cada control está escrito como el defecto que la medición encontró, no como el
comportamiento que se desea: así, si alguna de las tres se revirtiera, la
prueba diría **qué** se rompió y no solo que algo falla.

Los tres defectos, medidos sobre la familia de conformidad v0.6 y publicados en
`artifacts/adr002_round/ronda_primaria_v0.1.json`:

* 66 lecturas de polaridad invertidas, de las que salían 38 fusiones;
* un elemento **aún no vigente** que pasaba la puerta del tiempo;
* un elemento `ARCHIVADA` que pasaba la puerta de disponibilidad.

No miden rendimiento y no ejecutan el benchmark.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.common import gates
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Candidata,
    Cardinalidad,
    Clase,
    EjesDeclarados,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
    Modo,
    Peticion,
    Polaridad,
    VentanaTemporal,
)

RAIZ: Final = Path(__file__).resolve().parents[3]
CORPUS: Final = RAIZ / "experiments/adr002/benchmark/conformance_corpus_v0_6.json"

OBJETIVO: Final = "2026-04-01T00:00:00Z"


def _item(**cambios: object) -> ItemCanonico:
    base: dict[str, object] = {
        "id": "MEMORIA:1",
        "clase": Clase.MEMORIA,
        "project_id": "1",
        "texto": "texto",
        "subject_key": "sujeto",
        "vigente": True,
        "disponible": True,
        "created_at": "2026-01-01T00:00:00Z",
        "ejes": EjesDeclarados(),
    }
    base.update(cambios)
    return ItemCanonico(**base)  # type: ignore[arg-type]


def _candidata(item: ItemCanonico) -> Candidata:
    return Candidata(
        item=item,
        etapa=Etapa.E1,
        lectura=LecturaSemantica(
            sujeto="sujeto", polaridad=Polaridad.AFIRMATIVA, condicion=None, tiempo=None, medio="x"
        ),
        razon="prueba",
        senal="clave_exacta",
    )


def _peticion(*, modo: Modo = Modo.M1_ORDINARIO, admite_no_vigentes: bool = False) -> Peticion:
    return Peticion(
        operation_id="correccion",
        consulta="consulta",
        proposito="responder_al_usuario",
        modo=modo,
        ambito=Ambito(global_=True, proyectos=()),
        ventana=VentanaTemporal(tiempo_objetivo=OBJETIVO),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=10,
        limite_duro=10,
        admite_no_vigentes=admite_no_vigentes,
    )


def _pasa(item: ItemCanonico, peticion: Peticion) -> gates.Filtrado:
    return gates.aplicar_previas([_candidata(item)], peticion)


# ---------------------------------------------------------------------------
# D1 · El alcance de la negación, no su presencia
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "negativa"),
    [
        # Los tres que el canon declara NEGATIVA. Perder uno sería peor que el
        # defecto que se corrige: dejaría de distinguirse lo que RF-19 protege.
        ("En este viaje no se alquila coche.", True),
        ("No uses opciones de vuelo con escala.", True),
        ("No usar PostgreSQL en este proyecto.", True),
        # `sin` como preposición modifica; no niega la afirmación.
        ("El usuario prefiere que redactes en tono directo y sin adornos.", False),
        # El marcador tras conjunción subordinante niega la subordinada.
        ("El contrato de mantenimiento se renovó, pero no consta desde cuándo.", False),
        ("Se aprobó el presupuesto aunque no se firmó el anexo.", False),
        # Lo que sigue a dos puntos es contenido citado.
        ("Nota marcada por el usuario: no uses esto como memoria.", False),
    ],
    ids=[
        "negacion-principal-1",
        "negacion-principal-2",
        "negacion-principal-3",
        "sin-modifica",
        "pero-subordina",
        "aunque-subordina",
        "dos-puntos-citan",
    ],
)
def test_la_negacion_se_lee_por_su_alcance(texto: str, negativa: bool) -> None:
    assert lexical.polaridad_negativa(texto) is negativa


def test_ninguna_polaridad_del_corpus_se_lee_al_reves() -> None:
    """La comprobación de resta: cero discrepancias sobre los 97 elementos.

    La ronda primaria midió 66. Esta prueba fija el resultado en cero y falla
    en cuanto vuelva a haber una, sea por una regresión del detector o por un
    elemento nuevo que el corpus añada.
    """
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    discrepantes = [
        item["id"]
        for item in corpus["items"]
        if item.get("polaridad")
        != ("NEGATIVA" if lexical.polaridad_negativa(item["text"]) else "AFIRMATIVA")
    ]
    assert discrepantes == []


# ---------------------------------------------------------------------------
# D2 · La puerta del tiempo mira la aplicabilidad, no solo el corte
# ---------------------------------------------------------------------------


def test_lo_que_aun_no_esta_en_vigor_no_entra() -> None:
    """El defecto medido: `B04-CA-26` recibía un elemento vigente desde mayo."""
    futuro = _item(ejes=EjesDeclarados(valid_from="2026-05-01T00:00:00Z"))
    filtrado = _pasa(futuro, _peticion())
    assert filtrado.admitidas == ()
    assert any(p == "G8" and "aun no vigente" in m for _i, p, m in filtrado.descartes)


def test_lo_que_aun_no_esta_en_vigor_tampoco_entra_en_modo_historico() -> None:
    """Consultar el pasado no permite recuperar lo que aún no había empezado."""
    futuro = _item(ejes=EjesDeclarados(valid_from="2026-05-01T00:00:00Z"))
    assert _pasa(futuro, _peticion(modo=Modo.M2_HISTORICO, admite_no_vigentes=True)).admitidas == ()


def test_lo_expirado_no_entra_en_modo_ordinario_y_si_en_el_historico() -> None:
    """Es la otra mitad: «admite no vigentes» significa exactamente esto."""
    expirado = _item(
        ejes=EjesDeclarados(valid_from="2026-01-01T00:00:00Z", valid_to="2026-03-01T00:00:00Z")
    )
    assert _pasa(expirado, _peticion()).admitidas == ()
    historico = _peticion(modo=Modo.M2_HISTORICO, admite_no_vigentes=True)
    assert len(_pasa(expirado, historico).admitidas) == 1


def test_lo_vigente_en_el_instante_entra() -> None:
    vigente = _item(ejes=EjesDeclarados(valid_from="2026-01-01T00:00:00Z", valid_to=None))
    assert len(_pasa(vigente, _peticion()).admitidas) == 1


def test_sin_ejes_temporales_la_puerta_degrada_al_corte_como_antes() -> None:
    """Un sustrato que no declara la ventana no puede ser juzgado por ella."""
    sin_ejes = _item(ejes=EjesDeclarados())
    assert len(_pasa(sin_ejes, _peticion()).admitidas) == 1


# ---------------------------------------------------------------------------
# D3a · La puerta de disponibilidad lee el eje, no el estado colapsado
# ---------------------------------------------------------------------------


def test_lo_archivado_no_entra_en_un_modo_ordinario() -> None:
    """El defecto medido: `B04-CA-04` recibía un elemento `ARCHIVADA`.

    El colapso de estado de Sirius 0.1 lo marca `archived` y `disponible` solo
    cae para lo borrado, de modo que ninguna puerta lo veía.
    """
    archivado = _item(ejes=EjesDeclarados(disponibilidad="ARCHIVADA"))
    filtrado = _pasa(archivado, _peticion())
    assert filtrado.admitidas == ()
    assert any(p == "G2" and "ARCHIVADA" in m for _i, p, m in filtrado.descartes)


def test_lo_archivado_sigue_siendo_inspeccionable_por_quien_puede() -> None:
    """Archivado no es borrado: existe, y `M3`/`M4` lo inspeccionan."""
    archivado = _item(ejes=EjesDeclarados(disponibilidad="ARCHIVADA"))
    assert len(_pasa(archivado, _peticion(modo=Modo.M4_GESTION)).admitidas) == 1


def test_lo_borrado_sigue_desapareciendo_para_todos() -> None:
    """La mitad vieja de `G2` no se toca: lo borrado no se degrada, se va."""
    borrado = _item(disponible=False)
    for modo in (Modo.M1_ORDINARIO, Modo.M3_FUENTE, Modo.M4_GESTION):
        assert _pasa(borrado, _peticion(modo=modo)).admitidas == ()


def test_lo_disponible_entra() -> None:
    disponible = _item(ejes=EjesDeclarados(disponibilidad="DISPONIBLE"))
    assert len(_pasa(disponible, _peticion()).admitidas) == 1
