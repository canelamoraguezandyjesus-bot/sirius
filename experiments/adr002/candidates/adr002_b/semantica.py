"""Indice semantico real: derivado, reconstruible, borrable y con proveedor fuera.

Es la pieza que faltaba para falsar la hipotesis que ``ADR-002`` dejo abierta.
El indice PPMI de ``vectores.py`` **no puede** falsarla: su vocabulario sale del
propio corpus, de modo que dos formas de decir lo mismo solo se acercan si ya
coinciden en algun elemento. Aqui los vectores vienen de **fuera**, y esa es la
unica diferencia que se pone a prueba.

EL PROVEEDOR NO ENTRA
=====================

Este modulo **no sabe** que modelo produce los vectores. Habla con un
``CodificadorSemantico``, que es un protocolo de tres miembros, y guarda en el
sidecar **cual** lo construyo. Abrirlo con otro codificador falla cerrado: un
indice construido con un modelo y consultado con otro compara cosas que no son
comparables, y eso es peor que no tener indice.

Por eso ``B04-RF-31`` se cumple aqui de forma literal —«ninguna obligacion exige
embeddings, RAG, FTS, vectores, grafos o un modelo concreto»—: cambiar de modelo
es cambiar el objeto que se pasa a ``construir``, y nada mas.

QUE NO SALE DE LA MAQUINA
=========================

Nada. El codificador se ejecuta en local; este modulo no abre conexiones de
red, no conoce direcciones remotas y no recibe credenciales. Si algun dia un
codificador remoto se autorizara, seria **otra** implementacion del mismo
protocolo y el cambio quedaria confinado a ella.

DETERMINISMO POR CONSTRUCCION
=============================

No se persiste ni un flotante. El codificador entrega enteros en punto fijo y
aqui se guardan tal cual, junto con la norma al cuadrado tambien entera: dos
construcciones sobre el mismo canon y el mismo codificador producen el mismo
fichero logico, y eso se comprueba por igualdad, no se promete.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, runtime_checkable

from experiments.adr002.candidates.adr002_b.vectores import (
    SUFIJOS_DE_FICHERO,
    IndiceCorruptoError,
    IndiceDesfasadoError,
    IndiceInexistenteError,
    IndiceNoUtilizableError,
    _elementos_del_canon,
    huella_del_canon,
)

#: Version del formato del sidecar. Un sidecar de otra version no se lee.
VERSION_DEL_FORMATO: Final = "semantica-densa-entera-v1"

#: Escala de punto fijo. La misma que usa el PPMI, por coherencia de lectura.
ESCALA_FIJA: Final = 1_000_000

#: Cota de dimensiones. Un vector mas largo no es mas semantico: es un error de
#: quien lo produce, y aceptarlo dejaria crecer el derivado sin techo.
DIMENSIONES_MAXIMAS: Final = 1024

#: Cuantas candidatas propone la senal como maximo. Es una **propuesta**: las
#: puertas ``G1-G12`` deciden despues, igual que con cualquier otra senal.
TOP_K: Final = 8

#: Coseno minimo para proponer. Una similitud baja no es una candidata debil:
#: es ruido, y proponerla obligaria a las puertas a limpiar lo que la senal
#: deberia no haber dicho.
COSENO_MINIMO: Final = 0.55

TABLAS_DEL_SIDECAR: Final[tuple[str, ...]] = ("metadatos", "vectores_de_elemento")

_DDL: Final = """
CREATE TABLE metadatos (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE vectores_de_elemento (
    identidad TEXT PRIMARY KEY,
    vector TEXT NOT NULL,
    norma_cuadrada INTEGER NOT NULL
);
"""


class CodificadorNoDisponibleError(RuntimeError):
    """El codificador pedido no puede usarse en esta maquina.

    Es un error **tipado y explicito**, nunca una degradacion silenciosa a otra
    senal: un candidato que dijera «no habia modelo, uso lo lexico» mediria una
    cosa distinta de la que declara y lo haria sin que nadie se enterase.
    """


@runtime_checkable
class CodificadorSemantico(Protocol):
    """Lo unico que este modulo necesita saber de un modelo. Tres miembros.

    Que sea tan estrecho es el punto: el proveedor no puede filtrarse hacia el
    indice, ni el indice hacia el proveedor.
    """

    @property
    def identificador(self) -> str:
        """Nombre y version del modelo. Viaja al sidecar y se compara al abrir."""
        ...

    @property
    def dimensiones(self) -> int:
        """Longitud fija de los vectores que entrega."""
        ...

    def codificar(self, textos: Sequence[str]) -> tuple[tuple[int, ...], ...]:
        """Un vector de enteros en punto fijo por texto, en el mismo orden."""
        ...


def _validar_vector(vector: Sequence[int], dimensiones: int, *, de: str) -> tuple[int, ...]:
    if len(vector) != dimensiones:
        msg = f"{de}: el codificador entrego {len(vector)} dimensiones y declara {dimensiones}"
        raise IndiceCorruptoError(msg)
    if any(not isinstance(v, int) or isinstance(v, bool) for v in vector):
        msg = f"{de}: el codificador entrego algo que no es entero; no se persisten flotantes"
        raise IndiceCorruptoError(msg)
    return tuple(vector)


def construir(ruta_canon: Path, ruta_sidecar: Path, codificador: CodificadorSemantico) -> None:
    """Construye el sidecar ENTERO desde el canon. Borra lo previo primero.

    Borrar antes de construir evita que el indice viejo y el nuevo coexistan,
    que es lo que ``TOL-207`` obliga a contar dentro del presupuesto de memoria.
    """
    if not 0 < codificador.dimensiones <= DIMENSIONES_MAXIMAS:
        msg = (
            f"dimensiones fuera de cota: {codificador.dimensiones}; "
            f"el maximo es {DIMENSIONES_MAXIMAS}"
        )
        raise IndiceCorruptoError(msg)
    borrar(ruta_sidecar)
    conexion_canon = sqlite3.connect(str(ruta_canon))
    try:
        elementos = _elementos_del_canon(conexion_canon)
    finally:
        conexion_canon.close()
    huella = huella_del_canon(ruta_canon)

    identidades = [identidad for identidad, _clave, _texto in elementos]
    # El texto que se codifica es el del canon, tal cual. Ni la razon de
    # criticidad ni ninguna anotacion del banco entran aqui: el sidecar se
    # construye con lo que Sirius guardo, no con lo que el oraculo sabe.
    vectores = codificador.codificar([texto for _i, _c, texto in elementos])
    if len(vectores) != len(elementos):
        msg = f"el codificador devolvio {len(vectores)} vectores para {len(elementos)} elementos"
        raise IndiceCorruptoError(msg)

    conexion = sqlite3.connect(str(ruta_sidecar))
    try:
        conexion.executescript(_DDL)
        conexion.executemany(
            "INSERT INTO metadatos (clave, valor) VALUES (?, ?)",
            [
                ("version_del_formato", VERSION_DEL_FORMATO),
                ("codificador", codificador.identificador),
                ("dimensiones", str(codificador.dimensiones)),
                ("escala_fija", str(ESCALA_FIJA)),
                ("huella_del_canon", huella),
                ("elementos", str(len(elementos))),
            ],
        )
        filas = []
        for identidad, vector in zip(identidades, vectores, strict=True):
            valido = _validar_vector(vector, codificador.dimensiones, de=identidad)
            filas.append(
                (
                    identidad,
                    json.dumps(list(valido), separators=(",", ":")),
                    sum(v * v for v in valido),
                )
            )
        conexion.executemany(
            "INSERT INTO vectores_de_elemento (identidad, vector, norma_cuadrada) VALUES (?, ?, ?)",
            filas,
        )
        conexion.commit()
    finally:
        conexion.close()


def borrar(ruta_sidecar: Path) -> None:
    """Elimina el sidecar y sus ficheros auxiliares. Idempotente."""
    for sufijo in SUFIJOS_DE_FICHERO:
        Path(f"{ruta_sidecar}{sufijo}").unlink(missing_ok=True)


def residuos(ruta_sidecar: Path) -> tuple[str, ...]:
    """Lo que quedo despues de borrar. Vacio es la unica respuesta correcta."""
    return tuple(
        f"{ruta_sidecar.name}{sufijo}"
        for sufijo in SUFIJOS_DE_FICHERO
        if Path(f"{ruta_sidecar}{sufijo}").exists()
    )


@dataclass(frozen=True, slots=True)
class CoincidenciaSemantica:
    """Una propuesta de la senal: identidad y similitud. **Nunca contenido**."""

    identidad: str
    similitud: float


class LectorSemantico:
    """Lectura del sidecar, siempre fallando cerrado.

    Comprueba tres cosas antes de responder nada: que el formato es el suyo,
    que el modelo es el mismo con el que se construyo, y que el canon no ha
    cambiado desde entonces. Cualquiera de las tres que falle es un error
    tipado; ninguna degrada a «devuelvo lo que pueda».
    """

    def __init__(
        self,
        ruta_sidecar: Path,
        ruta_canon: Path,
        codificador: CodificadorSemantico,
    ) -> None:
        if not ruta_sidecar.exists():
            msg = f"no hay indice semantico en {ruta_sidecar.name}"
            raise IndiceInexistenteError(msg)
        self._codificador = codificador
        self._conexion = sqlite3.connect(f"file:{ruta_sidecar}?mode=ro", uri=True)
        try:
            metadatos = {
                str(c): str(v)
                for c, v in self._conexion.execute("SELECT clave, valor FROM metadatos")
            }
        except sqlite3.DatabaseError as fallo:
            self._conexion.close()
            msg = "el indice semantico no es una base legible"
            raise IndiceCorruptoError(msg) from fallo

        if metadatos.get("version_del_formato") != VERSION_DEL_FORMATO:
            self._conexion.close()
            msg = "versiones incompatibles del formato del indice semantico"
            raise IndiceCorruptoError(msg)
        if metadatos.get("codificador") != codificador.identificador:
            self._conexion.close()
            msg = (
                "el indice se construyo con otro codificador; comparar vectores de "
                "modelos distintos no compara nada"
            )
            raise IndiceCorruptoError(msg)
        if metadatos.get("dimensiones") != str(codificador.dimensiones):
            self._conexion.close()
            msg = "el indice declara otras dimensiones que el codificador actual"
            raise IndiceCorruptoError(msg)
        if metadatos.get("huella_del_canon") != huella_del_canon(ruta_canon):
            self._conexion.close()
            msg = "el canon cambio desde que se construyo el indice semantico"
            raise IndiceDesfasadoError(msg)

    def close(self) -> None:
        self._conexion.close()

    def __enter__(self) -> LectorSemantico:
        return self

    def __exit__(self, *_excepcion: object) -> None:
        self.close()

    def consultar(
        self, consulta: str, *, k: int = TOP_K, minimo: float = COSENO_MINIMO
    ) -> tuple[CoincidenciaSemantica, ...]:
        """Las ``k`` identidades mas proximas por coseno, sobre el umbral.

        Devuelve identidades y similitudes; **jamas texto**. El contenido lo
        materializa despues el puerto canonico con una consulta dirigida, que es
        lo que mantiene una sola fuente de verdad.
        """
        vector = _validar_vector(
            self._codificador.codificar([consulta])[0],
            self._codificador.dimensiones,
            de="consulta",
        )
        norma_consulta = sum(v * v for v in vector)
        if norma_consulta == 0:
            return ()
        coincidencias: list[CoincidenciaSemantica] = []
        for identidad, crudo, norma in self._conexion.execute(
            "SELECT identidad, vector, norma_cuadrada FROM vectores_de_elemento ORDER BY identidad"
        ):
            if int(norma) == 0:
                continue
            otro = json.loads(str(crudo))
            producto = sum(a * b for a, b in zip(vector, otro, strict=True))
            coseno = producto / ((norma_consulta**0.5) * (int(norma) ** 0.5))
            if coseno >= minimo:
                coincidencias.append(CoincidenciaSemantica(str(identidad), coseno))
        coincidencias.sort(key=lambda c: (-c.similitud, c.identidad))
        return tuple(coincidencias[:k])


__all__ = [
    "COSENO_MINIMO",
    "DIMENSIONES_MAXIMAS",
    "ESCALA_FIJA",
    "TABLAS_DEL_SIDECAR",
    "TOP_K",
    "VERSION_DEL_FORMATO",
    "CodificadorNoDisponibleError",
    "CodificadorSemantico",
    "CoincidenciaSemantica",
    "IndiceCorruptoError",
    "IndiceDesfasadoError",
    "IndiceInexistenteError",
    "IndiceNoUtilizableError",
    "LectorSemantico",
    "borrar",
    "construir",
    "residuos",
]
