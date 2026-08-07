"""Pruebas funcionales de la corrupcion LOGICA del sidecar (paquete 03).

**Solo despues de la ficha B vigente.** Los paquetes de correccion 03 y 04
cambiaron las fuentes de la huella de `ADR002-B`; estas pruebas exigen que los commits de
entrada de `ficha_ADR002-A_v5.json` y `ficha_ADR002-B_v7.json` sean ancestros
estrictos, y quedan suspendidas mientras no lo sean.

Lo que se demuestra, seccion a seccion, siempre sobre sidecars construidos
por el propio constructor y luego MANIPULADOS via SQL —es decir, ficheros que
superan `quick_check`, tablas, versiones, parametros y huella del canon—:

- **JSON corrupto** (18 formas): cada una produce `IndiceCorruptoError`, sin
  recuperacion parcial, sin degradar a la base y sin reproducir en el mensaje
  ni el valor plantado ni texto protegido.
- **Norma corrupta**: tipo, signo, cero, discrepancia con la suma de
  cuadrados y no representable fallan cerrados ANTES de calcular coseno
  alguno.
- **Identidad corrupta** (11 formas): `IndiceCorruptoError` del lector, nunca
  `IdentificadorInvalidoError` como salida externa, mensaje sin la identidad
  ni fragmentos protegidos, y el puerto sin ejecutar SQL alguno por esa
  identidad.
- **Referencias logicas**: posting huerfano, elemento sin vector, dimensiones
  fuera del vocabulario y filas duplicadas fallan tipadas; nada se omite en
  silencio dentro del alcance consumido.
- **Aritmetica**: los estados que antes escapaban como division por cero,
  raiz de negativo o coseno imposible se traducen a corrupcion logica tipada.
- **Defensa del candidato**: si el puerto rechazara una identidad, B lo
  traduce a corrupcion de indice con causa preservada y mensaje generico.
- **A y common intactos**: arboles y blobs exactos, ficha y acta de
  reaprobacion de A v3 sin un byte cambiado.

Lo que estas pruebas **no** hacen: no miden rendimiento, no usan el corpus
oficial ni casos oficiales, y no producen ningun artefacto de benchmark.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates import fixtures_b
from experiments.adr002.candidates.adr002_b import vectores
from experiments.adr002.candidates.adr002_b.candidate import candidato
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    MaterializacionPorIdentidad,
    Modo,
    Peticion,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import (
    IdentificadorInvalidoError,
    PuertoSqlite,
)

RAIZ = Path(__file__).resolve().parents[3]
FICHAS_SUCESORAS: Final = (
    "artifacts/adr002_cards/ficha_ADR002-A_v5.json",
    "artifacts/adr002_cards/ficha_ADR002-B_v7.json",
)

#: La consulta de control: en el fixture, "faro" comparte dimensiones con
#: varios elementos, de modo que la sentencia de candidatos CONSUME filas.
TERMINOS: Final = ("faro",)
CONSULTA: Final = "faro"


def _git(*argumentos: str) -> str:
    return subprocess.run(
        ["git", *argumentos], cwd=str(RAIZ), capture_output=True, text=True, check=False
    ).stdout.strip()


def _es_ancestro_estricto(ruta: str) -> bool:
    entrada = _git("log", "--format=%H", "--diff-filter=A", "--", ruta)
    if not entrada:
        return False
    commit_de_entrada = entrada.splitlines()[-1]
    if commit_de_entrada == _git("rev-parse", "HEAD"):
        return False
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit_de_entrada, "HEAD"],
            cwd=str(RAIZ),
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


pytestmark = pytest.mark.skipif(
    not all(_es_ancestro_estricto(ficha) for ficha in FICHAS_SUCESORAS),
    reason=(
        "las fichas ADR002-A v5 y ADR002-B v7 aun no son ancestros estrictos: "
        "ejecutar ahora produciria evidencia no utilizable (TOL-210, regla 3)"
    ),
)


@pytest.fixture
def indexada(tmp_path: Path) -> fixtures_b.FixtureB:
    fixture = fixtures_b.construir_base(tmp_path / "corrupcion.db")
    fixtures_b.construir_sidecar(fixture)
    return fixture


def _manipular(fixture: fixtures_b.FixtureB, sql: str, parametros: tuple = ()) -> None:
    """Corrompe el sidecar por SQL: sigue superando quick_check y metadatos."""
    conexion = sqlite3.connect(str(fixture.sidecar))
    try:
        conexion.execute(sql, parametros)
        conexion.commit()
    finally:
        conexion.close()


def _lector(fixture: fixtures_b.FixtureB) -> vectores.LectorVectorial:
    return vectores.LectorVectorial(fixture.ruta, fixture.sidecar)


def _peticion(consulta: str) -> Peticion:
    return Peticion(
        operation_id="op-corrupcion",
        consulta=consulta,
        proposito="comprobacion tecnica de reglas, sin medicion",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=False, proyectos=(fixtures_b.PROYECTO_ACTIVO,)),
        ventana=VentanaTemporal(tiempo_objetivo="2026-07-01T00:00:00"),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=5,
        limite_duro=50,
        objetivos=1,
    )


def test_premisa_la_consulta_de_control_consume_candidatas(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Ancla del alcance consumido: sin filas consumidas no habria deteccion."""
    lector = _lector(indexada)
    coincidencias = lector.consultar(TERMINOS)
    lector.close()
    assert len(coincidencias) >= 1


