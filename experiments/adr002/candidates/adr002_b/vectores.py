"""Indice vectorial distribucional de ``ADR002-B``: disperso, derivado y no autoritativo.

Es la realizacion experimental de la senal semantica vectorial tardia. El
benchmark decidira si aporta mejora material; su eleccion **no aprueba**
embeddings, proveedor ni almacenamiento para produccion (ARQ-00 §23 prohibe
decidirlos «hasta que la evidencia los justifique»; B04-RF-31 prohibe atar el
contrato a una realizacion).

Como funciona, entero, local y sin red:

1. **Coocurrencia documental.** Cada elemento canonico vigente es una unidad
   de coocurrencia. Dos terminos coocurren si aparecen en el mismo elemento;
   el conteo es binario por elemento: determinista y ajeno al orden interno.
2. **PPMI en punto fijo.** ``max(0, ln(n(t,c)*N / (df(t)*df(c))))`` escalado a
   entero por 10^6. No se persiste ningun flotante: dos construcciones sobre
   el mismo canon producen exactamente los mismos enteros, y la determinacion
   se comprueba por igualdad, no se promete.
3. **Vectores de elemento.** Suma de los vectores PPMI de sus terminos en
   vocabulario, podada a las dimensiones de mayor peso.
4. **Consulta.** Mismo vocabulario y misma transformacion que los elementos.
   Candidato solo quien comparte con la consulta al menos
   ``SOLAPAMIENTO_MINIMO`` dimensiones positivas —condicion estructural: una
   coincidencia numerica minima no fabrica candidatas—. Orden por coseno con
   desempate estable. Se devuelven identificadores, claves de sujeto y
   similitudes: **nunca contenido**; el contenido lo materializa despues el
   puerto canonico con una consulta dirigida.
5. **Fail closed.** Indice inexistente, corrupto o cuya huella de canon ya no
   coincide -> excepcion tipada. Ninguna degradacion silenciosa. La
   corrupcion LOGICA —un SQLite que supera quick_check pero cuyos valores
   violan el formato persistido normativo— tambien falla cerrada: identidades,
   vectores JSON, normas y aritmetica de similitud se validan sobre los datos
   realmente consumidos por cada consulta, con mensajes minimizados que jamas
   reproducen celdas del sidecar (paquete de correccion 03).

Las dos lecturas directas del canon de este modulo —construir y recomputar la
huella de origen— son **ciclo de vida del derivado**, la misma naturaleza que
el repoblado de ``derived.py``: no entregan contenido al flujo de resultados.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, TypeGuard

from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.common.contracts import Clase

# --------------------------------------------------------------------------
# Version y parametros congelados por el paquete de trabajo 12, antes de
# ejecutar nada. Ningun valor procede de una medicion: no existe ninguna.
# --------------------------------------------------------------------------

VERSION_DEL_ALGORITMO: Final = "ppmi-documental-disperso-v1"
VERSION_DE_TOKENIZACION: Final = "adr002_a.lexical-v1"

VOCABULARIO_MAXIMO: Final = 4096
FRECUENCIA_DOCUMENTAL_MINIMA: Final = 2
TOKENS_POR_ELEMENTO_MAXIMOS: Final = 64
DIMENSIONES_MAXIMAS_POR_VECTOR: Final = 256
ESCALA_FIJA: Final = 1_000_000
CONSULTA_TERMINOS_MAXIMOS: Final = 16
TOP_K: Final = 8
SOLAPAMIENTO_MINIMO: Final = 2
ELEMENTOS_EXAMINADOS_MAXIMOS: Final = 4096
ALMACENAMIENTO_MAXIMO_SIDECAR_B: Final = 33_554_432

PARAMETROS_CONGELADOS: Final[dict[str, int]] = {
    "vocabulario_maximo": VOCABULARIO_MAXIMO,
    "frecuencia_documental_minima": FRECUENCIA_DOCUMENTAL_MINIMA,
    "tokens_por_elemento_maximos": TOKENS_POR_ELEMENTO_MAXIMOS,
    "dimensiones_maximas_por_vector": DIMENSIONES_MAXIMAS_POR_VECTOR,
    "escala_fija": ESCALA_FIJA,
    "consulta_terminos_maximos": CONSULTA_TERMINOS_MAXIMOS,
    "top_k": TOP_K,
    "solapamiento_minimo": SOLAPAMIENTO_MINIMO,
    "elementos_examinados_maximos": ELEMENTOS_EXAMINADOS_MAXIMOS,
}

#: Origen exclusivo del indice: memorias vigentes y decisiones aprobadas, con
#: su revision canonica vigente. Ni mensajes como verdad, ni datos del
#: benchmark, ni datos externos. Ambas lecturas son dirigidas por estado.
_SQL_MEMORIAS_VIGENTES: Final = """
SELECT m.id, m.subject_key, r.content
FROM memories AS m
JOIN memory_revisions AS r ON r.memory_id = m.id AND r.is_current = 1
WHERE m.status = 'current' AND r.content IS NOT NULL
ORDER BY m.id
"""
_SQL_DECISIONES_APROBADAS: Final = """
SELECT d.id, d.subject, r.content
FROM decisions AS d
JOIN decision_revisions AS r ON r.decision_id = d.id AND r.is_current = 1
WHERE d.status = 'approved' AND r.content IS NOT NULL
ORDER BY d.id
"""

#: Las tablas del sidecar. Cerradas: el volcado logico las recorre todas.
TABLAS_DEL_SIDECAR: Final[tuple[str, ...]] = (
    "metadatos",
    "vocabulario",
    "vectores_de_termino",
    "vectores_de_elemento",
    "posting",
)

#: Sufijos que el borrado debe eliminar ademas del fichero principal.
SUFIJOS_DE_FICHERO: Final[tuple[str, ...]] = ("", "-wal", "-shm", "-journal")


class IndiceNoUtilizableError(RuntimeError):
    """El indice vectorial no puede usarse. Siempre se falla cerrado."""


class IndiceInexistenteError(IndiceNoUtilizableError):
    """No hay sidecar donde deberia haberlo."""


class IndiceCorruptoError(IndiceNoUtilizableError):
    """El sidecar existe pero no es integro o no es compatible."""


class IndiceDesfasadoError(IndiceNoUtilizableError):
    """El canon cambio desde que el indice se construyo."""


class IndiceInconsistenteError(IndiceNoUtilizableError):
    """El indice cita identidades que el canon no contiene.

    Un derivado que afirma la existencia de elementos inexistentes no es
    evidencia utilizable: se falla cerrado, sin recuperacion parcial y sin
    degradar a la base lexico-estructurada. El mensaje contiene solo
    identificadores y clases, jamas contenido.
    """


# --------------------------------------------------------------------------
# Huella del canon de origen: la que detecta el desfase
# --------------------------------------------------------------------------


def _elementos_del_canon(conexion: sqlite3.Connection) -> list[tuple[str, str, str]]:
    filas: list[tuple[str, str, str]] = []
    for identidad, clave, texto in conexion.execute(_SQL_MEMORIAS_VIGENTES):
        filas.append((f"MEMORIA:{identidad}", str(clave or ""), str(texto or "")))
    for identidad, clave, texto in conexion.execute(_SQL_DECISIONES_APROBADAS):
        filas.append((f"DECISION:{identidad}", str(clave or ""), str(texto or "")))
    return sorted(filas)


def huella_del_canon(ruta_canon: Path) -> str:
    """SHA-256 de la serializacion determinista de los elementos indexables."""
    conexion = sqlite3.connect(str(ruta_canon))
    try:
        resumen = hashlib.sha256()
        for identidad, clave, texto in _elementos_del_canon(conexion):
            resumen.update(f"{identidad}\x1f{clave}\x1f{texto}\x1e".encode())
        return resumen.hexdigest()
    finally:
        conexion.close()


# --------------------------------------------------------------------------
# Construccion, borrado y volcado logico
# --------------------------------------------------------------------------


def _tokens(texto: str) -> tuple[str, ...]:
    return lexical.terminos_significativos(texto)[:TOKENS_POR_ELEMENTO_MAXIMOS]


def _podar(dims: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """A lo sumo ``DIMENSIONES_MAXIMAS_POR_VECTOR``, conservando el mayor peso."""
    ordenadas = sorted(dims)
    if len(ordenadas) <= DIMENSIONES_MAXIMAS_POR_VECTOR:
        return ordenadas
    ordenadas.sort(key=lambda dv: (-dv[1], dv[0]))
    return sorted(ordenadas[:DIMENSIONES_MAXIMAS_POR_VECTOR])


def construir(ruta_canon: Path, ruta_sidecar: Path) -> None:
    """Construye el sidecar ENTERO desde el canon. Borra lo previo primero.

    Borrar antes de construir es tambien lo que evita la coexistencia de
    indice viejo y nuevo que TOL-207 obliga a contar dentro del presupuesto.
    """
    borrar(ruta_sidecar)
    conexion_canon = sqlite3.connect(str(ruta_canon))
    try:
        elementos = _elementos_del_canon(conexion_canon)
    finally:
        conexion_canon.close()
    huella = huella_del_canon(ruta_canon)

    tokens_por_elemento = {e: frozenset(_tokens(texto)) for e, _clave, texto in elementos}
    total = len(elementos)

    frecuencia: dict[str, int] = {}
    for presentes in tokens_por_elemento.values():
        for termino in presentes:
            frecuencia[termino] = frecuencia.get(termino, 0) + 1
    admitidos = sorted(t for t, n in frecuencia.items() if n >= FRECUENCIA_DOCUMENTAL_MINIMA)
    if len(admitidos) > VOCABULARIO_MAXIMO:
        por_frecuencia = sorted(admitidos, key=lambda t: (-frecuencia[t], t))
        admitidos = sorted(por_frecuencia[:VOCABULARIO_MAXIMO])
    dimension_de = {termino: indice for indice, termino in enumerate(admitidos)}

    coocurrencias: dict[tuple[int, int], int] = {}
    for presentes in tokens_por_elemento.values():
        en_vocabulario = sorted(dimension_de[t] for t in presentes if t in dimension_de)
        for t in en_vocabulario:
            for c in en_vocabulario:
                if t != c:
                    coocurrencias[t, c] = coocurrencias.get((t, c), 0) + 1

    vectores_de_termino: dict[int, list[tuple[int, int]]] = {}
    for (t, c), conjunta in sorted(coocurrencias.items()):
        ppmi = math.log((conjunta * total) / (frecuencia[admitidos[t]] * frecuencia[admitidos[c]]))
        if ppmi <= 0:
            continue
        peso = round(ppmi * ESCALA_FIJA)
        if peso <= 0:
            # El formato persistido exige pesos estrictamente positivos
            # (paquete de correccion 03): un ppmi minusculo que redondea a
            # cero no se persiste, porque un peso cero no aporta candidatura
            # ni producto y romperia el invariante que valida el lector.
            continue
        vectores_de_termino.setdefault(t, []).append((c, peso))
    vectores_de_termino = {t: _podar(dims) for t, dims in vectores_de_termino.items()}

    filas_de_elemento: list[tuple[str, str, str, int]] = []
    filas_de_posting: list[tuple[int, str]] = []
    for elemento, clave, _texto in elementos:
        acumulado: dict[int, int] = {}
        for termino in sorted(tokens_por_elemento[elemento]):
            for dimension, valor in vectores_de_termino.get(dimension_de.get(termino, -1), []):
                acumulado[dimension] = acumulado.get(dimension, 0) + valor
        dims = _podar((d, v) for d, v in acumulado.items() if v > 0)
        if not dims:
            continue
        norma_cuadrada = sum(valor * valor for _d, valor in dims)
        filas_de_elemento.append(
            (elemento, clave, json.dumps(dims, separators=(",", ":")), norma_cuadrada)
        )
        filas_de_posting.extend((dimension, elemento) for dimension, _v in dims)

    salida = sqlite3.connect(str(ruta_sidecar))
    try:
        salida.executescript(
            "CREATE TABLE metadatos (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);"
            "CREATE TABLE vocabulario (termino TEXT PRIMARY KEY, dimension INTEGER NOT NULL,"
            " frecuencia_documental INTEGER NOT NULL);"
            "CREATE TABLE vectores_de_termino (dimension INTEGER PRIMARY KEY,"
            " dimensiones TEXT NOT NULL);"
            "CREATE TABLE vectores_de_elemento (elemento TEXT PRIMARY KEY,"
            " clave_de_sujeto TEXT NOT NULL, dimensiones TEXT NOT NULL,"
            " norma_cuadrada INTEGER NOT NULL);"
            "CREATE TABLE posting (dimension INTEGER NOT NULL, elemento TEXT NOT NULL);"
            "CREATE INDEX ix_posting_dimension ON posting (dimension, elemento);"
        )
        metadatos = {
            "version_del_algoritmo": VERSION_DEL_ALGORITMO,
            "version_de_tokenizacion": VERSION_DE_TOKENIZACION,
            "huella_del_canon": huella,
            "parametros": json.dumps(PARAMETROS_CONGELADOS, sort_keys=True),
            "elementos": str(total),
            "terminos": str(len(admitidos)),
        }
        salida.executemany("INSERT INTO metadatos VALUES (?, ?)", sorted(metadatos.items()))
        salida.executemany(
            "INSERT INTO vocabulario VALUES (?, ?, ?)",
            [(termino, dimension_de[termino], frecuencia[termino]) for termino in admitidos],
        )
        salida.executemany(
            "INSERT INTO vectores_de_termino VALUES (?, ?)",
            [
                (dimension, json.dumps(dims, separators=(",", ":")))
                for dimension, dims in sorted(vectores_de_termino.items())
                if dims
            ],
        )
        salida.executemany(
            "INSERT INTO vectores_de_elemento VALUES (?, ?, ?, ?)", filas_de_elemento
        )
        salida.executemany("INSERT INTO posting VALUES (?, ?)", sorted(filas_de_posting))
        salida.commit()
    finally:
        salida.close()


def borrar(ruta_sidecar: Path) -> None:
    """Borra el sidecar ENTERO: fichero principal, wal, shm y journal."""
    for sufijo in SUFIJOS_DE_FICHERO:
        Path(f"{ruta_sidecar}{sufijo}").unlink(missing_ok=True)


def residuos(ruta_sidecar: Path) -> tuple[str, ...]:
    """Ficheros del sidecar que siguen existiendo. Tras borrar: ninguno."""
    return tuple(
        f"{ruta_sidecar.name}{sufijo}"
        for sufijo in SUFIJOS_DE_FICHERO
        if Path(f"{ruta_sidecar}{sufijo}").exists()
    )


def volcado_logico(
    ruta_sidecar: Path,
) -> tuple[tuple[str, tuple[tuple[object, ...], ...]], ...]:
    """Contenido logico completo y ordenado: la base de toda igualdad."""
    conexion = sqlite3.connect(str(ruta_sidecar))
    try:
        volcado = []
        for tabla in TABLAS_DEL_SIDECAR:
            filas = conexion.execute(f"SELECT * FROM {tabla}").fetchall()
            volcado.append((tabla, tuple(sorted(tuple(fila) for fila in filas))))
        return tuple(volcado)
    finally:
        conexion.close()


# --------------------------------------------------------------------------
# Validacion logica del formato persistido (paquete de correccion 03)
#
# quick_check garantiza paginas SQLite integras, no valores logicos validos.
# Todo dato consumido por una consulta se valida aqui antes de usarse, y toda
# violacion es IndiceCorruptoError con mensaje minimizado: tabla, tipo de
# defecto y posicion ordinal en el alcance consumido; jamas la celda.
# --------------------------------------------------------------------------

#: Tolerancia exclusiva para el error de evaluacion en coma flotante del
#: coseno: con la norma igual exacta a la suma de cuadrados, Cauchy-Schwarz
#: acota el cociente a 1 en aritmetica exacta y el error de evaluacion ronda
#: 1e-15; por encima de esta holgura solo hay corrupcion.
_TOLERANCIA_DE_COSENO: Final = 1e-9

#: El maximo INTEGER que SQLite declara almacenar; por encima, la celda ya no
#: es un entero exacto y el punto fijo deja de ser representable.
_ENTERO_MAXIMO_DE_SQLITE: Final = 2**63 - 1

#: Formato canonico exacto de una identidad persistida en el sidecar. Las
#: clases proceden del contrato comun (unica fuente de nombres); usarlas no
#: modifica la capa comun. Se aplica con ``fullmatch`` y sin anclas: un salto
#: de linea final o cualquier apendice invalida, sin la ambiguedad de ``$``.
_FORMATO_DE_IDENTIDAD_PERSISTIDA: Final = re.compile(
    rf"({'|'.join(re.escape(clase.value) for clase in Clase)}):([1-9][0-9]*)"
)

#: Formato canonico exacto de la huella del canon persistida en metadatos:
#: el hexdigest de un SHA-256, 64 caracteres, minusculas, sin nada mas. Se
#: aplica con ``fullmatch`` y sin anclas, por la misma razon que el anterior
#: (paquete de correccion 04).
_FORMATO_DE_HUELLA_PERSISTIDA: Final = re.compile(r"[0-9a-f]{64}")


def _es_entero_real(valor: object) -> TypeGuard[int]:
    """``int`` exacto: ``bool`` es subtipo de ``int`` y no es un entero real."""
    return type(valor) is int


def _identidad_persistida_valida(valor: object) -> bool:
    """Cadena completa con clase real, ``:`` unico y entero ASCII positivo
    sin ceros iniciales, sin espacios y sin contenido adicional."""
    return type(valor) is str and _FORMATO_DE_IDENTIDAD_PERSISTIDA.fullmatch(valor) is not None


def _huella_persistida_valida(valor: object) -> bool:
    """Hexdigest SHA-256 canonico: 64 caracteres de ``[0-9a-f]``, nada mas.

    Una celda que no lo cumpla no es una huella y no puede compararse con
    ninguna: el indice esta CORRUPTO, no desfasado (paquete 04).
    """
    return type(valor) is str and _FORMATO_DE_HUELLA_PERSISTIDA.fullmatch(valor) is not None


def _pares_de_vector_validados(
    celda: object, *, tabla: str, posicion: int, terminos_totales: int
) -> list[tuple[int, int]]:
    """La UNICA deserializacion admitida de un vector persistido.

    Un vector valido es exactamente: lista JSON de pares de longitud dos;
    dimension entera real en ``[0, terminos_totales)``; peso entero real
    estrictamente positivo y representable; sin dimensiones repetidas; en
    orden canonico ascendente; con a lo sumo
    ``DIMENSIONES_MAXIMAS_POR_VECTOR`` pares. Nada mas. ``JSONDecodeError``,
    ``TypeError`` y ``ValueError`` no escapan: aqui se traducen.
    """

    def _corrupto(defecto: str) -> IndiceCorruptoError:
        msg = (
            f"{tabla}: vector persistido invalido "
            f"({defecto}; fila {posicion} del alcance consumido)"
        )
        return IndiceCorruptoError(msg)

    if type(celda) is not str:
        raise _corrupto("la celda no es texto")
    try:
        crudo = json.loads(celda)
    except ValueError as error:  # JSONDecodeError es subtipo de ValueError
        raise _corrupto("no es JSON valido") from error
    if type(crudo) is not list:
        raise _corrupto("la raiz no es una lista")
    if len(crudo) > DIMENSIONES_MAXIMAS_POR_VECTOR:
        raise _corrupto("cardinalidad superior a la maxima")
    pares: list[tuple[int, int]] = []
    anterior = -1
    for par in crudo:
        if type(par) is not list or len(par) != 2:
            raise _corrupto("entrada que no es un par de longitud dos")
        dimension, peso = par
        if not _es_entero_real(dimension):
            raise _corrupto("dimension que no es un entero real")
        if not _es_entero_real(peso):
            raise _corrupto("peso que no es un entero real")
        if dimension < 0 or dimension >= terminos_totales:
            raise _corrupto("dimension fuera del vocabulario")
        if peso <= 0:
            raise _corrupto("peso no estrictamente positivo")
        if peso > _ENTERO_MAXIMO_DE_SQLITE:
            raise _corrupto("peso no representable")
        if dimension <= anterior:
            raise _corrupto("dimensiones repetidas o fuera del orden canonico")
        anterior = dimension
        pares.append((dimension, peso))
    return pares


def _norma_cuadrada_validada(celda: object, pares: list[tuple[int, int]], *, posicion: int) -> int:
    """Entera real, estrictamente positiva, representable e IGUAL exacta a la
    suma de los cuadrados de los pesos validados. Una discrepancia es
    corrupcion logica: con esto no hay division por cero, ni raiz de
    negativo, ni coseno no finito por datos del sidecar."""

    def _corrupto(defecto: str) -> IndiceCorruptoError:
        msg = (
            "vectores_de_elemento: norma cuadrada invalida "
            f"({defecto}; fila {posicion} del alcance consumido)"
        )
        return IndiceCorruptoError(msg)

    if not _es_entero_real(celda):
        raise _corrupto("no es un entero real")
    if celda <= 0:
        raise _corrupto("no es estrictamente positiva")
    if celda > _ENTERO_MAXIMO_DE_SQLITE:
        raise _corrupto("no es representable")
    if celda != sum(peso * peso for _dimension, peso in pares):
        raise _corrupto("no coincide con la suma de cuadrados de los pesos validados")
    return celda


# --------------------------------------------------------------------------
# Lectura instrumentada, fail closed
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CoincidenciaVectorial:
    """Identificador, clave de sujeto y similitud. Nunca contenido."""

    elemento: str
    clave_de_sujeto: str
    similitud_fija: int
    solapamiento: int

    @property
    def banda(self) -> str:
        """Granularidad de presentacion para la traza; no umbral de seleccion."""
        if self.similitud_fija >= ESCALA_FIJA // 2:
            return "alta"
        if self.similitud_fija >= ESCALA_FIJA // 4:
            return "media"
        return "baja"


@dataclass(frozen=True, slots=True)
class ConsultaVectorialRegistrada:
    """Una consulta al indice realmente ejecutada, con sus conteos."""

    operacion: str
    terminos_en_vocabulario: int
    dimensiones_consultadas: int
    elementos_examinados: int
    devueltos: int


@dataclass(slots=True)
class RegistroVectorial:
    """Lo que el lector ejecuto, para auditar la activacion tardia."""

    consultas: list[ConsultaVectorialRegistrada] = field(default_factory=list)


class LectorVectorial:
    """Abre el sidecar comprobando integridad, versiones y huella del canon.

    Todo fallo es cerrado y tipado: quien lo reciba no puede confundirlo con
    «cero resultados», y el motor comun actual no lo adjudica como ``S7`` —esa
    limitacion esta registrada en el paquete 12 y no se disimula aqui.
    """

    def __init__(self, ruta_canon: Path, ruta_sidecar: Path) -> None:
        if not ruta_sidecar.is_file():
            # Sin la ruta: quien construye el lector se la paso y ya la tiene,
            # el rastreo conserva el sitio de la llamada, y asi NINGUNA
            # interpolacion de esta apertura procede de una celda, de una
            # excepcion interna ni del entorno (paquete de correccion 04).
            msg = "no existe el indice vectorial en la ruta declarada"
            raise IndiceInexistenteError(msg)
        self.registro = RegistroVectorial()
        self._conexion = sqlite3.connect(str(ruta_sidecar))
        try:
            integridad = self._conexion.execute("PRAGMA quick_check").fetchone()
            if integridad is None or integridad[0] != "ok":
                msg = "el sidecar no supera la comprobacion de integridad"
                raise IndiceCorruptoError(msg)
            presentes = {
                str(nombre)
                for (nombre,) in self._conexion.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            if not set(TABLAS_DEL_SIDECAR) <= presentes:
                faltan = sorted(set(TABLAS_DEL_SIDECAR) - presentes)
                msg = f"el sidecar no contiene las tablas esperadas: faltan {faltan}"
                raise IndiceCorruptoError(msg)
            metadatos = dict(self._conexion.execute("SELECT clave, valor FROM metadatos"))
        except sqlite3.DatabaseError as error:
            self._conexion.close()
            # El texto del error fisico puede arrastrar fragmentos del
            # contenido de la base: se conserva como CAUSA, no se reproduce.
            msg = "el sidecar no es una base legible"
            raise IndiceCorruptoError(msg) from error
        except IndiceCorruptoError:
            self._conexion.close()
            raise
        if (
            metadatos.get("version_del_algoritmo") != VERSION_DEL_ALGORITMO
            or metadatos.get("version_de_tokenizacion") != VERSION_DE_TOKENIZACION
        ):
            self._conexion.close()
            msg = "el sidecar declara versiones incompatibles con este lector"
            raise IndiceCorruptoError(msg)
        if metadatos.get("parametros") != json.dumps(PARAMETROS_CONGELADOS, sort_keys=True):
            self._conexion.close()
            msg = "el sidecar se construyo con otros parametros congelados"
            raise IndiceCorruptoError(msg)
        conteos: dict[str, int] = {}
        for clave_de_conteo in ("elementos", "terminos"):
            declarado = metadatos.get(clave_de_conteo)
            if (
                type(declarado) is not str
                or not declarado.isascii()
                or not declarado.isdigit()
                or (len(declarado) > 1 and declarado.startswith("0"))
            ):
                self._conexion.close()
                msg = f"metadatos: el conteo {clave_de_conteo!r} no es un entero canonico"
                raise IndiceCorruptoError(msg)
            conteos[clave_de_conteo] = int(declarado)
        if conteos["terminos"] > VOCABULARIO_MAXIMO:
            self._conexion.close()
            msg = "metadatos: el conteo 'terminos' excede el vocabulario maximo"
            raise IndiceCorruptoError(msg)
        #: Cota superior del rango de dimensiones que valida cada consulta.
        self._terminos_totales = conteos["terminos"]
        # El formato se valida ANTES de recomputar la huella del canon: una
        # celda que no es una huella no puede compararse con ninguna, y asi
        # el caso corrupto ni siquiera lee el canon entero (paquete 04).
        declarada = metadatos.get("huella_del_canon")
        if not _huella_persistida_valida(declarada):
            self._conexion.close()
            msg = "metadatos: la huella del canon no tiene el formato canonico de SHA-256"
            raise IndiceCorruptoError(msg)
        if declarada != huella_del_canon(ruta_canon):
            self._conexion.close()
            msg = "el canon cambio desde que se construyo el indice"
            raise IndiceDesfasadoError(msg)

    def close(self) -> None:
        self._conexion.close()

    def consultar(
        self, terminos: Sequence[str], *, excluidos: frozenset[str] = frozenset()
    ) -> tuple[CoincidenciaVectorial, ...]:
        """Top-K por coseno entre quienes comparten dimensiones con la consulta.

        Tres sentencias dirigidas al sidecar: vocabulario de los terminos,
        vectores de esos terminos, y candidatos de ``posting`` con su vector
        en una sola sentencia (LEFT JOIN con la columna de solapamiento, para
        que una referencia huerfana aparezca en vez de desaparecer). Devuelve
        identificadores; los ``excluidos`` no consumen plazas del top-K.

        Todo dato consumido se valida (paquete de correccion 03) y toda
        corrupcion —logica o fisica— cierra la conexion y propaga
        ``IndiceCorruptoError``: un lector que entrego corrupcion no queda
        parcialmente valido.
        """
        try:
            return self._consultar_validando(terminos, excluidos)
        except IndiceCorruptoError:
            self._conexion.close()
            raise
        except sqlite3.DatabaseError as error:
            self._conexion.close()
            msg = "el sidecar fallo fisicamente durante la consulta"
            raise IndiceCorruptoError(msg) from error

    def _consultar_validando(
        self, terminos: Sequence[str], excluidos: frozenset[str]
    ) -> tuple[CoincidenciaVectorial, ...]:
        acotados = sorted(set(terminos))[:CONSULTA_TERMINOS_MAXIMOS]
        dimensiones_de_terminos: list[int] = []
        if acotados:
            marcas = ",".join("?" * len(acotados))
            for posicion, fila in enumerate(
                self._conexion.execute(
                    f"SELECT dimension FROM vocabulario WHERE termino IN ({marcas}) "
                    f"ORDER BY dimension",
                    acotados,
                )
            ):
                dimension = fila[0]
                if (
                    not _es_entero_real(dimension)
                    or dimension < 0
                    or dimension >= self._terminos_totales
                ):
                    msg = f"vocabulario: dimension invalida (fila {posicion} del alcance consumido)"
                    raise IndiceCorruptoError(msg)
                dimensiones_de_terminos.append(dimension)
        consulta: dict[int, int] = {}
        if dimensiones_de_terminos:
            marcas = ",".join("?" * len(dimensiones_de_terminos))
            for posicion, fila in enumerate(
                self._conexion.execute(
                    f"SELECT dimensiones FROM vectores_de_termino WHERE dimension IN ({marcas}) "
                    f"ORDER BY dimension",
                    dimensiones_de_terminos,
                )
            ):
                pares_de_termino = _pares_de_vector_validados(
                    fila[0],
                    tabla="vectores_de_termino",
                    posicion=posicion,
                    terminos_totales=self._terminos_totales,
                )
                for dimension, valor in pares_de_termino:
                    consulta[dimension] = consulta.get(dimension, 0) + valor
        dims = _podar(consulta.items())
        if not dims:
            self.registro.consultas.append(
                ConsultaVectorialRegistrada(
                    operacion="consulta_vectorial",
                    terminos_en_vocabulario=len(dimensiones_de_terminos),
                    dimensiones_consultadas=0,
                    elementos_examinados=0,
                    devueltos=0,
                )
            )
            return ()

        vector_consulta = dict(dims)
        marcas = ",".join("?" * len(dims))
        filas = self._conexion.execute(
            "SELECT c.elemento, c.solapamiento, v.elemento, v.clave_de_sujeto, "
            "v.dimensiones, v.norma_cuadrada FROM ("
            f"SELECT elemento, count(*) AS solapamiento FROM posting "
            f"WHERE dimension IN ({marcas}) GROUP BY elemento "
            f"HAVING solapamiento >= ? ORDER BY elemento LIMIT ?"
            ") AS c LEFT JOIN vectores_de_elemento AS v ON v.elemento = c.elemento "
            "ORDER BY c.elemento",
            (
                *[dimension for dimension, _v in dims],
                SOLAPAMIENTO_MINIMO,
                ELEMENTOS_EXAMINADOS_MAXIMOS,
            ),
        ).fetchall()

        norma_consulta = math.sqrt(sum(valor * valor for valor in vector_consulta.values()))
        puntuadas: list[CoincidenciaVectorial] = []
        for posicion, fila_candidata in enumerate(filas):
            citado, solapamiento_citado, presente, clave, dimensiones, norma_cuadrada = (
                fila_candidata
            )
            if not _identidad_persistida_valida(citado):
                msg = (
                    "posting: identidad con formato no canonico "
                    f"(fila {posicion} del alcance consumido)"
                )
                raise IndiceCorruptoError(msg)
            if citado in excluidos:
                # De una fila excluida solo se consume la identidad, que ya
                # quedo validada: su vector no participa en nada.
                continue
            if presente is None:
                msg = (
                    "posting: referencia huerfana a un elemento sin vector "
                    f"(fila {posicion} del alcance consumido)"
                )
                raise IndiceCorruptoError(msg)
            if type(clave) is not str:
                msg = (
                    "vectores_de_elemento: clave de sujeto de tipo invalido "
                    f"(fila {posicion} del alcance consumido)"
                )
                raise IndiceCorruptoError(msg)
            pares = _pares_de_vector_validados(
                dimensiones,
                tabla="vectores_de_elemento",
                posicion=posicion,
                terminos_totales=self._terminos_totales,
            )
            norma = _norma_cuadrada_validada(norma_cuadrada, pares, posicion=posicion)
            solapamiento = sum(1 for d, _v in pares if d in vector_consulta)
            if solapamiento_citado != solapamiento:
                msg = (
                    "posting: solapamiento incoherente con el vector del elemento "
                    f"(fila {posicion} del alcance consumido)"
                )
                raise IndiceCorruptoError(msg)
            producto = sum(vector_consulta.get(d, 0) * v for d, v in pares)
            if producto <= 0:
                # Imposible con pares validados y solapamiento >= 2: pesos
                # estrictamente positivos en ambos lados. Si ocurre, es
                # corrupcion, no un caso a saltar en silencio.
                msg = (
                    "vectores_de_elemento: producto escalar no positivo con "
                    f"solapamiento declarado (fila {posicion} del alcance consumido)"
                )
                raise IndiceCorruptoError(msg)
            coseno = producto / (norma_consulta * math.sqrt(norma))
            if not math.isfinite(coseno) or coseno > 1.0 + _TOLERANCIA_DE_COSENO:
                msg = (
                    "vectores_de_elemento: coseno fuera del intervalo permitido "
                    f"(fila {posicion} del alcance consumido)"
                )
                raise IndiceCorruptoError(msg)
            puntuadas.append(
                CoincidenciaVectorial(
                    elemento=citado,
                    clave_de_sujeto=clave,
                    similitud_fija=min(round(coseno * ESCALA_FIJA), ESCALA_FIJA),
                    solapamiento=solapamiento,
                )
            )
        puntuadas.sort(key=lambda c: (-c.similitud_fija, c.elemento))
        seleccion = tuple(puntuadas[:TOP_K])
        self.registro.consultas.append(
            ConsultaVectorialRegistrada(
                operacion="consulta_vectorial",
                terminos_en_vocabulario=len(dimensiones_de_terminos),
                dimensiones_consultadas=len(dims),
                elementos_examinados=len(filas),
                devueltos=len(seleccion),
            )
        )
        return seleccion


__all__ = [
    "ALMACENAMIENTO_MAXIMO_SIDECAR_B",
    "CONSULTA_TERMINOS_MAXIMOS",
    "DIMENSIONES_MAXIMAS_POR_VECTOR",
    "ELEMENTOS_EXAMINADOS_MAXIMOS",
    "ESCALA_FIJA",
    "FRECUENCIA_DOCUMENTAL_MINIMA",
    "PARAMETROS_CONGELADOS",
    "SOLAPAMIENTO_MINIMO",
    "SUFIJOS_DE_FICHERO",
    "TABLAS_DEL_SIDECAR",
    "TOKENS_POR_ELEMENTO_MAXIMOS",
    "TOP_K",
    "VERSION_DEL_ALGORITMO",
    "VERSION_DE_TOKENIZACION",
    "VOCABULARIO_MAXIMO",
    "CoincidenciaVectorial",
    "ConsultaVectorialRegistrada",
    "IndiceCorruptoError",
    "IndiceDesfasadoError",
    "IndiceInconsistenteError",
    "IndiceInexistenteError",
    "IndiceNoUtilizableError",
    "LectorVectorial",
    "RegistroVectorial",
    "borrar",
    "construir",
    "huella_del_canon",
    "residuos",
    "volcado_logico",
]
