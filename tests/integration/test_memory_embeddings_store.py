"""Las huellas de los recuerdos en sirius.db, con sqlite-vec (pieza F de ADR-233, ADR-238).

Sobre una base de verdad, creada con las migraciones, y la extensión de verdad.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from sirius.adapters.persistence import sqlite_memory_embeddings
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_memory_embeddings import (
    SqliteMemoryEmbeddingStore,
    build_sqlite_memory_embedding_store,
)
from sirius.adapters.persistence.sqlite_memory_repository import (
    SqliteMemoryRepository,
    build_sqlite_memory_repository,
)

pytestmark = pytest.mark.integration

_MODELO = "modelo-de-huellas"


@pytest.fixture
def base(tmp_path: Path) -> Path:
    ruta = tmp_path / "sirius.db"
    upgrade_to_head(ruta)
    return ruta


@pytest.fixture
def recuerdos(base: Path) -> Iterator[SqliteMemoryRepository]:
    repositorio = build_sqlite_memory_repository(base)
    yield repositorio
    repositorio.close()


@pytest.fixture
def huellas(base: Path) -> Iterator[SqliteMemoryEmbeddingStore]:
    almacen = build_sqlite_memory_embedding_store(base)
    yield almacen
    almacen.close()


def _guarda(recuerdos: SqliteMemoryRepository, texto: str) -> tuple[int, int]:
    recuerdo = recuerdos.create_memory(texto, "manual")
    return recuerdo.id, recuerdo.current_revision.id


def test_sqlite_vec_carga_y_las_huellas_viven_en_la_misma_base(
    base: Path, recuerdos: SqliteMemoryRepository, huellas: SqliteMemoryEmbeddingStore
) -> None:
    memoria, revision = _guarda(recuerdos, "Le pirra el cocido.")

    huellas.save(memoria, revision, _MODELO, [1.0, 0.0])

    assert huellas.available
    assert huellas.count() == huellas.count(_MODELO) == 1
    with sqlite3.connect(base) as conexion:
        assert conexion.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone() == (1,)


def test_faltan_las_de_los_recuerdos_sin_huella_de_ese_modelo_los_nuevos_antes(
    recuerdos: SqliteMemoryRepository, huellas: SqliteMemoryEmbeddingStore
) -> None:
    viejo = _guarda(recuerdos, "Tiene una moto vieja.")
    nuevo = _guarda(recuerdos, "Le pirra el cocido.")

    assert [(p.memory_id, p.content) for p in huellas.pending(_MODELO, 10)] == [
        (nuevo[0], "Le pirra el cocido."),
        (viejo[0], "Tiene una moto vieja."),
    ]

    huellas.save(*nuevo, _MODELO, [1.0])

    assert [p.memory_id for p in huellas.pending(_MODELO, 10)] == [viejo[0]]
    assert [p.memory_id for p in huellas.pending("otro-modelo", 10)] == [nuevo[0], viejo[0]]
    assert len(huellas.pending(_MODELO, 0)) == 0


def test_al_corregir_un_recuerdo_su_huella_vieja_no_vale_y_vuelve_a_faltar(
    recuerdos: SqliteMemoryRepository, huellas: SqliteMemoryEmbeddingStore
) -> None:
    memoria, revision = _guarda(recuerdos, "Vive en Madrid.")
    huellas.save(memoria, revision, _MODELO, [1.0, 0.0])

    corregido = recuerdos.correct_memory(memoria, "Se ha mudado a Valencia.", "manual")

    [falta] = huellas.pending(_MODELO, 10)
    assert falta.revision_id == corregido.current_revision.id
    assert falta.content == "Se ha mudado a Valencia."
    assert huellas.nearest([1.0, 0.0], _MODELO, min_similarity=0.0, limit=10) == []

    huellas.save(memoria, corregido.current_revision.id, _MODELO, [0.0, 1.0])

    assert huellas.count() == 1
    assert huellas.pending(_MODELO, 10) == []


def test_busca_por_parecido_del_mas_al_menos_con_umbral_limite_y_modelo(
    recuerdos: SqliteMemoryRepository, huellas: SqliteMemoryEmbeddingStore
) -> None:
    igual = _guarda(recuerdos, "igual")
    cerca = _guarda(recuerdos, "cerca")
    lejos = _guarda(recuerdos, "lejos")
    de_otro_modelo = _guarda(recuerdos, "otro")
    huellas.save(*igual, _MODELO, [1.0, 0.0])
    huellas.save(*cerca, _MODELO, [1.0, 1.0])
    huellas.save(*lejos, _MODELO, [0.0, 1.0])
    huellas.save(*de_otro_modelo, "otro-modelo", [1.0, 0.0])

    encontrados = huellas.nearest([1.0, 0.0], _MODELO, min_similarity=0.5, limit=10)

    assert [memoria for memoria, _ in encontrados] == [igual[0], cerca[0]]
    assert encontrados[0][1] == pytest.approx(1.0)
    assert encontrados[1][1] == pytest.approx(0.7071, abs=1e-3)
    assert huellas.nearest([1.0, 0.0], _MODELO, min_similarity=0.5, limit=1) == encontrados[:1]


def test_una_huella_de_otro_tamano_o_de_ceros_no_rompe_la_busqueda(
    recuerdos: SqliteMemoryRepository, huellas: SqliteMemoryEmbeddingStore
) -> None:
    corta = _guarda(recuerdos, "corta")
    ceros = _guarda(recuerdos, "ceros")
    buena = _guarda(recuerdos, "buena")
    huellas.save(*corta, _MODELO, [1.0])
    huellas.save(*ceros, _MODELO, [0.0, 0.0])
    huellas.save(*buena, _MODELO, [1.0, 0.0])

    encontrados = huellas.nearest([1.0, 0.0], _MODELO, min_similarity=0.0, limit=10)

    assert [memoria for memoria, _ in encontrados] == [buena[0]]


def test_lo_archivado_o_borrado_se_lleva_su_huella_y_ya_no_se_encuentra_ni_falta(
    recuerdos: SqliteMemoryRepository, huellas: SqliteMemoryEmbeddingStore
) -> None:
    archivado = _guarda(recuerdos, "archivado")
    borrado = _guarda(recuerdos, "borrado")
    vigente = _guarda(recuerdos, "vigente")
    for recuerdo in (archivado, borrado, vigente):
        huellas.save(*recuerdo, _MODELO, [1.0, 0.0])

    recuerdos.archive_memory(archivado[0])
    recuerdos.delete_memory(borrado[0])

    # La huella de lo borrado o archivado no se queda en la base, ni sin buscarla.
    assert huellas.count() == 1
    assert [m for m, _ in huellas.nearest([1.0, 0.0], _MODELO, min_similarity=0.0, limit=10)] == [
        vigente[0]
    ]
    assert huellas.pending(_MODELO, 10) == []


def test_sin_sqlite_vec_guarda_pero_no_busca_por_significado(
    base: Path, recuerdos: SqliteMemoryRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_carga(conexion: object, registro: object) -> None:
        raise sqlite3.OperationalError("no se pudo cargar la extensión")

    monkeypatch.setattr(sqlite_memory_embeddings, "_load_sqlite_vec", no_carga)
    almacen = build_sqlite_memory_embedding_store(base)
    try:
        memoria, revision = _guarda(recuerdos, "Le pirra el cocido.")
        almacen.save(memoria, revision, _MODELO, [1.0, 0.0])

        assert not almacen.available
        assert almacen.count() == 1
        assert almacen.nearest([1.0, 0.0], _MODELO, min_similarity=0.0, limit=10) == []
    finally:
        almacen.close()


def test_carga_de_una_vez_los_recuerdos_pedidos_en_su_orden(
    recuerdos: SqliteMemoryRepository,
) -> None:
    primero, _ = _guarda(recuerdos, "primero")
    segundo, _ = _guarda(recuerdos, "segundo")

    cargados = recuerdos.get_memories([segundo, 999, primero])

    assert [r.current_revision.content for r in cargados] == ["segundo", "primero"]
    assert recuerdos.get_memories([]) == []
