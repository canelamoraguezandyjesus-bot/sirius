"""Los codificadores concretos. **Aqui, y solo aqui, se nombra un modelo.**

``semantica.py`` habla con un protocolo de tres miembros y no sabe quien lo
implementa. Este modulo es el unico sitio del experimento donde aparece el
nombre de un modelo, y por eso es el unico que habria que tocar para cambiarlo.
Esa es la forma concreta que toma «el proveedor queda desacoplado».

DOS FAMILIAS, Y NO SE CONFUNDEN
===============================

* ``CodificadorDeterminista`` **no es semantico** y su nombre lo dice. No
  depende de nada, produce vectores estables y sirve para probar el ciclo de
  vida del derivado —construir, borrar, regenerar, fallar cerrado— en cualquier
  maquina y sin descargar nada. Usarlo para medir recuperacion seria medir una
  funcion de dispersion.

* Los codificadores reales cargan un modelo entrenado **fuera** de este corpus.
  Se importan de forma perezosa: quien no tenga el modelo instalado recibe un
  ``CodificadorNoDisponibleError`` tipado, nunca una degradacion callada a otra
  senal.

NADA SALE DE LA MAQUINA
=======================

Los dos codificadores reales de aqui se ejecutan en local. Ningun texto del
canon viaja a ningun servicio: el modelo entra una vez como paquete y despues
no hay red. Un codificador remoto seria otra clase en este mismo fichero y
exigiria una autorizacion que hoy no existe.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Final

from experiments.adr002.candidates.adr002_b.semantica import (
    ESCALA_FIJA,
    CodificadorNoDisponibleError,
)

#: Dimensiones del codificador determinista. Pequeno a proposito: no pretende
#: representar significado, solo ejercitar el formato.
DIMENSIONES_DETERMINISTA: Final = 32


class CodificadorDeterminista:
    """Vectores estables derivados del texto por dispersion. **No semantico.**

    Existe para que las pruebas del ciclo de vida del derivado —que son las que
    ``ADR-002`` exige para cualquier indice— corran sin instalar un modelo de
    600 MB. Dos textos parecidos NO producen vectores parecidos, y esa es
    justamente la propiedad que lo hace inutil para recuperar e inmejorable
    para comprobar que el formato es determinista.
    """

    identificador: Final = "determinista-sha256-v1"
    dimensiones: Final = DIMENSIONES_DETERMINISTA

    def codificar(self, textos: Sequence[str]) -> tuple[tuple[int, ...], ...]:
        vectores: list[tuple[int, ...]] = []
        for texto in textos:
            resumen = hashlib.sha256(texto.encode("utf-8")).digest()
            crudo = [resumen[i % len(resumen)] - 128 for i in range(self.dimensiones)]
            norma = sum(v * v for v in crudo) ** 0.5 or 1.0
            vectores.append(tuple(int(v / norma * ESCALA_FIJA) for v in crudo))
        return tuple(vectores)


class CodificadorSpacy:
    """Vectores de un modelo de spaCy entrenado sobre corpus externos.

    Dos modos, y el que se elija queda escrito en el sidecar:

    * ``estatico`` — un vector por palabra, agregado por **maximo entre pares**
      de palabras con contenido. Es la agregacion que mejor resultado dio en la
      medicion previa, y la razon es entendible: el sinonimo que salva la
      distancia es **una** palabra, y promediar la frase entera lo diluye.
    * ``contextual`` — la media de los estados ocultos del transformer.

    El modelo se carga una sola vez y se reutiliza. Cargarlo por consulta
    convertiria la latencia medida en la del arranque del modelo.
    """

    def __init__(self, modelo: str, *, modo: str = "estatico") -> None:
        if modo not in ("estatico", "contextual"):
            msg = f"modo de codificacion desconocido: {modo!r}"
            raise CodificadorNoDisponibleError(msg)
        self._modelo_nombre = modelo
        self._modo = modo
        try:
            import spacy
        except ImportError as fallo:  # pragma: no cover - depende de la maquina
            msg = (
                "spaCy no esta instalado; el codificador real no puede usarse y "
                "no se degrada en silencio a otra senal"
            )
            raise CodificadorNoDisponibleError(msg) from fallo
        try:
            self._nlp = spacy.load(modelo)
        except OSError as fallo:  # pragma: no cover - depende de la maquina
            msg = f"el modelo {modelo!r} no esta instalado en esta maquina"
            raise CodificadorNoDisponibleError(msg) from fallo
        self._dimensiones = (
            int(self._nlp.vocab.vectors.shape[1])
            if modo == "estatico"
            else self._dimensiones_contextuales()
        )

    def _dimensiones_contextuales(self) -> int:
        doc = self._nlp("texto de sondeo")
        return int(self._vector_contextual(doc).shape[0])

    @property
    def identificador(self) -> str:
        return f"spacy:{self._modelo_nombre}:{self._modo}"

    @property
    def dimensiones(self) -> int:
        return self._dimensiones

    @staticmethod
    def _vector_contextual(doc: object):  # type: ignore[no-untyped-def]
        import numpy as np

        datos = doc._.trf_data  # type: ignore[attr-defined]
        trozos = []
        for pieza in datos.last_hidden_layer_state:
            arreglo = np.asarray(
                getattr(pieza, "dataXd", None) if hasattr(pieza, "dataXd") else pieza.data
            )
            if arreglo.ndim == 1:
                arreglo = arreglo.reshape(1, -1)
            trozos.append(arreglo)
        return np.vstack(trozos).mean(axis=0) if trozos else np.zeros(768, dtype="float32")

    def codificar(self, textos: Sequence[str]) -> tuple[tuple[int, ...], ...]:
        import numpy as np

        vectores: list[tuple[int, ...]] = []
        for doc in self._nlp.pipe(list(textos)):
            if self._modo == "contextual":
                crudo = self._vector_contextual(doc)
            else:
                con_contenido = [
                    t.vector
                    for t in doc
                    if t.pos_ in ("NOUN", "PROPN", "VERB", "ADJ") and t.has_vector and not t.is_stop
                ]
                crudo = (
                    np.mean(con_contenido, axis=0)
                    if con_contenido
                    else np.zeros(self._dimensiones, dtype="float32")
                )
            norma = float(np.linalg.norm(crudo)) or 1.0
            vectores.append(tuple(int(v / norma * ESCALA_FIJA) for v in crudo))
        return tuple(vectores)


__all__ = [
    "DIMENSIONES_DETERMINISTA",
    "CodificadorDeterminista",
    "CodificadorSpacy",
]
