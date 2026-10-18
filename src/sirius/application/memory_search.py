"""Buscar los recuerdos por palabras y por significado (pieza F de ADR-233, ADR-238).

Cada turno busca de las dos maneras y carga solo lo que encuentra:

- **Por palabras**, con la búsqueda de siempre (FTS5), ordenada por lo bien que
  casan.
- **Por significado**, con la huella de la pregunta contra las de los recuerdos.
  Lo que solo trae el significado tiene que parecerse de verdad: por debajo del
  umbral no entra.

Las huellas de los recuerdos las calcula ``MemoryEmbeddingService`` en segundo
plano. Si el modelo de huellas no está, la búsqueda sigue por palabras.

A cada modelo se le piden las huellas con el formato que recomienda su ficha para
buscar, y su umbral va con ese formato (ADR-251).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sirius.domain.memory import Memory
from sirius.infrastructure.logging import get_logger
from sirius.ports.embeddings import MemoryEmbeddingStore, TextEmbedder
from sirius.ports.knowledge_search_repository import MemoryKeywordSearch
from sirius.ports.memory_repository import MemoryLoader

__all__ = [
    "EMBEDDING_FORMATS",
    "EMBED_BATCH",
    "MIN_SIMILARITY",
    "PLAIN_FORMAT",
    "SEARCH_LIMIT",
    "EmbeddingFormat",
    "FoundMemory",
    "MemoryEmbeddingService",
    "MemorySearch",
    "embedding_format",
    "min_similarity_for",
]

_logger = get_logger(__name__)

#: Parecido mínimo, de 0 a 1, para que el significado traiga un recuerdo solo, con un
#: modelo sin formato conocido. Se fijó sin datos del propietario (ADR-238); el de
#: EmbeddingGemma ya sale de los suyos (ADR-251).
MIN_SIMILARITY = 0.5

#: Cuántos recuerdos trae cada manera de buscar, como mucho.
SEARCH_LIMIT = 12

#: Cuántas huellas se piden a la vez al modelo. Pocas: cuando el propietario
#: escribe, las huellas paran antes del grupo siguiente, y el turno espera a que
#: acabe el que va por la mitad (ronda 2 de Codex). Con el modelo ya cargado,
#: cuatro frases cortas son décimas; el primer grupo tarda además lo que tarde
#: Ollama en cargarlo, y eso el turno lo esperaría igual.
EMBED_BATCH = 4


@dataclass(frozen=True, slots=True)
class EmbeddingFormat:
    """Cómo se le piden las huellas a un modelo para buscar, y desde qué parecido cuentan.

    ``name`` va dentro de la clave de las huellas: las pedidas con otro formato, o con
    otro modelo, no se comparan con estas, y se vuelven a calcular.
    """

    name: str
    query: str
    document: str
    #: ``None``: el de los modelos sin formato conocido, ``MIN_SIMILARITY``.
    min_similarity: float | None

    def key(self, model: str) -> str:
        """La clave de las huellas de ``model`` con este formato."""
        return f"{model}#{self.name}" if self.name else model

    def for_query(self, text: str) -> str:
        return self.query.replace("{text}", text)

    def for_document(self, text: str) -> str:
        return self.document.replace("{text}", text)


#: Las frases tal cual, como hasta ADR-251: la clave es el nombre del modelo.
PLAIN_FORMAT = EmbeddingFormat("", "{text}", "{text}", None)

#: El formato que recomienda la ficha de cada modelo para buscar, por la familia en su
#: nombre de Ollama. El umbral de EmbeddingGemma es el centro del tramo en el que el
#: banco de memoria, con los parecidos que midió su ordenador el 16-10-2026, da lo
#: mismo: de 0,24 a 0,28 (ADR-251).
EMBEDDING_FORMATS: dict[str, EmbeddingFormat] = {
    "embeddinggemma": EmbeddingFormat(
        "busqueda-1",
        "task: search result | query: {text}",
        "title: none | text: {text}",
        0.26,
    ),
}


def embedding_format(model: str) -> EmbeddingFormat:
    """El formato con que se le piden las huellas a ``model``; sin uno conocido, tal cual."""
    name = model.lower()
    return next(
        (found for family, found in EMBEDDING_FORMATS.items() if family in name), PLAIN_FORMAT
    )


def min_similarity_for(model: str) -> float:
    """El parecido mínimo con que busca ``model``: el de su formato, o ``MIN_SIMILARITY``."""
    threshold = embedding_format(model).min_similarity
    return MIN_SIMILARITY if threshold is None else threshold


@dataclass(frozen=True, slots=True)
class FoundMemory:
    """Un recuerdo que trae la búsqueda, y cómo: por palabras, por significado o por las dos."""

    memory: Memory
    word_rank: int | None
    """Su puesto en la búsqueda por palabras, 0 el que mejor casa; ``None`` si no lo trajo."""
    similarity: float | None

    @property
    def by_words(self) -> bool:
        return self.word_rank is not None


class MemoryEmbeddingService:
    """Las huellas de los recuerdos: calcularlas y buscar con ellas."""

    def __init__(
        self,
        embedder: TextEmbedder,
        store: MemoryEmbeddingStore,
        *,
        query_embedder: TextEmbedder | None = None,
    ) -> None:
        """``query_embedder`` da la huella de la pregunta dentro del turno; es el
        mismo modelo con menos paciencia. Sin él, el de los recuerdos."""
        self._embedder = embedder
        self._store = store
        self._query_embedder = query_embedder or embedder
        self._format = embedding_format(embedder.model_name)
        #: La última pregunta, con su modelo y su huella. Dentro de un turno la piden
        #: la búsqueda de recuerdos y los ejemplos de la semilla (ADR-240), y Ollama
        #: solo tiene que darla una vez.
        self._last_query: tuple[str, str, list[float]] | None = None

    @property
    def model_name(self) -> str:
        return self._embedder.model_name

    @property
    def model_key(self) -> str:
        """La clave de las huellas: el modelo y su formato (ADR-251)."""
        return self._format.key(self._embedder.model_name)

    @property
    def min_similarity(self) -> float:
        """El parecido mínimo para que el significado traiga un recuerdo solo."""
        return min_similarity_for(self._embedder.model_name)

    def embed_pending(self, should_stop: Callable[[], bool] = lambda: False) -> int:
        """Calcula las huellas que faltan, las de los recuerdos nuevos antes. Devuelve cuántas.

        Lo lanza la ventana en segundo plano, al abrirse y al guardar un recuerdo.
        Si el modelo de huellas falla, para y lo intenta la vez siguiente.
        """
        model = self.model_key
        done = 0
        seen: set[tuple[int, int]] = set()
        while not should_stop():
            pending = self._store.pending(model, EMBED_BATCH)
            batch = {(memory.memory_id, memory.revision_id) for memory in pending}
            # Si vuelve lo mismo que ya se guardó, guardar no está sirviendo: se
            # para en vez de pedir huellas sin fin.
            if not pending or batch <= seen:
                break
            seen |= batch
            try:
                embeddings = self._embedder.embed(
                    [self._format.for_document(memory.content) for memory in pending]
                )
            except Exception as exc:  # sin modelo de huellas, la búsqueda sigue por palabras
                # Si ya le pidieron parar, el fallo es el de cerrar al salir, que corta la
                # petición a medias: no es un fallo del modelo, y no se avisa (#696).
                if not should_stop():
                    _logger.warning("No se pudieron calcular huellas (%s)", type(exc).__name__)
                break
            if len(embeddings) != len(pending):
                _logger.warning("El modelo de huellas no dio una por recuerdo")
                break
            for memory, embedding in zip(pending, embeddings, strict=True):
                # Si mientras tanto se archivó, se borró o se corrigió, no se guarda.
                if self._store.save(memory.memory_id, memory.revision_id, model, embedding):
                    done += 1
        return done

    def warm_up(self, should_stop: Callable[[], bool] = lambda: False) -> None:
        """Pide una huella para que Ollama cargue el modelo antes del primer turno.

        La ventana lo hace al abrirse, en segundo plano, y ``sirius-oye`` al arrancar. Si
        falla, no pasa nada: el primer turno lo cargará o seguirá por palabras. Si ya le
        pidieron parar, el fallo es el de cerrar al salir, y no se avisa (#696).
        """
        if not self._store.available:
            return
        try:
            self._embedder.embed(["hola"])
        except Exception as exc:  # sin modelo de huellas, la búsqueda sigue por palabras
            if not should_stop():
                _logger.warning("No se pudo cargar el modelo de huellas (%s)", type(exc).__name__)

    def embed_query(self, query_text: str) -> list[float] | None:
        """La huella de la pregunta, o ``None`` si no se puede buscar por significado."""
        if not self._store.available or not query_text.strip():
            return None
        model = self.query_model_name
        last = self._last_query
        if last is not None and last[0] == query_text and last[1] == model:
            return list(last[2])
        try:
            [embedding] = self._query_embedder.embed([self._format.for_query(query_text)])
        except Exception as exc:  # sin modelo de huellas, la búsqueda sigue por palabras
            _logger.warning("No se pudo calcular la huella de la pregunta (%s)", type(exc).__name__)
            return None
        self._last_query = (query_text, model, list(embedding))
        return embedding

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]] | None:
        """Las huellas de ``texts`` dentro del turno, una por texto, o ``None`` si no hay.

        Con la misma poca paciencia que la pregunta: las piden los ejemplos de la
        semilla para elegir los que más se parecen (ADR-240), y sin ellas se eligen
        por palabras.
        """
        if not self._store.available or not texts:
            return None
        try:
            embeddings = self._query_embedder.embed(
                [self._format.for_document(text) for text in texts]
            )
        except Exception as exc:  # sin modelo de huellas, los ejemplos van por palabras
            _logger.warning("No se pudieron calcular huellas (%s)", type(exc).__name__)
            return None
        if len(embeddings) != len(texts):
            _logger.warning("El modelo de huellas no dio una por texto")
            return None
        return embeddings

    @property
    def query_model_name(self) -> str:
        """La clave de las huellas que se piden dentro del turno: el modelo y su formato."""
        return self._format.key(self._query_embedder.model_name)

    def nearest(self, embedding: Sequence[float]) -> list[tuple[int, float]]:
        """Los recuerdos que se parecen a ``embedding`` por encima del umbral, del más al menos.

        Si la búsqueda por significado falla, devuelve nada y el turno sigue con lo
        que encuentren las palabras: una huella mala nunca puede romper la charla.
        """
        try:
            return self._store.nearest(
                embedding,
                self.model_key,
                min_similarity=self.min_similarity,
                limit=SEARCH_LIMIT,
            )
        except Exception as exc:  # sin búsqueda por significado, sigue por palabras
            _logger.warning("No se pudo buscar por significado (%s)", type(exc).__name__)
            return []

    def similarity_between(self, first: int, second: int) -> float | None:
        """El parecido entre dos recuerdos por sus huellas, o ``None`` si no se puede saber.

        Lo pide el desempate por lo más nuevo (ADR-251). Si falla, no desempata: nunca
        rompe el turno.
        """
        try:
            return self._store.similarity(first, second, self.model_key)
        except Exception as exc:  # sin el parecido, el orden se queda como estaba
            _logger.warning("No se pudo comparar dos recuerdos (%s)", type(exc).__name__)
            return None


class MemorySearch:
    """Lo que encuentra cada turno: por palabras, por significado, o las dos."""

    def __init__(
        self,
        keywords: MemoryKeywordSearch,
        memories: MemoryLoader,
        embeddings: MemoryEmbeddingService | None,
    ) -> None:
        self._keywords = keywords
        self._memories = memories
        self._embeddings = embeddings

    def find(self, query_text: str) -> list[FoundMemory]:
        """Los recuerdos vigentes que casan con ``query_text``, cargados de una vez.

        Las palabras llegan ordenadas por lo bien que casan (bm25), y ese puesto
        viaja con cada recuerdo hasta la ordenación final (ronda 2 de Codex).
        """
        word_ranks: dict[int, int] = {}
        for memory_id in self._keywords.search_memory_ids(query_text, SEARCH_LIMIT):
            word_ranks.setdefault(memory_id, len(word_ranks))
        similarities: dict[int, float] = {}
        if self._embeddings is not None:
            embedding = self._embeddings.embed_query(query_text)
            if embedding is not None:
                similarities = dict(self._embeddings.nearest(embedding))
        found = self._memories.get_memories(
            [*word_ranks, *(similarities.keys() - word_ranks.keys())]
        )
        return [
            FoundMemory(memory, word_ranks.get(memory.id), similarities.get(memory.id))
            for memory in found
        ]

    def similarity_between(self, first: int, second: int) -> float | None:
        """El parecido entre dos recuerdos, o ``None`` sin búsqueda por significado."""
        if self._embeddings is None:
            return None
        return self._embeddings.similarity_between(first, second)
