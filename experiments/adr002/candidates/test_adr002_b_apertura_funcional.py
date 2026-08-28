"""Pruebas funcionales de la APERTURA del sidecar (paquete de correccion 04).

**Solo despues de la ficha B v4.** El paquete de correccion 04 cambio las
fuentes de la huella de `ADR002-B`; estas pruebas exigen que los commits de
entrada de `ficha_ADR002-A_v5.json` y `ficha_ADR002-B_v7.json` sean ancestros
estrictos, y quedan suspendidas mientras no lo sean.

Lo que se demuestra, seccion a seccion, sobre sidecars construidos por el
constructor real y luego MANIPULADOS via SQL —ficheros que siguen superando
`quick_check`, tablas, versiones y parametros—:

- **Huella malformada** (once formas): `IndiceCorruptoError`, mensaje
  generico, la celda no aparece ni entera ni por fragmentos, ningun texto
  protegido, conexion cerrada y ningun lector utilizable.
- **Huella valida pero distinta**: `IndiceDesfasadoError` —no corrupcion—,
  sin ninguna de las dos huellas en el mensaje, conexion cerrada.
- **Error fisico con centinela**: `IndiceCorruptoError`, mensaje externo sin
  el centinela, causa original preservada, conexion cerrada.
- **Auditoria de las ocho aperturas**: cada una devuelve su subtipo exacto y
  ninguna arrastra contenido de celdas.

Toda afirmacion de cierre se comprueba **vigilando las conexiones realmente
abiertas** por el modulo, no declarandola: cuando `__init__` lanza, no existe
instancia que inspeccionar, de modo que el unico modo honesto de probarlo es
registrar cada conexion que el modulo abre y su estado final.

Lo que estas pruebas **no** hacen: no miden rendimiento, no usan el corpus
oficial ni casos oficiales, y no producen ningun artefacto de benchmark.
"""

from __future__ import annotations

import sqlite3
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates import fixtures_b
from experiments.adr002.candidates.adr002_b import vectores

RAIZ = Path(__file__).resolve().parents[3]
FICHAS_SUCESORAS: Final = (
    "artifacts/adr002_cards/ficha_ADR002-A_v5.json",
    "artifacts/adr002_cards/ficha_ADR002-B_v7.json",
)

#: Un hexdigest SHA-256 canonico que no es el del fixture: sirve para separar
#: «formato invalido» de «huella distinta».
HUELLA_CANONICA_AJENA: Final = "0" * 63 + "f"

#: Texto con el vocabulario protegido del fixture, para plantarlo en la celda
#: y comprobar que no reaparece en ningun mensaje.
TEXTO_PROTEGIDO_LARGO: Final = (
    "el faro de poniente guarda la memoria de las mareas vivas y la baliza del "
    "espigon descansa junto al varadero de la darsena vieja"
)


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


# --------------------------------------------------------------------------
# Vigilancia de conexiones: la unica forma honesta de probar el cierre
# --------------------------------------------------------------------------


class _ConexionVigilada(sqlite3.Connection):
    """Conexion real que recuerda si fue cerrada."""

    def __init__(self, *argumentos: object, **nombrados: object) -> None:
        super().__init__(*argumentos, **nombrados)  # type: ignore[arg-type]
        self.cerrada = False

    def close(self) -> None:
        self.cerrada = True
        super().close()


@pytest.fixture
def conexiones(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[_ConexionVigilada]]:
    """Registra cada conexion que ``vectores`` abre, para auditar su cierre."""
    abiertas: list[_ConexionVigilada] = []
    real = sqlite3.connect

    def _vigilada(ruta: str, *argumentos: object, **nombrados: object) -> sqlite3.Connection:
        conexion = real(ruta, *argumentos, factory=_ConexionVigilada, **nombrados)  # type: ignore[call-overload]
        abiertas.append(conexion)
        return conexion

    monkeypatch.setattr(vectores.sqlite3, "connect", _vigilada)
    yield abiertas


@pytest.fixture
def indexada(tmp_path: Path) -> fixtures_b.FixtureB:
    fixture = fixtures_b.construir_base(tmp_path / "apertura.db")
    fixtures_b.construir_sidecar(fixture)
    return fixture


