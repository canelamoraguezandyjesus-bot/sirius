"""La proyeccion experimental: que sea fiel, cerrada y ciega al oraculo.

Estas pruebas no miden nada ni ejecutan el benchmark. Comprueban tres cosas
que, si se rompieran, invalidarian cualquier medicion posterior:

* que la proyeccion **no toca el esquema canonico** ni el arbol de Sirius 0.1;
* que **la capacidad gobierna el acceso**: un candidato no obtiene el plano
  reservado, y no por convencion sino porque la llamada falla;
* que **el oraculo no entra**: ni por firma, ni por campo, ni por descuido.
"""

from __future__ import annotations

import copy
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.candidates.adr002_a.candidate import candidato
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    ItemCanonico,
    Modo,
    Peticion,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.projection import build
from experiments.adr002.projection import contracts as P

from sirius.adapters.persistence.migrations import upgrade_to_head

RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parents[3]

#: Arbol Git de ``src/sirius`` declarado por la ficha congelada de ``T0``.
ARBOL_DE_FUENTES_DECLARADO = "6d8558ef1fe4994cb15a12967525bf3496b3c0b8"


@pytest.fixture(scope="module")
def familia() -> dict[str, Any]:
    return build.cargar_familia()


@pytest.fixture(scope="module")
def proyeccion(tmp_path_factory: pytest.TempPathFactory) -> P.ProyeccionExperimental:
    return build.construir_desde_la_familia(tmp_path_factory.mktemp("proyeccion") / "v0_6")


def _peticion(consulta: str, proyectos: tuple[str, ...] = ("2",)) -> Peticion:
    return Peticion(
        operation_id="proyeccion",
        consulta=consulta,
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=False, proyectos=proyectos),
        ventana=VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=10,
        limite_duro=10,
    )


# ---------------------------------------------------------------------------
# No modifica Sirius 0.1
# ---------------------------------------------------------------------------


