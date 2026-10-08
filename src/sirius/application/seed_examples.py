"""Los ejemplos de la semilla que ve cada petición (ADR-240).

La identidad guarda todos los ejemplos de charla, que servirán para entrenarle. La
charla no los lee en fila: en cada petición van los ``SHOWN`` que más se parecen a
lo que se habla, barajados, para que Sirius coja la actitud y no repita las frases.
Es lo que pidió el propietario el 07-10-2026: que no los lea «de una manera
lineal», pero que no se borren.

El parecido lo mide el modelo de huellas que ya busca los recuerdos (ADR-238), con
lo que se le dice a Sirius en cada ejemplo. Sin él, cuentan las palabras en común,
y entre los que empatan decide el azar.
"""

from __future__ import annotations

import math
import random
import re
from collections.abc import Sequence

from sirius.application.memory_search import EMBED_BATCH, MemoryEmbeddingService
from sirius.domain.identity import SeedExample
from sirius.domain.plain_text import plain

__all__ = ["SHOWN", "SeedExamplePicker"]

#: Cuántos ejemplos lleva cada petición, como mucho.
SHOWN = 3

_WORD = re.compile(r"[^\W_]{4,}")


class SeedExamplePicker:
    """Elige los ejemplos de una petición: los que más se parecen, en orden barajado."""

    def __init__(
        self,
        embeddings: MemoryEmbeddingService | None = None,
        *,
        rng: random.Random | None = None,
    ) -> None:
        """Sin ``embeddings``, el parecido es por palabras en común."""
        self._embeddings = embeddings
        self._rng = rng or random.Random()
        #: Las huellas de lo que se dice en cada ejemplo, por modelo: no cambian.
        self._vectors: dict[tuple[str, str], list[float]] = {}

    def pick(self, examples: Sequence[SeedExample], text: str) -> tuple[SeedExample, ...]:
        """Los ``SHOWN`` ejemplos que más se parecen a ``text``, barajados.

        Nunca devuelve más de ``SHOWN``. Si hay menos, van todos, también barajados.
        """
        chosen = list(examples)
        if len(chosen) > SHOWN:
            scores = self._by_meaning(chosen, text) or self._by_words(chosen, text)
            ranked = sorted(
                range(len(chosen)), key=lambda index: (-scores[index], self._rng.random())
            )
            chosen = [chosen[index] for index in ranked[:SHOWN]]
        self._rng.shuffle(chosen)
        return tuple(chosen)

    def _by_meaning(self, examples: Sequence[SeedExample], text: str) -> list[float] | None:
        """Lo que se parece cada ejemplo a ``text`` según sus huellas, o ``None`` sin ellas."""
        if self._embeddings is None:
            return None
        query = self._embeddings.embed_query(text)
        if query is None:
            return None
        model = self._embeddings.query_model_name
        missing = sorted({e.said for e in examples if (model, e.said) not in self._vectors})
        # De pocos en pocos, como las de los recuerdos: cada tanda cabe en la paciencia
        # de la pregunta, y lo que se calculó se queda aunque la siguiente falle.
        for start in range(0, len(missing), EMBED_BATCH):
            batch = missing[start : start + EMBED_BATCH]
            vectors = self._embeddings.embed_texts(batch)
            if vectors is None:
                return None
            for said, vector in zip(batch, vectors, strict=True):
                self._vectors[(model, said)] = vector
        return [_cosine(query, self._vectors[(model, e.said)]) for e in examples]

    @staticmethod
    def _by_words(examples: Sequence[SeedExample], text: str) -> list[float]:
        words = _words(text)
        return [float(len(words & _words(e.said))) for e in examples]


def _words(text: str) -> set[str]:
    return set(_WORD.findall(plain(text)))


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """El coseno de dos huellas; si una es más corta, lo que le falta cuenta como cero."""
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=False)) / norm
