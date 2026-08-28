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
import subprocess
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
#: (literal propio), el tipo de defecto (literal propio), la posicion ordinal,
#: el nombre del metadato de conteo (literal propio) y la lista de tablas que
#: faltan (diferencia de conjuntos sobre TABLAS_DEL_SIDECAR, de modo que solo
#: puede contener constantes nuestras). Jamas una celda del sidecar, jamas el
#: texto de una excepcion interna, jamas un dato del entorno.
_NOMBRES_PERMITIDOS: Final = frozenset(
    {"tabla", "defecto", "posicion", "clave_de_conteo", "faltan"}
)


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


def test_la_apertura_solo_interpola_nombres_permitidos() -> None:
    """Auditoria COMPLETA del paquete 04: ninguna interpolacion de la
    apertura procede de una celda, de una excepcion interna ni del entorno."""
    nombres = _nombres_interpolados(inspect.getsource(vectores.LectorVectorial.__init__))
    assert nombres <= _NOMBRES_PERMITIDOS, nombres


def test_la_apertura_no_reproduce_la_huella_ni_el_error_fisico() -> None:
    """Las dos fugas del paquete 04, fijadas por nombre."""
    apertura = inspect.getsource(vectores.LectorVectorial.__init__)
    for fuga in (
        "{metadatos.get('huella_del_canon')}",
        '{metadatos.get("huella_del_canon")}',
        "{declarada",
        "{actual",
        "{error",
        "{ruta_sidecar",
        "{ruta_canon",
    ):
        assert fuga not in apertura, fuga


def test_el_error_fisico_de_apertura_conserva_la_causa_sin_reproducirla() -> None:
    apertura = inspect.getsource(vectores.LectorVectorial.__init__)
    assert "except sqlite3.DatabaseError as error:" in apertura
    assert 'msg = "el sidecar no es una base legible"' in apertura
    assert "raise IndiceCorruptoError(msg) from error" in apertura
    assert "except Exception" not in apertura


def test_los_mensajes_de_apertura_son_literales_salvo_dos_justificados() -> None:
    """Todo ``msg =`` de la apertura es una cadena literal salvo dos, y las
    dos interpolan constantes propias: el nombre fijo del metadato de conteo
    y la lista de tablas ausentes."""
    apertura = inspect.getsource(vectores.LectorVectorial.__init__)
    # Recuento sobre TODO el fuente, no por linea: la fuga que el paquete 04
    # corrigio era una f-string multilinea entre parentesis y un recuento por
    # linea no la habria visto (hallazgo de la auditoria adversarial).
    assert apertura.count('f"') == 2
    assert 'f"metadatos: el conteo {clave_de_conteo!r}' in apertura
    assert 'f"el sidecar no contiene las tablas esperadas: faltan {faltan}"' in apertura


def test_la_lista_de_tablas_ausentes_solo_puede_contener_constantes_propias() -> None:
    """``faltan`` es ``sorted(set(TABLAS_DEL_SIDECAR) - presentes)``: una
    diferencia de conjuntos sobre nuestra constante, de modo que jamas puede
    contener un nombre leido del sidecar."""
    apertura = inspect.getsource(vectores.LectorVectorial.__init__)
    assert "faltan = sorted(set(TABLAS_DEL_SIDECAR) - presentes)" in apertura
    # Lo que importa no es la identidad de conjuntos —que seria tautologica—
    # sino que un nombre LEIDO DEL SIDECAR jamas puede aparecer en el mensaje:
    # con una tabla intrusa presente, el resultado no la contiene.
    presentes = {"metadatos", "tabla_intrusa_con_nombre_hostil"}
    faltan = sorted(set(vectores.TABLAS_DEL_SIDECAR) - presentes)
    assert "tabla_intrusa_con_nombre_hostil" not in faltan
    assert set(faltan) < set(vectores.TABLAS_DEL_SIDECAR)


# --------------------------------------------------------------------------
# Huella persistida: validador cerrado, corrupcion frente a desfase
# --------------------------------------------------------------------------


def test_existe_un_validador_cerrado_de_sha256_persistido() -> None:
    assert vectores._FORMATO_DE_HUELLA_PERSISTIDA.pattern == r"[0-9a-f]{64}"
    assert ".fullmatch(" in inspect.getsource(vectores._huella_persistida_valida)


def test_el_validador_acepta_solo_sesenta_y_cuatro_hexadecimales_minusculos() -> None:
    valida = "0" * 63 + "f"
    assert vectores._huella_persistida_valida(valida)
    for invalida in (
        "",
        "0" * 63,
        "0" * 65,
        "F" * 64,
        "0" * 63 + "G",
        " " + "0" * 63,
        "0" * 63 + " ",
        "0" * 64 + "\n",
        "\n" + "0" * 64,
        "sha256:" + "0" * 64,
    ):
        assert not vectores._huella_persistida_valida(invalida), invalida
    for no_cadena in (None, 12345, True, b"0" * 64):
        assert not vectores._huella_persistida_valida(no_cadena)


