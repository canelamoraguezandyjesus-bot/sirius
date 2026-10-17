"""La memoria con lo que midió su ordenador el 16-10-2026 (ADR-251).

Su base de ese día, con huellas de qwen3, se abre con el modelo nuevo sin mezclar
huellas; «cosas que cambian» desempata por lo más nuevo por el camino real del banco;
y «tiene» ya no trae recuerdos solo por la palabra.
"""

from __future__ import annotations

import math
import sqlite3
import struct
from collections.abc import Sequence
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

import pasar_el_banco_de_memoria as orden
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.memory_search import embedding_format
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.memory_bank import CAMBIAN, MEMORY_BANK, MemoryCase
from sirius.infrastructure.paths import resolve_paths

pytestmark = pytest.mark.integration

_REPO = Path(__file__).resolve().parents[2]
#: La cabeza de la base antes de ADR-251: la de su ordenador el 16-10-2026.
_SU_CABEZA = "b0f472943480"


class _Gemma:
    """Un EmbeddingGemma de mentira: 768 números, y apunta lo que se le pide."""

    model_name = "embeddinggemma"

    def __init__(self) -> None:
        self.pedidas: list[str] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.pedidas.extend(texts)
        return [[1.0] + [0.0] * 767 for _ in texts]


def test_su_base_con_una_huella_de_qwen3_se_abre_con_gemma_sin_mezclar_huellas(
    tmp_path: Path,
) -> None:
    rutas = resolve_paths()
    base = rutas.data_dir / "sirius.db"
    base.parent.mkdir(parents=True, exist_ok=True)
    config = Config(str(_REPO / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{base}")
    command.upgrade(config, _SU_CABEZA)
    recuerdos = build_sqlite_memory_repository(base)
    recuerdo = recuerdos.create_memory("Le pirra el cocido.", "manual")
    recuerdos.close()
    with sqlite3.connect(base) as conexion:
        conexion.execute(
            "INSERT INTO memory_embeddings (memory_id, revision_id, model, embedding, created_at)"
            " VALUES (?, ?, 'qwen3-embedding:0.6b', ?, '2026-10-16 20:00:00.000000')",
            (recuerdo.id, recuerdo.current_revision.id, struct.pack("<1024f", *[0.5] * 1024)),
        )

    # Lo que hace la ventana al abrirse con la versión nueva: migrar y calcular lo que falta.
    initialize_persistence(rutas)
    gemma = _Gemma()
    dependencias = build_conversation_dependencies(
        base, tmp_path / "copias", secret_store=FakeSecretStore(), text_embedder=gemma
    )
    servicio = dependencias.memory_embedding_service
    # Antes de recalcularla, la de qwen3 no se compara con una pregunta de gemma.
    assert servicio.nearest([1.0] + [0.0] * 767) == []

    assert servicio.embed_pending() == 1

    clave = embedding_format("embeddinggemma").key("embeddinggemma")
    with sqlite3.connect(base) as conexion:
        assert conexion.execute(
            "SELECT model, length(embedding), length(bits) FROM memory_embeddings"
        ).fetchall() == [(clave, 768 * 4, 768 // 8)]
    assert gemma.pedidas == ["title: none | text: Le pirra el cocido."]
    assert [memoria for memoria, _ in servicio.nearest([1.0] + [0.0] * 767)] == [recuerdo.id]
    dependencias.close_database_connections()


#: Cuántos números llevan las huellas de mentira: los cuatro primeros, para los textos
#: del caso; los demás, uno para cada texto que no es del caso.
_NUMEROS = 64


class _Fijadas:
    """Cada texto del caso, con el coseno que se le pide; cualquier otro, a 90 grados de
    todo, cada uno en su eje."""

    model_name = "huellas-fijadas"

    def __init__(self, tabla: dict[str, list[float]]) -> None:
        self._tabla = tabla
        self._aparte: dict[str, int] = {}

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._huella(texto) for texto in texts]

    def _huella(self, texto: str) -> list[float]:
        if texto in self._tabla:
            return list(self._tabla[texto])
        eje = 4 + self._aparte.setdefault(texto, len(self._aparte))
        vector = [0.0] * _NUMEROS
        vector[eje] = 1.0
        return vector


def _vector(*primeros: float) -> list[float]:
    return [*primeros, *[0.0] * (_NUMEROS - len(primeros))]


def _en(eje: int, coseno: float) -> list[float]:
    vector = _vector(coseno)
    vector[eje] = math.sqrt(1 - coseno * coseno)
    return vector


def _cambia(caso: MemoryCase) -> _Fijadas:
    """Lo de antes se parece 0,02 más a la pregunta que lo de ahora, y los dos se parecen
    entre sí 0,74: como en su ordenador, donde lo de antes solía ganar."""
    antes, otro, ahora = caso.memories
    de_ahora = _en(1, 0.70)
    de_antes = _vector(0.72)
    # Coseno entre los dos: 0,72 * 0,70 + y * 0,7141 = 0,74.
    de_antes[1] = (0.74 - 0.72 * 0.70) / math.sqrt(1 - 0.70**2)
    de_antes[2] = math.sqrt(1 - 0.72**2 - de_antes[1] ** 2)
    return _Fijadas(
        {caso.question: _vector(1.0), ahora: de_ahora, antes: de_antes, otro: _en(3, 0.2)}
    )


def test_en_cosas_que_cambian_va_delante_lo_de_ahora_por_el_camino_real(tmp_path: Path) -> None:
    casos = tuple(caso for caso in MEMORY_BANK if caso.family == CAMBIAN)

    aciertos = [
        orden.pasa_un_caso(caso, _cambia(caso), tmp_path / f"{numero:02d}")
        for numero, caso in enumerate(casos)
    ]

    assert aciertos == [True] * 14


def test_tiene_ya_no_trae_un_recuerdo_solo_por_la_palabra(tmp_path: Path) -> None:
    [caso] = [caso for caso in MEMORY_BANK if caso.id == "MB-071"]
    assert "Tiene dos gatos." in caso.memories

    assert orden.pasa_un_caso(caso, _Fijadas({}), tmp_path / "caso")
