"""La búsqueda de recuerdos de cada turno, por palabras y por significado (ADR-238)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from sirius.application.memory_search import (
    EMBED_BATCH,
    MIN_SIMILARITY,
    SEARCH_LIMIT,
    MemoryEmbeddingService,
    MemorySearch,
)
from sirius.domain.memory import Memory, MemoryRevision, MemoryStatus
from sirius.ports.embeddings import EmbeddingError, PendingMemory

_AHORA = datetime(2026, 10, 7, tzinfo=UTC)


def _recuerdo(memory_id: int, texto: str) -> Memory:
    revision = MemoryRevision(memory_id * 10, memory_id, 1, texto, "manual", None, _AHORA)
    return Memory(memory_id, MemoryStatus.CURRENT, revision, _AHORA, _AHORA)


@dataclass
class _Palabras:
    encontrados: list[int] = field(default_factory=list)
    pedidos: list[tuple[str, int]] = field(default_factory=list)

    def search_memory_ids(self, query_text: str, limit: int) -> list[int]:
        self.pedidos.append((query_text, limit))
        return list(self.encontrados)


@dataclass
class _Recuerdos:
    por_id: dict[int, Memory]
    cargas: list[list[int]] = field(default_factory=list)

    def get_memories(self, memory_ids: Sequence[int]) -> list[Memory]:
        self.cargas.append(list(memory_ids))
        return [self.por_id[i] for i in memory_ids if i in self.por_id]


@dataclass
class _Huellas:
    model_name: str = "huellas"
    falla: bool = False
    pedidas: list[list[str]] = field(default_factory=list)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.pedidas.append(list(texts))
        if self.falla:
            msg = "sin modelo"
            raise EmbeddingError(msg)
        return [[float(len(texto))] for texto in texts]


@dataclass
class _Almacen:
    available: bool = True
    parecidos: list[tuple[int, float]] = field(default_factory=list)
    falla_al_buscar: bool = False
    pendientes: list[PendingMemory] = field(default_factory=list)
    guardadas: list[tuple[int, int, str, list[float]]] = field(default_factory=list)
    busquedas: list[tuple[list[float], str, float, int]] = field(default_factory=list)
    #: Recuerdos que se archivaron o borraron mientras se calculaba su huella.
    rechaza: set[int] = field(default_factory=set)

    def pending(self, model: str, limit: int) -> list[PendingMemory]:
        hechas = {memoria for memoria, _, modelo, _ in self.guardadas if modelo == model}
        return [p for p in self.pendientes if p.memory_id not in hechas][:limit]

    def save(
        self, memory_id: int, revision_id: int, model: str, embedding: Sequence[float]
    ) -> bool:
        if memory_id in self.rechaza:
            return False
        self.guardadas.append((memory_id, revision_id, model, list(embedding)))
        return True

    def nearest(
        self, embedding: Sequence[float], model: str, *, min_similarity: float, limit: int
    ) -> list[tuple[int, float]]:
        self.busquedas.append((list(embedding), model, min_similarity, limit))
        if self.falla_al_buscar:
            msg = "vec_distance_cosine falló"
            raise RuntimeError(msg)
        return list(self.parecidos)

    def count(self, model: str | None = None) -> int:
        return len(self.guardadas)


def _busqueda(
    palabras: _Palabras, almacen: _Almacen | None, huellas: _Huellas | None = None
) -> tuple[MemorySearch, _Recuerdos]:
    recuerdos = _Recuerdos({i: _recuerdo(i, f"recuerdo {i}") for i in range(1, 10)})
    servicio = (
        MemoryEmbeddingService(huellas or _Huellas(), almacen) if almacen is not None else None
    )
    return MemorySearch(palabras, recuerdos, servicio), recuerdos


def test_junta_lo_que_traen_las_palabras_y_el_significado_y_dice_como_llego_cada_uno() -> None:
    palabras = _Palabras(encontrados=[1, 2])
    almacen = _Almacen(parecidos=[(2, 0.9), (3, 0.6)])
    busqueda, recuerdos = _busqueda(palabras, almacen)

    encontrados = {f.memory.id: (f.by_words, f.similarity) for f in busqueda.find("¿y eso?")}

    assert encontrados == {1: (True, None), 2: (True, 0.9), 3: (False, 0.6)}
    assert palabras.pedidos == [("¿y eso?", SEARCH_LIMIT)]
    # Se cargan de una vez, cada uno una sola vez.
    assert len(recuerdos.cargas) == 1
    assert sorted(recuerdos.cargas[0]) == [1, 2, 3]


def test_cada_recuerdo_lleva_su_puesto_por_palabras_tal_como_llegan_por_bm25() -> None:
    """El orden de las palabras no se pierde por el camino (ronda 2 de Codex)."""
    busqueda, _ = _busqueda(_Palabras(encontrados=[3, 1, 2]), _Almacen(parecidos=[(4, 0.7)]))

    puestos = {f.memory.id: f.word_rank for f in busqueda.find("¿y eso?")}

    assert puestos == {3: 0, 1: 1, 2: 2, 4: None}


def test_el_significado_pide_el_umbral_y_el_limite_y_la_huella_de_la_pregunta() -> None:
    almacen = _Almacen()
    huellas = _Huellas()
    busqueda, _ = _busqueda(_Palabras(), almacen, huellas)

    busqueda.find("cocido")

    assert huellas.pedidas == [["cocido"]]
    assert almacen.busquedas == [([6.0], "huellas", MIN_SIMILARITY, SEARCH_LIMIT)]


def test_sin_servicio_de_huellas_busca_solo_por_palabras() -> None:
    busqueda, _ = _busqueda(_Palabras(encontrados=[4]), None)

    assert [(f.memory.id, f.by_words, f.similarity) for f in busqueda.find("moto")] == [
        (4, True, None)
    ]


def test_si_el_modelo_de_huellas_falla_sigue_por_palabras() -> None:
    almacen = _Almacen(parecidos=[(3, 0.9)])
    busqueda, _ = _busqueda(_Palabras(encontrados=[4]), almacen, _Huellas(falla=True))

    assert [f.memory.id for f in busqueda.find("moto")] == [4]
    assert almacen.busquedas == []


def test_si_la_busqueda_por_significado_falla_sigue_por_palabras() -> None:
    almacen = _Almacen(falla_al_buscar=True)
    busqueda, _ = _busqueda(_Palabras(encontrados=[4]), almacen)

    assert [f.memory.id for f in busqueda.find("moto")] == [4]


@pytest.mark.parametrize("pregunta", ["", "   "])
def test_una_pregunta_vacia_no_pide_huella(pregunta: str) -> None:
    huellas = _Huellas()
    busqueda, _ = _busqueda(_Palabras(), _Almacen(), huellas)

    busqueda.find(pregunta)

    assert huellas.pedidas == []


def test_sin_sqlite_vec_no_pide_huella_de_la_pregunta() -> None:
    huellas = _Huellas()
    busqueda, _ = _busqueda(_Palabras(), _Almacen(available=False), huellas)

    busqueda.find("cocido")

    assert huellas.pedidas == []


def test_calcula_las_huellas_que_faltan_y_las_guarda_con_su_revision_y_su_modelo() -> None:
    almacen = _Almacen(pendientes=[PendingMemory(i, i * 10, f"recuerdo {i}") for i in range(1, 21)])
    servicio = MemoryEmbeddingService(_Huellas(), almacen)

    hechas = servicio.embed_pending()

    assert hechas == 20
    assert [(m, r, modelo) for m, r, modelo, _ in almacen.guardadas] == [
        (i, i * 10, "huellas") for i in range(1, 21)
    ]


def test_las_huellas_paran_cuando_se_les_pide_entre_un_grupo_y_el_siguiente() -> None:
    almacen = _Almacen(pendientes=[PendingMemory(i, i * 10, f"recuerdo {i}") for i in range(1, 41)])
    servicio = MemoryEmbeddingService(_Huellas(), almacen)
    grupos: list[int] = []

    def para_tras_el_primero() -> bool:
        grupos.append(len(almacen.guardadas))
        return len(almacen.guardadas) > 0

    hechas = servicio.embed_pending(should_stop=para_tras_el_primero)

    assert hechas == EMBED_BATCH
    assert grupos == [0, EMBED_BATCH]


def test_cada_grupo_es_pequeno_para_que_el_turno_espere_poco() -> None:
    """Al escribir él, el turno espera a que acabe el grupo que va por la mitad:
    cuanto más pequeño, menos espera (rondas 1 y 2 de Codex)."""
    almacen = _Almacen(pendientes=[PendingMemory(i, i * 10, f"recuerdo {i}") for i in range(1, 41)])
    huellas = _Huellas()

    MemoryEmbeddingService(huellas, almacen).embed_pending()

    assert EMBED_BATCH <= 4
    assert max(len(grupo) for grupo in huellas.pedidas) == EMBED_BATCH


def test_lo_que_se_archivo_o_borro_mientras_tanto_no_cuenta_como_hecho() -> None:
    almacen = _Almacen(
        pendientes=[PendingMemory(i, i * 10, f"recuerdo {i}") for i in (1, 2)], rechaza={2}
    )

    assert MemoryEmbeddingService(_Huellas(), almacen).embed_pending() == 1


def test_si_el_modelo_de_huellas_falla_no_guarda_nada_y_lo_deja_para_otra_vez() -> None:
    almacen = _Almacen(pendientes=[PendingMemory(1, 10, "recuerdo 1")])
    servicio = MemoryEmbeddingService(_Huellas(falla=True), almacen)

    assert servicio.embed_pending() == 0
    assert almacen.guardadas == []


def test_si_guardar_no_quita_el_pendiente_las_huellas_paran_en_vez_de_seguir_sin_fin() -> None:
    class _AlmacenQueNoGuarda(_Almacen):
        def pending(self, model: str, limit: int) -> list[PendingMemory]:
            return list(self.pendientes)

    class _HuellasQueCuentan(_Huellas):
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            if len(self.pedidas) > 3:
                msg = "pide huellas sin fin"
                raise AssertionError(msg)
            return super().embed(texts)

    almacen = _AlmacenQueNoGuarda(pendientes=[PendingMemory(1, 10, "recuerdo 1")])
    huellas = _HuellasQueCuentan()

    MemoryEmbeddingService(huellas, almacen).embed_pending()

    assert huellas.pedidas == [["recuerdo 1"]]


def test_si_el_modelo_no_da_una_huella_por_recuerdo_no_guarda_ninguna() -> None:
    class _HuellasCortas(_Huellas):
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            return super().embed(texts)[:-1]

    almacen = _Almacen(pendientes=[PendingMemory(i, i * 10, f"recuerdo {i}") for i in (1, 2)])

    assert MemoryEmbeddingService(_HuellasCortas(), almacen).embed_pending() == 0
    assert almacen.guardadas == []


def test_la_huella_de_la_pregunta_la_da_el_modelo_con_poca_paciencia() -> None:
    de_los_recuerdos = _Huellas()
    de_la_pregunta = _Huellas()
    almacen = _Almacen(pendientes=[PendingMemory(1, 10, "recuerdo 1")])
    servicio = MemoryEmbeddingService(de_los_recuerdos, almacen, query_embedder=de_la_pregunta)

    servicio.embed_pending()
    servicio.embed_query("cocido")

    assert de_los_recuerdos.pedidas == [["recuerdo 1"]]
    assert de_la_pregunta.pedidas == [["cocido"]]


def test_cargar_el_modelo_pide_una_huella_y_nunca_rompe_nada() -> None:
    huellas = _Huellas()
    MemoryEmbeddingService(huellas, _Almacen()).warm_up()
    assert huellas.pedidas == [["hola"]]

    sin_vec = _Huellas()
    MemoryEmbeddingService(sin_vec, _Almacen(available=False)).warm_up()
    assert sin_vec.pedidas == []

    MemoryEmbeddingService(_Huellas(falla=True), _Almacen()).warm_up()


# --- ADR-240: la misma pregunta una sola vez, y las huellas de los ejemplos ------------


def test_la_misma_pregunta_pide_su_huella_una_sola_vez_y_otra_pregunta_la_suya() -> None:
    """Dentro de un turno la piden la búsqueda y los ejemplos de la semilla."""
    huellas = _Huellas()
    servicio = MemoryEmbeddingService(huellas, _Almacen())

    primera = servicio.embed_query("cocido")
    segunda = servicio.embed_query("cocido")
    otra = servicio.embed_query("paella")

    assert primera == segunda == [6.0]
    assert otra == [6.0]
    assert huellas.pedidas == [["cocido"], ["paella"]]


def test_una_huella_que_falla_no_se_guarda_y_se_vuelve_a_pedir() -> None:
    huellas = _Huellas(falla=True)
    servicio = MemoryEmbeddingService(huellas, _Almacen())

    assert servicio.embed_query("cocido") is None
    huellas.falla = False
    assert servicio.embed_query("cocido") == [6.0]
    assert huellas.pedidas == [["cocido"], ["cocido"]]


def test_las_huellas_de_varios_textos_las_da_el_modelo_con_poca_paciencia() -> None:
    lento, rapido = _Huellas(model_name="lento"), _Huellas(model_name="rapido")
    servicio = MemoryEmbeddingService(lento, _Almacen(), query_embedder=rapido)

    assert servicio.embed_texts(["uno", "cuatro"]) == [[3.0], [6.0]]
    assert servicio.query_model_name == "rapido"
    assert rapido.pedidas == [["uno", "cuatro"]]
    assert lento.pedidas == []


def test_sin_huellas_para_varios_textos_devuelve_nada_y_nunca_rompe() -> None:
    assert MemoryEmbeddingService(_Huellas(falla=True), _Almacen()).embed_texts(["a"]) is None
    assert MemoryEmbeddingService(_Huellas(), _Almacen(available=False)).embed_texts(["a"]) is None
    assert MemoryEmbeddingService(_Huellas(), _Almacen()).embed_texts([]) is None


def test_si_el_modelo_no_da_una_huella_por_texto_no_devuelve_ninguna() -> None:
    class _Corto(_Huellas):
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            return super().embed(texts)[:-1]

    assert MemoryEmbeddingService(_Corto(), _Almacen()).embed_texts(["a", "b"]) is None