# --------------------------------------------------------------------------
# A. JSON corrupto: las dieciocho formas
# --------------------------------------------------------------------------

_JSON_CORRUPTO: Final[tuple[tuple[str, str], ...]] = (
    ("truncado", "[[1,"),
    ("raiz_objeto", '{"dimensiones": [1, 2]}'),
    ("raiz_cadena", '"[[1,2]]"'),
    ("raiz_null", "null"),
    ("par_longitud_1", "[[3]]"),
    ("par_longitud_3", "[[3,4,5]]"),
    ("dimension_cadena", '[["3",4]]'),
    ("peso_cadena", '[[3,"4"]]'),
    ("dimension_flotante", "[[3.0,4]]"),
    ("peso_flotante", "[[3,4.5]]"),
    ("dimension_booleana", "[[true,4]]"),
    ("peso_booleano", "[[3,true]]"),
    ("dimension_negativa", "[[-1,4]]"),
    ("peso_cero", "[[3,0]]"),
    ("peso_negativo", "[[3,-4]]"),
    ("dimension_repetida", "[[3,4],[3,5]]"),
    ("orden_no_canonico", "[[5,4],[3,5]]"),
    ("cardinalidad_excesiva", json.dumps([[i, 1] for i in range(257)])),
)


@pytest.mark.parametrize(("etiqueta", "celda"), _JSON_CORRUPTO, ids=[e for e, _ in _JSON_CORRUPTO])
def test_un_vector_de_elemento_corrupto_falla_tipado_y_minimizado(
    indexada: fixtures_b.FixtureB, etiqueta: str, celda: str
) -> None:
    _manipular(indexada, "UPDATE vectores_de_elemento SET dimensiones = ?", (celda,))
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        lector.consultar(TERMINOS)
    mensaje = str(caso.value)
    assert "vectores_de_elemento" in mensaje
    assert celda not in mensaje
    for texto in indexada.textos:
        assert texto not in mensaje


def test_un_vector_de_termino_corrupto_falla_tipado(indexada: fixtures_b.FixtureB) -> None:
    """La ruta de consulta tambien valida los vectores de termino."""
    _manipular(indexada, "UPDATE vectores_de_termino SET dimensiones = ?", ("[[1,",))
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        lector.consultar(TERMINOS)
    assert "vectores_de_termino" in str(caso.value)


def test_tras_la_corrupcion_el_lector_no_queda_parcialmente_valido(
    indexada: fixtures_b.FixtureB,
) -> None:
    """La conexion se cierra: no hay lector a medias tras entregar corrupcion."""
    _manipular(indexada, "UPDATE vectores_de_elemento SET dimensiones = ?", ("null",))
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceCorruptoError):
        lector.consultar(TERMINOS)
    # La conexion quedo cerrada: el intento de reuso tampoco entrega nada y
    # sigue fallando cerrado y tipado (el error de conexion cerrada de
    # sqlite3 es DatabaseError y se traduce igual que el resto).
    with pytest.raises(vectores.IndiceCorruptoError):
        lector.consultar(TERMINOS)


