"""Comprobaciones ESTATICAS de ``ADR002-B``.

El paquete 12 prohibe ejecutar el candidato y construir ningun indice antes de
que su ficha este congelada. Estas pruebas respetan esa guarda: **no ejecutan
el motor, no construyen bases de datos y no construyen el sidecar**.
Inspeccionan estructura, contratos, composicion y parametros congelados sobre
el codigo y sobre los tipos, que es todo lo que este commit permite.

Las pruebas funcionales llegan despues, en su propio commit, cuando el commit
de entrada de ``ficha_ADR002-B_v1.json`` ya sea ancestro estricto.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from experiments.adr002.candidates.adr002_b import candidate as b
from experiments.adr002.candidates.adr002_b import vectores
from experiments.adr002.candidates.common import neutrality
from experiments.adr002.candidates.common.contracts import SenalesDeCandidato
from experiments.adr002.cards import card_protocol as cp

RAIZ = Path(__file__).resolve().parents[3]
PAQUETE = RAIZ / "experiments/adr002/candidates/adr002_b"


def _fuente(nombre: str) -> str:
    return (PAQUETE / nombre).read_text(encoding="utf-8")


def _codigo(nombre: str) -> str:
    """Fuente sin docstrings ni comentarios: los controles miran el CODIGO."""
    return neutrality._sin_comentarios(_fuente(nombre))


# --------------------------------------------------------------------------
# Aislamiento y neutralidad
# --------------------------------------------------------------------------


def test_adr002_b_no_reimplementa_el_motor_ni_las_puertas() -> None:
    """El mismo control de aislamiento que rige para ``ADR002-A``."""
    assert neutrality.fallos_de_aislamiento_del_candidato(RAIZ, "adr002_b") == []


def test_la_capa_comun_sigue_neutral_con_b_presente() -> None:
    """Anadir B no puede haber ensuciado la capa comun: se recomprueba."""
    assert neutrality.fallos_de_neutralidad(RAIZ) == []


def test_la_base_de_a_no_cambio_ni_un_byte() -> None:
    """Los blobs de ``adr002_a`` y ``common`` son los preinscritos vigentes.

    Es la regla de parada hecha maquina: si un candidato exigiera tocar la
    base en silencio, este control lo denunciaria. El paquete de correccion
    02 SI toco ``contracts.py`` y ``port.py`` —por eso existen las fichas
    sucesoras A v3 y B v2—, y sus blobs quedan fijados aqui de nuevo: el
    proximo cambio silencioso volvera a fallar.

    El **paso 5 del plan aprobado** —«corregir `common` una sola vez»— toco
    los siete modulos comunes, anadio ``grouping.py`` y alcanzo a ``adr002_a``
    en los dos puntos donde leia la clave de sujeto como cadena. Los blobs se
    vuelven a fijar aqui: la regla no se levanta, se reancla, y el proximo
    cambio no autorizado seguira fallando.
    """
    import subprocess

    fijados = {
        "experiments/adr002/candidates/common/contracts.py": (
            "3cfa7bc75268e68a3e368c93625bf7d71d3e51d0"
        ),
        "experiments/adr002/candidates/common/engine.py": (
            "991c68d5f04b48521e2d1450ff071aa7497f3744"
        ),
        "experiments/adr002/candidates/common/gates.py": (
            "8e6f0e57850658f763d10277dc0574bd6c78fcbb"
        ),
        "experiments/adr002/candidates/common/stops.py": (
            "b1f737efd91e140c9af691c6a7e2323c84d54c4c"
        ),
        "experiments/adr002/candidates/common/port.py": (
            "90d5d043ef128cb795f6613953ee0fea6acfb825"
        ),
        "experiments/adr002/candidates/common/trace.py": (
            "01d97bbc5244774caf6bce687d17c4b4e620d4aa"
        ),
        "experiments/adr002/candidates/common/derived.py": (
            "996e353b44fe16af035689912a6a69520ee8097e"
        ),
        "experiments/adr002/candidates/common/grouping.py": (
            "12ec4f89273b75dae5ede4d686b8e0d2c16f483b"
        ),
        "experiments/adr002/candidates/common/neutrality.py": (
            "a7828c5d17902a8abc7ec90407607fcc29da75cf"
        ),
        "experiments/adr002/candidates/adr002_a/candidate.py": (
            "d057c12a9be4df15b2d3bfe50b986cbc57403273"
        ),
        "experiments/adr002/candidates/adr002_a/lexical.py": (
            "7e88de4cfb07384bc99034e10aab44c801dd4796"
        ),
    }
    for ruta, blob in fijados.items():
        observado = subprocess.run(
            ["git", "hash-object", str(RAIZ / ruta)],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        assert observado == blob, f"{ruta}: {observado} != {blob} (base alterada)"


# --------------------------------------------------------------------------
# Identidad, protocolo y composicion
# --------------------------------------------------------------------------


def test_adr002_b_declara_su_definicion_canonica() -> None:
    assert b.IDENTIFICADOR == "ADR002-B"
    assert "senal semantica vectorial" in b.DEFINICION_CANONICA
    assert "unicamente en etapas tardias" in b.DEFINICION_CANONICA
    assert "tras fallar la puerta de suficiencia" in b.DEFINICION_CANONICA


def test_la_senal_declarada_es_la_de_su_alternativa() -> None:
    """La ficha exigira exactamente esta cadena; discrepar la invalidaria."""
    assert b.SENAL_TARDIA == cp.SENAL_POR_ALTERNATIVA["ADR002-B"] == "semantica_vectorial"


def test_adr002_b_satisface_el_protocolo_del_candidato() -> None:
    """Construir la instancia es de tipos, no de ejecucion: nada se abre."""
    instancia = b.candidato(Path("no-existe.db"), Path("no-existe.vectores.db"))
    assert isinstance(instancia, SenalesDeCandidato)
    assert instancia.identificador == "ADR002-B"
    assert instancia.senal_tardia_habilitada == "semantica_vectorial"


def test_el_indice_es_perezoso_y_no_se_abre_al_construir() -> None:
    """Cero trabajo adelantado: ni abierto ni consultado al instanciar.

    Las rutas apuntan a ficheros inexistentes a proposito: si la construccion
    del candidato abriera el sidecar, esta prueba reventaria con el error
    tipado en vez de pasar.
    """
    instancia = b.candidato(Path("no-existe.db"), Path("no-existe.vectores.db"))
    assert instancia.indice_abierto is False
    assert instancia.invocaciones_vectoriales == 0
    assert instancia.registro_vectorial is None


def test_la_composicion_delega_en_a_y_no_copia_su_logica() -> None:
    """``ADR002-B = ADR002-A v2 + senal vectorial``: contiene, no duplica."""
    codigo = _codigo("candidate.py")
    assert "CandidatoA()" in codigo
    assert "self._base.candidatas(contexto)" in codigo
    assert "self._base.leer(item, consulta)" in codigo
    for duplicado in (
        "def _e1",
        "def _e2",
        "def _e3",
        "def _e4",
        "def _terminos_puente",
        "def _familias_de_sujeto",
        "def _construir",
    ):
        assert duplicado not in codigo, f"logica de A copiada: {duplicado}"


def test_la_ruta_vectorial_solo_puede_activarse_en_e3() -> None:
    """La guarda de etapa esta en el codigo y es unica.

    El motor ya garantiza el orden; esta guarda garantiza que el candidato ni
    siquiera puede intentarlo fuera de ``E3``, y que la ruta vectorial tiene
    un unico punto de entrada.
    """
    codigo = _codigo("candidate.py")
    assert "contexto.etapa is not Etapa.E3" in codigo
    assert codigo.count("self._vectoriales(") == 1
    guarda = codigo.index("contexto.etapa is not Etapa.E3")
    invocacion = codigo.index("self._vectoriales(")
    assert guarda < invocacion, "la guarda de etapa debe preceder a la invocacion"


def test_el_candidato_no_traga_los_fallos_del_indice() -> None:
    """Fail closed: el candidato no captura para degradar.

    Capturar el error tipado del indice para degradar a «sin vector» seria
    exactamente la degradacion silenciosa que el paquete 12 prohibe. El UNICO
    ``except`` admitido es la defensa de frontera del paquete de correccion
    03: captura exclusivamente el error tipado del puerto y lo RE-LANZA como
    corrupcion de indice con la causa preservada; no traga nada.
    """
    codigo = _codigo("candidate.py")
    assert codigo.count("except ") == 1
    assert "except IdentificadorInvalidoError as error:" in codigo
    assert "raise vectores.IndiceCorruptoError(msg) from error" in codigo
    for tragado in ("except Exception", "except vectores.", "except Indice"):
        assert tragado not in codigo


def test_el_ambito_no_es_generador_tampoco_en_b() -> None:
    """El defecto 2 de A no puede reaparecer en B."""
    codigo = _codigo("candidate.py") + _codigo("vectores.py")
    assert "por_entidad" not in codigo
    assert "ambito.proyectos" not in codigo


def test_b_materializa_por_identidad_y_nunca_por_clave() -> None:
    """El defecto del paquete de correccion 02 no puede reaparecer.

    La ruta vectorial pide al puerto exactamente los identificadores que el
    sidecar devolvio; la clave de sujeto ya no decide que fila se recupera, y
    una identidad ausente falla cerrada en vez de perderse callada.
    """
    codigo = _codigo("candidate.py")
    assert "por_identificadores" in codigo
    assert "por_clave_exacta" not in codigo
    assert "materializacion.ausentes" in codigo
    assert "IndiceInconsistenteError" in codigo


# --------------------------------------------------------------------------
# Parametros congelados por el paquete 12
# --------------------------------------------------------------------------


def test_los_parametros_congelados_son_los_del_paquete_12() -> None:
    """Los valores del §6 del paquete, uno a uno. Cambiarlos exige acto."""
    assert vectores.VOCABULARIO_MAXIMO == 4096
    assert vectores.FRECUENCIA_DOCUMENTAL_MINIMA == 2
    assert vectores.TOKENS_POR_ELEMENTO_MAXIMOS == 64
    assert vectores.DIMENSIONES_MAXIMAS_POR_VECTOR == 256
    assert vectores.ESCALA_FIJA == 1_000_000
    assert vectores.CONSULTA_TERMINOS_MAXIMOS == 16
    assert vectores.TOP_K == 8
    assert vectores.SOLAPAMIENTO_MINIMO == 2
    assert vectores.ELEMENTOS_EXAMINADOS_MAXIMOS == 4096
    assert vectores.ALMACENAMIENTO_MAXIMO_SIDECAR_B == 33_554_432
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


def test_el_sidecar_declara_versiones() -> None:
    assert vectores.VERSION_DEL_ALGORITMO == "ppmi-documental-disperso-v1"
    assert vectores.VERSION_DE_TOKENIZACION == "adr002_a.lexical-v1"


def test_las_cotas_de_b_respetan_las_de_la_infraestructura() -> None:
    """Las cotas nuevas son de la misma familia que las existentes.

    La segunda asercion no es decorativa: la materializacion por clave exacta
    solo es correcta mientras ``TOP_K`` quepa en los argumentos que el puerto
    admite; si alguien subiera ``TOP_K`` por encima, ``_acotar`` truncaria
    claves en silencio y se perderian coincidencias.
    """
    from experiments.adr002.candidates.adr002_a import candidate as a
    from experiments.adr002.candidates.common import port

    assert vectores.CONSULTA_TERMINOS_MAXIMOS == port.ARGUMENTOS_MAXIMOS
    assert vectores.TOP_K <= port.ARGUMENTOS_MAXIMOS
    assert vectores.TOP_K == a.TERMINOS_PUENTE_MAXIMOS
    assert vectores.DIMENSIONES_MAXIMAS_POR_VECTOR * 2 == port.LIMITE_POR_CONSULTA


# --------------------------------------------------------------------------
# El sidecar: separacion del canon y fallo cerrado
# --------------------------------------------------------------------------


def test_la_consulta_vectorial_devuelve_identificadores_y_nunca_contenido() -> None:
    """El indice no puede convertirse en segunda fuente de verdad."""
    campos = {campo.name for campo in dataclasses.fields(vectores.CoincidenciaVectorial)}
    assert campos == {"elemento", "clave_de_sujeto", "similitud_fija", "solapamiento"}
    assert "texto" not in campos
    assert "contenido" not in campos


def test_las_lecturas_del_canon_son_dirigidas_y_de_solo_lectura() -> None:
    """El ciclo de vida lee el canon con predicado y jamas lo escribe."""
    for sql in (vectores._SQL_MEMORIAS_VIGENTES, vectores._SQL_DECISIONES_APROBADAS):
        normalizado = " ".join(sql.split()).upper()
        assert normalizado.startswith("SELECT")
        assert " WHERE " in normalizado
    codigo = _codigo("vectores.py")
    assert re.search(r"\b(UPDATE|DELETE FROM|ALTER TABLE)\b", codigo) is None
    for tabla_del_canon in (
        "memories",
        "memory_revisions",
        "decisions",
        "decision_revisions",
        "messages",
        "knowledge_fts",
        "message_fts",
    ):
        assert re.search(rf"CREATE\s+(VIRTUAL\s+)?TABLE\s+{tabla_del_canon}\b", codigo) is None
        assert f"DROP TABLE IF EXISTS {tabla_del_canon}" not in codigo


def test_el_fallo_del_indice_es_cerrado_y_tipado() -> None:
    """Tres causas, tres tipos, un antecesor comun. Nada se degrada."""
    for tipo in (
        vectores.IndiceInexistenteError,
        vectores.IndiceCorruptoError,
        vectores.IndiceDesfasadoError,
    ):
        assert issubclass(tipo, vectores.IndiceNoUtilizableError)
        assert issubclass(tipo, RuntimeError)
    codigo = _codigo("vectores.py")
    assert "raise IndiceInexistenteError" in codigo
    assert "raise IndiceCorruptoError" in codigo
    assert "raise IndiceDesfasadoError" in codigo


def test_el_borrado_cubre_los_cuatro_ficheros() -> None:
    """El contrato de purga de ADR-001 aplica entero al sidecar."""
    assert vectores.SUFIJOS_DE_FICHERO == ("", "-wal", "-shm", "-journal")


def test_ninguna_dependencia_prohibida_en_adr002_b() -> None:
    """Biblioteca estandar y SQLite: nada externo, nada descargado."""
    for nombre in ("candidate.py", "vectores.py", "__init__.py"):
        codigo = _codigo(nombre)
        for dependencia in neutrality.IMPORTS_PROHIBIDOS:
            patron = rf"^\s*(import|from)\s+{re.escape(dependencia)}\b"
            assert re.search(patron, codigo, re.M) is None, f"{nombre}: {dependencia}"


def test_el_paquete_no_conoce_el_benchmark() -> None:
    """Ni casos oficiales, ni adjudicaciones, ni etiquetas esperadas."""
    for nombre in ("candidate.py", "vectores.py", "__init__.py"):
        fuente = _fuente(nombre)
        for prohibido in ("B04-CA-", "PDP-CA-", "RED-0", "ESPERADOS", "casos_oficiales"):
            assert prohibido not in fuente, f"{nombre}: {prohibido}"
