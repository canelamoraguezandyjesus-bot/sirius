"""Comprobaciones ESTATICAS de la infraestructura comun y de ``ADR002-A``.

El acta de preinscripcion prohibe ejecutar el candidato antes de que su ficha
este congelada. Estas pruebas respetan esa guarda: **no instancian
``CandidatoA``, no construyen bases de datos y no ejecutan el motor**.
Inspeccionan estructura, contratos y neutralidad sobre el codigo y sobre los
tipos, que es todo lo que este commit permite.

Las pruebas funcionales llegan despues, en su propio commit, cuando el commit
de entrada de la ficha ya sea ancestro estricto.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from experiments.adr002.candidates.adr002_a import candidate as a
from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.common import contracts, engine, gates, neutrality, stops

RAIZ = Path(__file__).resolve().parents[3]


# --------------------------------------------------------------------------
# Neutralidad de la capa comun
# --------------------------------------------------------------------------


def test_la_capa_comun_es_neutral() -> None:
    """El control que da sentido a comparar candidatos entre si."""
    assert neutrality.fallos_de_neutralidad(RAIZ) == []


def test_el_candidato_no_reimplementa_el_motor_ni_las_puertas() -> None:
    assert neutrality.fallos_de_aislamiento_del_candidato(RAIZ, "adr002_a") == []


def test_el_control_de_neutralidad_denuncia_lo_que_debe(tmp_path: Path) -> None:
    """Un verificador que nunca denuncia no verifica nada."""
    comun = tmp_path / "experiments/adr002/candidates/common"
    comun.mkdir(parents=True)
    (comun / "sucio.py").write_text(
        "import numpy\nUMBRAL = 'ADR002-A'\nvector = 1\n", encoding="utf-8"
    )
    fallos = neutrality.fallos_de_neutralidad(tmp_path, ("sucio.py",))
    assert any("ADR002-A" in f for f in fallos)
    assert any("numpy" in f for f in fallos)
    assert any("vector" in f for f in fallos)


def test_la_prosa_honesta_no_hace_fallar_el_control(tmp_path: Path) -> None:
    """Nombrar lo prohibido para negarlo no es una violacion.

    Si lo fuera, la unica forma de pasar el control seria borrar la
    documentacion que explica por que la capa comun no usa vectores.
    """
    comun = tmp_path / "experiments/adr002/candidates/common"
    comun.mkdir(parents=True)
    (comun / "limpio.py").write_text(
        '"""Esta capa no contiene embeddings ni vector alguno."""\n'
        "# tampoco un indice_relacional derivado\n"
        "VALOR = 1\n",
        encoding="utf-8",
    )
    assert neutrality.fallos_de_neutralidad(tmp_path, ("limpio.py",)) == []


# --------------------------------------------------------------------------
# El contrato normativo, completo
# --------------------------------------------------------------------------


def test_las_seis_etapas_estan_en_orden() -> None:
    assert [e.value for e in contracts.ORDEN_DE_ETAPAS] == ["E0", "E1", "E2", "E3", "E4", "E5"]
    assert [e.value for e in contracts.ETAPAS_DE_EXPANSION] == ["E1", "E2", "E3", "E4"]


def test_las_doce_puertas_estan_completas_y_ordenadas() -> None:
    assert [g for g, _ in gates.PUERTAS] == [f"G{n}" for n in range(1, 13)]
    assert list(gates.PUERTAS_PREVIAS) == [f"G{n}" for n in range(1, 11)]
    assert gates.PUERTA_SEMANTICA == "G11"
    assert gates.PUERTA_CRITICIDAD == "G12"


def test_las_siete_paradas_estan_completas() -> None:
    assert list(stops.IDENTIFICADORES) == [f"S{n}" for n in range(1, 8)]


def test_s1_esta_deshabilitada_en_exhaustiva() -> None:
    """La regla de ``B04 §15.2`` que mas se olvida, hecha estructura."""
    assert not stops.s1_disponible(contracts.Cardinalidad.EXHAUSTIVA)
    assert stops.s1_disponible(contracts.Cardinalidad.EXACTA)
    assert stops.s1_disponible(contracts.Cardinalidad.ACOTADA)


def test_una_parada_desconocida_es_un_error() -> None:
    import pytest

    with pytest.raises(ValueError, match="parada desconocida"):
        stops.Parada("S9", "inventada")


def test_los_cinco_modos_existen() -> None:
    assert [m.value for m in contracts.Modo] == ["M1", "M2", "M3", "M4", "M5"]


def test_el_puerto_no_ofrece_ningun_barrido_completo() -> None:
    """Un metodo que devolviera el canon entero invitaria a saltarse etapas."""
    metodos = {
        n
        for n, _ in inspect.getmembers(contracts.PuertoDeRecuperacion, inspect.isfunction)
        if not n.startswith("_")
    }
    assert metodos == {
        "por_clave_exacta",
        "por_termino_lexico",
        "por_prefijo_de_sujeto",
        "historial_y_fuentes",
    }


def test_el_puerto_no_admite_identificadores_de_proyecto_como_generador() -> None:
    """Defecto 2: el ambito filtra en G4; no genera candidatos.

    ``por_entidad(project_ids)`` enumeraba el proyecto y filtraba despues. El
    metodo ya no existe, y su sustituto consulta prefijos de sujeto concretos.
    """
    assert not hasattr(contracts.PuertoDeRecuperacion, "por_entidad")
    codigo = (RAIZ / "experiments/adr002/candidates/adr002_a/candidate.py").read_text("utf-8")
    assert "por_entidad" not in codigo
    assert "ambito.proyectos" not in codigo


def test_el_ambito_aisla_por_construccion() -> None:
    """``G4``/``RF-06``: fuera de ambito no contamina."""
    global_ = contracts.Ambito(global_=True, proyectos=())
    cerrado = contracts.Ambito(global_=False, proyectos=("PRJ-UNO",))
    assert global_.autoriza("PRJ-DOS")
    assert cerrado.autoriza("PRJ-UNO")
    assert not cerrado.autoriza("PRJ-DOS")
    assert not cerrado.autoriza(None)


# --------------------------------------------------------------------------
# ADR002-A: identidad y forma, sin ejecutarlo
# --------------------------------------------------------------------------


def test_adr002_a_declara_su_definicion_canonica() -> None:
    """Literal de ``ARQ-00 §23``, no una parafrasis."""
    assert a.DEFINICION_CANONICA == (
        "expansion escalonada solo lexica/estructurada en todas las etapas E0-E5."
    )
    assert a.IDENTIFICADOR == "ADR002-A"


def test_adr002_a_no_habilita_senal_tardia_adicional() -> None:
    assert a.SENAL_TARDIA == "ninguna_adicional"


def test_adr002_a_declara_medios_para_las_cuatro_etapas_de_expansion() -> None:
    """``E3`` incluida: no declararla seria la degradacion que A no es."""
    assert set(a.MEDIOS_POR_ETAPA) == set(contracts.ETAPAS_DE_EXPANSION)
    for etapa, medio in a.MEDIOS_POR_ETAPA.items():
        assert len(medio.strip()) > 20, etapa


def test_adr002_a_satisface_el_protocolo_del_candidato() -> None:
    """Estructural: tiene lo que el motor exige, sin instanciarlo."""
    for miembro in ("identificador", "senal_tardia_habilitada", "candidatas", "leer"):
        assert hasattr(a.CandidatoA, miembro), miembro


def test_adr002_a_no_contiene_senal_vectorial_ni_indice_derivado() -> None:
    """La prohibicion vale tambien dentro del candidato: A es lexico o no es A.

    Para la capa comun la prohibicion nace de la neutralidad; para ``ADR002-A``
    nace de su propia definicion canonica, y por eso se comprueba aparte.
    """
    for nombre in ("candidate.py", "lexical.py"):
        codigo = (RAIZ / "experiments/adr002/candidates/adr002_a" / nombre).read_text("utf-8")
        sin_prosa = neutrality._sin_comentarios(codigo).lower()
        for termino in ("embedding", "coseno", "faiss", "hnsw", "knn"):
            assert termino not in sin_prosa, f"{nombre}: {termino}"
        for dependencia in neutrality.IMPORTS_PROHIBIDOS:
            assert f"import {dependencia}" not in sin_prosa


def test_adr002_a_no_es_t0() -> None:
    """T0 no implementa etapas ni puertas; A las recorre por el motor comun."""
    codigo = (RAIZ / "experiments/adr002/candidates/adr002_a/candidate.py").read_text("utf-8")
    assert "T0" in codigo  # lo declara expresamente para no confundirse con el
    assert "_e1" in codigo and "_e2" in codigo and "_e3" in codigo and "_e4" in codigo


# --------------------------------------------------------------------------
# Los recursos lexicos son deterministas
# --------------------------------------------------------------------------


def test_la_tokenizacion_pliega_diacriticos_como_el_indice() -> None:
    assert lexical.tokenizar("Está aquí, glaciar") == ("esta", "aqui", "glaciar")


def test_los_terminos_significativos_descartan_vacias_sin_perder_orden() -> None:
    assert lexical.terminos_significativos("el faro de la costa") == ("faro", "costa")


def test_la_raiz_y_las_variantes_son_deterministas() -> None:
    assert lexical.raiz("lanzaderas") == "lanzader"
    assert lexical.variantes("faro") == lexical.variantes("faro")
    assert "faro" in lexical.variantes("faro")


def test_la_negacion_y_la_condicion_se_detectan_por_marcador() -> None:
    assert lexical.polaridad_negativa("el faro no funciona")
    assert not lexical.polaridad_negativa("el faro funciona")
    assert lexical.condicion_declarada("si el faro funciona") == "si"
    assert lexical.condicion_declarada("el faro funciona") is None


def test_el_sujeto_prefiere_la_clave_del_canon() -> None:
    assert lexical.sujeto_estructural("MEM-P-1", "texto cualquiera") == "MEM-P-1"
    assert lexical.sujeto_estructural("", "faro de costa") == "faro"


# --------------------------------------------------------------------------
# El motor no mide y no toca el corpus oficial
# --------------------------------------------------------------------------


def _modulos_auditables() -> list[Path]:
    """Los modulos sujetos a los controles de contenido.

    Se excluyen las pruebas y el inventario de neutralidad por la misma razon:
    **nombran lo prohibido para prohibirlo**. Exigirles que no lo nombren
    obligaria a vaciar el inventario y a borrar las pruebas que lo comprueban,
    que es justo lo contrario de auditar.
    """
    base = RAIZ / "experiments/adr002/candidates"
    return [
        ruta
        for ruta in sorted(base.rglob("*.py"))
        if not ruta.name.startswith("test_") and ruta.name != neutrality.INVENTARIO_EXCLUIDO
    ]


def test_ningun_modulo_del_paquete_mide_ni_abre_red() -> None:
    """Este paquete recupera; medir es otro acto, con otra autorizacion."""
    for ruta in _modulos_auditables():
        codigo = ruta.read_text(encoding="utf-8")
        for prohibido in ("perf_counter", "time.time", "socket", "requests", "urllib.request"):
            assert prohibido not in codigo, f"{ruta.name} usa {prohibido}"


def test_el_paquete_no_referencia_el_corpus_oficial() -> None:
    """Evaluar a A con el corpus congelado exige una autorizacion que no existe."""
    for ruta in _modulos_auditables():
        codigo = ruta.read_text(encoding="utf-8")
        for prohibido in ("performance_corpus_v0_2", "conformance_corpus_v0_4"):
            assert prohibido not in codigo, f"{ruta.name} referencia {prohibido}"


def test_la_exclusion_del_inventario_es_exactamente_una() -> None:
    """La excepcion no se hereda: un modulo comun nuevo entra al control."""
    comunes = {r.name for r in (RAIZ / "experiments/adr002/candidates/common").glob("*.py")} - {
        "__init__.py"
    }
    assert comunes == {*neutrality.MODULOS_COMUNES, neutrality.INVENTARIO_EXCLUIDO}


def test_el_motor_expone_una_sola_entrada() -> None:
    """Un camino de codigo para todos: no hay via que solo un candidato tome."""
    publicas = [n for n in engine.__all__ if not n.startswith("_")]
    assert "recuperar" in publicas
    firma = inspect.signature(engine.recuperar)
    assert list(firma.parameters) == ["peticion", "puerto", "candidato"]
