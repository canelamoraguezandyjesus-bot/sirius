"""Contrato de la familia sucesora v0.6 · corrección de `B04-CA-19`.

Demuestra **solo** lo que la corrección exige y nada más:

1. `DEC-006`, `DEC-007` y `DEC-008` comparten sujeto;
2. comparten propiedad;
3. `CA-19` es estructuralmente agrupable;
4. cambiar la entidad de uno rompe la agrupacion;
5. cambiar la propiedad de uno rompe la agrupacion;
6. los canales se generan sin leer casos ni referencias;
7. el discriminante `MEM-950` → `MEM-951` continua en pie;
8. la v0.4 y la v0.5 permanecen byte a byte intactas;
9. `ADR002-TOL-208` permanece intacta.

Las mutaciones se ejecutan sobre copias en memoria: **el arbol no se toca**.
No ejecuta T0, no implementa ni ejecuta ADR002-A/B/C/D y no mide rendimiento.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.benchmark import build_corpus_v0_6 as B6
from experiments.adr002.benchmark import schema_v0_6 as S6
from experiments.adr002.benchmark import validate_corpus_v0_5 as V5
from experiments.adr002.benchmark import validate_corpus_v0_6 as V6

AQUI = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def artefactos() -> dict[str, Any]:
    return V6.cargar()


@pytest.fixture(scope="module")
def corpus(artefactos: dict[str, Any]) -> dict[str, Any]:
    return artefactos["conformance_corpus_v0_6.json"]


def _claves(corpus: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Regenera los dos canales con la regla aprobada sobre un corpus dado."""
    return B6.construir_subject_keys(corpus), B6.construir_property_keys(corpus)


# ---------------------------------------------------------------------------
# 1, 2 y 3 · el defecto corregido
# ---------------------------------------------------------------------------


def test_1_los_tres_items_de_ca19_comparten_sujeto(artefactos: dict[str, Any]) -> None:
    sujetos = {i: artefactos["subject_keys_v0_2.json"]["valores"][i] for i in S6.ITEMS_CA_19}
    assert len(set(sujetos.values())) == 1, sujetos
    assert None not in sujetos.values(), sujetos


def test_2_los_tres_items_de_ca19_comparten_propiedad(artefactos: dict[str, Any]) -> None:
    propiedades = {i: artefactos["property_keys_v0_2.json"]["valores"][i] for i in S6.ITEMS_CA_19}
    assert len(set(propiedades.values())) == 1, propiedades
    assert None not in propiedades.values(), propiedades