def test_el_formato_invalido_es_corrupcion_y_el_valor_distinto_es_desfase() -> None:
    """Las dos causas son distinguibles por tipo, y el formato se valida
    ANTES de recomputar la huella del canon."""
    apertura = inspect.getsource(vectores.LectorVectorial.__init__)
    validacion = apertura.index("_huella_persistida_valida")
    recomputo = apertura.index("huella_del_canon(ruta_canon)")
    comparacion = apertura.index("raise IndiceDesfasadoError")
    assert validacion < recomputo < comparacion
    corrupcion = apertura[validacion:recomputo]
    assert "raise IndiceCorruptoError" in corrupcion
    assert "formato canonico de SHA-256" in corrupcion
    assert apertura.count("raise IndiceDesfasadoError(msg)") == 1


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
    # Cotas anadidas por la fe de erratas 04 contra los escapes sin tipar.
    assert vectores._DIGITOS_MAXIMOS_DE_ENTERO == 19
    assert vectores._LONGITUD_MAXIMA_DE_VECTOR == 16384


# --------------------------------------------------------------------------
# Fe de erratas 04: ninguna excepcion sin tipar puede escapar
# --------------------------------------------------------------------------


def test_el_conteo_se_acota_en_digitos_antes_de_convertirlo() -> None:
    """Sin la cota, int() lanzaba ValueError sin tipar (limite de CPython)."""
    apertura = inspect.getsource(vectores.LectorVectorial.__init__)
    cota = apertura.index("_DIGITOS_MAXIMOS_DE_ENTERO")
    conversion = apertura.index("int(declarado)")
    assert cota < conversion


def test_el_vector_se_acota_en_longitud_antes_de_deserializar() -> None:
    """Sin la cota, el decodificador podia lanzar RecursionError sin tipar."""
    validador = inspect.getsource(vectores._pares_de_vector_validados)
    cota = validador.index("_LONGITUD_MAXIMA_DE_VECTOR")
    deserializacion = validador.index("json.loads(")
    assert cota < deserializacion
    assert "except RecursionError as error:" in validador
    assert "anidamiento no admisible" in validador


def test_la_identidad_persistida_es_representable_por_el_puerto() -> None:
    """Sin la cota, una identidad de miles de digitos hacia estallar a SQLite
    con OverflowError, un escape sin tipar desde E3."""
    assert vectores._identidad_persistida_valida("MEMORIA:1")
    assert vectores._identidad_persistida_valida(f"MEMORIA:{2**63 - 1}")
    assert not vectores._identidad_persistida_valida("MEMORIA:" + "9" * 4000)
    assert not vectores._identidad_persistida_valida(f"MEMORIA:{2**63}")
    assert not vectores._identidad_persistida_valida("MEMORIA:" + "9" * 19)


def test_la_recomputacion_del_canon_cierra_la_conexion_al_fallar() -> None:
    """La limitacion 2 (canon ilegible sin tipar) se CONSERVA declarada; lo
    que se corrige es la fuga del descriptor del sidecar."""
    apertura = inspect.getsource(vectores.LectorVectorial.__init__)
    bloque = apertura[apertura.index("vigente = huella_del_canon") :]
    assert "except BaseException:" in bloque
    assert "self._conexion.close()" in bloque
    assert "raise\n" in bloque


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


# --------------------------------------------------------------------------
# Alcance del paquete 04: nada fuera de adr002_b, ningun limite movido
# --------------------------------------------------------------------------


def _git(*argumentos: str) -> str:
    return subprocess.run(
        ["git", *argumentos],
        cwd=str(RAIZ_CANDIDATOS.parents[2]),
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()


def test_common_y_adr002_a_permanecen_en_sus_arboles_exactos() -> None:
    """Se comprueba SIEMPRE, tambien mientras las funcionales estan
    suspendidas: la regla de parada del paquete 04 no admite tocarlos."""
    assert (
        _git("rev-parse", "HEAD:experiments/adr002/candidates/common")
        == "7f048eda34ea8ba47182758184e3431ae43663bb"
    )
    assert (
        _git("rev-parse", "HEAD:experiments/adr002/candidates/adr002_a")
        == "71faf3a7f986e3cac1d06746db95a21f6ff36f37"
    )


def test_los_limites_de_consulta_y_almacenamiento_no_se_movieron() -> None:
    """El paquete 04 no toca ``consultar``: mismas tres sentencias dirigidas
    al sidecar y mismos parametros congelados."""
    validando = inspect.getsource(vectores.LectorVectorial._consultar_validando)
    assert validando.count("self._conexion.execute(") == 3
    assert vectores.ALMACENAMIENTO_MAXIMO_SIDECAR_B == 33_554_432
    assert vectores.ELEMENTOS_EXAMINADOS_MAXIMOS == 4096
    assert vectores.TOP_K == 8
    assert vectores.SOLAPAMIENTO_MINIMO == 2
    assert vectores.CONSULTA_TERMINOS_MAXIMOS == 16
    assert vectores.VOCABULARIO_MAXIMO == 4096
    assert vectores.PARAMETROS_CONGELADOS == {
        "vocabulario_maximo": 4096,
        "frecuencia_documental_minima": 2,
        "tokens_por_elemento_maximos": 64,
        "dimensiones_maximas_por_vector": 256,
        "escala_fija": 1_000_000,
        "consulta_terminos_maximos": 16,
        "top_k": 8,
        "solapamiento_minimo": 2,
        "elementos_examinados_maximos": 4096,
    }