def test_la_proyeccion_no_toca_el_arbol_de_fuentes() -> None:
    observado = subprocess.run(
        ["git", "rev-parse", "HEAD:src/sirius"],
        cwd=RAIZ_DEL_REPOSITORIO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert observado == ARBOL_DE_FUENTES_DECLARADO


def test_el_plano_de_entrada_es_el_esquema_canonico_sin_ddl_adicional(
    proyeccion: P.ProyeccionExperimental, tmp_path: Path
) -> None:
    """Una tabla de mas aqui romperia la garantia sobre la que el puerto vive."""
    virgen = tmp_path / "virgen.sqlite3"
    upgrade_to_head(virgen)
    esperado = _objetos(sqlite3.connect(str(virgen)))
    observado = _objetos(sqlite3.connect(str(proyeccion.ruta_de_entrada())))
    assert observado == esperado


def _objetos(conexion: sqlite3.Connection) -> set[tuple[str, str]]:
    try:
        return {
            (str(fila[0]), str(fila[1]))
            for fila in conexion.execute("SELECT type, name FROM sqlite_master")
        }
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# La capacidad gobierna el acceso
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("candidato_id", ["ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D"])
def test_ningun_candidato_abre_el_plano_reservado(
    proyeccion: P.ProyeccionExperimental, candidato_id: str
) -> None:
    with pytest.raises(P.AccesoNoAutorizadoError):
        proyeccion.abrir(P.Plano.RESERVADO, candidato_id)


def test_common_y_b05_si_abren_el_plano_reservado(proyeccion: P.ProyeccionExperimental) -> None:
    for consumidor in ("common", "B05"):
        conexion = proyeccion.abrir(P.Plano.RESERVADO, consumidor)
        conexion.close()


def test_b05_no_abre_los_planos_de_entrada(proyeccion: P.ProyeccionExperimental) -> None:
    """B05 recibe el handoff, no el canal de recuperacion."""
    for plano in (P.Plano.ENTRADA, P.Plano.EJES_P2):
        with pytest.raises(P.AccesoNoAutorizadoError):
            proyeccion.abrir(plano, "B05")


def test_el_plano_reservado_se_abre_en_solo_lectura(
    proyeccion: P.ProyeccionExperimental,
) -> None:
    conexion = proyeccion.abrir(P.Plano.RESERVADO, "common")
    try:
        with pytest.raises(sqlite3.OperationalError):
            conexion.execute("DELETE FROM property_key")
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# El oraculo no entra
# ---------------------------------------------------------------------------


def test_el_constructor_solo_conoce_cuatro_artefactos() -> None:
    assert P.ARTEFACTOS_FUENTE == (
        "conformance_corpus_v0_6.json",
        "subject_keys_v0_2.json",
        "property_keys_v0_2.json",
        "applied_criticality_v0_1.json",
    )


@pytest.mark.parametrize(
    "prohibido",
    ["cases_v0_", "references_v0_", "resultado_esperado", "elegibles", "grupos_esperados"],
)
def test_el_generador_no_nombra_ningun_artefacto_de_oraculo(prohibido: str) -> None:
    fuente = (Path(build.__file__).read_text(encoding="utf-8")) + (
        Path(P.__file__).read_text(encoding="utf-8")
    )
    assert prohibido not in fuente


@pytest.mark.parametrize(
    "columna_prohibida",
    ["nota", "grupo_homonimo", "traza", "fuente"],
)
def test_ningun_plano_materializa_una_columna_de_oraculo(
    proyeccion: P.ProyeccionExperimental, columna_prohibida: str
) -> None:
    """``criticidad.fuente`` bruta porta identificadores de caso del banco."""
    for plano, consumidor in ((P.Plano.EJES_P2, "common"), (P.Plano.RESERVADO, "common")):
        conexion = proyeccion.abrir(plano, consumidor)
        try:
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall():
                columnas = {
                    str(c[1]) for c in conexion.execute(f"PRAGMA table_info({fila[0]})").fetchall()
                }
                assert columna_prohibida not in columnas, f"{fila[0]}.{columna_prohibida}"
        finally:
            conexion.close()


def test_la_criticidad_aplicada_no_arrastra_identificadores_de_caso(
    proyeccion: P.ProyeccionExperimental,
) -> None:
    """El control es preventivo: hoy ninguno coincide, y si coincidiera, falla."""
    from experiments.adr002.benchmark import schema_v0_5 as S5

    conexion = proyeccion.abrir(P.Plano.RESERVADO, "common")
    try:
        for fila in conexion.execute(
            "SELECT razon_segura, regla_de_politica FROM criticidad_aplicada"
        ):
            for valor in fila:
                assert not S5.contiene_identificador_de_caso(valor or "")
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# Identidad canonica
# ---------------------------------------------------------------------------


def test_la_identidad_no_depende_del_orden_de_recorrido() -> None:
    assert P.identidad_canonica("MEM-007") == "MEMORIA:7"
    assert P.identidad_canonica("MEM-950") == "MEMORIA:950"
    assert P.identidad_canonica("DEC-006") == "DECISION:6"
    assert P.identidad_canonica("MSG-030") == "MENSAJE:30"


def test_una_referencia_sin_identidad_canonica_devuelve_none() -> None:
    """Entidades y proyectos **no** son elementos del canon."""
    assert P.referencia_canonica("ENT-ROTOR") is None
    assert P.referencia_canonica("PRJ-ALFA") is None
    assert P.referencia_canonica("MEM-950") == "MEMORIA:950"


def test_un_identificador_ajeno_falla_cerrado() -> None:
    with pytest.raises(P.ProyeccionError):
        P.identidad_canonica("ENT-ROTOR")
    with pytest.raises(P.ProyeccionError):
        P.identidad_canonica("MEM-000")


def test_una_colision_de_identidad_aborta_la_construccion(
    familia: dict[str, Any], tmp_path: Path
) -> None:
    corpus = copy.deepcopy(familia["conformance_corpus_v0_6.json"])
    corpus["items"].append(copy.deepcopy(corpus["items"][0]))
    with pytest.raises(P.ProyeccionError, match="colision"):
        build.construir(
            tmp_path / "colision",
            corpus=corpus,
            sujetos=familia["subject_keys_v0_2.json"]["valores"],
            propiedades=familia["property_keys_v0_2.json"]["valores"],
            criticidad=familia["applied_criticality_v0_1.json"]["valores"],
        )


# ---------------------------------------------------------------------------
# Fallo cerrado
# ---------------------------------------------------------------------------


def test_un_valor_fuera_del_vocabulario_p2_aborta(familia: dict[str, Any], tmp_path: Path) -> None:
    corpus = copy.deepcopy(familia["conformance_corpus_v0_6.json"])
    corpus["items"][0]["validez"] = "PROBABLEMENTE_VIGENTE"
    with pytest.raises(P.ProyeccionError, match="vocabulario"):
        build.construir(
            tmp_path / "vocabulario",
            corpus=corpus,
            sujetos=familia["subject_keys_v0_2.json"]["valores"],
            propiedades=familia["property_keys_v0_2.json"]["valores"],
            criticidad=familia["applied_criticality_v0_1.json"]["valores"],
        )


def test_una_decision_purgada_no_se_proyecta_al_estado_mas_parecido() -> None:
    """``DecisionStatus`` no tiene equivalente: se aborta en vez de aproximar."""
    with pytest.raises(P.ProyeccionImposibleError):
        P.estado_de_decision("CONFIRMADA", "VIGENTE", "PURGADA")


def test_un_canal_lateral_incompleto_aborta(familia: dict[str, Any], tmp_path: Path) -> None:
    propiedades = dict(familia["property_keys_v0_2.json"]["valores"])
    del propiedades["MEM-001"]
    with pytest.raises(P.ProyeccionError, match="incompleto"):
        build.construir(
            tmp_path / "incompleto",
            corpus=familia["conformance_corpus_v0_6.json"],
            sujetos=familia["subject_keys_v0_2.json"]["valores"],
            propiedades=propiedades,
            criticidad=familia["applied_criticality_v0_1.json"]["valores"],
        )


# ---------------------------------------------------------------------------
# Ausencia declarada, nunca inventada
# ---------------------------------------------------------------------------


def test_los_canales_laterales_son_totales_con_null_incluido(
    proyeccion: P.ProyeccionExperimental, familia: dict[str, Any]
) -> None:
    total = len(familia["conformance_corpus_v0_6.json"]["items"])
    conexion = proyeccion.abrir(P.Plano.RESERVADO, "common")
    try:
        for tabla in ("property_key", "criticidad_aplicada"):
            filas = int(conexion.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0])
            assert filas == total, tabla
        nulos = int(
            conexion.execute("SELECT count(*) FROM property_key WHERE valor IS NULL").fetchone()[0]
        )
        assert nulos == 85, "la ausencia se declara, no se omite"
    finally:
        conexion.close()


