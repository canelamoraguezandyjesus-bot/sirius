"""``ADR002-C``: que la senal relacional sea tardia, explicita y falsable.

No comprueban que C recupere mejor: comprueban que **su senal es exactamente
la que su definicion canonica declara** y que se puede falsar. El discriminante
es la prueba central: si borrar una arista concreta no quita un alcance
concreto, la senal relacional no estaria haciendo nada y C seria A con otro
nombre.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest
from experiments.adr002.candidates.adr002_a.candidate import candidato as candidato_a
from experiments.adr002.candidates.adr002_c import relaciones
from experiments.adr002.candidates.adr002_c.candidate import (
    DEFINICION_CANONICA,
    IDENTIFICADOR,
    SENAL_TARDIA,
    candidato,
)
from experiments.adr002.candidates.common import engine, neutrality
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    Etapa,
    Modo,
    Peticion,
    SenalesDeCandidato,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.projection import build
from experiments.adr002.projection.contracts import Plano
from experiments.adr002.projection.plane import PlanoReservado

RAIZ = Path(__file__).resolve().parents[3]

#: Los dos extremos del discriminante relacional de la familia v0.6.
SEMILLA = "MEMORIA:950"
DESTINO = "MEMORIA:951"
ARISTA = "REL-010"
#: Consulta que alcanza la semilla por via lexica y **no** alcanza el destino.
CONSULTA = "calibrado del rotor"
#: Proyecto del delta relacional, el octavo del corpus.
PROYECTO_DELTA = "8"


@pytest.fixture(scope="module")
def proyeccion(tmp_path_factory: pytest.TempPathFactory):
    return build.construir_desde_la_familia(tmp_path_factory.mktemp("c") / "planos")


def _peticion(consulta: str = CONSULTA, *, limite: int = 10) -> Peticion:
    return Peticion(
        operation_id="adr002-c",
        consulta=consulta,
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=False, proyectos=(PROYECTO_DELTA,)),
        ventana=VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=limite,
        limite_duro=limite,
    )


def _recuperar(proyeccion, candidato_bajo_prueba, peticion=None, plano_relacional=None):
    plano = PlanoReservado(proyeccion)
    try:
        with PuertoSqlite(proyeccion.ruta_de_entrada(), proyeccion.ruta(Plano.EJES_P2)) as puerto:
            return engine.recuperar(peticion or _peticion(), puerto, candidato_bajo_prueba, plano)
    finally:
        plano.close()


# ---------------------------------------------------------------------------
# Identidad y definicion canonica
# ---------------------------------------------------------------------------


def test_c_declara_su_definicion_canonica() -> None:
    assert IDENTIFICADOR == "ADR002-C"
    assert SENAL_TARDIA == "relacional_explicita"
    assert "senal relacional explicita" in DEFINICION_CANONICA
    assert "unicamente en etapas tardias" in DEFINICION_CANONICA


def test_c_implementa_el_contrato_de_candidato(proyeccion) -> None:
    c = candidato(proyeccion.ruta(Plano.EJES_P2))
    assert isinstance(c, SenalesDeCandidato)
    assert c.senal_tardia_habilitada == SENAL_TARDIA


def test_c_no_reimplementa_el_motor_ni_las_puertas() -> None:
    assert neutrality.fallos_de_aislamiento_del_candidato(RAIZ, "adr002_c") == []


def test_la_capa_comun_sigue_sin_nombrar_a_ningun_candidato() -> None:
    assert neutrality.fallos_de_neutralidad(RAIZ) == []


# ---------------------------------------------------------------------------
# El discriminante: la razon de ser de C
# ---------------------------------------------------------------------------


def test_a_alcanza_la_semilla_y_no_el_destino(proyeccion) -> None:
    """Si A llegase al destino, el discriminante no discriminaria nada."""
    recuperacion = _recuperar(proyeccion, candidato_a())
    assert SEMILLA in recuperacion.ids
    assert DESTINO not in recuperacion.ids


def test_c_alcanza_el_destino_por_la_arista_explicita(proyeccion) -> None:
    c = candidato(proyeccion.ruta(Plano.EJES_P2))
    recuperacion = _recuperar(proyeccion, c)
    c.cerrar()
    assert SEMILLA in recuperacion.ids
    assert DESTINO in recuperacion.ids
    alcanzado = next(r for r in recuperacion.resultados if r.item.id == DESTINO)
    assert alcanzado.etapa_de_origen is Etapa.E3, "la senal es tardia: E3, nunca antes"
    assert ARISTA in alcanzado.explicacion.coincidencia
    assert "DERIVA_DE" in alcanzado.explicacion.coincidencia


def test_borrar_la_arista_elimina_el_alcance(proyeccion, tmp_path: Path) -> None:
    """La falsacion: sin la arista, C es indistinguible de A en este caso."""
    copia = tmp_path / "ejes_sin_arista.sqlite3"
    shutil.copy(proyeccion.ruta(Plano.EJES_P2), copia)
    conexion = sqlite3.connect(str(copia))
    try:
        conexion.execute("DELETE FROM relaciones WHERE id = ?", (ARISTA,))
        conexion.commit()
    finally:
        conexion.close()

    c = candidato(copia)
    recuperacion = _recuperar(proyeccion, c)
    c.cerrar()
    assert SEMILLA in recuperacion.ids
    assert DESTINO not in recuperacion.ids, "sin la arista el destino no debe alcanzarse"
    assert set(recuperacion.ids) == set(_recuperar(proyeccion, candidato_a()).ids)


def test_la_ablacion_deja_a_c_identico_a_a(proyeccion) -> None:
    """Sin senal relacional, C **es** A: cualquier otra diferencia es un defecto."""
    c = candidato(proyeccion.ruta(Plano.EJES_P2), con_senal_relacional=False)
    sin_senal = _recuperar(proyeccion, c)
    c.cerrar()
    base = _recuperar(proyeccion, candidato_a())
    assert sin_senal.ids == base.ids
    assert sin_senal.parada.identificador == base.parada.identificador


def test_el_destino_es_recuperable_por_su_propia_consulta(proyeccion) -> None:
    """Control positivo: el destino no esta escondido, solo no es alcanzable
    desde la consulta de la semilla por via lexica."""
    recuperacion = _recuperar(proyeccion, candidato_a(), _peticion("bitacora municipal"))
    assert DESTINO in recuperacion.ids


# ---------------------------------------------------------------------------
# La senal es tardia de verdad
# ---------------------------------------------------------------------------


def test_el_plano_no_se_abre_cuando_las_etapas_tempranas_bastan(proyeccion) -> None:
    """Cero trabajo adelantado: se comprueba sobre el contador, no se promete."""
    exacta = Peticion(
        operation_id="temprana",
        consulta=CONSULTA,
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=False, proyectos=(PROYECTO_DELTA,)),
        ventana=VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"),
        cardinalidad=Cardinalidad.EXACTA,
        limite_objetivo=1,
        limite_duro=5,
        objetivos=1,
    )
    c = candidato(proyeccion.ruta(Plano.EJES_P2))
    recuperacion = _recuperar(proyeccion, c, exacta)
    assert recuperacion.parada.identificador == "S1", "E1 basta: la suficiencia para antes de E3"
    assert c.invocaciones_relacionales == 0
    assert not c.plano_abierto
    c.cerrar()


def test_el_plano_se_abre_una_sola_vez_y_consulta_dirigido(proyeccion) -> None:
    c = candidato(proyeccion.ruta(Plano.EJES_P2))
    _recuperar(proyeccion, c)
    assert c.invocaciones_relacionales == 1
    registro = c.registro_relacional
    assert registro is not None
    assert [op for op, _p, _f in registro.consultas] == ["salientes"]
    _op, parametros, filas = registro.consultas[0]
    assert parametros == (SEMILLA,), "la consulta se dirige por semilla concreta"
    assert filas <= relaciones.ARISTAS_MAXIMAS
    c.cerrar()


def test_un_solo_salto_declarado() -> None:
    assert relaciones.SALTOS == 1


# ---------------------------------------------------------------------------
# Tipo, direccion y extremos
# ---------------------------------------------------------------------------


def test_los_dos_tipos_que_otra_regla_adjudica_no_expanden() -> None:
    assert set(relaciones.TIPOS_NO_EXPANDEN) == {"SUSTITUYE_A", "CONFLICTO_CON"}
    for tipo, motivo in relaciones.TIPOS_NO_EXPANDEN.items():
        assert tipo not in relaciones.TIPOS_QUE_EXPANDEN
        assert motivo.strip(), "un tipo excluido sin motivo no seria auditable"


def test_una_supersesion_no_expande_y_se_declara(proyeccion) -> None:
    """``DEC-003 SUSTITUYE_A DEC-002``: la adjudica ``G7``, no una arista."""
    with relaciones.FuenteRelacional(proyeccion.ruta(Plano.EJES_P2)) as fuente:
        utiles = fuente.salientes(["DECISION:3"])
        assert utiles == ()
        assert [a for a, _t, _m in fuente.registro.descartadas_por_tipo] == ["REL-001"]


def test_la_direccion_se_respeta(proyeccion) -> None:
    """``APOYA`` y ``REFUTA`` no son simetricas: seguirlas al reves las falsearia."""
    with relaciones.FuenteRelacional(proyeccion.ruta(Plano.EJES_P2)) as fuente:
        desde_destino = fuente.salientes([DESTINO])
        assert all(a.origen_canonico == DESTINO for a in desde_destino)
        assert SEMILLA not in [a.destino_canonico for a in desde_destino]


def test_un_extremo_sin_identidad_canonica_se_declara(proyeccion) -> None:
    """``REL-006 MEM-017 DERIVA_DE DOC-004``: un documento no es del canon."""
    with relaciones.FuenteRelacional(proyeccion.ruta(Plano.EJES_P2)) as fuente:
        fuente.salientes(["MEMORIA:17"])
        assert ("REL-006", "DOC-004") in fuente.registro.no_materializables


# ---------------------------------------------------------------------------
# Corrupciones: todas cerradas y tipadas
# ---------------------------------------------------------------------------


def _plano_corrupto(origen: Path, destino: Path, sql: str, parametros: tuple[object, ...]) -> Path:
    shutil.copy(origen, destino)
    conexion = sqlite3.connect(str(destino))
    try:
        conexion.execute(sql, parametros)
        conexion.commit()
    finally:
        conexion.close()
    return destino


def test_un_plano_ausente_falla_cerrado(tmp_path: Path) -> None:
    with pytest.raises(relaciones.PlanoRelacionalAusenteError):
        relaciones.FuenteRelacional(tmp_path / "no-existe.sqlite3")


def test_un_tipo_desconocido_invalida_la_fuente(proyeccion, tmp_path: Path) -> None:
    corrupto = _plano_corrupto(
        proyeccion.ruta(Plano.EJES_P2),
        tmp_path / "tipo.sqlite3",
        "UPDATE relaciones SET tipo = ? WHERE id = ?",
        ("INVENTADA", ARISTA),
    )
    with pytest.raises(relaciones.RelacionInvalidaError, match="desconocido"):
        relaciones.FuenteRelacional(corrupto)


def test_un_extremo_vacio_invalida_la_fuente(proyeccion, tmp_path: Path) -> None:
    corrupto = _plano_corrupto(
        proyeccion.ruta(Plano.EJES_P2),
        tmp_path / "vacio.sqlite3",
        "UPDATE relaciones SET destino = '' WHERE id = ?",
        (ARISTA,),
    )
    with pytest.raises(relaciones.RelacionInvalidaError, match="extremo vacio"):
        relaciones.FuenteRelacional(corrupto)


def test_un_bucle_invalida_la_fuente(proyeccion, tmp_path: Path) -> None:
    """Un ciclo de longitud uno se alcanzaria a si mismo y no aportaria nada."""
    corrupto = _plano_corrupto(
        proyeccion.ruta(Plano.EJES_P2),
        tmp_path / "bucle.sqlite3",
        "UPDATE relaciones SET destino = origen WHERE id = ?",
        (ARISTA,),
    )
    with pytest.raises(relaciones.RelacionInvalidaError, match="bucle"):
        relaciones.FuenteRelacional(corrupto)


def test_un_destino_inexistente_en_el_canon_falla_cerrado(proyeccion, tmp_path: Path) -> None:
    """Un grafo que afirma elementos que el canon no contiene no es utilizable."""
    corrupto = _plano_corrupto(
        proyeccion.ruta(Plano.EJES_P2),
        tmp_path / "ausente.sqlite3",
        "UPDATE relaciones SET destino = 'MEM-999', destino_canonico = 'MEMORIA:999' WHERE id = ?",
        (ARISTA,),
    )
    c = candidato(corrupto)
    with pytest.raises(relaciones.RelacionInconsistenteError, match="no contiene"):
        _recuperar(proyeccion, c)
    c.cerrar()


def test_la_corrupcion_no_se_degrada_a_recuperacion_parcial(proyeccion, tmp_path: Path) -> None:
    """Sin relaciones, C no es C: no hay caida silenciosa a la base."""
    corrupto = _plano_corrupto(
        proyeccion.ruta(Plano.EJES_P2),
        tmp_path / "parcial.sqlite3",
        "UPDATE relaciones SET tipo = ? WHERE id = ?",
        ("DESCONOCIDA", "REL-001"),
    )
    c = candidato(corrupto)
    with pytest.raises(relaciones.FuenteRelacionalError):
        _recuperar(proyeccion, c)


# ---------------------------------------------------------------------------
# Sin oraculo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prohibido", ["nota", "cases_v0_", "references_v0_", "resultado_esperado", "grupos_esperados"]
)
def test_c_no_nombra_nada_del_oraculo(prohibido: str) -> None:
    import re

    paquete = RAIZ / "experiments/adr002/candidates/adr002_c"
    for ruta in sorted(paquete.glob("*.py")):
        # El control mira el **codigo**, no la prosa: es el mismo criterio que
        # ``neutrality._sin_comentarios`` fija para la capa comun. Explicar por
        # que la nota esta prohibida no es leerla, y un control que fallase por
        # eso solo conseguiria que alguien borrase la explicacion.
        codigo = neutrality._sin_comentarios(ruta.read_text(encoding="utf-8"))
        assert not re.search(rf"\b{re.escape(prohibido)}", codigo), (
            f"{ruta.name} nombra {prohibido}"
        )


def test_c_no_selecciona_la_nota_de_ninguna_relacion(proyeccion) -> None:
    """La nota es oraculo prohibido; el plano ni siquiera la materializa."""
    conexion = proyeccion.abrir(Plano.EJES_P2, "common")
    try:
        columnas = {str(c[1]) for c in conexion.execute("PRAGMA table_info(relaciones)")}
    finally:
        conexion.close()
    assert "nota" not in columnas


def test_c_es_determinista(proyeccion) -> None:
    c = candidato(proyeccion.ruta(Plano.EJES_P2))
    primera = _recuperar(proyeccion, c)
    segunda = _recuperar(proyeccion, c)
    c.cerrar()
    assert primera.ids == segunda.ids