def test_3_ca19_es_estructuralmente_agrupable(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    """Ningun eje de la regla de agrupacion queda desconocido, y hay tres procedencias."""
    assert not B6.fallos_de_agrupabilidad_ca_19(
        artefactos["subject_keys_v0_2.json"], artefactos["property_keys_v0_2.json"]
    )
    afectados = [i for i in corpus["items"] if i["id"] in set(S6.ITEMS_CA_19)]
    procedencias = {tuple(i["procedencia"]) for i in afectados}
    assert len(procedencias) == 3, procedencias
    assert all(procedencias), procedencias


def test_3b_en_la_v0_5_ambos_ejes_eran_nulos() -> None:
    """El defecto era real: sin esto la correccion no tendria objeto."""
    sk = json.loads((AQUI / "subject_keys_v0_1.json").read_text(encoding="utf-8"))["valores"]
    pk = json.loads((AQUI / "property_keys_v0_1.json").read_text(encoding="utf-8"))["valores"]
    for ident in S6.ITEMS_CA_19:
        assert sk[ident] is None, ident
        assert pk[ident] is None, ident


def test_3c_las_claves_salen_del_generador_y_no_estan_escritas_a_mano(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    subject_keys, property_keys = _claves(corpus)
    assert subject_keys["valores"] == artefactos["subject_keys_v0_2.json"]["valores"]
    assert property_keys["valores"] == artefactos["property_keys_v0_2.json"]["valores"]


# ---------------------------------------------------------------------------
# 4 y 5 · mutaciones que DEBEN romper la agrupacion
# ---------------------------------------------------------------------------


def test_4_cambiar_la_entidad_de_uno_rompe_la_agrupacion(corpus: dict[str, Any]) -> None:
    mutado = copy.deepcopy(corpus)
    mutado["entidades"].append(
        {
            "id": "ENT-OTRA-PLATAFORMA",
            "nombre_canonico": "plataforma alterna",
            "alias": [],
            "grupo_homonimo": None,
            "nota": "mutacion de prueba",
        }
    )
    for item in mutado["items"]:
        if item["id"] == "DEC-008":
            item["entity_ids"] = ["ENT-OTRA-PLATAFORMA"]
    subject_keys, property_keys = _claves(mutado)
    fallos = B6.fallos_de_agrupabilidad_ca_19(subject_keys, property_keys)
    assert fallos, "cambiar la entidad de uno debe romper la agrupacion"
    assert any("sujeto" in f for f in fallos), fallos


def test_4b_quitar_la_entidad_de_uno_devuelve_el_defecto(corpus: dict[str, Any]) -> None:
    mutado = copy.deepcopy(corpus)
    for item in mutado["items"]:
        if item["id"] == "DEC-007":
            item["entity_ids"] = []
    subject_keys, property_keys = _claves(mutado)
    assert subject_keys["valores"]["DEC-007"] is None
    assert property_keys["valores"]["DEC-007"] is None
    assert B6.fallos_de_agrupabilidad_ca_19(subject_keys, property_keys)


def test_5_cambiar_la_propiedad_de_uno_rompe_la_agrupacion(corpus: dict[str, Any]) -> None:
    """Mismo sujeto, predicado distinto: la clave lateral debe separarlos."""
    mutado = copy.deepcopy(corpus)
    for item in mutado["items"]:
        if item["id"] == "DEC-006":
            item["text"] = "La plataforma de despliegue aprobada queda revocada."
    subject_keys, property_keys = _claves(mutado)
    assert len({subject_keys["valores"][i] for i in S6.ITEMS_CA_19}) == 1
    fallos = B6.fallos_de_agrupabilidad_ca_19(subject_keys, property_keys)
    assert fallos, "cambiar el predicado de uno debe romper la agrupacion"
    assert any("propiedad" in f for f in fallos), fallos


def test_5b_un_texto_distinto_en_uno_de_los_tres_aborta_la_construccion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La entidad se justifica por el texto: si el texto no es ese, no hay caso."""
    from experiments.adr002.benchmark import canonical_source_v0_4 as CS4

    monkeypatch.setattr(S6, "TEXTO_COMPARTIDO_CA_19", "Otro texto que nadie escribio.")
    with pytest.raises(S6.ContratoFamiliaV06Error):
        B6.construir_corpus_conformidad(CS4.cargar_canon())


def test_5c_la_entidad_en_un_cuarto_item_la_detecta_el_validador(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    mutado = copy.deepcopy(corpus)
    for item in mutado["items"]:
        if item["id"] == "DEC-009":
            item["entity_ids"] = [S6.ENTIDAD_CA_19]
    inf = V6.Informe()
    V6._ca_19(
        mutado,
        artefactos["subject_keys_v0_2.json"],
        artefactos["property_keys_v0_2.json"],
        inf,
    )
    assert inf.fallos


# ---------------------------------------------------------------------------
# 6 · los canales no leen casos ni referencias
# ---------------------------------------------------------------------------


def test_6_los_canales_se_generan_sin_leer_casos_ni_referencias(
    corpus: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Se instrumenta la lectura de ficheros: lo que no se abre no se puede leer."""
    abiertos: list[str] = []
    lee_bytes, lee_texto = Path.read_bytes, Path.read_text

    def espia_bytes(self: Path, *a: Any, **k: Any) -> bytes:
        abiertos.append(self.name)
        return lee_bytes(self, *a, **k)

    def espia_texto(self: Path, *a: Any, **k: Any) -> str:
        abiertos.append(self.name)
        return lee_texto(self, *a, **k)

    monkeypatch.setattr(Path, "read_bytes", espia_bytes)
    monkeypatch.setattr(Path, "read_text", espia_texto)
    B6.construir_subject_keys(corpus)
    B6.construir_property_keys(corpus)

    prohibidos = [
        f for f in abiertos if any(p in f for p in ("cases_", "references_", "t0_preexecution"))
    ]
    assert not prohibidos, prohibidos
    assert abiertos == [], abiertos


def test_6b_las_firmas_no_admiten_ningun_artefacto_de_oraculo() -> None:
    import inspect

    for nombre in ("construir_subject_keys", "construir_property_keys"):
        assert list(inspect.signature(getattr(B6, nombre)).parameters) == ["corpus"], nombre


# ---------------------------------------------------------------------------
# 7 · el discriminante relacional continua en pie
# ---------------------------------------------------------------------------


def test_7_el_discriminante_mem950_mem951_continua(
    corpus: dict[str, Any], artefactos: dict[str, Any]
) -> None:
    """Los extremos, la arista y sus claves son identicos a los de la v0.5.

    Con entradas identicas el comportamiento de la recuperacion es identico por
    determinismo, y la prueba funcional real sobre `ADR002-A` sigue ejecutandose
    sin cambios en ``candidates/test_adr002_discriminante_relacional.py``.
    """
    v0_5 = json.loads((AQUI / "conformance_corpus_v0_5.json").read_text(encoding="utf-8"))
    v0_5_sk = json.loads((AQUI / "subject_keys_v0_1.json").read_text(encoding="utf-8"))["valores"]
    por_id_6 = {i["id"]: i for i in corpus["items"]}
    por_id_5 = {i["id"]: i for i in v0_5["items"]}

    for ident in (S6.ITEM_ORIGEN_DELTA, S6.ITEM_DESTINO_DELTA):
        assert por_id_6[ident] == por_id_5[ident], ident
        assert artefactos["subject_keys_v0_2.json"]["valores"][ident] == v0_5_sk[ident]

    assert corpus["relaciones"] == v0_5["relaciones"]
    arista = next(r for r in corpus["relaciones"] if r["id"] == S6.RELACION_DELTA)
    assert arista["tipo"] == S6.TIPO_RELACION_DELTA
    assert (arista["origen"], arista["destino"]) == (
        S6.ITEM_ORIGEN_DELTA,
        S6.ITEM_DESTINO_DELTA,
    )

    origen = por_id_6[S6.ITEM_ORIGEN_DELTA]["text"]
    destino = por_id_6[S6.ITEM_DESTINO_DELTA]["text"]
    assert not (V5._terminos_del_indice([origen]) & V5._terminos_del_indice([destino]))

    en_ambito = [i["id"] for i in corpus["items"] if i["project_id"] == S6.PROYECTO_DELTA]
    assert sorted(en_ambito) == sorted([S6.ITEM_ORIGEN_DELTA, S6.ITEM_DESTINO_DELTA])


# ---------------------------------------------------------------------------
# 8 y 9 · custodia
# ---------------------------------------------------------------------------


def test_8_v0_4_y_v0_5_permanecen_byte_a_byte() -> None:
    for blobs in (S6.BLOBS_V0_4, S6.BLOBS_V0_5):
        for nombre, esperado in blobs.items():
            assert V5._blob_git((AQUI / nombre).read_bytes()) == esperado, nombre


def test_8b_los_heredados_se_heredan_por_blob_y_no_se_regeneran() -> None:
    for nombre, esperado in S6.HEREDADOS_V0_6.items():
        assert V5._blob_git((AQUI / nombre).read_bytes()) == esperado, nombre
    for nombre in ("cases_v0_6.json", "references_v0_6.json", "applied_criticality_v0_2.json"):
        assert not (AQUI / nombre).exists(), nombre


def test_9_tol_208_permanece_intacta() -> None:
    from experiments.adr002.rederivation import rederivation_protocol as rp

    raiz = AQUI.parents[2]
    for ruta, esperado in rp.CORPUS_CONGELADO.items():
        assert V5._blob_git((raiz / ruta).read_bytes()) == esperado, ruta
    assert V5._blob_git((raiz / rp.LINEA_BASE_HISTORICA).read_bytes()) == rp.BLOB_LINEA_BASE


# ---------------------------------------------------------------------------
# Cierre · el validador y el barrido
# ---------------------------------------------------------------------------


def test_el_validador_v0_6_esta_en_verde() -> None:
    inf, _ = V6.validar()
    assert inf.fallos == [], inf.fallos


def test_el_barrido_no_altera_ninguna_adjudicacion_heredada(corpus: dict[str, Any]) -> None:
    from experiments.adr002.benchmark import build_corpus_v0_5 as B5
    from experiments.adr002.benchmark import canonical_source_v0_4 as CS4

    base = B5.construir_corpus_conformidad(CS4.cargar_canon())
    barrido = B6.barrido_impacto_ca_19(base, corpus)
    assert barrido["cambios"] == []
    assert barrido["adjudicaciones_recalculadas"] == S6.DOMINIOS_RECALCULADOS