def test_una_property_key_nula_no_hace_inelegible_al_elemento(
    proyeccion: P.ProyeccionExperimental,
) -> None:
    """La ausencia impide agrupar; **no** excluye. Son cosas distintas."""
    conexion = proyeccion.abrir(P.Plano.RESERVADO, "common")
    try:
        sin_propiedad = {
            str(f[0])
            for f in conexion.execute("SELECT identidad FROM property_key WHERE valor IS NULL")
        }
    finally:
        conexion.close()
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperados = {i.id for i in puerto.por_termino_lexico(["presupuesto"])}
    assert recuperados & sin_propiedad, "un item sin propiedad sigue siendo recuperable"


def test_el_sujeto_ausente_no_se_fabrica(proyeccion: P.ProyeccionExperimental) -> None:
    """Fabricarlo seria ``P-SUJETO-01``, la proyeccion expresamente descartada.

    La proyeccion escribe cadena vacia porque ``decisions.subject`` es
    ``NOT NULL``; el puerto corregido la vuelve a leer como ``None``, de modo
    que la ausencia llega al motor **como ausencia** y no como sujeto en blanco.
    """
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        sin_sujeto = puerto.por_identificadores(["MEMORIA:1"]).items
        assert sin_sujeto[0].subject_key is None
        assert not sin_sujeto[0].sujeto_determinado
        # Y una clave vacia no alcanza nada ni por clave exacta ni por prefijo.
        assert puerto.por_clave_exacta([""]) == ()
        assert puerto.por_prefijo_de_sujeto([""]) == ()


# ---------------------------------------------------------------------------
# Los dos mecanismos, separados
# ---------------------------------------------------------------------------


def test_la_identidad_exacta_no_consulta_sujeto_ni_propiedad() -> None:
    clases = P.clases_por_identidad_exacta(["MEMORIA:1", "MEMORIA:1", "DECISION:6"])
    assert clases == {"DECISION:6": ("DECISION:6",), "MEMORIA:1": ("MEMORIA:1", "MEMORIA:1")}


def test_la_equivalencia_candidata_es_exactamente_la_de_ca_19(
    familia: dict[str, Any],
) -> None:
    sujetos = {
        P.identidad_canonica(k): v for k, v in familia["subject_keys_v0_2.json"]["valores"].items()
    }
    propiedades = {
        P.identidad_canonica(k): v for k, v in familia["property_keys_v0_2.json"]["valores"].items()
    }
    clases = P.clases_candidatas_de_equivalencia(sujetos, propiedades)
    assert list(clases.values()) == [("DECISION:6", "DECISION:7", "DECISION:8")]