def test_el_motor_no_degrada_a_la_base_ante_json_corrupto(
    indexada: fixtures_b.FixtureB,
) -> None:
    """De extremo a extremo: fallo cerrado, ninguna Recuperacion parcial."""
    _manipular(indexada, "UPDATE vectores_de_elemento SET dimensiones = ?", ("[[3,0]]",))
    b = candidato(indexada.ruta, indexada.sidecar)
    with PuertoSqlite(indexada.ruta) as puerto, pytest.raises(vectores.IndiceCorruptoError):
        engine.recuperar(_peticion(CONSULTA), puerto, b)


# --------------------------------------------------------------------------
# B. Norma corrupta
# --------------------------------------------------------------------------

_NORMAS_CORRUPTAS: Final[tuple[tuple[str, str], ...]] = (
    ("cadena", "UPDATE vectores_de_elemento SET norma_cuadrada = 'nueve'"),
    ("cero", "UPDATE vectores_de_elemento SET norma_cuadrada = 0"),
    ("negativa", "UPDATE vectores_de_elemento SET norma_cuadrada = -4"),
    (
        "distinta_de_la_suma",
        "UPDATE vectores_de_elemento SET norma_cuadrada = norma_cuadrada + 1",
    ),
)


@pytest.mark.parametrize(
    ("etiqueta", "sql"), _NORMAS_CORRUPTAS, ids=[e for e, _ in _NORMAS_CORRUPTAS]
)
def test_una_norma_corrupta_falla_cerrada_antes_del_coseno(
    indexada: fixtures_b.FixtureB, etiqueta: str, sql: str
) -> None:
    _manipular(indexada, sql)
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
        lector.consultar(TERMINOS)
    assert type(caso.value) is vectores.IndiceCorruptoError
    assert "norma cuadrada invalida" in str(caso.value)


def test_una_norma_nula_o_booleana_o_desbordada_es_corrupcion() -> None:
    """Las formas que SQLite no puede almacenar se validan en la unidad:
    NULL (la columna es NOT NULL), booleano (SQLite lo adapta a entero) y un
    entero por encima del maximo representable (SQLite lo convertiria a
    real)."""
    for celda in (None, True, 2**63):
        with pytest.raises(vectores.IndiceCorruptoError):
            vectores._norma_cuadrada_validada(celda, [(0, 1)], posicion=0)


# --------------------------------------------------------------------------
# C. Identidad corrupta
# --------------------------------------------------------------------------

_TEXTO_PROTEGIDO_LARGO: Final = (
    "MEMORIA:el faro de poniente guarda la memoria de las mareas vivas y la "
    "baliza del espigon descansa junto al varadero de la darsena vieja"
)

_IDENTIDADES_CORRUPTAS: Final[tuple[tuple[str, str], ...]] = (
    ("sin_separador", "MEMORIAuno"),
    ("clase_desconocida", "RECUERDO:1"),
    ("multiples_separadores", "MEMORIA:1:2"),
    ("id_vacio", "MEMORIA:"),
    ("id_cero", "MEMORIA:0"),
    ("id_negativo", "MEMORIA:-1"),
    ("ceros_iniciales", "MEMORIA:007"),
    ("espacios", "MEMORIA: 1"),
    ("digitos_no_ascii", "MEMORIA:\uff11"),  # digito 1 fullwidth, no ASCII
    ("texto_protegido_largo", _TEXTO_PROTEGIDO_LARGO),
    ("salto_de_linea", "MEMORIA:1\n"),
)


@pytest.mark.parametrize(
    ("etiqueta", "identidad"), _IDENTIDADES_CORRUPTAS, ids=[e for e, _ in _IDENTIDADES_CORRUPTAS]
)
def test_una_identidad_corrupta_falla_tipada_sin_reproducirse(
    indexada: fixtures_b.FixtureB, etiqueta: str, identidad: str
) -> None:
    _manipular(indexada, "UPDATE posting SET elemento = ?", (identidad,))
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
        lector.consultar(TERMINOS)
    assert type(caso.value) is vectores.IndiceCorruptoError
    assert not isinstance(caso.value, IdentificadorInvalidoError)
    mensaje = str(caso.value)
    assert "identidad con formato no canonico" in mensaje
    assert identidad not in mensaje
    assert identidad.strip() not in mensaje
    assert "faro de poniente" not in mensaje


