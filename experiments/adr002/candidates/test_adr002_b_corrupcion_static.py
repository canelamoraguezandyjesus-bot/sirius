"""Controles ESTATICOS del paquete de correccion 03, sin ejecutar B.

Todo lo que aqui se comprueba se lee del codigo fuente: no se construye
ningun sidecar, no se ejecuta ninguna consulta y no se toca ningun fixture
funcional —eso llega despues de congelar la ficha B v3 (TOL-210, regla 3)—.

Lo que se demuestra:

- la deserializacion de vectores esta CENTRALIZADA: ``json.loads`` aparece
  una unica vez en ``vectores.py``, dentro del validador central, y ninguna
  ruta de consulta lo usa directamente;
- la identidad persistida se valida en el lector ANTES de llegar al puerto,
  con ``fullmatch`` y con las clases del contrato comun como unica fuente;
- los mensajes de corrupcion no interpolan celdas del sidecar: solo tabla,
  tipo de defecto y posicion o conteo;
- la defensa en profundidad del candidato captura unicamente el error tipado
  del puerto, lo traduce con causa preservada y mensaje literal minimizado;
- toda corrupcion en consulta cierra la conexion;
- el constructor descarta pesos que redondean a cero, para que el invariante
  «peso estrictamente positivo» sea real;
- la referencia documental de la composicion es ``ADR002-A`` v3;
- ``common`` y ``adr002_a`` no se tocaron (los anclajes de blobs de
  ``test_adr002_b_static.py`` siguen vigentes y lo prueban en cada corrida).
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.adr002_b import candidate, vectores

RAIZ_CANDIDATOS: Final = Path(__file__).resolve().parent

FUENTE_VECTORES: Final = (RAIZ_CANDIDATOS / "adr002_b" / "vectores.py").read_text(encoding="utf-8")
FUENTE_CANDIDATO: Final = (RAIZ_CANDIDATOS / "adr002_b" / "candidate.py").read_text(
    encoding="utf-8"
)


# --------------------------------------------------------------------------
# Deserializacion centralizada
# --------------------------------------------------------------------------


def test_json_loads_aparece_solo_en_el_validador_central() -> None:
    """Una unica deserializacion admitida: la del validador."""
    assert FUENTE_VECTORES.count("json.loads(") == 1
    validador = inspect.getsource(vectores._pares_de_vector_validados)
    assert "json.loads(" in validador


def test_ninguna_ruta_de_consulta_deserializa_por_su_cuenta() -> None:
    consultar = inspect.getsource(vectores.LectorVectorial.consultar)
    validando = inspect.getsource(vectores.LectorVectorial._consultar_validando)
    assert "json.loads" not in consultar
    assert "json.loads" not in validando
    assert "_pares_de_vector_validados" in validando


def test_la_consulta_no_usa_coerciones_de_tipo_sobre_celdas() -> None:
    """Ni ``int(...)`` ni ``str(...)`` sobre celdas: tipo exacto o corrupcion."""
    validando = inspect.getsource(vectores.LectorVectorial._consultar_validando)
    assert "int(fila[0])" not in validando
    assert "str(elemento)" not in validando
    assert "_es_entero_real" in validando


# --------------------------------------------------------------------------
# Identidad: validada en el lector, antes del puerto
# --------------------------------------------------------------------------


def test_el_formato_de_identidad_procede_de_la_clase_comun_y_es_fullmatch() -> None:
    assert "re.escape(clase.value) for clase in Clase" in FUENTE_VECTORES
    assert ".fullmatch(" in FUENTE_VECTORES


def test_la_identidad_se_valida_antes_de_construir_coincidencias() -> None:
    validando = inspect.getsource(vectores.LectorVectorial._consultar_validando)
    validacion = validando.index("_identidad_persistida_valida")
    construccion = validando.index("CoincidenciaVectorial(")
    assert validacion < construccion


def test_el_candidato_defiende_la_frontera_con_el_puerto() -> None:
    """Captura SOLO el error tipado del puerto y lo traduce con causa."""
    fuente = inspect.getsource(candidate.CandidatoB._vectoriales)
    assert "except IdentificadorInvalidoError as error:" in fuente
    assert "raise vectores.IndiceCorruptoError(msg) from error" in fuente
    assert "except Exception" not in fuente
    assert "except ValueError" not in fuente


def test_el_mensaje_de_la_defensa_es_literal_y_minimizado() -> None:
    """El mensaje de la traduccion no interpola NADA: es una constante."""
    fuente = inspect.getsource(candidate.CandidatoB._vectoriales)
    bloque = fuente[fuente.index("except IdentificadorInvalidoError") :]
    bloque = bloque[: bloque.index("raise vectores.IndiceCorruptoError")]
    assert "{" not in bloque.replace("{'", "'")  # sin f-strings en el mensaje


# --------------------------------------------------------------------------
# Minimizacion: los mensajes de corrupcion no llevan celdas
# --------------------------------------------------------------------------

_INTERPOLACION: Final = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)")

#: Los unicos nombres que un mensaje de corrupcion puede interpolar: la tabla
#: (literal propio), el tipo de defecto (literal propio), la posicion ordinal
#: y el nombre del metadato de conteo (literal propio). Jamas una celda.
_NOMBRES_PERMITIDOS: Final = frozenset({"tabla", "defecto", "posicion", "clave_de_conteo"})


def _nombres_interpolados(fuente: str) -> frozenset[str]:
    return frozenset(_INTERPOLACION.findall(fuente))


def test_los_validadores_solo_interpolan_nombres_permitidos() -> None:
    for funcion in (
        vectores._pares_de_vector_validados,
        vectores._norma_cuadrada_validada,
    ):
        nombres = _nombres_interpolados(inspect.getsource(funcion))
        assert nombres <= _NOMBRES_PERMITIDOS, nombres


def test_la_consulta_solo_interpola_posicion_y_marcas_de_sql() -> None:
    nombres = _nombres_interpolados(
        inspect.getsource(vectores.LectorVectorial._consultar_validando)
    )
    assert nombres <= (_NOMBRES_PERMITIDOS | {"marcas"}), nombres


def test_los_conteos_de_metadatos_no_interpolan_la_celda() -> None:
    apertura = inspect.getsource(vectores.LectorVectorial.__init__)
    assert "{declarado" not in apertura
    assert "no es un entero canonico" in apertura
    assert "excede el vocabulario maximo" in apertura


# --------------------------------------------------------------------------
# Cierre de conexiones y traduccion fisica
# --------------------------------------------------------------------------


def test_toda_corrupcion_en_consulta_cierra_la_conexion() -> None:
    consultar = inspect.getsource(vectores.LectorVectorial.consultar)
    assert "except IndiceCorruptoError:" in consultar
    assert "except sqlite3.DatabaseError as error:" in consultar
    assert consultar.count("self._conexion.close()") == 2


def test_la_apertura_valida_los_conteos_y_cierra_al_fallar() -> None:
    apertura = inspect.getsource(vectores.LectorVectorial.__init__)
    seccion = apertura[apertura.index("conteos") :]
    assert seccion.count("self._conexion.close()") >= 2
    assert "_terminos_totales" in apertura


# --------------------------------------------------------------------------
# Invariantes del formato persistido
# --------------------------------------------------------------------------


def test_el_constructor_descarta_pesos_que_redondean_a_cero() -> None:
    construir = inspect.getsource(vectores.construir)
    assert "if peso <= 0:" in construir
    assert "if v > 0" in construir


def test_las_cotas_del_validador_son_las_congeladas() -> None:
    assert vectores.DIMENSIONES_MAXIMAS_POR_VECTOR == 256
    assert vectores._ENTERO_MAXIMO_DE_SQLITE == 2**63 - 1
    assert vectores._TOLERANCIA_DE_COSENO == 1e-9
    assert vectores.ESCALA_FIJA == 1_000_000


def test_la_puntuacion_fija_queda_recortada_a_la_escala() -> None:
    validando = inspect.getsource(vectores.LectorVectorial._consultar_validando)
    assert "min(round(coseno * ESCALA_FIJA), ESCALA_FIJA)" in validando


def test_el_join_de_candidatos_expone_referencias_huerfanas() -> None:
    """LEFT JOIN con columna de solapamiento: lo huerfano aparece y falla."""
    validando = inspect.getsource(vectores.LectorVectorial._consultar_validando)
    assert "LEFT JOIN vectores_de_elemento" in validando
    assert "c.solapamiento" in validando
    assert "referencia huerfana" in validando
    assert "solapamiento incoherente" in validando


# --------------------------------------------------------------------------
# Referencia documental y jerarquia de errores
# --------------------------------------------------------------------------


def test_la_composicion_documenta_la_base_vigente_a_v3() -> None:
    assert "`ADR002-A` v3 + senal vectorial tardia" in FUENTE_CANDIDATO
    assert "`ADR002-A` v2" not in FUENTE_CANDIDATO


def test_la_jerarquia_de_errores_no_crece() -> None:
    """La corrupcion logica es IndiceCorruptoError: no se inventan subtipos."""
    assert issubclass(vectores.IndiceCorruptoError, vectores.IndiceNoUtilizableError)
    assert issubclass(vectores.IndiceInconsistenteError, vectores.IndiceNoUtilizableError)
    tipados = {
        nombre
        for nombre in vectores.__all__
        if nombre.startswith("Indice") and nombre.endswith("Error")
    }
    assert tipados == {
        "IndiceNoUtilizableError",
        "IndiceInexistenteError",
        "IndiceCorruptoError",
        "IndiceDesfasadoError",
        "IndiceInconsistenteError",
    }