def test_un_eje_ausente_nunca_agrupa() -> None:
    """La duda no fusiona: dos ejes conocidos y uno nulo no forman clase."""
    sujetos = {"MEMORIA:1": "vehiculo", "MEMORIA:2": "vehiculo", "MEMORIA:3": None}
    propiedades = {"MEMORIA:1": "PK-aaa", "MEMORIA:2": None, "MEMORIA:3": "PK-aaa"}
    assert P.clases_candidatas_de_equivalencia(sujetos, propiedades) == {}


def test_la_equivalencia_no_es_identidad(proyeccion: P.ProyeccionExperimental) -> None:
    """Los tres de ``CA-19`` comparten propiedad y **siguen siendo tres**."""
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        materializacion = puerto.por_identificadores(["DECISION:6", "DECISION:7", "DECISION:8"])
    assert len({i.id for i in materializacion.items}) == 3


# ---------------------------------------------------------------------------
# Perdidas declaradas: lo que el canon no puede sostener viaja en ejes_p2
# ---------------------------------------------------------------------------


def test_los_tres_ejes_de_estado_viajan_intactos(proyeccion: P.ProyeccionExperimental) -> None:
    """El estado del canon colapsa tres ejes; ``ejes_p2`` los conserva."""
    conexion = proyeccion.abrir(P.Plano.EJES_P2, "common")
    try:
        fila = conexion.execute(
            "SELECT confirmacion, validez, disponibilidad FROM ejes_del_item "
            "WHERE corpus_id = 'MEM-008'"
        ).fetchone()
    finally:
        conexion.close()
    assert tuple(fila) == ("RECHAZADA", "VIGENTE", "DISPONIBLE")
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        item = puerto.por_identificadores(["MEMORIA:8"]).items[0]
    # El canon solo puede decir "no vigente": por que no lo es, lo dice el eje.
    assert not item.vigente


def test_la_lista_cerrada_conserva_sus_miembros(proyeccion: P.ProyeccionExperimental) -> None:
    """Una clave foranea no puede expresar un ambito multiproyecto cerrado."""
    conexion = proyeccion.abrir(P.Plano.EJES_P2, "common")
    try:
        miembros = {
            str(f[0])
            for f in conexion.execute(
                "SELECT miembro FROM miembros_de_lista_cerrada WHERE lista = 'LISTA-CERRADA-AB'"
            )
        }
    finally:
        conexion.close()
    assert miembros == {"PRJ-ALFA", "PRJ-BETA"}


def test_polaridad_y_condicion_no_cruzan_a_item_canonico(
    proyeccion: P.ProyeccionExperimental,
) -> None:
    """Entregarlas sustituiria por el dato lo que ``RF-19`` mide."""
    assert not hasattr(ItemCanonico, "polaridad")
    assert set(P.CAMPOS_QUE_NO_CRUZAN_A_ITEM_CANONICO) == {"polaridad", "condicion"}
    conexion = proyeccion.abrir(P.Plano.EJES_P2, "common")
    try:
        negativas = int(
            conexion.execute(
                "SELECT count(*) FROM ejes_reservados_al_arnes WHERE polaridad = 'NEGATIVA'"
            ).fetchone()[0]
        )
    finally:
        conexion.close()
    assert negativas == 3, "siguen materializadas; lo que no hacen es cruzar"


def test_el_item_global_no_tiene_proyecto(proyeccion: P.ProyeccionExperimental) -> None:
    """``ambito GLOBAL`` se proyecta como ``project_id`` nulo, que es su forma."""
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        item = puerto.por_identificadores(["MEMORIA:1"]).items[0]
    assert item.project_id is None
    assert not Ambito(global_=False, proyectos=("2",)).autoriza(item.project_id)
    assert Ambito(global_=True, proyectos=()).autoriza(item.project_id)


# ---------------------------------------------------------------------------
# Relaciones: una materializada, nueve no
# ---------------------------------------------------------------------------


def test_solo_la_supersesion_entre_decisiones_esta_en_el_canon(
    proyeccion: P.ProyeccionExperimental,
) -> None:
    conexion = proyeccion.abrir(P.Plano.EJES_P2, "common")
    try:
        materializadas = {
            str(f[0])
            for f in conexion.execute(
                "SELECT id FROM relaciones WHERE materializada_en_el_canon = 1"
            )
        }
        total = int(conexion.execute("SELECT count(*) FROM relaciones").fetchone()[0])
    finally:
        conexion.close()
    assert materializadas == {"REL-001", "REL-008"}
    assert total == 10

    entrada = sqlite3.connect(str(proyeccion.ruta_de_entrada()))
    try:
        enlaces = {
            (int(f[0]), int(f[1]))
            for f in entrada.execute(
                "SELECT id, supersedes_decision_id FROM decisions "
                "WHERE supersedes_decision_id IS NOT NULL"
            )
        }
    finally:
        entrada.close()
    assert enlaces == {(3, 2), (13, 12)}