def test_la_identidad_corrupta_no_llega_jamas_al_puerto(
    indexada: fixtures_b.FixtureB,
) -> None:
    """De extremo a extremo: el puerto no ejecuta ni una sentencia por esa
    identidad, y la salida externa es corrupcion de indice, no el error del
    puerto."""
    _manipular(indexada, "UPDATE posting SET elemento = ?", (_TEXTO_PROTEGIDO_LARGO,))
    b = candidato(indexada.ruta, indexada.sidecar)
    with PuertoSqlite(indexada.ruta) as puerto:
        with pytest.raises(vectores.IndiceCorruptoError) as caso:
            engine.recuperar(_peticion(CONSULTA), puerto, b)
        operaciones = [consulta.operacion for consulta in puerto.registro.consultas]
    assert not any(operacion.startswith("por_identidad") for operacion in operaciones)
    assert not isinstance(caso.value, IdentificadorInvalidoError)
    assert _TEXTO_PROTEGIDO_LARGO not in str(caso.value)


# --------------------------------------------------------------------------
# D. Referencias logicas
# --------------------------------------------------------------------------


def test_un_posting_que_cita_un_elemento_sin_vector_falla_huerfano(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Identidad valida en formato, pero sin fila en vectores_de_elemento: el
    LEFT JOIN la expone y falla cerrada, en vez de desaparecer en el JOIN."""
    _manipular(indexada, "UPDATE posting SET elemento = 'MEMORIA:9998'")
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        lector.consultar(TERMINOS)
    assert "referencia huerfana" in str(caso.value)


def test_un_elemento_consumido_sin_su_vector_falla_huerfano(
    indexada: fixtures_b.FixtureB,
) -> None:
    """El caso quirurgico: borrar el vector de UNA candidata consumida."""
    lector_limpio = _lector(indexada)
    coincidencias = lector_limpio.consultar(TERMINOS)
    lector_limpio.close()
    assert coincidencias
    victima = coincidencias[0].elemento
    _manipular(indexada, "DELETE FROM vectores_de_elemento WHERE elemento = ?", (victima,))
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        lector.consultar(TERMINOS)
    assert "referencia huerfana" in str(caso.value)
    assert victima not in str(caso.value)


def test_un_vector_con_dimensiones_fuera_del_vocabulario_falla(
    indexada: fixtures_b.FixtureB,
) -> None:
    _manipular(
        indexada,
        "UPDATE vectores_de_elemento SET dimensiones = '[[99998,3],[99999,4]]', "
        "norma_cuadrada = 25",
    )
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        lector.consultar(TERMINOS)
    assert "fuera del vocabulario" in str(caso.value)


def test_un_vector_de_termino_fuera_del_vocabulario_falla(
    indexada: fixtures_b.FixtureB,
) -> None:
    _manipular(indexada, "UPDATE vectores_de_termino SET dimensiones = '[[99999,4]]'")
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        lector.consultar(TERMINOS)
    assert "fuera del vocabulario" in str(caso.value)


def test_las_filas_de_posting_duplicadas_fallan_incoherentes(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Una fila duplicada infla el conteo de posting frente al vector real."""
    _manipular(indexada, "INSERT INTO posting SELECT dimension, elemento FROM posting")
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        lector.consultar(TERMINOS)
    assert "solapamiento incoherente" in str(caso.value)


# --------------------------------------------------------------------------
# E. Aritmetica: lo que antes escapaba como error generico
# --------------------------------------------------------------------------


def test_la_division_por_cero_ya_no_escapa(indexada: fixtures_b.FixtureB) -> None:
    """Norma cero: antes ZeroDivisionError en el coseno; ahora corrupcion."""
    _manipular(indexada, "UPDATE vectores_de_elemento SET norma_cuadrada = 0")
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
        lector.consultar(TERMINOS)
    assert type(caso.value) is vectores.IndiceCorruptoError


def test_la_raiz_de_negativo_ya_no_escapa(indexada: fixtures_b.FixtureB) -> None:
    """Norma negativa: antes ValueError de math.sqrt; ahora corrupcion."""
    _manipular(indexada, "UPDATE vectores_de_elemento SET norma_cuadrada = -9")
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
        lector.consultar(TERMINOS)
    assert type(caso.value) is vectores.IndiceCorruptoError


def test_el_coseno_imposible_no_llega_a_computarse(indexada: fixtures_b.FixtureB) -> None:
    """Norma minuscula pero distinta de la suma: antes un coseno gigantesco
    fuera de todo intervalo; ahora la discrepancia con la suma de cuadrados
    falla ANTES de dividir."""
    _manipular(indexada, "UPDATE vectores_de_elemento SET norma_cuadrada = 1")
    lector = _lector(indexada)
    with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
        lector.consultar(TERMINOS)
    assert type(caso.value) is vectores.IndiceCorruptoError
    assert "no coincide con la suma" in str(caso.value)


# --------------------------------------------------------------------------
# F. Defensa en la frontera con el puerto
# --------------------------------------------------------------------------


class _PuertoQueRechaza(PuertoSqlite):
    """Doble tecnico: el puerto rechaza toda identidad, reproduciendo valor.

    Es el escenario que la validacion del lector impide normalmente: se fuerza
    aqui para probar la red de seguridad del candidato."""

    def por_identificadores(self, identificadores: Sequence[str]) -> MaterializacionPorIdentidad:
        msg = "identificador canonico invalido: 'CELDA-SECRETA-QUE-NO-DEBE-SALIR'"
        raise IdentificadorInvalidoError(msg)


def test_el_candidato_traduce_el_rechazo_del_puerto_a_corrupcion(
    indexada: fixtures_b.FixtureB,
) -> None:
    b = candidato(indexada.ruta, indexada.sidecar)
    with (
        _PuertoQueRechaza(indexada.ruta) as puerto,
        pytest.raises(vectores.IndiceCorruptoError) as caso,
    ):
        engine.recuperar(_peticion(CONSULTA), puerto, b)
    assert isinstance(caso.value.__cause__, IdentificadorInvalidoError)
    mensaje = str(caso.value)
    assert "CELDA-SECRETA-QUE-NO-DEBE-SALIR" not in mensaje
    assert "puerto canonico rechaza" in mensaje


# --------------------------------------------------------------------------
# H. A y common intactos, por arboles y blobs
# --------------------------------------------------------------------------


def test_common_y_adr002_a_permanecen_intactos_por_arboles() -> None:
    assert (
        _git("rev-parse", "HEAD:experiments/adr002/candidates/common")
        == "5adbff67a82165141f14b0890ba90978fc81366a"
    )
    assert (
        _git("rev-parse", "HEAD:experiments/adr002/candidates/adr002_a")
        == "777e8a540a550ef7e71ec9a60dc7ff516a53ab3c"
    )


def test_la_ficha_vigente_de_a_y_su_acta_son_las_congeladas() -> None:
    assert (
        _git("rev-parse", "HEAD:artifacts/adr002_cards/ficha_ADR002-A_v6.json")
        == "691514cf5becd2d8ece50035de58a84426498b71"
    )
    acta = (
        "docs/architecture/SIRIUS_0.2_ADR_002_ADR002_A_V3_PREPARADO_BENCHMARK_REAPROBACION_v1.0.md"
    )
    assert _git("rev-parse", f"HEAD:{acta}") == "f2babe06a8c883924a464df6fc96d14f52da367d"
    ficha = json.loads(
        (RAIZ / "artifacts/adr002_cards/ficha_ADR002-A_v6.json").read_text(encoding="utf-8")
    )
    assert ficha["estado"] == "CONGELADA"
    assert ficha["congelacion"]["huella"] == "d305073ce5bb21a07e8523969752a9f06a966d01"


# --------------------------------------------------------------------------
# J. Estas pruebas no miden nada
# --------------------------------------------------------------------------

_MARCADOR_DEL_CONTROL = "def test_estas_pruebas_no_miden_rendimiento"


def test_estas_pruebas_no_miden_rendimiento() -> None:
    codigo = Path(__file__).read_text(encoding="utf-8")
    cuerpo = codigo.split(_MARCADOR_DEL_CONTROL)[0]
    for prohibido in ("perf_counter", "timeit", "time.time", "p95", "percentil", "latencia"):
        assert prohibido not in cuerpo, prohibido
    assert "performance_corpus" not in cuerpo
    assert "conformance_corpus" not in cuerpo