def _manipular(fixture: fixtures_b.FixtureB, sql: str, parametros: tuple = ()) -> None:
    conexion = sqlite3.connect(str(fixture.sidecar))
    try:
        conexion.execute(sql, parametros)
        conexion.commit()
    finally:
        conexion.close()


def _plantar_huella(fixture: fixtures_b.FixtureB, valor: object) -> None:
    _manipular(
        fixture,
        "UPDATE metadatos SET valor = ? WHERE clave = 'huella_del_canon'",
        (valor,),
    )


def _abrir(fixture: fixtures_b.FixtureB) -> vectores.LectorVectorial:
    return vectores.LectorVectorial(fixture.ruta, fixture.sidecar)


def _todo_cerrado(abiertas: list[_ConexionVigilada]) -> bool:
    return bool(abiertas) and all(conexion.cerrada for conexion in abiertas)


def test_premisa_la_vigilancia_observa_una_apertura_correcta(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    """Ancla: sin vigilancia efectiva, las aserciones de cierre no dirian nada."""
    lector = _abrir(indexada)
    assert conexiones, "la vigilancia no registro ninguna conexion"
    lector.close()
    assert _todo_cerrado(conexiones)


# --------------------------------------------------------------------------
# A. Huella malformada: once formas
# --------------------------------------------------------------------------

_HUELLAS_MALFORMADAS: Final[tuple[tuple[str, str], ...]] = (
    ("texto_protegido_largo", TEXTO_PROTEGIDO_LARGO),
    ("salto_de_linea", "0" * 64 + "\n"),
    ("cadena_vacia", ""),
    ("sesenta_y_tres", "0" * 63),
    ("sesenta_y_cinco", "0" * 65),
    ("mayusculas", "F" * 64),
    ("no_hexadecimal", "g" * 64),
    ("espacio_inicial", " " + "0" * 63),
    ("espacio_final", "0" * 63 + " "),
    ("con_prefijo", "sha256:" + "0" * 57),
    ("valor_numerico", "12345"),
)


@pytest.mark.parametrize(
    ("etiqueta", "celda"), _HUELLAS_MALFORMADAS, ids=[e for e, _ in _HUELLAS_MALFORMADAS]
)
def test_una_huella_malformada_es_corrupcion_minimizada(
    indexada: fixtures_b.FixtureB,
    conexiones: list[_ConexionVigilada],
    etiqueta: str,
    celda: str,
) -> None:
    _plantar_huella(indexada, celda)
    with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
        _abrir(indexada)
    assert type(caso.value) is vectores.IndiceCorruptoError
    mensaje = str(caso.value)
    assert "formato canonico de SHA-256" in mensaje
    # Ni entera ni por fragmentos: ningun trozo no trivial de la celda sale.
    # (La celda vacia se excluye de la contencion: "" esta en toda cadena.)
    if celda:
        assert celda not in mensaje
    for trozo in (celda[:16], celda[-16:], celda.strip()):
        if len(trozo) >= 4:
            assert trozo not in mensaje, trozo
    for texto in indexada.textos:
        assert texto not in mensaje
    assert _todo_cerrado(conexiones)


def test_una_huella_no_textual_se_valida_en_la_unidad() -> None:
    """SQLite adapta a texto lo que se le pasa en una columna TEXT NOT NULL;
    los tipos que no pueden almacenarse se validan en el predicado."""
    for celda in (None, 12345, True, 3.5, b"0" * 64):
        assert not vectores._huella_persistida_valida(celda)


def test_la_huella_malformada_no_llega_a_recomputar_el_canon(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    """La validacion precede al recomputo: con la celda corrupta, el canon
    NO se abre —solo hay una conexion, la del propio sidecar—."""
    _plantar_huella(indexada, "no-soy-una-huella")
    # Se mide el DELTA de la apertura: la vigilancia tambien registra las
    # conexiones que la propia prueba abrio para manipular el sidecar.
    antes = len(conexiones)
    with pytest.raises(vectores.IndiceCorruptoError):
        _abrir(indexada)
    abiertas_por_la_apertura = len(conexiones) - antes
    assert abiertas_por_la_apertura == 1, "el canon NO debe abrirse con la huella corrupta"
    assert _todo_cerrado(conexiones)


def test_una_huella_canonica_si_obliga_a_recomputar_el_canon(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    """Contraste del control anterior: con la huella bien formada, el canon
    SI se abre —dos conexiones—, de modo que la prueba de ahorro discrimina."""
    _plantar_huella(indexada, HUELLA_CANONICA_AJENA)
    antes = len(conexiones)
    with pytest.raises(vectores.IndiceDesfasadoError):
        _abrir(indexada)
    assert len(conexiones) - antes == 2
    assert _todo_cerrado(conexiones)


# --------------------------------------------------------------------------
# B. Huella canonica pero distinta: desfase, no corrupcion
# --------------------------------------------------------------------------


def test_una_huella_canonica_distinta_es_desfase_sin_reproducirla(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    real = vectores.huella_del_canon(indexada.ruta)
    _plantar_huella(indexada, HUELLA_CANONICA_AJENA)
    with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
        _abrir(indexada)
    assert type(caso.value) is vectores.IndiceDesfasadoError
    assert not isinstance(caso.value, vectores.IndiceCorruptoError)
    mensaje = str(caso.value)
    assert mensaje == "el canon cambio desde que se construyo el indice"
    assert HUELLA_CANONICA_AJENA not in mensaje
    assert real not in mensaje
    assert _todo_cerrado(conexiones)


def test_el_desfase_real_por_cambio_del_canon_sigue_siendo_desfase(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    """El caso natural: el canon cambia y la huella persistida sigue siendo
    canonica. Debe seguir tipandose como desfase, no como corrupcion."""
    fixtures_b.anadir_memoria(indexada.ruta, "clave-nueva", "texto inerte de relleno")
    with pytest.raises(vectores.IndiceDesfasadoError) as caso:
        _abrir(indexada)
    assert "!=" not in str(caso.value)
    assert _todo_cerrado(conexiones)


# --------------------------------------------------------------------------
# C. Error fisico con centinela
# --------------------------------------------------------------------------

_CENTINELA_FISICO: Final = "CENTINELA-FISICO-QUE-NO-DEBE-SALIR"


def test_un_error_fisico_conserva_la_causa_sin_reproducir_su_texto(
    indexada: fixtures_b.FixtureB, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Doble tecnico: la lectura de ``sqlite_master`` falla con un texto
    distinguible. La salida es corrupcion tipada, el centinela no aparece en
    el mensaje externo, la causa se conserva y la conexion queda cerrada."""
    abiertas: list[_ConexionVigilada] = []
    real = sqlite3.connect

    class _ConexionQueFalla(_ConexionVigilada):
        def execute(self, sql: str, *argumentos: object) -> sqlite3.Cursor:  # type: ignore[override]
            if "sqlite_master" in sql:
                raise sqlite3.DatabaseError(_CENTINELA_FISICO)
            return super().execute(sql, *argumentos)  # type: ignore[arg-type]

    def _fabricar(ruta: str, *argumentos: object, **nombrados: object) -> sqlite3.Connection:
        conexion = real(ruta, *argumentos, factory=_ConexionQueFalla, **nombrados)  # type: ignore[call-overload]
        abiertas.append(conexion)
        return conexion

    monkeypatch.setattr(vectores.sqlite3, "connect", _fabricar)
    with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
        _abrir(indexada)
    assert type(caso.value) is vectores.IndiceCorruptoError
    mensaje = str(caso.value)
    assert mensaje == "el sidecar no es una base legible"
    assert _CENTINELA_FISICO not in mensaje
    assert isinstance(caso.value.__cause__, sqlite3.DatabaseError)
    assert _CENTINELA_FISICO in str(caso.value.__cause__)
    assert _todo_cerrado(abiertas)


# --------------------------------------------------------------------------
# D. Auditoria de las ocho aperturas
# --------------------------------------------------------------------------


def test_un_sidecar_inexistente_es_inexistencia_sin_la_ruta(
    indexada: fixtures_b.FixtureB,
) -> None:
    ausente = indexada.sidecar.with_name("no-existe.db")
    with pytest.raises(vectores.IndiceInexistenteError) as caso:
        vectores.LectorVectorial(indexada.ruta, ausente)
    mensaje = str(caso.value)
    assert mensaje == "no existe el indice vectorial en la ruta declarada"
    assert str(ausente) not in mensaje
    assert ausente.name not in mensaje


def test_una_base_ilegible_es_corrupcion(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    indexada.sidecar.write_bytes(b"esto ya no es una base de datos")
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        _abrir(indexada)
    assert "no es una base legible" in str(caso.value) or "integridad" in str(caso.value)
    assert _todo_cerrado(conexiones)


def test_unas_tablas_ausentes_son_corrupcion_con_nombres_propios(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    _manipular(indexada, "DROP TABLE posting")
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        _abrir(indexada)
    mensaje = str(caso.value)
    assert "faltan" in mensaje
    # Solo puede citar nombres de nuestra propia constante.
    for citado in ("posting",):
        assert citado in mensaje
    assert set(vectores.TABLAS_DEL_SIDECAR) >= {"posting"}
    assert _todo_cerrado(conexiones)


def test_unas_versiones_incompatibles_son_corrupcion(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    _manipular(
        indexada,
        "UPDATE metadatos SET valor = ? WHERE clave = 'version_del_algoritmo'",
        (TEXTO_PROTEGIDO_LARGO,),
    )
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        _abrir(indexada)
    mensaje = str(caso.value)
    assert mensaje == "el sidecar declara versiones incompatibles con este lector"
    assert TEXTO_PROTEGIDO_LARGO not in mensaje
    assert _todo_cerrado(conexiones)


def test_unos_parametros_incompatibles_son_corrupcion(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    _manipular(
        indexada,
        "UPDATE metadatos SET valor = ? WHERE clave = 'parametros'",
        (TEXTO_PROTEGIDO_LARGO,),
    )
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        _abrir(indexada)
    mensaje = str(caso.value)
    assert mensaje == "el sidecar se construyo con otros parametros congelados"
    assert TEXTO_PROTEGIDO_LARGO not in mensaje
    assert _todo_cerrado(conexiones)


def test_unos_conteos_invalidos_son_corrupcion_sin_la_celda(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    _manipular(
        indexada,
        "UPDATE metadatos SET valor = ? WHERE clave = 'terminos'",
        (TEXTO_PROTEGIDO_LARGO,),
    )
    with pytest.raises(vectores.IndiceCorruptoError) as caso:
        _abrir(indexada)
    mensaje = str(caso.value)
    assert "no es un entero canonico" in mensaje
    assert "terminos" in mensaje
    assert TEXTO_PROTEGIDO_LARGO not in mensaje
    assert _todo_cerrado(conexiones)


def test_ningun_mensaje_de_apertura_arrastra_texto_protegido(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Barrido final: se planta el mismo texto protegido en cada celda de
    metadatos, UNA POR UNA, y ningun mensaje lo reproduce.

    El sidecar se restaura entre iteraciones: sin restaurar, la primera celda
    corrupta cortocircuitaria todas las demas y el barrido solo ejerceria una
    rama repetida —el defecto que la auditoria adversarial encontro en la
    primera version de esta prueba—.
    """
    intacto = indexada.sidecar.read_bytes()
    for clave in (
        "version_del_algoritmo",
        "version_de_tokenizacion",
        "parametros",
        "elementos",
        "terminos",
        "huella_del_canon",
    ):
        indexada.sidecar.write_bytes(intacto)
        _manipular(
            indexada,
            "UPDATE metadatos SET valor = ? WHERE clave = ?",
            (TEXTO_PROTEGIDO_LARGO, clave),
        )
        with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
            _abrir(indexada)
        assert TEXTO_PROTEGIDO_LARGO not in str(caso.value), clave
        assert "faro de poniente" not in str(caso.value), clave
        # Y cada celda ejerce SU rama, no la de la primera corrupcion.
        esperado = {
            "version_del_algoritmo": "versiones incompatibles",
            "version_de_tokenizacion": "versiones incompatibles",
            "parametros": "otros parametros congelados",
            "elementos": "el conteo 'elementos'",
            "terminos": "el conteo 'terminos'",
            "huella_del_canon": "formato canonico de SHA-256",
        }[clave]
        assert esperado in str(caso.value), (clave, str(caso.value))


# --------------------------------------------------------------------------
# F. A intacta, por arboles y blobs
# --------------------------------------------------------------------------


def test_common_y_adr002_a_permanecen_intactos_por_arboles() -> None:
    assert (
        _git("rev-parse", "HEAD:experiments/adr002/candidates/common")
        == "7f048eda34ea8ba47182758184e3431ae43663bb"
    )
    assert (
        _git("rev-parse", "HEAD:experiments/adr002/candidates/adr002_a")
        == "71faf3a7f986e3cac1d06746db95a21f6ff36f37"
    )


def test_la_ficha_vigente_de_a_y_su_acta_son_las_congeladas() -> None:
    assert (
        _git("rev-parse", "HEAD:artifacts/adr002_cards/ficha_ADR002-A_v7.json")
        == "215939967a76e1c05366b1fb80262e94339f0ab7"
    )
    acta = (
        "docs/architecture/SIRIUS_0.2_ADR_002_ADR002_A_V3_PREPARADO_BENCHMARK_REAPROBACION_v1.0.md"
    )
    assert _git("rev-parse", f"HEAD:{acta}") == "f2babe06a8c883924a464df6fc96d14f52da367d"


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


# --------------------------------------------------------------------------
# K. Fe de erratas 04: ninguna excepcion sin tipar escapa del candidato
# --------------------------------------------------------------------------


def test_un_conteo_de_miles_de_digitos_es_corrupcion_tipada(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    """Antes: ValueError desnuda del limite de conversion de CPython, que
    ademas revelaba cuantos digitos tenia la celda."""
    intacto = indexada.sidecar.read_bytes()
    for clave in ("elementos", "terminos"):
        indexada.sidecar.write_bytes(intacto)  # sin restaurar, solo se probaria la primera
        _manipular(
            indexada,
            "UPDATE metadatos SET valor = ? WHERE clave = ?",
            ("9" * 5000, clave),
        )
        with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
            _abrir(indexada)
        assert type(caso.value) is vectores.IndiceCorruptoError
        mensaje = str(caso.value)
        assert f"el conteo {clave!r} no es un entero canonico" in mensaje
        assert "5000" not in mensaje
        assert "9999" not in mensaje
        assert _todo_cerrado(conexiones)


def test_un_vector_con_anidamiento_profundo_es_corrupcion_tipada(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Antes: RecursionError desnuda, que no es subtipo de ValueError y
    escapaba del validador central y de los dos except de consultar."""
    intacto = indexada.sidecar.read_bytes()
    for tabla in ("vectores_de_termino", "vectores_de_elemento"):
        indexada.sidecar.write_bytes(intacto)
        _manipular(
            indexada,
            f"UPDATE {tabla} SET dimensiones = ?",
            ("[" * 100000 + "]" * 100000,),
        )
        lector = _abrir(indexada)
        with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
            lector.consultar(("faro",))
        assert type(caso.value) is vectores.IndiceCorruptoError
        assert "longitud superior a la maxima" in str(caso.value)


def test_una_identidad_no_representable_no_llega_al_puerto(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Antes: el lector la aceptaba y SQLite lanzaba OverflowError desnuda a
    traves de la frontera con el puerto."""
    gigante = "MEMORIA:" + "9" * 4000
    assert not vectores._identidad_persistida_valida(gigante)
    _manipular(indexada, "UPDATE posting SET elemento = ?", (gigante,))
    lector = _abrir(indexada)
    with pytest.raises(vectores.IndiceNoUtilizableError) as caso:
        lector.consultar(("faro",))
    assert type(caso.value) is vectores.IndiceCorruptoError
    assert "identidad con formato no canonico" in str(caso.value)
    assert "9999" not in str(caso.value)


def test_el_canon_ilegible_ya_no_filtra_la_conexion_del_sidecar(
    indexada: fixtures_b.FixtureB, conexiones: list[_ConexionVigilada]
) -> None:
    """La limitacion 2 de la fe de erratas 03 se CONSERVA: el escape sigue sin
    tipar. Lo que se corrigio es la fuga del descriptor."""
    indexada.ruta.unlink()
    with pytest.raises(sqlite3.OperationalError):
        _abrir(indexada)
    assert _todo_cerrado(conexiones)