def test_el_discriminante_relacional_sigue_siendo_una_arista_no_materializada(
    proyeccion: P.ProyeccionExperimental,
) -> None:
    """Es la razon de ser de ``ADR002-C``: si el canon la tuviera, no discriminaria."""
    conexion = proyeccion.abrir(P.Plano.EJES_P2, "common")
    try:
        fila = conexion.execute(
            "SELECT tipo, origen_canonico, destino_canonico, materializada_en_el_canon "
            "FROM relaciones WHERE id = 'REL-010'"
        ).fetchone()
    finally:
        conexion.close()
    assert tuple(fila) == ("DERIVA_DE", "MEMORIA:950", "MEMORIA:951", 0)


# ---------------------------------------------------------------------------
# Determinismo y reproducibilidad
# ---------------------------------------------------------------------------


def test_dos_construcciones_producen_el_mismo_contenido_logico(tmp_path: Path) -> None:
    primera = build.construir_desde_la_familia(tmp_path / "primera")
    segunda = build.construir_desde_la_familia(tmp_path / "segunda")
    assert build.contenido_logico(primera) == build.contenido_logico(segunda)


def test_el_manifiesto_congelado_coincide_con_lo_que_se_construye(
    proyeccion: P.ProyeccionExperimental, familia: dict[str, Any]
) -> None:
    """La proyeccion se congela **antes** de ejecutar candidatos: aqui se
    comprueba que lo congelado sigue siendo lo que el generador produce."""
    congelado = json.loads(
        (Path(build.__file__).parent / "projection_manifest_v0_1.json").read_text(encoding="utf-8")
    )
    recomputado = build.manifiesto(
        proyeccion,
        blobs_de_origen=congelado["blobs_de_origen"],
        sujetos=familia["subject_keys_v0_2.json"]["valores"],
        propiedades=familia["property_keys_v0_2.json"]["valores"],
    )
    assert recomputado["huella_logica_total"] == congelado["huella_logica_total"]
    assert recomputado == congelado


def test_los_blobs_de_origen_del_manifiesto_son_los_reales() -> None:
    congelado = json.loads(
        (Path(build.__file__).parent / "projection_manifest_v0_1.json").read_text(encoding="utf-8")
    )
    for nombre, declarado in congelado["blobs_de_origen"].items():
        observado = subprocess.run(
            ["git", "hash-object", f"experiments/adr002/benchmark/{nombre}"],
            cwd=RAIZ_DEL_REPOSITORIO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert observado == declarado, nombre


# ---------------------------------------------------------------------------
# La proyeccion es ejecutable de verdad
# ---------------------------------------------------------------------------


def test_el_motor_comun_recorre_la_proyeccion_de_extremo_a_extremo(
    proyeccion: P.ProyeccionExperimental,
) -> None:
    """No mide: comprueba que la proyeccion **se puede ejecutar**."""
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(_peticion("plataforma despliegue"), puerto, candidato())
    assert recuperacion.parada.identificador
    assert [p.etapa for p in recuperacion.traza.pasos] == ["E0", "E1", "E2", "E3", "E4", "E5"]


def test_ca_19_es_alcanzable_por_los_tres_caminos_del_puerto(
    proyeccion: P.ProyeccionExperimental,
) -> None:
    esperado = {"DECISION:6", "DECISION:7", "DECISION:8"}
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        assert {i.id for i in puerto.por_termino_lexico(["plataforma"])} == esperado
        assert {i.id for i in puerto.por_clave_exacta(["plataformadedespliegue"])} == esperado
        assert {i.id for i in puerto.por_prefijo_de_sujeto(["plataforma"])} == esperado


def test_el_historial_llega_como_evidencia_atribuida(
    proyeccion: P.ProyeccionExperimental,
) -> None:
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        historial = puerto.historial_y_fuentes(["plataforma"])
    assert [i.id for i in historial] == ["MENSAJE:30"]
    assert all(i.clase_de_evidencia.value == "ATRIBUIDA" for i in historial)


def test_el_mensaje_redactado_no_es_recuperable(proyeccion: P.ProyeccionExperimental) -> None:
    """``B4d``: redactar anula el contenido, y el indice deja de casarlo."""
    entrada = sqlite3.connect(str(proyeccion.ruta_de_entrada()))
    try:
        fila = entrada.execute("SELECT content, redacted_at FROM messages WHERE id = 13").fetchone()
    finally:
        entrada.close()
    assert fila[0] is None
    assert fila[1] is not None
